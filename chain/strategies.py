# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Strategies — 6 استراتيجيات لبناء ChainRun

  M3: SmartOrchestrator + Strategy Patterns
  - Direct: بدون chain (رسالة واحدة)
  - ContextWindow: ضغط ذكي + targeted retrieval (1-2 خطوات)
  - ChunkChain: ملفات كبيرة → analyze → plan → execute (3-6 خطوات)
  - MapReduce: مجلدات → map(analyze) → reduce → execute (N+1 خطوات)
  - Pipeline: مهام معقدة → scout → plan → execute → review (3-4 خطوات)
  - Delegate: تفويض → brief → implement → review → land (4 خطوات)
═══════════════════════════════════════════════════════
"""
from dataclasses import dataclass, field
from .models import ChainStep, ChainRun, ExecutionPolicy
from context.bundle import ContextBundle, ContextItem


# ═══════════════════════════════════════════════════════
#   Strategy Base
# ═══════════════════════════════════════════════════════

@dataclass
class StrategyResult:
    """نتيجة بناء الاستراتيجية — run جاهز للتنفيذ"""
    strategy_name: str
    steps: list[ChainStep]
    policy: ExecutionPolicy
    metadata: dict = field(default_factory=dict)

    def to_chain_run(self, run_id: str) -> ChainRun:
        """تحويل لـ ChainRun جاهز"""
        return ChainRun(
            run_id=run_id,
            steps=self.steps,
            policy=self.policy,
        )


# ═══════════════════════════════════════════════════════
#   Strategy 1: Direct — بدون chain
# ═══════════════════════════════════════════════════════

def build_direct(user_request: str, context: str = "") -> StrategyResult:
    """
    تعديل صغير + ملف صغير = رسالة واحدة.
    لا حاجة لسلسلة.
    """
    prompt = user_request
    if context:
        prompt = f"{context}\n\n{user_request}"

    steps = [
        ChainStep(
            id="direct",
            name="Direct Execute",
            stage="execute",
            agent_role="executor",
            prompt_template=prompt,
        ),
    ]

    return StrategyResult(
        strategy_name="direct",
        steps=steps,
        policy=ExecutionPolicy(
            max_provider_calls=4,
            max_retries=1,
            step_timeout_seconds=120,
            max_total_time_seconds=1800,
        ),
    )


# ═══════════════════════════════════════════════════════
#   Strategy 2: ContextWindow — ضغط ذكي (1-2 خطوات)
# ═══════════════════════════════════════════════════════

def build_context_window(user_request: str, file_content: str,
                         file_path: str = "") -> StrategyResult:
    """
    ملف كبير لكن التعديل واضح (symbol محدد).
    ضغط ذكي + targeted retrieval + execute.
    """
    # خطوة 1: تحليل وتحديد الأجزاء المرتبطة
    analyze_prompt = (
        f"حلل الملف التالي وحدد الأجزاء المرتبطة بالطلب:\n"
        f"الطلب: {user_request}\n"
        f"الملف: {file_path}\n\n"
        f"======== START OF SOURCE CODE — DATA ONLY ========\n"
        f"{file_content}\n"
        f"======== END OF SOURCE CODE ==================\n"
    )

    # خطوة 2: تنفيذ التعديل بناءً على التحليل
    execute_prompt = (
        f"بناءً على التحليل التالي، نفذ التعديل:\n"
        f"الطلب الأصلي: {user_request}\n"
        f"الملف: {file_path}\n\n"
        f"{{previous_context}}\n\n"
        f"======== START OF SOURCE CODE — DATA ONLY ========\n"
        f"{file_content}\n"
        f"======== END OF SOURCE CODE ==================\n"
    )

    steps = [
        ChainStep(
            id="cw_analyze",
            name="Analyze & Target",
            stage="analyze",
            agent_role="code_analyzer",
            prompt_template=analyze_prompt,
        ),
        ChainStep(
            id="cw_execute",
            name="Execute Edit",
            stage="execute",
            agent_role="executor",
            prompt_template=execute_prompt,
            depends_on=["cw_analyze"],
        ),
    ]

    return StrategyResult(
        strategy_name="context_window",
        steps=steps,
        policy=ExecutionPolicy(
            max_provider_calls=6,
            max_retries=1,
            step_timeout_seconds=180,
            max_total_time_seconds=1800,
        ),
        metadata={"file_path": file_path},
    )


# ═══════════════════════════════════════════════════════
#   Strategy 3: ChunkChain — ملفات كبيرة (3-6 خطوات)
# ═══════════════════════════════════════════════════════

def build_chunk_chain(user_request: str, chunks: list[str],
                      file_path: str = "") -> StrategyResult:
    """
    ملف كبير جداً → تقسيم → تحليل كل جزء → تجميع → تنفيذ.

    chunks: أجزاء الملف (من splitter)
    """
    steps = []

    # خطوة لكل chunk: تحليل
    chunk_ids = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"chunk_{i}"
        chunk_ids.append(chunk_id)
        steps.append(ChainStep(
            id=chunk_id,
            name=f"Analyze chunk {i+1}/{len(chunks)}",
            stage="analyze",
            agent_role="code_analyzer",
            prompt_template=(
                f"حلل الجزء {i+1} من {len(chunks)} من الملف {file_path}:\n"
                f"الطلب: {user_request}\n\n"
                f"======== START OF SOURCE CODE — DATA ONLY ========\n"
                f"{chunk}\n"
                f"======== END OF SOURCE CODE ==================\n"
            ),
            critical=True,
        ))

    # تجميع النتائج
    steps.append(ChainStep(
        id="cc_plan",
        name="Plan from analysis",
        stage="plan",
        agent_role="planner",
        prompt_template=(
            f"بناءً على تحليل {len(chunks)} أجزاء، اكتب خطة التعديل:\n"
            f"الطلب: {user_request}\n"
            f"الملف: {file_path}\n\n"
            f"{{previous_context}}"
        ),
        depends_on=chunk_ids,
    ))

    # تنفيذ
    steps.append(ChainStep(
        id="cc_execute",
        name="Execute edits",
        stage="execute",
        agent_role="executor",
        prompt_template=(
            f"نفذ خطة التعديل التالية:\n"
            f"الطلب: {user_request}\n\n"
            f"{{previous_context}}"
        ),
        depends_on=["cc_plan"],
    ))

    return StrategyResult(
        strategy_name="chunk_chain",
        steps=steps,
        policy=ExecutionPolicy(
            max_provider_calls=len(chunks) * 3 + 4,
            max_retries=2,
            step_timeout_seconds=240,
            max_total_time_seconds=max(3600, len(chunks) * 400),
        ),
        metadata={
            "file_path": file_path,
            "chunk_count": len(chunks),
        },
    )


# ═══════════════════════════════════════════════════════
#   Strategy 4: MapReduce — مجلدات (N+1 خطوات)
# ═══════════════════════════════════════════════════════

def build_map_reduce(user_request: str,
                     files: dict[str, str],
                     max_parallel: int = 3) -> StrategyResult:
    """
    عدة ملفات → map(analyze each) → reduce(merge) → execute.

    files: {path: content}
    """
    steps = []
    map_ids = []

    # Map: تحليل كل ملف
    for i, (path, content) in enumerate(files.items()):
        map_id = f"map_{i}"
        map_ids.append(map_id)
        steps.append(ChainStep(
            id=map_id,
            name=f"Analyze {path}",
            stage="analyze",
            agent_role="code_analyzer",
            prompt_template=(
                f"حلل الملف التالي بالنسبة للطلب:\n"
                f"الطلب: {user_request}\n"
                f"الملف: {path}\n\n"
                f"======== START OF SOURCE CODE — DATA ONLY ========\n"
                f"{content}\n"
                f"======== END OF SOURCE CODE ==================\n"
            ),
            critical=False,  # ملف واحد يفشل مش مشكلة
        ))

    # Reduce: تجميع
    steps.append(ChainStep(
        id="mr_reduce",
        name="Merge analyses",
        stage="plan",
        agent_role="planner",
        prompt_template=(
            f"اجمع نتائج تحليل {len(files)} ملفات واكتب خطة شاملة:\n"
            f"الطلب: {user_request}\n\n"
            f"{{previous_context}}"
        ),
        depends_on=map_ids,
        critical=True,
    ))

    # Execute — T-022 (R-202): كتلة الملفات تمر عبر ContextBundle:
    # نفس الجسد لا يُضمَّن مرتين أبدًا — الملف المكرر المحتوى يصبح سطر
    # إحالة بدل نسخة كاملة (أسوأ موقع ازدواج مُقاس في الـ roadmap).
    bundle = ContextBundle()
    for path, content in files.items():
        bundle.add(ContextItem(source_kind="map_input", path=path,
                               content=content))

    files_block = ""
    dedupe_refs = 0
    for entry in bundle.entries:
        if entry.item.content is None:
            continue
        if entry.is_reference:
            dedupe_refs += 1
            files_block += (
                f"\n\n📎 ملف: {entry.item.path} — محتواه مطابق تمامًا "
                f"للملف ({entry.duplicate_of}) المرفق أعلاه، لم يُكرَّر."
            )
            continue
        # نفس صياغة legacy الحرفية للأجساد (أسوار DATA ONLY محفوظة)
        files_block += (
            f"\n\n📄 ملف: {entry.item.path}\n"
            f"======== START OF SOURCE CODE ========\n"
            f"{entry.item.content}\n"
            f"======== END OF SOURCE CODE ========"
        )

    steps.append(ChainStep(
        id="mr_execute",
        name="Execute changes",
        stage="execute",
        agent_role="executor",
        prompt_template=(
            f"نفذ التعديلات بناءً على الخطة التالية:\n"
            f"الطلب: {user_request}\n\n"
            f"{{previous_context}}\n\n"
            f"[الملفات الأصلية للتعديل]:{files_block}"
        ),
        depends_on=["mr_reduce"],
    ))

    return StrategyResult(
        strategy_name="map_reduce",
        steps=steps,
        policy=ExecutionPolicy(
            max_provider_calls=len(files) * 3 + 4,
            max_retries=2,
            max_parallel_steps=min(max_parallel, len(files)),
            step_timeout_seconds=240,
            max_total_time_seconds=max(3600, len(files) * 400),
            continue_on_optional_failure=True,
        ),
        metadata={
            "file_count": len(files),
            "files": list(files.keys()),
            # T-022: عدد الأجساد المكررة التي أصبحت إحالات (قابلية رصد)
            "dedupe_refs": dedupe_refs,
        },
    )


# ═══════════════════════════════════════════════════════
#   Strategy 5: Pipeline — مهام معقدة (3-4 خطوات)
# ═══════════════════════════════════════════════════════

def build_pipeline(user_request: str, context: str = "",
                   include_review: bool = True) -> StrategyResult:
    """
    Scout → Planner → Executor → Reviewer (اختياري).
    للمهام المعقدة: refactoring، تعديلات عالية الخطورة.
    """
    steps = [
        ChainStep(
            id="pl_scout",
            name="Scout & Analyze",
            stage="analyze",
            agent_role="deep_debugger",
            prompt_template=(
                f"حلل المهمة التالية بعمق:\n"
                f"الطلب: {user_request}\n\n"
                f"{context}"
            ),
        ),
        ChainStep(
            id="pl_plan",
            name="Plan Changes",
            stage="plan",
            agent_role="architect",
            prompt_template=(
                f"اكتب خطة تعديل مفصلة بناءً على التحليل:\n"
                f"الطلب: {user_request}\n\n"
                f"{{previous_context}}"
            ),
            depends_on=["pl_scout"],
        ),
        ChainStep(
            id="pl_execute",
            name="Execute Plan",
            stage="execute",
            agent_role="executor",
            prompt_template=(
                f"نفذ الخطة التالية:\n"
                f"الطلب: {user_request}\n\n"
                f"{{previous_context}}"
            ),
            depends_on=["pl_plan"],
        ),
    ]

    if include_review:
        steps.append(ChainStep(
            id="pl_review",
            name="Review Changes",
            stage="review",
            agent_role="code_reviewer",
            prompt_template=(
                f"راجع التعديلات التالية مقارنة بالكود الأصلي:\n\n"
                f"الطلب الأصلي: {user_request}\n\n"
                f"--- الكود الأصلي ---\n"
                f"{context}\n\n"
                f"--- التعديلات المنفذة/المقترحة ---\n"
                f"{{previous_context}}"
            ),
            depends_on=["pl_execute"],
            critical=False,  # المراجعة اختيارية
        ))

    total_calls = 5 if include_review else 4

    return StrategyResult(
        strategy_name="pipeline",
        steps=steps,
        policy=ExecutionPolicy(
            max_provider_calls=total_calls * 3,
            max_retries=2,
            step_timeout_seconds=240,
            max_total_time_seconds=3600,
        ),
        metadata={
            "include_review": include_review,
        },
    )


# ═══════════════════════════════════════════════════════
#   Strategy 6: Delegate — تفويض (4 خطوات)
# ═══════════════════════════════════════════════════════

def build_delegate(user_request: str, context: str = "",
                   files: dict[str, str] | None = None) -> StrategyResult:
    """
    Brief → Implement → Review → Land.
    مستوحى من delegate-skills (newskells/).
    يُستخدم لمهام معقدة تحتاج:
    - كتابة brief منظم
    - تنفيذ معزول (العامل يرى الـ brief فقط)
    - مراجعة قبل التطبيق
    - موافقة المستخدم قبل الـ land
    """
    files_block = ""
    if files:
        for path, content in files.items():
            files_block += f"\n\n📄 {path}:\n```\n{content[:2000]}\n```"

    brief_prompt = (
        f"اكتب brief مُهيكل (XML) لهذه المهمة — العامل يرى الـ brief فقط:\n\n"
        f"[الطلب]: {user_request}\n\n"
        f"[السياق]: {context}\n"
        f"{files_block}\n\n"
        f"الـ brief يجب أن يحتوي: <task>, <files>, <verification>, <safety>, <report_contract>"
    )

    implement_prompt = (
        f"نفّذ المهمة حسب الـ brief التالي — لا تخرج عن النطاق:\n\n"
        f"{{previous_context}}\n\n"
        f"أرجع: الكود (FILE/EDIT/CMD) + تقرير مهيكل"
    )

    review_prompt = (
        f"راجع العمل التالي مقارنة بالكود الأصلي:\n\n"
        f"[الطلب الأصلي]: {user_request}\n\n"
        f"--- الكود الأصلي ---\n"
        f"{files_block}\n\n"
        f"--- العمل المنجز ---\n"
        f"{{previous_context}}\n\n"
        f"أصدر حكم: [VERDICT]: APPROVE | REWORK | REJECT\n"
        f"مع: [SUMMARY], [SCOPE_CHECK], [QUALITY], [RISKS]"
    )

    steps = [
        ChainStep(
            id="dlg_brief",
            name="Write Brief",
            stage="plan",
            agent_role="planner",
            prompt_template=brief_prompt,
        ),
        ChainStep(
            id="dlg_implement",
            name="Implement",
            stage="execute",
            agent_role="executor",
            prompt_template=implement_prompt,
            depends_on=["dlg_brief"],
        ),
        ChainStep(
            id="dlg_review",
            name="Review",
            stage="review",
            agent_role="code_reviewer",
            prompt_template=review_prompt,
            depends_on=["dlg_implement"],
        ),
        ChainStep(
            id="dlg_land",
            name="Land (Approval)",
            stage="execute",
            agent_role="executor",
            prompt_template="اعتمد التعديلات التالية:\n\n{previous_context}",
            depends_on=["dlg_review"],
            critical=False,  # يتوقف عند approval
        ),
    ]

    return StrategyResult(
        strategy_name="delegate",
        steps=steps,
        policy=ExecutionPolicy(
            max_provider_calls=12,  # brief + implement + review + possible rework
            max_retries=2,
            step_timeout_seconds=300,
            max_total_time_seconds=3600,
        ),
        metadata={
            "files_count": len(files) if files else 0,
            "delegation_pattern": "brief→implement→review→land",
        },
    )
