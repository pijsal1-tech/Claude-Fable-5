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

    @property
    def total(self) -> float:
        return (self.size_score + self.file_count_score +
                self.cross_file_score + self.request_complexity +
                self.risk_score)

    @property
    def recommended_strategy(self) -> str:
        """الاستراتيجية المقترحة بناءً على الـ score"""
        score = self.total
        if score <= 2.0:
            return "direct"
        elif score <= 4.0:
            # ملفات متعددة (4+) مع تعقيد متوسط → map_reduce أفضل من context_window
            if self.file_count_score >= 3.0:
                return "map_reduce"
            return "context_window"
        elif score <= 7.0:
            # أي ملفات متعددة (2+) → map_reduce بدل chunk_chain
            if self.file_count_score >= 1.5:
                return "map_reduce"
            return "chunk_chain"
        else:
            return "pipeline"

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
]

_COMPLEX_REQUEST_PATTERNS = [
    r"refactor", r"rewrite", r"redesign", r"migrate",
    r"إعادة.*هيكلة", r"إعادة.*كتابة", r"نقل",
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
    """

    # ── عتبات ──
    SMALL_FILE_LINES = 200
    MEDIUM_FILE_LINES = 1000
    LARGE_FILE_LINES = 4000
    TOKEN_BUDGET = 8000  # تقدير tokens لكل chunk

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
        complexity_hits = sum(
            1 for p in _COMPLEX_REQUEST_PATTERNS
            if re.search(p, request_lower, re.IGNORECASE)
        )
        if complexity_hits >= 3:
            analysis.request_complexity = 3.0
        elif complexity_hits >= 1:
            analysis.request_complexity = 1.5
        elif len(user_request) > 200:
            analysis.request_complexity = 1.0

        # ── 5. Risk Score ──
        risk_hits = sum(
            1 for p in _HIGH_RISK_PATTERNS
            if re.search(p, request_lower, re.IGNORECASE)
        )
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
                        force_strategy: str | None = None) -> StrategyResult:
        """
        يحلل ويبني StrategyResult جاهزة.

        force_strategy: يفرض استراتيجية معينة (للتجاوز اليدوي).
        """
        analysis = self.analyze_complexity(
            user_request, files, file_content, file_path
        )

        strategy = force_strategy or analysis.recommended_strategy

        if strategy == "direct":
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

        elif strategy == "context_window":
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

        elif strategy == "chunk_chain":
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

        elif strategy == "map_reduce":
            result = build_map_reduce(user_request, files or {})

        elif strategy == "pipeline":
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
            # Fallback to direct
            result = build_direct(user_request)

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
