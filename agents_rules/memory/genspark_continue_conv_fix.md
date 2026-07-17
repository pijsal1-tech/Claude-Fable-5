# 🔴 Memory: مشكلة Continue Conversation — كل Run شات جديد

## 📅 تاريخ الحل: 2026-03-25

---

## ❌ المشكلة (الأعراض)
كل run بيعمل محادثة جديدة بدل ما يكمل على نفس المحادثة.

```
Run 1 → project: 3b013ffe (account A: fuveri)
Run 2 → project: 4232b8c6 (جديد!) ❌
Run 3 → project: xxxxxxxx (جديد!) ❌
```

---

## 🎯 Root Causes (3 مشاكل متداخلة)

### مشكلة 1: اختيار project غلط
```
❌ الخطأ: آخر project_id في urls[] بغض النظر عن صاحبه
✅ الصح: project بتاع نفس الحساب المختار (owner_email)
```
**الفايل والسطر:** `genspark_chat.py` → سطر ~1893

### مشكلة 2: اختيار الحساب غلط
```
❌ الخطأ: pick_account عشوائي حتى لو عارفين صاحب الـ project
✅ الصح: locked_email (صاحب الـ project) → نختاره مباشرة
```
**الفايل والسطر:** `genspark_chat.py` → سطر ~1959

### مشكلة 3: Genspark لا يقبل project_id من account تاني
```
account A → project 3b013ffe (owner: account A)
account B → tries to continue 3b013ffe → 500 (ownership mismatch!)
```
**الحل:** لازم نكمل بنفس الحساب اللي أنشأ الـ project

---

## ✅ الحل النهائي (3 تعديلات في genspark_chat.py)

### تعديل 1: pick_best_project بناءً على owner_email
```python
# السطر ~1890 في main() / cli_mode
urls = cv.get("urls", [])
project_id = None
_all_accts = load_accounts(cfg)
for _acct in _all_accts:
    _email_try = (_acct.get("email") or "").strip().lower()
    _found = pick_best_project(cv, _email_try)  # دالة pick_best_project موجودة!
    if _found:
        project_id = _found
        locked_email = _acct.get("email")  # قفّل على الحساب
        break
history = cv.get("messages", [])  # ← لازم تيجي هنا!
```

### تعديل 2: pick_account يحترم locked_email
```python
# السطر ~1959
elif project_id:
    accounts = load_accounts(cfg)
    if locked_email:
        # ← نختار صاحب الـ project مباشرة
        acc = next((a for a in accounts if 
                    a.get("email","").lower() == locked_email.lower() 
                    and a.get("cookies")), None)
        if acc:
            cookies = acc["cookies"]
            active_email = locked_email.lower()
        else:
            # جرّب login لو عنده password
            ...
```

### تعديل 3: الـ auto-recovery يحتفظ بالـ history
```python
# السطر ~2011 — عند __INVALID_PROJECT__
if pid == "__INVALID_PROJECT__":
    project_id = None
    # ✅ مش history = []  ← لا تمسح السياق!
    # history يتحفظ → AI بيعرف موضوع المحادثة
```

---

## 🔍 دوال مهمة موجودة في الكود

```python
pick_best_project(conv, target_email)
# → بيرجع آخر project_id اللي email ده صاحبه في urls[]
# الملف: genspark_chat.py سطر ~563

update_conversation(cfg, conv_name, email, ...)
# → بيحفظ owner_email في urls[]:
#   urls_list.append({
#       "project_id": ...,
#       "owner_email": email,  ← موجودة!
#   })
```

---

## 🗂️ بنية conversations.json الصح

```json
{
  "default": {
    "project_id": "current-project-id",
    "account": "owner@email.com",
    "urls": [
      {
        "project_id": "abc123",
        "owner_email": "accountA@mail.com",  ← مهم!
        "created_at": "...",
        "msg_count": 5
      }
    ],
    "messages": [...]
  }
}
```

---

## ⚠️ مشاكل شائعة تانية

| المشكلة | السبب | الحل |
|---------|-------|------|
| 500 من project قديم | Project انتهى/اتمسح من Genspark | Auto-recovery → project_id=None → project جديد |
| `cfg.accounts` AttributeError | الـ accounts مش في cfg | استخدم `load_accounts(cfg)` |
| history بتتمسح عند recovery | كانت `history = []` في auto-recovery | امسح السطر ده |
| runner بيختار حساب غلط | pick_account عشوائي | استخدم locked_email أولاً |

---

## 🧪 طريقة التحقق (بعد التعديل)

```
Run 1: project_id=None → يتولد project جديد (e.g., cdf62d8d)
Run 2: picks (owner) cyzesa3533 → cdf62d8d ✅ نفس الـ project!
Run 3: picks (owner) cyzesa3533 → cdf62d8d ✅ كمّل تاني!
```

**علامة نجاح الإصلاح:**
```
📧 account@email.com → يكمل xxxxxxxx... (owner)   ← كلمة (owner) دي مهمة!
```

---

## 📁 الملفات المتأثرة
- `Genspark_V2/genspark_chat.py`
  - سطر ~1890: اختيار project بـ owner_email
  - سطر ~1959: اختيار الحساب بـ locked_email
  - سطر ~2011: حفظ history عند auto-recovery
  - سطر ~1006: force:true على التكملة
  - سطر ~1044: قبول 200 و204 كـ success
