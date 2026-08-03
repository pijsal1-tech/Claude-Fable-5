# 🤖 GEMINI.md — قواعد مشروع AI_MDULE

> **📌 اقرأ الملف ده قبل ما تلمس أي سطر في المشروع.**
> بيخليك تفهم المشروع وتشتغل صح من أول لحظة.

---

## 🗣️ اللغة والأسلوب

- **كلمني بالمصري دايماً** — مش فصحى
- **استخدم Emojis** عشان الوضوح
- **مختصر ومباشر** — بلاش حشو
- **كود → code blocks** مع اسم اللغة دايماً

---

## 🏗️ المشروع — AI Orchestration System

### الـ Stack:
| الطبقة | التقنية |
|--------|---------|
| **API** | FastAPI (`api/app.py`) |
| **Providers** | OpenAI, Gemini, Together, Anthropic, Groq + DeepSeek Browser |
| **Vector DB** | Qdrant (`localhost:6333`) |
| **Embedding** | `paraphrase-multilingual-mpnet-base-v2` (local) |
| **Task Queue** | Celery + Redis |
| **Config** | `.env` + `config/settings.py` |
| **Browser Automation** | SeleniumBase (`uc=True`) |

### الـ Flow:
```
Query → classify domain → RAG retrieve → Provider generate → log + feedback
```

---

## ⚙️ Provider Pattern — إلزامي

### كل provider لازم:
1. **يورث من** `BaseProvider` في `providers/base.py`
2. **يرجع** `ProviderResponse` (مش string!)
3. **ينفذ:** `ask()` + `generate()` + optional `search()`
4. **يتسجل في** `providers/manager.py` → `_init_providers()`

### إضافة provider جديد — خطوتين بس:
```python
# 1. في manager.py → _init_providers()
"deepseek": DeepSeekProvider,

# 2. في key_map (لو محتاج API key)
"deepseek": self._settings.deepseek_api_key,
```

### DeepSeek Provider — خاص:
- **Legacy (Browser):** بيشتغل بـ SeleniumBase — موجود في `providers/deepseek_provider.py`
- **🆕 Pure Requests:** `deepseek_chat.py` — بدون browser — Android headers + WASM PoW
- الـ `ask()` و `generate()` في Browser version لازم يستخدموا `asyncio.to_thread()` عشان Selenium sync

---

## 🔒 قواعد إلزامية — Non-Negotiable

### ⛔ ممنوع:
- **مسح أي ملف** أو استبداله كامل — تعديل بس
- **Hardcoded API Keys** — كلها في `.env`
- **تعديل Auth/Security** بدون طلب صريح
- **كسر Provider Interface** — `ProviderResponse` غير قابل للتغيير

### ✅ إلزامي:
- **Git Commit قبل أي تعديل كبير**
- **DRY تماماً** — صفر تكرار
- **كل إعداد جديد في** `config/settings.py` و `.env.example`
- **try/except لكل DOM interaction** (Selenium)
- **الـ README.md = سجل حي** — أضف بس، لا تمسح
- **v2 (32 model) يشتغل بالتوازي مع كل خطوة** — `ask_32_models.py` يشتغل دايماً بالتوازي مع أي registration script

### 🤝 Playwright + curl_cffi معاً (ERNIE Pattern):
- **Playwright** → Baidu calls (passport/conf + email_login + send_code + reg/email) — نفس session اللي جنت jnmq  
- **curl_cffi** → خدمات خارجية (Emailnator, temp-mail) — مش Baidu
- **سبب العزل:** server بيربط passport tokens بـ browser session بتاع jnmq

---

## 📁 خريطة الملفات المهمة

| الملف/المجلد | الوظيفة |
|-------------|---------|
| `api/app.py` | FastAPI entry point |
| `orchestrator/` | منطق التنسيق بين الطبقات |
| `providers/base.py` | ⚠️ الـ BaseProvider — لا تعدله |
| `providers/manager.py` | إدارة الـ providers + fallback |
| `providers/deepseek_provider.py` | Browser automation provider (legacy) |
| `config/settings.py` | كل الإعدادات من `.env` |
| `config/domains.yaml` | تعريف الـ domains |
| `embedding/` | Qdrant + sentence-transformers |
| `ingestion/` | Pipeline للـ PDF/CSV/URL/OCR |
| `ديب سيك/deepseek_chat.py` | 🆕 Pure requests client — Android headers + WASM PoW + pre-fetch |
| `ديب سيك/refresh.py` | 🆕 Android v3 — curl_cffi token refresh (بدون browser!) |
| `ديب سيك/accounts_deepseek.json` | قاعدة بيانات الحسابات |
| `monitor.py` | 🧠 المراقب المركزي (13 providers) |
| `shared/` | 📦 مكتبة مشتركة: ui + io + delay |
| `.Genspark_😎/genspark_register.py` | 🆕 Azure AD B2C + CAPTCHA Multi-Solver (Groq/Pollinations/OCR) + PKCE |
| `.Genspark_😎/genspark_master.py` | 🆕 Register + Login + Chat في سكريبت واحد |
| `ارينا/arena_register.py` | Arena CDP + _cdp_eval() + _mega_click() |
| `ارينا/arena_hybrid_login.py` | 🆕 Hybrid Login: pure requests + browser fallback — كلهم CDP (مش execute_script!) |
| `ارينا/refresh.py` | 🆕 Cookie injection refresh + hybrid_login fallback — متوافق مع monitor.py |
| `ارينا/test_click.py` | 🆕 اختبار 17 طريقة click — WINNER = CDP Runtime.evaluate |
| `ارينا/debug_login_btn.py` | 🆕 debug script لمعرفة الـ buttons الموجودة في أي صفحة |

---

## 🐛 قواعد SeleniumBase (DeepSeek)

### CSS Selectors الحالية:
```python
MSG_CONTAINER  = 'div.dad65929'        # ⚠️ Hashed — ممكن يتغير
REPLY_DONE_BTN = 'div.db183363.ds-icon-button'  # 5 أزرار = رد اكتمل
MESSAGE_INPUT  = 'textarea[placeholder="Message DeepSeek"]'
```

### قواعد ثابتة:
- `uc=True` = ضروري لتخطي Cloudflare
- بدون `user_data_dir` = أفضل (بيمنع تعارض Port)
- كل طلب = browser session جديد (مشكلة أداء معروفة)
- `input()` في production = خطر! (بيبلوك)

---

## 📝 لما تقول "حدث السجل" — البروتوكول الإلزامي الكامل

> **⛔ مفيش خطوة تتعدى بدون الخطوات دي كلها!**

### الخطوات بالترتيب:

**1️⃣ حدّث `README.md`** — أضف في:
- **سجل الإنجازات** → الجديد في الآخر
- **الملفات الجديدة** → لو في ملفات جديدة
- **سجل المشاكل** → `| #رقم | [TAG] | وصف | أعراض | سبب | حل | حالة |`
- **دروس مستفادة** → `| #رقم | [TAG] | الدرس | السياق |`

**2️⃣ حدّث `GEMINI.md`** — لو في قواعد جديدة أو patterns اتضافت

**3️⃣ اعمل Git Commit:**
```bash
git add -A
git commit -m "📚 [وصف التحديث]"
```

**4️⃣ ارفع على GitLab:**
```bash
git push origin master
```

**5️⃣ ابعتلي جدول التغييرات:**
| العنصر | ✅ اتضاف | ✏️ اتعدل | ❌ اتمسح |
|--------|----------|----------|----------|
| مثال   | حاجة جديدة | حاجة اتغيرت | حاجة اترمت |

**6️⃣ 🔍 مراجعة ذاتية (فيب كودج style) — قبل ما تبعت الرد:**
```
اسأل نفسك:
✅ هل README.md اتحدث صح؟
✅ هل GEMINI.md محتاج يتحدث؟
✅ هل الكود مش فيه تكرار (DRY)؟
✅ هل الـ git commit والـ push اتعملوا؟
✅ هل جدول التغييرات واضح ومكتمل؟
✅ هل في حاجة ممكن تكسر؟
لو جواب على أي سؤال = لأ → صلّح قبل ما تبعت!
```

**Tags:** `[API]` `[Script]` `[Config]` `[Security]` `[Performance]` `[Backend]` `[Debug]`

### ⚠️ قواعد إلزامية:
- ❌ مفيش أي حاجة تتمسح من README.md
- ✅ كل جديد يتضاف في آخر القسم المناسب
- ❌ مفيش تواريخ
- 🔢 ترقيم المشاكل تسلسلي GLOBAL

---

## 🚀 تشغيل المشروع

```bash
# Docker (الأسهل)
docker-compose up -d

# محلي
uvicorn api.app:app --host 0.0.0.0 --port 8000
# API على: http://localhost:8000
# Qdrant: http://localhost:6333
```

---

## 💡 نصائح للـ AI

- **لو شفت pattern متكرر** → حوّله لـ helper تلقائياً
- **لو لقيت bug محتمل** → قوله حتى لو مسألناش
- **لو التغيير ممكن يكسر حاجة** → حذّر قبل
- **قبل أي تعديل كبير** → `git add -A && git commit -m "📸 Backup"`
- **الـ ProviderResponse** = عقد ثابت، لا تكسره أبداً

---

## 🔄 أنماط التواصل — Communication Shortcuts

> **نفّذ تلقائي من غير ما تسأل:**

### 📌 "طلب اخر" (بأي صيغة):
- طلب جديد مستقل تماماً — **صفّر السياق** وابدأ من الأول
- مش شرط تنصيص — "طلب اخر" أو "طلب آخر" أو "request اخر" = نفس المعنى

### 📌 "كمل" أو "Continue":
- كمّل من آخر نقطة وقفت عندها — **مش تعيد شرح اللي فات**

### 📌 "حدث السجل":
- افتح `README.md` وأضف الإنجازات الجديدة بالتنسيق المحدد

### 📌 "نفذ كل حاجه انت صح":
- موافق 100% — **نفذ فوراً بدون مراجعة تانية**

### 📌 لما يبعتلك آراء متعددة (فيب كودج):
1. اعمل **جدول مقارنة** بين كل الآراء
2. رتّبهم **الأفضل للأضعف** مع التبرير
3. استخرج **أهم الثغرات**
4. **حدّث البلان** — واستنى موافقة قبل التنفيذ

### 📌 لما يبعت صورة/screenshot:
- حلل وافهم من السياق — **مش تسأل "عايز إيه؟"**

### 📌 لما يعطيك رأي أو قرار تقني (فيب كودج mode):
- **قوله 3 حاجات تلقائي:**
  1. ✅ إيه الكويس في القرار
  2. ⚠️ إيه المخاطر أو العيوب
  3. 💡 إيه البديل الأفضل لو في
- **ديما راجع قراراته** — مش بس تنفذ
- لو الرأي غلط → **قول بصراحة** حتى لو مسألناش
- **ملف المراجعة:** `VIBE_CODING_PROMPT.md` — فيه برومت جاهز

---

## 🧑💻 أسلوب زيزو في الشغل

### 🎯 طريقة التفكير:
- **بيفكر كـ Product Owner** — يوصف والـ AI ينفذ
- **بيشتغل بـ Phases** — مراحل واضحة ومرتبة
- **بيسأل "إيه رأيك"** — عايز رأي صريح مش مجرد تنفيذ

### 💬 طريقة التواصل:
- **مصري 100%** — عامية مصرية طبيعية
- **مختصر** — يكتب الطلب في سطرين ويتوقع فهم كامل
- **حساس جداً لمسح الملفات** — ممنوع نهائياً

### ⚡ نصائح عملية:
- لو مش فاهم → **اسأل** مش تفترض
- الخلاصة في الآخر دايماً — سطرين كفاية
- لو في اقتراح → قدمه بدون ما يسأل

---

## 🔑 معلومات ثابتة

### Telegram:
- **Chat ID:** `1124247595`
- **Bot Token:** `7875476610:AAEvfVPqV7mnuqK2aZcn0tAq9yfpgKHg7tU`
- **Bot Username:** `@sheets2025from_bot`

---

## 🏗️ مبادئ البنية (Architecture Principles)

### ⛔ Non-Negotiable:
- **DRY تماماً** — صفر تكرار. أي كود يتكتب مرة واحدة بس
- **SSOT** — كل الإعدادات في مكان واحد: `config/settings.py`
- **SOLID** — مبادئ الخمسة بدون استثناء
- **Clean Architecture** — Domain → Application → Infrastructure

### ✅ إلزامي:
- **Config-driven** — أي إعداد جديد في `config/settings.py` + `.env.example`
- **Pure Functions** — دوال قابلة للاختبار منفردة
- **Backward-compatible** — أي تغيير جديد ميكسرش القديم

---

## 🚨 Red Flags — علامات تحذيرية

❌ **لو شفت أي حاجة من دول = توقّف فوراً:**
- تكرار نفس الكود في أكتر من مكان
- Hardcoded Values (أرقام/مفاتيح/مسارات مكتوبة يدوي)
- `except Exception: pass` بدون logging
- ملفات > 500 سطر بدون سبب
- dependencies مبعثرة وتشتيت السكربتات (أوامر الأتمتة يجب أن تكون Single File Doctrine)
- **OPSEC Header Mismatch:** خلط بصمات التشفير `Safari` مع هيدرات `Chrome` (بيعمل Block فوري)
- **Data Regex Parsing:** معالجة أكواد الدول أو الأرقام بالـ Regex اليدوي بدل المكتبات الثقيلة (زي `phonenumbers`)
- import بيجيب كل حاجة بدون `__all__`
- **مزج `f-string` مع `plain string` في JS code للـ CDP**: `f"...{{"` + `"..."` = `}}` في JS = Syntax Error صامت! الحل: `% formatting` أو string موحدة
- **`uc_open_with_reconnect`** في SeleniumBase: بيسبب browser exit. استخدم `uc_open` + `sleep(8)` بدله

---

## ✅ Quality Checklist — قبل كل تسليم

### Code Quality:
- [ ] **Test-Before-Talk (ممنوع التسليم الأعمى):** هل قمت بتشغيل الكود فعلياً وتأكدت من خروجه بـ Exit Code 0 قبل أن تبلغ المستخدم بالنجاح؟
- [ ] DRY: صفر تكرار
- [ ] SSOT: الإعدادات في `config/settings.py`
- [ ] Modular: فصل المسؤوليات واضح
- [ ] Type hints موجودة

### Security:
- [ ] مفيش API keys في الكود — كلها في `.env`
- [ ] Input validation موجود
- [ ] try/except شامل مع logging

### Python-Specific:
- [ ] `asyncio.to_thread()` لأي sync code داخل async
- [ ] `ProviderResponse` مش string
- [ ] لو provider جديد → مسجل في `manager.py`

### 🔥 Register Script — إلزامي قبل أي سكريبت تسجيل (Checklist):

> **⛔ مش هقبل register script بدون ما كل النقط دي تتحقق!**

#### 📝 التعليقات والأسلوب:
- [ ] كل تعليق في الكود **عربي كامل** — مفيش `# OTP timeout` لازم `# مهلة انتظار كود التحقق`
- [ ] `banner()` + `final_stats()` + `step()` **بالعربي** — مش إنجليزي
- [ ] `colorama` + **fallback** لو مش موجودة
- [ ] مفيش `print()` عادي من غير ألوان

#### ⚙️ Config و Constants:
- [ ] `LOOP_MODE` + `MAX_ACCOUNTS` + `DELAY_BETWEEN` + `OTP_TIMEOUT` كـ **module-level constants**
- [ ] `Config` dataclass بيستخدم الـ constants كـ defaults
- [ ] `--max`, `--loop`/`--no-loop`, `--delay`, `--timeout`, `--provider`, `--list`, `--count`, `--headless` في argparse

#### 📧 Email Providers:
- [ ] `EMAIL_PROVIDERS` list كاملة = كل اللي ممكن يتستخدم
- [ ] **كل provider في الـ list لازم يكون ليه class/function فعلية!** (مش بس اسم)
- [ ] الـ providers الفعلية الحالية:

| الاسم | الـ Class | المكتبة | الملاحظة |
|-------|---------|---------|----------|
| `emailnator` | `EmailnatorClient` | `curl_cffi` | Gmail aliases (dot/plus) |
| `mailtm` | `TempMailAPI` / `MailTmClient` | `requests` | دومينات متغيرة |
| `tempmail` | `TempMailOrgClient` | `curl_cffi` | temp-mail.org |
| `tempnet` | `TempNetClient` | `cloudscraper` | temporary-mail.net (Gmail) |
| `besttemp` | `BestTempClient` | `requests` | besttemporaryemail.com (Livewire) |
| `dropmailx` | `DropmailxClient` | `requests` | ridermail.shop domains |
| `mix` | دمج/rotation بين أكتر من واحد | — | بيلف عليهم بالتبادل |

#### 💾 accounts.json — حقول إلزامية:
- [ ] كل حساب لازم يكون فيه:
```json
{
  "email": "...",
  "password": "...",
  "cookies": {},
  "provider": "emailnator",
  "status": "active",
  "last_updated": "2026-03-19T08:24:44",
  "expires_in": 48
}
```
- [ ] `provider` = auto-detect من الدومين (`gmail.com`→`emailnator`, `ridermail.shop`→`dropmailx`, غير كده→`mailtm`)
- [ ] Atomic write: `.tmp` → `.replace()`

#### 🔄 Loop Mode:
- [ ] `LOOP_MODE = True` = **الـ default** — يفضل يشتغل لحد Ctrl+C
- [ ] `--no-loop` flag عشان يشتغل مرة واحدة
- [ ] `--max N` = حد أقصى في وضع التكرار
- [ ] `Ctrl+C` مملون: `⛔ اتوقف بـ Ctrl+C`

