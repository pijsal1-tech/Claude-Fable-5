# 🧠 Memory System — دليل الاستخدام

> أنت الـ AI - اقرأ الملفات دي في بداية كل محادثة عشان تفهم سياق المستخدم

## 📁 الملفات وأهميتها

| الملف | المحتوى | متى تقرأه |
|-------|---------|-----------|
| `style_prefs.md` | أسلوب التواصل + تفضيلات العمل | **دايماً** في أول المحادثة |
| `automation_patterns.md` | flows + patterns + sequences المعروفة | لما الطلب فيه automation |
| `provider_knowledge.md` | معرفة الـ providers + قراراتهم | لما تضيف/تعدل provider |
| `decisions_log.md` | قرارات تقنية مهمة اتخدت | قبل ما تقترح حاجة جديدة |
| `promptcowboy_knowledge.md` | 🤠 PromptCowboy كامل: Flow + Action IDs + مشاكل | **لما تشتغل على PromptCowboy** |

## ⚡ طريقة الاستخدام

### AI يقرأ:
```bash
# في بداية أي session مهم — اقرأ الملفات دي:
type .agents\memory\style_prefs.md
type .agents\memory\provider_knowledge.md
```

### AI يضيف:
لما تعرف معلومة جديدة عن المستخدم → ضيفها في الملف المناسب:
```
✅ زيزو يفضل curl_cffi على requests لأي تطبيق جديد
✅ zizo بيشتغل دايماً بـ LOOP_MODE = True
```

### مشروع جديد:
```
خد نسخة من مجلد .agents/memory/ + حطه في مشروعك الجديد
→ الـ AI هيبدأ فاهم أسلوبك من اللحظة الأولى
```

---
*آخر تحديث: تلقائي من الـ AI بعد كل session مهم*
