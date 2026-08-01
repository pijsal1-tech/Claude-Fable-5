# 🐛 [TSK-502 / FIX-02] تقرير هندسي نهائي: تنظيف رموز ألوان ANSI ومعالجة أخطاء مهلة الشبكة (Timeout)

---

## 📌 1. المتاع والمعرّف التوثيقي (Metadata)
- **رمز المهمة**: `TSK-502` (المعروف بـ `FIX-02`)
- **المكونات المتأثرة**: `providers/base.py` ، `core/chat_dispatch.py` ، و `static/js/stream_render.js`
- **السياسة المتبعة**: D-8-أ (تنظيف مخرجات الواجهة والتجاوب مع أخطاء المزودين)
- **إصدار التحديث المرتقب**: `v1.0.0-rc.2` (تحت قسم `[Fixed]` في `CHANGELOG.md`)
- **التصنيف**: `[UI-UX]` / `[Debug]` / `[Network]` / `[ANSI-Filter]`

---

## 🔍 2. الأعراض والأدلة المباشرة (Observed Symptoms)

عند توقف أو تأخر استجابة الموديل (مثل `Blackbox AI / glm-5.2-vercel`) لأكثر من 300 ثانية (5 دقائق):
1. **ظهور أخطاء مهلة الشبكة**:
   ```
   curl: (28) Operation timed out after 300004 milliseconds with 0 bytes received
   ```
2. **تلوث واجهة المستخدم برموز ANSI الخام**:
   تظهر الأكواد الخام مثل `\033[91m` أو `[91m` في نص الرسالة بدلاً من عرض النص العربي النظيف المنسق.

---

## 🧩 3. التحليل الهندسي والجذور الثلاثة للمشكلة (Root Causes)

| # | السبب الجذري | التوصيف الفني |
|---|---|---|
| **1** | **غياب فلتر ANSI في السيرفر** | الـ Providers تلقي باستثناءات الألوان الحية في الـ Terminal دون فلترة للأكواد (`\x1b[91m...`) |
| **2** | **عدم الفلترة في الـ Stream Render** | الواجهة (`stream_render.js`) لا تقوم بـ Regex Strip لرموز الألوان قبل حقن النص في الـ DOM |
| **3** | **عدم وجود رسائل عربية صديقة للمستخدم** | رسالة الخطأ الخام تسرب تفاصيل الشبكة والـ Curl للمستخدم النهائي بدلاً من رسالة خطأ منظمة |

---

## 🔧 4. التكنيك الهندسي المحكم للإصلاح (Production Patch Architecture)

### أ. دالة الفلترة في بايثون (`providers/base.py` / `core/chat_dispatch.py`):

```python
import re

def strip_ansi_codes(text: str) -> str:
    """TSK-502: تنظيف أكواد ألوان ANSI الخام لمنع تلوث واجهة الشات"""
    if not text:
        return ""
    # الـ Regex الشامل لتنظيف كل تسلسلات ألوان ANSI
    ansi_escape = re.compile(r'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', text)
    # تنظيف متبقيات الألوان المقطوعة مثل [91m و [0m
    cleaned = re.sub(r'\[\d{1,2}m', '', cleaned)
    return cleaned.strip()
```

### ب. فلترة الواجهة بـ JavaScript (`static/js/stream_render.js`):

```javascript
function cleanAnsiColors(text) {
    if (!text) return "";
    return text.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
               .replace(/\[\d{1,2}m/g, '');
}
```

---

## 🧪 5. مصفوفة حالات الاختبار الحرجة (Required Test Cases)

| # | حالة الاختبار | المحتوى المدخل | النتيجة المتوقعة |
|:---:|---|---|---|
| **1** | `test_ansi_red_strip` | `\033[91mError\033[0m` | `Error` نظيفة بدون رموز |
| **2** | `test_curl_timeout_28` | استجابة timeout بعد 300 ثانية | رسالة توضح تعذر الاتصال بالمزود بلغة عربية سريعة |
| **3** | `test_clean_stream_render` | إطار WS يحتوي على `[91mText` | عرض `Text` بلون الخطأ المنسق بالـ CSS فقط |

---

## ✅ 6. التغييرات المتوقعة عند التطبيق

1. **القبل**: ظهور `[91m❌ [Blackbox AI] خطأ في الاتصال: Failed...[0m`
2. **البعد**: `❌ خطأ في الاتصال بالمزود: انتهت مهلة الانتظار (Timeout). يرجى المحاولة لاحقاً أو اختيار موديل آخر.`