---

## 🆘 Rollback & Recovery — لو حاجة اتكسرت

### خطوات الاسترجاع:
```bash
# استرجاع ملف واحد من آخر commit آمن
git checkout HEAD -- providers/deepseek_provider.py

# استرجاع كل الملفات من آخر commit
git checkout HEAD -- .

# شوف آخر commits وارجع لأي واحد
git log --oneline -10
git checkout <commit-hash> -- .
```

### قبل ما تعمل أي تعديل كبير:
```bash
git add -A && git commit -m "📸 Backup before [وصف]"
```

### لو Qdrant مش شغال:
```bash
docker start qdrant
# أو
docker-compose up -d qdrant
```

### لو DeepSeek Browser مش بيفتح:
1. اقفل كل Chrome من Task Manager
2. احذف `deepseek_profile/` لو موجود
3. شغّل السكربت تاني

---

## 📋 `.env.example` — Template إلزامي

```env
# AI Providers
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
TOGETHER_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...

# DeepSeek (Browser — مش API)
DEEPSEEK_EMAIL=your@email.com
DEEPSEEK_PASSWORD=your_password_here

# Infrastructure
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_URL=redis://localhost:6379/0

# Config
DEFAULT_PROVIDER=openai
EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2
CLASSIFICATION_THRESHOLD=0.6
LOG_LEVEL=INFO
```

> ⚠️ **أي متغير جديد** لازم يتضاف هنا + في `config/settings.py`

---

## ⚡ الماستر برومت المختصر

```
تصرّف كـ Senior Architect. DRY + SSOT + Modular + Production-Ready.
ممنوع Hardcoded values — كل إعداد في Config.
قبل أي كود: افهم → اقترح → نفذ أصغر تغيير → اختبر → سجّل.
ممنوع مسح ملفات. Git Commit قبل وبعد.
الرد: المشكلة → الحل الأفضل (مع ليه) → كود نظيف → edge cases → خلاصة TL;DR.
```

---

## 🔍 النقد الذاتي — إلزامي في كل رسالة

> **📌 في نهاية كل رسالة فيها كود أو تعديل، راجع نفسك:**

```
🔍 نقد ذاتي:
1. ❌/✅ هل في dead code اتسابت؟
2. ❌/✅ هل في selectors/variables معرّفة ومش بتتستخدم؟
3. ❌/✅ هل كان ممكن أوصل للحل بخطوات أقل؟
4. ❌/✅ هل في تكرار (DRY violation)؟
5. ❌/✅ هل نسيت git commit أو تحديث السجل؟
6. ❌/✅ هل قمت باختبار الكود فعلياً (Execution Test) باستخدام أوامر التيرمينال وتأكدت من خلوه من أخطاء الـ Syntax قبل تقديم الرد؟ (ممنوع التسليم الأعمى أو التخمين).
```

### قواعد:
- **ممنوع تبعت رد فيه كود بدون نقد ذاتي في الآخر**
- **كن صريح** — لو غلطت قول "غلطت في X"
- **اذكر اللي كان ممكن يتعمل أحسن** حتى لو مسألناش

## 🔑 قاعدة الضغط الذهبية — لأي موقع React/Next.js

> **📌 مستفادة من Arena.ai — مؤكدة بـ test_click.py (17 method, 1 winner)**

### ⭐ القاعدة الأولى دايماً (قبل أي طريقة تانية):
```python
def cdp_eval(sb, js: str):
    """تشغيل JS في main world زي Chrome console — userGesture=True هو السر"""
    result = sb.driver.execute_cdp_cmd("Runtime.evaluate", {
        "expression": js,
        "returnByValue": True,
        "awaitPromise": False,
        "userGesture": True,   # ← SIR EL KALAM
    })
    return result.get("result", {}).get("value") if result else None

# الاستخدام (أسرع وأبسط click ممكن):
cdp_eval(sb, """
    (function() {
        const btn = Array.from(document.querySelectorAll('button'))
            .find(el => el.innerText.includes('Continue with email'));
        if (!btn) return false;
        btn.scrollIntoView({behavior:'instant', block:'center'});
        btn.click();
        return true;
    })()
""")
```

### ليه دي بس اللي اشتغلت؟

| الطريقة | السبب |
|--------|-------|
| `CDP Input.dispatchMouseEvent` | React مش بيسمعه |
| `ActionChains` (WebDriver) | بيمر بـ WebDriver layer |
| `sb.click() / uc_click()` | نفس WebDriver |
| `execute_script btn.click()` | **isolated world** — React مش فيه |
| ⭐ `Runtime.evaluate + userGesture=True` | **main world** + Chrome بيعاملها كـ user gesture حقيقي |

### ⚠️ القاعدة:
- أي زرار **React/Next.js مش بيستجبش** → أول حاجة جربها: `cdp_eval` + `userGesture=True`
- **مش** `execute_script` — دي بيشتغل في isolated world
- **مش** `dispatchMouseEvent` — React مش بيشوفه

---

## 🤖 SeleniumBase Pattern — قابل لأي موقع AI

> **📌 استخدم النمط ده مع أي موقع AI (DeepSeek / ChatGPT / Claude / Gemini...)**
> الفرق الوحيد = الـ Selectors في الأعلى.

### ⚙️ Template Selectors (خصّصها لكل موقع):
```python
# ─── تعريف الـ Selectors هنا فقط ─────────────────────────
SITE_URL       = "https://chat.deepseek.com/sign_in"   # رابط الموقع
LOGIN_BTN      = "a[href='/sign_in']"                  # زرار الدخول
EMAIL_INPUT    = "input[name='identifier']"            # حقل الإيميل
PASS_INPUT     = "input[type='password']"              # حقل الباسورد
SUBMIT_BTN     = "button[type='submit']"               # زرار Submit
MSG_INPUT      = "textarea[placeholder*='Message']"    # حقل الرسالة
REPLY_DONE     = "div.db183363.ds-icon-button"         # مؤشر انتهاء الرد
MSG_CONTENT    = "div.ds-markdown"                     # نص الرد
# ──────────────────────────────────────────────────────────
```

### 📐 القواعد الإلزامية (Non-Negotiable):
```python
# ✅ Dynamic Waits فقط — ❌ sleep() ممنوع نهائياً
sb.wait_for_element_visible(SELECTOR, timeout=15)
sb.wait_for_element_clickable(SELECTOR, timeout=10)
sb.wait_for_element_not_visible(LOADING, timeout=30)

# ✅ كل عملية في function مستقلة
def login(sb, email, password): ...
def send_message(sb, text): ...
def wait_for_reply(sb): ...
def get_reply_text(sb): ...

# ✅ try/except على كل DOM interaction
try:
    sb.click(SELECTOR)
except Exception as e:
    logger.error(f"فشل: {e}")
    return None

# ✅ uc=True لتخطي Cloudflare + Bot Detection
with SB(uc=True, headless=False) as sb:  # headless=True في production
    ...
```

### 🏗️ Template كامل جاهز:
```python
from seleniumbase import SB
import logging

logger = logging.getLogger(__name__)

# ─── Selectors (غيّرها حسب الموقع) ──────────────
SITE_URL    = "https://YOUR_AI_SITE.com"
EMAIL_INPUT = "input[type='email']"
PASS_INPUT  = "input[type='password']"
SUBMIT_BTN  = "button[type='submit']"
MSG_INPUT   = "textarea"
REPLY_DONE  = "button.done-indicator"   # مؤشر انتهاء الرد
MSG_CONTENT = "div.response-text"
TIMEOUT     = 15  # ثواني
# ──────────────────────────────────────────────────

def login(sb, email: str, password: str) -> bool:
    """تسجيل الدخول — يرجع True لو نجح"""
    try:
        sb.uc_open(SITE_URL)
        sb.wait_for_element_visible(EMAIL_INPUT, timeout=TIMEOUT)
        sb.type(EMAIL_INPUT, email)
        sb.type(PASS_INPUT, password)
        sb.click(SUBMIT_BTN)
        sb.wait_for_element_visible(MSG_INPUT, timeout=TIMEOUT)
        logger.info("✅ تسجيل دخول ناجح")
        return True
    except Exception as e:
        logger.error(f"❌ فشل تسجيل الدخول: {e}")
        return False

def send_message(sb, text: str) -> bool:
    """إرسال رسالة"""
    try:
        sb.wait_for_element_clickable(MSG_INPUT, timeout=TIMEOUT)
        sb.type(MSG_INPUT, text)
        sb.send_keys(MSG_INPUT, "\n")
        return True
    except Exception as e:
        logger.error(f"❌ فشل إرسال الرسالة: {e}")
        return False

def wait_for_reply(sb, timeout: int = 60) -> bool:
    """انتظر اكتمال الرد"""
    try:
        sb.wait_for_element_visible(REPLY_DONE, timeout=timeout)
        return True
    except Exception as e:
        logger.error(f"❌ انتهى الـ timeout: {e}")
        return False

def get_reply_text(sb) -> str | None:
    """اقرأ نص الرد"""
    try:
        sb.wait_for_element_visible(MSG_CONTENT, timeout=TIMEOUT)
        return sb.get_text(MSG_CONTENT)
    except Exception as e:
        logger.error(f"❌ فشل قراءة الرد: {e}")
        return None

def run_bot(email: str, password: str, prompt: str) -> str | None:
    """الدالة الرئيسية — تعمل login + send + wait + read"""
    with SB(uc=True, headless=False) as sb:
        if not login(sb, email, password):
            return None
        if not send_message(sb, prompt):
            return None
        if not wait_for_reply(sb):
            return None
        return get_reply_text(sb)
```

### 🔄 تكييف مع أي موقع AI — خطوتين:
```
1. غيّر الـ Selectors في الأعلى (CSS أو XPath)
2. عدّل wait_for_reply() حسب مؤشر الموقع:
   - Button Counting (DeepSeek)
   - aria-live region
   - element disappear (loading spinner)
   - text stability
```

### 🚨 Red Flags:
- ❌ `time.sleep()` في أي مكان = ممنوع
- ❌ Selector hardcoded في منتص الكود
- ❌ مفيش try/except على DOM interaction
- ❌ `headless=True` في development (صعب debug)

---

## 🆕 Patterns المتقدمة — اتعلمناها من Code Review

### ① @dataclass Config مع Validation — الأحدث والأنظف:
```python
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Config:
    """⚙️ SSOT — كل الإعدادات + validation تلقائي"""
    login_url: str    = "https://chat.deepseek.com/sign_in"
    email: str        = os.getenv("DEEPSEEK_EMAIL", "")
    password: str     = os.getenv("DEEPSEEK_PASSWORD", "")
    headless: bool    = os.getenv("DEEPSEEK_HEADLESS", "false").lower() == "true"
    timeout: int      = int(os.getenv("DEEPSEEK_TIMEOUT", "25"))
    enable_search: bool    = False
    enable_deepthink: bool = False
    reply_wait_secs: int   = 120
    reply_done_btns: int   = 5

    def __post_init__(self):
        """✅ بيتشيك تلقائياً — لو .env ناقص → يعرفك فوراً"""
        if not self.email:
            raise ValueError("❌ DEEPSEEK_EMAIL مش موجود في .env!")
        if not self.password:
            raise ValueError("❌ DEEPSEEK_PASSWORD مش موجود في .env!")

config = Config()
```

---

### ② setup_logging() — دالة منفصلة (مش basicConfig في module):
```python
import logging, sys

def setup_logging(level: str = "INFO") -> logging.Logger:
    """استدعيها في if __name__ == '__main__' بس — مش في module!"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("deepseek")

# في module:
log = logging.getLogger("deepseek")  # بدون basicConfig!

# في if __name__ == '__main__' بس:
if __name__ == "__main__":
    log = setup_logging("INFO")
```
> **⚠️ `basicConfig` في module = بيعمل override على logging بتاع FastAPI!**

---

### ③ DeepSeekSession — Session Reuse (10x أسرع!):
```python
class DeepSeekSession:
    """🎯 Login مرة واحدة → رسايل كتير — بدل 60 ثانية per request → 5 ثواني!"""
    def __init__(self):
        self.sb = None
        self._is_logged_in = False

    def __enter__(self):
        self.sb = SB(uc=True, headless=config.headless)
        self.sb.__enter__()
        navigate_to_login(self.sb)
        fill_credentials(self.sb)
        click_login(self.sb)
        if not verify_login(self.sb):
            raise RuntimeError("❌ فشل اللوجين!")
        self._is_logged_in = True
        return self

    def __exit__(self, *args):
        if self.sb:
            self.sb.__exit__(*args)

    def ask(self, message: str) -> str:
        if not self._is_logged_in:
            raise RuntimeError("❌ Session مش active!")
        return send_message_and_get_reply(self.sb, message)

# الاستخدام:
with DeepSeekSession() as s:
    r1 = s.ask("سؤال 1")
    r2 = s.ask("سؤال 2")
    r3 = s.ask("سؤال 3")
    # Login مرة واحدة بس! 🎉
```

---

### ④ Re-render Guard — حل StaleElement أثناء Streaming:
```python
# React بيعمل re-render → النص ممكن يقصر فجأة!
while True:
    current_text = get_latest_text(sb)
    if len(current_text) < sent_so_far:
        sent_so_far = 0   # DOM اتغير كامل → reset من الأول
    new_chunk = current_text[sent_so_far:]
    if new_chunk:
        print(new_chunk, end="", flush=True)
        sent_so_far = len(current_text)
```

---

### ⑤ JS Click — لتخطي CSS Hidden + Responsive Elements:
```python
# ⚠️ المشكلة: عنصر موجود في DOM بس parent بيه class "hidden md:flex"
# → seleniumbase بتعتبره hidden وبترمي exception!
# ✅ الحل: JS click بيتخطى كل visibility checks!

def js_click_combobox(sb, text: str = "Battle Mode") -> str | None:
    """
    يضغط على combobox بنصّه — بيتجاوز hidden CSS
    مفيد مع: Radix UI / shadcn / أي Tailwind responsive component
    """
    return sb.execute_script(f"""
        const combos = document.querySelectorAll('button[role="combobox"]');
        for (const btn of combos) {{
            if (btn.textContent.includes('{text}') && btn.offsetParent !== null) {{
                btn.scrollIntoView({{behavior: 'instant', block: 'center'}});
                btn.click();
                return 'clicked:' + btn.textContent.trim().slice(0, 30);
            }}
        }}
        // fallback: آخر combobox مرئي
        if (combos.length > 0) {{
            const last = combos[combos.length - 1];
            last.scrollIntoView({{behavior: 'instant', block: 'center'}});
            last.click();
            return 'fallback:' + last.textContent.trim().slice(0, 30);
        }}
        return null;
    """)
```

---

### ⑥ Radix UI Portal Dropdown — اختيار Option:
```python
# ⚠️ Radix UI / shadcn dropdowns:
# → لما تضغط combobox، الـ options بتظهر في <body> كـ Portal!
# → مش جوا الـ button نفسه!
# → لازم تدور على role="option" في role="listbox"

DIRECT_OPTION_XPATHS = [
    '//div[@role="option" and .//p[normalize-space(text())="Direct"]]',
    '//*[@role="option" and .//p[normalize-space(text())="Direct"]]',
    '//*[@role="listbox"]//*[normalize-space(text())="Direct"]',
    '//p[normalize-space(text())="Direct"]',   # آخر حل
]

# قاعدة ثابتة:
# ✅ بعد JS click على combobox → انتظر 0.8 ثانية → Portal يظهر
# ✅ بعدين ابحث عن role="option" في الـ listbox
# ❌ ممنوع تدور على "Direct" جوا الـ combobox button نفسه (Portal منفصل!)
```

---

## 🎓 Agent Learning Architecture — code_generator.py

> **📌 الـ Agent بيتعلم يكتب كود تلقائي من templates حقيقية بدل ما AI يكتب من الصفر.**

### الـ Flow:
```
HAR → تحليل auth_type → Template Compose (فوراً!) → AI Review (2K prompt)
                           ↓ (لو مفيش template)
                      AI Generation (26K prompt) ← fallback
```

### Template Registry (5 auth types):
```python
_TEMPLATE_REGISTRY = {
    "password":   ("ai21", "AI21_Maestro/ai21_register.py"),     # 669L
    "OTP":        ("mistral", "mistral/mistral_register.py"),     # 881L
    "session":    ("arena", "ارينا/arena_register.py"),
    "magic-link": ("you", "you.com/you.com_register.py"),         # 1223L
    "oauth":      ("zo", "zo.computer/zo.computer_register.py"),  # 901L
}
```

### CodeGenConfig:
```python
@dataclass
class CodeGenConfig:
    composer: str = "template"       # "template" أو "ai"
    teacher: str = "antigravity"     # الـ agent نفسه
    reviewers: list = [...]          # AI providers للمراجعة
    max_review_rounds: int = 2
    auto_fix: bool = True
    learn_from_errors: bool = True
```

### 3 حمايات (Guards):
| Guard | الوظيفة |
|-------|---------|
| 🛡️ **Length Guard** | لو auto-fix رجّع كود أقصر بـ 50%+ → يرجع الأصلي |
| 🛡️ **Template Protection** | لو template موجود (>200L) → يحفظ في `generated/` |
| 🎓 **AI Review** | `multi_ask()` بيسأل 6 providers بالتوازي (prompt 2K بدل 26K) |

