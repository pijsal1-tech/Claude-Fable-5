# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  🧠 KnowledgeAccumulator — ذاكرة تراكمية للـ Agent

  تجمع كل المعلومات المكتشفة أثناء agent loop.
  لا تضيع عند تبديل الحساب أو إعادة المحاولة.

  T-043 (R-503): المخازن الخام (_files_read/_dirs_listed/...)
  حُذفت — الذاكرة الآن **view فوق ContextBundle**:
  - كل نتيجة أداة تُسجّل عنصرًا في الحزمة (hash-dedup عند
    الإدراج: نفس الجسد لمسار آخر = reference؛ إعادة قراءة
    نفس المسار بنفس المحتوى = لا إدخال جديد إطلاقًا).
  - ``build_iteration_context`` (الجديدة): برومبت كل iteration
    يحمل **delta** — العناصر غير المرسلة verbatim، وما سبق
    إرساله سطر إحالة واحد مضغوط (`path (hash…)`) — مع أرضية
    recent-k: آخر k عناصر دائمًا verbatim.
  - ``build_context`` باقية كعرض كامل **بلا حالة إرسال**
    (initial لأول مرة، وعرض النتائج للمستخدم في الـ fallback)
    — نفس شكل الأقسام القديم حرفيًا.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any

from context.bundle import BundleEntry, ContextBundle, ContextItem, content_hash


@dataclass
class ToolResult:
    """نتيجة أداة واحدة"""
    tool: str                    # اسم الأداة (read_file, list_dir, ...)
    args: dict                   # المعاملات
    result: str                  # الناتج (نص)
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    iteration: int = 0          # في أي iteration تمت

    def to_summary(self, max_len: int = 500) -> str:
        """ملخص مختصر — يُستخدم في prompt"""
        preview = self.result[:max_len]
        if len(self.result) > max_len:
            preview += f"\n... ({len(self.result) - max_len} حرف إضافي)"

        status = "✅" if self.success else "❌"
        args_str = ", ".join(f"{k}={v!r}" for k, v in self.args.items())
        return f"{status} {self.tool}({args_str}):\n{preview}"

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "args": self.args,
            "result": self.result[:1000],
            "success": self.success,
            "iteration": self.iteration,
        }


# ── تصنيف أداة → source_kind في الحزمة ──
# (auto_* هي نتائج الـ prefetch — كانت لا تُصنّف قديمًا فلا تظهر
#  في السياق إطلاقًا؛ الآن تسجَّل كغيرها — إصلاح ضمن R-503.)
_TOOL_KIND = {
    "read_file": "file", "auto_file": "file",
    "auto_tree": "file", "auto_deps": "file", "auto_info": "file",
    "list_dir": "dir", "auto_dir": "dir",
    "search_code": "search", "auto_search": "search",
    "run_command": "command",
}

# أرضية الحداثة: آخر كم عنصر يُعرض verbatim دائمًا ولو سبق إرساله
RECENT_K_DEFAULT = 3


