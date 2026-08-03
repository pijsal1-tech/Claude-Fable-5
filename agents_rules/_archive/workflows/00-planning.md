---
description: نظام التخطيط الاحترافي V10 — 12 منهجية | Google · Amazon · Intercom · ADR · Pre-mortem · RFC 2119 · Adaptive · Critical Thinking · UX · Rollback · Exit Criteria · PRD Export
---

# /planning — المرجع الموحد للتخطيط V10

> **12 منهجية من أكبر شركات هندسة البرمجيات في العالم**

---

## 🔬 V10 — المنهجيات الكاملة (12)

| # | المنهجية | المصدر | ما تضيفه |
|---|---------|--------|---------|
| 1 | **Amazon Working Backwards PR/FAQ** | Amazon Product Dev | اكتب press release قبل أي كود |
| 2 | **Goals + Non-Goals** | Couchbase/Uber RFC | حدد الـ scope — يمنع scope creep |
| 3 | **Key Metrics + Open Questions** | Google Design Doc | كيف تعرف إنك نجحت؟ |
| 4 | **RICE + Team Capacity** | Intercom + V9 | أولويات موضوعية + وقت حقيقي بعد حساب الفريق |
| 5 | **ADR Records** | GitHub MADR ⭐5K | كل قرار له Status lifecycle + Exit Criteria |
| 6 | **Pre-mortem Analysis** | Gary Klein / Atlassian | "تخيل الفشل" — Gate إلزامي |
| 7 | **RFC 2119 Keywords** | Amazon AWS SOPs | MUST/SHOULD/MAY — دقة لغوية |
| 8 | **Smart Progress** | V5 | Progress bar + Checkpoints كل 3 أسئلة |
| 9 | **Adaptive AI** | V6 | USER_PROFILE + Onboarding + Stack Injection |
| 10 | **Reversibility Flag** | Bezos 2015 | Type 1/Type 2 + Rollback Plan |
| 11 | **Shape Up Appetite** | Basecamp | كم مستعد تصرف؟ مش كم سيأخذ؟ |
| 12 | **PRD Export** | V9 | مستند شامل جاهز للمشاركة بأمر واحد |

---

## 📁 الملفات الثلاثة — اقرأهم بالترتيب

| # | الملف | الوظيفة | امتى تستخدمه |
|---|-------|---------|--------------|
| 1️⃣ | [`أنت مخطط احترافي شامل.md`](../تخطيط/أنت%20مخطط%20احترافي%20شامل.md) | البرومبت الكامل V10 — ابعته لأي AI | دايماً — أساس كل حاجة |
| 2️⃣ | [`USER_PROFILE.md`](../سيستم/USER_PROFILE.md) | بروفايلك الشخصي — الصقه مع البرومبت | دايماً بعد Onboarding |
| 3️⃣ | [`PLANNING_TRACKER.md`](../سيستم/PLANNING_TRACKER.md) | ADR Log + Pre-mortem + Gates cross-session | بعد كل محادثة تخطيط |
| 4️⃣ | [`PLANNING_TEMPLATES.md`](../سيستم/PLANNING_TEMPLATES.md) | 5 قوالب جاهزة حسب نوع المشروع | أول الجلسة عشان توفر وقت |

---

## ⚡ Quick Start — 3 خطوات

```
الخطوة 1️⃣: أول مرة → قول "Onboarding" → يبني USER_PROFILE.md
  قرارات: Stack + Level + Tracking + ميزات (<3 دقيقة)

الخطوة 2️⃣: اختار القالب من PLANNING_TEMPLATES.md
  (بوت / موقع / API / AI Provider / Full Stack)

الخطوة 3️⃣: في أي AI ابعت:
  [البرومبت] + [USER_PROFILE.md] + [القالب]

الخطوة 4️⃣: بعد كل إجابة → حدّث PLANNING_TRACKER.md
  ثم الصقه في AI جديد للاستمرار

الخطوة 5️⃣ (اختياري): عند الانتهاء → قول "اعمل PRD"
  يولّد مستند كامل جاهز للمشاركة مع الفريق
```

---

## 🔀 متى تستخدم التخطيط؟

```
✅ USE: مشروع كبير / قرارات تقنية متعددة / A/B/C/D مطلوبة
✅ USE: فيتشر جديد معقد / تغيير architecture
❌ SKIP: bug واضح / تعديل بسيط / مهمة بخطوة واحدة
```

---

## 🚀 طرق التشغيل

### من Cursor/Claude/Gemini (مباشرة):
```
1. افتح أنت مخطط احترافي شامل.md
2. انسخ كل المحتوى
3. الصقه في المحادثة
4. اكتب وصف مشروعك
```

### من Runner (A2A):
```bash
python -m crew.runner --orchestrate spec-kit \
  --target "وصف المشروع" \
  --model gemini/gemini-2.0-pro
```