### القواعد:
- ❌ ممنوع حذف أو تعديل الـ templates الأصلية (golden scripts)
- ✅ generated code يتحفظ في `generated/` subfolder
- ✅ الـ agent يتعلم من كل حساب ناجح (agent_memory.py)

---

### ⑦ shared/ Library — Import بدل Repeat:
```python
# ⚠️ بدل ما كل provider يكرر step/ok/fail/warn/human_delay/atomic_save:
from shared import step, ok, fail, warn, info, human_delay
from shared.io import atomic_save, load_accounts, upsert_account

# استخدام:
step(1, 5, "Registering...")
ok("Done!")
upsert_account("accounts.json", {"email": "x@y.com", "status": "active"})
```
> **📌 أي provider جديد يستخدم `shared/` — مفيش تكرار!**

---

### ⑧ ai_engine.py — File I/O & Flexible Model Selection:
```python
# ── قراءة السؤال من ملف نصي (بدل كتابته يدوي) ────────────────
# python ai_engine.py --input-file question.txt
# python ai_engine.py -f question.txt

# ── تحديد موديل/provider بالاسم ────────────────────────────────
# python ai_engine.py --models groq,ernie                   # providers بس
# python ai_engine.py --models groq:kimi-k2,ernie:EB50      # exact models

# ── حفظ الردود في ملفات ─────────────────────────────────────────
# python ai_engine.py --output-dir ./results                # مجلد الحفظ
# python ai_engine.py --output-format json                  # txt | json | both

# ── batch mode: كل سطر في الملف = سؤال مستقل ───────────────────
# python ai_engine.py --input-file questions.txt --mode batch --models groq
```

**الـ Helper Functions الجديدة:**
| الدالة | الوظيفة |
|--------|---------|
| `_read_input_file(path)` | قرأ ملف كـ prompt واحد — بيتجاهل `#` والفاضي |
| `_read_input_file_as_questions(path)` | قرأ ملف كـ list أسئلة (للـ batch) |
| `_parse_models(models_str)` | حوّل `"groq:kimi-k2,ernie"` لـ `[(provider, model)]` |
| `_save_output(results, dir, format)` | حفظ TXT + JSON بـ timestamp تلقائي |

**output file naming:**
```
output_YYYYMMDD_HHMMSS.txt          # askو multi mode
output_YYYYMMDD_HHMMSS_q001.txt     # batch mode (رقم السؤال في الاسم)
```

**قاعدة إلزامية:**
- ❌ `ThreadPoolExecutor` لازم يكون **global import** (مش local جوا block) — عشان batch و multi يستخدموه معاً!
- ✅ الـ BOM في ملفات Windows: استخدم `encoding='utf-8-sig'` في `open()` لتجنب `﻿` في أول السطر
- ✅ `ai_config.yaml` القسم `output:` بيتحكم في الإعدادات الافتراضية

---

### ⑨ REFRESH_LAYERS — Extensible Multi-Layer Refresh:
```python
# ── نمط قابل للتوسع لتجديد حسابات أي provider ─────────────
REFRESH_LAYERS = [
    ("Layer 0 — Token Validity Check", _layer0_check_token),  # ⚡ فوري
    ("Layer 1 — Magic Link",           _layer1_magic_link),   # 🕐 ~120s
    # ("Layer 2 — Browser Fallback",   _layer2_browser),      # 🐢 محجوز
]

# لإضافة layer جديد: سطرين بس!
# 1. اكتب _layerN_xxx(acc, sess) -> dict | None
# 2. أضفها في REFRESH_LAYERS
```

**القواعد:**
- كل layer = `function(acc, sess) -> dict | None`
- `dict` → نجح (ممكن `{"skip": True}` لو مش محتاج تجديد)
- `None` → فشل → روح للـ layer التاني
- `_detect_provider(email)` بيكتشف provider من الدومين تلقائياً
- `_save_accounts()` = Atomic write (`.tmp → .replace()`) — إلزامي

---

*آخر تحديث: v2.6 — REFRESH_LAYERS extensible pattern + accounts.json compliance*


---

## 🚫 الكلمات الفضفاضة — ممنوع استخدامها بدون سبب حقيقي

> **📌 دي كلمات الـ AI بيحبها جداً بس بتكون فاضية من غير محتوى حقيقي.**
> **⛔ ممنوع تستخدمهم إلا لو فيه دليل فعلي في الكود/الخطة.**

### الكلمات المحظورة:

`احترافي جداً` • `مستقر` • `متوازن` • `عملي` • `قابل للتخصيص` • `قابل للتكامل` • `بدون تعقيد` • `سهل الصيانة` • `محسّن للأداء` • `عالي الكفاءة` • `بديهي` • `سهل الاستخدام` • `تجربة مستخدم ممتازة` • `سلس` • `متجدد` • `مرن جداً` • `يتكيف بسرعة` • `ديناميكي` • `متعدد الاستخدامات` • `قابل للتطوير المستمر` • `حل ذكي قابل للتوسع` • `أداء عالي ومرونة ممتازة` • `فعّال` • `كفء` • `متطور` • `عصري` • `شامل` • `متكامل` • `قابل للتطبيق` • `نتائج ملموسة` • `قيمة مضافة` • `مؤثر` • `له صدى` • `عائد استثمار` • `رؤية واضحة` • `خطة محكمة` • `تفكير مستقبلي` • `واعد` • `منظم` • `قابل للفهم` • `قابل لإعادة الاستخدام` • `سهل الدمج` • `متين` • `Robust` • `يتحمّل الأعطال` • `Fault-tolerant` • `جاهز للمستقبل` • `Future-proof` • `خطوات تنفيذ` • `تقترح` • `قابل التوسع` • `اقتراحات` • `رأيك` • `احترافي` • `ابتكار` • `الأفضل` • `الأحسن` • `ذكي` • `مرن` • `ديناميكياً` • `مرونة عالية` • `الخلاصة` • `DRY` (بدون شرح كيف) • `قابل للصيانة` • `مركزي` • `معياري` • `كود نظيف` • `بدون تكرار`

### ✅ البديل الصح:

```
❌ "الكود نظيف وقابل للصيانة"
✅ "الكود مش فيه تكرار — do_auto بقى 12 سطر بدل 80"

❌ "حل ذكي قابل للتوسع"
✅ "بنضيف provider جديد بسطرين في manager.py"

❌ "أداء عالي ومرونة ممتازة"
✅ "Login مرة واحدة بدل 60 ثانية لكل request"
```

> **القاعدة:** بدل الوصف → قدّم **رقم، مثال، أو مقارنة قبل/بعد**.


---

## 🧠 آراء الـ AIs — قواعد مستخلصة (إلزامية)

> **📌 دي نتيجة مراجعة 5 AIs على `deepseek_register.py` — محفوظة كقواعد ثابتة للمستقبل.**

### 🏆 ترتيب الـ AIs حسب الجودة:

| # | الـ AI | أفضل اكتشاف | الضعف |
|---|-------|------------|-------|
| 🥇 | **Opt-Minus v3 (ChatGPT)** | `arguments[]` في JS = الوحيد الآمن | 357 سطر (شوية كتير) |
| 🥈 | **Claude** | تبسيط + DRY صح + 170 سطر | شال EmailnatorClient |
| 🥉 | **GPT-4 التفصيلي** | تحليل ممتاز (A-F) | الكود نفسه فيه f-string! |
| 4️⃣ | **Gemini** | reasoning كويس | أرادت ملفات منفصلة ❌ |

---

### 📋 قاعدة #1 — ملف واحد فقط لكل سكريبت

```
✅ سكريبت Python واحد فقط
✅ ملف accounts مجاور (txt)
❌ ممنوع: emailnator_client.py / utils.py / helper.py منفصلة
```

> **السبب:** التعقيد الزيادة بيكسر الصيانة — اللي يقدر يبقى في ملف واحد يفضل فيه.

---

### 📋 قاعدة #2 — `arguments[]` إلزامي في كل JS + نص

```python
# ❌ ممنوع نهائياً (JS injection + crash مع quotes):
sb.execute_script(f"el.value = '{text}'")
sb.execute_script(f"... uses '{variable}' ...")

# ✅ إلزامي دايماً (آمن 100% مع أي نص):
sb.execute_script("""
    document.querySelector(arguments[0]).value = arguments[1];
""", selector, text)
```

> **السبب:** لو الباسورد فيه `'` أو `"` → crash فوري. `arguments[]` ما بيتأثرش بأي character.

---

### 📋 قاعدة #3 — `pathlib` للـ accounts file (إلزامي)

```python
# ❌ ممنوع (بيتحفظ في CWD مش جنب السكريبت):
ACCOUNTS_FILE = "accounts_deepseek.txt"

# ✅ إلزامي (دايماً جنب السكريبت + resolve لـ symlinks):
from pathlib import Path
from dataclasses import field  # ← ضروري مع default_factory!

_BASE_DIR = Path(__file__).resolve().parent  # .resolve() بيحل symlinks
ACCOUNTS_FILE = str(_BASE_DIR / "accounts_deepseek.txt")
```

---

### 📋 قاعدة #4 — verify بعد كل `fast_type()`

```python
# بعد كل fast_type → تحقق robust + retry:
fast_type(sb, selector, text)
typed = sb.execute_script("""
    const el = document.querySelector(arguments[0]);
    return el ? el.value : "";   # ← ما بيكسرش لو العنصر مش موجود
""", selector)
if not typed or len(typed) < 3:
    log.warning("⚠️ retry بـ sb.type()")
    sb.clear(selector)
    sb.type(selector, text)
```

---

### 📋 قاعدة #5 — لا `except: pass` أبداً

```python
# ❌ ممنوع:
except Exception:
    pass

# ✅ إلزامي:
except Exception as e:
    log.debug(f"[تجاهل] {e}")  # على الأقل logging
```

---

### 📋 قاعدة #6 — `do_auto` = wrapper فقط (DRY)

```python
# ❌ ممنوع: do_auto تكرر كود do_register (80 سطر مكررة!)

# ✅ إلزامي: do_auto = 5 سطر بس
def do_auto(sb):
    client = EmailnatorClient()
    email = client.generate_email()
    if not email:
        log.error("❌ فشل توليد الإيميل!")
        return False
    return do_register(sb, email, config.DEFAULT_PASSWORD, auto_fetch=True)
```

---

### 📋 قاعدة #7 — `accept_checkboxes` لازم ترجع count + logging

```python
def accept_checkboxes(sb) -> int:
    count = sb.execute_script("""
        let c = 0;
        for (const cb of document.querySelectorAll('input[type="checkbox"]')) {
            const s = getComputedStyle(cb);
            if (s.display==="none" || s.visibility==="hidden") continue;
            if (cb.disabled) continue;  // ← من Gemini!
            if (!cb.checked) { cb.click(); c++; }
        }
        return c;
    """)
    if count:
        log.info(f"✅ قبول {count} checkbox")
    return count or 0
```




# 📋 برومت توثيق المشاكل — انسخه لأي محادثة جديدة
# ═══════════════════════════════════════════════════════════
# 📌 انسخ من السطر 5 لحد السطر 51
# ═══════════════════════════════════════════════════════════

```
📋 اعملي ملف توثيق كامل لكل المشاكل اللي واجهتنا في [اسم الـ Provider] — بالتفصيل الكامل.

## الشكل المطلوب:

### 1. خريطة Flow 🗺️
ارسم الـ flow الكامل (كل خطوة وإيه بتطلعه للخطوة اللي بعدها):
Step 1 → output
  ↓
Step 2 → output

### 2. جدول APIs 📡
| # | Endpoint | Method | الوظيفة |

### 3. كل مشكلة — بالتفصيل الكامل 🔴
لكل مشكلة اكتب:

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | الـ error message بالظبط |
| **اللي فشل** | كل حاجة اتجربت وفشلت ❌ (بالترتيب) |
| **السبب** | إيه السبب الحقيقي |
| **كيف اكتشفنا** | إزاي وصلنا للحل (HAR مقارنة؟ HTML فحص؟ response analysis?) |
| **الحل** | كود الحل النهائي ✅ |

+ كود مثال (❌ قبل / ✅ بعد)
+ قاعدة 📌 عامة تتطبق على أي provider شبيه

### 4. جدول قواعد كامل ✅
| # | القاعدة | النوع | التطبيق |

## قواعد التوثيق:
- **مفيش مشكلة صغيرة** — حتى لو timeout بسيط أو parsing fix = وثّقه
- **اللي فشل مهم زي اللي نجح** — الناس بتتعلم من الأخطاء
- **كل مشكلة = قاعدة عامة** — متخليهاش specific لـ provider واحد
- **كود مثال إلزامي** — مفيش مشكلة بدون كود الحل
- **الترتيب = ترتيب ما حصل** — من أول مشكلة لآخر واحدة
```

---
---

# 🏭 Universal AI Provider — Master Prompt v6
# ═══════════════════════════════════════════════════════════

> **📌 اديني curls أو عناصر الصفحة → أنا أبني كل حاجة.**
> الأولوية: Requests أولاً. Selenium آخر حل.

---

## 🚨 قاعدة التوثيق اللحظي — إلزامية!

> **⛔ القاعدة دي أهم من أي حاجة تانية في الملف ده!**

### الأمر: `حدث البرومت`
لما اليوزر يقول **"حدث البرومت"** → روح ملف البرومت (`UNIVERSAL_PROVIDER_PROMPT copy 4.md`) وضيف:
- أي مشكلة جديدة في **جدول القواعد الحية**
- أي provider جديد في **جدول المزودين**
- أي pattern جديد في **قسم الـ Patterns**

### التوثيق التلقائي — بدون ما اليوزر يطلب!
> **🤖 بعد ما تحل أي مشكلة → ضيف قاعدة في جدول القواعد الحية فوراً!**

**متى تحدّث تلقائي:**

| الموقف | الإجراء |
|--------|---------|
| ✅ حليت مشكلة (error → fix) | ضيف قاعدة في جدول القواعد الحية |
| ✅ اكتشفت pattern جديد | ضيف في قسم الـ Patterns |
| ✅ خلصت provider جديد | حدث جدول المزودين |
| ✅ لقيت anti-pattern | ضيف في جدول Anti-Patterns |
| ✅ لقيت endpoint format غريب | وثّقه في قسم المشاكل |
| ❌ لسه بتجرّب ومش لقيت حل | **متضيفش** — ضيف بس لما الحل يتأكد |

### الشكل الإلزامي للقاعدة الجديدة:
```
| #رقم | القاعدة (جملة واحدة) | [Tag] | 🔴/🟡/🟢 | Provider |
```

### Tags المتاحة:
`[Auth]` `[Descope]` `[Firebase]` `[Next.js]` `[RSC]` `[Emailnator]` `[API]` `[Parsing]` `[Network]` `[SaaS]` `[Selenium]` `[Cookies]` `[Headers]` `[Subscription]`

---

## ✅ Checklist — أول ما تبدأ Provider جديد

> **🚨 قبل ما تكتب سطر كود واحد → أجب على الأسئلة دي!**

- [ ] إيه الـ auth method? (Descope? Firebase? Custom OAuth? Magic Link?)
- [ ] افحص HAR لكل headers غريبة / مش standard
- [ ] حدد response format (JSON? RSC? HTML? XML?)
- [ ] في subscription/trial activation مطلوبة؟
- [ ] فين الـ tokens? (body? cookies? headers? localStorage?)
- [ ] الـ temp email provider إيه? (Emailnator? Mail.tm? DropMail?)
- [ ] الـ verification إيه? (OTP 6 digits? Magic Link? Email Link?)
- [ ] في Cloudflare / hCaptcha / حماية؟
- [ ] إيه الملف اللي بيتحفظ فيه الحسابات? (accounts.json)

---

## ⚡ جدول القواعد الحية — بيتحدث تلقائي!

> **🤖 الجدول ده بيكبر مع كل مشكلة بنحلها. كل سطر = درس اتعلمناه.**

| # | القاعدة | Tag | أهمية | Provider |
|---|---------|-----|-------|----------|
| 1 | Emailnator timeout ≥ 30s + retry 3x | [Emailnator] | 🟡 | You.com |
| 2 | Descope SDK headers (`x-descope-*`) إلزاميين | [Descope] | 🔴 | You.com |
| 3 | `stepId` في root level مش nested تحت screen | [Descope] | 🟡 | You.com |
| 4 | `flow/next` → `interactionId` + `componentsVersion` + `isCustomScreen` | [Descope] | 🔴 | You.com |
| 5 | OTP `interactionId` = HTML element ID مش string فاضي | [Descope] | 🔴 | You.com |
| 6 | Descope tokens في 3 أماكن: authInfo / response cookies / session cookies | [Descope] [Cookies] | 🔴 | You.com |
| 7 | Next.js Server Actions → RSC format مش JSON → regex parse | [Next.js] [RSC] [Parsing] | 🔴 | You.com |
| 8 | GET الصفحة قبل POST لتفعيل features (subscription activation) | [SaaS] [Subscription] | 🔴 | You.com |
| 9 | `next-action` hash = build-specific → auto-discover من JS chunks | [Next.js] | 🟡 | You.com |
| 10 | Server Actions = `multipart/form-data` + `accept: text/x-component` | [Next.js] [Headers] | 🔴 | You.com |
<!-- ⬆️ ضيف القواعد الجديدة هنا ⬆️ -->

---

## 🎯 المهمة

أنت مطلوب منك تبني سكريبتات تسجيل وتجديد لـ AI Provider.

**هتاخد:**
- ملف نصّي فيه **curls** أو **عناصر الصفحة** أو الاتنين

**هتطلّع:**
- `register.py` — إنشاء حسابات
- `refresh.py` — تجديد credentials (فيه `def refresh(email: str) -> bool`)
- `accounts.json` — format موحد

