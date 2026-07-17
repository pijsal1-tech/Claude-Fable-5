# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  AgentLoader — تحميل agent prompts من agents_rules/
  
  M1b: Agent Registry
  - يحمّل prompts حسب الـ stage + agent_role
  - يدعم fallback لأدوار مفقودة
  - حماية من path traversal + encoding + size
  - versioning عبر content hash
═══════════════════════════════════════════════════════
"""
import hashlib
import pathlib
from dataclasses import dataclass, field


# ── حدود أمان ──
MAX_PROMPT_SIZE = 50_000    # 50KB حد أقصى لملف prompt
MAX_PROMPT_LINES = 1000     # حد أقصى للأسطر


@dataclass(frozen=True)
class AgentPrompt:
    """
    prompt محمّل ومعرّف — frozen للأمان والـ caching.
    
    role: الدور (مثل "code_analyzer")
    stage: المرحلة (analyze / plan / execute / review)
    source: المصدر (agents_rules / base / fallback)
    content: محتوى الـ prompt
    content_hash: sha256 للتحقق والـ cache key
    size_bytes: حجم المحتوى
    line_count: عدد الأسطر
    """
    role: str
    stage: str
    source: str              # "agents_rules" | "base" | "fallback"
    content: str
    content_hash: str
    size_bytes: int
    line_count: int


class AgentLoader:
    """
    يحمّل agent prompts من:
    1. agents_rules/ (20+ prompt متخصص)
    2. chain/prompts/ (4 base prompts لكل stage)
    3. fallback افتراضي (لو كل شيء مفقود)
    
    ترتيب البحث:
    agent_role → stage base → fallback
    
    حماية:
    - path traversal (../../) ممنوع
    - ملفات أكبر من MAX_PROMPT_SIZE مرفوضة
    - encoding errors تُتعامل بـ replace
    """

    # ── خريطة: agent_role → مسار نسبي من agents_rules/ ──
    ROLE_MAP: dict[str, str] = {
        # ── Analyzers (stage: analyze) ──
        "code_analyzer":     "سيستم/أنت محلل جودة.md",
        "bug_analyzer":      "سيستم/أنت مراجع أخطاء.md",
        "api_analyzer":      "سيستم/أنت محلل API Flow.md",
        "security_analyzer": "سيستم/أنت مهندس أمان.md",
        "perf_analyzer":     "سيستم/أنت محلل أداء.md",
        "deep_debugger":     "سيستم/أنت محقق أخطاء عميق.md",
        "request_analyzer":  "سيستم/أنت محلل طلبات.md",
        "quality_guard":     "سيستم/أنت حارس الجودة.md",

        # ── Planners (stage: plan) ──
        "planner":           "سيستم/أنت مخطط.md",
        "architect":         "سيستم/أنت مهندس معماري.md",

        # ── Executors (stage: execute) ──
        "executor":          "MICRO_WORKER_SYSTEM_PROMPT.md",
        "backend_dev":       "هندسة-تطبيقات/أنت مهندس Backend.md",
        "frontend_dev":      "هندسة-تطبيقات/أنت مطور Frontend.md",

        # ── Reviewers (stage: review) ──
        "code_reviewer":     "هندسة-تطبيقات/أنت مراجع الكود الآمن.md",
        "quality_reviewer":  "سيستم/أنت محلل جودة.md",
        "vibe_reviewer":     "سيستم/أنت مراجع Vibe.md",
        "evidence_reviewer": "سيستم/أنت فاحص بأدلة.md",
        "compat_reviewer":   "سيستم/أنت مراجع توافق.md",

        # ── Meta ──
        "orchestrator":      "سيستم/أنت مدير الأوركسترا.md",
        "review_manager":    "سيستم/أنت مدير المراجعة.md",
        "team_manager":      "سيستم/أنت مدير فريق.md",
    }

    # ── خريطة: agent_role → stage ──
    ROLE_STAGE_MAP: dict[str, str] = {
        "code_analyzer": "analyze", "bug_analyzer": "analyze",
        "api_analyzer": "analyze", "security_analyzer": "analyze",
        "perf_analyzer": "analyze", "deep_debugger": "analyze",
        "request_analyzer": "analyze", "quality_guard": "analyze",

        "planner": "plan", "architect": "plan",

        "executor": "execute", "backend_dev": "execute",
        "frontend_dev": "execute",

        "code_reviewer": "review", "quality_reviewer": "review",
        "vibe_reviewer": "review", "evidence_reviewer": "review",
        "compat_reviewer": "review",

        "orchestrator": "meta", "review_manager": "meta",
        "team_manager": "meta",
    }

    def __init__(self, agents_dir: str | pathlib.Path | None = None,
                 base_prompts_dir: str | pathlib.Path | None = None):
        """
        agents_dir: مسار agents_rules/ (افتراضي: بجوار chain/)
        base_prompts_dir: مسار chain/prompts/ (افتراضي: chain/prompts/)
        """
        if agents_dir is None:
            # agents_rules/ بجوار chain/
            self._agents_dir = pathlib.Path(__file__).resolve().parent.parent / "agents_rules"
        else:
            self._agents_dir = pathlib.Path(agents_dir).resolve()

        if base_prompts_dir is None:
            self._base_dir = pathlib.Path(__file__).resolve().parent / "prompts"
        else:
            self._base_dir = pathlib.Path(base_prompts_dir).resolve()

        # cache للـ prompts المحمّلة
        self._cache: dict[str, AgentPrompt] = {}

    def load(self, role: str) -> AgentPrompt:
        """
        يحمّل prompt لدور معين.
        
        ترتيب البحث:
        1. agents_rules/ (الدور المتخصص)
        2. chain/prompts/ (base prompt للـ stage)
        3. fallback افتراضي
        
        النتيجة تُخزن في cache (content_hash يمنع إعادة قراءة نفس الملف).
        """
        # Cache hit
        if role in self._cache:
            return self._cache[role]

        stage = self.ROLE_STAGE_MAP.get(role, "execute")

        # 1. Try agents_rules/
        if role in self.ROLE_MAP:
            rel_path = self.ROLE_MAP[role]
            prompt = self._load_from_dir(self._agents_dir, rel_path, role, stage, "agents_rules")
            if prompt is not None:
                self._cache[role] = prompt
                return prompt

        # 2. Try base prompts (chain/prompts/base_{stage}.md)
        base_file = f"base_{stage}.md"
        prompt = self._load_from_dir(self._base_dir, base_file, role, stage, "base")
        if prompt is not None:
            self._cache[role] = prompt
            return prompt

        # 3. Fallback
        fallback = self._make_fallback(role, stage)
        self._cache[role] = fallback
        return fallback

    def load_by_stage(self, stage: str) -> AgentPrompt:
        """
        يحمّل base prompt لـ stage معيّن مباشرةً.
        مفيد لما مفيش agent_role محدد.
        """
        # Try base prompt first
        base_file = f"base_{stage}.md"
        prompt = self._load_from_dir(self._base_dir, base_file, f"base_{stage}", stage, "base")
        if prompt is not None:
            return prompt
        return self._make_fallback(f"base_{stage}", stage)

    def get_available_roles(self) -> list[str]:
        """الأدوار المتاحة فعلياً (ملفاتها موجودة)"""
        available = []
        for role, rel_path in self.ROLE_MAP.items():
            full_path = self._agents_dir / rel_path
            if full_path.exists() and full_path.is_file():
                available.append(role)
        return sorted(available)

    def get_role_stage(self, role: str) -> str:
        """يرجع الـ stage لدور معين"""
        return self.ROLE_STAGE_MAP.get(role, "execute")

    def clear_cache(self):
        """تنظيف الـ cache"""
        self._cache.clear()

    # ═══════════════════════════════════════════════════
    #   Internal
    # ═══════════════════════════════════════════════════

    def _load_from_dir(self, base_dir: pathlib.Path, rel_path: str,
                       role: str, stage: str, source: str) -> AgentPrompt | None:
        """
        يحمّل ملف prompt مع حماية:
        - path traversal
        - حجم الملف
        - encoding
        """
        if not base_dir.exists():
            return None

        # ── حماية path traversal ──
        # نتأكد إن المسار النهائي بيقع جوه base_dir
        try:
            full_path = (base_dir / rel_path).resolve()
        except (ValueError, OSError):
            return None

        # Check: المسار لازم يكون جوه base_dir
        try:
            full_path.relative_to(base_dir.resolve())
        except ValueError:
            # Path traversal attempt!
            return None

        if not full_path.exists() or not full_path.is_file():
            return None

        # ── حماية الحجم ──
        try:
            size = full_path.stat().st_size
        except OSError:
            return None

        if size > MAX_PROMPT_SIZE:
            return None

        # ── قراءة المحتوى ──
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return None

        if not content.strip():
            return None

        line_count = content.count("\n") + 1
        if line_count > MAX_PROMPT_LINES:
            # اقطع الملف لو طويل جداً (مع تحذير)
            lines = content.split("\n")[:MAX_PROMPT_LINES]
            content = "\n".join(lines)
            content += f"\n\n[... truncated at {MAX_PROMPT_LINES} lines ...]"
            line_count = MAX_PROMPT_LINES

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        return AgentPrompt(
            role=role,
            stage=stage,
            source=source,
            content=content,
            content_hash=content_hash,
            size_bytes=len(content.encode("utf-8")),
            line_count=line_count,
        )

    def _make_fallback(self, role: str, stage: str) -> AgentPrompt:
        """fallback prompt بسيط لما مفيش ملف"""
        stage_instructions = {
            "analyze": "حلل الكود التالي واستخرج: الرموز (functions, classes)، العلاقات (imports)، المشاكل المحتملة. أرجع النتيجة بصيغة JSON منظمة.",
            "plan":    "بناءً على التحليل، اكتب خطة تعديل واضحة تحدد: أي ملفات تتعدل، أي أسطر تتغير، ما هو التعديل بالضبط. كن محدداً.",
            "execute": "نفّذ المهمة التالية. أرجع الكود فقط بصيغة EDIT blocks. لا شرح طويل. لا أسئلة.",
            "review":  "راجع الكود/التعديلات التالية. اذكر المشاكل بصيغة JSON: severity, evidence, fix. أرجع verdict: APPROVE / REQUIRES_FIXES / BLOCK.",
            "meta":    "نسّق بين المهام التالية واتخذ القرار المناسب.",
        }
        content = stage_instructions.get(stage, stage_instructions["execute"])
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        return AgentPrompt(
            role=role,
            stage=stage,
            source="fallback",
            content=content,
            content_hash=content_hash,
            size_bytes=len(content.encode("utf-8")),
            line_count=content.count("\n") + 1,
        )
