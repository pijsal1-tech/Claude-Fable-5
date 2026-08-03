---
# 👤 AI_PROVIDERS — User Planning Profile
# يُقرأ تلقائياً في بداية كل جلسة تخطيط
# حدّثه بعد كل Onboarding أو بعد 10 جلسات
---

## 🎯 البروفايل الأساسي

```yaml
# [انسخ القسم ده والصقه في بداية أي AI مع البرومبت]

profile_version: "1.0"

# نوع المشاريع الرئيسية:
project_types:
  - بوت / automation     # A
  - API / Backend        # D
  - websites             # B

# Stack المفضل:
primary_stack: Python
secondary_stack: JavaScript

# مستوى الخبرة:
# محترف | متوسط | مبتدئ | متغير (يسأل كل مرة)
level: محترف

# نظام التتبع:
# progress_bar | checkpoint_3 | on_demand | numbered
tracking: progress_bar + checkpoint_3

# صيغة عدد الأسئلة:
# fixed | estimate | phases | by_priority
question_format: phases + by_priority

# التعلم من السياق:
# auto_record | suggest | disabled
context_learning: auto_record + suggest

# عمق الشرح:
# مختصر | متوسط | تفصيلي | ذكي (يسأل) | متدرج
explanation: مختصر

# ميزات إضافية:
extras:
  - best_practices      # اقتراحات تلقائية حسب Stack
  - warnings            # تحذيرات الأخطاء الشائعة
  - smart_compare       # مقارنات ذكية A vs B
  - checkpoints         # نقاط حفظ قابلة للرجوع
```

---

## 📊 Stack-Specific Rules (يُطبَّق تلقائياً)

### Python 🐍
```
💡 Best Practices تلقائية:
  ✅ استخدم dataclass أو Pydantic للـ models
  ✅ Type hints في كل function
  ✅ asyncio.to_thread() للـ sync code داخل async
  MUST NOT: global state | مزج asyncio + threading
  MUST: try/except شامل مع logging
  SHOULD: config من .env مش hardcoded

⚠️ تحذيرات تلقائية:
  • Cloudflare → MUST uc=True في SeleniumBase
  • Selenium → MUST NOT user_data_dir (port conflict)
  • JSON write → MUST atomic (.tmp → .replace)
```

### JavaScript / TypeScript 🟨
```
💡 Best Practices تلقائية:
  ✅ TypeScript مش JavaScript للمشاريع الكبيرة
  ✅ Error boundaries في React
  MUST NOT: any type | callback hell
  SHOULD: async/await مش .then()
```

---

## 🧠 Patterns المكتشفة (Context Learning)

```
# يُملأ تلقائياً بعد كل جلسة

pattern_1: | التكرار: 0/3 | → [اختيار X دايماً]
pattern_2: | التكرار: 0/3 | → [...]
...
```

---

## 📅 سجل الجلسات

| # | المشروع | ADRs | RICE Top | Gates | ملاحظة |
|---|---------|------|----------|-------|--------|
| 1 | [...] | [...] | [...] | 6/6 | — |

**إجمالي الجلسات:** 0
**آخر تحديث للبروفايل:** [...]

---

## 🔄 تحديث البروفايل

```
طريقة التحديث:
1. بعد Onboarding جديد → استبدل الـ yaml أعلاه
2. لو مستواك تغير → غير `level`
3. لو عايز Stack جديد → أضفه في `primary_stack`
4. بعد 10 جلسات → راجع الـ patterns وحدّث

أمر الـ Onboarding: قول للـ AI "ابدأ Onboarding"
```
