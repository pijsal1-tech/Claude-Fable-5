# QA-001 — Context / Attachments / Security

## المشاكل المرتبطة

- `BUG-CTX-001` — عدم اتساق بين سياق المشروع الحالي والملفات التي يعتمد عليها الرد.
- `BUG-ATT-001` — attached-content خارجي يظهر رغم طلب عدم استخدام مرفقات أو سياق قديم.
- `BUG-AUTO-001` — أمر `لا تحلل المشروع` لم يمنع `TREE . Analyzed`.
- `BUG-SEC-003` — auto-analysis حلل `acco33unts.txt` رغم منع صريح.

## الحكم الحالي

القسم غير جاهز للاستخدام الآمن قبل إصلاح auto-analysis وsensitive file denylist.

## أعلى دليل

```text
SAFE
TXT acco33unts.txt Analyzed
TREE . Analyzed
```

## اقتراح إصلاح فقط

- Zero Context Mode فعلي.
- Runtime denylist بناءً على أمر المستخدم.
- Sensitive filename classifier قبل إدخال الملفات إلى context.
- فصل واضح بين `system_project_context` و `user_attached_files` و `stale_external_context`.
