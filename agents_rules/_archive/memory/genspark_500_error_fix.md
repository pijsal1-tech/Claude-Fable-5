# 🔴 Memory: مشكلة 500 Error — project_id قديم

## ✅ الإجماع (6 موديلز متفقين 100%)

### الـ Root Cause
```
conversations.json → project_id قديم/محذوف
↓ POST /api/agent/ask_proxy
↓ 500 Internal Server Error
المشكلة مش في الحسابات — في الـ project نفسه!
```

### الحلقة المفرغة
```
retry 1: account A + project=1362ed26 → 500 ❌
retry 2: account B + project=1362ed26 → 500 ❌
retry 3: account C + project=1362ed26 → 500 ❌
الكود بيغيّر الحساب بس مش الـ project!
```

---

## 🔧 الإصلاحات المتفق عليها (بالترتيب)

### إصلاح 0: فوري (30 ثانية)
في `conversations.json` → `"project_id": null`

### إصلاح 1: send_chat يرجع signal
```python
# Line ~995
if r.status_code != 200:
    p(Fore.RED, f"  ❌ {r.status_code}: {r.text[:120]}")
    if r.status_code == 500:
        return None, "__INVALID_PROJECT__", None
    return None, None, None
```

### إصلاح 2: retry loop يتعامل مع الـ signal
```python
ans, new_pid, asst_mid = send_chat(...)
if new_pid == "__INVALID_PROJECT__":
    p(Fore.YELLOW, "  ⚠️ Project invalid → reset...")
    project_id = None
    history = []
    _invalidate_project(cfg, conv_name)
    break
```

### إصلاح 3: دالة _invalidate_project
```python
def _invalidate_project(cfg, conv_name="default"):
    try:
        convs = load_convs(cfg)
        if conv_name in convs:
            old = convs[conv_name].get("project_id", "?")
            convs[conv_name]["project_id"] = None
            convs[conv_name]["history"] = []
            save_convs(convs, cfg)
            p(Fore.YELLOW, f"  🗑️ مسح project: {str(old)[:12]}...")
    except Exception as e:
        p(Fore.RED, f"  ⚠️ فشل المسح: {e}")
```

---

## 📊 مقارنة آراء الموديلز

| الموديل | الإصلاح الفوري | signal | invalidate func | validate قبل |
|---------|---------------|--------|-----------------|-------------|
| Gemini  | ✅ | ✅ | ❌ (ضمني) | ❌ (Lazy أفضل) |
| ChatGPT 1 | ✅ | ✅ | ✅ | ✅ |
| ChatGPT 2 | ✅ | ✅ | ✅ | ✅ |
| ChatGPT 3 | ✅ | ✅ | ✅ | ✅ |
| ChatGPT 4 | ✅ | ✅ | ✅ | ✅ |
| ChatGPT 5 | ✅ | ✅ | ✅ | ✅ (HEAD check) |

**نقطة خلاف وحيدة:** Gemini بيقول Lazy Validation أفضل (لا تعمل validate قبل). الباقي بيقترحوا validate_project قبل الإرسال.

**رأيي: Gemini صح** — validate_project = API call زيادة مع كل رسالة = overhead. الـ signal approach أسرع وأخف.

---

## 🎯 الـ Agents المختارين للتنفيذ

1. `سيستم/أنت مدير المراجعة.md` — تنسيق ومراجعة شاملة
2. `سيستم/أنت محقق أخطاء عميق.md` — تحليل flow الـ retry
3. `سيستم/أنت محلل API Flow.md` — تحليل الـ 500 error response
4. `هندسة-تطبيقات/أنت مراجع الكود الآمن.md` — فحص الـ signal pattern
5. `هندسة-تطبيقات/أنت مهندس Backend.md` — تنفيذ الإصلاح
6. `سيستم/أنت مراجع أخطاء.md` — validation نهائية

---

## 📁 الملفات المتأثرة
- `genspark_chat.py` → Lines 992-997 + ~1940 + new function
- `conversations.json` → project_id = null (مؤقت)
