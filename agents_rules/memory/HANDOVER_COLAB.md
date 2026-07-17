# 🚨 HANDOVER TO LOCAL AGENT (CURSOR/WINDSURF)

## 🎯 الهدف الحالي (Current Objective)
استخدام **Google Colab** لفك تشفير وتجميع `blutter` لتخطي مشكلة الـ C++ Compiler على بيئة الويندوز الحالية.

## 🛠️ التعليمات التنفيذية (تعليمات ملزمة للـ Local Agent)
أنت الآن تقرأ هذا الملف بناءً على توجيهات Antigravity (Vibe Coder). 

1. اطلب من المستخدم فتح `https://colab.research.google.com/` وإنشاء Notebook جديد.
2. اطلب من المستخدم وضع هذا الكود في أول خلية (Cell) وتشغيلها:
   ```bash
   !git clone https://github.com/worawit/blutter.git
   %cd blutter
   !pip install -r requirements.txt
   ```
3. اطلب من المستخدم رفع `libapp.so` و `libflutter.so` إلى مسار `/content/` في Colab. (بمجرد أن تشرح له الأمر، ذكره أن الملفات موجودة محلياً في `d:\SMS\.hRhRhRhRhRhR\AI_Parallel_Runner\تطبيق\`).
4. أعط للمستخدم الأمر التالي لتشغيل Blutter وفك التطبيق:
   ```bash
   !python blutter.py /content/ /content/blutter_out --rebuild
   ```
5. بعد انتهاء خطوة الفك، اطلب من المستخدم تنفيذ هذا الأمر لاستخراج دالة التشفير مباشرة:
   ```bash
   !grep -ri "security\|encrypt\|RSA\|cipher\|sign" /content/blutter_out/pp.txt
   !grep -ri "security\|encrypt" /content/blutter_out/asm/*
   ```
6. أخيراً، اطلب من المستخدم تحميل مجلد `blutter_out` (أو ملفات البحث الناتجة) ووضعها في الـ Workspace هنا، واكتب أنت (أيها الـ Local Agent) في `tasks.md` أن المهمة تمت لكي يقرأها Antigravity ونكمل بناء السكربت.

**توقف هنا ونفذ الخطوات فوراً مع المستخدم وتأكد من توجيهه بوضوح.**
