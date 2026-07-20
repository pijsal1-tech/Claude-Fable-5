# -*- coding: utf-8 -*-
"""طبقات الذاكرة (R-802 / T-103): الطبقة الحلقية — ملخص لكل run.

═══════════════════════ نموذج الطبقات ═══════════════════════

R-802 يبني ثلاث طبقات فوق تيار JSONL نفسه:

  ┌─────────────────────────────────────────────────────────┐
  │ working   — نافذة R-302/R-304 القائمة (sessions/memory) │
  │             **مرجع لا نسخة**: هذه الوحدة لا تعيد بناءها │
  │             ولا تلمسها — ``ConversationMemory.window()`` │
  │             يبقى المصدر الوحيد للأدوار المتجهة للموديل. │
  ├─────────────────────────────────────────────────────────┤
  │ episodic  — **هذه الوحدة (T-103)**: سجل حلقة مضغوط لكل  │
  │             run (الهدف/النتيجة/الملفات/القرارات) يُلحق  │
  │             بـ ``session_<id>.episodes.jsonl`` بعد نهاية │
  │             الـ run — خارج المسار الساخن.               │
  ├─────────────────────────────────────────────────────────┤
  │ semantic  — T-104/T-105: فهرس embeddings فوق الأدوار +  │
  │             الحلقات؛ يفهرس **نفس أشكال السجلات** المعرفة│
  │             هنا (لهذا الحلقية أولًا — تحدد الشكل).       │
  └─────────────────────────────────────────────────────────┘

═══════════════════ مخطط سجل الحلقة (format=1) ═══════════════════

سطر JSON واحد في الـ sidecar (نفس ضمانات append-only للتيار الرئيسي —
الكتابة عبر ``SessionStore.append_episode`` حصريًا، لا قراءة/كتابة خام
هنا — حدود SafeReader على context/ تبقى نظيفة):

    {"kind": "episode", "format": 1,
     "run_id": str,           # معرّف الـ run — مفتاح الحلقة
     "goal": str,             # طلب المستخدم الذي أطلق الـ run
     "outcome": str,          # حالة الـ run النهائية (completed|failed|cancelled)
     "files_touched": [str],  # مسارات نسبية مسّها الـ run
     "key_decisions": [str],  # نقاط مضغوطة من نتائج الخطوات
     "started_at": str, "completed_at": str,   # ISO — من توقيت الـ run
     "ts": str}               # وقت كتابة الحلقة نفسها

سجل بـ ``kind`` مختلف أو format أحدث **يُتخطى بصمت** عند القراءة —
نفس فلسفة توافق T-029 (قارئ قديم لا ينفجر على أنواع مستقبلية).

═══════════════════ خطاف ما-بعد-الـ-run ═══════════════════

``EpisodicLayer.summarize_and_record(digest, summarizer=None)`` هو
الخطاف: يُستدعى بعد انتهاء الـ run (التوصيل بمسار الإنهاء مهمة لاحقة —
هذه الوحدة مستقلة كي تُختبر بلا bridge). المدخل ``RunDigest`` بيانات
خام صرفة — **بلا استيراد chain/** (chain يستورد context؛ الاستيراد
العكسي = دورة): مَن يملك ChainRun يبني الـ digest من حقوله.

**عقد التدهور (بند القبول):** فشل الملخِّص أو فشل الكتابة نفسها ⇒
لا-حلقة (``None``) والخطأ في ``last_error`` — **لا استثناء يتسرب
أبدًا**: الحلقات مشتقة اختيارية، وفقدان حلقة أرخص من إسقاط run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional, Sequence

from sessions.store import SessionStore

EPISODE_KIND = "episode"
EPISODE_FORMAT = 1

# حدود الملخِّص البدائي — حلقة "مضغوطة" فعلًا لا نسخة ثانية من النتائج
MAX_DECISIONS = 5
MAX_DECISION_CHARS = 160


def _now_iso() -> str:
    return datetime.now().isoformat()


# ═══════════════════ أشكال البيانات ═══════════════════

@dataclass(frozen=True)
class RunDigest:
    """المدخل الخام للتلخيص — يُبنى عند نهاية الـ run من حقوله.

    بيانات صرفة (نصوص وأزواج) كي تبقى الوحدة بلا أي استيراد من
    chain/؛ ``step_results`` أزواج ``(step_id, result_text)`` بترتيب
    التنفيذ.
    """
    run_id: str
    goal: str
    outcome: str
    files_touched: tuple[str, ...] = ()
    step_results: tuple[tuple[str, str], ...] = ()
    started_at: str = ""
    completed_at: str = ""


@dataclass(frozen=True)
class EpisodeRecord:
    """سجل حلقة واحد — انعكاس سطر الـ sidecar (المخطط برأس الوحدة)."""
    run_id: str
    goal: str
    outcome: str
    files_touched: tuple[str, ...] = ()
    key_decisions: tuple[str, ...] = ()
    started_at: str = ""
    completed_at: str = ""
    ts: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": EPISODE_KIND,
            "format": EPISODE_FORMAT,
            "run_id": self.run_id,
            "goal": self.goal,
            "outcome": self.outcome,
            "files_touched": list(self.files_touched),
            "key_decisions": list(self.key_decisions),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "ts": self.ts,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "EpisodeRecord":
        return cls(
            run_id=str(data.get("run_id", "")),
            goal=str(data.get("goal", "")),
            outcome=str(data.get("outcome", "")),
            files_touched=tuple(str(p) for p in
                                data.get("files_touched", []) or []),
            key_decisions=tuple(str(d) for d in
                                data.get("key_decisions", []) or []),
            started_at=str(data.get("started_at", "")),
            completed_at=str(data.get("completed_at", "")),
            ts=str(data.get("ts", "")),
        )


# ═══════════════════ الملخِّص ═══════════════════

# عقد الملخِّص: digest ⇒ نقاط قرار. أي استثناء منه = تدهور لا-حلقة.
Summarizer = Callable[[RunDigest], Sequence[str]]


def heuristic_key_decisions(digest: RunDigest) -> list[str]:
    """الملخِّص الافتراضي — حتمي بلا موديل ولا شبكة.

    أول سطر غير فارغ من نتيجة كل خطوة، موسومًا بمعرّفها، مبتورًا عند
    ``MAX_DECISION_CHARS``، بحد أقصى ``MAX_DECISIONS`` نقاط. ملخِّص
    provider-backed يُوصَل لاحقًا عبر نفس العقد (``Summarizer``).
    """
    decisions: list[str] = []
    for step_id, result in digest.step_results:
        for line in result.splitlines():
            stripped = line.strip()
            if stripped:
                point = f"[{step_id}] {stripped}"
                if len(point) > MAX_DECISION_CHARS:
                    point = point[:MAX_DECISION_CHARS - 1] + "…"
                decisions.append(point)
                break
        if len(decisions) >= MAX_DECISIONS:
            break
    return decisions


# ═══════════════════ الطبقة الحلقية ═══════════════════

@dataclass
class EpisodicLayer:
    """قراءة/كتابة حلقات جلسة واحدة فوق ``SessionStore`` (T-103).

    الطبقة لا تملك ملفات: كل الثبات عبر ``append_episode`` /
    ``replay_episodes`` في المخزن (sidecar ملحق-فقط بنفس ضمانات
    التعافي من التمزّق). ``last_error`` يحمل آخر فشل تدهور —
    للتشخيص، ليس تدفق تحكم.
    """
    store: SessionStore
    session_id: str
    last_error: Optional[str] = field(default=None, init=False)

    # ── الكتابة (خطاف ما-بعد-الـ-run) ──

    def summarize_and_record(
        self, digest: RunDigest,
        summarizer: Optional[Summarizer] = None,
    ) -> Optional[EpisodeRecord]:
        """تلخيص run منتهٍ وإلحاق حلقته — **لا يرفع استثناء أبدًا**.

        أي فشل (الملخِّص، بناء السجل، الكتابة للقرص) ⇒ ``None`` مع
        ``last_error`` — الـ run لا يتأثر (بند قبول T-103).
        """
        try:
            fn: Summarizer = (summarizer if summarizer is not None
                              else heuristic_key_decisions)
            decisions = tuple(str(d) for d in fn(digest))
            episode = EpisodeRecord(
                run_id=digest.run_id,
                goal=digest.goal,
                outcome=digest.outcome,
                files_touched=digest.files_touched,
                key_decisions=decisions,
                started_at=digest.started_at,
                completed_at=digest.completed_at,
                ts=_now_iso(),
            )
            self.store.append_episode(self.session_id, episode.to_json())
        except Exception as exc:   # noqa: BLE001 — عقد التدهور الصريح
            self.last_error = f"{type(exc).__name__}: {exc}"
            return None
        self.last_error = None
        return episode

    # ── القراءة ──

    def episodes(self) -> list[EpisodeRecord]:
        """كل الحلقات بترتيب الكتابة.

        سجلات بـ ``kind`` غير حلقي أو ``format`` أحدث تُتخطى (توافق
        أمامي — نفس فلسفة T-029). sidecar غائب = قائمة فارغة.
        """
        result = self.store.replay_episodes(self.session_id)
        episodes: list[EpisodeRecord] = []
        for rec in result.records:
            if rec.get("kind") != EPISODE_KIND:
                continue
            if int(rec.get("format", 0)) > EPISODE_FORMAT:
                continue
            episodes.append(EpisodeRecord.from_json(rec))
        return episodes

    def episodes_for_run(self, run_id: str) -> list[EpisodeRecord]:
        """حلقات run بعينه (الاستعلام بالمهمة — روح R-802 episodic)."""
        return [e for e in self.episodes() if e.run_id == run_id]
