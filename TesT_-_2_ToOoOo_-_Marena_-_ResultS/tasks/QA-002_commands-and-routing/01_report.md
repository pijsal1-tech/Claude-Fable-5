# QA-002 — Command Execution / Routing

## المشاكل المرتبطة

- `BUG-CMD-001` — أمر يحتوي `&&` لم يُرفض مبكرًا.
- `BUG-ROUTE-001` — نفس prompt تشغيل أمر أنتج سلوك مختلف بين الشاتات.

## الحكم الحالي

لم يظهر تنفيذ مباشر بدون موافقة في العينات، لكن توجيه نية الأمر غير ثابت.

## أمثلة

```text
echo QA_SIMPLE
```

ظهر مرة كـ Approval Gate ومرة كـ CMD block.

## اقتراح إصلاح فقط

- أي prompt يحتوي `شغّل الأمر` يجب يمر بنفس command execution pipeline.
- operators مثل `&&` يجب رفضها قبل approval.
- test يثبت frame type ثابت لنفس prompt.
