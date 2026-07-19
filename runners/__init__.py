# -*- coding: utf-8 -*-
"""runners/ — تطبيقات عقد Runner (T-040+, R-501).

كل وضع تنفيذ يصبح Runner واحدًا يجتاز RunnerContractMixin:
- direct.DirectRunner  — رد provider واحد يُبث كقطع (T-040).
- chain.ChainRunner    — يلف ChainBridge الحالي خلف العقد (T-040).
- (T-041: agent + delegate — ومعهما حذف حلقة الاستطلاع والعلم)

دورة حياة العلم (بند توثيق T-040):
المسارات القديمة في server.py هي الافتراضي؛ ضبط متغير البيئة
LEGACY_DISPATCH=0 يفعّل مسار الـ runners لوضعي direct + chain. بعد إثبات
المطابقة لكل الأوضاع (T-041) يُحذف العلم والمسارات القديمة معًا —
مسار إرسال واحد (بند قبول R-501).
"""
from runners.chain import ChainRunner
from runners.direct import DirectRunner

__all__ = ["ChainRunner", "DirectRunner"]
