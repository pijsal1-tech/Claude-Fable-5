---
description: Checklist إلزامي - أول ما تبدأ أي AI Provider جديد
globs: "**/*.py"
---
# ✅ Checklist — بداية أي Provider جديد

> **⛔ ممنوع كتابة سطر كود واحد قبل الإجابة على كل الأسئلة دي!**

## البرومبت — ابعته للـ AI مع الـ HAR/curl:

```
معيا ملف HAR/curl لـ [اسم الموقع].
🫷 قبل أي كود، أجبني على هذا الـ Checklist فقط:

1. إيه الـ auth method? (Descope? Firebase? Custom OAuth? Magic Link? Ory Kratos?)
2. فين يعيش الـ token? (body JSON؟ cookies؟ headers؟ localStorage؟)
3. في Cloudflare أو hCaptcha؟ (لو أيوه → Hybrid مطلوب)
4. طريقة التحقق؟ (OTP 6 أرقام؟ Magic Link؟ Email Link مع redirect؟)
5. الـ temp email المناسب؟ (Emailnator؟ Mail.tm؟ TempMail؟)
6. الـ response format؟ (JSON؟ RSC Next.js؟ HTML؟)
7. في subscription/trial activation مطلوبة بعد التسجيل؟

⛔ لا تكتب أي كود قبل موافقتي على إجاباتك.
```

## بعد الإجابة — اختار المسار:

| النتيجة | المسار |
|---------|--------|
| لا Cloudflare + JSON API | ➡️ `03-provider-requests.md` (Requests فقط) |
| في Cloudflare + API موجود | ➡️ `04-provider-hybrid.md` (Hybrid) |
| مفيش API + JS ثقيل | ➡️ `05-provider-selenium.md` (Selenium فقط) |