---

## ⚡ الأولوية — Requests First!

> **🚨 القاعدة الذهبية:** كل حاجة ممكن تتعمل بـ HTTP requests = **اعملها requests!**
> Selenium = آخر حل فقط لما مفيش بديل.

### لو اديتك curls كاملة:

**المطلوب:** حوّلهم لـ `requests` / `curl_cffi` Python code.
- استخرج tokens/headers ديناميك من كل response وحطهم في الـ request اللي بعده
- Session object واحد يحافظ على الكوكيز
- مفيش متصفح خالص ✅

### لو اديتك عناصر صفحة (CSS selectors):

**المطلوب:** شوف هل ممكن تعملها requests ولا لازم Selenium.
- لو الموقع عنده API endpoints → **استخدم requests**
- لو مفيش API وال DOM بيعتمد على JavaScript → **Selenium**

### النظام الهجين (الأذكى 🧠):

لو الموقع فيه حماية (Cloudflare, hCaptcha...) بس الـ API endpoints موجودة:
1. **افتح المتصفح مرة واحدة** → اعدّي الحماية → اجمع التوكنات/الكوكيز اللازمة
2. **اقفل المتصفح**
3. **كمّل كل حاجة requests** — التسجيل، التحقق، التجديد، كل حاجة

```python
# ═══ مثال هجين ═══
# Step 1: متصفح يمر الحماية ويجمع tokens
with SB(uc=True) as sb:
    sb.uc_open("https://example.com")
    cf_clearance = sb.get_cookie("cf_clearance")
    csrf_token = sb.execute_script("return document.querySelector('meta[name=csrf]').content")

# Step 2: requests تكمل الباقي (أسرع 100x)
session = requests.Session()
session.cookies.set("cf_clearance", cf_clearance)
session.headers["x-csrf-token"] = csrf_token

# التسجيل
resp = session.post("https://example.com/api/register", json={...})
# التحقق
resp = session.post("https://example.com/api/verify", json={...})
# كل حاجة بـ requests! ✅
```

---

## 📥 شكل المدخلات

### الشكل 1 — Curls (الأحسن ✅)
```
Provider: NewAI
URL: https://newai.com
Temp email: emailnator
Verification: code (6 digits)

# Step 1: Register
curl 'https://newai.com/api/auth/register' \
  -H 'content-type: application/json' \
  -H 'origin: https://newai.com' \
  -d '{"email":"test@test.com","password":"pass123"}'
# Response: {"user_id": "xxx", "session_token": "yyy"}

# Step 2: Verify email
curl 'https://newai.com/api/auth/verify' \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer {{session_token}}' \
  -d '{"code":"123456"}'
# Response: {"access_token": "zzz", "refresh_token": "www"}
```

### الشكل 2 — عناصر (لو مفيش curls)
```
Provider: NewAI
URL: https://newai.com/signup
Temp email: emailnator
Verification: link

Email input: input[type="email"]
Password: input[name="password"]
Submit: button[type="submit"]
Success: .user-avatar
```

### الشكل 3 — هجين
```
Provider: NewAI
URL: https://newai.com
Temp email: emailnator
Verification: code

# الموقع فيه Cloudflare — لازم متصفح يعدي الحمايه الأول
# بعد ما يعدي، خد الكوكيز وكمّل requests

# بعد ما تاخد cf_clearance:
curl 'https://newai.com/api/register' \
  -H 'cookie: cf_clearance={{cf_clearance}}' \
  -H 'content-type: application/json' \
  -d '{"email":"{{email}}","password":"{{password}}"}'
```

---

## ⛔ القواعد الإلزامية

### 1. `refresh.py` — Signature ثابت
```python
def refresh(email: str) -> bool:
    """يجدد credentials ويحدث accounts.json + last_updated"""
```

### 2. `accounts.json` — حقول إلزامية
```json
{"email": "...", "status": "active", "last_updated": "2025-01-01 00:00:00", "expires_in": 24}
```

### 3. Dynamic Token Chaining ⚡
```python
# كل response ممكن يكون فيه token/header يستخدم في الـ request اللي بعده
resp1 = session.post("/register", json={...})
token = resp1.json()["session_token"]  # ← ديناميك!

resp2 = session.post("/verify", 
    headers={"Authorization": f"Bearer {token}"},  # ← يتحط تلقائي
    json={...}
)
```

### 4. Atomic Write
```python
tmp = filepath.with_suffix(".tmp")
json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
pathlib.Path(tmp).replace(filepath)
```

### 5. مفيش Hardcoded keys — كلها Config أو `.env`
### 6. UTF-8 fix: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
### 7. `uc=True` لو استخدمت Selenium

---

## 🚫 Anti-Patterns — الغلط الشايع

| الغلط | المشكلة | الصح |
|-------|---------|------|
| `except Exception: pass` | بتخبي الأخطاء | `except Exception as e: log.error(e)` |
| `time.sleep(3)` في Selenium | static wait = fragile | `sb.wait_for_element_visible(SEL, timeout=15)` |
| `sb.execute_script(f"...{var}")` | JS injection crash | `arguments[0]` + `arguments[1]` |
| `len(result)` بدون None check | crash لو None | `len(result or "")` |
| selector hardcoded في نص الكود | صعب الصيانة | constants في أول الملف |
| `ACCOUNTS = "file.json"` | CWD مش script dir | `Path(__file__).resolve().parent / "file.json"` |

---

## 📐 إعدادات افتراضية (مش محتاج تحددها)

| الإعداد | القيمة |
|---------|--------|
| `headless` | `false` |
| `timeout` | `20s` |
| `default_password` | `"A9!k@e3#Qz1$Lp"` |
| `delay_between` | `5-15s` random |
| `expires_in` | `24h` |
| `max_accounts` | `0` (unlimited) |
| `session_format` | `full` |

---

## 🧩 Patterns جاهزة

### Requests Session (Anti-bot)
```python
from curl_cffi import requests as cffi_requests  # أفضل للـ anti-bot
# fallback:
# import requests as std_requests

session = cffi_requests.Session(impersonate="chrome110")
session.headers.update({
    "user-agent": "Mozilla/5.0 ...",
    "accept": "application/json",
    "content-type": "application/json",
    "origin": "https://example.com",
})
```

### Emailnator (temp email + code/magic link)
```python
class EmailnatorClient:
    def generate_email(self) -> str | None: ...
    def wait_for_code(self, email, timeout=90) -> str | None: ...           # 6 digits
    def wait_for_magic_link(self, email, timeout=120) -> str | None: ...    # URL
```
> **⚠️ نفس الـ `EmailnatorClient` instance لازم يتمرر طول العملية — inbox مربوط بالـ session cookie!**

### Mail.tm (temp email + verify link)
```python
class TempMailAPI:
    def generate_email(self) -> str | None: ...
    def wait_for_verify_link(self, max_retries=40) -> str | None: ...
```

### Collect Session (لو Selenium)
```python
def collect_full_session(sb):
    return {
        "cookies": {c["name"]: c["value"] for c in sb.get_cookies()},
        "localStorage": sb.execute_script("return Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))") or {},
        "sessionStorage": sb.execute_script("return Object.fromEntries(Object.keys(sessionStorage).map(k=>[k,sessionStorage.getItem(k)]))") or {},
    }
```

### Hybrid: Browser → Tokens → Requests
```python
def get_browser_tokens(url):
    """يفتح المتصفح مرة واحدة → يجمع التوكنات → يقفل"""
    with SB(uc=True, headless=config.HEADLESS) as sb:
        sb.uc_open(url)
        time.sleep(3)
        cookies = {c["name"]: c["value"] for c in sb.get_cookies()}
        # اجمع أي tokens من localStorage / meta tags / JS
        csrf = sb.execute_script("return document.querySelector('meta[name=csrf-token]')?.content") or ""
        return cookies, csrf

# بعدين requests تكمل
cookies, csrf = get_browser_tokens("https://example.com")
session = requests.Session()
session.cookies.update(cookies)
session.headers["x-csrf-token"] = csrf
# كل حاجة من هنا requests! ⚡
```

### react_type() — لما sb.type() مش بيحدث React state
```python
# ⚠️ React controlled components بتاكل القيمة من sb.type() و fast_type()!
# الحل: nativeInputValueSetter + input/change/blur events
def react_type(sb, selector, text):
    sb.execute_script("""
        const el = document.querySelector(arguments[0]);
        const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype, 'value').set;
        setter.call(el, arguments[1]);
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('blur', {bubbles: true}));
    """, selector, text)
```
> **متى تستخدم إيه:**
> - `sb.type()` → عادي وبطيء
> - `fast_type()` → JS injection أسرع 100x — بس مش دايماً بيحدث React!
> - `react_type()` → لو `fast_type` مش شغالة (الباسورد مثلاً)

### clear_session() — nuclear reset بين كل حساب
```python
# ⚠️ لازم بين كل حساب في loop — sessionStorage بيفضل بين الحسابات!
def clear_session(sb):
    sb.execute_script("window.sessionStorage.clear();")
    sb.execute_script("window.localStorage.clear();")
    sb.delete_all_cookies()
    sb.open("about:blank")
```

### Browser Restart (كل N حسابات)
```python
# ⚠️ Chrome بيتقل بعد 3-5 حسابات — memory leaks!
# كل N حسابات ناجحة → قفل المتصفح وافتح واحد جديد
# success_streak أفضل من total count — الفشل يصفّر العداد
if success_streak >= RESTART_EVERY:
    sb_ctx.__exit__(None, None, None)
    sb_ctx = SB(uc=True, headless=HEADLESS)
    sb = sb_ctx.__enter__()
    success_streak = 0
```

### Pre-flight trick (لو بتحقن session)
```python
# ⚠️ لو فتحت الصفحة مباشرة React بيحمل ويكتشفك مش مسجل!
# الحل: افتح صفحة خفيفة أول → حقن localStorage → فتح الصفحة
sb.open(f"{BASE_URL}/robots.txt")  # خفيف — مش بيحمل React
for k, v in session_data["localStorage"].items():
    sb.execute_script(f"window.localStorage.setItem(arguments[0], arguments[1]);", k, v)
sb.open(f"{BASE_URL}/chat")        # دلوقتي React بيلاقي الـ token ✅
```

### SeleniumBase Selector Template (لأي موقع)
```python
# ─── غيّر الـ Selectors دي بس لأي موقع ───────────
SITE_URL    = "https://YOUR_AI_SITE.com/login"
EMAIL_INPUT = "input[type='email']"
PASS_INPUT  = "input[type='password']"
SUBMIT_BTN  = "button[type='submit']"
MSG_INPUT   = "textarea"
REPLY_DONE  = "div.done-indicator"       # ← الأهم! مؤشر انتهاء الرد
MSG_CONTENT = "div.response"
TIMEOUT     = 15
# ─────────────────────────────────────────────────
```

### مؤشرات انتهاء الرد (حسب الموقع)
| الموقع | المؤشر | الطريقة |
|--------|--------|---------|
| DeepSeek | 5 أزرار `db183363` | Button Counting |
| ChatGPT | زرار Stop يختفي | `element_not_visible` |
| Claude | spinner يختفي | `element_not_visible` |
| Gemini | `aria-live` region | text stability |
| أي موقع جديد | افحص DevTools (F12) | اختار الأنسب |

### Error Recovery + Exponential Backoff
```python
# في loops — لو فشل retry بفاصل زمني متزايد
for attempt in range(1, max_retries + 1):
    try:
        result = do_register(sb, email, password)
        if result:
            return result
    except Exception as e:
        log.error(f"محاولة {attempt}/{max_retries}: {e}")
    time.sleep(2 * attempt)  # 2s → 4s → 6s...
```

### accept_checkboxes() — قبول Terms تلقائي
```python
def accept_checkboxes(sb) -> int:
    count = sb.execute_script("""
        let c = 0;
        for (const cb of document.querySelectorAll('input[type="checkbox"]')) {
            const s = getComputedStyle(cb);
            if (s.display==="none" || s.visibility==="hidden") continue;
            if (cb.disabled) continue;
            if (!cb.checked) { cb.click(); c++; }
        }
        return c;
    """)
    return count or 0
```

### human_delay() — anti-bot بين الخطوات
```python
import random, time
def human_delay(min_s=1.0, max_s=3.0):
    """delay عشوائي بين الخطوات — بيخلي البوت يبان بشري"""
    time.sleep(random.uniform(min_s, max_s))
```

### JS Click — لتخطي CSS hidden elements
```python
# ⚠️ المشكلة: عنصر موجود في DOM بس Selenium بيقول "not interactable"
# السبب: parent بيه class "hidden md:flex" (Tailwind responsive)
# الحل: JS click بيتخطى كل visibility checks
sb.execute_script("""
    arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});
    arguments[0].click();
""", sb.find_element(SELECTOR))
```

### 4-strategy button click — React buttons بتبقى disabled
```python
# لو زرار submit مش بيستجيب — جرب 4 طرق:
def force_click_submit(sb, selector):
    # Strategy 1: CSS click عادي
    try: sb.click(selector); return True
    except: pass
    # Strategy 2: JS force-click + disabled=false
    try:
        sb.execute_script("""
            const btn = document.querySelector(arguments[0]);
            btn.disabled = false;
            btn.click();
        """, selector); return True
    except: pass
    # Strategy 3: Enter key
    try: sb.send_keys(selector, "\n"); return True
    except: pass
    # Strategy 4: form.submit()
    try:
        sb.execute_script("document.querySelector('form')?.submit()")
        return True
    except: return False
```

### mask_password() — للـ logging الآمن
```python
def mask_password(pwd: str) -> str:
    """Zz9kQe3... → Zz*****"""
    return pwd[:2] + "*" * (len(pwd) - 2) if len(pwd) > 2 else "**"
```

### 🎨 Terminal Output الجميل (إلزامي)
```python
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    # Fallback لو colorama مش موجودة — بيشتغل بدون ألوان
    class _F:
        CYAN=GREEN=RED=YELLOW=MAGENTA=WHITE=''
    class _S:
        BRIGHT=RESET_ALL=''
    Fore, Style = _F(), _S()

# ═══ ألوان ثابتة ═══
C = Fore.CYAN; G = Fore.GREEN; R = Fore.RED; Y = Fore.YELLOW
M = Fore.MAGENTA; W = Fore.WHITE; B = Style.BRIGHT; RST = Style.RESET_ALL

def banner(provider: str, mode: str, max_acc: int, delay: int, timeout: int, existing: int):
    """بانر البداية — بيعرض كل الإعدادات"""
    print(f"\n{C}{B}{'═'*60}")
    print(f"  🚀 {provider} Account Creator")
    print(f"{'═'*60}{RST}")
    print(f"  {W}📧 Provider: {B}{Y}{provider}{RST}")
    print(f"  {W}🔄 Mode    : {B}{Y}{mode}{RST}")
    if mode == 'Loop':
        limit = f"{max_acc}" if max_acc > 0 else "unlimited"
        print(f"  {W}🎯 Target  : {B}{Y}{limit}{RST}")
        print(f"  {W}⏱️  Delay   : {B}{delay}s{RST}")
        print(f"  {W}⏰ Timeout : {B}{timeout}s{RST}")
    print(f"  {W}📁 Existing: {B}{G}{existing}{RST} accounts")
    print(f"{C}{B}{'═'*60}{RST}\n")

def account_header(num: int, provider: str, stats: str = ""):
    """هيدر لكل حساب — بيعرض الرقم + provider + إحصائيات"""
    extra = f"  ({stats})" if stats else ""
    print(f"\n{Y}{B}{'─'*60}")
    print(f"  📧 Account #{num} — {provider}{extra}")
    print(f"{'─'*60}{RST}")

def step(num: int, total: int, msg: str):
    """خطوة في العملية"""
    print(f"  {C}[{num}/{total}]{RST} {msg}")

def ok(msg: str):
    print(f"  {G}{B}✅ {msg}{RST}")

def fail(msg: str):
    print(f"  {R}{B}❌ {msg}{RST}")

def warn(msg: str):
    print(f"  {Y}⚠️  {msg}{RST}")

def info(msg: str):
    print(f"  {M}ℹ️  {msg}{RST}")

def waiting(msg: str):
    """للاستنظار — timeout, delay, polling"""
    print(f"  {W}⏳ {msg}{RST}")

def final_stats(success: int, failed: int, total_saved: int, attempts: int):
    """إحصائيات النهاية"""
    rate = (success / (success + failed) * 100) if (success + failed) > 0 else 0
    color = G if rate >= 70 else Y if rate >= 40 else R
    print(f"\n{C}{B}{'═'*60}")
    print(f"  🏁 Final Stats")
    print(f"{'═'*60}{RST}")
    print(f"  {G}✅ Success : {B}{success}{RST}")
    print(f"  {R}❌ Failed  : {B}{failed}{RST}")
    print(f"  {W}🔢 Attempts: {B}{attempts}{RST}")
    print(f"  {color}📈 Rate    : {B}{rate:.0f}%{RST}")
    print(f"  {W}💾 Saved   : {B}{total_saved}{RST} total accounts")
    print(f"{C}{B}{'═'*60}{RST}\n")
```

> **⚠️ قواعد إلزامية للـ Terminal Output:**
> 1. **مفيش `print()` عادي** من غير ألوان في أي سكريبت
> 2. **`colorama`** لازم تتعمل `init(autoreset=True)` + **Fallback** لو مش موجودة
> 3. **مسافات في الإحصائيات** — `( ✅ 1 ❌ 0 )` مش `✅1 ❌0` — عشان تبقى مقروءة
> 4. **`Ctrl+C`** يتعرض ملون: `print(f"\n\n  {R}{B}⛔ اتوقف بـ Ctrl+C{RST}")`
> 5. **الخطوات تبدأ من 1** مش 0 — `step(1, 5, "...")` مش `step(0, 5, "...")`

