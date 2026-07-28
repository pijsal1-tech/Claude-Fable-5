# -*- coding: utf-8 -*-
"""QA-T06 (جزء TSK-103) — توحيد مسارات حقن السياق تحت ContextBudget (BUG-03).

صفر استدعاءات AI خارجية (حدود QA_MASTER_PLAN): كل شيء عبر
gather_message_context مباشرة بميزانية صريحة أو ميزانية config.yaml.

معيار القبول (IMPLEMENTATION_TASKS): إرفاق مجلد 15 ملفًا + ملف 100KB →
الحمولة النهائية ≤ سقف الميزانية، ولا اقتطاع صامت بلا وسم (QA-T03R).
"""
import pathlib

from context.budget import CharsPerTokenEstimator, ContextBudget
from context.facade import _DROP_MARKER, gather_message_context


def _mk_project(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "main.py").write_text("print('x')\n", encoding="utf-8")
    return root


def _attached_15_files_plus_100kb() -> list:
    """محاكاة مسار attach (15 ملفًا × 2000 حرف) + ملف مكتشف 100KB."""
    attached = [("attach_folder:/fake", "[📂 سياق المجلد المرفق: /fake (15 ملفات)]")]
    for i in range(15):
        attached.append((f"attach_file:f{i}.py", f"--- f{i}.py ---\n" + ("x" * 2000)))
    attached.append(("detected_file:/fake/big.txt",
                     "[📄 محتوى الملف: /fake/big.txt]:\n```txt\n" + ("y" * 100 * 1024) + "\n```"))
    return attached


class TestAttachedPayloadCapped:
    """BUG-03: الحمولة النهائية مسقوفة بميزانية السياق."""

    def test_15_files_plus_100kb_within_budget(self, tmp_path):
        """معيار القبول الحرفي: مجلد 15 ملفًا + ملف 100KB → الحمولة ≤ السقف."""
        root = _mk_project(tmp_path)
        budget = ContextBudget(model_window=8_000, reserved_output=1_000,
                               estimator=CharsPerTokenEstimator(4))
        ctx = gather_message_context(root, "تتبع 3 طبقات في المشروع",
                                     attached=_attached_15_files_plus_100kb(),
                                     budget=budget)
        est = CharsPerTokenEstimator(4)
        assert est.estimate(ctx.user_text_with_files) <= budget.budget_tokens
        # الرسالة الأصلية must_have — لا تُسقط أبدًا
        assert "تتبع 3 طبقات" in ctx.user_text_with_files

    def test_config_yaml_budget_used_by_default(self, tmp_path):
        """بدون budget صريح: السقف من config.yaml:context_budget."""
        root = _mk_project(tmp_path)
        ctx = gather_message_context(root, "رسالة",
                                     attached=_attached_15_files_plus_100kb())
        default_budget = ContextBudget.from_config(
            __import__("context.facade", fromlist=["_app_config"])._app_config())
        est = CharsPerTokenEstimator(4)
        assert est.estimate(ctx.user_text_with_files) <= default_budget.budget_tokens

    def test_no_silent_truncation_marker_present(self, tmp_path):
        """QA-T03R: أي إسقاط يظهر بوسم ظاهر + قائمة dropped_attached."""
        root = _mk_project(tmp_path)
        budget = ContextBudget(model_window=2_000, reserved_output=500,
                               estimator=CharsPerTokenEstimator(4))
        ctx = gather_message_context(root, "رسالة قصيرة",
                                     attached=_attached_15_files_plus_100kb(),
                                     budget=budget)
        assert ctx.dropped_attached, "الميزانية الضيقة يجب أن تُسقط عناصر"
        assert _DROP_MARKER in ctx.user_text_with_files, "لا اقتطاع صامت بلا وسم"

    def test_small_attachment_kept_intact(self, tmp_path):
        """مرفق صغير داخل الميزانية: يبقى كاملًا وبلا وسم إسقاط."""
        root = _mk_project(tmp_path)
        budget = ContextBudget(model_window=128_000, reserved_output=8_000,
                               estimator=CharsPerTokenEstimator(4))
        attached = [("detected_file:/x/a.py",
                     "[📄 محتوى الملف: /x/a.py]:\n```py\nprint(1)\n```")]
        ctx = gather_message_context(root, "اشرح الملف", attached=attached,
                                     budget=budget)
        assert "print(1)" in ctx.user_text_with_files
        assert ctx.dropped_attached == []
        assert _DROP_MARKER not in ctx.user_text_with_files


class TestHistoricalBehaviorPreserved:
    """attached=None (الافتراضي) = السلوك القديم بايت-بايت (goldens T-017)."""

    def test_no_attached_identical_output(self, tmp_path):
        root = _mk_project(tmp_path)
        a = gather_message_context(root, "رسالة عادية عن main.py")
        b = gather_message_context(root, "رسالة عادية عن main.py",
                                   attached=None)
        assert a.user_text_with_files == b.user_text_with_files
        assert a.mentioned_files == b.mentioned_files
        assert a.project_context == b.project_context
        assert a.dropped_attached == [] and b.dropped_attached == []

    def test_empty_attached_list_same_as_none(self, tmp_path):
        root = _mk_project(tmp_path)
        a = gather_message_context(root, "سؤال")
        b = gather_message_context(root, "سؤال", attached=[])
        assert a.user_text_with_files == b.user_text_with_files


class TestDroppedAccounting:
    """الإسقاط مرصود: الأدنى طبقةً والأكبر حجمًا أولًا، والرسالة محفوظة."""

    def test_largest_attachment_dropped_first(self, tmp_path):
        root = _mk_project(tmp_path)
        budget = ContextBudget(model_window=1_200, reserved_output=200,
                               estimator=CharsPerTokenEstimator(4))
        attached = [
            ("small", "s" * 100),
            ("huge", "h" * 100_000),
        ]
        ctx = gather_message_context(root, "م", attached=attached,
                                     budget=budget)
        assert "huge" in ctx.dropped_attached
        assert "small" not in ctx.dropped_attached
