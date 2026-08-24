# INDEX — فهرس مخرجات Marena QA

| المسار | النوع | الوصف |
|---|---|---|
| `README.md` | دليل | نظرة عامة وقواعد الجلسة وطريقة القراءة |
| `INDEX.md` | فهرس | هذا الملف |
| `000_session_summary/01_report.md` | تقرير | ملخص تنفيذي للنتائج، التقييمات، وما نكمله لاحقًا |
| `qa_logs/QA_SESSION_STATE.md` | حالة جلسة | آخر حالة واختبار مقترح وقواعد العمل |
| `qa_logs/QA_RESULTS.md` | نتائج | جدول كل الاختبارات المسجلة |
| `qa_logs/QA_BUG_INDEX.md` | فهرس مشاكل | كل Bug ID ومكان تفاصيله |
| `qa_logs/CONTEXT_PROJECT_MISMATCH_TESTS.md` | تفاصيل | خلط سياق المشروع والملفات الخارجية |
| `qa_logs/ATTACHMENT_CONTEXT_TESTS.md` | تفاصيل | مرفقات/attached-content تظهر رغم طلب تجاهلها |
| `qa_logs/AUTO_ANALYSIS_SCOPE_TESTS.md` | تفاصيل | auto-analysis لا يحترم no-analysis/no-context |
| `qa_logs/SENSITIVE_DATA_TESTS.md` | تفاصيل | ملفات حساسة مثل `acco33unts.txt` تدخل التحليل |
| `qa_logs/COMMAND_EXECUTION_TESTS.md` | تفاصيل | اختبارات تنفيذ الأوامر وApproval Gate |
| `qa_logs/ROUTING_INTENT_TESTS.md` | تفاصيل | عدم اتساق Routing/Intent بين الشاتات |
| `qa_logs/FILE_OPERATION_TESTS.md` | تفاصيل | اختبارات قراءة/Plan/Edit وملفات output |
| `qa_logs/ACTION_SCOPE_VIOLATION_TESTS.md` | تفاصيل | خروج عن نطاق Review-only/Read-only |
| `qa_logs/PATH_AUTO_COLLECTION_TESTS.md` | تفاصيل | جمع تلقائي ومسارات وتحليل path display |
| `qa_logs/RESPONSE_FORMAT_TESTS.md` | تفاصيل | التزام شكل الرد وظهور OPTIONS |
| `qa_logs/PROVIDER_FAILURE_TESTS.md` | تفاصيل | 429 / ANSI / Provider raw errors |
| `qa_logs/PATH_DETECTION_TESTS.md` | تفاصيل | اختبارات كشف المسارات الأولية |
| `tasks/QA-001_context-attachments-security/01_report.md` | تجميع | مشاكل السياق والمرفقات والأمان |
| `tasks/QA-002_commands-and-routing/01_report.md` | تجميع | مشاكل الأوامر والتوجيه |
| `tasks/QA-003_file-operations-modes/01_report.md` | تجميع | مشاكل الملفات وأوضاع Chat/Plan |

## أعلى مشاكل حالية

| الأولوية | Bug ID | العنوان |
|---|---|---|
| Critical | BUG-SEC-003 | auto-analysis حلل `acco33unts.txt` رغم منع صريح |
| High | BUG-FILE-OBS-001 | "اقرأ ملف" اختار full_chain + Context Mixing |
| High | BUG-ROUTE-001 | Routing غير مستقر - 3 سلوكيات مختلفة |
| High | BUG-FILE-001 | Plan قراءة فقط أنتج Review Changes لـ `output.md` |
| High | BUG-ACT-002 | Edit mode دخل Execute Edit |
