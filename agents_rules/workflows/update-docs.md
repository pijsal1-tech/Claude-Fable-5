---
description: Protocol for updating all documentation files — automatically after every task OR when user says "حدث ملفات" or "شوف ملفات"
---

# /update-docs — بروتوكول تحديث الملفات الإلزامي

> **📌 القاعدة الأهم:**
> 1. **بعد كل task** → حدّث تلقائي بدون ما اليوزر يطلب!
> 2. **لما اليوزر يقول "حدث السجل" أو "حدث ملفات"** → نفس الخطوات.
> 3. **لما اليوزر يقول "شوف ملفات"** → اقرأ الـ 4 ملفات الأساسية من AI_PROVIDERS واستوعبهم!

> **🤖 القراءة التلقائية: الـ AI لازم يقرأ الـ workflow ده لحظي بـ `view_file` من غير ما اليوزر يطلب!**

// turbo-all

---

## ⚠️ قواعد ثابتة (Non-Negotiable):

1. ❌ **مفيش حاجة تتمسح** من أي ملف — إضافة بس!
2. ✅ **كل جديد يتضاف في الآخر** — مش في النص
3. 🔢 **ترقيم مشاكل/دروس README تسلسلي GLOBAL** — آخر رقم في الـ comment
4. 🏷️ **كل مشكلة ليها Tag** — `[API]` `[Script]` `[Config]` etc.
5. 🇪🇬 **كل حاجة بالمصري** — الـ task + الـ commit + كل artifact
6. 🔀 **Git commit مشروط** — لو مفيش تغييرات → مفيش commit!
7. ⛔ **بي ريييب = local بس!** — ممنوع `git push` لبي ريييب نهائياً. الـ push فقط لـ AI_PROVIDERS!

---

## 🗺️ المسارات الثابتة (SSOT) — لا تتغير

> **📌 الـ AI دايماً يقرأ ويكتب من المسارات دي مباشرة — حتى لو شغّال في مشروع بي ريييب!**

| الملف | المسار الوحيد في العالم |
|-------|------------------------|
| `README.md` | `D:\SMS\AI_PROVIDERS\README.md` |
| `GEMINI.md` | `D:\SMS\AI_PROVIDERS\GEMINI.md` |
| `UNIVERSAL_PROVIDER_PROMPT.md` | `D:\SMS\AI_PROVIDERS\UNIVERSAL_PROVIDER_PROMPT.md` |
| `Burp_Suite.md` | `D:\SMS\AI_PROVIDERS\v2\Burp_Suite.md` |

> ⚠️ **ملفوش نسخ في بي ريييب** — الملفات دي موجودة في AI_PROVIDERS بس!

### .agents (يفضل في الاتنين — لازم يتعدلوا في الاتنين):
| الملف | مسار ١ | مسار ٢ |
|-------|--------|--------|
| `update-docs.md` | `D:\SMS\AI_PROVIDERS\.agents\workflows\update-docs.md` | `d:\SMS\بي ريييب\.agents\workflows\update-docs.md` |
| `new-provider.md` | `D:\SMS\AI_PROVIDERS\.agents\workflows\new-provider.md` | `d:\SMS\بي ريييب\.agents\workflows\new-provider.md` |

---

## 🔍 أمر "شوف ملفات"

> **لما اليوزر يقول "شوف ملفات" → اقرأ الـ 4 ملفات الأساسية فوراً!**

```python
# استدعي view_file على كل الـ 4 بالتوازي:
view_file("D:\\SMS\\AI_PROVIDERS\\README.md")           # استوعب الإنجازات + المشاكل + الدروس
view_file("D:\\SMS\\AI_PROVIDERS\\GEMINI.md")           # استوعب القواعد + Patterns
view_file("D:\\SMS\\AI_PROVIDERS\\UNIVERSAL_PROVIDER_PROMPT.md")  # استوعب القواعد + Providers
view_file("D:\\SMS\\AI_PROVIDERS\\v2\\Burp_Suite.md")  # استوعب HAR analysis
```

---

## الخطوات الإلزامية لـ "حدث ملفات" (بالترتيب):

### 1️⃣ حدّث الملفات الأساسية في AI_PROVIDERS:

**`README.md`** → `D:\SMS\AI_PROVIDERS\README.md`
- سجل الإنجازات → `| #رقم | الإنجاز | الملفات |`
- الملفات الجديدة → `| الملف | الوظيفة | الحالة |`
- سجل المشاكل → `| #رقم | [TAG] | وصف | أعراض | سبب | حل | حالة |`
- دروس مستفادة → `| #رقم | [TAG] | الدرس | السياق |`
- **⚠️ آخر رقم مشكلة comment `<!-- آخر رقم مشكلة مستخدم: #XX -->`**

**`UNIVERSAL_PROVIDER_PROMPT.md`** → `D:\SMS\AI_PROVIDERS\UNIVERSAL_PROVIDER_PROMPT.md`
- قاعدة جديدة → قبل comment `⬆️`
- provider جديد → حدث جدول المزودين
- pattern/anti-pattern جديد

**`GEMINI.md`** → `D:\SMS\AI_PROVIDERS\GEMINI.md`
- patterns جديدة / قواعد جديدة

**`Burp_Suite.md`** → `D:\SMS\AI_PROVIDERS\v2\Burp_Suite.md`
- HAR analysis جديد / إنجازات / مشاكل

### 2️⃣ لو عدّلت .agents workflows → حدّث في الاتنين:
```python
# بعد تعديل .agents في AI_PROVIDERS:
shutil.copy(r"D:\SMS\AI_PROVIDERS\.agents\workflows\update-docs.md",
            r"d:\SMS\بي ريييب\.agents\workflows\update-docs.md")
shutil.copy(r"D:\SMS\AI_PROVIDERS\.agents\workflows\new-provider.md",
            r"d:\SMS\بي ريييب\.agents\workflows\new-provider.md")
```

### 3️⃣ Git — AI_PROVIDERS بس يترفع!
```bash
# AI_PROVIDERS — commit + push GitLab
cd "D:\SMS\AI_PROVIDERS"
git add -A
git commit -m "📚 [وصف بالمصري]"
git push origin master

# بي ريييب — commit محلي بس! ⛔ ممنوع push!
cd "d:\SMS\بي ريييب"
git add -A
git commit -m "📚 [نفس الوصف]"
# ⛔ مفيش git push هنا!
```

---

## 🤖 إمتى يتنفذ؟

| الأمر | الفعل |
|-------|-------|
| `"شوف ملفات"` | اقرأ الـ 4 ملفات من AI_PROVIDERS فوراً |
| `"حدث ملفات"` / `"حدث السجل"` / `/update-docs` | عدّل الـ 4 ملفات في AI_PROVIDERS |
| بعد كل task | نفس خطوات "حدث ملفات" تلقائي |

→ **الـ AI ينفذ تلقائي بدون أسئلة!**
