# 🔴 Debug: ERNIE (Baidu) + Grok (x.ai)

---

## 🟠 ERNIE — Playwright + osfuid fingerprint

### Flow:
```
Emailnator (@gmail.com فقط!)
  ↓ Playwright stealth init_script
  ↓ retry loop: osfuid (3×reload) ← jnmq SHA1 fingerprint
  ↓ button#sendCodeBtn (click fields أولاً لتفعيله!)
  ↓ div.pass-button.continue-button.active (مش <button>!)
  ↓ verify_code في reg/email (مش code!)
  ↓ Get Started → session capture (16 cookie!)
```

### القواعد:

| # | القاعدة | أهمية |
|---|---------|-------|
| 1 | `osfuid` = ephemeral per-session (SHA1 من jnmq) — مش قابل لإعادة الاستخدام | 🔴 |
| 2 | `button#sendCodeBtn` محتاج fields تتمفعّل أولاً (click email → click password) | 🔴 |
| 3 | Submit button = `div.pass-button.continue-button.active` مش `<button>` | 🔴 |
| 4 | Password limit: 8-14 chars — `Aa1@` + `token_hex(3)` = 10 chars | 🟡 |
| 5 | `@googlemail.com` مرفوض — حذف `googleMail` من Emailnator options | 🟡 |
| 6 | `verify_code` هو اسم الـ field في `reg/email` body مش `code`! | 🔴 |
| 7 | refresh.py لازم يبعت **كل الـ 16 cookie** مش osduss بس | 🔴 |

### SSE Parser:
```python
# ⚠️ أنماط SSE في ERNIE:
# event:major  → بداية thinking
# event:thought → thinking text (is_end:1 = نهاية التفكير بس!)
# event:step   → بعد التفكير
# event:message → الرد الحقيقي (is_end:1 هنا = نهاية فعلية!)

# ❌ غلط: break على أي is_end:1
# ✅ صح: break بس على event:message + is_end:1
```

### Endpoint:
```
✅ /eb/chat/conversation/v2   ← الحقيقي (من Burp)
❌ /eb/conversation/chat      ← يرجع code:1 دايماً!
```

### Models:
| Model ID | الاسم |
|----------|-------|
| `EB50` | ERNIE Bot 5.0 |
| `X1_1` | ERNIE X1 |
| `EB50-ARENA-LOW-260110` | ERNIE Arena Low |
| `EB50-ARENA-HIGH-1220` | ERNIE Arena High |

---

## 🟣 Grok (x.ai) — gRPC-web + Turnstile Hybrid

### Flow:
```
mailtm/emailnator → OTP email
  ↓ curl_cffi gRPC: SendEmailValidationCode
  ↓ poll email → OTP (remove dashes!)
  ↓ gRPC: VerifyEmailValidationCode
  ↓ SeleniumBase (مرة واحدة): /sign-up + Turnstile token
  ↓ Next.js Server Action: createUserWithEmail
  ↓ Cookies → accounts_grok.json
```

### القواعد:

| # | القاعدة | أهمية |
|---|---------|-------|
| 1 | OTP code بييجي بـ dashes: `CPN-8NX` → `.replace("-","").upper()` إلزامي | 🔴 |
| 2 | OTP expiry ~18 دقيقة — auto-polling فوري بمجرد الإرسال | 🔴 |
| 3 | `/sign-up` Server Action بيطلب Turnstile token → SeleniumBase مرة واحدة | 🔴 |
| 4 | gRPC: binary protobuf format — `grpc-status:3` = invalid, `grpc-status:5` = expired | 🟡 |
| 5 | Hybrid: SeleniumBase (Turnstile) + curl_cffi (gRPC) — browser مرة واحدة فقط! | 🟡 |
