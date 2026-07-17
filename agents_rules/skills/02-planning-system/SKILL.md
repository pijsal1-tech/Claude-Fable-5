---
name: 0- نظام التخطيط
description: أدوات التخطيط الاحترافي — templates + tracker
---



# === PLANNING_TEMPLATES.md ===

# 📋 Project Type Templates — قوالب جاهزة

> **اختار القالب المناسب، انسخه، وابعته مع البرومبت الرئيسي.**
> القوالب دي بتوفر عليك وقت كتير في أول كل مشروع.

---

## 1️⃣ بوت / سكريبت تلقائي

```
📌 النوع: بوت / سكريبت Python
📌 الهدف: [مثلاً: تسجيل حسابات / مراقبة / automation]
📌 التقنية: Python + [curl_cffi / SeleniumBase / requests]
📌 الموارد:
  - RAM: [...] MB
  - Storage: [...] GB
  - Can it run 24/7? [Yes/No]
📌 المواقع المستهدفة: [...]
📌 Authentication: [API Key / Cookie / Browser]
📌 Anti-Bot Protection: [Cloudflare / reCAPTCHA / None / Unknown]
📌 Email Provider: [emailnator / tempmail / mailtm / own emails]
📌 الكمية: [X حساب / يوم | X request / ساعة]
📌 أهم حاجة: [سرعة / موثوقية / سهولة صيانة]
```

---

## 2️⃣ موقع ويب / Web App

```
📌 النوع: موقع ويب
📌 الهدف: [مثلاً: e-commerce / portfolio / dashboard / SaaS]
📌 المستخدمين المتوقعين: [X/شهر]
📌 التقنية: [غير متأكد / React / Next.js / Vue / Plain HTML]
📌 Backend: [Python/FastAPI / Node.js / PHP / لا يوجد]
📌 Database: [PostgreSQL / MongoDB / MySQL / SQLite / لا يوجد]
📌 Auth: [Email/Pass / Google / GitHub / لا يوجد]
📌 Hosting: [VPS / Shared / Serverless / Vercel / Fly.io]
📌 Budget: [مجاناً / $5-20/شهر / أكتر]
📌 Mobile-friendly: [ضروري / مش مهم]
📌 أهم حاجة: [جمال التصميم / سرعة / SEO / سهولة التطوير]
```

---

## 3️⃣ API / Backend Service

```
📌 النوع: API / Microservice
📌 الهدف: [مثلاً: REST API / Webhook / Integration]
📌 التقنية: [FastAPI / Flask / Express / Spring]
📌 Clients: [Frontend فقط / Mobile / Other services]
📌 Auth: [API Key / JWT / OAuth2 / Session]
📌 Database: [...]
📌 Rate Limiting: [مطلوب؟]
📌 Performance: [X requests/sec]
📌 Deployment: [Docker / Serverless / VPS]
📌 Documentation: [Swagger / Postman / لا يوجد]
📌 Testing: [Unit Tests / Integration / لا]
```

---

## 4️⃣ AI Provider Integration (AI_PROVIDERS)

```
📌 النوع: AI Provider جديد
📌 اسم الـ Provider: [...]
📌 الموقع: [...]
📌 Auth Type: [API Key / Cookie-based / Browser]
📌 Anti-Bot: [Cloudflare / CAPTCHA / None]
📌 الـ Endpoint: [معروف / محتاج Reverse Engineering]
📌 المميزات: [Chat / Image / Code / Voice]
📌 Free Tier: [كم طلب / يوم؟]
📌 Email للتسجيل: [Gmail / Temp / Any]
📌 تشابه مع: [provider شبيه عندنا = ...]
📌 الهدف من الإضافة: [استخدام مباشر / Registration فقط / Rotation]
```

---

## 5️⃣ نظام متكامل (Full Stack)

```
📌 النوع: نظام كامل (Full Stack)
📌 المشكلة اللي بيحلها: [...]
📌 المستخدمين: [من هم؟ كمية؟]
📌 الـ Core Features:
  1. [Feature 1]
  2. [Feature 2]
  3. [Feature 3]
📌 الـ Nice-to-have:
  - [Feature X]
📌 Database: [...]
📌 Frontend: [...]
📌 Backend: [...]
📌 Infrastructure: [...]
📌 Budget/Resources: [...]
📌 Timeline: [...]
📌 Team Size: [وحدك / X أشخاص]
📌 Experience Level: [مبتدئ / متوسط / متقدم]
```