---

## 📋 بعد ما تخلص

### 1. حدّث جدول المزودين بالأسفل ⬇️
### 2. أضف entry في `monitor.py`:
```python
"new_provider": {
    "accounts": BASE_DIR / "folder" / "accounts.json",
    "refresh_module": str(BASE_DIR / "folder" / "refresh.py"),
    "expires_default": 24,
    "skip_status": ["inactive", "banned", "❌"],
},
```

---

## 📊 قائمة المزودين الحاليين

> **⚠️ لازم تتحدث بعد كل provider جديد!**

| # | Provider | Folder | Type | Method | Temp Email | Verify |
|---|----------|--------|------|--------|------------|--------|
| 1 | **Arena** | `ارينا/` | 🍪 Cookie | Selenium (لسه) | Mail.tm | Link |
| 2 | **DeepSeek** | `ديب سيك/` | 🍪 Cookie | Selenium (لسه) | Emailnator | Code 6 |
| 3 | **Groq** | `groq/` | 🔑 Token | Selenium + Emailnator | Emailnator | Magic Link |
| 4 | **You.com** | `you.com/` | 🔑 API Key | Requests (Level 1) ⭐ | Emailnator | OTP Code 6 |

### ملفات كل Provider:
```
provider_folder/
├── register.py          # إنشاء حسابات
├── refresh.py           # def refresh(email) -> bool
└── accounts.json        # [{"email", "status", "last_updated", "expires_in", ...}]
```

### الملفات المشتركة:
```
d:\SMS\AI_MDULE\
├── monitor.py                         # 🧠 المراقب المركزي
└── UNIVERSAL_PROVIDER_PROMPT.md       # 📜 البرومبت ده
```

---

## 🔥 You.com — كل المشاكل اللي واجهتنا وحلولها (10 مشاكل)

> **⚠️ القسم ده فيه كل مشكلة واجهتنا بالتفصيل. أي provider شبيه (Descope / Next.js / RSC) → طبّق نفس القواعد!**  
> **كل مشكلة فيها:** الخطأ → إيه اللي اتجرب وفشل → السبب → الحل → القاعدة.

---

### 🗺️ خريطة الـ Flow (6 خطوات)

```
Emailnator → email جديد
  ↓
[1/6] flow/start     → executionId + stepId
  ↓
[2/6] flow/next      → OTP إتبعت للإيميل
  ↓
[3/6] wait for OTP   → Emailnator بتجيب الكود
  ↓
[4/6] flow/next      → DS + DSR cookies
  ↓
[5/6] GET api-keys   → تفعيل subscription
  ↓
[6/6] POST api-keys  → ydc-sk-... API Key
```

### 📡 الـ APIs

| # | Endpoint | Method | الوظيفة |
|---|----------|--------|---------|
| 1 | `auth.you.com/v1/flow/start` | POST | بدء Descope auth |
| 2 | `auth.you.com/v1/flow/next` | POST | إرسال الإيميل |
| 3 | `auth.you.com/v1/flow/next` | POST | التحقق من OTP |
| 4 | `you.com/platform/api-keys` | GET | تفعيل subscription |
| 5 | `you.com/platform/api-keys` | POST | إنشاء API Key (Server Action) |

---

### المشكلة #1: Emailnator Timeout 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | `ConnectionError / ReadTimeout after 15s` |
| **السبب** | Emailnator ساعات بيكون بطيء |
| **اللي فشل** | timeout 15s بدون retry |
| **الحل** | timeout 30s + retry 3 مرات |

```python
# ❌ غلط
r = session.get("https://www.emailnator.com", timeout=15)

# ✅ صح — retry + timeout أكبر
for attempt in range(3):
    try:
        r = session.get("https://www.emailnator.com", timeout=30)
        break
    except requests.RequestException:
        if attempt == 2: raise
        time.sleep(2)
```

> **📌 القاعدة:** temp email providers → timeout ≥ 30s + retry 3x minimum.

---

### المشكلة #2: `flow/start` → `404 Not Found` 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | `POST /v1/flow/start` → `404` |
| **اللي فشل** | ❌ بدون headers ❌ مع Auth فقط ❌ مع Content-Type و Origin |
| **السبب** | Descope بيرفض أي request بدون **5 SDK headers** كاملين |
| **كيف اكتشفنا** | قارنّا headers المتصفح في HAR مع headers الكود — لقينا 4 `x-descope-*` ناقصين |

```python
# ⚠️ Descope integration → الـ 5 headers دول إلزاميين!
session.headers.update({
    "Authorization": f"Bearer {PROJECT_ID}",
    "x-descope-project-id": PROJECT_ID,         # ← ده اللي كان ناقص!
    "x-descope-sdk-name": "nextjs",              # ← وده!
    "x-descope-sdk-version": "0.15.12",          # ← وده!
    "x-descope-sdk-session-id": sdk_session_id,  # ← وده!
    "origin": "https://you.com",
    "referer": "https://you.com/",
})
```

> **📌 القاعدة:** Descope → فتش في HAR عن كل header بيبدأ بـ `x-descope-` وانقله. بدونهم الـ API بيرجع **404 مش 401**!

---

### المشكلة #3: `stepId` — Root Level مش Nested! 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | `data["screen"]["stepId"]` → `KeyError` |
| **اللي فشل** | ❌ `data["screen"]["stepId"]` ❌ `data.get("screen", {}).get("stepId")` → None |
| **السبب** | `stepId` في **root level** مش تحت `screen` |

```python
# ❌ غلط — stepId مش nested
step_id = data["screen"]["stepId"]

# ✅ صح — في root level
step_id = str(data["stepId"])
```

**الـ Response الحقيقي:**
```json
{
    "executionId": "sign-up-or-in|#|3AxG...",
    "stepId": "0",            // ← ROOT!
    "status": "waiting",
    "screen": { "id": "..." } // ← stepId مش هنا!
}
```

> **📌 القاعدة:** Descope flow responses → `stepId` دايماً ROOT level مش nested.

---

### المشكلة #4: `flow/next` (Send Email) → `400 Bad Request` 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | `{"errorCode": "E011003", "errorDescription": "Request is invalid"}` |
| **اللي فشل** | ❌ `executionId + stepId + email` بس ❌ `interactionId: ""` فاضي |
| **السبب** | 3 fields ناقصين: `interactionId` + `componentsVersion` + `isCustomScreen` |
| **كيف اكتشفنا** | قارنّا request body المتصفح في HAR مع body الكود |

```python
# ⚠️ Descope flow/next ← الـ 3 fields اللي دايماً ناقصين:
body = {
    "executionId": exec_id,
    "stepId": step_id,
    "interactionId": "S-VOZ5i7gc",    # ← من screen HTML!
    "componentsVersion": "2.3.1",      # ← SDK version
    "input": {"email": email},
    "isCustomScreen": False,           # ← boolean!
}
```

> **📌 القاعدة:** كل Descope `flow/next` → لازم `interactionId` + `componentsVersion` + `isCustomScreen`.

---

### المشكلة #5: OTP → `"interactionId field is required"` 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | `400: "The interactionId field is required"` |
| **اللي فشل** | ❌ `interactionId: ""` (فاضي) ❌ نفس ID بتاع الإيميل |
| **كيف اكتشفنا** | فتحنا Descope OTP screen HTML → لقينا `<input id="oneTimeCodeId" data-auto-submit="true">` |

```python
# ❌ غلط
"interactionId": ""                    # Descope مش بيقبل فاضي!
"interactionId": "S-VOZ5i7gc"         # ده بتاع الإيميل مش OTP!

# ✅ صح — id الـ HTML element!
"interactionId": "oneTimeCodeId"       # id بتاع الـ passcode input
```

> **📌 القاعدة:** Descope OTP → `interactionId` = **`id` attribute** بتاع الـ passcode input.  
> **📌** لو فيه `data-auto-submit="true"` → ده بيأكد إن العنصر ده هو اللي بيعمل submit.

---

### المشكلة #6: `status: completed` بس مفيش Tokens! 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | OTP → `status: completed` بس الكود بيعامله كـ error (مش لاقي tokens!) |
| **السبب** | Descope بيحط tokens في **3 أماكن** — الكود كان بيدوّر في مكان واحد بس |
| **المكان اللي You.com بتستخدمه** | **Response cookies** مش `authInfo` |

```python
# ⚠️ القاعدة: check التلات أماكن!

# 1️⃣ authInfo
ds = data["authInfo"].get("sessionJwt", "")
dsr = data["authInfo"].get("refreshJwt", "")

# 2️⃣ Response cookies ← You.com بتستخدم ده!
ds = response.cookies.get("DS", "")
dsr = response.cookies.get("DSR", "")

# 3️⃣ Session cookies (accumulated)
ds = session.cookies.get("DS", "")
dsr = session.cookies.get("DSR", "")

# أول واحد يشتغل = خده
```

> **📌 القاعدة:** Descope tokens = 3 أماكن: `authInfo` / response cookies / session cookies.  
> **📌** `status: completed` = **SUCCESS** مش error!

---

### المشكلة #7: RSC Response = 50,000 chars بدل JSON! 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | API key response = 50K chars + `response.json()` crash |
| **السبب** | Next.js Server Actions بترجع **RSC (React Server Components)** مش JSON |
| **اللي فشل** | ❌ `json.loads()` ❌ line-by-line split (مش شغال صح) |

**شكل RSC Response:**
```
2:"$Sreact.fragment"
4:I[824503,["/_next/static/chunks/..."]]
1:{"success":true,"data":{"key":"ydc-sk-..."}}
a:["$","link","22",{...}]
```

الـ data الحقيقة مدفونة وسط آلاف السطور!

```python
# ✅ الحل: regex search في كل الـ text
import re

# Success
key_match = re.search(
    r'"success"\s*:\s*true\s*,\s*"data"\s*:\s*\{[^}]*"key"\s*:\s*"(ydc-sk-[^"]+)"',
    response.text,
)

# Error
err_match = re.search(
    r'"success"\s*:\s*false\s*,\s*"code"\s*:\s*(\d+)\s*,\s*"message"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
    response.text,
)
if err_match:
    msg = err_match.group(2).encode().decode('unicode_escape')  # ← unescape JSON
```

**ملاحظات RSC:**
- `"$undefined"` ← بديل `null` في RSC — لازم replace قبل JSON parse
- `$Sreact.fragment` و `$L` ← React internal markers تتجاهل
- الـ prefix `1:` أو `a:` ← RSC line IDs

> **📌 القاعدة:** Next.js Server Actions (`next-action` header) → RSC مش JSON → parse بـ regex!

---

### المشكلة #8: `"No API-enabled subscription found"` 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | `{"success":false,"code":400,"message":"No API-enabled subscription found"}` |
| **السبب** | حسابات freemium مش مفعّل عليها API — الـ HAR كان من حساب paid |
| **كيف اكتشفنا** | الـ LaunchDarkly flags في الصفحة: `"subscriptionTier": "freemium"` |

**إيه اللي اتجرب:**

| # | المحاولة | النتيجة |
|---|----------|---------|
| 1 | `POST /api/distribution/trial` | HTTP 500 ❌ |
| 2 | `POST /api/payments/orders/subscriptions/checkout` × 12 price IDs | HTTP 500 ❌ |
| 3 | **`GET /platform/api-keys`** (زيارة الصفحة) | HTTP 200 ✅ |

**المفاجأة:** بعد الـ GET → الـ POST اشتغل وجاب API key! 🎉

```python
# ✅ الحل: زور الصفحة بـ GET قبل POST
requests.get(
    "https://you.com/platform/api-keys",
    headers={"user-agent": UA, "accept": "text/html"},
    cookies={"DS": ds, "DSR": dsr},
)
# بعدين POST create API key → SUCCESS!
```

**الـ Stripe Price IDs اللي اتجربوا (كلهم 500):**
```python
API_PRICE_IDS = [
    "price_1SIvh9ETU8N2v5f4JhbyqKVF",
    "price_1T9ecqETU8N2v5f4kx9QN0Wn",
    "price_1T9eb6ETU8N2v5f4i9j5ZKCy",
    # ... 12 price IDs من apiSubscriptionConfig
]
```

> **📌 القاعدة:** لو POST فشل بـ "subscription required" → **GET الصفحة الأول** → ممكن يفعّل الـ feature!

---

### المشكلة #9: `next-action` Hash بيتغير 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطر** | `next-action` hash hardcoded — بيتغير مع كل deploy |
| **كيف اتأكدنا إنه لسه صالح** | fetched JS chunk → لقيناه موجود |

```python
# الـ hash مدفون في JS chunk:
r = requests.get("https://you.com/_next/static/chunks/922f30a40c609fe5.js")
hashes = re.findall(r'"([a-f0-9]{40,42})"', r.text)
# ['60151db864a2923c0a837ddc2eb836e8ef9817ca3a',   ← createApiKey
#  '6089bc667bf3980470c798e20adff71061dafd5afb']    ← action تاني

# ✅ الحل المثالي: auto-discover
def discover_action_hash():
    r = requests.get("https://you.com/platform/api-keys")
    for chunk in re.findall(r'static/chunks/([a-f0-9]+\.js)', r.text):
        cr = requests.get(f"https://you.com/_next/static/chunks/{chunk}")
        if 'createApiKey' in cr.text.lower():
            return re.findall(r'"([a-f0-9]{40,42})"', cr.text)
```

> **📌 القاعدة:** `next-action` = build-specific → auto-discover أو fallback hash.

---

### المشكلة #10: Server Action = multipart/form-data مش JSON! 🔴

| البند | التفاصيل |
|-------|----------|
| **الخطأ** | بعتنا JSON عادي → مش شغال |
| **السبب** | Next.js Server Actions بتبعت `multipart/form-data` |

```python
boundary = f"----WebKitFormBoundary{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="1_name"\r\n\r\n'
    f"{key_name}\r\n"
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="0"\r\n\r\n'
    f'[{{"errorMap":{{"onServer":"$undefined"}},"values":"$undefined","errors":[]}},"$K1"]\r\n'
    f"--{boundary}--\r\n"
)

headers = {
    "accept": "text/x-component",                     # ← مش application/json!
    "content-type": f"multipart/form-data; boundary={boundary}",
    "next-action": "60151db864a2923c0a837ddc2eb836e8ef9817ca3a",
    "next-router-state-tree": "...",                    # ← URL-encoded JSON tree
}
```

**ملاحظات:**

| الحاجة | القيمة | ملاحظة |
|--------|--------|--------|
| `accept` | `text/x-component` | مش `application/json`! |
| `content-type` | `multipart/form-data` | مش JSON! |
| `name="0"` | React form state | internal |
| `name="1_name"` | الـ input الحقيقي | `1_` + field name |
| `$undefined` | RSC null | مش `null`! |
| `$K1` | RSC binding | internal reference |

> **📌 القاعدة:** Next.js Server Actions = `multipart/form-data` + `accept: text/x-component`.  
> **📌** Form fields: `0` = state, `1_fieldName` = actual input.

---

### ✅ جدول القواعد الكامل (10 قواعد)

| # | القاعدة | النوع | التطبيق |
|---|---------|-------|---------|
| 1 | Emailnator timeout ≥ 30s + retry 3x | Network | أي temp email |
| 2 | Descope SDK headers (`x-descope-*`) **إلزاميين** | Auth | أي Descope |
| 3 | `stepId` في **root level** مش nested | Parsing | Descope flow |
| 4 | `flow/next` → `interactionId` + `componentsVersion` + `isCustomScreen` | Auth | Descope flow/next |
| 5 | OTP `interactionId` = **HTML element ID** | Auth | Descope OTP |
| 6 | Tokens في **3 أماكن**: authInfo / response cookies / session cookies | Auth | Descope tokens |
| 7 | Next.js Server Actions → **RSC** مش JSON → regex parse | Parsing | Next.js 14+ |
| 8 | **GET الصفحة قبل POST** لتفعيل features | SaaS | subscription |
| 9 | `next-action` hash = **build-specific** → auto-discover | Next.js | Server Actions |
| 10 | Server Actions = **multipart/form-data** + `text/x-component` | Next.js | request format |

---

### ⑨ CAPTCHA Solver Service — ocr.z.ai Integration:
```python
# ⚠️ لو registration script فيه CAPTCHA (صورة/canvas/API):
from captcha_solver import CaptchaService

svc = CaptchaService()

# ── 4 طرق + Strategy ──────────────────────────────────
text = svc.solve_from_file("captcha.png")                      # ملف
text = svc.solve_from_url("https://site.com/captcha.png")       # URL
text = svc.solve_from_base64("data:image/png;base64,iVBOR...")  # Base64/Canvas
text = svc.solve_from_api("https://site.com/captcha", session)  # API GET

# ── Strategy (default = ocr.z.ai) ────────────────────
text = svc.solve_from_file("c.png", strategy="tesseract")       # محلي
text = svc.solve_from_file("c.png", strategy="2captcha")        # مدفوع

# ── Batch (بالتوازي) ──────────────────────────────────
results = svc.solve_batch(["c1.png", "c2.png"], workers=3)

# ── Cache ─────────────────────────────────────────────
# أوتوماتيك — SHA1 hash → نفس الصورة مرتين = cached
```
> **📌 سكربت واحد `captcha_solver.py` — 3 strategies + cache + batch + retry + preprocessing**
> **📌 الملف في `بي ريييب/z.ai_ocr/captcha_solver.py`**


