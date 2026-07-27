# ARCHITECTURE_REVIEW.md — editor_v4 (P1)

> **المرحلة:** P1 — مراجعة معمارية | **الوضع:** MODE A (تخطيط، لا تعديل مصدر)
> **المستودع:** `pijsal1-tech/Claude-Fable-5` — فرع `genspark_ai_developer`
> **تاريخ المراجعة:** 2026-07-27 | **الحالة تعيش في:** `docs/engineering/PROGRESS.md` فقط
> **سياسة الاستشهاد:** كل ادعاء يُسند إلى ملف + دالة + نطاق أسطر **فعلي** (تم التحقق من الأسطر مباشرة، لا اعتماد على تلميحات CONTEXT). الأسرار تُذكر كـ `[REDACTED — file:Lnn]`.

---

## 0. ملخص تنفيذي

editor_v4 هو محرر أكواد مدعوم بالذكاء الاصطناعي: خادم Flask + flask-sock (`server.py`، 2,613 سطرًا) يخدم واجهة أمامية أحادية الصفحة (`static/app.js`، 3,723 سطرًا؛ `static/index.html`، 510 أسطر)، مع أربعة أوضاع تشغيل (chat / plan / build / edit)، وطبقة مزودين متعددة (11 ملفًا في `providers/`) خلف `ProviderPool` بقواطع دوائر (Circuit Breakers)، ومحرك سياق متعدد المصادر (`context/`)، ونظام سلاسل تنفيذ (`chain/`) بعقد Runner موحّد (`core/runner.py` + `runners/`).

المشروع مرّ بإعادة هيكلة عميقة (سلسلة مهام T-0xx موثقة في تعليقات الكود و`config.yaml`) أدخلت: جذر تركيب `AppContext`، سياق جلسة لكل اتصال WS (`SessionContext`)، ناقل أحداث `EventBus`، سجل تنفيذ `ExecutionRegistry` مع `RunTicket` (سياسة تشغيل واحد + إلغاء تعاوني)، بوابة موافقات `ApprovalGate`، مدير نقاط استرجاع `CheckpointManager`، وفهرس مشروع مقلوب `ProjectIndex`. توجد حزمة اختبارات حقيقية (**103 ملف اختبار**: 52 unit / 25 integration / 5 contracts / 4 goldens + fakes/fixtures/frame_harness).

**أهم المخاطر المعمارية المكتشفة (تفصيلها في §7):** الخلط بين الأوضاع في مسار العرض (البذرة الخلفية لـ BUG-01)، غياب fallback على مسار البث المباشر رغم وجود `stream_with_fallback` جاهز وغير موصول (BUG-02 جزئي)، حلقة إعادة محاولة غير محدودة في `providers/use_ai.py`، بث زائف في `providers/genspark.py`، وثغرة قائمة التجاهل `test---results` (BUG-04).

---

## 1. P1a — خريطة المستودع ومسؤوليات الوحدات

### 1.1 جذر المستودع

