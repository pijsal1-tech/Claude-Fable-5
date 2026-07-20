# -*- coding: utf-8 -*-
"""Demo strategy plugin — الحزمة المرجعية لمؤلّفي الإضافات (T-102 / R-801).

هذه أبسط إضافة استراتيجية صالحة: صنف بـ ``build(ctx)`` يرجع
``StrategyResult`` (خطوة executor واحدة تكرّر الطلب) + ``routing_hints``
تعلن متى تُرشَّح. العقد الكامل في ``chain/plugin_api.py`` (رأس الوحدة)
و``examples/demo_strategy/README.md``.

ملاحظة استيراد: الإضافة تستورد ``chain.*`` من المضيف — التثبيت
والتشغيل يفترضان بيئة المضيف نفسها (الإضافة بلا مضيف لا معنى لها).
"""
from __future__ import annotations

from chain.models import ChainStep, ExecutionPolicy
from chain.strategies import StrategyResult


class DemoEchoStrategy:
    """استراتيجية تجريبية: خطوة executor واحدة تصيغ الطلب مع السياق.

    ``routing_hints`` (يستهلكها التوجيه في T-102):
    - ``keywords``: الطلب المطابق لأي كلمة يُرشَّح لهذه الإضافة.
    - ``max_complexity``: لا ترشيح فوق هذا التعقيد (الإضافة التجريبية
      للطلبات البسيطة فقط).
    """

    routing_hints = {
        "keywords": ["demo echo", "echo demo"],
        "max_complexity": 3.0,
    }

    def build(self, ctx, **kwargs) -> StrategyResult:
        """يبني خطة من خطوة واحدة — الطلب + مسارات سياق ctx إن وجدت."""
        paths = ctx.context_paths()
        context_note = ""
        if paths:
            context_note = "\n\nContext files: " + ", ".join(paths)
        ctx.emit("plugin_progress",
                 {"plugin": "demo_echo", "stage": "planned"})
        steps = [
            ChainStep(
                id="demo-echo",
                name="Demo Echo Execute",
                stage="execute",
                agent_role="executor",
                prompt_template=ctx.user_request + context_note,
            ),
        ]
        return StrategyResult(
            strategy_name="plugin:demo_echo",
            steps=steps,
            policy=ExecutionPolicy(
                max_provider_calls=2,
                max_retries=1,
                step_timeout_seconds=120,
                max_total_time_seconds=600,
            ),
            metadata={"plugin": "demo_echo"},
        )
