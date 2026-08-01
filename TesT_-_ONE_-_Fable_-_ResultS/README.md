# TesT_-_ONE_-_Fable_-_ResultS — مخرجات المحلل الخارجي

> **الوضع:** Sandbox قراءة فقط — كل الكتابة داخل هذا المجلد حصريًا،
> بلا أي git commit/push من المحلل، وبلا ملفات تنفيذية (.py/.js/.sh).
> **القاعدة (Base) وقت التحليل:** `91b8c4c` — `git log --oneline -3`:
> ```
> 91b8c4c Delete TesT_-_ONE_-_ResultS/1
> 58d7458 Delete TesT_-_ONE_-_ResultS/TesT_-_ONE_-_ResultS directory
> c7a80af Add files via upload
> ```
> **إعادة تحقق:** الباتش أعيد فحصه بـ `git apply --check` بنجاح أيضًا على
> `853ba4f` (كومِت بوت الرفع التلقائي الذي أضاف ملفات هذا المجلد) —
> لأن الكومِت لم يمس أي ملف كود.

## المهمة الحالية

**TSK-504** — حادثة شات على موديل `glm-5.2-vercel` أثناء `delegate`:
1. رموز ANSI خام (`[91m` / `[0m`) ظاهرة في واجهة الشات.
2. `curl: (28) Operation timed out after 300004 milliseconds` — تعليق 300s
   ثم فشل نهائي بلا تحويل تلقائي لمزود بديل.

## كيف تقرأ هذا المجلد

| الترتيب | الملف | المحتوى |
|--------|-------|---------|
| 1 | `000_project_understanding/01_report.md` | فهم المشروع وخريطة المسار المعماري للحادثة |
| 2 | `tasks/TSK-504_ansi-and-timeout/01_report.md` | الأدلة (path:line + نواتج أوامر فعلية)، 3 أسباب جذرية، قسم «مطلوب من المالك» |
| 3 | `tasks/TSK-504_ansi-and-timeout/02_proposed.patch` | الباتش (unified diff) — **متحقق بـ `git apply --check`** |
| 4 | `tasks/TSK-504_ansi-and-timeout/03_verdict.md` | الحكم (APPLY)، المخاطر، أثر البوابات، ومرجع كود الاختبار كـ fences |
| — | `INDEX.md` | فهرس آلي مختصر |

## خلاصة من سطر واحد

التعقيم يُحقن عند **بوابة النقل الأوحد** (`_WSAdapter._send` — server.py:369)،
والـ failover يُفعَّل بتوجيه نداءات `DelegateBridge` الثلاثة إلى
`provider_pool.send_with_fallback` الجاهز أصلًا (providers/pool.py:291) —
مع سقوط سلس للمسار القديم؛ ومنبع المهلة (300s) داخل `providers/blackbox.py`
**المفقود من الريبو** → مطلوب من المالك (تفاصيل في 01_report.md §6).

## نتائج التحقق (مختصر)

| الفحص | النتيجة |
|-------|---------|
| `git apply --check 02_proposed.patch` من جذر الريبو | ✅ exit 0 |
| mypy (أعلام `scripts/check.sh`) على `server.py` + `chain/delegate.py` المعدّلين | ✅ Success: no issues |
| تحقق سلوكي معزول (strip_ansi × 4 حالات + failover × 3 مسارات) | ✅ 7/7 PASS |
| نظافة الريبو أثناء العمل (`git status --porcelain` قبل إنشاء هذا المجلد) | ✅ فارغ |
