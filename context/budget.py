# -*- coding: utf-8 -*-
"""ContextBudget (R-203 / T-023): تجميع سياق محاسَب بالتوكنز بدل حدود الحروف.

المشكلة (roadmap R-203): كل قرار قصّ كان حدّ حروف ad-hoc محلّي
(`chars/4` في الـ orchestrator، حدود per-item في ContextBuilder، قصّ
حروف في الـ knowledge) — لا أحد يحاسب **المجموع**، فالبرومبت المجمّع قد
يتجاوز نافذة الموديل ويفشل عند المزود، أو يقصّ أهم عنصر بصمت.

الحل: `ContextBudget(model_window, reserved_output)` — قبول مرتّب
بالأهمية عبر أربع طبقات، تقدير توكنز بمقدّر واحد قابل للاستبدال، وإسقاط
حتمي (الطبقة الأدنى أولًا، الأكبر أولًا) مع تقرير `dropped[]` صريح.

## دلالات الطبقات (tier semantics)

| tier            | الدلالة                                        | الإسقاط |
|-----------------|--------------------------------------------------|---------|
| `must_have`     | بدونه المهمة مستحيلة (طلب المستخدم، الملف الهدف) | **أبدًا** — عند الفيض: خطاف تلخيص لكل عنصر، وإلا يُحتفظ به مع `overflowed=True` |
| `high`          | مرجّح الحاجة بشدة (ملفات مذكورة، نتائج خطوات)   | بعد نفاد normal |
| `normal`        | سياق داعم (ملفات keyword، بنية المشروع)         | بعد نفاد opportunistic |
| `opportunistic` | «لو فيه مساحة» (README، deps، بحث نصي)          | أول ما يُضحّى به |

- الإسقاط داخل الطبقة: **الأكبر توكنز أولًا**؛ التعادل → الأحدث إدخالًا
  أولًا (الأقدم أعلى قيمة) — ترتيب حتمي بالكامل.
- هامش أمان 10% افتراضيًا (بند مخاطر R-203: عدم دقة المقدّر).
- T-024 وصّل الوحدة بمسارات البرومبت: ``chain/context_builder.py``
  (build_prompt_section)، ``chain/knowledge.py`` (build_context)،
  ``chain/orchestrator.py`` (مقدّر _split_content)، و``build_delegate``
  في ``chain/strategies.py`` — حدود الحروف الثابتة حُذفت.
- الضبط من ``config.yaml`` قسم ``context_budget`` عبر ``from_config``
  (model_window / reserved_output / safety_margin / chunk_token_budget).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol, runtime_checkable

TIERS: tuple[str, ...] = ("must_have", "high", "normal", "opportunistic")
_TIER_RANK = {name: i for i, name in enumerate(TIERS)}

DEFAULT_SAFETY_MARGIN = 0.10   # بند مخاطر R-203: هامش 10% لعدم دقة المقدّر

# افتراضيات الضبط (T-024) — تُقرأ من config.yaml قسم context_budget إن وُجد
DEFAULT_MODEL_WINDOW = 128_000
DEFAULT_RESERVED_OUTPUT = 8_000


# ═══════════════════════════ تقدير التوكنز ═══════════════════════════

@runtime_checkable
class TokenEstimator(Protocol):
    """مقدّر توكنز قابل للاستبدال — tokenizer المزود أو تقريب chars/4."""

    def estimate(self, text: str) -> int:
        """عدد التوكنز التقديري لنص — يجب ألا يقل عن 1 لنص غير فارغ."""
        ...


class CharsPerTokenEstimator:
    """التقريب الافتراضي: حرف÷4 ≈ توكن (نفس تخمين legacy لكن مركزيًا)."""

    def __init__(self, chars_per_token: int = 4) -> None:
        self._cpt = max(1, chars_per_token)

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // self._cpt)


# ═══════════════════════════ نموذج البيانات ═══════════════════════════

@dataclass(frozen=True)
class BudgetItem:
    """عنصر مرشّح للبرومبت — نص + طبقة أهمية.

    ``key`` معرّف ثابت (مسار/step id) يظهر في تقرير ``dropped[]``.
    """
    key: str
    text: str
    tier: str = "normal"

    def __post_init__(self) -> None:
        if self.tier not in _TIER_RANK:
            raise ValueError(
                f"tier غير معروف: {self.tier!r} — المسموح: {TIERS}")


@dataclass(frozen=True)
class DroppedItem:
    """سجل إسقاط واحد — للـ logs/UI (قرار مرصود لا تدهور صامت)."""
    key: str
    tier: str
    tokens: int
    reason: str


@dataclass
class PackResult:
    """نتيجة الحزم: ما بقي، ما سقط، والمحاسبة.

    ``overflowed=True`` = الـ must_have وحدها تجاوزت الميزانية حتى بعد
    خطاف التلخيص — احتُفظ بها (لا تُسقط أبدًا) لكن الفيض **مرصود**.
    """
    kept: list[BudgetItem] = field(default_factory=list)
    dropped: list[DroppedItem] = field(default_factory=list)
    total_tokens: int = 0
    budget_tokens: int = 0
    overflowed: bool = False

    def to_dict(self) -> dict:
        """ملخص JSON-serializable للـ logging."""
        return {
            "kept": [it.key for it in self.kept],
            "dropped": [
                {"key": d.key, "tier": d.tier,
                 "tokens": d.tokens, "reason": d.reason}
                for d in self.dropped
            ],
            "total_tokens": self.total_tokens,
            "budget_tokens": self.budget_tokens,
            "overflowed": self.overflowed,
        }


# خطاف التلخيص: (item, target_tokens) → نص ملخّص أو None (تعذّر التلخيص)
SummarizeHook = Callable[[BudgetItem, int], "str | None"]


# ═══════════════════════════ الميزانية ═══════════════════════════

class ContextBudget:
    """قبول مرتّب بالأهمية داخل نافذة الموديل.

    الاستخدام:
        budget = ContextBudget(model_window=128_000, reserved_output=4_000)
        result = budget.pack([
            BudgetItem("user_request", text, tier="must_have"),
            BudgetItem("src/app.py", body, tier="high"),
            BudgetItem("README.md", readme, tier="opportunistic"),
        ])
        prompt_parts = [it.text for it in result.kept]
        if result.dropped:
            log.info("context dropped: %s", result.to_dict()["dropped"])
    """

    def __init__(self, model_window: int, reserved_output: int = 0,
                 estimator: TokenEstimator | None = None,
                 safety_margin: float = DEFAULT_SAFETY_MARGIN,
                 summarize_hook: SummarizeHook | None = None) -> None:
        if model_window <= 0:
            raise ValueError("model_window يجب أن يكون موجبًا")
        if reserved_output < 0 or reserved_output >= model_window:
            raise ValueError("reserved_output خارج النطاق")
        if not (0.0 <= safety_margin < 1.0):
            raise ValueError("safety_margin يجب أن يكون في [0, 1)")
        self.model_window = model_window
        self.reserved_output = reserved_output
        self.safety_margin = safety_margin
        self.estimator: TokenEstimator = estimator or CharsPerTokenEstimator()
        self.summarize_hook = summarize_hook

    @classmethod
    def from_config(cls, cfg: dict | None = None, *,
                    estimator: TokenEstimator | None = None,
                    summarize_hook: SummarizeHook | None = None,
                    ) -> "ContextBudget":
        """بناء ميزانية من dict الضبط (config.yaml) — T-024.

        يقرأ ``cfg["context_budget"]``: ``model_window`` /
        ``reserved_output`` / ``safety_margin``. أي مفتاح غائب (أو
        ``cfg=None``) يسقط على الافتراضيات المركزية أعلاه.
        """
        section = (cfg or {}).get("context_budget") or {}
        return cls(
            model_window=int(section.get("model_window",
                                         DEFAULT_MODEL_WINDOW)),
            reserved_output=int(section.get("reserved_output",
                                            DEFAULT_RESERVED_OUTPUT)),
            safety_margin=float(section.get("safety_margin",
                                            DEFAULT_SAFETY_MARGIN)),
            estimator=estimator,
            summarize_hook=summarize_hook,
        )

    @property
    def budget_tokens(self) -> int:
        """التوكنز المتاحة للسياق بعد حجز المخرجات وهامش الأمان."""
        usable = self.model_window - self.reserved_output
        return max(0, int(usable * (1.0 - self.safety_margin)))

    # ── الحزم ──

    def pack(self, items: Iterable[BudgetItem]) -> PackResult:
        """حزم العناصر داخل الميزانية — حتمي بالكامل.

        الخوارزمية:
        1. تقدير توكنز كل عنصر (مقدّر واحد مشترك).
        2. القبول الكامل ثم الإسقاط من الطبقة الأدنى أولًا
           (opportunistic → normal → high)؛ داخل الطبقة الأكبر أولًا،
           والتعادل → الأحدث إدخالًا أولًا.
        3. ``must_have`` لا تُسقط أبدًا: عند الفيض بعد إفراغ كل ما دونها
           يُستدعى خطاف التلخيص لكل عنصر (الأكبر أولًا)؛ إن بقي فيض
           يُحتفظ بها ويُعلَّم ``overflowed=True`` (مرصود لا صامت).
        """
        entries: list[tuple[int, BudgetItem, int]] = []   # (idx, item, tokens)
        for idx, item in enumerate(items):
            entries.append((idx, item, self.estimator.estimate(item.text)))

        limit = self.budget_tokens
        total = sum(t for _, _, t in entries)
        dropped: list[DroppedItem] = []
        kept: dict[int, tuple[BudgetItem, int]] = {
            idx: (item, tokens) for idx, item, tokens in entries
        }

        # ── مرحلة الإسقاط: الطبقات الدنيا من الأسفل للأعلى ──
        for tier in reversed(TIERS[1:]):        # opportunistic → normal → high
            if total <= limit:
                break
            # مرشحو هذه الطبقة: الأكبر أولًا، التعادل → الأحدث إدخالًا أولًا
            candidates = sorted(
                (idx for idx, (it, _) in kept.items() if it.tier == tier),
                key=lambda i: (-kept[i][1], -i),
            )
            for idx in candidates:
                if total <= limit:
                    break
                item, tokens = kept.pop(idx)
                total -= tokens
                dropped.append(DroppedItem(
                    key=item.key, tier=item.tier, tokens=tokens,
                    reason="budget: dropped lowest tier, largest first",
                ))

        # ── فيض الـ must_have: خطاف التلخيص لكل عنصر ──
        overflowed = False
        if total > limit:
            over = total - limit
            mh_indices = sorted(
                (idx for idx, (it, _) in kept.items()
                 if it.tier == "must_have"),
                key=lambda i: (-kept[i][1], -i),
            )
            for idx in mh_indices:
                if total <= limit:
                    break
                item, tokens = kept[idx]
                if self.summarize_hook is None:
                    continue
                # الهدف: حجم العنصر مطروحًا منه الفيض المتبقي (بحد أدنى 1)
                target = max(1, tokens - (total - limit))
                summary = self.summarize_hook(item, target)
                if summary is None:
                    continue
                new_tokens = self.estimator.estimate(summary)
                if new_tokens >= tokens:
                    continue   # التلخيص لم يوفّر شيئًا — تجاهله
                kept[idx] = (
                    BudgetItem(key=item.key, text=summary, tier=item.tier),
                    new_tokens,
                )
                total -= (tokens - new_tokens)
            if total > limit:
                overflowed = True   # نحتفظ بالـ must_have — الفيض مرصود

        ordered = [kept[idx][0] for idx in sorted(kept.keys())]
        return PackResult(
            kept=ordered,
            dropped=dropped,
            total_tokens=total,
            budget_tokens=limit,
            overflowed=overflowed,
        )
