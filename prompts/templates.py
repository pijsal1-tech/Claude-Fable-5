# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Prompt Templates — قوالب البرومبتات الثلاثة
  مأخوذة من prompt.md ومخصصة لتطوير الويب
═══════════════════════════════════════════════════════
"""
import pathlib

_PROMPTS_DIR = pathlib.Path(__file__).resolve().parent

# ── تحميل System Prompt ──
def _load_system_prompt() -> str:
    path = _PROMPTS_DIR / "web_system.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "أنت مطور ويب خبير."


SYSTEM_PROMPT = _load_system_prompt()


# ════════════════════════════════════════════════════
# قوالب الأوضاع الثلاثة
# ════════════════════════════════════════════════════

PLANNING_TEMPLATE = """
[الدور والمسؤولية]
أنت تعمل بصفة Staff Software Engineer ومدير تقني Tech Lead.
مهمتك التخطيط المعماري الصارم للمشروع التالي:

{user_request}

[سياق المشروع الحالي]
{project_context}

[قواعد ما قبل التخطيط]
1. حدد افتراضاتك حول المتطلبات بوضوح.
2. إذا وجد غموض في المتطلبات، توقف واسأل فوراً.
3. اقترح الحل الأبسط (Simplicity First).

[البروتوكولات الإلزامية]
1. الوعي الزمني: استخدم أحدث الإصدارات المستقرة.
2. منع زحف الميزات: التزم بالنطاق المطلوب فقط.
3. المعمارية الذكية: أقل قدر من الكود يحل المشكلة.
4. خريطة المشروع: قدم TECH_STACK, SYSTEM_FLOW, ARCHITECTURE.

[المخرج المطلوب]
قدم خطة عمل مكثفة مع Milestones قابلة للتحقق.
استخدم صيغ الكود المحددة في System Prompt.
""".strip()


EXECUTION_TEMPLATE = """
[تفويض التنفيذ المستمر]
أنت Tech Lead المسؤول عن تحويل المتطلبات إلى كود جاهز.

{user_request}

[سياق المشروع الحالي]
{project_context}

[معايير التنفيذ]
1. بساطة التنفيذ: إذا كان يمكن كتابة 50 سطراً بدلاً من 200، افعل ذلك.
2. التنفيذ الموجه بالأهداف: لكل ميزة، حدد معيار النجاح قبل كتابتها.

[بروتوكولات العمل]
1. جودة الكود: ممنوع Placeholders أو TODO. كود كامل ومعالج للأخطاء.
2. التحقق الذاتي: تأكد من عدم وجود Regression.

[أمر الانطلاق]
ابدأ التنفيذ الآن. اكتب الكود الكامل باستخدام صيغ FILE/CMD/EDIT المحددة.
""".strip()


EDITING_TEMPLATE = """
[الدور والمهمة]
أنت Staff Software Engineer. المطلوب جراحة برمجية للمشروع:

{user_request}

[سياق المشروع الحالي]
{project_context}

[الملفات المستهدفة]
{target_files}

[قواعد التعديل الجراحي]
1. المس فقط ما يجب لمسه — لا تحسن كود مجاور.
2. مطابقة الأسلوب: التزم بأسلوب الكود الحالي.
3. نظف مخلفاتك فقط: إذا تسبب تعديلك في كود يتيم، أزله.

[بروتوكول التنفيذ]
1. تحليل التأثير: حدد الملفات المتأثرة بدقة.
2. استخدم صيغة EDIT للتعديلات الجراحية.
3. تأكد من عدم كسر الميزات الأخرى.
""".strip()


# ════════════════════════════════════════════════════
# بناء البرومبت النهائي
# ════════════════════════════════════════════════════

def build_prompt(mode: str, user_request: str,
                 project_context: str = "", target_files: str = "") -> str:
    """
    بناء البرومبت الكامل حسب الوضع.

    Args:
        mode: "plan" | "build" | "edit" | "chat"
        user_request: طلب المستخدم
        project_context: ملخص بنية المشروع
        target_files: محتوى الملفات المستهدفة (لوضع edit)

    Returns:
        البرومبت النهائي الجاهز للإرسال
    """
    context = project_context or "لم يتم تحديد مشروع بعد."

    if mode == "plan":
        return PLANNING_TEMPLATE.replace("{user_request}", user_request).replace("{project_context}", context)
    elif mode == "build":
        return EXECUTION_TEMPLATE.replace("{user_request}", user_request).replace("{project_context}", context)
    elif mode == "edit":
        return EDITING_TEMPLATE.replace("{user_request}", user_request).replace("{project_context}", context).replace("{target_files}", target_files or "لم يتم تحديد ملفات.")
    else:
        # وضع chat العادي — سؤال مباشر
        if context != "لم يتم تحديد مشروع بعد.":
            return f"[سياق المشروع]\n{context}\n\n[السؤال]\n{user_request}"
        return user_request


def get_system_prompt() -> str:
    """إرجاع System Prompt"""
    return SYSTEM_PROMPT