# === PLANNING_TRACKER.md ===

# 📊 PLANNING TRACKER — V4
# ADR + Pre-mortem + RICE + Google Metrics + Amazon PR/FAQ

> **انسخ لكل مشروع. حدّثه بعد كل محادثة. الصقه في أي AI للاستمرار.**

---

## 📰 Amazon Working Backwards — PR/FAQ

```
العنوان: [...]
الفئة المستهدفة: [...]
المشكلة: [...]
الحل: [...]
النتيجة: [...]
اقتباس افتراضي: "[...]"

FAQ:
Q1: [أصعب سؤال تقني؟] → A: [...]
Q2: [التكلفة/الوقت؟] → A: [...]
Q3: [المخاطرة الأكبر؟] → A: [...]
```

---

## 🎯 Scope Definition

```
✅ Goals:
• G1: [...]
• G2: [...]

❌ Non-Goals (خارج الـ scope — عمداً):
• NG1: [...] — السبب: [...]
• NG2: [...] — السبب: [...]
```

---

## 📊 Key Metrics for Success

| الميتريك | Target | طريقة القياس | الحالة |
|---------|--------|-------------|--------|
| [M1] | [X] | [إزاي] | ⏳ |
| [M2] | [Y] | [إزاي] | ⏳ |
| Counter-metric | لا نتجاوز [Z] | [إزاي] | ⏳ |

---

## ❓ Open Questions

| # | السؤال | المالك | ETA | الحالة |
|---|--------|--------|-----|--------|
| OQ1 | [...] | [...] | [...] | 🔴 مفتوح |
| OQ2 | [...] | [...] | [...] | 🟡 جار |

---

## 📊 RICE Scoring

```
RICE = (Reach × Impact × Confidence%) ÷ Effort

┌──────────────┬───────┬───────┬────────┬────────┬──────────┐
│ ADR/Feature  │Reach  │Impact │Confid. │Effort  │RICE Score│
├──────────────┼───────┼───────┼────────┼────────┼──────────┤
│ ADR-01       │       │       │   %    │        │          │
│ ADR-02       │       │       │   %    │        │          │
└──────────────┴───────┴───────┴────────┴────────┴──────────┘
Priority Order: 1st=[ADR-X] | 2nd=[ADR-Y] | 3rd=[ADR-Z]
```

---

## 📋 ADR Log

### ADR-01: [عنوان]

```
Status: [Proposed/Accepted/Superseded/Deprecated]
RICE: [score]
Context: [...]
Decision: [...]
  MUST: [...] | SHOULD: [...] | MUST NOT: [...]
Rationale: [...]
Consequences: ✅[...] ❌[...] ⚠️[...]
Metric Impact: [M1: +X% / —]
Superseded By: [ADR-X / —]
```

### ADR-02: [عنوان]
[نفس الهيكل]

---

## ⚡ Risk Matrix

```
┌─────────────────┬──────────┬──────────┬───────────┐
│ ADR             │Likelihood│  Impact  │Risk Level │
├─────────────────┼──────────┼──────────┼───────────┤
│ ADR-01          │    L     │    M     │    🟢     │
│ ADR-02          │    M     │    H     │    🔴     │
├─────────────────┼──────────┼──────────┼───────────┤
│ Overall         │          │          │    🟡     │
└─────────────────┴──────────┴──────────┴───────────┘
```

---

## 💀 Pre-mortem

```
"تخيل الفشل بعد 3 شهور"

1. [السبب] | ADR يحميه: [X/—] | الوقاية: [...]
2. [السبب] | ADR يحميه: [Y/—] | الوقاية: [...]
3. [السبب] | ADR يحميه: [Z/—] | الوقاية: [...]

Pre-mortem Score: [X/3]
```

---

## 📁 سجل المحادثات

| # | AI Tool | الموضوع | ADRs | آخر ADR |
|---|---------|---------|------|---------|
| 1 | [...] | [...] | 01-03 | ADR-03 |

