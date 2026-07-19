# -*- coding: utf-8 -*-
"""runners/ — تطبيقات عقد Runner (T-040/T-041, R-501).

معمارية الإرسال (بند توثيق T-041)
═════════════════════════════════
مسار إرسال **واحد**: كل رسالة تصل ws_handler تُترجم إلى
``RunRequest`` ثم ``RUNNERS[strategy](**deps).run(request, ticket, sink)``
(الخريطة في server.py). علم LEGACY_DISPATCH والسلم القديم — stream-worker
المباشر، نداء start_chain المباشر، وحلقة استطلاع الـ Agent داخل
ws_handler — حُذفوا جميعًا في T-041 بعد إثبات المطابقة
(tests/integration/test_dispatch_parity.py).

الأدوار الأربعة (كلها تجتاز RunnerContractMixin كاملة):
- direct.DirectRunner     — رد provider واحد يُبث كقطع run_output.
- chain.ChainRunner       — يلف ChainBridge؛ إطارات الجسر أحداث حرة.
- agent.AgentRunner       — يلف AgentLoop؛ الرد النهائي قطع بحجم 80
  (مطابق للمسار المحذوف)؛ on_loop ينشر الحلقة النشطة حتى تصل
  agent_approval_response/cancel_agent من مستوى WS الأعلى مباشرة —
  هذا ما جعل حلقة الاستطلاع (الـ workaround) قابلة للحذف.
- delegate.DelegateRunner — يلف DelegateBridge؛ waiting_approval يُغلق
  الأحداث لكن يترك التذكرة حية — land()/reject() يحسمانها.

تدفق الأحداث للواجهة: كل runner يبث عبر EventStream (started → أحداث
حرة → finished)؛ ``server._RunnerWSAdapter`` يترجمها لإطارات WS القديمة
حرفيًا (run_output → chunk؛ الأحداث الحرة تمر بأسمائها؛ أحداث دورة
الحياة صامتة). دورة حياة التذكرة: الـ runner يُنهيها بنفس status
النتيجة — والأغلفة التي تُنهي تذاكرها بنفسها (AgentLoop/الجسور)
يبقى نداء الإنهاء الثاني معها لا-عملية آمنة.
"""
from runners.agent import AgentRunner
from runners.chain import ChainRunner
from runners.delegate import DelegateRunner
from runners.direct import DirectRunner

__all__ = ["AgentRunner", "ChainRunner", "DelegateRunner", "DirectRunner"]
