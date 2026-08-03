# 📚 Memory: نظام Genspark Chat — الدروس الكاملة

## 📅 آخر تحديث: 2026-03-25

---

## ✅ المشاكل المحلولة (بالترتيب)

---

### 🔴 المشكلة 1: كل Run = محادثة جديدة (مش تكملة)

**الأعراض:**
- كل تشغيل = URL جديد وليس تكملة للمحادثة القديمة

**السبب الجذري:**
- `project_id` في `conversations.json` كان بيتاخد من `urls[-1]` بغض النظر عن صاحبه
- لو الحساب المختار مختلف عن صاحب الـ project → 500 ownership mismatch

**الحل:**
```python
# ❌ الخطأ: آخر project مهما كان صاحبه
project_id = urls[-1]["project_id"]

# ✅ الصح: pick_account أولاً ثم pick_best_project للحساب المختار
result = pick_account(accounts, cfg, skip_emails)
acc, cookies = result
active_email = (acc.get("email") or "").strip().lower()
_best_pid = pick_best_project(conv, active_email)
project_id = _best_pid  # None لو مالهوش project
```

**الدالة المهمة:**
```python
pick_best_project(conv, target_email)
# → بترجع آخر project_id اللي target_email هو صاحبه
# الملف: genspark_chat.py سطر ~563
```

---

### 🔴 المشكلة 2: نفس الحساب يتكرر كل Run (الـ cooldown مش بيشتغل)

**الأعراض:**
```
Run 1: zijuze → project d001d434
Run 2: zijuze → نفس project d001d434 (cooldown متجاهل!)
```

**السببان الجذريان:**
1. الكود كان يجبر `locked_email` (owner) مباشرة بدون cooldown check
2. `last_sent_chat_sent` كان بيتحفظ **بعد** الإرسال مش قبله

**الحل الجذري (تعديلان):**

**Fix 1 — elif project_id:**
```python
# ❌ الخطأ: جبر صاحب المشروع مباشرة (بيتخطى cooldown!)
if locked_email:
    acc = get_account_by_email(locked_email)
    
# ✅ الصح: pick_account أولاً (cooldown-aware)
result = pick_account(accounts, cfg, skip_emails)
acc, cookies = result
# ثم pick_best_project للحساب المختار
_best_pid = pick_best_project(conv, active_email)
```

**Fix 2 — last_sent_chat_sent قبل الإرسال:**
```python
# ❌ الخطأ: بعد الإرسال → cooldown مش فعال بين runs
if answer:  # بعد send_chat
    accounts[i]["last_sent_chat_sent"] = now

# ✅ الصح: قبل الإرسال → cooldown فعال من أول ثانية
if attempt == 0:  # قبل send_chat
    accounts[i]["last_sent_chat_sent"] = now
    save_accounts(accounts, cfg)
```

**النتيجة:**
```
Run 1: dyjyte5361  → project جديد ✅
Run 2: zikega235   → project جديد ✅ (حساب مختلف!)
Run 3: حساب تالت  → project جديد ✅
...بعد 29h...
Run N: dyjyte5361  → يكمل projectه ✅
```

---

### 🟡 المشكلة 3: history بتتمسح عند الـ rotation

**الأعراض:**
- الحساب الجديد مالهوش project → `history = []` → الـ AI لا يعرف السياق

**الحل:**
```python
# ❌ الخطأ: مسح history
project_id = None
history = []

# ✅ الصح: احتفظ بالـ history كـ context
project_id = None
# history تتحفظ كـ context للـ AI
```

---

## 🏗️ بنية conversations.json الصح

```json
{
  "default": {
    "project_id": "current-project",
    "messages": [...],
    "urls": [
      {
        "project_id": "abc123",
        "owner_email": "acc1@mail.com",
        "created_at": "..."
      }
    ]
  }
}
```

**⚠️ مهم: `owner_email` في كل url هو مفتاح الـ pick_best_project**

---

## ⚙️ إعدادات مهمة في Config

```python
account_cooldown_hours: int = 29  # الـ cooldown بالساعات
min_balance: int = 50             # أقل حد رصيد
prefer_balance: int = 100         # يبدأ بالأعلى
tie_break: str = "highest"        # أعلى رصيد أولاً
```

---

## 🗺️ flow الكامل (بعد الإصلاح)

```
1. load conversations.json → project_id الموجود
2. pick_account() [cooldown-aware] → acc
3. pick_best_project(conv, acc.email) → project بتاع الحساب ده
4. لو project موجود → كمل عليه ✅
5. لو مفيش → project_id=None + history محفوظة كـ context
6. قبل send_chat → احفظ last_sent_chat_sent
7. send_chat() → answer
8. update_conversation() → حفظ project_id + owner_email
```

---

## ⚠️ مشاكل شائعة

| المشكلة | السبب | الحل |
|---------|-------|------|
| 500 من project | ownership mismatch | Fix 1: pick_account أولاً |
| نفس الحساب دايماً | last_sent بعد send | Fix 2: last_sent قبل send |
| AI لا يعرف السياق | history=[] عند rotation | خلّي history محفوظة |
| cooldown مش بيشتغل | elapsed time مش بيتحسب | pick_account() بيعمله |

---

## 🔍 دوال مهمة

| الدالة | الأسطر | الوظيفة |
|--------|--------|---------|
| `pick_account()` | ~583 | اختيار حساب بالرصيد + cooldown |
| `pick_best_project()` | ~563 | project بتاع email معين |
| `update_conversation()` | ~480 | حفظ project_id + owner_email |
| `_update_balance()` | ~1583 | تحديث الرصيد بعد الإرسال |
