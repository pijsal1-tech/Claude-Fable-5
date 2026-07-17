# 📋 بعد ما تخلص — monitor.py + Provider List

## الخطوة 1: أضف في `monitor.py`:

```python
"new_provider": {
    "accounts": BASE_DIR / "folder_name" / "accounts_provider.json",
    "refresh_module": str(BASE_DIR / "folder_name" / "refresh.py"),
    "expires_default": 24,
    "skip_status": ["inactive", "banned", "❌"],
},
```

## الخطوة 2: هيكل الملفات (اتبعه بالظبط):

```
provider_folder/
├── provider_register.py         # إنشاء حسابات — بـ provider prefix
├── refresh.py                   # def refresh(email) -> bool — بدون prefix!
└── accounts_provider.json       # بـ provider prefix
```

## الخطوة 3: حدّث جدول المزودين في `UNIVERSAL_PROVIDER_PROMPT.md`:

```
| 14 | **New Provider** | `folder/` | 🔑 Token/🍪 Cookie | Method | Email Provider | Verify |
```

## المزودين الحاليين:

| # | Provider | Folder | Type | Method | Email | Verify |
|---|----------|--------|------|--------|-------|--------|
| 1 | Arena | `ارينا/` | 🍪 | Hybrid: curl_cffi + SeleniumBase | Mail.tm | Link |
| 2 | DeepSeek | `ديب سيك/` | 🍪 | Hybrid Level 2: WAF + fetch() | Emailnator | Code 6 |
| 3 | Groq | `groq/` | 🔑 | Selenium | Emailnator | Magic Link |
| 4 | You.com | `you.com/` | 🔑 | Requests Level 1 (Descope) ⭐ | Email+Mail.tm+Drop | OTP 6 |
| 5 | Zo Computer | `zo.computer/` | 🍪 | Requests Level 1 (Magic Link) ⭐ | Emailnator+Mail.tm | Magic Link |
| 6 | Runable | `Runable/` | 🍪 | Requests Level 1 ⭐ | Emailnator+Drop | Magic Link |
| 7 | Mistral | `mistral/` | 🍪 | Requests Level 1 (Ory Kratos) ⭐ | Mail.tm | OTP 6+SMS |
| 8 | AI21 | `AI21_Maestro/` | 🔑 | Requests Level 1 (Firebase) ⭐ | Emailnator+Mail.tm | Email Link |
| 9 | Cohere | `cohereR/` | 🔑 | Requests Level 1 (BlobheartAPI) ⭐ | BestTemp | Email Link |
| 10 | Perplexity | `Perplexity AI/` | 🔑 | curl_cffi (Android Mobile API) ⭐ | Mail.tm+5 others | OTP 6 |
| 11 | Grok (x.ai) | `grok/` | 🍪 | Hybrid: gRPC + Turnstile | mailtm+emailnator | OTP 6 |
| 12 | ERNIE | `ernie.baidu/` | 🍪 | Playwright (osfuid fingerprint) | Emailnator | OTP 6 |
| 13 | Genspark | `Genspark_😎/` | 🍪 | Requests + Azure B2C + CAPTCHA ⭐ | Mail.tm | OTP 6 |

## الملفات المشتركة:

```
d:\SMS\AI_PROVIDERS\
├── monitor.py                    # 🧠 المراقب المركزي (13 providers)
├── shared/                       # 📦 مكتبة مشتركة
│   ├── __init__.py              # re-exports
│   ├── ui.py                    # step/ok/fail/warn/banner
│   ├── io.py                    # atomic_save/load_accounts
│   └── delay.py                 # human_delay
└── بي ريييب/z.ai_ocr/
    ├── captcha_solver.py         # 🔓 CAPTCHA (4 methods + 3 strategies)
    └── captcha_client.py         # واجهة بسيطة
```

## CAPTCHA Integration (لو الموقع فيه captcha):

```python
from captcha_solver import CaptchaService
svc = CaptchaService()
text = svc.solve_from_file("captcha.png")        # من ملف
text = svc.solve_from_url("https://site/c.png")  # من URL
```
