# Provider Failure Tests — اختبارات فشل المزودين والشبكة

## BUG-PROV-001 — ظهور 429 من Blackbox كرسالة خام مع ANSI وبدون fallback واضح

### الحالة
Open / Confirmed from user transcript

### الخطورة
Medium إلى High حسب هل يوجد fallback فعلي أم لا.

### البرومبت المرتبط
```text
عايزك تراجعلي فكرة مسار الفلو بتاع المشروع من غير ما تفتح أي فولدر جديد
```

### المتوقع
- عند 429، تظهر رسالة مفهومة بدون ANSI escape codes.
- يتم fallback لمزود آخر إن كان متاحًا.
- لا يتم بعدها جمع سياق عشوائي/قديم.
- يتم تسجيل rate limit كحدث واضح.

### الفعلي
ظهر للمستخدم:
```text
[91m❌ [Blackbox AI] فشل الطلب (429): {"error":{"message":"blackbox.Error: AzureException RateLimitError - {
 "error": {
 "message": "Your requests to gpt-5.5 for gpt-5.5 in swedencentral have exceeded rate limit.",
 "type": "too_many_requests",
 "param": null,
 "code": "rate_limit_exceeded"
 }
}. Re[0m
```

ثم ظهر جمع تلقائي لمعلومات من مسارات غير متوقعة.

### التصنيف
Provider failure UX + possible fallback/context coupling bug.

### اقتراح إصلاح فقط — بدون تنفيذ الآن
- تنظيف ANSI من رسائل provider قبل عرضها في UI.
- تصنيف 429 كـ rate_limit مع retry_after/fallback واضح.
- فصل فشل provider عن context gathering حتى لا يعيد استخدام سياق قديم أو يبدأ تحليل عشوائي.
- إضافة اختبار provider 429 يتوقع رسالة UI نظيفة وفallback مضبوط.