class KnowledgeAccumulator:
    """
    ذاكرة تراكمية — view فوق ContextBundle (T-043 / R-503).

    المعرفة لا تُفقد عند:
    - تبديل الحساب (account switch)
    - إعادة المحاولة (retry)
    - انتهاء الـ iteration

    وتكلفة كل iteration مسطّحة: ما أُرسل مرة لا يُعاد حقنه —
    يُشار إليه بسطر واحد (``build_iteration_context``).
    """

    def __init__(self) -> None:
        self._bundle = ContextBundle()
        # meta جانبية للعرض فقط (success/query/العرض الأصلي للمسار)
        # — الجسد نفسه ملك الحزمة، لا مخزن خام موازٍ.
        self._meta: dict[tuple[str, str], dict[str, Any]] = {}
        # آخر hash معروف لكل مفتاح هوية أساسي — لكشف إعادة القراءة
        # بنفس المحتوى (تُبتلع) أو بمحتوى جديد (تُسجّل نسخة محدثة)
        self._last_hash: dict[tuple[str, str], str] = {}
        # عدد النسخ المحدثة لكل مفتاح أساسي (لتوليد مفتاح هوية فريد)
        self._revisions: dict[tuple[str, str], int] = {}
        # ما أُرسل فعلًا للموديل (مفاتيح BudgetItem التي نجت من الحزم)
        self._sent_keys: set[str] = set()

        self._tool_results: list[ToolResult] = []
        self._observations: list[str] = []          # ملاحظات AI
        self._errors: list[str] = []                # أخطاء حصلت
        self._iteration: int = 0

    # ──── إضافة معرفة ────

    def add_tool_result(self, tool: str, args: dict, result: str,
                        success: bool = True) -> ToolResult:
        """إضافة نتيجة أداة — تسجَّل في الحزمة (hash-dedup عند الإدراج)."""
        tr = ToolResult(
            tool=tool,
            args=args,
            result=result,
            success=success,
            iteration=self._iteration,
        )
        self._tool_results.append(tr)

        kind = _TOOL_KIND.get(tool)
        if kind is None or not success and kind != "command":
            # أداة غير مصنفة أو فشل غير-أمري: تبقى في سجل الأدوات فقط
            # (الفشل يصل للموديل عبر add_error/ملاحظات الحلقة)
            return tr

        display = str(
            args.get("path")
            or args.get("query")
            or args.get("command")
            or args.get("source")
            or tool
        )
        base_key = (kind, display)
        h = content_hash(result)

        if self._last_hash.get(base_key) == h:
            # إعادة قراءة بنفس المحتوى — dedup كامل، لا إدخال جديد
            return tr

        path = display
        if base_key in self._last_hash:
            # نفس الهوية بمحتوى جديد (ملف عُدّل ثم أُعيدت قراءته):
            # نسخة محدثة بمفتاح هوية فريد — الجسد الجديد يُعرض
            self._revisions[base_key] = self._revisions.get(base_key, 0) + 1
            path = f"{display}@r{self._revisions[base_key]}"
        self._last_hash[base_key] = h

        item = ContextItem(source_kind=kind, path=path, content=result)
        self._bundle.add(item)
        self._meta[item.key] = {
            "display": display,
            "success": success,
            "iteration": self._iteration,
        }
        return tr

    def add_observation(self, text: str):
        """إضافة ملاحظة من AI (مثل: 'الملف يستخدم React hooks')"""
        self._observations.append(text)

    def add_error(self, text: str):
        """تسجيل خطأ"""
        self._errors.append(text)

    def next_iteration(self):
        """انتقال لـ iteration جديدة"""
        self._iteration += 1

    # ──── بناء سياق للـ prompt ────

    def _body_entries(self) -> list[BundleEntry]:
        """عناصر الحزمة الحاملة لجسد (غير الإحالات) بترتيب الإدراج."""
        return [e for e in self._bundle.entries
                if e.item.content is not None and not e.is_reference]

    def _ref_entries(self) -> list[BundleEntry]:
        """عناصر جسدها مكرر لعنصر سابق (hash-dedup عند الإدراج)."""
        return [e for e in self._bundle.entries if e.is_reference]

    @staticmethod
    def _section_header(kind: str) -> str:
        return {
            "file": "📂 [ملفات تم قراءتها]:\n",
            "dir": "📁 [مجلدات تم استعراضها]:\n",
            "search": "🔍 [نتائج بحث]:\n",
            "command": "⚡ [أوامر تم تنفيذها]:\n",
        }[kind]

    def _render_body(self, e: BundleEntry) -> str:
        """جسد عنصر واحد — بنفس أشكال الأقسام القديمة حرفيًا."""
        meta = self._meta.get(e.item.key, {})
        display = meta.get("display", e.item.path)
        content = e.item.content or ""
        kind = e.item.source_kind
        if kind == "file":
            return f"\n--- {display} ---\n{content}\n"
        if kind == "dir":
            return f"\n{display}/:\n{content}\n"
        if kind == "search":
            return f"\nبحث: {display}\n{content}\n"
        status = "✅" if meta.get("success", True) else "❌"
        return f"\n{status} $ {display}\n{content}\n"

    def _stable_core_items(self) -> list:
        """الملاحظات والأخطاء — صغيرة وحاسمة، تُرفق في كل إرسال."""
        from context.budget import BudgetItem
        items = []
        if self._observations:
            # T-030 (R-302): القصّة الحرفية [-10:] → سياسة نافذة مسماة
            from sessions.memory import (
                POLICY_KNOWLEDGE_OBSERVATIONS, select_history)
            sec = "💡 [ملاحظات سابقة]:\n"
            for obs in select_history(self._observations,
                                      POLICY_KNOWLEDGE_OBSERVATIONS):
                sec += f"- {obs}\n"
            items.append(BudgetItem(key="observations", text=sec, tier="high"))
        if self._errors:
            sec = "⚠️ [أخطاء]:\n"
            for err in self._errors[-5:]:
                sec += f"- {err}\n"
            items.append(BudgetItem(key="errors", text=sec, tier="high"))
        return items

    def build_context(self, max_tokens: int = 8000) -> str:
        """
        عرض كامل **بلا حالة إرسال** — للإرسال الأول وللعرض النهائي
        للمستخدم. نفس أقسام T-024 (حزم بالتوكنز، لا قصّ في المنتصف)،
        مصدرها الآن الحزمة: الجسد المكرر (hash) يظهر إحالة لا نسخة.
        """
        if not self.has_knowledge:
            return ""
        from context.budget import BudgetItem, ContextBudget

        candidates: list[BudgetItem] = []   # (بترتيب الإدراج = ترتيب العرض)
        bodies = self._body_entries()

        # ── ملفات مقروءة ── (كل ملف عنصر مستقل — يُسقط الأكبر أولًا لو لزم)
        files = [e for e in bodies if e.item.source_kind == "file"]
        if files:
            candidates.append(BudgetItem(
                key="files:header", text=self._section_header("file"),
                tier="high"))
            for e in files:
                candidates.append(BudgetItem(
                    key=f"file:{e.item.path}",
                    text=self._render_body(e),
                    tier="high"))

        # ── مجلدات ──
        dirs = [e for e in bodies if e.item.source_kind == "dir"]
        if dirs:
            sec = self._section_header("dir")
            for e in dirs:
                sec += self._render_body(e)
            candidates.append(BudgetItem(key="dirs", text=sec, tier="normal"))

        # ── نتائج بحث ── (آخر 5 — كما كان)
        searches = [e for e in bodies if e.item.source_kind == "search"]
        if searches:
            sec = self._section_header("search")
            for e in searches[-5:]:
                sec += self._render_body(e)
            candidates.append(BudgetItem(key="searches", text=sec,
                                         tier="normal"))

        # ── أوامر نُفذت ──
        commands = [e for e in bodies if e.item.source_kind == "command"]
        if commands:
            sec = self._section_header("command")
            for e in commands:
                sec += self._render_body(e)
            candidates.append(BudgetItem(key="commands", text=sec,
                                         tier="normal"))

        # ── أجساد مكررة (hash-dedup) — إحالة سطرية ──
        refs = self._ref_entries()
        if refs:
            lines = "\n".join(
                f"- {self._meta.get(e.item.key, {}).get('display', e.item.path)} "
                f"— محتواه مطابق لـ {e.duplicate_of} أعلاه، لم يُكرَّر."
                for e in refs
            )
            candidates.append(BudgetItem(
                key="dup-refs", text=f"📎 [مكرر المحتوى]:\n{lines}\n",
                tier="normal"))

        candidates.extend(self._stable_core_items())

        budget = ContextBudget(model_window=max_tokens, reserved_output=0)
        packed = budget.pack(candidates)
        context = "\n".join(it.text for it in packed.kept)
        if packed.dropped:
            context += (f"\n... (أُسقط {len(packed.dropped)} قسم معرفة — "
                        f"ميزانية التوكنز: {packed.budget_tokens})")
        return context

    def build_iteration_context(self, max_tokens: int = 6000,
                                recent_k: int = RECENT_K_DEFAULT) -> str:
        """
        سياق iteration بصيغة **delta** (T-043 / R-503):

        - عنصر لم يُرسل بعد ⇒ جسده كاملًا (verbatim).
        - آخر ``recent_k`` عناصر ⇒ verbatim دائمًا (أرضية الحداثة —
          حماية من فقدان الموديل لخيط المحتوى المُحال).
        - عنصر سبق إرساله (وليس حديثًا) ⇒ سطر إحالة مضغوط واحد:
          ``path (hash8)`` — تكلفته توكنات معدودة لا جسد كامل.
        - النواة الثابتة (ملاحظات/أخطاء) تُرفق دائمًا — صغيرة وحاسمة.

        ما نجا من الحزم فقط يُعلَّم كمُرسل — عنصر أسقطته الميزانية
        يُعاد عرضه كاملًا في الجولة التالية.
        """
        if not self.has_knowledge:
            return ""
        from context.budget import BudgetItem, ContextBudget

        bodies = self._body_entries()
        recent_cutoff = max(0, len(bodies) - max(recent_k, 0))

        candidates: list[BudgetItem] = []
        verbatim_keys: list[str] = []
        ref_lines: list[str] = []

        for idx, e in enumerate(bodies):
            key = f"{e.item.source_kind}:{e.item.path}"
            display = self._meta.get(e.item.key, {}).get("display",
                                                         e.item.path)
            if key in self._sent_keys and idx < recent_cutoff:
                # سبق إرساله وليس حديثًا — إحالة سطرية
                ref_lines.append(f"{display} ({(e.content_hash or '')[:8]})")
                continue
            header = self._section_header(e.item.source_kind)
            candidates.append(BudgetItem(
                key=key,
                text=f"{header}{self._render_body(e)}",
                tier="high" if e.item.source_kind == "file" else "normal",
            ))
            verbatim_keys.append(key)

        # أجساد مكررة hash-dedup — إحالة دائمًا (جسدها عند عنصر آخر)
        for e in self._ref_entries():
            display = self._meta.get(e.item.key, {}).get("display",
                                                         e.item.path)
            ref_lines.append(f"{display} (مطابق لـ {e.duplicate_of})")

        if ref_lines:
            candidates.append(BudgetItem(
                key="sent-refs",
                text=("📎 [سبق إرساله — متاح لديك من الجولات السابقة، "
                      "لم يُكرَّر]:\n" + "، ".join(ref_lines) + "\n"),
                tier="high",   # صغير — وتذكيره يمنع إعادة طلب الملفات
            ))

        candidates.extend(self._stable_core_items())

        budget = ContextBudget(model_window=max_tokens, reserved_output=0)
        packed = budget.pack(candidates)
        kept_keys = {it.key for it in packed.kept}
        # التعليم بعد النجاة فقط — المُسقط لم يصل للموديل
        self._sent_keys.update(k for k in verbatim_keys if k in kept_keys)

        context = "\n".join(it.text for it in packed.kept)
        if packed.dropped:
            context += (f"\n... (أُسقط {len(packed.dropped)} قسم معرفة — "
                        f"ميزانية التوكنز: {packed.budget_tokens})")
        return context

    # ──── معلومات ────

    @property
    def iteration(self) -> int:
        return self._iteration

    @property
    def total_results(self) -> int:
        return len(self._tool_results)

    @property
    def files_count(self) -> int:
        return len({self._meta.get(e.item.key, {}).get("display", e.item.path)
                    for e in self._bundle.entries
                    if e.item.source_kind == "file"})

    @property
    def has_knowledge(self) -> bool:
        return bool(len(self._bundle) or self._tool_results
                    or self._observations or self._errors)

    def _kind_count(self, kind: str) -> int:
        return len({self._meta.get(e.item.key, {}).get("display", e.item.path)
                    for e in self._bundle.entries
                    if e.item.source_kind == kind})

    def get_summary(self) -> dict:
        """ملخص لعرضه في الـ UI"""
        return {
            "iterations": self._iteration,
            "tools_used": self.total_results,
            "files_read": self.files_count,
            "dirs_listed": self._kind_count("dir"),
            "searches": self._kind_count("search"),
            "commands": self._kind_count("command"),
            "observations": len(self._observations),
            "errors": len(self._errors),
        }

    def clear(self):
        """مسح كل المعرفة (بداية جديدة)"""
        self._bundle = ContextBundle()
        self._meta.clear()
        self._last_hash.clear()
        self._revisions.clear()
        self._sent_keys.clear()
        self._tool_results.clear()
        self._observations.clear()
        self._errors.clear()
        self._iteration = 0
