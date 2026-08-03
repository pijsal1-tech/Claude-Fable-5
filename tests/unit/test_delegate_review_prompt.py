# -*- coding: utf-8 -*-
"""TSK-CEV-114 (FI-14): حراس التلاعب بالاختبارات في مراجعة التفويض.

اختبار تسييج واحد يثبت أن معايير كشف التلاعب بالاختبارات
(review-and-land.md §"Check the tests before trusting the gates")
موجودة نصًا في الـprompt المُحمَّل فعليًا عبر نفس مسار الإنتاج
(`_load_prompt("delegate_review.md")` — chain/delegate.py:229).
تحرير مستقبلي يُسقط هذه المعايير من الـprompt يكسر هذا الاختبار
بدل أن يمر صامتًا.
"""
from chain.delegate import _load_prompt


class TestReviewPromptTamperingCriteria:
    """FI-14: نص المعايير يجب أن ينجو من أي تعديل مستقبلي للـprompt."""

    def _prompt(self) -> str:
        text = _load_prompt("delegate_review.md")
        assert text, "delegate_review.md مفقود أو فارغ — عقد المراجعة مكسور"
        return text

    def test_tampering_section_present(self):
        """القسم موجود ويربط التلاعب بتغيير العقد ⇒ REWORK أو REJECT."""
        text = self._prompt()
        assert "افحص الاختبارات قبل أن تثق بالبوابات" in text
        assert "تغيير عقد ⇒ REWORK أو REJECT" in text
        assert "لا يُمتص صامتًا" in text

    def test_three_tampering_criteria_present(self):
        """المعايير الثلاثة من review-and-land.md:8-19 موجودة نصًا."""
        text = self._prompt()
        # 1) تعديل غير مُكلَّف به على اختبارات قائمة
        assert "تعديل غير مُكلَّف به على اختبارات قائمة" in text
        assert "unbriefed edit" in text
        # 2) skip/تعطيل/تعليق = عاملها كفاشلة
        assert "إضافة skip أو تعطيل أو تعليق" in text
        assert "treat as failing" in text
        # 3) تليين التأكيدات
        assert "تليين تأكيدات" in text
        assert "exact→contains/truthy" in text

    def test_verdict_format_line_untouched(self):
        """صيغة الحكم التي يعتمد عليها _parse_verdict (delegate.py:706)
        باقية حرفيًا — إضافة FI-14 لم تمسها."""
        text = self._prompt()
        assert "[VERDICT]: APPROVE | REWORK | REJECT" in text
