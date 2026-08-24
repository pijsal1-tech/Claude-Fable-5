# Path Auto-Collection Tests — اختبارات الجمع التلقائي وفتح المسارات

## BUG-PATH-002 — Auto Analyzer حلل ملفات ومسارات خارج المشروع المفتوح رغم طلب عدم فتح فولدر جديد

### الحالة
Open / Confirmed from user transcript

### الخطورة
Critical Candidate

### المشروع المفتوح حسب المستخدم
```text
D:\SMS\1__New_folder
```

### البرومبت
```text
عايزك تراجعلي فكرة مسار الفلو بتاع المشروع من غير ما تفتح أي فولدر جديد
```

### المتوقع
- لا يفتح فولدر جديد.
- لا يحلل ملفات خارج root الحالي إلا لو مرفقة صراحة في نفس الرسالة.
- لا يحلل مسارات من جلسة/سياق سابق.
- يحترم “من غير ما تفتح أي فولدر جديد”.

### الفعلي
الأداة عرضت عناصر Analyzed من مسارات غير متوقعة:
```text
AAA_GGG_iii_VIBE_CODING/groq/Root/مراجعة_وتحليل_المشروع.md
01_check_fb_cookies.py
/SMS/.h
RhRhRhRhRhR/facebook__SMS/01_check_fb_cookies.py
facebook.c
om/profile.php
02_check_fb_cookies.py
.py
من
w1EvgCD5r2DHa9t3
TREE .
SRC __future__
SRC annotations
SRC argparse
```

### التصنيف
Bug في حدود scope/context/path auto collection.

### اقتراح إصلاح فقط — بدون تنفيذ الآن
- إضافة allowlist: auto analyzer لا يقرأ إلا داخل `current_project_root`.
- إذا المستخدم قال “من غير فتح فولدر جديد”، يتم تعطيل path expansion وfolder attach auto-follow.
- إضافة UI indicator يوضح: Current project root + Attached context root.
- إضافة test يمنع تحليل أي file path لا يبدأ بـ current_project_root إلا لو attached explicitly في نفس الرسالة.

### Reproductions

#### Reproduction 1
- التاريخ: 2026-08-06
- المشروع المفتوح: `D:\SMS\1__New_folder`
- النتيجة: ظهرت ملفات `facebook__SMS` و`AAA_GGG_iii_VIBE_CODING` و`/SMS/.h` في analyzed list.


## BUG-PATH-003 — ذكر root الحالي في الرسالة فتح كارت مسار بدل الالتزام بتحليل المشروع الحالي فقط

### الحالة
Open / Confirmed from user transcript

### الخطورة
High

### البرومبت
```text
راجعلي المشروع المفتوح الحالي فقط داخل D:\SMS\1__New_folder. مسموح تستخدم الملفات الموجودة داخل هذا المجلد فقط بما فيها R_rewind.ai لو كان داخله. ممنوع تستخدم أي ملف أو فولدر خارج D:\SMS\1__New_folder، وممنوع تستخدم مرفقات أو سياق قديم. اذكر أسماء أول 5 ملفات اعتمدت عليها.
```

### المتوقع
- طالما المستخدم قال "المشروع المفتوح الحالي فقط" وذكر نفس root، لا ينبغي تعطيل الرد بكارت تغيير مجلد العمل.
- لو المسار هو نفس المشروع الحالي، يتم اعتباره قيد نطاق وليس طلب تبديل مشروع.
- لا يتم تحليل أي شيء خارج root.

### الفعلي
ظهر كارت:
```text
📂 مسار مكتشف
اكتشفت مسار مجلد في رسالتك:
D:\SMS\1__New_folder
ماذا تريد أن أفعل؟
🔄 تغيير مجلد العمل 📎 إرفاق كسياق فقط 💬 تجاهل والمتابعة
```
ثم الرد اعتمد على ملفات غير متوقعة مثل:
```text
.AAA_GGG_iii_VIBE_CODING/groq/Root/مراجعة_وتحليل_المشروع.md
facebook__SMS/Root/مراجعة_وتحليل_المشروع.md
facebook__SMS/test/يوزر_وباس_فقط.txt
```

### التصنيف
Path detection UX bug + scope enforcement bug.

### اقتراح إصلاح فقط — بدون تنفيذ الآن
- إذا المسار المكتشف يساوي current_project_root، لا تعرض كارت "تغيير مجلد العمل".
- تعامل معه كـ تأكيد نطاق scope فقط.
- أضف اختبار: prompt يحتوي current root لا ينتج path_detected_options.
- أضف تحقق أن كل ملفات analyzed تحت current root.


## BUG-PATH-004 — analyzed list يقتطع/يعرض مسار R_rewind.ai كـ ai/Root

### الحالة
Open / Confirmed twice in FILE-001

### الخطورة
Low/Medium

### الدليل
المستخدم طلب مراجعة:
```text
R_rewind.ai/Root/00_CONSTITUTION.md
```
لكن analyzed list عرض:
```text
MD ai/Root/00_CONSTITUTION.md Analyzed
DIR ai Analyzed
DIR Root Analyzed
DIR IP Analyzed
```

### المتوقع
عرض المسار كما هو أو نسبيًا بوضوح:
```text
R_rewind.ai/Root/00_CONSTITUTION.md
```

### الفعلي
تم عرض `ai/Root/...`، مما قد يربك المستخدم ويجعل `R_rewind.ai` يبدو كأنه فقد جزءًا من اسمه.

### اقتراح إصلاح فقط — بدون تنفيذ الآن
- مراجعة formatter الخاص بـ analyzed artifacts.
- التأكد أن النقطة في اسم المجلد `R_rewind.ai` لا تُفسر كامتداد يؤدي لاقتطاع الاسم.
- إضافة test لمسارات تحتوي dot في اسم directory.
