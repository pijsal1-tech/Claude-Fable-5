<div align="center">

# 🚀 WebDev AI Editor

### محرر كود ذكي يعمل بالذكاء الاصطناعي — مستوحى من Antigravity

**يقرأ مشروعك • يفهم الكود • يعدل الملفات • ينفذ الأوامر — تلقائياً**

[![Version](https://img.shields.io/badge/Version-1.0.0--rc.1-blue?style=for-the-badge)](core/version.py)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Web_Server-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real_Time-010101?style=for-the-badge&logo=socketdotio)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![CEV](https://img.shields.io/badge/CEV_Audit-99%2F100_GO-brightgreen?style=for-the-badge)](docs/engineering/RELEASE_READINESS_REPORT.md)

</div>

---

## 📋 نظرة عامة

**WebDev AI Editor** هو محرر كود يعمل عبر المتصفح، يتصل بعدة مزودي ذكاء اصطناعي (AI Providers) **مجاناً** بدون API Keys. يقرأ مشروعك الحقيقي من نظام الملفات، يفهم بنية الكود، ويقدر ينشئ ملفات جديدة أو يعدل ملفات موجودة أو ينفذ أوامر — كل ده من واجهة ويب أنيقة.

### ✨ ما يميز هذا المشروع

| الميزة | الوصف |
|--------|-------|
| 🆓 **مجاني بالكامل** | يعمل مع مزودي AI مجانيين — لا يحتاج API Keys |
| 📂 **وصول حقيقي للملفات** | يقرأ ويعدل ملفات مشروعك فعلياً |
| 🔗 **Chain System** | يقسّم المهام المعقدة لخطوات ذكية تلقائياً |
| 🧠 **21 عميل متخصص** | من bug analyzer لـ architect لـ security auditor |
| 🔄 **8 مزودي AI** | Genspark, DeepSeek, AlleAI, UseAI, You.com, Perplexity, Blackbox, OpenAI Shelby |
| 💬 **Real-time Streaming** | ردود AI تظهر حرف بحرف عبر WebSocket |
| 🛡️ **Backup تلقائي** | نسخة احتياطية قبل أي تعديل |
| 📋 **إدارة جلسات** | حفظ واستعادة محادثات سابقة |
| 🖥️ **غلاف سطح مكتب** | تغليف Windows exe بنقرة مزدوجة (PyInstaller + pywebview) |
| 🧩 **نظام إضافات** | استراتيجيات خارجية عبر entry points ببوابة تحقق وحجر صحي |
| 🪝 **خطّافات المالك** | hooks بعقد «تشديد-فقط» (pre_command / post_write / post_run) |
| 🔍 **بحث دائم مفهرس** | فهرس بحث دائم عبر الجلسات مع تحديث تزايدي |
| 🩺 **تشخيص وإعدادات** | `/api/diagnostics` + `/api/settings` — قراءة فقط مُطهَّرة |
| 🔐 **Workspace Trust** | قرار ثقة صريح لكل مجلد قبل التنفيذ |
| 🔔 **فحص تحديث opt-in** | `/api/update-check` — معطَّل افتراضيًا، صفر phone-home |
| 🎨 **ثيمات + رموز تصميم** | 4 ثيمات (dark/light/monokai/high-contrast) مبنية على design tokens (`static/themes/tokens.css`) |
| ✅ **مُدقَّق بالكامل (CEV)** | برنامج تدقيق شامل 12 بوابة — بطاقة 99/100 + إقرار جاهزية GO (عقد localhost) |

---

## 🏗️ المعمارية

```
┌─────────────────────────────────────────────────────────────┐
│                    🌐 Browser (Frontend)                     │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │  Chat UI   │  │ File Tree  │  │  Code Preview/Edit   │  │
│  └─────┬──────┘  └────────────┘  └──────────────────────┘  │
│        │ WebSocket                                           │
├────────┼────────────────────────────────────────────────────┤
│        ▼                                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              🖥️ server.py (Flask + Sock)              │   │
│  │                                                       │   │
│  │  message ──→ FileManager.read ──→ build_prompt ──→ AI │   │
│  │  chain_message ──→ ChainBridge ──→ SmartOrchestrator  │   │
│  │  apply_action ──→ FileManager.write / CommandRunner   │   │
│  └──────┬──────────────┬──────────────┬─────────────────┘   │
│         │              │              │                       │
│  ┌──────▼────┐  ┌──────▼────┐  ┌─────▼──────┐              │
│  │ Providers │  │  Actions  │  │   Chain    │              │
│  │ (4 AIs)   │  │ (Files,   │  │ (Smart    │              │
│  │           │  │  Commands,│  │  Task      │              │
│  │           │  │  Parser)  │  │  Splitting)│              │
│  └───────────┘  └───────────┘  └────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 التشغيل السريع

### المتطلبات
- Python 3.10+
- pip

### التثبيت

```bash
# استنساخ المشروع
git clone <repo-url>
cd <project-root>

# تثبيت مكتبات التشغيل (القائمة القانونية — TSK-713)
pip install -r requirements.txt

# تشغيل السيرفر
python server.py --project ./my_project --port 5000
```

### إعداد بيئة التطوير (Dev Setup)

```bash
# تثبيت أدوات التطوير والاختبار
pip install -r requirements-dev.txt

# تشغيل الفحص الكامل (types + tests)
./scripts/check.sh

# أو تشغيل الاختبارات فقط
python -m pytest
```

### الاستخدام

```bash
# فتح مشروع محدد
python server.py --project D:/projects/my_website

# تحديد مزود AI معين
python server.py --project . --model genspark:claude-sonnet-5

# تغيير البورت
python server.py --port 8080
```

ثم افتح المتصفح على: **http://127.0.0.1:5000**

### 🖥️ نسخة سطح المكتب (Windows)

بدل المتصفح: غلاف نافذة أصلية بنقرة مزدوجة —

```bash
python desktop.py --project ./my_project      # تشغيل مباشر
# أو تغليف exe كامل:
pyinstaller desktop.spec                       # الناتج: dist/WebDevAIEditor/
```

التفاصيل الكاملة (بناء/تغليف/استكشاف أخطاء/قناة التحديث):
`docs/desktop/WINDOWS_BUILD.md`.

---

## 🧩 المكونات الرئيسية

### 1. 🤖 مزودي الذكاء الاصطناعي (Providers)

8 مزودي AI مجانيين — لا يحتاجون API Keys:

| المزود | الموديلات | المميزات |
|--------|----------|----------|
| **Genspark** | Claude Sonnet 5, GPT-4o, Gemini 2.5 Pro | Streaming ✗, Parallel ✓, 200K context |
| **DeepSeek** | DeepSeek Chat, R1 | Streaming ✓, Parallel ✓, 64K context |
| **AlleAI** | Claude, GPT, Gemini | Streaming ✓, Parallel ✓, 128K context |
| **UseAI** | Gateway models | Streaming ✓, Auto-registration, 200K context |
| **You.com** | 21 موديل | سكربت ميداني ديناميكي عبر `_NEW_PROVIDERS` |
| **Perplexity** | 44 موديل | سكربت ميداني ديناميكي عبر `_NEW_PROVIDERS` |
| **Blackbox** | 24 موديل | سكربت ميداني ديناميكي عبر `_NEW_PROVIDERS` |
| **OpenAI Shelby** | gpt-5-3-high / mini / pro | ChatGPT Mobile Gateway — المزود الافتراضي في السجل |

**تبديل المزود أثناء الاستخدام**: من القائمة في الواجهة أو عبر WebSocket.

### 2. 📂 مدير الملفات (FileManager)

```python
# يتعامل مع مشروعك الحقيقي
fm = FileManager("D:/projects/my_app")
fm.read_file("src/app.py")           # قراءة ملف
fm.write_file("src/new.py", code)    # إنشاء ملف
fm.edit_file("src/app.py", old, new) # تعديل جراحي
fm.scan_project()                     # مسح المشروع
fm.get_project_tree()                 # شجرة الملفات
fm.create_full_backup()               # نسخة احتياطية
```

**ذكاء الملفات:**
- يتجاهل تلقائياً: `node_modules`, `.git`, `__pycache__`, `dist`
- يقرأ 30+ نوع ملف نصي
- حد أقصى 500KB للملف الواحد
- Backup تلقائي قبل أي تعديل

### 3. 🔗 نظام السلاسل الذكية (Chain System)

أقوى ميزة في المشروع — يحل مشكلة الملفات الكبيرة والمشاريع المعقدة:

#### كيف يعمل؟

```
طلب المستخدم ──→ SmartOrchestrator
                      │
                      ▼
              تحليل التعقيد (5 أبعاد):
              • حجم الملف (عدد الأسطر)
              • عدد الملفات
              • الترابط بين الملفات
              • تعقيد الطلب
              • مستوى المخاطرة
                      │
                      ▼
              اختيار الاستراتيجية:
              ├── Direct (بسيط → خطوة واحدة)
              ├── ContextWindow (متوسط → خطوتين)
              ├── ChunkChain (ملف كبير → تقسيم)
              ├── MapReduce (ملفات كثيرة → موازي)
              └── Pipeline (معقد → analyze→plan→execute→review)
                      │
                      ▼
              ChainExecutor (تنفيذ + retries + budget)
```

#### الاستراتيجيات الخمسة

| الاستراتيجية | متى تُستخدم | عدد الخطوات |
|-------------|-------------|-------------|
| **Direct** | ملف صغير + طلب بسيط | 1 |
| **ContextWindow** | ملف متوسط (200-600 سطر) | 2 |
| **ChunkChain** | ملف كبير (600+ سطر) | N+2 |
| **MapReduce** | مجلد بملفات كثيرة | N+2 |
| **Pipeline** | طلب معقد أو خطير | 3-4 |

#### مسح مجلد كامل 📂

```javascript
// من الـ Frontend
ws.send(JSON.stringify({
    type: "chain_message",
    text: "حلل المشروع ده وأصلح الأخطاء",
    folder_path: "D:/projects/my_app"
}));
```

**ذكاءات المسح:**
- يتجاهل `node_modules`, `.git`, `__pycache__`, `dist`, `build`...
- يقرأ 40+ امتداد نصي (py, js, ts, vue, go, rs, java...)
- يرتب الملفات بالأهمية: **كود أولاً → HTML/CSS → config → docs**
- حدود: 50 ملف max / 200KB per file / 2MB total

### 4. 🧠 نظام العملاء (Agent System)

21 عميل متخصص، كل واحد عنده prompt مخصص:

| العميل | التخصص | المرحلة |
|--------|--------|---------|
| `code_analyzer` | تحليل جودة الكود | analyze |
| `bug_analyzer` | اكتشاف وإصلاح الأخطاء | analyze |
| `api_analyzer` | تحليل APIs والتكاملات | analyze |
| `architect` | التصميم المعماري | plan |
| `backend_dev` | تطوير الباكند | execute |
| `frontend_dev` | تطوير الفرونتند | execute |
| `db_designer` | تصميم قواعد البيانات | plan |
| `security_auditor` | مراجعة أمنية | review |
| `performance_optimizer` | تحسين الأداء | review |
| ... | +12 عميل إضافي | متنوع |

**Fallback ذكي بـ 3 مستويات:**
1. 🔍 يبحث في `agents_rules/` عن prompt مخصص
2. 📋 يرجع لـ base prompts (analyze/plan/execute/review)
3. 🔄 يستخدم prompt افتراضي عام

### 5. ⚡ محلل الردود (Response Parser)

يفهم 3 صيغ من ردود AI:

```markdown
<!-- إنشاء ملف جديد -->
```FILE: src/app.py
print("hello world")
```

<!-- تعديل جراحي -->
```EDIT: src/app.py
<<<< OLD
print("hello")
====
print("hello world")
>>>> NEW
```

<!-- تنفيذ أمر -->
```CMD
npm install express
```
```

### 6. 📋 إدارة الجلسات (Session Manager)

- حفظ تلقائي لكل محادثة
- استعادة جلسات سابقة
- Crash-safe: كل رسالة تُحفظ فوراً
- تبديل بين مشاريع مختلفة

---

## 💬 بروتوكول WebSocket

### الرسائل الواردة (Client → Server)

| Type | Payload | الوظيفة |
|------|---------|---------|
| `message` | `{text, mode}` | رسالة عادية للـ AI |
| `chain_message` | `{text, folder_path?, file_path?, strategy?}` | تشغيل chain ذكي |
| `chain_cancel` | `{reason?}` | إلغاء chain نشط |
| `chain_status` | `{}` | حالة chain النشط |
| `list_runs` | `{}` | كل الـ runs في السجل (نشطة ومنتهية) |
| `cancel_run` | `{run_id, reason?}` | إلغاء تعاوني لـ run محدد بمعرّفه |
| `apply_action` | `{action}` | تطبيق إجراء واحد |
| `apply_all_actions` | `{actions[]}` | تطبيق كل الإجراءات |
| `execute_plan` | `{actions[]}` | تنفيذ خطة معتمدة |
| `ping` | `{}` | فحص الاتصال |

### الرسائل الصادرة (Server → Client)

| Type | الوظيفة |
|------|---------|
| `start` | بداية رد AI |
| `chunk` | جزء من الرد (streaming) |
| `done` | انتهاء الرد + actions + options |
| `plan` | خطة تحتاج موافقة |
| `chain_started` | بداية chain + عدد الخطوات |
| `chain_step` | تحديث خطوة (running/success/error/skipped) |
| `chain_finished` | انتهاء chain + budget |
| `chain_cancelled` | تم إلغاء chain |
| `runs_list` | `{runs: [{id, mode, state, started_at, is_cancelled, cancel_reason, finished_at}]}` |
| `cancel_run_result` | `{run_id?, acknowledged, error?}` — error: `not_found` \| `missing_run_id` |
| `busy` | run نشط بالفعل — يحمل `active_run` بمعرّفه |
| `folder_scanned` | ملخص مسح المجلد |
| `project_switched` | تم تبديل المشروع |
| `error` | رسالة خطأ |
| `pong` | رد على ping |


### 🌐 سطح REST (مختارات)

السطح كامل مجمَّد باختبار عقد (`tests/unit/test_rest_blueprints.py`) —
أي توسيع يحتاج قرارًا موثَّقًا. أبرز النقاط:

| Endpoint | Method | الوظيفة |
|----------|--------|---------|
| `/api/info` | GET | معلومات المشروع + المزود + رقم الإصدار |
| `/api/diagnostics` | GET | حزمة تشخيص مُطهَّرة (بيئة/تبعيات/مقاييس/إضافات) |
| `/api/settings` | GET | الإعدادات الفعالة — whitelist مُطهَّر (لا أسرار/مسارات) |
| `/api/permissions` | GET | سياسة الأوامر والأدوات الحية |
| `/api/trust` | GET/POST | قراءة/تسجيل قرار ثقة المجلد |
| `/api/update-check` | GET | فحص تحديث يدوي (opt-in — معطَّل افتراضيًا) |
| `/api/capacity` | GET | سعة صادقة من CapacityModel |
| `/api/metrics/runs` | GET | عدّادات + p50/p95 لمدد الـ runs |

---

## 🎨 الواجهة (Frontend)

واجهة ويب عربية أنيقة تشمل:

| المكون | الوصف |
|--------|-------|
| 💬 **Chat Panel** | محادثة مع AI بتقنية streaming |
| 📂 **File Tree** | شجرة ملفات المشروع مع استعراض |
| 🔧 **Mode Selector** | أوضاع: Chat / Plan / Build / Edit |
| 🤖 **Model Picker** | تبديل بين مزودي وموديلات AI |
| 📋 **Session History** | استعراض واستعادة جلسات |
| ✅ **Plan Review** | مراجعة وموافقة على خطط التعديل |
| ⚡ **Quick Replies** | اقتراحات ذكية بعد كل رد |

---

## 📁 هيكل المشروع

```
<project-root>/
├── 🖥️  server.py                    # الخادم الرئيسي (Flask + WebSocket)
├── 🪟  desktop.py + desktop.spec    # غلاف سطح المكتب + مواصفة PyInstaller
├── 📋  config.yaml                  # إعدادات المشروع
│
├── 🎨  static/                      # الواجهة الأمامية
│   ├── index.html                   # الصفحة الرئيسية (+ favicon)
│   ├── app.js                       # نواة الواجهة (مُقسَّم — FI-07)
│   ├── js/app/                      # وحدات الواجهة المفصولة:
│   │   ├── 10_chat_ws_stream.js     #   قلب الدردشة/WS/البث
│   │   ├── 20_editor_files_terminal.js # المحرر/الملفات/التيرمنال
│   │   ├── 30_sessions_models_attachments.js # الجلسات/النماذج/المرفقات
│   │   ├── 40_panels.js             #   اللوحات (diagnostics/settings/...)
│   │   └── 90/91_*.js               #   بحث palette + ثقة المجلد
│   ├── style.css                    # التصميم (مُرمَّز بـdesign tokens)
│   ├── themes/                      # tokens.css + 4 ثيمات
│   └── icons/                       # favicon.svg + sprite.svg
│
├── 🤖  providers/                   # مزودي الذكاء الاصطناعي (8)
│   ├── base.py                      # العقد الأساسي + MockProvider
│   ├── genspark.py                  # Genspark (Claude, GPT, Gemini)
│   ├── deepseek.py                  # DeepSeek Chat
│   ├── alle_ai.py                   # AlleAI
│   ├── use_ai.py                    # UseAI (Browser Bridge)
│   ├── you_com.py                   # You.com (21 موديل)
│   ├── perplexity.py                # Perplexity (44 موديل)
│   ├── blackbox.py                  # Blackbox (24 موديل)
│   ├── openai_shelby.py             # OpenAI Shelby (gpt-5-3 family)
│   ├── pool.py + capacity.py        # تجميع + نموذج السعة
│   └── registry.py                  # سجل المزودين
│
├── ⚙️  actions/                     # الإجراءات
│   ├── file_manager.py              # إدارة ملفات المشروع
│   ├── command_runner.py            # تنفيذ أوامر الطرفية
│   ├── response_parser.py           # تحليل ردود AI
│   └── session_manager.py           # إدارة الجلسات
│
├── 📝  prompts/                     # قوالب البرومبتات
│   ├── core_system.md               # System Prompt — نواة عامة
│   ├── web_overlay.md               # طبقة تخصص الويب (تُركَّب فوق النواة)
│   └── templates.py                 # قوالب Plan/Build/Edit/Chat + التركيب
│
├── 🔗  chain/                       # نظام السلاسل الذكية
│   ├── models.py                    # ChainStep, ChainRun, Budget, Cancel
│   ├── executor.py                  # DAG Executor (retries + persistence)
│   ├── orchestrator.py              # Smart Orchestrator (5D complexity)
│   ├── strategies.py                # 5 استراتيجيات تقسيم
│   ├── bridge.py                    # Event→WS + folder scanner
│   ├── agent_loader.py              # تحميل 21 عميل
│   └── prompts/                     # base prompts (analyze/plan/execute/review)
│
├── 🧬  core/                        # نواة الخدمات (version، approval، hooks،
│                                    #   update_check، workspace_trust، backends، ...)
├── 🌐  routes/                      # blueprints سطح REST (meta/files/sessions/...)
├── 🧭  context/                     # محرك السياق + الفهرس الدائم
├── 🧩  examples/demo_strategy/      # إضافة مرجعية + دليل مؤلف الإضافات
│
├── 🧠  agents_rules/               # قواعد العملاء (21 تخصص)
│   ├── AGENTS.md                    # القواعد الرئيسية
│   ├── MICRO_WORKER_SYSTEM_PROMPT.md
│   ├── بحث/، بناء/، تخطيط/...      # مجلدات التخصصات
│   └── rules/, skills/, tools/      # قواعد ومهارات إضافية
│
├── 🧪  tests/                       # المجموعة الكاملة — العدد الحقيقي من CI
│   ├── unit/                        # وحدات (محرك السياق، الفهرس، الجلسات، ...)
│   ├── integration/                 # تكامل (WS، السلاسل، التنفيذ المتوازي، ...)
│   ├── contracts/                   # عقود المزودين (ProviderContractMixin)
│   ├── goldens/                     # مخرجات مثبتة (parity السياق)
│   └── fixtures/ + fakes/           # مشروع عيّنة + FakeProvider
│
├── ⚙️  .github/workflows/ci.yml     # CI: check.sh + coverage ratchet
│
├── 📂  sessions/                    # كود مخزن الجلسات (البيانات خارج git)
│
└── 📚  docs/                        # التوثيق (engineering/ سجلات الحوكمة،
                                     #   desktop/ دليل البناء وقائمة المالك)
```

---

## 🧪 الاختبارات

```bash
# الفحص الكامل — نفس بوابات CI حرفيًا
# (mypy + flake8 pyflakes + ~17 بوابة بنيوية + pytest)
./scripts/check.sh

# أو الاختبارات فقط
python -m pytest

# مع قياس التغطية (أرضية coverage_baseline.txt تصاعدية-فقط)
python -m pytest --cov=. --cov-report=term
python scripts/coverage_ratchet.py check
```

> **مبدأ الصدق (R-703):** لا أرقام اختبارات مكتوبة يدويًا هنا — العدد
> الحقيقي والنتيجة الحقيقية مصدرهما تشغيل CI الفعلي
> (`.github/workflows/ci.yml`) أو `./scripts/check.sh` محليًا.
> التغطية محروسة بـ ratchet تصاعدي-فقط: لا تنخفض تحت الأرضية
> المسجلة في `coverage_baseline.txt` أبدًا.

### 🛡️ بوابات الجودة في `check.sh` (مختارات)

| البوابة | ماذا تحرس |
|---------|-------------|
| **mypy** | أنواع ساكنة على providers/chain/core/context/sessions/routes + server/desktop |
| **flake8 — F-rules** | صفر استيرادات/متغيرات ميتة (pyflakes فقط — D-18) |
| **SafeReader boundary** | لا قراءات خام في context/ (حجب الأسرار) |
| **import cycles** | صفر دورات استيراد (AST-based) |
| **color tokens** | لا ألوان خام خارج static/themes/ |
| **injection guard** | أسوار حماية في كل طبقات الـprompts |
| **routing corpus** | مصفوفة التوجيه المثبّتة لا تنحرف |
| **agent manifest** | 21 عميلًا مُجرودين بـschema — لا ملفات يتيمة |

---

## ⚙️ الإعدادات

### `config.yaml`

```yaml
# المزود الافتراضي — config هو المصدر الوحيد (T-051):
# السيرفر يقرأ هذه القيمة عند الإقلاع؛ --model يتقدّم عليها فقط.
default_provider: "use_ai"

# إعدادات المزودين
providers:
  genspark:
    model: "claude-sonnet-5"
  deepseek:
    model: "deepseek-chat"
  use_ai:
    model: "gateway-claude-sonnet-5"
    auto_register: true
    auto_register_max: 5

# عام
auto_execute: false          # طلب إذن قبل الأوامر
backup_before_edit: true     # نسخة احتياطية قبل التعديل
max_context_files: 15        # أقصى ملفات في السياق
force_command_approval: false  # إلزام الموافقة على كل أمر — غياب المفتاح = true (راجع «حدود النشر»)

# أقسام اختيارية (معطَّلة افتراضيًا — أمثلة معلَّقة في نهاية config.yaml):
# hooks:    خطّافات المالك «تشديد-فقط» (pre_command/post_write/post_run)
#           — فشل pre_command ⇒ حجب الأمر (fail-closed)؛ لا تمنح موافقة أبدًا.
# updates:  فحص تحديث يدوي opt-in (check_enabled + manifest_url)
#           — الافتراضي معطَّل ⇒ صفر اتصال شبكة (لا phone-home).
```

---

## 🔒 الأمان

| الميزة | التفاصيل |
|--------|----------|
| 🛡️ **Backup تلقائي** | ZIP كامل قبل أي تعديل |
| 🚫 **Path Traversal Protection** | يمنع `../` والمسارات المطلقة |
| ⚠️ **Command Approval** | خيار طلب موافقة قبل تنفيذ أوامر |
| 🔒 **Force Command Approval** | راية `force_command_approval` — موافقة إلزامية على كل أمر (TSK-502) |
| 📏 **Size Limits** | حدود على حجم الملفات والمجلدات |
| 🔐 **Binary File Rejection** | يرفض الملفات غير النصية |
| 🔐 **Workspace Trust** | قرار ثقة مستخدم صريح لكل مجلد (fail-closed عند الغياب) |
| 🪝 **Owner Hooks** | خطّافات «تشديد-فقط»: ترفع الصرامة ولا تستطيع منح موافقة أبدًا |
| 🕵️ **لا phone-home** | صفر اتصالات صادرة افتراضيًا — فحص التحديث opt-in يدوي فقط |

### 🚧 حدود النشر والأمان (Deployment Limits — TSK-502 / NF-16 / TSK-737)

هذه الأداة مصمّمة كـ **أداة تطوير محلية لمستخدم واحد على
localhost** — ليست خدمة ويب للنشر العام. الحدود المعمارية التي
يجب فهمها قبل أي تشغيل:

1. **لا مصادقة على REST/WebSocket إطلاقًا**: كل endpoints
   (`/api/run`، `/api/write/...`، `/api/restore/...`، الخ) مفتوحة
   لأي طرف يصل للمنفذ — من يصل للمنفذ يملك مشروعك وطرفيّتك.
   والأخطر (نموذج تهديد TSK-737 — T4): **قناة الموافقة نفسها
   WS غير مُصادَق** — نظير شبكي متصل يوافق على أفعاله بنفسه،
   فلا تقسية سلوكية تعوّض الربط المكشوف.
2. **الربط غير loopback مرفوض كوديًا (TSK-737 — القرار 9)**:
   `--host 127.0.0.1` (الافتراضي) يقصر الوصول على جهازك؛ أي
   `--host` خارج loopback (127/8 + `::1` + `localhost`) **يرفض
   الإقلاع** برسالة شارحة — لم يعد تحذيرًا نصيًا بل إنفاذًا
   كوديًا fail-closed. للوصول عن بُعد الآمن: نفق SSH
   (`ssh -L 5000:127.0.0.1:5000 …`)، أو VPN، أو reverse-proxy
   بمصادقة — كلها تنتهي إلى loopback فتعمل مع الافتراضي بلا
   أي راية. لمن يُصرّ رغم الخطر: راية `--unsafe-expose-network`
   الصريحة — وحتى معها تُقفَل مسارات: `POST /api/permissions`
   (403)، ووكلاء ACP (رفض)، ويُقسَر `force_command_approval=true`
   (لا يمكن قلبه من config أو overrides).
3. **مواضع تنفيذ بلا موافقة تفاعلية (افتراضيًا)**: مسارات
   `/api/run` و`/api/run-file` وapply-actions تنفّذ بـ
   `need_approval=False` — حارس `DANGEROUS_COMMANDS` الساكن
   (rm/del/format/sudo/…) هو الخط الوحيد عندها. مقبول على
   localhost؛ **غير كافٍ لأي سيناريو آخر**.
4. **الحل: راية `force_command_approval`** في `config.yaml`
   (TSK-617 — قرار D-1: **غياب المفتاح أو تعذّر قراءة config =
   `true`** — الافتراض البرمجي آمن؛ القيمة الصريحة تُحترم):
   - `false` (صريح في config المشحون — تعطيل واعٍ لـ localhost) —
     السلوك التاريخي كما هو (توافق كامل).
   - `true` — **كل أمر** من أي مسار (REST/apply) يمر ببوابة
     الموافقة التفاعلية إلزاميًا — حتى الأوامر المصنّفة آمنة
     وحتى مع `auto_approve`. فعّلها دائمًا عند أي ربط خارج
     `127.0.0.1` أو عند العمل على مشروع حساس.
   الأوامر الخطيرة (`DANGEROUS_COMMANDS`) تتطلب موافقة دائمًا
   في الحالتين — الراية توسّع البوابة، لا تضيّقها أبدًا.
5. **الأسرار**: ملفات `.env` وأشباهها محجوبة عن الموديل عبر
   SafeReader، ومتغيرات البيئة الحساسة تُطمس قبل تنفيذ الأوامر —
   لكن هذا لا يغني عن البندين 1–2 أعلاه.
6. **نموذج التهديد الكامل (TSK-737 — القرار 9)**: موثّق في
   `docs/engineering/DEVELOPMENT_TASKS.md §TSK-737` (T1–T6) —
   خلاصته: لا مصادقة تُلحَق ترقيعًا بأداة localhost؛ الوصول
   عن بُعد = طبقة خارجية تنتهي إلى loopback. ملاحظة CSRF
   (T6): endpoints الـ JSON تتطلب `Content-Type: application/json`
   ولا CORS headers تُرسل — دفاع ضمني قائم ضد متصفح على
   جهاز المالك نفسه.

---

## 🤝 المساهمة

### إضافة مزود AI جديد

1. أنشئ ملف في `providers/` يرث من `BaseProvider`
2. نفّذ `send()` و `stream()` و `is_available()`
3. سجّله في `main()` بـ `register_provider()`
4. أضف اختبار عقد في `tests/contracts/` (يرث `ProviderContractMixin`)

> ملاحظة أنواع: عند التحميل الديناميكي بـ`module_from_spec` استخدم
> حارس None (`if spec is None or spec.loader is None: raise ImportError`)
> — بوابة mypy تغطي `providers/` كاملًا (استثناء وحيد: `openai_shelby.py`).

### إضافة استراتيجية كإضافة خارجية (Plugin) 🧩

بدون لمس كود المضيف — عبر entry points:

1. حزمة Python تعرّف class يطابق عقد `chain/plugin_api.py`
   (`strategy_name` + `routing_hints` + `build(ctx)` — `PluginContext`
   هو السطح الوحيد المرئي للإضافة).
2. سجّلها في `pyproject.toml` تحت group باسم `webdev_ai.strategies`.
3. عند الإقلاع: بوابة تحقق ثلاثية (import/shape/dry_run) — الإضافة
   الفاسدة تُحجَر (quarantine) ولا تُسقط المضيف أبدًا؛ الحالة تظهر في
   `/api/diagnostics` (مفتاح `plugins`).

المثال الكامل خطوة-بخطوة: `examples/demo_strategy/README.md`.

### إضافة عميل (Agent) جديد

1. أنشئ مجلد في `agents_rules/` باسم التخصص
2. أضف ملف `.md` بالـ system prompt
3. العميل يتم اكتشافه تلقائياً

### إضافة استراتيجية Chain جديدة

1. أضف builder function في `chain/strategies.py`
2. أضف condition في `chain/orchestrator.py`
3. أضف tests في `tests/unit/test_routing_matrix.py` (مصفوفة التوجيه المثبّتة)

---

## 🔢 سياسة الإصدارات (TSK-716)

- **المصدر الوحيد لرقم الإصدار**: `core/version.py` (`__version__`) —
  يظهر في ترويسة الإقلاع، وراية `python server.py --version`،
  وحقل `version` في `/api/info`.
- **SemVer**: `MAJOR.MINOR.PATCH[-rc.N]`
  - `patch`: إصلاحات بلا تغيير عقد.
  - `minor`: ميزات متوافقة (دفعات P1/P2).
  - `major`: أي كسر عقد (أشكال JSON / إطارات WS / عقد localhost).
- **لاحقة `-rc.N`** كانت تبقى حتى تحقق Windows (قرار D-8-ب) —
  **أُلغي الشرط بقرار مالك D-19 (2026-08-04)**: إصدار `v1.0.0` النهائي
  لتثبيت Baseline مرجعي. الإصدار الحالي: `1.0.0`.
- **الوسم**: `git tag vX.Y.Z[-rc.N]` بعد إغلاق كل دفعة إنتاج
  (بوابة الإغلاق: `check.sh` ALL GREEN).

---

## 📜 الرخصة

انظر ملف `LICENSE` في جذر المستودع (© 2026 pijsal1-tech — جميع
الحقوق محفوظة حاليًا؛ قابلة للاستبدال برخصة مفتوحة بقرار مالك موثق).
الاستخدام الحالي: شخصي وتعليمي.

---

<div align="center">

**صُنع بـ ❤️ بواسطة Belal**

*مستوحى من Antigravity IDE — لأن كل مطور يستحق أدوات ذكية مجاناً*

*حالة الجودة: برنامج CEV مُغلق بإقرار جاهزية GO (99/100) — انظر `docs/engineering/RELEASE_READINESS_REPORT.md`*

</div>
