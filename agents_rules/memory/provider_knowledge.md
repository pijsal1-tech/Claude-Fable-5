# 🤖 Provider Knowledge — معرفة الـ Providers

> الـ AI يقرأ الملف ده قبل ما يضيف أو يعدل أي provider

## 📊 Providers الموجودة والحالة

| Provider | الملف | Auth Type | Email | Monitor | Status |
|----------|-------|-----------|-------|---------|--------|
| Groq | `groq/groq_token_generator.py` | API Key | emailnator | ✅ | Active |
| Genspark | `.Genspark_😎/genspark_register.py` | Azure B2C + CAPTCHA | emailnator | ✅ | Active |
| Arena | `ارينا/arena_register.py` | OAuth + CDP | emailnator | ✅ | Active |
| DeepSeek | `ديب سيك/deepseek_chat.py` | Browser/Requests | — | ✅ | Active |
| **PromptCowboy** | `P__promptcowboy/promptcowboy_register.py` | **Next.js Server Action + OTP** | **Mailnesia** | ❌ | **Active ✅** |
| You.com | — | — | — | ✅ | In Monitor |
| Zo Computer | — | — | — | ✅ | In Monitor |
| Runable | — | — | — | ✅ | In Monitor |
| Cohere | — | — | — | ✅ | In Monitor |
| Mistral | — | — | — | ✅ | In Monitor |
| AI21 | — | — | — | ✅ | In Monitor |
| ERNIE | — | — | — | ✅ | Active (Baidu) |


## 🛡️ Anti-Bot Patterns المعروفة

| الموقع/النوع | الحل المثبت |
|-------------|------------|
| Cloudflare | SeleniumBase + `uc=True` |
| React buttons | CDP `Runtime.evaluate + userGesture=True` |
| Baidu/ERNIE | Playwright (passport session) |
| WASM PoW | DeepSeek requests pattern |
| Azure B2C | PKCE + CAPTCHA multi-solver |

## 📧 Email Providers المعروفة

| Provider | Class | متى تستخدم |
|----------|-------|-----------|
| emailnator | `EmailnatorClient` | Gmail aliases — الأكثر استقراراً |
| tempnet | `TempNetClient` | Gmail + Cloudflare bypass |
| mailtm | `TempMailAPI` | custom domains |
| besttemp | `BestTempClient` | Livewire sites |
| dropmailx | `DropmailxClient` | ridermail.shop |

## ⚠️ قرارات تقنية مهمة

- **DeepSeek:** استخدم pure requests (WASM PoW) مش browser للـ API
- **Arena:** CDP فقط للـ click — مش execute_script ولا ActionChains
- **ERNIE:** Playwright للـ Baidu + curl_cffi للخدمات الخارجية (مش تخلطهم!)
- **Genspark:** Azure B2C = PKCE flow — لازم browser

---
*[AI: ضيف هنا أي provider جديد أو pattern جديد اكتشفته]*
