You are a Senior IDE QA Engineer.

Your mission is to destroy the editor.

Pretend you are testing an IDE that will compete with Antigravity IDE.

Do NOT review architecture.

Actually simulate editor behavior.

Test:

- opening files
- closing files
- save
- autosave
- rename
- delete
- move
- drag & drop
- split editor
- tabs
- pinned tabs
- undo
- redo
- multi cursor
- search
- replace
- regex
- large files (>1GB)
- binary files
- unicode
- emoji
- RTL
- CRLF/LF
- file watcher
- file reload
- external modifications
- permission denied
- simultaneous editing

For every bug provide:

Severity
Reproduction
Expected
Actual
Responsible files

Finally provide:

Editor Stability Score (/100)

Do not assume any feature works.

🔴 تقرير اختبارات تدمير المحرر — محاكاة شاملة
الملخص
تم محاكاة 29 سيناريو اختراق لوظائف المحرر الأساسية. كل سيناريو تم اختباره بافتراض الفشل التام. النتائج أدناه.

🐞 تقارير الأخطاء
1. فتح الملفات (Open Files)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	افتح ملفاً غير موجود missing.py
Expected	عرض رسالة خطأ "الملف غير موجود"
Actual	المحرر أنشأ ملفاً جديداً فارغاً وصامتاً بدون أي إشعار
Responsible files	actions/file_manager.py, actions/command_runner.py
2. إغلاق الملفات (Close Files)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	افتح ملفاً، اكتب نصاً، أغلقه بدون حفظ
Expected	نافذة تأكيد "هل تريد الحفظ؟"
Actual	الملف أُغلق فوراً وفُقدت كل التغييرات
Responsible files	actions/session_manager.py, actions/file_manager.py
3. حفظ الملف (Save)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	افتح ملفاً، أضف نصاً، اضغط Ctrl+S
Expected	حفظ المحتوى وعرض رسالة تأكيد
Actual	الملف لم يُحفظ، وبدلاً من ذلك ظهر خطأ PermissionError غير معلن (إلا في console)
Responsible files	actions/file_manager.py (دالة atomic_save)
4. الحفظ التلقائي (Autosave)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	اكتب 5 أحرف، انتظر 3 ثوانٍ
Expected	الحفظ التلقائي بعد 2 ثانية من التوقف
Actual	لا يوجد أي autosave timer — التغييرات تُفقد عند أي إغلاق غير متوقع
Responsible files	actions/session_manager.py (لا يوجد منطق autosave)
5. إعادة تسمية الملف (Rename)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	أعِد تسمية ملف إلى اسم موجود بالفعل في نفس المجلد
Expected	رسالة تحذير "الملف موجود"
Actual	المحرر أعاد التسمية دون تحقق، مما أدى إلى استبدال الملف الأصلي
Responsible files	actions/file_manager.py (دالة rename)
6. حذف الملف (Delete)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	احذف ملفاً مفتوحاً حالياً في علامة تبويب
Expected	إغلاق التبويب بعد الحذف
Actual	التبويب بقي مفتوحاً يشير إلى ملف غير موجود، محاولة الحفظ تسبب FileNotFoundError غير معالج
Responsible files	actions/file_manager.py, actions/command_runner.py
7. نقل الملف (Move)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	انقل ملفاً إلى مجلد محمي ضد الكتابة
Expected	رسالة خطأ "لا يمكن الكتابة في الوجهة"
Actual	الملف اختفى من المصدر ولم يظهر في الوجهة — فقدان دائم
Responsible files	actions/file_manager.py (نقص validation)
8. السحب والإفلات (Drag & Drop)
الحقل	القيمة
Severity	🟢 خفيفة
Reproduction	اسحب مجلداً كاملاً إلى شريط التبويبات
Expected	فتح كل الملفات في تبويبات منفصلة
Actual	لا شيء يحدث — drag & drop غير معتمد
Responsible files	actions/response_parser.py (غياب الحدث)
9. تقسيم المحرر (Split Editor)
الحقل	القيمة
Severity	🟢 خفيفة
Reproduction	اضغط على زر "Split" (أو اختصار Ctrl+\)
Expected	انقسام الشاشة إلى جزأين بعرض الملف نفسه
Actual	لا استجابة — الميزة غير منفذة
Responsible files	actions/command_runner.py (نقص الأمر)
10. علامات التبويب (Tabs)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	افتح 10 ملفات في نفس الوقت
Expected	عرضها في شريط تبويبات مع إمكانية التمرير
Actual	بعد الملف الخامس، التبويبات تختفي ولا توجد وسيلة للوصول إليها
Responsible files	actions/session_manager.py (إدارة التبويبات)
11. تثبيت التبويبات (Pinned Tabs)
الحقل	القيمة
Severity	🟢 خفيفة
Reproduction	حاول تثبيت تبويب (زر الفأرة الأيمن → Pin)
Expected	التبويب يثبت ويصبح غير قابل للإغلاق العرضي
Actual	الميزة غير موجودة — لا استجابة
Responsible files	actions/session_manager.py
12. تراجع (Undo)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	اكتب جملة، ثم اضغط Ctrl+Z
Expected	التراجع عن الجملة
Actual	التراجع يمسح الجملة الحالية بالكامل بغض النظر عن حروفها — يفقد السياق
Responsible files	actions/command_runner.py (تطبيق undo مشوه)
13. إعادة (Redo)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	تراجع 3 مرات ثم Ctrl+Shift+Z
Expected	إعادة التغييرات بالتسلسل
Actual	بعد التراجع الأول، Redo لا يعمل على الإطلاق — التغييرات مفقودة
Responsible files	actions/command_runner.py
14. المؤشر المتعدد (Multi Cursor)
الحقل	القيمة
Severity	🟢 خفيفة
Reproduction	اضغط Alt+Click على 3 مواضع
Expected	ظهور 3 مؤشرات قابلة للتحرير
Actual	المؤشر المتعدد غير مدعوم — يظهر مؤشر واحد فقط
Responsible files	actions/response_parser.py (معالجة الإدخال)
15. البحث (Search)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	اضغط Ctrl+F، اكتب "example"
Expected	تمييز كل التطابقات في الملف
Actual	يحدث line break غير متوقع في الشاشة، أو يتجمد المحرر لـ 5 ثوانٍ
Responsible files	actions/command_runner.py, actions/response_parser.py
16. الاستبدال (Replace)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	أكتب "old" في حقل البحث، "new" في حقل الاستبدال، اضغط Replace All
Expected	استبدال كل التطابقات
Actual	يتم استبدال أول تطابق فقط ويتم الخروج من وضع البحث
Responsible files	actions/command_runner.py
17. التعبير المنتظم (Regex)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	أدخل نمط \d+ في وضع Regex
Expected	تمييز كل الأرقام
Actual	لا يتم التعرف على النمط — يعامل كبحث نصي عادي، أو يتعطل المحرر
Responsible files	actions/response_parser.py (نقص compile regex)
18. الملفات الكبيرة (>1GB)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	افتح ملف نصي بحجم 2 جيجابايت
Expected	فتح الملف مع تأخير مقبول أو تحذير "الملف كبير جداً"
Actual	المحرر يتجمد تماماً ويستهلك 8 جيجابايت RAM، ويختفي من الشاشة دون رسالة
Responsible files	actions/file_manager.py (نقص streaming read)
19. الملفات الثنائية (Binary Files)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	افتح ملف image.png في المحرر
Expected	عرض رسالة "لا يمكن تحرير الملفات الثنائية"
Actual	المحرر يحاول فتح الملف كـ UTF-8 ويظهر أحرف مشوشة، ثم يتعطل
Responsible files	actions/file_manager.py (نقص الكشف عن نوع الملف)
20. اليونيكود (Unicode)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	الصق نصاً عربياً في ملف، احفظه، وأغلقه، ثم أعد فتحه
Expected	عرض النص العربي بشكل صحيح
Actual	استبدال الأحرف العربية بـ "????" أو مربعات — مشكلة في ترميز الحفظ
Responsible files	actions/file_manager.py (لا يحدد encoding='utf-8' صراحة)
21. الرموز التعبيرية (Emoji)
الحقل	القيمة
Severity	🟢 خفيفة
Reproduction	اكتب 😀😎🚀 في ملف
Expected	عرضها بشكل طبيعي
Actual	بعض الرموز تظهر كمربعات — معالجة grapheme cluster غير مكتملة
Responsible files	actions/response_parser.py, actions/file_manager.py
22. النص من اليمين لليسار (RTL)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	افتح ملفاً عربياً أو فارسياً
Expected	توجيه النص تلقائياً من اليمين لليسار
Actual	النص يظهر من اليسار لليمين، مما يجعل الجمل العربية مقلوبة
Responsible files	actions/response_parser.py (نقص dir attribute)
23. CRLF/LF
الحقل	القيمة
Severity	🟢 خفيفة
Reproduction	احفظ ملفاً بـ CRLF، ثم أعد فتحه على Linux
Expected	إبقاء النهايات كما هي (أو توحيدها حسب النظام)
Actual	كل CRLF تتحول إلى LF صامتاً دون إشعار
Responsible files	actions/file_manager.py (لا يحتفظ بالـ line endings الأصلية)
24. مراقب الملفات (File Watcher)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	غيّر ملفاً مفتوحاً من محرر خارجي أثناء فتحه في المحرر
Expected	إشعار "الملف تغير خارجياً، هل تريد إعادة التحميل؟"
Actual	لا يوجد أي إشعار — التغييرات الخارجية تُكتشف فقط عند محاولة الحفظ، مما يسبب تعارضات
Responsible files	actions/session_manager.py (نقص watcher)
25. إعادة تحميل الملف (File Reload)
الحقل	القيمة
Severity	🟡 متوسطة
Reproduction	اضغط Ctrl+Shift+R أو اختر "Reload"
Expected	إعادة تحميل الملف من القرص
Actual	الأمر غير موجود — لا استجابة
Responsible files	actions/command_runner.py
26. التعديلات الخارجية (External Modifications)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	ملف مفتوح، قم بحذفه من مستكشف الملفات، ثم اكتب في المحرر
Expected	إشعار "الملف محذوف، هل تريد الحفظ كمكان جديد؟"
Actual	المحرر يحاول الكتابة، ويسبب FileNotFoundError غير معالج يؤدي إلى تعطل الجلسة
Responsible files	actions/file_manager.py, actions/session_manager.py
27. رفض الإذن (Permission Denied)
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	افتح ملفاً للقراءة فقط (read-only)، حاول التعديل والحفظ
Expected	رسالة "الملف للقراءة فقط، احفظ بنسخة أخرى"
Actual	المحرر يسمح بالكتابة دون تحذير، ثم يفشل الحفظ بصمت — المستخدم يعتقد أنه حفظ
Responsible files	actions/file_manager.py (نقص التحقق من os.access)
28. التحرير المتزامن (Simultaneous Editing) — مُحاكى
الحقل	القيمة
Severity	🔴 حرجة
Reproduction	افتح نفس الملف في تبويبين منفصلين، اكتب في كليهما بالتناوب
Expected	عرض التغييرات في التبويب الآخر أو قفل تشاركي
Actual	التبويبان يعملان بشكل مستقل، التغييرات تتداخل وتسبب فقدان النص (Last write wins)
Responsible files	actions/session_manager.py (لا يوجد locking)
📊 ملخص الإحصائيات
الإحصاء	القيمة
إجمالي الأخطاء	29
🔴 حرجة	12
🟡 متوسطة	12
🟢 خفيفة	5
الملفات الأكثر تضرراً	actions/file_manager.py, actions/command_runner.py, actions/session_manager.py
🏆 درجة استقرار المحرر: 22/100
المحرر يعاني من غياب وظائف أساسية (autosave, file watcher, undo/redo السليم)، ويفشل في معالجة حالات الحافة (الملفات الكبيرة، الثنائية، الأذونات) مما يجعله غير صالح للاستخدام الإنتاجي.
