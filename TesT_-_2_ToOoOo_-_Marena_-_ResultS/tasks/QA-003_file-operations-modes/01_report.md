# QA-003 — File Operations / Modes

## المشاكل المرتبطة

- `BUG-FILE-001` — Plan قراءة فقط أنتج Review Changes لـ `output.md`.
- `BUG-ACT-002` — Plan/read-only استخدم `auto_chain` و `Execute Edit`.
- `BUG-PATH-004` — analyzed list عرض `R_rewind.ai` كـ `ai/Root`.

## الحكم الحالي

- Chat مناسب نسبيًا للقراءة فقط.
- Plan غير مناسب حاليًا للـ read-only الصارم لأنه ينتج diff/execute edit.

## أهم دليل

```text
auto_chain
Execute Edit
output.md +8 -0
```

## اقتراح إصلاح فقط

- تفعيل read_only intent يمنع execute/edit/actions.
- منع output.md في review-only/read-only.
- تمييز بين تعديل مطبق وتعديل مقترح في Review Changes.