### من AFlow (الأذكى):
```bash
# يحلل المهمة ويختار تلقائي
python -m crew.runner --auto "وصف المشروع"
# لو المهمة كبيرة → هيقترح تستخدم /planning أولاً
```

### من A2A مباشرة:
```bash
python -c "
from crew.a2a import delegate_task
delegate_task('plan', 'وصف مشروعك')
"
```

---

## 📋 الـ Workflow الكامل (شجرة القرار)

```
هل المشروع كبير أو معقد؟
├── لأ → استخدم أنت مخطط.md (العادي، 4 أسئلة)
└── أيوه ↓
    اختار القالب من PLANNING_TEMPLATES.md
    ↓
    ابعت أنت مخطط احترافي شامل.md + القالب لـ AI
    ↓
    جاوب A/B/C/D واحدة واحدة
    ↓
    بعد كل إجابة → حدّث PLANNING_TRACKER.md
    ↓
    محادثة جديدة? → الصق TRACKER في AI الجديد
    ↓
    كل الأسئلة 🔴 Critical اتجاوبت؟
    ├── لأ → كمّل الأسئلة
    └── أيوه ↓
        درجة جودة التخطيط ≥ 7/10?
        ├── لأ → راجع القرارات الضعيفة
        └── أيوه ↓
            قل "ابدأ التنفيذ" → /speckit أو --orchestrate
```

---

## 🏆 مقارنة أساليب التخطيط

| الأسلوب | المدة | القرارات | المخاطر | متى |
|---------|-------|---------|---------|-----|
| `أنت مخطط.md` (العادي) | 5 دقايق | 4 | ❌ | مهام بسيطة |
| `/planning` (هذا الملف) | 15-30 دقيقة | 10+ | ✅ Risk Matrix | مشاريع كبيرة |
| `/speckit` | ساعة+ | كل حاجة | ✅ كامل | مشاريع ضخمة |

---

## 💡 اقتراحات أقوى (Extras)

### 🔗 دمج /planning مع /speckit:
```
/planning → ينهي التخطيط → قل "ابدأ التنفيذ"
↓
/speckit specify → يبدأ كتابة المواصفات التقنية التفصيلية
↓
--orchestrate factory → ينفذ بفريق كامل
```

### ⚡ Auto-Trigger من AFlow:
لو `--auto` اكتشف إن المهمة معقدة (confidence < 60%) →
يطبع: `"💡 اقتراح: استخدم /planning أولاً للمشاريع الكبيرة"`

### 📊 Planning Score:
بعد الانتهاء دايماً اسأل نفسك:
```
✅ كل الأسئلة 🔴 Critical اتجاوبت? (+3)
✅ مافيش تناقضات? (+2)
✅ Risk Matrix Overall = 🟢 أو 🟡? (+2)
✅ فيه Plan B لكل قرار؟ (+2)
✅ الـ TRACKER محدّث؟ (+1)
─────────────────────
الدرجة الكاملة: /10
لازم ≥ 7 قبل ما تبدأ التنفيذ
```

---

## 🔴 قواعد لا تُكسر

```
❌ ممنوع تطلب الكود قبل "ابدأ التنفيذ"
❌ ممنوع تنسخ محادثات كاملة — الـ TRACKER كافي
❌ ممنوع تجاوب بإجابتين — فكر كويس واختار واحدة
✅ خد وقتك — التخطيط أهم من السرعة
✅ حدّث PLANNING_TRACKER.md بعد كل محادثة
✅ لو في تناقض → وقف وحله قبل ما تكمل
```

---

## 📊 الفرق الكامل بين الأساليب

| الميزة | مخطط عادي | V10 احترافي شامل |
|--------|-----------|-----------------|
| أسئلة | 4 | 10+ (حسب المشروع) |
| تتبع القرارات | ❌ | ✅ TRACKER + ADR |
| Risk Matrix | ❌ | ✅ Impact × Likelihood |
| Confidence Score | ❌ | ✅ لكل قرار |
| Plan B | ❌ | ✅ لكل خيار |
| كشف التناقضات | ❌ | ✅ HALT تلقائي |
| Cross-session | ❌ | ✅ TRACKER |
| جودة التخطيط | ❌ | ✅ /10 score |
| قوالب جاهزة | ❌ | ✅ 5 templates |
| Fatigue Guard | ❌ | ✅ عداد طاقة |
| Tech Debt | ❌ | ✅ لكل ADR |
| What-If | ❌ | ✅ تحليل فوري |
| Decision Journal | ❌ | ✅ مراجعة بعد المشروع |
| PRD Export | ❌ | ✅ مستند جاهز |
| Y-Statements | ❌ | ✅ ملخص سطر واحد (MADR 4.0) |
| Health Check | ❌ | ✅ 5 أبعاد (Spotify) |
| DACI Roles | ❌ | ✅ Driver/Approver (Intuit) |