---

## ✅ Execution Gates

```
Gate 1: [ ] PR/FAQ مكتوبة وواضحة
Gate 2: [ ] كل ADRs Critical → Accepted
Gate 3: [ ] Pre-mortem Score ≥ 2/3
Gate 4: [ ] Non-Goals محددة
Gate 5: [ ] Overall Risk 🟢 أو 🟡
Gate 6: [ ] موافقة "ابدأ التنفيذ"

Planning Quality: [X/10]
Top RICE: ADR-[X] = [score]
```

---

## 🚀 نسخة لـ AI التالي

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
من PLANNING_TRACKER V4:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
المشروع: [...]
PR/FAQ: "[عنوان] — [الحل المختصر]"
Goals: [...] | Non-Goals: [...]
Key Metrics: M1=[target] M2=[target]
RICE Top: ADR-[X]=[score]

ADR Log:
ADR-01: [عنوان] → Accepted | RICE=[X]
ADR-02: [عنوان] → Superseded → ADR-03

Pre-mortem: [X/3] | Risk: 🟡
آخر سؤال: رقم [X]
الطلب الجديد: [...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```


# === implementation_plan.md.resolved ===

# بلان Phase 3 — كل اللي لسه ناقص

## اكتشافات جديدة من المسح العميق

### monitor.py — فيه 10 providers مسجلين:
```
arena, deepseek, groq, you_com, zo_computer,
runable, cohere, mistral, ai21, ernie
```
**ناقص:** genspark, perplexity, chatgpt

### scheduler.py — 3 مهام:
| المهمة | التكرار |
|--------|---------|
| monitor (فحص صحة) | كل ساعة |
| profile_update (تحديث scores) | كل 6 ساعات |
| cache_cleanup | كل 24 ساعة |

### shared/ — API الفعلي (كان ناقص من الـ prompts):
```python
# shared/ui.py
step(num, total, msg)  # خطوة [1/5]
ok(msg)                # ✅ نجاح
fail(msg)              # ❌ فشل
warn(msg)              # ⚠️ تحذير
info(msg)              # ℹ️ معلومة
banner(title, width)   # ═══ عنوان ═══
separator(width)       # ─── فاصل ───
summary_line(label, value)

# shared/io.py
atomic_save(data, filepath)              # كتابة ذرية
load_accounts(filepath) → list          # قراءة حسابات
upsert_account(filepath, account, key)  # إضافة/تحديث

# shared/delay.py
human_delay(lo=1.0, hi=3.0)  # تأخير عشوائي
```

### .توافق — Guides موجودة مش مربوطة:
- [AI_TEAM_GUIDE.md](file:///d:/SMS/AI_PROVIDERS%20-%20Copy%20_Copy--Copy_Copy/v2/notes/AI_TEAM_GUIDE.md) — دليل ai_team.py
- [TEMPNET_LESSONS.md](file:///d:/SMS/AI_PROVIDERS%20-%20Copy%20_Copy--Copy_Copy/v2/notes/TEMPNET_LESSONS.md) — دروس TempNet

---

## المهام المتبقية

### Task 1: تحديث PROMPT_ENGINE_PRO — shared/ API الفعلي
**الحالي:** ذكرنا الملفات بس مش الـ functions
**المطلوب:** إضافة API signatures الفعلية (step, ok, fail, atomic_save...)

### Task 2: `/add-to-monitor` workflow
```
خطوات إضافة provider لـ monitor.py:
1. تأكد refresh.py فيه def refresh(email) → bool
2. أضف entry في PROVIDERS dict
3. اختبر: python monitor.py --provider {name} --dry-run
```

### Task 3: PROMPT_ENGINE_PRO — القسم العربي
**الحالي:** الـ prompts كلها إنجليزي
**المطلوب:** نسخة عربية كاملة — عشان تبعتها لـ AI بيفهم عربي أحسن

### Task 4: تحديث الـ prompts الموجودة بـ monitor/scheduler context
**المطلوب:** add-provider و add-refresh يذكروا:
- "بعد ما تخلص → أضف entry في monitor.py PROVIDERS dict"
- "scheduler.py بيشغل monitor كل ساعة تلقائي"

### Task 5: System prompt جديد — "أنت مراقب" (Monitor Expert)
**لما محتاج تشخيص شبكة providers كاملة:**
- فحص صحة كل الحسابات
- تقرير بالأرقام (active/expired/banned per provider)
- اقتراح refresh أو register جديد












Now I have the full picture. The script ran successfully and showed me all the headers and key lines. PROMPT_ENGINE_PRO.md already has the `shared/` API documented (lines 233-257 and 326-330) AND monitor/scheduler context (lines 257, 264, 344-345, 390). Let me now compile the complete review:

I have all the data I need. Here's the complete review:

---

## 🔍 مراجعة البلان — Phase 3 (5 مهام)

| # | المهمة | الحالة | التفاصيل |
|---|--------|--------|----------|
| **Task 1** | تحديث [PROMPT_ENGINE_PRO.md](cci:7://file:///d:/SMS/AI_PROVIDERS%20-%20Copy%20_Copy--Copy_Copy/.agents/%D8%B3%D9%8A%D8%B3%D8%AA%D9%85/PROMPT_ENGINE_PRO.md:0:0-0:0) بـ shared/ API | ✅ **تم** | الملف (430 سطر) فيه `shared/` API كامل في **سطور 233-257** (imports + function signatures) و**سطور 326-330** (نسخة تانية). كل الـ functions موجودة: `step, ok, fail, warn, info, banner, separator, summary_line, atomic_save, load_accounts, upsert_account, human_delay` |
| **Task 2** | `/add-to-monitor` workflow | ✅ **تم** | ملف [add-to-monitor.md](cci:7://file:///d:/SMS/AI_PROVIDERS%20-%20Copy%20_Copy--Copy_Copy/.agents/workflows/add-to-monitor.md:0:0-0:0) (82 سطر) كامل: entry format + refresh.py compatibility check + test commands + scheduler verification |
| **Task 3** | PROMPT_ENGINE_PRO — النسخة العربية | ⚠️ **جزئي** | الملف فيه أقسام عربية (خصوصاً v2.0 section سطر 297+) لكن مش نسخة **عربية كاملة** — لسه أغلب الـ prompts إنجليزي. القسم العربي `مخصصة لمشروعك` موجود بس مش كافي كـ "نسخة عربية كاملة" |
| **Task 4** | تحديث workflows بـ monitor context | ✅ **تم** | [PROMPT_ENGINE_PRO.md](cci:7://file:///d:/SMS/AI_PROVIDERS%20-%20Copy%20_Copy--Copy_Copy/.agents/%D8%B3%D9%8A%D8%B3%D8%AA%D9%85/PROMPT_ENGINE_PRO.md:0:0-0:0) سطر 257: `monitor.py → 10 providers`, سطر 264: `scheduler.py → 3 jobs`, سطر 390: `✓ When done → update monitor.py`. `/add-provider` سطر 97-98 بيذكر integration with monitor. `/add-refresh` سطر 54-57 بيذكر compatibility مع monitor |
| **Task 5** | System prompt "أنت مراقب" | ✅ **تم** | ملف `أنت مراقب.md` (3885 bytes) موجود وكامل — فيه: تقرير صحة الشبكة + اقتراح إجراءات + أوامر bash جاهزة + أسلوب عربي |

---

### 📊 الخلاصة:

- **4 من 5 مهام ✅ خلصوا بالكامل**
- **Task 3 (النسخة العربية الكاملة) ⚠️ جزئي** — في أقسام عربية اتضافت بس مش البرومبت **كله** بالعربي

### 💡 اقتراح:
لو عايز Task 3 يخلص — محتاج نعمل نسخة كاملة من [PROMPT_ENGINE_PRO.md](cci:7://file:///d:/SMS/AI_PROVIDERS%20-%20Copy%20_Copy--Copy_Copy/.agents/%D8%B3%D9%8A%D8%B3%D8%AA%D9%85/PROMPT_ENGINE_PRO.md:0:0-0:0) بالعربي (أو ملف منفصل `PROMPT_ENGINE_PRO_AR.md`). عايز أنفذ ده؟+