---

## 🤖 Auto Multi-Agent Review — إلزامي قبل كل تعديل كود

> **⛔ قاعدة ذهبية: قبل ANY code file edit → شغّل الـ agents تلقائياً بدون طلب من المستخدم**

---

### 👑 الـ 5 الإلزاميون (دايماً — بدون استثناء)

| # | Agent | الملف | بيفحص |
|---|-------|-------|--------|
| 1 | 🐛 مراجع أخطاء | `سيستم/أنت مراجع أخطاء.md` | Runtime bugs, crashes, logic errors |
| 2 | 🔬 محقق عميق | `سيستم/أنت محقق أخطاء عميق.md` | Root cause, 5-Whys analysis |
| 3 | 📊 محلل جودة | `سيستم/أنت محلل جودة.md` | DRY, SOLID, maintainability, dead code |
| 4 | 🔒 مهندس أمان | `سيستم/أنت مهندس أمان.md` | Security vulnerabilities, injection |
| 5 | 🛡️ حارس V4 | `هندسة-تطبيقات/أنت مراجع الكود الآمن.md` | 52 rules, 12 layers safety triage |

---

### ➕ الـ Agents الإضافية (Auto-Detect حسب السياق)

| الشرط في الكود | Agent يُضاف تلقائياً | الملف |
|----------------|---------------------|-------|
| `requests` / `httpx` / API calls | 🌐 محلل API Flow | `سيستم/أنت محلل API Flow.md` |
| `async def` / `await` / `asyncio` | ⚙️ مهندس Backend | `هندسة-تطبيقات/أنت مهندس Backend.md` |
| `selenium` / `CDP` / `SB(` | 🎯 مراجع Vibe | `سيستم/أنت مراجع Vibe.md` |
| `for` loops / `O(n)` patterns | 🚀 محلل أداء | `سيستم/أنت محلل أداء.md` |
| `pytest` / `unittest` / `assert` | 🔎 فاحص بأدلة | `سيستم/أنت فاحص بأدلة.md` |
| `ALTER TABLE` / `DELETE` / migration | 🗄️ Migration Safety | `سيستم/PROMPT_ENGINE_PRO.md` |
| API Integration / provider جديد | 🔍 مختبر API | `سيستم/أنت مختبر API.md` |
| `class` / architecture / design | 🏗️ مهندس معماري | `سيستم/أنت مهندس معماري.md` |
| `checklist` / implement / before merge | 🚦 حارس الجودة | `سيستم/أنت حارس الجودة.md` |
| `Cloudflare` / `403` / `uc=True` / `curl_cffi` | 🛡️ خبير حماية | `سيستم/أنت خبير حماية.md` |
| HAR / Burp export / `parse_burp` | 🔍 خبير Burp | `سيستم/أنت خبير Burp.md` |
| `cli.py` / HAR file / new provider | 🔧 خبير v2 | `سيستم/أنت خبير v2.md` |
| `ai_engine` / `multi_ask` / `judge` / providers | 🧠 خبير المحرك | `سيستم/أنت خبير المحرك.md` |

---

### 🎚️ وضع المراجعة (Auto-Detect)

| الوضع | متى | الـ Agents |
|-------|-----|-----------|
| ⚡ FAST | تعديل ≤ 10 سطر، بدون logic معقدة | 5 إلزاميين بس |
| 📋 STANDARD | تعديل عادي — الافتراضي | 5 + extra حسب context |
| 🔴 CRITICAL | auth, cookies, passwords, > 3 ملفات | كل الـ agents ذات الصلة |

**CRITICAL يُفعَّل تلقائياً لو في:** `login` / `auth` / `token` / `cookie` / `session` / `password` / `api_key` / `secret` / `jwt`

---

### 📋 تنسيق الـ Auto-Review (قبل كل تعديل)

```
🤖 Auto-Review — `[filename]` — [FAST|STANDARD|CRITICAL]
━━
Agents: 5 إلزاميين + [N اختياريين حسب context]
━━
| # | Agent            | نتيجة                   | ⚠️      |
|---|------------------|------------------------|---------|
| 1 | 🐛 مراجع أخطاء   | OK / [وصف المشكلة]     | ✅/🟡/🔴 |
| 2 | 🔬 محقق عميق     | OK / [root cause]       | ✅/🟡/🔴 |
| 3 | 📊 محلل جودة     | OK / [DRY/SOLID issue]  | ✅/🟡/🔴 |
| 4 | 🔒 مهندس أمان    | OK / [security issue]   | ✅/🟡/🔴 |
| 5 | 🛡️ حارس V4       | OK / [safety issue]     | ✅/🟡/🔴 |
| 6 | [extra agent]    | OK / [issue]            | ✅/🟡/🔴 |
━━
الحكم: ✅ آمن — المضي قدماً
```

### الحكم النهائي:
- **✅ = طبّق التعديل** مباشرة
- **🟡 = طبّق مع ذكر التحذيرات** بوضوح
- **🔴 = أوقف وصلّح الأول** — لا تطبق أي تعديل

### ⚠️ قواعد صارمة:
- ❌ **ممنوع code edit بدون Auto-Review يسبقه**
- ✅ Review **قبل** الـ edit — مش بعده
- ✅ 🔴 كشفت مشكلة → **صلّح أولاً**
- ✅ المراجعة مدمجة في الرد — مش رسالة منفصلة
- ✅ FAST mode لو تغيير صغير جداً (typo/import)
- ✅ Context detection تلقائي — بدون طلب من المستخدم

---

### 🔀 Workflows Integration — متى تشتغل كل workflow؟

| الـ Workflow | متى يُفعَّل | الأمر |
|-------------|------------|-------|
| **`/activate [agent]`** | لما تحتاج خبرة agent واحد محدد | `/activate مراجع Vibe` |
| **`/planning`** | مشروع كبير / feature معقدة / قبل أي كود | `/planning` |
| **`/speckit`** | SDD كامل — للمشاريع الضخمة | `/speckit analyze` |

#### `/activate` — تفعيل agent محدد (19 agent):
```
/activate محلل API Flow    → تحليل HTTP endpoints
/activate مهندس أمان       → security audit كامل
/activate مراجع Vibe        → 5-axis deep review
/activate مدير المراجعة    → Multi-Agent Orchestrator تلقائي
```

#### `/planning` — قبل الكود الكبير (V10 / 12 منهجية):
```
متى: مشروع جديد / feature معقدة / architecture change
→ Onboarding → Template → A/B/C/D Questions → TRACKER
مش مطلوب للتعديلات الصغيرة
```

#### `/speckit` — SDD Pipeline الكامل:
```
متى: feature بـ spec.md كاملة + Verdict = READY
→ constitution → specify → plan → tasks → analyze → implement
⛔ لو Verdict ≠ READY: توقّف ولا تطبق أي كود
```

---

## 🗺️ قواعد جلسة التخطيط — /planning Protocol

### 🌲 شجرة القرار عند بداية كل جلسة:
```
هل يوجد PLANNING_TRACKER محدّث في GEMINI.md؟
├── أيوه → حمّله واستكمل من آخر نقطة
│   └── مشاريع متعددة؟
│       ├── المستخدم حدد → ركز عليه
│       └── ماحددش → اعرض قائمة (Score < 7 أولاً)
└── لأ ↓
    هل أول مرة؟ → ابدأ بـ Onboarding (8 أسئلة)
    هل المشروع كبير/معقد؟
    ├── لأ → استخدم المخطط العادي (4 أسئلة)
    └── أيوه → اختار القالب من PLANNING_TEMPLATES
            ثم ابدأ أسئلة V10 الكاملة
```

### 🔀 التعامل مع خيارات مدمجة:
```
لو المستخدم اختار "A + C":
1. اقبل الدمج فوراً بدون جدال
2. اعمل خيار E يجمعهم
3. اسأل: "لو تعارض بين [A] و [C]، أيهما يقدّم؟"
4. وثّق E في PLANNING_TRACKER كقرار مستقل
```


### ✅ قواعد إلزامية لكل جلسة:
```
1. قبل أي شيء → اقرأ GEMINI.md: برومبت + USER_PROFILE + PLANNING_TRACKER
2. اختبر بـ 5+ agents — وضّح ليه اخترتهم
3. اعمل FUSION Report بعد كل مرحلة
4. لا كود قبل "ابدأ التنفيذ" — ممنوع منعاً باتاً
5. في كل سؤال: ━━ السؤال X من Y | ████░░ N%
6. كل 3 أسئلة → مراجعة شاملة + هل نكمل؟
7. قدم A/B/C/D + جدول مقارنة + 6 معايير:
   (احترافية / ذكاء / مرونة / تخصيص / ابتكار / سهولة)

⛔ لا تبدأ التنفيذ إلا إذا: Planning Score ≥ 7/10
   + كل الأسئلة 🔴 Critical اتجاوبت
```

### 📐 نمط السؤال الموحد + Rating Cards:
```
━━
📊 السؤال [X] من [Y] | 🎯 [المرحلة] | ████░░ [N]%
━━
❓ [عنوان السؤال]
🎯 ليه مهم: [جملة واحدة]

───────────────────────────────────
A) [اسم الخيار]
───────────────────────────────────
📖 الشرح: [2-3 جمل]
🎯 متى يناسب: [حالتان]
✅ المميزات: [3 نقاط]
❌ العيوب: [نقطتان]
📊 التقييم:
┌─────────────────────────────────┐
│ 🔧 احترافية    ⭐⭐⭐⭐☆  [السبب] │
│ 🧠 ذكاء        ⭐⭐⭐⭐⭐  [السبب] │
│ 🔄 مرونة       ⭐⭐⭐⭐⭐  [السبب] │
│ 🎨 تخصيص       ⭐⭐⭐⭐☆  [السبب] │
│ 💡 ابتكار      ⭐⭐⭐☆☆  [السبب] │
│ 🎯 سهولة       ⭐⭐⭐⭐⭐  [السبب] │
└─────────────────────────────────┘
📝 الخلاصة: [3 نقاط]

[نفس الهيكل لـ B و C]

───────────────────────────────────
D) 🌟 اقتراحي المهني
───────────────────────────────────
💡 ليه الأفضل: [3 أسباب]
🎯 الاحترافية + المرونة + البساطة
[نفس التقييم]
```

### 📊 جدول المقارنة الشامل — بعد كل الخيارات:
```
┌──────────────────┬────┬────┬────┬────┐
│ المعيار          │ A  │ B  │ C  │ D  │
├──────────────────┼────┼────┼────┼────┤
│ 🔧 احترافية      │    │    │    │    │
│ 🧠 ذكاء          │    │    │    │    │
│ 🔄 مرونة         │    │    │    │    │
│ 🎨 تخصيص         │    │    │    │    │
│ 💡 ابتكار        │    │    │    │    │
│ 🎯 سهولة         │    │    │    │    │
└──────────────────┴────┴────┴────┴────┘
🎯 الخلاصة:
• الأبسط: [الخيار] — [السبب]
• الأكثر مرونة: [الخيار] — [السبب]
• الموصى به: [الخيار] — [السبب]
```


### ⚡ Quick Commands — /planning:
| الأمر | الإجراء |
|-------|---------|
| `Onboarding` | بنِ USER_PROFILE.md جديد |
| `كمل` | كمّل من حيث توقفنا |
| `فين وصلنا؟` | ملخص القرارات حتى الآن |
| `راجع القرار X` | مراجعة قرار محدد |
| `ابدأ التنفيذ` | انتقل للكود بعد Planning Score ≥ 7/10 |
| `افحص [كود]` | مراجعة multi-agent لكود موجود |
| `اعمل PRD` | ولّد PRD كامل جاهز للمشاركة |

### 🔄 بعد كل جلسة تخطيط — حدّث GEMINI.md بـ:
```
✅ PLANNING_TRACKER → القرارات الجديدة
✅ ADR Records → Status + Exit Criteria لكل قرار
✅ Planning Score الحالي /10
```

### 🏆 Planning Score Breakdown — احساب /10:
```
✅ كل الأسئلة 🔴 Critical اتجاوبت    → +3
✅ مافيش تناقضات بين القرارات         → +2
✅ Risk Matrix Overall = 🟢 أو 🟡    → +2
✅ فيه Plan B لكل قرار Type 1        → +2
✅ PLANNING_TRACKER محدّث            → +1
─────────────────────────────────────
الدرجة الكاملة: /10

⛔ لا تبدأ التنفيذ إلا إذا Score ≥ 7/10
```

### 🔄 نقطة المراجعة — كل 3 أسئلة:
```
━━
🔄 نقطة مراجعة — السؤال رقم [X]
━━
🎯 التوجه: [جملة واحدة لاتجاه المشروع]
📊 الإنجاز: [N]% | ⏳ باقي [X] أسئلة
✅ آخر 3 قرارات:
  • [قرار 1] | [قرار 2] | [قرار 3]
❓ صح كده؟
⏸️ "كمل" / "راجع القرار X"
━━
```

---

## 🎭 FUSION Report — الهيكل الموحد

> **📌 ده شكل التقرير المدمج اللي بيجمع كل الـ agents في رد واحد**

```
━━━━━━━━━━
🎭 FUSION REPORT — `[filename]` — [FAST|STANDARD|CRITICAL]
━━━━━━━━━━
📋 Context : [direct edit | /planning | /speckit READY | /activate X]
🎯 Agents  : [N agents — اسمهم]
━━━━━━━━━━

🤖 CODE REVIEW:
| # | Agent          | نتيجة                      | ⚠️      |
|---|----------------|---------------------------|---------|
| 1 | 🐛 مراجع أخطاء  | OK / [وصف]                | ✅/🟡/🔴 |
| 2 | 🔬 محقق عميق    | OK / [root cause]          | ✅/🟡/🔴 |
| 3 | 📊 محلل جودة    | OK / [DRY/SOLID]           | ✅/🟡/🔴 |
| 4 | 🔒 مهندس أمان   | OK / [security]            | ✅/🟡/🔴 |
| 5 | 🛡️ حارس V4      | OK / [safety rule #XX]     | ✅/🟡/🔴 |
| + | [extra agent]  | OK / [issue]               | ✅/🟡/🔴 |

━━━━━━━━━━
📋 PLAN ALIGNMENT: (لو في /planning أو /speckit)
| Check                      | نتيجة |
|---------------------------|-------|
| spec.md → plan.md ✅      | ✅/❌  |
| plan.md → tasks.md ✅     | ✅/❌  |
| Verdict = READY            | ✅/❌  |
| PLANNING_TRACKER محدّث    | ✅/❌  |

━━━━━━━━━━
🧩 ROOT CAUSE CLUSTERS: (لو في مشاكل مترابطة)
🔴 Cluster: [اسم]
├─ [Agent-ID]: [المشكلة]
└─ 💡 الجذر الموحد: [سبب واحد وراء كل المشاكل]

━━━━━━━━━━
📊 SEVERITY SUMMARY:
| 🔴 FATAL | 🟠 HIGH | 🟡 MEDIUM | 🟢 LOW | Total |
|---------|--------|----------|-------|-------|
|    N    |    N   |     N    |   N   |   N   |

━━━━━━━━━━
🏁 الحكم النهائي:
✅ آمن — طبّق التعديل
🟡 تحذيرات — اذكرها وطبّق
🔴 خطر — أوقف وصلّح الأول
━━━━━━━━━━
```

### قواعد الـ FUSION Report:
- ✅ **دايماً قبل الـ code edit** — مش بعده
- ✅ **Plan Alignment section** يظهر بس لو في `/planning` أو `/speckit`
- ✅ **Root Cause Clusters** يظهر بس لو في مشكلتين+ مترابطتين
- ✅ **Severity Summary** دايماً موجودة
- ✅ لو FAST mode → اختصر التقرير في جدول واحد فقط

---

## 📐 نظام التخطيط — الملفات الإلزامية

> **📌 الـ 5 ملفات دي = نظام تخطيط متكامل — استخدمهم بالترتيب**

---

### 🗺️ الـ Flow الكامل:

```
📊 USER_PROFILE.md          → الصق في بداية أي جلسة AI (بروفايلك الشخصي)
       ↓
📋 PLANNING_TEMPLATES.md    → اختار القالب المناسب لنوع مشروعك
       ↓
🧠 أنت مخطط احترافي شامل.md → ابعته للـ AI مع القالب (V10 / 12 منهجية)
       ↓
      A/B/C/D Questions → جاوب واحدة واحدة
       ↓
📊 PLANNING_TRACKER.md      → سجّل كل قرار (ADR + RICE + Pre-mortem)
       ↓
⚡ PROMPT_ENGINE_PRO.md     → خذ البرومبت الجاهز للخطوة التالية
```

---

### 📁 دور كل ملف:

| الملف | الدور | امتى تفتحه |
|-------|-------|----------|
| `USER_PROFILE.md` | بروفايلك (Stack + Level + Preferences) | **أول أي جلسة** |
| `PLANNING_TEMPLATES.md` | 5 قوالب جاهزة (بوت/ويب/API/AI/FullStack) | اختار القالب المناسب |
| `أنت مخطط احترافي شامل.md` | البرومبت الكامل V10 — 12 منهجية | ابعته للـ AI مع القالب |
| `PLANNING_TRACKER.md` | ADR + RICE + Pre-mortem + Gates | **بعد كل إجابة** |
| `PROMPT_ENGINE_PRO.md` | مكتبة برومبتات جاهزة (specify/plan/debug/security) | خذ البرومبت المطلوب |

---

