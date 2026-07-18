# تدفق السياق (R-201 / T-019)

## الصورة الكاملة

```
WS "message" (server.py)
        │  user_text
        ▼
gather_message_context(fm.root, user_text)          ← النداء الوحيد في المعالج
        │  (context/facade.py)
        ▼
ContextEngine.gather(ContextRequest)
        │
        │  ProjectScan(root)  ← rglob("*") مفروز — مسح واحد للرسالة كلها
        │
        ├─► MentionSource   kind="mention"    exact-name matching
        │       أسماء بامتداد (config.json, src/app.js) ضد p.name
        │
        ├─► KeywordSource   kind="keyword"    stem matching المرن
        │       كلمات ≥3 أحرف بلا امتداد (database) ⊂ p.name
        │
        └─► StructureSource kind="structure"  بنية المشروع
                عنصر واحد <project_structure> = get_project_context()
        ▼
ContextBundle (مرتّب، first-wins على (source_kind, path)
               + T-021: sha256 content-dedupe — الجسد المكرر إحالة)
        ▼
facade: دمج mention→keyword بـ path-dedupe + حد إجمالي MAX_MENTIONED_FILES=10
        ▼
MessageContext:
  • mentioned_files        → routing (files_dict / file_content_for_routing)
  • user_text_with_files   → البرومبت (حقن legacy الحرفي render_legacy_injection)
  • project_context        → system prompt / agent loop
```

## عقود الـ parity

- **goldens T-017** (`tests/goldens/context/*.golden.json`) هي المرجع
  البايت-بايت لما يراه الموديل. `test_facade_matches_goldens` يعيد الستة
  عبر نفس النداء الذي يستدعيه المعالج.
- ترتيب legacy محفوظ: exact-matches أولًا ثم stem-matches، بلا تكرار،
  بحد إجمالي واحد.
- quirks محفوظة: huge-file يُذكر في العنوان بلا محتوى (`content=None`)؛
  فشل بناء البنية = سلسلة فارغة.

## الفرق الأدائي عن الكتلة القديمة

| | legacy (server.py المضمّنة) | ContextEngine |
|---|---|---|
| مشيات الشجرة لكل رسالة | `rglob` لكل اسم كامل **ولكل** جذع — O(files × words) | **1** (`ProjectScan`) |
| الحد | `MAX_MENTIONED = 100` بتعليق يدّعي 10 | `MAX_MENTIONED_FILES = 10` صادق |
| الاختبارات | صفر | goldens + وحدات + فرض "لا مشي شجري" |

## أين يقف الاستخراج الآن

- ✅ معالج WS (`message`) — يستدعي الـ facade (T-019).
- ✅ `chain/context_builder.py` — مُكيّف رقيق فوق الـ engine (T-020):
  `gather()` ينفّذ `ProjectScan` **واحدًا** ويمرره لكل المراحل؛ كل
  مسارات الـ rglob المكررة (fallback القراءة بالاسم + مسح البحث النصي +
  iterdir المجلدات) حُذفت لصالح فلترة `scan.files` في الذاكرة. سلوكه
  مثبّت بالـ goldens في `tests/goldens/chain/` (items + progress events
  + summary + prompt section) وبفرض هيكلي/سلوكي في
  `tests/unit/test_context_builder_convergence.py` (لا rglob في الملف؛
  مسح واحد بالضبط لكل gather).
- ✅ `AgentLoop._auto_prefetch` — يفوّض للمُكيّف أعلاه (T-020)؛ إطارات
  WS ونقل النتائج للـ Knowledge بلا تغيير (نفس عقد الـ goldens).
- ✅ `ContextBundle` انتقلت إلى `context/bundle.py` (T-021 / R-202) مع
  طبقة dedupe ثانية بالمحتوى (sha256): مفتاح الهوية `(source_kind,
  path)` يرفض المكرر (عقد T-018 بلا تغيير)، ومفتاح المحتوى يقبل
  الإدخال لكن كـ **reference** (`BundleEntry.is_reference` +
  `duplicate_of`). `render_prompt_block()` يطبع كل جسد مرة واحدة
  وملاحظة إحالة للبقية؛ `debug_dump()` يجيب عن «ليه الموديل شاف
  X؟» (index/source/path/hash/chars/reference — JSON-serializable).
  الـ facade وgoldens T-017/T-019 لم تتأثر: `items`/`paths` تُظهر
  الإحالات كعناصر كاملة بمحتواها — الـ renderer وحده من يَلزم
  بالإزالة. huge-file quirk محفوظ: `content=None` لا يُهَش ولا يكون
  إحالة.
- ⏳ توجيه map_reduce عبر الحزمة (≥40% تخفيض) — T-022.
- ⏳ `HistorySource` وميزانية render — T-023+/R-203.

لكتابة مصدر جديد راجع `context/AUTHORING.md` (القواعد الملزمة).
