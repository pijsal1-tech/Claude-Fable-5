# -*- coding: utf-8 -*-
"""ConversationMemory (R-302 / T-029): المالك الواحد للوصول إلى التاريخ.

المشكلة: "أي تاريخ يراه الموديل" يُقرَّر ad-hoc عند كل موقع نداء —
معالج WS يقصّ ``[-10:]``، والـ delegate يقصّ ``[-6:]``، والقوالب تحقن
القائمة كاملة. لا مكوّن يملك دلالات ذاكرة المحادثة.

هنا: كل تاريخ متجه للموديل يمر من ``window(policy)`` — سياسة واحدة
مسماة قابلة للضبط بدل ثلاث قصّات متناثرة (توصيل المستهلكين = T-030).

═══════════════════════ وثيقة الـ API ═══════════════════════

**البنية:** ``ConversationMemory(store, session_id, estimator=None)``
فوق ``SessionStore`` (سجل JSONL ملحق-فقط من T-027) — الذاكرة لا تملك
ملفات ولا تخزينًا خاصًا؛ السجل هو مصدر الحقيقة الوحيد، وكل حالة
(بما فيها التثبيت) مشتقة منه بإعادة التشغيل.

**التسجيل:**

- ``append(role, content, visibility="user", **extra) -> int``
  يلحق دورًا ويعيد ``turn_id`` (فهرس تسلسلي ثابت داخل الجلسة).
  ``visibility="agent"`` يوسم أدوار الأدوات (روح R-302: الـ agent يسجل
  في نفس التيار) — تُستبعد من النوافذ الافتراضية وتبقى قابلة للتشغيل.
  ``**extra`` حقول إضافية تُحفظ حرفيًا في السجل (توسعة R-802).

- ``pin(turn_id)`` / ``unpin(turn_id)``
  تثبيت دور ليقفز فوق أي تقليم نافذة (تعليمات يجب ألا تسقط).
  يُسجَّل كسجل علامة ملحق (``kind="pin"``) — لا تعديل في مكانه أبدًا؛
  حالة التثبيت الفعالة = آخر علامة لكل ``turn_id`` عند إعادة التشغيل.

**القراءة:**

- ``window(policy) -> list[Turn]``
  الأدوار المتجهة للموديل وفق سياسة مسماة، **بترتيب السجل دائمًا**:
  1. فلترة الرؤية (``include_agent``).
  2. الأدوار المثبتة تدخل النافذة أولًا (تنجو من أي تقليم).
  3. ``last_n``: آخر N أدوار غير مثبتة.
  4. ``token_budget``: من الأحدث للأقدم، الدور يدخل كاملًا أو يسقط
     كاملًا (whole-or-drop — نفس مبدأ R-203، وبنفس المقدّر المركزي
     ``CharsPerTokenEstimator``؛ المثبتة تُخصم أولًا).

- ``WindowPolicy(last_n=None, token_budget=None, include_agent=False)``
  سياسات جاهزة تطابق قصّات legacy الثلاث. **خريطة T-030 النهائية**
  (المواقع الفعلية حُدِّدت أثناء الترحيل — التخمين الأولي في T-029
  كان معكوسًا):

  =====================  ==========  =========================================
  السياسة                القيمة       الموقع الفعلي (قبل T-030)
  =====================  ==========  =========================================
  ``POLICY_FULL``        الكل         ``chain/delegate.py::_to_prompt_history``
  ``POLICY_CHAT``        آخر 10       ``chain/knowledge.py`` (``_observations``)
  ``POLICY_DELEGATE``    آخر 6        طيّ الـ history في المزودين الثلاثة
                                      (alle_ai / deepseek / genspark)
  =====================  ==========  =========================================

  الأسماء الدقيقة متاحة كأسماء بديلة لنفس الكائنات:
  ``POLICY_DELEGATE_RENDER`` / ``POLICY_KNOWLEDGE_OBSERVATIONS`` /
  ``POLICY_PROVIDER_HISTORY_FOLD``.

- ``select_history(items, policy)`` (جسر T-030): تطبيق سياسة نافذة
  على قائمة في الذاكرة (رسائل أو نصوص) — للمستهلكين الذين ما زالوا
  يحملون قوائم خام قبل توصيل ``ConversationMemory`` الكامل (T-031+).
  ملاحظة نطاق: ``chat_history[:-1]`` في server.py هي استبعاد الرسالة
  الحالية المكررة (بنيوية)، ليست قصّة نافذة — خارج سياسات T-030.

**النافذة الطبقية (R-304 / T-032):**

- ``tiered_window(TieredPolicy) -> TieredWindow``
  نافذة تحت ``ContextBudget`` بثلاث طبقات — مخطط الطبقات::

      ┌──────────── token_budget ────────────┐
      │ 📌 المثبت — حرفي دائمًا (يُخصم لا يُقصى) │
      │ 📋 ملخص الشريحة الوسطى — موسوم كملخص  │
      │ 💬 الأدوار الحديثة حرفيًّا — شريط متصل من  │
      │    الأحدث، أرضية ``recent_floor`` لا تُنتهك │
      └───────────────────────────────────────┘
        أقدم … [مُلخَّص] [مقصوص إن لزم] [حديث حرفي] … أحدث

  الفروق عن ``window(token_budget)``: الشريط الحديث **متصل**
  (يتوقف عند أول دور لا يسع — لا فجوات أمام الملخص)، والأرضية
  تتفوق على الميزانية (بند مخاطر R-304: النافذة الحرفية لا
  تنكمش تحت الأرضية أبدًا). الملخص يدخل النافذة فقط إذا كان
  يغطي أدوارًا أُسقطت فعلًا (الجلسات القصيرة لا تتغير — رجعية).
  ``TieredWindow.degraded`` صادقة: أدوار أُسقطت بلا تغطية ملخص =
  قصّة صريحة (التدهور المنصوص).

- **الملخص artifact في التيار نفسه** (سجل ``kind="summary"`` بحقول
  ``text``/``covers_until``/``ts``) — السجل مصدر الحقيقة الوحيد
  (مبدأ T-029)، والملخصات قابلة للتدقيق في سجل الجلسة (منفعة
  R-304 المنصوصة). الملخص الفعال = آخر سجل ملخص عند التشغيل.
  ``covers_until`` حصري: يغطي الأدوار ``[0, covers_until)``.

- ``update_summary(summarizer, upto=None)`` النواة المتزامنة —
  تلخّص الشريحة الجديدة تراكميًّا (الملخص السابق يُمرر للـ
  summarizer) وتلحق الـ artifact. تفشل بصوت عالٍ (للمستدعي
  المباشر/الاختبارات).
- ``maybe_update_summary_async(summarizer, every_n=10)`` خطّاف المسار
  الساخن: إن نمت الشريحة غير المغطاة ≥ ``every_n`` دورًا يُطلق
  خيط خلفي ديمون ويعود فورًا — **لا ينتظر التلخيص أبدًا ولا
  يرفع استثناءً** (فشل الخيط يُسجّل في ``last_summary_error``
  والنافذة تتدهور لقصّة صريحة). طلب واحد في الرحلة (inflight
  dedup). ``wait_for_summary(timeout)`` للاختبارات والإغلاق النظيف.

**الأعقاب:**

- ``summary() -> str | None``: نص آخر ملخص مخزن أو ``None``
  (كان stub دائم-None قبل T-032).
- ``search(query, limit=5) -> list[Turn]``: تعيد ``[]`` دائمًا —
  R-802 يوصّل الاسترجاع الدلالي.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, TypeVar

from context.budget import CharsPerTokenEstimator, TokenEstimator
from sessions.store import SessionStore, _now_iso

_T = TypeVar("_T")

# أنواع السجلات في التيار — سجل بلا kind هو رسالة (توافق T-027/T-028)
_KIND_MESSAGE = "message"
_KIND_PIN = "pin"
_KIND_SUMMARY = "summary"   # R-304 (T-032): artifact ملخص في التيار

# وسم الملخص في الـ prompt — بند مخاطر R-304: الملخصات تُوسم
# كملخصات دائمًا (درء انجراف/هلوسة الملخص بالتصريح لا بالإخفاء).
SUMMARY_LABEL = "📋 [ملخص المحادثة الأقدم — مُولَّد آليًّا وقد يفوته تفصيل]"

# ملخّص: دالة (أدوار الشريحة الجديدة, نص الملخص السابق أو None)
# → نص الملخص الجديد المدمج. التراكم مسؤولية الملخّص نفسه.
Summarizer = Callable[[Sequence["Turn"], Optional[str]], str]


# ═══════════════════════ نموذج البيانات ═══════════════════════

@dataclass(frozen=True)
class Turn:
    """دور واحد في المحادثة كما تراه النوافذ."""
    turn_id: int          # فهرس تسلسلي ثابت داخل الجلسة (ترتيب السجل)
    role: str
    content: str
    ts: str = ""
    visibility: str = "user"    # "user" | "agent" (أدوار الأدوات)
    pinned: bool = False


@dataclass(frozen=True)
class WindowPolicy:
    """سياسة نافذة مسماة — القيم None = بلا حد من هذا النوع.

    ``last_n`` و``token_budget`` قابلان للتركيب: يُطبَّق ``last_n``
    أولًا ثم تُشذَّب النتيجة بالميزانية.
    """
    last_n: Optional[int] = None
    token_budget: Optional[int] = None
    include_agent: bool = False

    def __post_init__(self) -> None:
        if self.last_n is not None and self.last_n < 0:
            raise ValueError("last_n لا يكون سالبًا")
        if self.token_budget is not None and self.token_budget < 0:
            raise ValueError("token_budget لا يكون سالبًا")


# خريطة سياسات legacy (T-030 استبدل القصّات بهذه الأسماء):
POLICY_FULL = WindowPolicy()                    # القائمة كاملة
POLICY_CHAT = WindowPolicy(last_n=10)           # قصّة [-10:]
POLICY_DELEGATE = WindowPolicy(last_n=6)        # قصّة [-6:]

# T-030: الأسماء الدقيقة بعد تحديد المواقع الفعلية — نفس الكائنات؛
# أسماء T-029 أعلاه تبقى واجهة مثبتة (اختباراتها تعتمد عليها).
POLICY_DELEGATE_RENDER = POLICY_FULL            # delegate يرسل القائمة كما هي
POLICY_KNOWLEDGE_OBSERVATIONS = POLICY_CHAT     # [-10:] في chain/knowledge.py
POLICY_PROVIDER_HISTORY_FOLD = POLICY_DELEGATE  # [-6:] في المزودين الثلاثة


# ══════════════ النافذة الطبقية (R-304 / T-032) ══════════════

@dataclass(frozen=True)
class SummaryArtifact:
    """ملخص مخزن في تيار الجلسة — يغطي الأدوار ``[0, covers_until)``."""
    text: str
    covers_until: int
    ts: str = ""


@dataclass(frozen=True)
class TieredPolicy:
    """سياسة النافذة الطبقية — راجع مخطط الطبقات في docstring الوحدة.

    ``recent_floor``: أدنى عدد أدوار حديثة تدخل حرفيًّا مهما ضاقت
    الميزانية (النافذة الحرفية لا تنكمش تحت الأرضية — R-304).
    """
    token_budget: int
    recent_floor: int = 4
    include_agent: bool = False

    def __post_init__(self) -> None:
        if self.token_budget < 0:
            raise ValueError("token_budget لا يكون سالبًا")
        if self.recent_floor < 1:
            raise ValueError("recent_floor ≥ 1 — النافذة الحرفية لا تُعدَم")


@dataclass(frozen=True)
class TieredWindow:
    """ناتج ``tiered_window`` — ملخص (إن دخل) + أدوار حرفية بترتيب السجل.

    ``degraded``: أدوار أُسقطت دون أن يغطيها ملخص — قصّة صريحة
    (مسار التدهور المنصوص عند غياب/تأخر/فشل الملخّص).
    """
    summary: Optional[SummaryArtifact]
    turns: list[Turn]
    degraded: bool = False

    def summary_block(self) -> str:
        """كتلة الملخص الموسومة للـ prompt — "" إن لم يدخل ملخص."""
        if self.summary is None:
            return ""
        return f"{SUMMARY_LABEL}:\n{self.summary.text}"


def select_history(items: Sequence[_T], policy: WindowPolicy) -> list[_T]:
    """تطبيق سياسة نافذة على قائمة في الذاكرة (جسر T-030).

    المستهلكون القدامى يحملون قوائم خام (``list[Message]`` أو
    ``list[str]``) لا جلسات JSONL — هذه الدالة تعطيهم نفس دلالات
    ``last_n`` بسياسة مسماة بدل قصّة حرفية متناثرة. عندما يكتمل توصيل
    ``ConversationMemory`` في المستهلكين (T-031+) تُستبدل بـ
    ``memory.window(policy)`` نفسها.

    التكافؤ القيمي: ``select_history(xs, WindowPolicy(last_n=n))``
    ``== xs[-n:]`` حرفيًا (مثبت بالاختبارات) — و``last_n=None`` تعيد
    نسخة من القائمة كاملة.

    ``token_budget`` يتطلب أدوارًا كاملة بمحتوى — يُرفض هنا صراحة:
    استخدم ``ConversationMemory.window``.
    """
    if policy.token_budget is not None:
        raise ValueError(
            "token_budget يتطلب ConversationMemory.window — "
            "select_history تطبق last_n فقط")
    if policy.last_n is None:
        return list(items)
    if policy.last_n == 0:
        return []
    return list(items[-policy.last_n:])


# ═══════════════════════ الواجهة ═══════════════════════

class ConversationMemory:
    """المالك الواحد لدلالات ذاكرة المحادثة — راجع docstring الوحدة."""

    def __init__(self, store: SessionStore, session_id: str,
                 estimator: TokenEstimator | None = None) -> None:
        self._store = store
        self._session_id = session_id
        self._estimator = estimator or CharsPerTokenEstimator()
        # كاش عدّاد الأدوار — يُملأ كسولاً من السجل ثم يُزاد محليًّا،
        # فيبقى append بلا إعادة تشغيل للسجل (لا ننقض O(1) لـ T-027)
        self._turn_count: Optional[int] = None
        # R-304 (T-032): حالة الملخّص الخلفي — طلب واحد في الرحلة
        self._summary_lock = threading.Lock()
        self._summary_thread: Optional[threading.Thread] = None
        self.last_summary_error: Optional[BaseException] = None

    # ── التسجيل ──

    def append(self, role: str, content: str,
               visibility: str = "user", **extra: Any) -> int:
        """إلحاق دور — يعيد turn_id الثابت (فهرس السجل التسلسلي)."""
        if visibility not in ("user", "agent"):
            raise ValueError(f"visibility غير معروفة: {visibility!r}")
        turn_id = self._next_turn_id()
        record: dict[str, Any] = dict(extra)
        record.update({
            "kind": _KIND_MESSAGE,
            "role": role,
            "content": content,
            "visibility": visibility,
        })
        record.setdefault("ts", _now_iso())
        self._store.append_record(self._session_id, record)
        self._turn_count = turn_id + 1
        return turn_id

    def pin(self, turn_id: int) -> None:
        """تثبيت دور — علامة ملحقة، الحالة الفعالة تُشتق عند القراءة."""
        self._append_pin_marker(turn_id, pinned=True)

    def unpin(self, turn_id: int) -> None:
        self._append_pin_marker(turn_id, pinned=False)

    def _append_pin_marker(self, turn_id: int, pinned: bool) -> None:
        if turn_id < 0 or turn_id >= self._next_turn_id():
            raise ValueError(f"turn_id غير موجود: {turn_id}")
        self._store.append_record(self._session_id, {
            "kind": _KIND_PIN, "turn": turn_id, "pinned": pinned,
        })

    # ── القراءة ──

    def turns(self) -> list[Turn]:
        """كل الأدوار بترتيب السجل مع حالة تثبيت فعالة — بلا نافذة."""
        turns: list[Turn] = []
        pin_state: dict[int, bool] = {}
        for rec in self._store.replay(self._session_id).records:
            kind = rec.get("kind", _KIND_MESSAGE)
            if kind == _KIND_PIN:
                pin_state[int(rec.get("turn", -1))] = bool(
                    rec.get("pinned", True))
            elif kind == _KIND_MESSAGE:
                turns.append(Turn(
                    turn_id=len(turns),
                    role=str(rec.get("role", "")),
                    content=str(rec.get("content", "")),
                    ts=str(rec.get("ts", "")),
                    visibility=str(rec.get("visibility", "user")),
                ))
            # أنواع مستقبلية (R-802) تُتخطى بأمان
        if pin_state:
            turns = [
                Turn(t.turn_id, t.role, t.content, t.ts, t.visibility,
                     pinned=pin_state.get(t.turn_id, False))
                for t in turns
            ]
        return turns

    def window(self, policy: WindowPolicy = POLICY_FULL) -> list[Turn]:
        """الأدوار المتجهة للموديل وفق السياسة — بترتيب السجل دائمًا."""
        visible = [t for t in self.turns()
                   if policy.include_agent or t.visibility == "user"]

        pinned = [t for t in visible if t.pinned]
        unpinned = [t for t in visible if not t.pinned]

        # last_n على غير المثبت — المثبت ينجو خارج العدّ
        if policy.last_n is not None:
            unpinned = unpinned[len(unpinned) - min(
                policy.last_n, len(unpinned)):]

        selected = {t.turn_id for t in pinned} | {
            t.turn_id for t in unpinned}

        # token_budget: المثبت يُخصم أولًا، ثم من الأحدث للأقدم
        # whole-or-drop (مبدأ R-203، بالمقدّر المركزي نفسه)
        if policy.token_budget is not None:
            remaining = policy.token_budget
            kept: set[int] = set()
            for t in pinned:   # المثبت دائمًا داخل — يُخصم لا يُقصى
                remaining -= self._estimator.estimate(t.content)
                kept.add(t.turn_id)
            for t in reversed(unpinned):
                cost = self._estimator.estimate(t.content)
                if cost <= remaining:
                    remaining -= cost
                    kept.add(t.turn_id)
                # لا break: دور أقدم أصغر قد يسع الميزانية المتبقية —
                # لكن الترتيب النهائي ترتيب السجل، فلا خلط
            selected &= kept

        return [t for t in visible if t.turn_id in selected]

    # ── الأعقاب (واجهة مثبتة — تنفيذ لاحق) ──

    def summary(self) -> Optional[str]:
        """ملخص المحادثة — stub: لا تلخيص بعد (R-304 يوصّله)."""
        return None

    def search(self, query: str, limit: int = 5) -> list[Turn]:
        """استرجاع دلالي — stub: لا فهرس بعد (R-802 يوصّله)."""
        return []

    # ── داخلي ──

    def _next_turn_id(self) -> int:
        """turn_id التالي = عدد سجلات الرسائل — يُحسب مرة ثم يُكاش."""
        if self._turn_count is None:
            self._turn_count = sum(
                1 for rec in self._store.replay(self._session_id).records
                if rec.get("kind", _KIND_MESSAGE) == _KIND_MESSAGE)
        return self._turn_count
