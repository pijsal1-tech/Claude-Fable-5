# 📖 دروس متقدمة — مش في جدول القواعد الحية

> **📌 دروس مستخرجة من README.md — patterns اتعلمناها من مشاكل حقيقية مش مغطيين في `15-live-rules-full.md`**

---

## 🔐 Auth Patterns المتقدمة

| # | الدرس | Tag | Provider |
|---|-------|-----|----------|
| 1 | Clerk Auth = 4 خطوات تتابعي: GET Session ID → POST JWT → extract token. `curl_cffi impersonate="chrome120"` إلزامي | [Auth] [Clerk] | Uncensored |
| 2 | Azure AD B2C: `csrf` و `transId` موجودين في HTML كـ JSON inline — regex مش meta tags! | [Auth] [B2C] | Genspark |
| 3 | Azure B2C PKCE: `code_verifier` (32 bytes urlsafe) → SHA256 → base64url = `code_challenge` | [Auth] [B2C] | Genspark |
| 4 | B2C CAPTCHA session TTL قصير — بعد 5 محاولات: OAuth refresh كامل (session + tx + csrf) مش بس sleep | [Auth] [B2C] | Genspark |
| 5 | Clerk JWT = short-lived (~1 ساعة) → اعتمد على `last_updated` + `SESSION_VALID_HRS` بدل decode JWT | [Auth] [Clerk] | Uncensored |
| 6 | Clerk 422 = incomplete account → `status = "layer1_failed"` في monitor skip | [Auth] [Clerk] | Uncensored |

---

## 🌐 WebSocket + SSE Patterns

| # | الدرس | Tag | Provider |
|---|-------|-----|----------|
| 7 | WebSocket: مفيش `message_type: done` — استخدم `end_of_stream: true` + `raw_text` للخروج | [API] [WebSocket] | Uncensored |
| 8 | ERNIE SSE `event:thought is_end:1` = نهاية التفكير ≠ نهاية الرد! track `current_event` | [API] [SSE] | ERNIE |
| 9 | Genspark SSE = 3 formats: `field_name/field_value` + OpenAI delta + direct content | [API] [SSE] | Genspark |
| 10 | SSE `stream=True` + `iter_lines` + timeout ≥ 300s لأن boot بياخد 2-4 دقايق | [API] [SSE] | Zo.computer |

---

## 🛡️ Security + Encoding

| # | الدرس | Tag |
|---|-------|-----|
| 11 | PowerShell `Set-Content` بيضيف UTF-8 BOM → JSON parsing يفشل → استخدم Python | [Config] [Debug] |
| 12 | PowerShell `-c` بيكسر Arabic text — اكتب script في `C:\tmp\` | [Debug] |
| 13 | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` إلزامي في كل سكريبت | [Config] |
| 14 | `datetime.fromisoformat()` أفضل من `strptime` — بتدعم كل الـ formats | [Script] |

---

## 🏗️ Architecture Patterns

| # | الدرس | Tag |
|---|-------|-----|
| 15 | Account Rotation: `TokenManager` بيحمّل من JSON + auto-switch لو 401/403. مفيش hardcoded token! | [Config] |
| 16 | Round-robin token rotation = فرق دراماتيكي: 49% → 91% success rate | [Performance] |
| 17 | `pplx_pool.py` كـ shared module أفضل من كل ملف يعمل import — مكان واحد للـ API logic | [DRY] |
| 18 | Circular import حل: `ai_agents` هو الوسيط الوحيد بين `tools` و `ai_team` | [Backend] |
| 19 | Config defaults لازم تكون **في الكود** — ملف JSON اختياري للـ override بس | [Config] |
| 20 | Quarantine أفضل من Disable الدائم — Auto-Revive بعد 15 دقيقة | [Performance] |
| 21 | Jaccard similarity (0.70 threshold) لمنع Task loops في Meta-Agent | [Backend] |
| 22 | Cache data كل 5s في Dashboard — مش عند كل request | [Performance] |

---

## 🔧 React/DOM Patterns

| # | الدرس | Tag |
|---|-------|-----|
| 23 | `send_keys()` و `fast_type()` مش بيحدثوا React state — لازم `InputEvent` + `inputType: 'insertText'` | [Script] [React] |
| 24 | React بيضيّع آخر حرف من `send_keys` — re-set القيمة كاملة + `blur` event | [Script] [React] |
| 25 | `get_cookies()` بيجيب cookies بس — DeepSeek `userToken` في localStorage مش cookies! | [Script] |
| 26 | Pre-flight trick: `robots.txt` أولاً → حقن localStorage → فتح الصفحة | [Script] |
| 27 | Content-based detection أفضل من role/class selectors — بيدور على النص | [Script] |
| 28 | Radix UI dropdown بيفتح في `<body>` مش جوا button — `role="option"` | [Script] |

---

## 📧 Email + Verify Patterns

| # | الدرس | Tag |
|---|-------|-----|
| 29 | Microsoft OTP مش بييجي على domains زي pazard/onbap — استخدم emailnator (googlemail) | [Mail] |
| 30 | OTP في الـ email subject مباشرة — أسرع من HTML parsing: `re.search(r'\b(\d{6})\b', subject)` | [Mail] |
| 31 | `seen_ids` snapshot قبل `SendCode` يفلتر OTP القديم | [Mail] |
| 32 | Email verify link: regex يدور على "Confirm" button href مش أول link! | [Mail] |

---

## 🧪 Testing + Debug

| # | الدرس | Tag |
|---|-------|-----|
| 33 | `stdin` test pattern: سكريبت مستقل بـ N طريقة + watch for success element + print WINNER | [Debug] |
| 34 | JS source analysis أسرع من brute-force endpoints! `var currentLang = ""; fetch(...)` | [Debug] |
| 35 | `em-dash (—)` و `→` في Python = SyntaxError! ASCII characters فقط في الكود | [Debug] |
| 36 | partial f-string edit بيخلي triple-quote مفتوح — اعمل replace للـ block كاملة | [Debug] |
| 37 | Models بتموت بدون إنذار — `_test_failed.py` يتشغل دوري | [Debug] |
| 38 | `mycdp` KeyError errors (Chrome 146) = noise — بيتجاهلوا مش بيأثروا | [Debug] |

---

## 🌸 Pollinations Patterns

| # | الدرس | Tag |
|---|-------|-----|
| 39 | Pollinations `sk_` API key = auto-create من session token: `POST /api/keys` → key صالح 30 يوم | [API] |
| 40 | Persistent History: `history.json` بيتحفظ بين الـ runs — `/clear` يمسح + `--no-history` يعطّل | [Config] |
| 41 | Token Usage Tracking per-message: prompt_tokens + completion_tokens + `/usage` command | [Performance] |