| مسار | نوع | مسؤولية | ملاحظات |
|---|---|---|---|
| `server.py` (2,613L) | كود منفَّذ | نقطة الدخول: Flask routes + WS handler + التركيب في `main()` (L2326) | 28 مسار HTTP (L590–L1222) + `ws_handler` (L2213) |
| `worker.py` (433L) | كود منفَّذ | مستهلك قائمة عمل Redis Streams لوضع dispatch=worker | `resolve_dispatch_mode` يُقرأ من server.py أيضًا |
| `config.yaml` (191L) | تهيئة | كل مفاتيح التشغيل (انظر §5.3) | لا أسرار داخله حاليًا؛ أمثلة api_key معلّقة (L184–L191) |
| `actions/` (5 ملفات) | كود منفَّذ | تنفيذ الأفعال: ملفات/أوامر/جلسات/تحليل ردود | §4 |
| `providers/` (11 ملفًا) | كود منفَّذ | تجريد المزودين + Pool + قواطع + ميزانية/سعة | §3 |
| `context/` (14 ملفًا + `sources/`) | كود منفَّذ | محرك السياق متعدد المصادر + فهرس + ميزانية توكنز | §3.4 |
| `chain/` (23 ملفًا) | كود منفَّذ | سلاسل التنفيذ: planner/router/executor/strategies/agent_loop/bridge | §4.3 |
| `core/` (13 ملفًا) | كود منفَّذ | الهيكل الأساسي: AppContext, SessionContext, EventBus, ExecutionRegistry, ApprovalGate, CheckpointManager, Runner protocol, backends, lease | §1.2 |
| `runners/` (4 runners) | كود منفَّذ | تنفيذات عقد Runner: direct/agent/chain/delegate | §2.2 |
| `prompts/` | كود + قالب | `templates.py` (build_prompt حسب الوضع) + `web_system.md` | §4.1 |
| `static/` | كود منفَّذ (متصفح) | `app.js` + `index.html` + CSS — الواجهة كاملة | §2.4 |
| `tests/` (103 ملفًا) | اختبارات | unit(52)/integration(25)/contracts(5)/goldens(4) + fakes + frame_harness.py | أصل مهم لـ P6/P8 |
| `docs/` | وثائق | خطط المراحل + runbooks + هذه الوثيقة (`docs/engineering/`) | |
| `test-results/` و `test---results/` | بيانات/أرشيف | **كلاهما موجود بالجذر**؛ الثاني (triple-dash) أرشيف QA خارجي | جوهر BUG-04 — §5.2 |
| `sessions/`, `data/` | بيانات وقت تشغيل | جلسات JSON، بيانات محلية | |
| `agents_rules/`, `newskells/`, `improvements/`, `examples/`, `scripts/`, `src/`, `public/` | مواد مساعدة/مخلفات | ليست في مسار التنفيذ الرئيسي | مرشح دين تقني — §7.5 |

### 1.2 وحدات `core/` (العمود الفقري بعد إعادة الهيكلة)

| ملف | أصناف رئيسية | مسؤولية |
|---|---|---|
| `core/app_context.py` (137L) | `AppContext` (L91)، `ProjectHandle` (L44)، `StaleHandleError` (L39) | جذر التركيب: مزود نشط، تبديل موديل/مشروع مع إبطال handles قديمة (`invalidate` L53, `ensure_valid` L60) |
| `core/session_context.py` (141L) | `SessionContext` (L57) | حالة لكل اتصال WS: `fm` (L82)، `cmd_runner` (L87)، `switch_project` (L91)، `active_provider` (L108)، `binding_banner` (L116)، `close` (L121) |
| `core/events.py` (189L) | `EventBus` (L111) + أحداث `RunStarted/StepProgress/ApprovalRequested/RunFinished/RoutingDecided/BudgetChanged` (L64–L99) | نشر/اشتراك مع history لكل run (256 حدثًا افتراضيًا، L120) وقفل RLock لكل run (`_lock_for` L171) |
| `core/execution.py` (346L) | `RunTicket` (L87)، `RunBusyError` (L76)، ExecutionRegistry | سياسة تشغيل واحد لكل مشروع، إلغاء تعاوني (`cancel` L159)، heartbeat (L169)، حالات نهائية (`finish` L177) |
| `core/approval.py` (286L) | `ApprovalGate` (L139)، `ApprovalRequest` (L93)، `Verdict` (L117) | طلب/حل الموافقات (`request` L179, `resolve` L206) + سجل تدقيق (`audit_entries` L231) + وضع تفاعلي (`_interactive` L238) |
| `core/checkpoint.py` (557L) | `CheckpointManager` (L162)، `SnapshotEntry` (L84)، `Conflict` (L115)، `RestoreReport` (L133) | لقطات content-addressed (`snapshot` L182, `_store_blob` L280)، أختام seal (L244)، استرجاع مع كشف تعارضات |
| `core/runner.py` | بروتوكول `Runner` + `RunRequest`/`RunResult`/`EventStream` + ثوابت أحداث | العقد الموحّد الذي تنفذه runners/ الأربعة |
| `core/backends.py` / `backends_redis.py` | مصانع backend (memory / Redis Streams) | `backends_from_config` يُقرأ من `config.yaml` مفتاح `backend:` (L131) |
| `core/lease.py` | حجز per-project (SET NX PX) | لوضع dispatch=worker |
| `core/project_memory.py` | `ProjectMemoryStore` | ذاكرة مشروع دائمة (أوامر memory_* في WS) |
| `core/strategy.py` | أدوات استراتيجية مشتركة | مساند لـ chain/strategies |

### 1.3 وحدات `actions/`

