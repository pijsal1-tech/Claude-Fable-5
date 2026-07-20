<div align="center">

# 🚀 WebDev AI Editor

### محرر كود ذكي يعمل بالذكاء الاصطناعي — مستوحى من Antigravity

**يقرأ مشروعك • يفهم الكود • يعدل الملفات • ينفذ الأوامر — تلقائياً**

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Web_Server-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real_Time-010101?style=for-the-badge&logo=socketdotio)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

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
| 🔄 **4 مزودي AI** | Genspark, DeepSeek, AlleAI, UseAI |
| 💬 **Real-time Streaming** | ردود AI تظهر حرف بحرف عبر WebSocket |
| 🛡️ **Backup تلقائي** | نسخة احتياطية قبل أي تعديل |
| 📋 **إدارة جلسات** | حفظ واستعادة محادثات سابقة |

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
cd editor_v2

# تثبيت المكتبات
pip install flask flask-sock websockets requests

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

---

## 🧩 المكونات الرئيسية

### 1. 🤖 مزودي الذكاء الاصطناعي (Providers)

4 مزودي AI مجانيين — لا يحتاجون API Keys:

| المزود | الموديلات | المميزات |
|--------|----------|----------|
| **Genspark** | Claude Sonnet 5, GPT-4o, Gemini 2.5 Pro | Streaming ✗, Parallel ✓, 200K context |
| **DeepSeek** | DeepSeek Chat, R1 | Streaming ✓, Parallel ✓, 64K context |
| **AlleAI** | Claude, GPT, Gemini | Streaming ✓, Parallel ✓, 128K context |
| **UseAI** | Gateway models | Streaming ✓, Auto-registration, 200K context |

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
editor_v2/
├── 🖥️  server.py                    # الخادم الرئيسي (Flask + WebSocket)
├── 📋  config.yaml                  # إعدادات المشروع
│
├── 🎨  static/                      # الواجهة الأمامية
│   ├── index.html                   # الصفحة الرئيسية
│   ├── app.js                       # منطق الواجهة (63KB)
│   └── style.css                    # التصميم (39KB)
│
├── 🤖  providers/                   # مزودي الذكاء الاصطناعي
│   ├── base.py                      # العقد الأساسي + MockProvider
│   ├── genspark.py                  # Genspark (Claude, GPT, Gemini)
│   ├── deepseek.py                  # DeepSeek Chat
│   ├── alle_ai.py                   # AlleAI
│   ├── use_ai.py                    # UseAI (Browser Bridge)
│   └── registry.py                  # سجل المزودين
│
├── ⚙️  actions/                     # الإجراءات
│   ├── file_manager.py              # إدارة ملفات المشروع
│   ├── command_runner.py            # تنفيذ أوامر الطرفية
│   ├── response_parser.py           # تحليل ردود AI
│   └── session_manager.py           # إدارة الجلسات
│
├── 📝  prompts/                     # قوالب البرومبتات
│   ├── web_system.md                # System Prompt
│   └── templates.py                 # قوالب Plan/Build/Edit/Chat
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
└── 📂  sessions/                    # كود مخزن الجلسات (البيانات خارج git)
```

---

## 🧪 الاختبارات

```bash
# الفحص الكامل — نفس بوابات CI حرفيًا (mypy + البوابات البنيوية + pytest)
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
```

---

## 🔒 الأمان

| الميزة | التفاصيل |
|--------|----------|
| 🛡️ **Backup تلقائي** | ZIP كامل قبل أي تعديل |
| 🚫 **Path Traversal Protection** | يمنع `../` والمسارات المطلقة |
| ⚠️ **Command Approval** | خيار طلب موافقة قبل تنفيذ أوامر |
| 📏 **Size Limits** | حدود على حجم الملفات والمجلدات |
| 🔐 **Binary File Rejection** | يرفض الملفات غير النصية |

---

## 🤝 المساهمة

### إضافة مزود AI جديد

1. أنشئ ملف في `providers/` يرث من `BaseProvider`
2. نفّذ `send()` و `stream()` و `is_available()`
3. سجّله في `main()` بـ `register_provider()`

### إضافة عميل (Agent) جديد

1. أنشئ مجلد في `agents_rules/` باسم التخصص
2. أضف ملف `.md` بالـ system prompt
3. العميل يتم اكتشافه تلقائياً

### إضافة استراتيجية Chain جديدة

1. أضف builder function في `chain/strategies.py`
2. أضف condition في `chain/orchestrator.py`
3. أضف tests في `tests/test_orchestrator.py`

---

## 📜 الرخصة

هذا المشروع للاستخدام الشخصي والتعليمي.

---

<div align="center">

**صُنع بـ ❤️ بواسطة Belal**

*مستوحى من Antigravity IDE — لأن كل مطور يستحق أدوات ذكية مجاناً*

</div>