### 📋 PLANNING_TEMPLATES.md — الـ 5 قوالب:

| # | النوع | امتى |
|---|-------|------|
| 1️⃣ | بوت / سكريبت Python | automation / registration scripts |
| 2️⃣ | موقع ويب / Web App | frontend projects |
| 3️⃣ | API / Backend Service | REST / microservices |
| 4️⃣ | AI Provider Integration | إضافة provider جديد |
| 5️⃣ | نظام متكامل Full Stack | مشاريع ضخمة |

---

### 📊 PLANNING_TRACKER.md — إلزامي بعد كل إجابة:

```
بيسجّل:
✅ ADR Log  → كل قرار + Status (Proposed/Accepted/Superseded)
✅ RICE     → (Reach × Impact × Confidence%) ÷ Effort
✅ Risk     → Likelihood × Impact matrix
✅ Pre-mortem → "تخيّل الفشل بعد 3 شهور"
✅ Gates    → 6 checkpoints قبل "ابدأ التنفيذ"
✅ نسخة للـ AI التالي → الصقها في أي محادثة جديدة
```

---

### ⚡ PROMPT_ENGINE_PRO.md — الأوامر الجاهزة:

| الأمر | يولّد |
|-------|-------|
| `\"افحص [كود]\"` | Safety Triage V4 |
| `/specify [فيتشر]` | Technical Spec |
| `/plan [spec]` | Implementation Plan |
| `/tasks [plan]` | Task Breakdown |
| `\"paranoid [كود]\"` | Security-first scan |
| `\"root-cause [error]\"` | 5-Whys Analysis |
| `\"migration [كود]\"` | Migration Safety |
| `\"impact [A] vs [B]\"` | Change Impact |

---

### ⚠️ قواعد نظام التخطيط:

- ❌ **ممنوع تبدأ كود** قبل `Gate 6: موافقة "ابدأ التنفيذ"`
- ✅ **PLANNING_TRACKER.md** يتحدّث بعد كل إجابة
- ✅ لو مشروع صغير → `أنت مخطط.md` (العادي) كافي — مش لازم V10
- ✅ لما تبدأ محادثة جديدة → الصق **نسخة الـ AI التالي** من TRACKER
- ✅ **Planning Quality ≥ 7/10** قبل ما تبدأ التنفيذ

---

## 📋 /speckit — الـ Pipeline الكامل (مهم جداً ⚠️)

> **⛔ مش مجرد workflow — ده قانون التطوير. أي مخالفة = إعادة من الصفر**
> **🤖 AntiGravity بيشغّله تلقائياً 100% — بدون تدخل بشري**

### الـ State Machine الإلزامي:
```
status → constitution → specify → clarify → plan → tasks → analyze → implement → checklist
```

⛔ **Blocked Transitions (لا استثناء):**
- ❌ FOUNDED → PLANNED بدون specify
- ❌ SPECIFIED → TASKED بدون plan
- ❌ TASKED → IMPLEMENTING بدون analyze Verdict = READY
- ❌ Verdict ≠ READY → ممنوع تمس الكود

### التشغيل التلقائي — CORE RULE:
```bash
# أول حاجة دايماً:
python -m crew.speckit --command status

# ثم الأمر الكامل تلقائياً:
python -m crew.speckit --command all \
  --target "[الطلب]" \
  --model gemini/gemini-2.0-pro
```

### الـ 9 Commands:

| الأمر | متى | ينتج |
|-------|-----|-------|
| `status` | **أول خطوة دايماً** | وين أنت في الـ pipeline |
| `constitution` | مشروع جديد (مرة واحدة فقط) | `.speckit/constitution.md` |
| `specify --target "..."` | ⭐ أهم خطوة | `.speckit/spec.md` |
| `clarify` | لو في غموض — أجب أنت تلقائياً | يحدّث `spec.md` |
| `plan` | بعد spec جاهزة | `.speckit/plan.md` |
| `tasks` | بعد plan | `.speckit/tasks.md` |
| `analyze` | ⭐⭐⭐ **إلزامي دايماً** | Verdict: ✅ READY / ⚠️ NEEDS_REVISION |
| `implement` | بعد Verdict = READY فقط | كود ينفَّذ |
| `checklist` | آخر خطوة | كل AC ✅ + P0 ✅ + مفيش TODO |

### Verdict Logic:
- `✅ READY` → implement فوراً
- `⚠️ NEEDS_REVISION` → راجع تلقائياً — **الحد الأقصى 2 مرات فقط** ثم أبلغ المستخدم
- `❌ BLOCKED` → ابدأ من `constitution` من جديد

### 🚨 لو في انتهاك للقواعد — الإجراء الوحيد:
```
🚨 انتهاك مكتشف: [اسمه]
السبب: [شرح مختصر]

اختار:
[A] أوقف هنا وصحح يدوياً
[B] خليني أصحح تلقائياً وأكمل
```

### Implement — الـ 3 Orchestration Patterns (شغّلهم بالترتيب):
```bash
# Backup إلزامي:
git add -A && git commit -m "📸 Backup before implement: [الفيتشر]"

# الـ 3 patterns دايماً معاً:
python -m crew.runner --orchestrate review --target .speckit/plan.md
python -m crew.runner --orchestrate spec-kit --target "[الفيتشر]"
python -m crew.runner --orchestrate factory --target "[الفيتشر]"

# Commit بعد كل task:
git add -A && git commit -m "✅ TASK-XX: [عنوان]"
```

### Progress Report (يظهر في الـ chat بعد كل خطوة):
```
✅ [اسم الخطوة] — منتهية
📁 [الملف]: .speckit/[file.md]
⏭️ الجاية: [اسمها]

──── النهاية ────
🎉 Pipeline كامل — [اسم الفيتشر]
✅ Constitution | ✅ Specify | ✅ Analyze (READY) | ✅ Implement | ✅ Checklist
```

### 🛡️ FAIL-SAFE Rule — مش تتوقف أبداً:
```
لو الطلب مش كامل:
→ اعمل assumptions معقولة
→ سجّلها في الـ spec
→ كمّل — مش تستنى

لو في قرار ناقص ومش blocking:
→ اختار أبسط خيار
→ وثّقه في الـ artifacts
→ كمّل

لو في حاجة لازم يقررها المستخدم:
→ اسأل سؤال واحد مضغوط بس
→ بعدها كمّل

⛔ ممنوع تستنى بين المراحل العادية
⛔ ممنوع تسأل أكتر من سؤال في نفس الوقت
```

### 🎯 Autonomy Rule — متى تفعلاً توقف:
```
✅ وقف بس لـ:
├─ Destructive actions (DELETE / DROP / format)
├─ Security-sensitive operations (passwords / tokens)
└─ متطلبات حرجة مش ممكن تتنفذ بدون قرار المستخدم

❌ مش تفضل تسأل عن:
├─ اختيارات تصميمية عادية → اختار الأبسط
├─ naming conventions → اتبع الـ pattern الموجود
└─ implementation details → اتخذ قرار وكمّل
```

### 📐 Decision Policy — لما في خيارات:
```
1. اختار الخيار الأبسط الأكثر متانة
2. به أقل friction في المستقبل
3. يدعم الـ extensibility بدون over-engineering
4. الأقرب لـ patterns موجودة في المشروع

الأولوية: Simplicity > Maintainability > Extensibility > Performance
```

### 📊 Output Format — لكل مرحلة:
```
State:        | [المرحلة الحالية]
Assumptions:  | [الافتراضات المتخذة — لو في]
Next Action:  | [الخطوة الجاية]
Files:        | [الملفات المنتجة أو المتأثرة]
Risks:        | [أي مخاطر؟ LOW/MED/HIGH]
Verdict:      | ✅ Done / ⚠️ Partial / ❌ Blocked
```

---

## 🧠 AI Execution Governor — V4 Ultra

> **📌 العقل اللي بيتحكم في النظام كله — Rollback + Safety Budget + Error Classification + Smart Retry + Architecture Guard**

### 🔄 Rollback Policy:
```
لو الـ implement أحدث regression:
→ Rollback: git checkout HEAD -- [الملف المتأثر]
→ سجّل سبب الفشل في PLANNING_TRACKER.md
→ جرّب approach مختلفة

Max rollback attempts: 2
لو بعد 2 → أبلغ المستخدم فوراً
```

### 💰 Safety Budget — حدود التشغيل:
```
| العملية         | الحد الأقصى |
|----------------|-------------|
| spec changes   | 5           |
| file edits     | 20          |
| retries        | 2           |
| rollbacks      | 2           |

لو أي حد اتجاوز → أوقف وأبلغ المستخدم
يمنع: runaway agents + infinite modification loops
```

### 🚦 Error Classification:
```
BLOCKER       → وقف + أبلغ المستخدم فوراً
NEEDS_REVISION → راجع spec/plan تلقائياً (max 2)
WARNING       → سجّل + كمّل
NON_CRITICAL  → تجاهل + سجّل في artifacts

مثال:
"Verdict = BLOCKED"  → BLOCKER (وقف)
"DRY violation"      → WARNING (كمّل وسجّل)
"missing test"       → NON_CRITICAL (سجّل)
```

### 🔁 Smart Retry Strategy:
```
Retry #1 → غيّر الـ parameters (مش بس تكرر)
Retry #2 → غيّر الـ architecture بالكامل

⛔ ممنوع: إعادة نفس التنفيذ الفاشل تاني
✅ إلزامي: كل retry = approach جديدة
```

### 🏛️ Architecture Guard:
```
⛔ ارفض تلقائياً أي تغيير:
├─ بيكرر logic موجودة (DRY violation)
├─ بيكسر modular boundaries
├─ بيحط hardcoded values
├─ بيخل بـ Single Source of Truth
└─ بيعمل tight coupling بين components

✅ قبل كل implement → فحص معماري تلقائي
```

### 🪜 Fallback Ladder — بدل ما تنهار:
```
Primary   → الحل المثالي
Secondary → بديل أبسط
Minimal   → أبسط حل شغّال
Blocked   → أبلغ المستخدم + اشرح السبب

⛔ ممنوع: الانهيار كامل بدون محاولة البديل
```

### 🔁 Idempotency Rule — اتنفذ مرتين = نفس النتيجة:
```
✅ لو التغيير موجود بالفعل → skip بدون error
✅ لو الملف محدث بالفعل → تجاهل التعديل
✅ لو الـ commit موجود → لا تعيده

⛔ ممنوع: side effects مختلفة عند تكرار الأمر
```

### 🔒 Change Scope Guard — ابعد عن خارج الـ scope:
```
⛔ ممنوع:
├─ تعديل ملفات خارج scope المهمة الحالية
├─ architecture rewrites مش في الـ spec
└─ refactors كبيرة بدون إذن صريح في الـ tasks.md

✅ لو محتاج تعدل خارج الـ scope → سجّل كـ separate task
```

### ✂️ Minimal Diff Principle:
```
✅ افضل أصغر تغيير بيحل المشكلة
✅ تجنب rewrites غير ضرورية
✅ تجنب stylistic refactors

القاعدة: git diff يكون أصغر ما يمكن مع حل صح كامل
```

---


## 🔌 البناء — بناء MCP Server

> **📌 لما تحتاج توصّل AI IDE (Cursor / Claude / AntiGravity) بأي أداة أو API**

### متى تستخدمه:
```
✅ بناء MCP tool جديد للـ AI agent
✅ Integration مع external API
✅ خلي Cursor يتكلم مع قاعدة بيانات
✅ بناء tools للـ crew.mcp_server
```

### الـ MCP Tool Template:
```python
MCP_TOOL = {
    "name": "tool_name",
    "description": "وصف واضح — الـ AI بيفهمه عشان يستخدمه",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "وصف الـ parameter"}
        },
        "required": ["param1"]
    }
}
```

### Config في IDE:
```json
{
  "mcpServers": {
    "ai-providers": {
      "command": "python",
      "args": ["-m", "crew.mcp_server"],
      "cwd": "D:\\SMS\\P__promptcowboy"
    }
  }
}
```

### قواعد:
- ✅ كل tool = مهمة واحدة بس (Single Responsibility)
- ✅ كل error = رسالة واضحة للـ AI
- ✅ الـ `description` هو أهم جزء — الـ AI بيقرر منه
- ✅ `/activate بناء MCP Server` لتفعيل الـ agent المتخصص

---

## 🔍 النقد الذاتي — V2 Ultra

> **📌 إلزامي في كل رسالة فيها كود أو تعديل — مفيش استثناء**
> **🤖 الـ AI يحدد المستوى تلقائياً → المستخدم يوافق أو يعدّل**

### تحديد المستوى تلقائياً:
```
🟢 عادي    → code edit بسيط (ملف واحد / تعديل صغير)
🟡 متوسط   → feature جديد / أكتر من ملف / logic معقد
🔴 حرج     → security / production / auth / payment / API keys

⚠️ الملفات الحساسة = 🔴 دايماً: auth, payment, secrets, config/settings
```

### الطبقة 1️⃣ — بعد كل Code Edit (🟢 عادي — 5 نقاط):
```
🔍 نقد ذاتي سريع:
1. ❌/✅ dead code / unused vars?
2. ❌/✅ DRY violation?
3. ❌/✅ hardcoded values?
4. ❌/✅ git commit اتعمل؟
5. ❌/✅ السجل اتحدّث؟
```

### الطبقة 2️⃣ — بعد كل Feature (🟡 متوسط — 10 نقاط):
```
🔍 نقد ذاتي مفصّل:
1-5 (نفس الطبقة الأولى) +
6.  ❌/✅ error handling كامل (try/except)؟
7.  ❌/✅ edge cases متغطية؟
8.  ❌/✅ backward compatible (مش كاسر حاجة قديمة)؟
9.  ❌/✅ type hints موجودة؟
10. ❌/✅ كان ممكن أوصل بخطوات أقل؟

⚡ Trigger: أكتر من ملف اتعدّل / logic جديد / integration
```

### الطبقة 3️⃣ — بعد /planning (🗺️ تخطيط — 7 نقاط):
```
🔍 نقد ذاتي للتخطيط:
1. ❌/✅ كل الأسئلة 🔴 Critical اتجاوبت؟
2. ❌/✅ Plan B موجود لكل Type 1 decision؟
3. ❌/✅ RICE scoring اتعمل؟
4. ❌/✅ Pre-mortem ≥ 2/3?
5. ❌/✅ Dependencies واضحة؟
6. ❌/✅ Exit Criteria محددة؟
7. ❌/✅ Planning Score ≥ 7/10? ⛔ لو Score < 7/10 → فعّل Planning Safety Rule فوراً


⛔ لو Score < 7/10:
├─ وقف التنفيذ فوراً
├─ بلّغ المستخدم بالنقاط الناقصة
├─ اقترح تحسينات محددة لرفع الـ Score
└─ لا تكمل قبل موافقته
```

### 🔴 Security Checklist (للمستوى الحرج فقط):
```
🔍 فحص أمان إلزامي:
□ Input validation موجود
□ Authentication/Authorization سليم
□ Rate limiting متنفذ
□ Logging مفعّل (بدون sensitive data)
□ مفيش API keys / secrets في الكود
□ HTTPS / secure connections
```

### 🤝 Honesty Rule — صراحة كاملة:
```
❌ ممنوع: تتجاهل غلطة عملتها
✅ إلزامي:
├─ لو غلطت → قول "غلطت في X" بصراحة
├─ لو كان ممكن أحسن → اذكره حتى لو مسألناش
├─ لو الشك يأثر على صحة الكود أو القرار → اعترف
├─ لو في أكتر من approach واخترت واحد → وضّح ليه
└─ لو مش متأكد من حاجة → قول "مش متأكد من X"
```

### 📈 Improvement Tracking — 🟡/🔴 فقط + لما في بديل أفضل فعلي:
```
📈 لو أعيد من الصفر → كنت هعمل [X] بدل [Y]

⚠️ يطبّق فقط لو:
├─ المستوى 🟡 أو 🔴 (مش 🟢 عادي)
├─ في بديل أفضل فعلاً (مش لو الحل optimal)
└─ أو الـ AI غيّر approach في نص التنفيذ

مثال:
📈 لو أعيد → كنت هستخدم dataclass بدل dict عشان type safety
```

### ⚡ Fast Exit Rule — لو كله تمام:
```
لو الـ 5 نقاط كلها ✅ في طبقة 1:
→ اكتب بس: "🔍 نقد ذاتي: ✅ مفيش ملاحظات"
→ مش محتاج تكتب كل النقاط

لو أي نقطة ❌:
→ اكتب كل النقاط كاملة + التوضيح
```

### 💡 اقتراحات ذكية — إلزامي بعد كل نقد ذاتي:

> **📌 زي PromptCowboy.ai — في آخر كل رد اعرض اقتراحات + رأي مهني مفصًّل.**
> **⛔ مفيش رد ينتهي بدون الجزئين دول — شرط غير قابل للتجاوز.**