| ملف | مسؤولية | نقاط ارتساء |
|---|---|---|
| `actions/file_manager.py` (317L) | قراءة/كتابة/حذف آمنة داخل workspace | `IGNORE_DIRS` L27–L31 (**يحتوي `test-results` — L30 — وليس `test---results`** ← دليل BUG-04)؛ كتابة ذرّية fsync+`os.replace`؛ write hooks (T-049)؛ `_resolve` → `resolve_workspace_path`؛ `MAX_FILE_SIZE=500KB`؛ نسخ احتياطي إلى `.webdev_backups/` (نسخة لكل ملف + ZIP كامل، حد 5) |
| `actions/response_parser.py` (253L) | تحويل رد الموديل إلى actions | أنماط ` ```FILE: ` / ` ```CMD ` / ` ```EDIT: ` + **fallback يحوّل أي code-block إلى create_file** (L131–L169، جذر BUG-01) + استخراج `[OPTIONS]` |
| `actions/command_runner.py` (259L) | تنفيذ أوامر مقيّد | shlex + حظر معاملات shell (`&&`,`|`,`;`,`>` — L82–L89) + قوائم SAFE/DANGEROUS + إخفاء أسرار البيئة + retry أُسّي |
| `actions/session_manager.py` (189L) | جلسات JSON | حفظ ذرّي fsync؛ **إعادة كتابة الملف كاملًا عند كل رسالة** (ملاحظة أداء §7.4)؛ تنظيف 30 يومًا |

### 1.4 معيار «الكود المنفَّذ»

المجلدات المصنفة «كود منفَّذ» أعلاه هي ما يستورده `server.py`/`worker.py` تعديًا (تحقق TIER A عبر خرائط import). `src/`, `public/`, `examples/`, `newskells/`, `improvements/`, `agents_rules/` **لا تظهر في أي import** من مسار التنفيذ — تُعامل كمواد مساعدة/مخلفات (بند دين تقني مرشح FND في P3e).

---

## 2. P1b — تدفقات وقت التشغيل

### 2.1 دورة حياة WebSocket

1. **اتصال:** المتصفح `initWebSocket` (`static/app.js` L143) → الخادم `ws_handler` (`server.py` L2213) ينشئ `SessionContext` ويربط `_WSAdapter` (موقع `ws.send` الوحيد) بـ `EventBus`.
2. **حلقة الاستقبال:** `ws_handler` يقرأ `ws.receive`، يفك JSON، ويمرر لـ `_handle_ws_message` (L1714) الذي يوزع حسب `type`: `ping`, `message`, `apply_action`, `apply_all_actions`, `execute_plan`, `cancel_agent`, `cancel_run`, `agent_approval_response`, `chain_message`, `chain_approval_response`, `chain_cancel/status`, `confirm_path_action`, `rollback_run/file`, `resume_scan/run`, `discard_run`, `list_runs`, `delegate_*`, `memory_*`.
3. **إغلاق:** كتلة `finally` في `ws_handler` تستدعي `sctx.close()` (`core/session_context.py` L121) — تنظيف حتمي.
4. **إعادة الاتصال (عميل):** `app.js` L143+ يعيد الاتصال تلقائيًا بعد 3 ثوانٍ عند `onclose`.

**ملاحظة (مرشح FND):** فرع `cancel_run` يمرر `ensure_ascii=False` كوسيط ثانٍ لـ `sctx.send` (`server.py` L2085–L2088) بينما بقية الاستدعاءات تمرر إطارًا واحدًا — يتطلب تحقق توقيع `sctx.send` في P3 (ثقة C2).

### 2.2 دورة حياة طلب AI — `_dispatch_chat_message` (`server.py` L1285)

المسار الكامل لرسالة `{type:"message", text, mode}`:

1. **كشف المسارات:** path detection (قابل للتخطي بـ `skip_path_detection`) → قد يرسل إطار `path_detected_options`.
2. **جمع السياق:** `gather_message_context` (`context/facade.py`، الاستدعاء عند `server.py` L1381) → (mentioned_files, user_text_with_files, project_context).
3. **التوجيه الذكي:** `request_router.route(...)` — **محروس بـ `mode != "chat"`** (L1401): وضع chat لا يمر عبر السلاسل أبدًا.
4. **مسار الـ Agent:** `if agent_tools and mode in ("build", "edit", "chat", "plan")` (L1512) — **كل الأوضاع** تدخل حلقة الـ agent عند توفر agent_tools:
   - `_agent_send_fn` (L1523–L1529) يستخدم `provider_pool.send_with_fallback` ✅ (fallback موجود هنا).
   - نهاية الحلقة: `parser.parse(full_response)` (L1594) ثم — **بغضّ النظر عن الوضع** — إذا وُجدت actions يُرسل إطار `"plan"` بها (L1605–L1611). ← نصف الدليل الخلفي لـ BUG-01.
5. **المسار المباشر (fallback):** يُبنى `RunRequest` ويُنفَّذ عبر `RUNNERS["direct"]` (L1632+) مع `stream_fn=lambda p,h,s: sctx.active_provider().stream(p,h,s)` (L1656–L1658) — **بلا fallback على البث** رغم وجود `stream_with_fallback` في `providers/pool.py` L320 ← دليل BUG-02.
6. **العرض النهائي المباشر:** `if mode in ("plan","build","edit") and actions:` → إطار `plan` (L1698)؛ **وإلا** إطار `"done"` (L1706–L1711) **الذي يظل يتضمن `actions`** حتى في وضع chat ← النصف الثاني من BUG-01 خلفيًا.

### 2.3 البث (Streaming)

- **الخادم:** `runners/direct.py` — `DirectRunner.run` (قراءة كاملة): started → فحوص إلغاء → بوابة موافقة → بث chunks مع فحص إلغاء لكل chunk → finished؛ لا استثناءات تتسرب.
- **العميل:** `handleWSMessage` (`app.js` L179) يوزع `start/chunk/done/plan/error/action_result/task_progress/project_switched/path_detected_options/chain_*`؛ `appendStreamChunk` (L928) يعيد **رسم الرسالة كاملة عند كل chunk** مع تحليل قنوات وتلوين syntax (مخاطرة أداء §7.4)؛ `finalizeStreamMessage` (L964) **يعرض شريط actions متى كانت `data.actions` غير فارغة بغضّ النظر عن الوضع** (~L1027–L1030) ← النصف الأمامي من BUG-01.

### 2.4 دورة حياة الجلسة

- إنشاء/تحميل/حذف عبر REST: `/api/sessions` (L873)، `/api/session/<id>` (L882/L918)، `/api/session/new` (L905)، `/api/clear` (L858).
- التخزين: `actions/session_manager.py` — JSON لكل جلسة، حفظ ذرّي، إعادة كتابة كاملة لكل رسالة، تنظيف > 30 يومًا.
- ربط الجلسة بالمشروع: بصمة sha256 لمسار المشروع (12 حرفًا) مع سياسات `warn/fork/block` (`config.yaml` L86–L88، الافتراضي warn_only=true) — البانر يُحقن عبر `SessionContext.binding_banner` (L116).

### 2.5 الإقلاع والتركيب — `main()` (`server.py` L2326)

الترتيب: قراءة config → `_resolve_default_provider` (قيمة config تتغلب) → تهيئة مزودي الـ fallback مسبقًا في الـ pool (L2517–L2530: genspark/deepseek/…) → `ApprovalGate` (علم `auto_execute`) → plugins → planner (`planner_from_config`) → `chain_bridge` → retention GC (`.ai_runs`) → `agent_tools`. أسماء backend/planner/dispatch المجهولة = **فشل إقلاع صاخب** (سياسة موثقة `config.yaml` L104–L144).

**تصحيح انجراف سياق (قاعدة 0.2):** الدالتان `_process_ai_chat` و`_safe_ws_send` المذكورتان في CONTEXT **لم تعودا موجودتين** — استُبدلتا أثناء إعادة الهيكلة بـ `_dispatch_chat_message` + `_WSAdapter`/`sctx.send` (تحقق grep كامل على server.py).

---

## 3. Provider Architecture (Out of Scope)

The Provider subsystem is intentionally excluded from this engineering review.

No implementation review, performance review, security review, architecture review, roadmap planning, task generation or QA planning should spend time analyzing Provider internals unless explicitly requested.

Only its public interfaces may be referenced when necessary.
### 3.1 العقد الأساسي — قراءة كاملة

**`providers/base.py` (451L، قراءة كاملة):**
- `BaseProvider` (ABC): `send` / `stream` / `is_available` تجريدية؛ `ProviderCapabilities`؛ `ProviderRequest`/`ProviderResponse`.
- **تصنيف أخطاء كامل:** قابلة لإعادة المحاولة (`ProviderRateLimitError`, `ProviderTimeoutError`, `ProviderTransientError`) مقابل غير قابلة (`ProviderAuthError`, `CreditExhausted`, `ContextTooLarge`, `Refusal`) — أساس منطق الـ pool.
- **`MockProvider` بأعطال مبرمجة** موجود داخل base.py — أصل جاهز لاختبارات P6 (مزودون محاكَون).

**`providers/registry.py` (63L، قراءة كاملة):** سجل أصناف بسيط + نسخة عامة (global instance).

**`providers/pool.py` (388L، قراءة كاملة):**
- `CircuitBreaker`: عتبة 3 أعطال، cooldown أساس 30s → سقف 600s (أُسّي)، الحالة تُشتق كسولًا من الطوابع الزمنية (CLOSED/OPEN/HALF_OPEN).
- `send_with_fallback` (L291–L318): يجرب السلسلة بالترتيب ويسجل نجاح/فشل في القواطع — **موصول** بمسار الـ agent (`server.py` L1523–L1529).
- `stream_with_fallback` (L320–L353): **موجود لكنه غير موصول** بالمسار المباشر (`server.py` L1656–L1658 يستدعي `active_provider().stream` مباشرة) ← جوهر ما تبقى من BUG-02.
- ترتيبات `_QUALITY_RANK` / `_COST_RANK` لاختيار السلسلة.

### 3.2 المزودان الأكثر استخدامًا — قراءة معمّقة

**`providers/use_ai.py` (687L — قراءة L1–L400 + خريطة دوال كاملة):** المزود الافتراضي (`config.yaml` L6: `default_provider: "use_ai"`). WebSocket نحو use.ai؛ إدارة pool حسابات بقفل threading (`_load/_save_accounts` L455/L463، `_find_ready_account` L475، `_register_fresh_account` L558، تسجيل تلقائي حتى 5 حسابات — config L178–L179). **مخاطرة حرجة:** `stream()` (يبدأ L140) يحوي حلقة `while True` (L174) **بلا حد أقصى للمحاولات** — تُنهك الحسابات وتعيد التسجيل والمحاولة مع نوم 3s؛ مرشح FND قوي لـ P3c (ثقة C2 — يحتاج تتبع كامل لمسارات الخروج).

**`providers/genspark.py` (380L — skim موجّه):** `stream` (L348–L356) **بث زائف**: يستدعي `send()` كاملًا ثم يقسّم الرد إلى chunks بطول 50 حرفًا — زمن أول-بايت = زمن الرد الكامل (مرشح FND لـ P3b).

### 3.3 بقية المزودين — **مصرَّح بأنها skim** (واجهة عامة + شذوذات فقط)

| ملف | حجم | الملاحظ من الـ skim |
|---|---|---|
| `providers/deepseek.py` (232L) | skim | `DeepSeekProvider`: `send` (L76) / `stream` (L163) / `get_remaining_calls` (L229)؛ **`_generate_fake_ip()` (L34)** — توليد IP زائف لتجاوز حدود المعدل (شذوذ هشاشة/امتثال، مرشح FND) |
| `providers/alle_ai.py` (270L) | skim | حسابات من ملف خارج الشجرة `new_providers/ALLe-ai/alle_ai_accounts.json` (L20–L22 — مسار غير موجود بالمستودع)؛ `_fresh_login(email, password)` (L53)؛ `stream` (L254) قصير — يبدو مبنيًا على send (تحقق مؤجل، C3) |
| `providers/openai_shelby.py` (209L) | skim | **أسرار مضمّنة حرفيًا في الكود**: `PLAY_INTEGRITY_TOKEN = [REDACTED — providers/openai_shelby.py:L24]`، `COOKIES = [REDACTED — providers/openai_shelby.py:L26]` (انتحال عميل ChatGPT Android — `USER_AGENT` L28). **مرشح FND أمني S2** لـ P3d |
| `providers/budget.py` (183L) | skim | `AccountAwareBudget` (L82): `check()` → `BudgetSnapshot` (L27: `can_chain` L35, `can_afford` L39, `best_provider_for` L43)، `reserve_for_chain` (L146)، `get_fallback_order` (L167)؛ ترتيب `_COST
