"""core/version.py — TSK-716 (P0-4 / دفعة D-8): رقم إصدار المنتج القانوني.

المصدر الوحيد لرقم الإصدار (SemVer). يُقرأ من:
- server.py: ترويسة الإقلاع + راية ``--version``.
- routes/meta.py (/api/info): حقل ``version`` (إضافة مفتاح فقط — TSK-716).

سياسة الرفع (موثقة في README §سياسة الإصدارات):
- ``-rc.N`` يبقى حتى يُنفِّذ المالك قائمة فحص Windows
  (docs/WINDOWS_COMPAT.md §6) — قرار D-8-ب: Windows أولًا.
- patch: إصلاحات بلا تغيير عقد. minor: ميزات متوافقة (دفعات P1/P2).
- major: أي كسر عقد (أشكال JSON/إطارات WS/عقد localhost).
"""

__version__ = "1.0.0-rc.1"
