# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  SmartOrchestrator — تصنيف المهمة + اختيار الاستراتيجية

  M3: SmartOrchestrator
  - complexity_score: حجم + عدد ملفات + علاقات + غموض + مخاطر
  - يختار: Direct / ContextWindow / ChunkChain / MapReduce / Pipeline
  - لا يعرف شيئاً عن الحسابات أو rate limits
═══════════════════════════════════════════════════════
"""
import re
import uuid
from dataclasses import dataclass, field
from typing import assert_never

from core.strategy import ExecutionStrategy
from context.bundle import ContextBundle, ContextItem

from .plugin_api import PluginContext
from .plugin_registry import StrategyPluginRegistry
from .strategies import (
    StrategyResult,
    build_direct,
    build_context_window,
    build_chunk_chain,
    build_map_reduce,
    build_pipeline,
)
from .models import ChainRun


# ═══════════════════════════════════════════════════════
#   Complexity Score
# ═══════════════════════════════════════════════════════

@dataclass
class ComplexityAnalysis:
    """نتيجة تحليل التعقيد"""
    size_score: float = 0.0          # حجم الملف/المشروع
    file_count_score: float = 0.0    # عدد الملفات
    cross_file_score: float = 0.0    # علاقات بين الملفات
    request_complexity: float = 0.0  # غموض الطلب
    risk_score: float = 0.0          # مخاطر (auth, DB, security)
    # T-036 (R-402): الإشارات المطابقة — أي أنماط أشعلت الدرجات
    # (للتفسير؛ **خارج to_dict عمدًا** — corpus T-034 يثبّت to_dict
    # بايت-بايت، والسجل ينقلها في RoutingRecord.matched_signals).
    matched_signals: dict[str, list[str]] = field(default_factory=dict)

    @property
    def total(self) -> float:
        return (self.size_score + self.file_count_score +
                self.cross_file_score + self.request_complexity +
                self.risk_score)

    @property
    def recommended(self) -> ExecutionStrategy:
        """T-035 (R-401): الاستراتيجية المقترحة — عضو enum لا نص حر."""
        score = self.total
        if score <= 2.0:
            return ExecutionStrategy.DIRECT
        elif score <= 4.0:
            # ملفات متعددة (4+) مع تعقيد متوسط → map_reduce أفضل من context_window
            if self.file_count_score >= 3.0:
                return ExecutionStrategy.MAP_REDUCE
            return ExecutionStrategy.CONTEXT_WINDOW
        elif score <= 7.0:
            # أي ملفات متعددة (2+) → map_reduce بدل chunk_chain
            if self.file_count_score >= 1.5:
                return ExecutionStrategy.MAP_REDUCE
            return ExecutionStrategy.CHUNK_CHAIN
        else:
            return ExecutionStrategy.PIPELINE

    @property
    def recommended_strategy(self) -> str:
        """مفردات السلك (to_dict / corpus T-034) — قيمة الـ enum نصًّا."""
        return self.recommended.value

    def to_dict(self) -> dict:
        return {
            "size_score": self.size_score,
            "file_count_score": self.file_count_score,
            "cross_file_score": self.cross_file_score,
            "request_complexity": self.request_complexity,
            "risk_score": self.risk_score,
            "total": self.total,
            "recommended_strategy": self.recommended_strategy,
        }


# ═══════════════════════════════════════════════════════
#   Risk Keywords
# ═══════════════════════════════════════════════════════

_HIGH_RISK_PATTERNS = [
    r"\bauth\b", r"\blogin\b", r"\bpassword\b", r"\btoken\b",
    r"\bsecur\w+\b", r"\bencrypt\w*\b", r"\bdecrypt\w*\b",
    r"\bpayment\b", r"\bcredit.card\b", r"\btransaction\b",
    r"\bdatabase\b", r"\bmigrat\w+\b", r"\bschema\b",
    r"\bdelete\b", r"\bdrop\b", r"\btruncate\b",
    r"\bdestructive\b", r"\birreversible\b",
    # Arabic
    r"حذف", r"مصادقة", r"أمان", r"تشفير", r"دفع", r"قاعدة.بيانات",
    # TSK-CEV-104 (F-015): مكافئات عربية شائعة كانت مفقودة —
    # «تسجيل الدخول» (مقابل login) و«كلمة السر/المرور» (مقابل password)
    r"تسجيل.{0,4}دخول", r"كلمة.{0,3}(?:ال)?(?:سر|مرور)",
]

_COMPLEX_REQUEST_PATTERNS = [
    r"refactor", r"rewrite", r"redesign", r"migrate",
    r"إعادة.*هيكلة", r"إعادة.*كتابة", r"نقل",
    # TSK-CEV-104 (F-015): الصيغ الفعلية المكافئة للمصادر أعلاه —
    # فعل الأمر «أعد/أعيدي/أعيدوا …» + المعرَّبة صوتيًا «ريفاكتور»
    # TSK-CEV-118 (F-017/FI-17, D-18): توسيع محور التصريف كاملًا —
    # حروف المضارعة [تني] («تعيد هيكلته»، «يعيد كتابة»، «نعيد تصميم»)
    # + جذور بلا تاء المصدر (هيكلته/كتابته) — النمط المُتحقَّق منه في
    # NEW_FINDINGS §CEV-F-017 (تحديث الاتساع). الواو لا تُضاف منفردة
    # (العطف «وتعيد» يلتقطه فرع التاء لأن re.search غير مُرسّى).
    r"[أاتني]ع(?:د|يد\w{0,2})\s*.{0,6}هيكل",
    r"[أاتني]ع(?:د|يد\w{0,2})\s*.{0,6}كتاب",
    r"[أاتني]ع(?:د|يد\w{0,2})\s*.{0,6}تصميم",
    r"ريفاكتور",
    r"architecture", r"هندسة.معمارية",
    r"across.*files", r"عبر.*ملفات", r"كل.*الملفات",
]


# ═══════════════════════════════════════════════════════
#   SmartOrchestrator
# ═══════════════════════════════════════════════════════

class SmartOrchestrator:
    """
    يحلل المهمة ويختار الاستراتيجية.

    لا يعرف شيئاً عن:
    - الحسابات
    - rate limits
    - Provider internals

    يعرف:
    - حجم الملفات/المشروع
    - عدد الملفات المتأثرة
    - تعقيد الطلب
    - المخاطر

    T-102 (R-801): يعرف أيضًا **سجل الإضافات** (اختياري):
    قبل الفصل على أعضاء ExecutionStrategy، إن طابق الطلبُ
    ``routing_hints`` لإضافة محمّلة (بعد المدمجين في الأولوية:
    force_strategy الصريح يتجاوز الإضافات دائمًا) تُبنى خطة الإضافة
    عبر ``PluginContext`` وتُنفَّذ بمسار Runner الطبيعي نفسه. أي
    استثناء من build() وقت التشغيل ⇒ سقوط آمن للاختيار المدمج —
    الإضافة لا تُسقط الطلب أبدًا.
    """

    # ── عتبات ──
    SMALL_FILE_LINES = 200
    MEDIUM_FILE_LINES = 1000
    LARGE_FILE_LINES = 4000
    TOKEN_BUDGET = 8000  # تقدير tokens لكل chunk

    def __init__(self,
                 plugin_registry: "StrategyPluginRegistry | None" = None
                 ) -> None:
        """plugin_registry: سجل T-100 بعد discover() — None = لا إضافات
        (السلوك الأساسي بايت-بايت، مثبت باختبار baseline)."""
        self._plugin_registry = plugin_registry

    # ═══════════════════════════════════════════════════
    #   T-102: ترشيح الإضافات (routing_hints)
    # ═══════════════════════════════════════════════════

    def _match_plugin(self, user_request: str,
                      total_complexity: float) -> tuple[str, type] | None:
        """أول إضافة محمّلة تطابق hints — (اسم، صنف) أو None.

        قواعد المطابقة (موثقة في examples/demo_strategy/README.md):
        - ``keywords``: أي كلمة تظهر في الطلب (بلا حساسية حالة).
        - ``max_complexity`` (اختياري): لا ترشيح فوقها.
        الترتيب حتمي: ترتيب أسماء السجل المفروز.
        """
        registry = self._plugin_registry
        if registry is None:
            return None
        for name in sorted(registry.loaded):
            cls = registry.loaded[name]
            hints = getattr(cls, "routing_hints", {}) or {}
            keywords = hints.get("keywords") or []
            if not any(str(kw).lower() in user_request.lower()
                       for kw in keywords):
                continue
            max_cx = hints.get("max_complexity")
            if max_cx is not None and total_complexity > float(max_cx):
                continue
            return name, cls
        return None

    def _build_via_plugin(self, name: str, cls: type, user_request: str,
                          files: dict[str, str] | None,
                          file_content: str | None,
                          file_path: str,
                          run_id: str = "",
                          metadata: dict | None = None
                          ) -> StrategyResult | None:
        """بناء خطة الإضافة عبر PluginContext — None عند أي فشل
        (سقوط آمن للاختيار المدمج؛ لا استثناء يتسرب للطلب).

        TSK-730b: run_id/metadata يصلان للإضافة عبر PluginContext —
        العقد (plugin_api) كان يكشفهما لكن هذا المسار الحقيقي كان
        يبنيهما فارغَين. emit تبقى noop وقت التخطيط (البناء متزامن
        قبل التشغيل — لا bus في الأوركستريتور بالتصميم)."""
        bundle = ContextBundle()
        if file_content:
            bundle.add(ContextItem("attachment", file_path or "attached",
                                   file_content))
        for fpath, fcontent in (files or {}).items():
            bundle.add(ContextItem("attachment", fpath, fcontent))
        ctx = PluginContext(user_request=user_request,
                            run_id=run_id,
                            _bundle=bundle,
                            _metadata=dict(metadata or {}))
        try:
            result = cls().build(ctx)
        except Exception:
            return None
        if not isinstance(result, StrategyResult) or not result.steps:
            return None
        return result

    def analyze_complexity(self, user_request: str,
                           files: dict[str, str] | None = None,
                           file_content: str | None = None,
                           file_path: str = "") -> ComplexityAnalysis:
        """
        يحلل تعقيد المهمة ويرجع complexity_score.

        files: {path: content} للمشاريع
        file_content: محتوى ملف واحد
        """
        analysis = ComplexityAnalysis()

        # ── 1. Size Score ──
        if file_content:
            lines = file_content.count("\n") + 1
            if lines <= self.SMALL_FILE_LINES:
                analysis.size_score = 0.5
            elif lines <= self.MEDIUM_FILE_LINES:
                analysis.size_score = 2.0
            elif lines <= self.LARGE_FILE_LINES:
                analysis.size_score = 4.0
            else:
                analysis.size_score = 6.0
        elif files:
            total_lines = sum(c.count("\n") + 1 for c in files.values())
            if total_lines <= 500:
                analysis.size_score = 1.0
            elif total_lines <= 2000:
                analysis.size_score = 3.0
            else:
                analysis.size_score = 5.0

        # ── 2. File Count Score ──
        if files:
            count = len(files)
            if count == 1:
                analysis.file_count_score = 0.0
            elif count <= 3:
                analysis.file_count_score = 1.5
            elif count <= 6:
                analysis.file_count_score = 3.0
            else:
                analysis.file_count_score = 4.0

        # ── 3. Cross-file Score ──
        if files and len(files) > 1:
            # Simple heuristic: count import/require references between files
            filenames = set()
            for path in files:
                name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                stem = name.rsplit(".", 1)[0]
                filenames.add(stem)

            cross_refs = 0
            for content in files.values():
                for stem in filenames:
                    if f"import {stem}" in content or f"from {stem}" in content:
                        cross_refs += 1
                    if f"require('{stem}" in content or f'require("{stem}' in content:
                        cross_refs += 1

            if cross_refs >= 4:
                analysis.cross_file_score = 2.0
            elif cross_refs >= 2:
                analysis.cross_file_score = 1.0

        # ── 4. Request Complexity ──
        request_lower = user_request.lower()
        # T-036: نلتقط الأنماط المطابقة نفسها (للتفسير) — العدّ لم يتغير
        complexity_matches = [
            p for p in _COMPLEX_REQUEST_PATTERNS
            if re.search(p, request_lower, re.IGNORECASE)
        ]
        complexity_hits = len(complexity_matches)
        if complexity_matches:
            analysis.matched_signals["request_complexity"] = complexity_matches
        if complexity_hits >= 3:
            analysis.request_complexity = 3.0
        elif complexity_hits >= 1:
            analysis.request_complexity = 1.5
        elif len(user_request) > 200:
            analysis.request_complexity = 1.0

        # ── 5. Risk Score ──
        risk_matches = [
            p for p in _HIGH_RISK_PATTERNS
            if re.search(p, request_lower, re.IGNORECASE)
        ]
        risk_hits = len(risk_matches)
        if risk_matches:
            analysis.matched_signals["risk"] = risk_matches
        # Also check file contents
        if file_content:
            risk_hits += sum(
                1 for p in _HIGH_RISK_PATTERNS
                if re.search(p, file_content[:5000], re.IGNORECASE)
            )
        if files:
            combined = " ".join(c[:2000] for c in files.values())
            risk_hits += sum(
                1 for p in _HIGH_RISK_PATTERNS
                if re.search(p, combined, re.IGNORECASE)
            )

        if risk_hits >= 4:
            analysis.risk_score = 3.0
        elif risk_hits >= 2:
            analysis.risk_score = 1.5
        elif risk_hits >= 1:
            analysis.risk_score = 0.5

        return analysis

    def select_strategy(self, user_request: str,
                        files: dict[str, str] | None = None,
                        file_content: str | None = None,
                        file_path: str = "",
                        force_strategy: str | None = None,
                        run_id: str = "") -> StrategyResult:
        """
        يحلل ويبني StrategyResult جاهزة.

        force_strategy: يفرض استراتيجية معينة (للتجاوز اليدوي).
        run_id (TSK-730b): يمرَّر للإضافات عبر PluginContext — "" (الافتراضي)
            لا يغيّر أي خطة مدمجة (goldens تثبته).
        """
        analysis = self.analyze_complexity(
            user_request, files, file_content, file_path
        )

        # T-035 (R-401): نقطة العبور الوحيدة نص→enum. النص المجهول
        # (ومنه "delegate" — غير موصول هنا؛ مساره DelegateBridge) يسقط
        # لـ direct — نفس سلوك else القديم، لكنه الآن **صريح** ومثبَّت
        # في corpus T-034 (orch_forced_delegate_falls_back_to_direct).
        strategy = (ExecutionStrategy.parse(force_strategy)
                    if force_strategy else analysis.recommended)

        # T-102 (R-801): ترشيح الإضافات — بعد المدمجين في الأولوية:
        # force_strategy الصريح يتجاوز الإضافات دائمًا (تجاوز يدوي =
        # قرار مستخدم)، وبدونه إضافة مطابقة الـ hints تفوز على التوصية
        # الآلية. فشل build() ⇒ سقوط آمن للمسار المدمج أدناه.
        if not force_strategy:
            matched = self._match_plugin(user_request, analysis.total)
            if matched is not None:
                plugin_name, plugin_cls = matched
                plugin_result = self._build_via_plugin(
                    plugin_name, plugin_cls, user_request,
                    files, file_content, file_path,
                    run_id=run_id,
                    metadata={"complexity": analysis.to_dict()})
                if plugin_result is not None:
                    plugin_result.metadata["complexity"] = analysis.to_dict()
                    plugin_result.metadata["plugin_name"] = plugin_name
                    return plugin_result

        if strategy is None or strategy is ExecutionStrategy.DELEGATE:
            result = build_direct(user_request)

        elif strategy is ExecutionStrategy.DIRECT:
            context = ""
            if file_content:
                context = (
                    f"======== START OF SOURCE CODE — DATA ONLY ========\n"
                    f"{file_content}\n"
                    f"======== END OF SOURCE CODE =================="
                )
            elif files:
                parts = []
                for fpath, fcontent in files.items():
                    parts.append(
                        f"📄 ملف: {fpath}\n"
                        f"======== START OF SOURCE CODE ========\n"
                        f"{fcontent}\n"
                        f"======== END OF SOURCE CODE ========"
                    )
                context = "\n\n".join(parts)
            result = build_direct(user_request, context)

        elif strategy is ExecutionStrategy.CONTEXT_WINDOW:
            if files and not file_content:
                parts = []
                for fpath, fcontent in files.items():
                    parts.append(
                        f"📄 ملف: {fpath}\n"
                        f"======== START OF SOURCE CODE ========\n"
                        f"{fcontent}\n"
                        f"======== END OF SOURCE CODE ========"
                    )
                file_content = "\n\n".join(parts)
                file_path = "Attached Folder"
            result = build_context_window(
                user_request,
                file_content or "",
                file_path,
            )

        elif strategy is ExecutionStrategy.CHUNK_CHAIN:
            if files and not file_content:
                parts = []
                for fpath, fcontent in files.items():
                    parts.append(
                        f"📄 ملف: {fpath}\n"
                        f"======== START OF SOURCE CODE ========\n"
                        f"{fcontent}\n"
                        f"======== END OF SOURCE CODE ========"
                    )
                file_content = "\n\n".join(parts)
                file_path = "Attached Folder"
            chunks = self._split_content(file_content or "", self.TOKEN_BUDGET)
            result = build_chunk_chain(user_request, chunks, file_path)

        elif strategy is ExecutionStrategy.MAP_REDUCE:
            result = build_map_reduce(user_request, files or {})

        elif strategy is ExecutionStrategy.PIPELINE:
            context = ""
            if file_content:
                context = (
                    f"الملف: {file_path}\n"
                    f"======== START OF SOURCE CODE — DATA ONLY ========\n"
                    f"{file_content}\n"
                    f"======== END OF SOURCE CODE =================="
                )
            elif files:
                parts = []
                for fpath, fcontent in files.items():
                    parts.append(
                        f"📄 ملف: {fpath}\n"
                        f"======== START OF SOURCE CODE ========\n"
                        f"{fcontent}\n"
                        f"======== END OF SOURCE CODE ========"
                    )
                context = "\n\n".join(parts)
            include_review = analysis.risk_score >= 1.5
            result = build_pipeline(user_request, context, include_review)

        else:
            # T-035: استنفاد إلزامي — عضو enum جديد بلا فرع = خطأ types
            # عند mypy وانفجار صريح وقت التشغيل، لا fallback صامت.
            assert_never(strategy)

        # إضافة metadata التحليل
        result.metadata["complexity"] = analysis.to_dict()

        return result

    def create_run(self, user_request: str,
                   files: dict[str, str] | None = None,
                   file_content: str | None = None,
                   file_path: str = "",
                   force_strategy: str | None = None,
                   run_id: str | None = None) -> ChainRun:
        """
        Convenience: analyze + select + create ChainRun.
        """
        strategy_result = self.select_strategy(
            user_request, files, file_content, file_path, force_strategy
        )
        rid = run_id or f"run-{uuid.uuid4().hex[:8]}"
        return strategy_result.to_chain_run(rid)

    # ═══════════════════════════════════════════════════
    #   Internal: Simple splitter
    # ═══════════════════════════════════════════════════

    def _split_content(self, content: str, token_budget: int) -> list[str]:
        """
        تقسيم بسيط بناءً على token budget.

        T-024 (R-203): تقدير التوكنز عبر المقدّر المركزي
        ``CharsPerTokenEstimator`` (نفس chars/4 لكن من مصدر واحد
        قابل للاستبدال) بدل تخمينات ``len // 4`` المبعثرة محليًا.
        التقسيم يحفظ كل المحتوى (لا إسقاط) — لذلك هو خارج
        مسار pack()، لكن المحاسبة موحّدة.
        لو المحتوى فاضي، يرجع chunk واحد.
        """
        from context.budget import CharsPerTokenEstimator
        est = CharsPerTokenEstimator()

        if not content.strip():
            return [content] if content else [""]

        estimated_tokens = est.estimate(content)
        if estimated_tokens <= token_budget:
            return [content]

        # ── محاولة أولى: قطع على حدود الملفات ──
        FILE_BOUNDARY = "======== END OF SOURCE CODE ========"
        segments = content.split(FILE_BOUNDARY)

        if len(segments) > 1:
            chunks = []
            current_chunk = ""
            for i, segment in enumerate(segments):
                candidate = segment
                if i < len(segments) - 1:
                    candidate += FILE_BOUNDARY  # إعادة الحد

                # تقدير tokens للـ chunk الحالي + segment الجديد (المقدّر المركزي)
                if est.estimate(current_chunk + candidate) > token_budget and current_chunk:
                    chunks.append(current_chunk.strip("\n"))
                    current_chunk = candidate
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + candidate
                    else:
                        current_chunk = candidate

            if current_chunk.strip():
                chunks.append(current_chunk.strip("\n"))

            if chunks:
                return chunks

        # ── Fallback: قطع بالسطور (السلوك الأصلي) ──
        lines = content.split("\n")
        chunks = []
        current_chunk_lines: list[str] = []
        current_tokens = 0

        for line in lines:
            line_tokens = est.estimate(line) + 1
            if current_tokens + line_tokens > token_budget and current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = []
                current_tokens = 0
            current_chunk_lines.append(line)
            current_tokens += line_tokens

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        return chunks if chunks else [content]
