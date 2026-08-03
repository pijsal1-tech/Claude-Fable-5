# 📧 Email Providers — Emailnator + Mail.tm + TempMail + BestTemp + TempNet

## 🗂 اختيار الـ Provider:

| Provider | المكتبة | الدومين | نوع الإيميل | يدعم |
|---------|---------|--------|------------|------|
| `emailnator` | `curl_cffi` | gmail.com | dot/plus aliases | Code + Magic Link |
| `mailtm` | `requests` | متغير | أي | Verify Link |
| `tempmail` | `curl_cffi` | temp-mail.org | عشوائي | OTP + Link |
| `tempnet` | `cloudscraper` | gmail.com | Gmail aliases | Code + Link |
| `besttemp` | `requests` | Livewire API | عشوائي | Confirm Link |
| `dropmailx` | `requests` | ridermail.shop | عشوائي | OTP |
| `mix` | rotation | — | دمج أكتر من provider | أي |

> **`mix` mode:** بيلف على الـ providers بالتبادل — `"mailtm,emailnator"` أو `"mix"` = كلهم.

## Auto-detect من الدومين:

```python
def _detect_provider(email: str) -> str:
    domain = email.split("@")[-1]
    if domain in ("gmail.com", "googlemail.com"):
        return "emailnator"  # أو tempnet حسب الـ --provider flag
    if domain == "ridermail.shop":
        return "dropmailx"
    return "mailtm"  # كل دومين تاني = mail.tm
```

## Interface موحد لكل Provider:

```python
class BaseEmailClient:
    def create_email(self) -> str | None: ...
    def wait_for_code(self, email, timeout=120) -> str | None: ...      # 6 digits
    def wait_for_link(self, email, timeout=120) -> str | None: ...      # URL
```

## 🚨 قواعد إلزامية:

```python
# Emailnator — نفس الـ instance طول العملية (inbox مرتبط بالـ session cookie)
client = EmailnatorClient()           # ← مش تعمل instance جديد!
email = client.create_email()
code = client.wait_for_code(email)   # ← نفس الـ client

# Mail.tm — احفظ الـ credentials عشان تفتح الـ inbox بعدين
{
    "email": "x@domain.com",
    "email_creds": {
        "password_mailtm": "...",       # ← suffixed دايماً
        "token_mailtm": "...",
        "account_id_mailtm": "..."
    }
}

# Mail.tm domains بتتغير ديناميك — مفيش hardcoded domains!
_MAILTM_DOMAINS = set()  # بيتملى تلقائي من الـ API
def _detect_mailtm(email):
    return email.split("@")[1] not in ("gmail.com", "ridermail.shop")

# temp-mail.org — data-code SHA256 إلزامي بعد activate
# بدون reload الصفحة بعد activate → 400 Invalid request!
```

## البرومبت لما تحتاج email provider:

```
عايز تضيف email provider جديد اسمه [اسم].
API: [الـ endpoints]
اتبع نفس Interface بتاع BaseEmailClient:
- create_email() → str
- wait_for_code(email, timeout) → str | None
- wait_for_link(email, timeout) → str | None
مع curl_cffi أو cloudscraper حسب الـ anti-bot.
```
