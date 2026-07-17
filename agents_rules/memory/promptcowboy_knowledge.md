# 🤠 PromptCowboy — ذاكرة كاملة

> **📌 اقرأ الملف ده قبل أي شغل على PromptCowboy بالكامل**
> آخر تحديث: بعد نجاح التسجيل التلقائي العملي

---

## 🌐 معلومات الموقع

| البند | القيمة |
|-------|--------|
| **URL** | `https://www.promptcowboy.ai` |
| **Stack** | Next.js (Vercel) — Server Actions |
| **Auth** | Email OTP (بدون password) |
| **حماية** | لا Cloudflare، لا CAPTCHA |
| **Supabase ProjectID** | `fjhhomqmqcxsodwtnzry` |

---

## 🔄 Auth Flow الكامل (من Burp Suite — مؤكّد 100%)

```
1. POST /auth?redirect_to=/
   Headers:
     next-action: 400f6165f933c37047a488df1e175c0c51758227a2
     Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
     Accept: text/x-component
   Body (multipart):
     1_email    = user@mailnesia.com
     1_redirectTo = /
     0          = ["$K1"]
   Response: 303 → Set-Cookie: sb-fjhhomqmqcxsodwtnzry-auth-token-code-verifier

2. [Mailnesia] انتظار OTP (6 digits) في الإيميل

3. POST /verify?email=user@mailnesia.com&redirect_to=/
   Headers:
     next-action: 40f51ae1a765bfc50c12745d1acaee58a5c420f4e5
     Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
     Accept: text/x-component
   Body (multipart):
     email      = user@mailnesia.com
     code       = 123456
     redirectTo = /
     0          = ["$K1"]
   Response: 200/303 → Session cookies ✅
```

---

## 🔑 Action IDs الثابتة (من JS bundle)

| الوظيفة | Action ID |
|---------|----------|
| **إرسال OTP** (`sendOTPAction`) | `400f6165f933c37047a488df1e175c0c51758227a2` |
| **التحقق من OTP** (`verifyOTPAction`) | `40f51ae1a765bfc50c12745d1acaee58a5c420f4e5` |

> ⚠️ هتتغير لو الموقع عمل deploy جديد — مصدرها: `/_next/static/chunks/app/(auth)/verify/page-*.js`

---

## 📧 Email Provider: Mailnesia

```
- مش محتاج تسجيل — أي اسم = mailbox شغال على طول
- Email: {اسم_عشوائي}@mailnesia.com
- فحص الـ inbox: GET https://mailnesia.com/mailbox/{name}
- قراءة رسالة: GET https://mailnesia.com/mailbox/{name}/{id}?noheadernofooter=ajax
- Extract OTP: re.search(r'\b(\d{6})\b', html)
- متوسط وقت الوصول: 10-30 ثانية
```

---

## 📁 ملفات المشروع

| الملف | الوظيفة |
|-------|---------|
| **السكربت** | `P__promptcowboy/promptcowboy_register.py` | ✅ سكربت التسجيل الرئيسي (OTP Flow) — v2 محسّن |
| `P__promptcowboy/p_romptcowboy_register.py` | ❌ قديم (Magic Link — غلط) — احتفظ به كـ reference |
| `P__promptcowboy/accounts_promptcowboy.json` | قاعدة بيانات الحسابات |

---

## ⚙️ إعدادات السكربت

```python
LOOP_MODE         = True       # تكرار لانهائي (افتراضي)
MAX_ACCOUNTS      = 0          # 0 = بلا حد
DELAY_BETWEEN     = 5          # ثواني بين كل حساب
OTP_TIMEOUT       = 50         # ثواني لانتظار الـ OTP (المستخدم غيّرها)
OTP_POLL_INTERVAL = 5          # ثواني بين كل محاولة فحص
ACCOUNTS_FILE     = "P__promptcowboy/accounts_promptcowboy.json"
```

### CLI Commands:
```bash
python promptcowboy_register.py             # loop لانهائي
python promptcowboy_register.py --no-loop   # حساب واحد
python promptcowboy_register.py --max 10    # 10 حسابات
python promptcowboy_register.py --count     # عدد الحسابات
python promptcowboy_register.py --list      # عرض الحسابات
```

---

## 🐛 مشاكل اتحلت (لا تكررها!)

### مشكلة 1: step() conflict
```
Error: TypeError: step() missing 2 required positional arguments: 'total' and 'msg'
سبب: shared.ui.step(num, total, msg) ≠ step(msg) المستخدم داخلياً
حل: تعريف step() محلي في السكربت يـoverride المستورد
```

### مشكلة 2: upsert_account signature
```
Error: TypeError: expected str, bytes or os.PathLike object, not list
سبب: shared.io.upsert_account(filepath, account) مش (accounts_list, account)
حل: upsert_account(cfg.accounts_file, account)  ← filepath أولاً
```

---

## 💡 دروس مستفادة

| # | الدرس | السياق |
|---|-------|--------|
| 1 | **`next-action` header هو المفتاح** في Next.js Server Actions — من Burp بس | الـ endpoint نفسه (`/auth`) بيتعامل مختلف حسب الـ action ID |
| 2 | **`multipart/form-data` مش JSON** — Next.js Server Actions بتاخد form-data | محاولة JSON أو URLencoded بتفشل بصمت |
| 3 | **Action IDs بتتغير** مع كل deploy — تحتاج تجيبها دايماً من الـ JS bundle | `/_next/static/chunks/app/(auth)/verify/page-*.js` |
| 4 | **Mailnesia أسرع وأسهل** من كل email providers لـ OTP — وصل خلال 10-20s | مش محتاج API key ولا registration |
| 5 | **PromptCowboy مفيش bot protection** — requests عادية تكفي | لا curl_cffi ولا selenium مطلوبين |

---

## 🔮 خطوات مستقبلية

- [ ] إضافة `refresh.py` لتجديد الـ session cookies بدون OTP
- [ ] دمج في `monitor.py`
- [ ] إضافة `chat.py` للتفاعل مع الـ API

---

*[AI: حدّث الـ Action IDs لو الموقع عمل deploy جديد وبدأت ترجع 401/403]*
