# 🧠 Philosophy — Requests First!

> **🚨 القاعدة الذهبية:** كل حاجة ممكن تتعمل بـ HTTP requests = **اعملها requests!**
> Selenium = آخر حل فقط لما مفيش بديل.

---

## 🎯 المهمة

أنت مطلوب منك تبني سكريبتات تسجيل وتجديد لـ AI Provider.

**هتاخد:**
- ملف نصّي فيه **curls** أو **عناصر الصفحة** أو الاتنين

**هتطلّع:**
- `register.py` — إنشاء حسابات
- `refresh.py` — تجديد credentials (فيه `def refresh(email: str) -> bool`)
- `accounts.json` — format موحد

---

## ⚡ القرار — Requests ولا Selenium ولا Hybrid?

### لو اديتك curls كاملة:
**المطلوب:** حوّلهم لـ `requests` / `curl_cffi` Python code.
- استخرج tokens/headers ديناميك من كل response وحطهم في الـ request اللي بعده
- Session object واحد يحافظ على الكوكيز
- مفيش متصفح خالص ✅

### لو اديتك عناصر صفحة (CSS selectors):
**المطلوب:** شوف هل ممكن تعملها requests ولا لازم Selenium.
- لو الموقع عنده API endpoints → **استخدم requests**
- لو مفيش API والـ DOM بيعتمد على JavaScript → **Selenium**

### النظام الهجين (الأذكى 🧠):
لو الموقع فيه حماية (Cloudflare, hCaptcha...) بس الـ API endpoints موجودة:
1. **افتح المتصفح مرة واحدة** → اعدّي الحماية → اجمع التوكنات/الكوكيز
2. **اقفل المتصفح**
3. **كمّل كل حاجة requests** — التسجيل، التحقق، التجديد

```python
# ═══ مثال هجين ═══
# Step 1: متصفح يمر الحماية ويجمع tokens
with SB(uc=True) as sb:
    sb.uc_open("https://example.com")
    cf_clearance = sb.get_cookie("cf_clearance")
    csrf_token = sb.execute_script("return document.querySelector('meta[name=csrf]').content")

# Step 2: requests تكمل الباقي (أسرع 100x)
session = requests.Session()
session.cookies.set("cf_clearance", cf_clearance)
session.headers["x-csrf-token"] = csrf_token

# التسجيل
resp = session.post("https://example.com/api/register", json={...})
# التحقق
resp = session.post("https://example.com/api/verify", json={...})
# كل حاجة بـ requests! ✅
```

---

## جدول القرار السريع:

| المعطيات | المسار | الملف |
|----------|--------|-------|
| curls كاملة + مفيش حماية | **Level 1: Requests** | `02-requests-level1.md` |
| curls + Cloudflare/hCaptcha | **Level 2: Hybrid** | `03-hybrid-level2.md` |
| عناصر صفحة + مفيش API | **Level 3: Selenium** | `03-hybrid-level2.md` |
| مفيش curls ولا عناصر | **اعمل HAR أولاً** | `02-har-analysis.md` |
