# -*- coding: utf-8 -*-
"""runners/ — تطبيقات عقد Runner (T-040+, R-501).

كل وضع تنفيذ يصبح Runner واحدًا يجتاز RunnerContractMixin:
- direct.DirectRunner  — رد provider واحد يُبث كقطع (T-040).
- chain.ChainRunner    — يلف ChainBridge الحالي خلف العقد (T-040).
- (T-041: agent + delegate)

المسارات القديمة في server.py تبقى خلف علم LEGACY_DISPATCH
(الافتراضي = قديم) حتى تثبت المطابقة لكل وضع — ثم تُحذف مع العلم.
"""
from runners.chain import ChainRunner
from runners.direct import DirectRunner

__all__ = ["ChainRunner", "DirectRunner"]
