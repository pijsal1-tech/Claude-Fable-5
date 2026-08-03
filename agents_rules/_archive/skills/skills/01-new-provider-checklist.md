# ✅ Checklist — أول ما تبدأ Provider جديد

> **⛔ ممنوع كتابة سطر كود واحد قبل الإجابة على كل الأسئلة دي!**

## البرومبت — ابعته للـ AI مع الـ HAR/curl:

```
معيا ملف HAR/curl لـ [اسم الموقع].
🫷 الخطوة الأولى: ممنوع كتابة أي كود الآن.

أجبني على هذا الـ Checklist:
1. إيه الـ auth method? (Descope? Firebase? Ory Kratos? Magic Link? Custom OAuth?)
2. فين يعيش الـ token? (body JSON؟ cookies؟ headers؟ localStorage؟)
3. في Cloudflare أو hCaptcha أو Turnstile؟ (لو أيوه → Hybrid مطلوب)
4. طريقة التحقق؟ (OTP 6 أرقام؟ Magic Link؟ Email Link مع redirect؟)
5. الـ temp email المناسب؟ (Emailnator؟ Mail.tm؟ TempMail؟ BestTemp؟)
6. الـ response format؟ (JSON؟ RSC Next.js؟ HTML؟ gRPC?)
7. في subscription/trial activation مطلوبة بعد التسجيل؟
8. أي headers خاصة بيبعتها المتصفح؟ (x-descope-* ؟ x-csrf-token؟)
9. الـ token بييجي من نفس domain ولا subdomain تاني؟

⛔ لا تكتب أي كود قبل موافقتي على إجاباتك.
```

## اختار المسار بعد الإجابة:

| إجابة #3 | الملف |
|---------|-------|
| ❌ مفيش حماية | `02-requests-level1.md` |
| ✅ في Cloudflare/hCaptcha | `03-hybrid-level2.md` |

## Hard Rules قبل البناء:

- [ ] `curl_cffi` مش `requests` عادي لأي anti-bot
- [ ] Session واحد يحافظ على الكوكيز طول العملية
- [ ] كل token يتاخد ديناميكياً من response السابق
- [ ] atomic write لـ `accounts.json`
- [ ] colorama + fallback في كل print
- [ ] UTF-8 fix: `sys.stdout.reconfigure(encoding="utf-8")`
- [ ] **OPSEC (Header Match):** استخدام `impersonate="chromeX"` يجب أن يُرافقه Header لـ Chrome. ممنوع الخلط!
- [ ] **Single File:** كتابة كود الأتمتة بالكامل ككتلة واحدة في السكريبت دون دوال خارجية من شأنها تشتيت مسارات العمل.
- [ ] **Solid Parsing:** استبدال Regex أرقام الهواتف والدول بمكتبة متخصصة كـ `phonenumbers`.
