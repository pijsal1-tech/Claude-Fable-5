# QA Bug Index — فهرس المشاكل

| Bug ID | القسم | العنوان | الخطورة | الحالة | الملف |
|---|---|---|---|---|---|
| BUG-CTX-001 | Context / Project Binding | عدم اتساق بين سياق المشروع الحالي والملفات التي يقرأها/يعتمد عليها الرد | High | Open / Needs verification | QA_TEST_ONLY/CONTEXT_PROJECT_MISMATCH_TESTS.md |
| BUG-SEC-001 | Sensitive Data Handling | الرد أشار أن الملفات المرفقة تحتوي emails/passwords/cookies/sessions | Critical | Open / Needs verification | QA_TEST_ONLY/SENSITIVE_DATA_TESTS.md |
| BUG-ACT-001 | Action Scope | طلب مراجعة فقط تحول إلى تنفيذ/إنشاء كود مزعوم | High | Open / Confirmed | QA_TEST_ONLY/ACTION_SCOPE_VIOLATION_TESTS.md |
| BUG-PROV-001 | Provider Failure | ظهور 429 من Blackbox كرسالة خام مع ANSI وبدون fallback واضح | Medium/High | Open / Confirmed | QA_TEST_ONLY/PROVIDER_FAILURE_TESTS.md |
| BUG-PATH-002 | Path / Auto Collection | Auto Analyzer حلل ملفات ومسارات خارج المشروع المفتوح رغم طلب عدم فتح فولدر جديد | Critical Candidate | Open / Confirmed | QA_TEST_ONLY/PATH_AUTO_COLLECTION_TESTS.md |
| BUG-PATH-003 | Path Detection UX | ذكر current root في الرسالة فتح كارت مسار بدل اعتباره تأكيد نطاق | High | Open / Confirmed | QA_TEST_ONLY/PATH_AUTO_COLLECTION_TESTS.md |
| BUG-ATT-001 | Attachments / Context | attached-content خارجي يظهر رغم طلب عدم استخدام مرفقات أو سياق قديم | High | Open / Confirmed | QA_TEST_ONLY/ATTACHMENT_CONTEXT_TESTS.md |
| BUG-AUTO-001 | Auto Analysis / Scope | أمر لا تحلل المشروع لم يمنع TREE auto-analysis | Medium/High | Open / Confirmed | QA_TEST_ONLY/AUTO_ANALYSIS_SCOPE_TESTS.md |
| BUG-SEC-003 | Sensitive Data / Auto Analysis | auto-analysis حلل acco33unts.txt رغم طلب عدم جمع سياق | Critical Candidate | Open / Confirmed | QA_TEST_ONLY/SENSITIVE_DATA_TESTS.md |
| BUG-UX-001 | Response Format / Options | OPTIONS ظهرت رغم طلب إجابة بكلمة واحدة فقط | Low/Medium | Open / Confirmed | QA_TEST_ONLY/RESPONSE_FORMAT_TESTS.md |
| BUG-CMD-001 | Command Execution | أمر يحتوي && لم يُرفض مبكرًا وتحوّل مرة لكود ومرة لطلب موافقة | High | Open / Confirmed | QA_TEST_ONLY/COMMAND_EXECUTION_TESTS.md |
| BUG-ROUTE-001 | Routing / Intent | نفس prompt تشغيل أمر أنتج سلوك مختلف بين شاتين | Medium/High | Open / Confirmed | QA_TEST_ONLY/ROUTING_INTENT_TESTS.md |
| BUG-PATH-004 | Path Display / Analyzed List | analyzed list يقتطع/يعرض R_rewind.ai كـ ai/Root | Low/Medium | Open / Confirmed | QA_TEST_ONLY/PATH_AUTO_COLLECTION_TESTS.md |
| BUG-FILE-001 | File Operations / Plan | Plan قراءة فقط أنتج Review Changes لملف output.md | High | Open / Confirmed | QA_TEST_ONLY/FILE_OPERATION_TESTS.md |
| BUG-FILE-OBS-001 | File Operations / Chat | "اقرأ ملف" اختار full_chain + Context Mixing لمشاريع مش مطلوبة | High | Open / Confirmed | QA_TEST_ONLY/FILE_OPERATION_TESTS.md |
| BUG-ACT-002 | Action Scope / Plan | Plan/read-only استخدم auto_chain Execute Edit | High | Open / Confirmed | QA_TEST_ONLY/ACTION_SCOPE_VIOLATION_TESTS.md |