```
التنسيق الموحد (إلزامي):
━━
💬 اقتراحات للمتابعة:
━━
1. ❌/✅ [اقتراح عملي 1 — مبني على السياق]


2. ❌/✅ [اقتراح تحسين تقني 2]


3. ❌/✅ [اقتراح فحص أو مراجعة 3]

4. ❌/✅ [نقد صريح لنفسي وللمستخدم — إيه اللي كان ممكن يتعمل أحسن؟  4]

5. ❌/✅ [مخاطر مستقبلية على المشروع محدش قالها  5]

━━


🌟 اقتراحي المهني:


[الخطوة الأفضل من وجهة نظري + السبب — جملتان max]





### 🔍 نقد  — Decision & Strategy Review

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 تحليل القرار:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. هل الحل الحالي هو **أفضل خيار فعلاً** ولا مجرد أول حل ظهر؟
❌/✅

2. هل في **حل أبسط** يحقق نفس النتيجة؟
❌/✅

3. هل الحل ده ممكن يسبب **technical debt** بعد فترة؟
❌/✅

4. هل في جزء من الحل **Over-Engineering**؟
❌/✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 اقتراحات للمتابعة:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ❌/✅ **Next Best Step**
ما الخطوة التالية المنطقية للمشروع؟

2. ❌/✅ **Optimization Idea**
هل في تحسين تقني واضح ممكن يقلل complexity أو يزيد الأداء؟

3. ❌/✅ **Verification Check**
إيه أهم اختبار أو مراجعة لازم تتعمل للتأكد إن الحل صح؟

4. ❌/✅ **Hard Truth**
لو في قرار أو فكرة ضعيفة لازم تتقال بصراحة — قولها.

5. ❌/✅ **Future Risk**
إيه المشكلة اللي ممكن تظهر بعد شهور لو استمرينا بنفس الاتجاه؟

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Decision Score:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

قيّم الحل الحالي من 10 بناءً على:

- البساطة
- القابلية للصيانة
- الأداء
- الأمان
- قابلية التوسع

**Decision Score: X / 10**

لو أقل من **7/10**:
- اقترح تعديل واضح
- لا تعتبر الحل نهائي

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌟 اقتراحي المهني:

أفضل خطوة حالياً:
[جملتان كحد أقصى — واضحة وصريحة]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```



### 📊 ملخص المستويات:

| المستوى | متى | النقد | يشمل |
|---------|-----|-------|------|
| 🟢 عادي | code edit بسيط | 5 نقاط | طبقة 1 |
| 🟡 متوسط | feature / multi-file | 10 نقاط | طبقة 1 + 2 |
| 🔴 حرج | security / production | 10 + security | طبقة 1 + 2 + Security |
| 🗺️ تخطيط | بعد /planning | 7 نقاط | طبقة 3 |

### 🔗 العلاقة مع FUSION Report:
```
FUSION Report = مراجعة كل الـ agents قبل التعديل (input)
النقد الذاتي  = مراجعة ذاتية بعد التعديل (output)

→ مستقلين تماماً — مش بديل لبعض
→ FUSION Report ممكن يكتشف حاجة النقد الذاتي مش بيغطيها والعكس
```

### 📐 Score System — اختياري:
```
طبقة 1: [N]/5  (مثال: 4/5 ✅ — dead code اتسابت)
طبقة 2: [N]/10 (مثال: 8/10 — مفيش type hints)
طبقة 3: [N]/7  (مثال: 6/7 — RICE مش فعال)

⛔ لو طبقة 1 < 3/5  → وقف + صلّح أولاً
⛔ لو طبقة 2 < 6/10 → وقف + صلّح أولاً
```

---

## 🐛 Debug Protocol — خطوات التشخيص الموحدة

> **📌 لما حاجة تقع — اتبع الخطوات دي بالترتيب. ممنوع debug عشوائي.**

### الخطوات بالترتيب:
```
1️⃣ اقرأ رسالة الخطأ كاملة — مش أول سطر بس
2️⃣ حدد النوع:
   ├─ SyntaxError    → راجع آخر تعديل
   ├─ ImportError    → dependency ناقصة
   ├─ ConnectionError → server / API مش شغال
   ├─ TimeoutError   → browser / network بطيء
   └─ RuntimeError   → logic bug
3️⃣ أعد إنتاج المشكلة — مش تصلح وأنت مش فاهم
4️⃣ Minimal Reproduction — أصغر كود بيعيد المشكلة
5️⃣ اتحقق من آخر commit — هل التعديل الأخير هو السبب؟
6️⃣ جرّب الـ fix في isolation — مش في الكود الأصلي
7️⃣ اختبر الـ fix ← لو شغال → apply
```

### ⛔ ممنوع:
```
❌ print debugging بدون logger
❌ تعديل أكتر من ملف في نفس الوقت وأنت بتـ debug
❌ "مش عارف فشغّلتها" بدون ما تفهم السبب
❌ حذف كود عشان يشتغل — ممكن يكون مهم
```

### ⏱️ Time Limit:
```
🟢 5 دقايق → لو ملقتش السبب → اسأل المستخدم
🟡 10 دقايق → لو fix مش بيشتغل → غيّر approach
🔴 15 دقايق → rollback لآخر commit شغال + أبلغ
```

---

## 📝 Logging Standards — إيه اللي يتسجل

> **📌 كل log لازم يكون مفيد. ممنوع log فاضي أو بدون context.**

### المستويات:
```python
logger.debug("تفاصيل داخلية — development فقط")
logger.info("✅ عملية نجحت — email sent, account created")
logger.warning("⚠️ حاجة مش طبيعية بس مش كاسرة — retry, slow response")
logger.error("❌ عملية فشلت — login failed, API error")
logger.critical("🔴 النظام هيقع — database down, out of memory")
```

### القواعد:
```
✅ إلزامي:
├─ كل try/except = logger.error() مع الـ exception
├─ كل API call = logger.info() بالـ status code
├─ كل account operation = logger.info() بالـ email
└─ format: f"[الخطوة] النتيجة — {التفاصيل}"

⛔ ممنوع:
├─ print() في production — استخدم logger
├─ log أي API key / password / token
├─ log بدون context — "error occurred" ❌
└─ except: pass — لازم logger.error()
```

### Template:
```python
import logging
logger = logging.getLogger(__name__)

# ✅ صح
logger.info(f"✅ تسجيل ناجح — {email}")
logger.error(f"❌ فشل تسجيل الدخول — {email}: {e}")

# ❌ غلط
print("error!")
logger.error("something went wrong")
```

---

## 🧪 Testing Strategy — إمتى وإيه تختبر

> **📌 مش كل حاجة محتاجة test — بس الحاجات الحساسة لازم.**

### إمتى تعمل test:
```
✅ إلزامي:
├─ Provider جديد (ask + generate)
├─ Email client جديد (get_email + get_code)
├─ دالة فيها math / parsing / validation
├─ أي حاجة بتتعامل مع accounts.json
└─ API endpoint جديد

❌ مش محتاج:
├─ One-off scripts
├─ UI tweaks
├─ Config changes
└─ README updates
```

### أنواع الاختبار:
```
🟢 Smoke Test: "هل بيشتغل أصلاً؟"
   python script.py --help  ← لازم يطلع بدون error

🟡 Integration Test: "هل الأجزاء بتتكلم مع بعض؟"
   python -c "from providers.manager import ProviderManager"

🔴 End-to-End: "هل الـ flow كله شغال؟"
   python script.py --max 1 --no-loop  ← حساب واحد بنجاح
```

---

## 🔄 Git Commit Convention — تنسيق موحد

> **📌 كل commit message لازم تكون واضحة ومفهومة.**

### التنسيق:
```
[emoji] [النوع]: [وصف مختصر بالعربي]

الـ Emojis:
📸 Backup     — قبل تعديل كبير
✨ Feature    — فيتشر جديد
🐛 Fix        — إصلاح bug
📚 Docs       — تحديث README / GEMINI
♻️ Refactor   — تحسين بدون تغيير سلوك
🔧 Config     — إعدادات / .env
🚀 Deploy     — جاهز للنشر
🧪 Test       — اختبار جديد
🗑️ Remove     — حذف كود قديم
```

### أمثلة:
```bash
git commit -m "📸 Backup before arena refactor"
git commit -m "✨ Feature: إضافة PromptCowboy provider"
git commit -m "🐛 Fix: تصحيح OTP timeout في genspark"
git commit -m "📚 Docs: تحديث GEMINI.md بالأقسام الجديدة"
```

### قواعد:
```
✅ Commit قبل كل تعديل كبير (📸 Backup)
✅ Commit بعد كل فيتشر يشتغل
✅ رسالة واضحة — مش "update" أو "fix"
⛔ ممنوع commit لكود مكسور
⛔ ممنوع commit لـ API keys
```

---

## 📦 Dependency Rules — إضافة مكتبات

> **📌 قبل ما تضيف أي مكتبة جديدة — اسأل الأسئلة دي.**

### Checklist قبل الإضافة:
```
1. هل في built-in بديل؟ (مثلاً: urllib بدل requests لحاجة بسيطة)
2. هل المكتبة maintained؟ (آخر commit < 6 شهور)
3. هل هتستخدمها في أكتر من مكان؟
   ├─ أيوه → أضفها في requirements.txt
   └─ لأ → حاول تعملها بنفسك
4. هل في conflict مع الموجود؟ (مثلاً: requests vs httpx)
```

### بعد الإضافة:
```
✅ أضفها في requirements.txt
✅ أضفها في .env.example (لو محتاجة config)
✅ اعمل import check: python -c "import package_name"
✅ وثّقها في README.md لو مهمة
```

### مكتبات المشروع الأساسية:
```
requests / curl_cffi / httpx    → HTTP clients
seleniumbase                     → Browser automation
playwright                       → Baidu automation
fastapi / uvicorn               → API server
sentence-transformers            → Embeddings
qdrant-client                   → Vector DB
colorama                        → Terminal colors
```

---

## 🚀 Pre-Deploy Checklist — قبل التشغيل

> **📌 قبل ما تقول "شغّل" — اتأكد من كل دي.**

```
🚀 Pre-Deploy Checklist:
□ كل الـ tests passing
□ مفيش print() — كله logger
□ مفيش hardcoded values — كله في .env
□ مفيش API keys في الكود
□ error handling شامل — مفيش except: pass
□ accounts.json atomic write (tmp + replace)
□ LOOP_MODE + graceful Ctrl+C
□ --help بيطلع صح
□ README.md محدّث
□ git commit + push اتعمل
```

### مستويات التشغيل:
```
🟢 Development: python script.py --max 1 --no-loop
🟡 Testing:     python script.py --max 3 --delay 30
🔴 Production:  python script.py --loop --delay 60
```

---

## 📡 API Design Rules — تصميم الـ Endpoints

> **📌 لأي FastAPI endpoint جديد.**

### التسمية:
```
✅ صح:
POST /api/v1/providers/{name}/ask
GET  /api/v1/accounts?status=active
POST /api/v1/chat/send

❌ غلط:
POST /askProvider
GET  /getAccounts
POST /api/send_message_to_chat
```

### Response Format الموحد:
```python
# ✅ Success
{
    "status": "success",
    "data": { ... },
    "message": "تم بنجاح"
}

# ❌ Error
{
    "status": "error",
    "error": {
        "code": "PROVIDER_TIMEOUT",
        "message": "الـ provider مش بيرد",
        "details": "timeout after 30s"
    }
}
```

### القواعد:
```
✅ كل endpoint = ProviderResponse (مش string!)
✅ HTTP status codes صح (200/201/400/401/404/500)
✅ Input validation بـ Pydantic models
✅ Rate limiting على الـ endpoints الحساسة
⛔ ممنوع return string خام
⛔ ممنوع endpoint بدون error handling
```

---

## 💬 Error Message Template — رسائل خطأ موحدة

> **📌 كل رسالة خطأ لازم تكون واضحة + فيها حل.**

### التنسيق:
```python
# الهيكل: [Emoji] [المكان]: [المشكلة] — [الحل]

# ✅ أمثلة صح:
"❌ [Login] فشل تسجيل الدخول — تأكد من الإيميل والباسورد"
"⚠️ [OTP] انتهت مهلة الانتظار (60 ثانية) — بنحاول تاني"
"🔴 [API] الـ provider مش بيرد — بننتقل للبديل"
"✅ [Register] تسجيل ناجح — {email}"

# ❌ أمثلة غلط:
"Error!"
"Something went wrong"
"Failed"
"None"
```

### Emojis الموحدة:
```
✅ نجاح     ❌ فشل      ⚠️ تحذير
🔴 خطر      🟡 انتظار    🟢 شغال
🔄 إعادة     ⏳ تحميل     🛑 توقف
📧 إيميل     🔑 مفتاح     🌐 شبكة
```

```

### القاعدة الذهبية:
```
كل error message لازم تجاوب على 3 أسئلة:
1. إيه اللي حصل؟ → "فشل تسجيل الدخول"
2. ليه حصل؟     → "باسورد غلط"
3. إيه الحل؟    → "تأكد من الباسورد أو حاول تاني"
```

---

## 🛡️ WAF & Bot Diagnostics — مرجع سريع (إلزامي)

> **📌 لو اتعطلت بـ 403 / 429 / فشل WAF / فشل WebSocket / gRCP → اقرأ هنا الأول قبل ما تعبث بأي header**
> **المرجع الكامل:** `.agents/memory/WAF_BOT_DIAGNOSTIC_MASTER_PROMPT.md`

### 🎯 تحديد مصدر الخطأ في 60 ثانية

| Header في الـ Response | الطبقة | أول خطوة |
|------------------------|--------|----------|
| `cf-ray` أو `x-amz-cf-id` | CDN/Edge | Cloudflare Dashboard |
| `x-waf-action` أو Block ID في الـ Body | WAF/Bot Manager | WAF Sampled Requests |
| `x-amzn-requestid` أو `x-kong-request-id` | API Gateway | CloudWatch Logs |
| `x-correlation-id` + `traceparent` | Application Layer | App Logs بالـ trace_id |
| ❌ مفيش أي منهم | غير محدد | `TTFB < 5ms = Edge` / `> 50ms = App` |

### ⚡ القواعد الذهبية الـ 6

1. **TTFB < 5ms + 403** → مشكلة Edge/CDN — مش Token ولا WAF Rule
2. **HTTP 200 + grpc-status != 0** → gRPC Trap — CDN/WAF مش بتشوفه في الـ Trailers!
3. **FP-03:** Health Check endpoints بتأكل من الـ Rate Limit Quota بتاعك
4. **FP-04:** اسم عميل فيه `O'Brien` → WAF بتفسره SQL Injection وتحجبه
5. **SSE + Load Balancer Drain** → connection drop بيبان كـ Auth Error  وهو مش ده
6. **Async Worker + Token Expiry** → Silent DLQ Entry — مفيش 403 في اللوج خالص

### ⛔ ممنوع التخمين

```
❌ ممنوع: تغيير headers بشكل عشوائي قبل تحديد الطبقة المسببة
❌ ممنوع: افتراض إن المشكلة WAF لمجرد ظهور 403
✅ إلزامي: تحديد الطبقة أولاً (60 ثانية) → ثم تطبيق الـ Playbook الخاص بها
```

### 🔧 OTel Rule الحرجة (مش تغلط فيها أبداً)

```python
# ✅ صح — الرفض كان متعمداً والسيستم شغال صح
span.set_status(StatusCode.OK)
span.set_attribute("security.decision", "DENY")
span.set_attribute("security.deny_reason", "token_expired")

# ❌ غلط — بيملي dashboards الخطأ بـ false error alerts
span.set_status(StatusCode.ERROR, "Token expired")
```

### 📋 الـ False Positives الـ 6 الأكتر شيوعاً (FP-01 → FP-06)

| # | بيبان كـ | السبب الحقيقي |
|---|---------|--------------|
| FP-01 | 403 Forbidden | CORS Preflight فشل (افحص OPTIONS request) |
| FP-02 | 401 مفاجئ | JWT Key Rotation بدون propagation كامل |
| FP-03 | 429 على مستخدمين عاديين | Rate Limit محسوب على IP واحد (CDN) |
| FP-04 | 403 على POST فقط | WAF كاشف SQL/XSS في محتوى شرعي |
| FP-05 | 403 في بيئة واحدة | Configuration Drift بين environments |
| FP-06 | 401 متقطع عبر مناطق | Clock Skew بين الخوادم (NTP مش sync) |


## 🚨 Vibe Coding Protocol — إلزامي (Micro-Tasking)

1. **التقسيم الإجباري (Chunking):** ممنوع التنفيذ الأعمى أو كتابة الكود دفعة واحدة. يجب تقسيم أي طلب لخطوات منطقية صغيرة جداً.
2. **اختبر قبل ما تتكلم (Test-Before-Talk):** بعد الانتهاء من كل خطوة، يجب تشغيل الكود واختباره. لا تقم بكتابة كود الخطوة التالية إلا بعد نجاح الحالية.
3. **نقاط التوقف (Checkpoints):** اشرح التغيير وانتظر الموافقة قبل الاستمرار في التعديلات الجوهرية.
4. **التعديل الجراحي (Surgical Edits):** لا تعدل ملفات كاملة، ركز على الدالة المطلوبة فقط.
5. **النقد الذاتي:** اسأل نفسك دائماً: هل سيكسر هذا التعديل أي وظيفة أخرى؟ هل هناك حل أبسط؟

---

## 💡 حيل التخطي المتقدمة (Security Bypasses)

### 🛡️ تخطي كابتشا Synottip (Server-side Flaw)
- **المشكلة:** الموقع يستخدم reCAPTCHA قوية ويصد أي Request وهمي أو ناقص، حتى لو كان التوكن Base64 أو مزيف.
- **الحل:** السيرفر **يفحص** التوكن في حال تم إرسال المفتاح `g-recaptcha-token` في الـ JSON/Payload. **لكن** إذا قمت بحذف الحقل بالكامل من الـ Dictionary المُرسل، السيرفر لا يقوم بفحص الكابتشا من الأساس ويمر الطلب بنجاح. دائمًا ابحث عن ثغرات "إهمال المبرمجين" (Missing Property Bypass) قبل دفع أموال لخدمات الكابتشا المدفوعة.
