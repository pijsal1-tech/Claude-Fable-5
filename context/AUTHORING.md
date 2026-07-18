# دليل كتابة مصدر سياق جديد (R-201) — stub

كل مصدر يطبّق بروتوكول `ContextSource` من `context/engine.py`:

```python
from context.engine import ContextItem, ContextRequest, ProjectScan

class MySource:
    kind = "my_source"          # معرّف provenance فريد وثابت

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        ...
```

## القواعد الملزمة

1. **ممنوع المشي الشجري.** لا `rglob` / `walk` / `iterdir` داخل المصدر —
   اعمل على `scan.files` (القائمة المفروزة الجاهزة) فقط. المحرّك ينفّذ
   `ProjectScan` **واحدًا** لكل `gather()` ويشاركه بين كل المصادر؛ هذا هو
   الإصلاح الأدائي المركزي لـ R-201 (legacy كان O(files × words) لكل
   رسالة). اختبار `test_mention_source_does_no_tree_walk` يوضح كيف
   تفرض ذلك على مصدرك.
2. **provenance دائمًا.** كل `ContextItem` يحمل `source_kind = self.kind`.
3. **المحتوى المتعذر = `None`**، لا سلسلة فارغة — العنصر "مذكور بلا
   محتوى" حالة مشروعة (راجع quirk الـ huge_file المثبّت في goldens T-017).
4. **لا ترمِ استثناءات للمستهلك.** المحرّك يعزل المصدر المعطوب (تسامح
   legacy)، لكن التزم داخليًا بالتعامل مع أخطاء I/O المتوقعة بنفسك.
5. **الحتمية.** أي تكرار على مجموعات → `sorted(...)` أولًا. مخرجات
   المصدر يجب أن تكون قابلة للتثبيت في golden.
6. **الحدود صادقة.** أي حد أقصى يكون برقم حقيقي وتعليق مطابق —
   لا نكرر `MAX_MENTIONED = 100  # حد أقصى 10 ملفات`.

## الاختبارات المطلوبة لكل مصدر جديد

- وحدات لسلوك المطابقة/الترتيب/الحدود.
- اختبار "لا مشي شجري" (monkeypatch على `pathlib.Path.rglob` يرمي).
- لو المصدر يعوّض سلوك legacy موجود: goldens parity أولًا (نمط T-017).

*(يتوسع هذا الدليل مع KeywordSource / ProjectStructureSource /
HistorySource في مهام R-201 التالية.)*
