# ⚡ Level 1 — Requests Only (مفيش Cloudflare)

> **Stack:** `curl_cffi` Session → Dynamic Token Chaining → Atomic Save

## البرومبت:

```
الـ Checklist جاهز. المسار: Level 1 (Requests Only).

📋 Provider: [اسم]
Auth: [طريقة]  |  Email: [provider]  |  Verify: [OTP/Link]

🎯 المطلوب بالترتيب:
الخطوة أ: ارسملي Dependency Flow (بدون كود):
  Step 1 → [endpoint] → output: [token/cookie]
    ↓
  Step 2 → [endpoint] → يحتاج: [المدخل] → output: [...]

الخطوة ب: (بعد موافقتي) اكتب register.py بـ curl_cffi.

⛔ القيود الإلزامية:
- curl_cffi مش requests عادي
- Session واحد يحافظ على الكوكيز
- كل token ديناميكي من response السابق (مفيش hardcoded!)
- LOOP_MODE=True كـ default + argparse كامل
- atomic write للـ accounts.json
- colorama + fallback
```

---

## 📐 Template register.py الكامل:

```python
#!/usr/bin/env python3
"""🚀 [Provider] Account Creator"""
from __future__ import annotations
import sys, json, time, random, argparse, logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class _F: CYAN=GREEN=RED=YELLOW=MAGENTA=WHITE=''
    class _S: BRIGHT=RESET_ALL=''
    Fore, Style = _F(), _S()

from curl_cffi import requests as cffi

C=Fore.CYAN; G=Fore.GREEN; R=Fore.RED; Y=Fore.YELLOW
M=Fore.MAGENTA; W=Fore.WHITE; B=Style.BRIGHT; RST=Style.RESET_ALL

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────
LOOP_MODE      = True                # الـ default: يفضل يشتغل
MAX_ACCOUNTS   = 0                   # 0 = unlimited
DELAY_BETWEEN  = 10                  # ثواني بين كل حساب
OTP_TIMEOUT    = 120                 # ثواني انتظار الـ OTP
DEFAULT_PASS   = "A9!k@e3#Qz1$Lp"   # باسورد افتراضي
ACCOUNTS_FILE  = Path(__file__).resolve().parent / "accounts_PROVIDER.json"

# ─── Config ────────────────────────────────────
@dataclass
class Config:
    loop: bool = LOOP_MODE
    max_accounts: int = MAX_ACCOUNTS
    delay: int = DELAY_BETWEEN
    otp_timeout: int = OTP_TIMEOUT
    email_provider: str = "mailtm"
    headless: bool = False
    password: str = DEFAULT_PASS

# ─── UI ────────────────────────────────────
def banner(cfg: Config, existing: int):
    mode = "Loop" if cfg.loop else "Single"
    print(f"\n{C}{B}{'═'*60}")
    print(f"  🚀 [Provider] Account Creator")
    print(f"{'═'*60}{RST}")
    print(f"  {W}📧 Provider: {B}{Y}{cfg.email_provider}{RST}")
    print(f"  {W}🔄 Mode    : {B}{Y}{mode}{RST}")
    if cfg.loop:
        limit = str(cfg.max_accounts) if cfg.max_accounts > 0 else "unlimited"
        print(f"  {W}🎯 Target  : {B}{Y}{limit}{RST}")
        print(f"  {W}⏱️  Delay   : {B}{cfg.delay}s{RST}")
    print(f"  {W}📁 Existing: {B}{G}{existing}{RST} accounts")
    print(f"{C}{B}{'═'*60}{RST}\n")

def account_header(num, provider, ok_count, fail_count):
    print(f"\n{Y}{B}{'─'*60}")
    print(f"  📧 Account #{num} — {provider} ( ✅ {ok_count} ❌ {fail_count} )")
    print(f"{'─'*60}{RST}")

def step(num, total, msg):    print(f"  {C}[{num}/{total}]{RST} {msg}")
def ok(msg):                   print(f"  {G}{B}✅ {msg}{RST}")
def fail(msg):                 print(f"  {R}{B}❌ {msg}{RST}")
def warn(msg):                 print(f"  {Y}⚠️  {msg}{RST}")

def final_stats(success, failed, total_saved):
    rate = (success / (success + failed) * 100) if (success + failed) > 0 else 0
    color = G if rate >= 70 else Y if rate >= 40 else R
    print(f"\n{C}{B}{'═'*60}")
    print(f"  🏁 Final Stats\n{'═'*60}{RST}")
    print(f"  {G}✅ Success : {B}{success}{RST}")
    print(f"  {R}❌ Failed  : {B}{failed}{RST}")
    print(f"  {color}📈 Rate    : {B}{rate:.0f}%{RST}")
    print(f"  {W}💾 Saved   : {B}{total_saved}{RST} total")
    print(f"{C}{B}{'═'*60}{RST}\n")

# ─── I/O ────────────────────────────────────
def _load_accounts() -> list:
    if ACCOUNTS_FILE.exists():
        return json.loads(ACCOUNTS_FILE.read_text("utf-8"))
    return []

def _save_accounts(accounts: list):
    tmp = ACCOUNTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(ACCOUNTS_FILE)

def _detect_provider(email: str) -> str:
    domain = email.split("@")[-1]
    if domain in ("gmail.com", "googlemail.com"): return "emailnator"
    if domain == "ridermail.shop": return "dropmailx"
    return "mailtm"

def list_accounts():
    accs = _load_accounts()
    for i, a in enumerate(accs, 1):
        status = a.get("status", "?")
        print(f"  {i}. {a['email']} [{status}]")
    print(f"\n  Total: {len(accs)}")

# ─── Email Factory ────────────────────────────────
def _create_mail_client(provider: str):
    if provider == "emailnator":
        from emailnator_client import EmailnatorClient
        return EmailnatorClient()
    elif provider == "mailtm":
        from mailtm_client import TempMailAPI
        return TempMailAPI()
    # ... إضافة providers تانية
    raise ValueError(f"Unknown email provider: {provider}")

# ─── Session ────────────────────────────────────
def get_session():
    session = cffi.Session(impersonate="chrome124")
    session.headers.update({
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://SITE.com",
        "referer": "https://SITE.com/",
    })
    return session

# ─── Register (غيّرها حسب Provider) ────────────
def register(email: str, password: str, cfg: Config) -> dict | None:
    session = get_session()
    try:
        # Step 1: Register
        step(1, 4, "إنشاء حساب...")
        r1 = session.post("https://SITE.com/api/register",
            json={"email": email, "password": password}, timeout=30)
        r1.raise_for_status()
        TOKEN = r1.json()["token"]  # ← دايماً ديناميك!
        ok(f"Token: {TOKEN[:20]}...")

        # Step 2: Wait OTP
        step(2, 4, "انتظار OTP...")
        # ... wait_for_code logic

        # Step 3: Verify
        step(3, 4, "تأكيد...")
        r2 = session.post("https://SITE.com/api/verify",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"code": "OTP_HERE"}, timeout=30)
        r2.raise_for_status()

        # Step 4: Save
        step(4, 4, "حفظ...")
        return {
            "email": email, "password": password,
            "token": r2.json().get("access_token", ""),
            "provider": _detect_provider(email),
            "status": "active",
            "last_updated": datetime.now().isoformat(),
            "expires_in": 24,
        }
    except Exception as e:
        fail(f"فشل: {e}")
        return None

# ─── Main Loop ────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=MAX_ACCOUNTS)
    parser.add_argument("--loop", action="store_true", default=LOOP_MODE)
    parser.add_argument("--no-loop", dest="loop", action="store_false")
    parser.add_argument("--delay", type=int, default=DELAY_BETWEEN)
    parser.add_argument("--timeout", type=int, default=OTP_TIMEOUT)
    parser.add_argument("--provider", default="mailtm",
        choices=["emailnator", "mailtm", "tempmail", "tempnet", "besttemp", "mix"])
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--count", action="store_true")
    args = parser.parse_args()

    if args.list: list_accounts(); return
    if args.count: print(len(_load_accounts())); return

    cfg = Config(loop=args.loop, max_accounts=args.max, delay=args.delay,
                 otp_timeout=args.timeout, email_provider=args.provider,
                 headless=args.headless)

    accounts = _load_accounts()
    banner(cfg, len(accounts))

    ok_count = fail_count = attempt = 0
    try:
        while True:
            attempt += 1
            if cfg.max_accounts > 0 and ok_count >= cfg.max_accounts:
                break

            mail_client = _create_mail_client(cfg.email_provider)
            email = mail_client.create_email()
            if not email: fail("فشل إنشاء إيميل"); fail_count += 1; continue

            account_header(attempt, cfg.email_provider, ok_count, fail_count)
            result = register(email, cfg.password, cfg)

            if result:
                accounts.append(result)
                _save_accounts(accounts)
                ok_count += 1
                ok(f"✅ {email}")
            else:
                fail_count += 1

            if not cfg.loop: break
            if cfg.delay > 0:
                print(f"  ⏳ Waiting {cfg.delay}s...")
                time.sleep(cfg.delay)

    except KeyboardInterrupt:
        print(f"\n\n  {R}{B}⛔ اتوقف بـ Ctrl+C{RST}")

    final_stats(ok_count, fail_count, len(accounts))

if __name__ == "__main__":
    main()
```

---

## جدول المزودين الكامل (13 provider):

| # | Provider | Folder | Type | Auth Method | Email | Verify |
|---|----------|--------|------|-------------|-------|--------|
| 1 | Arena | `ارينا/` | 🍪 | Hybrid: curl_cffi + SeleniumBase | Mail.tm | Link |
| 2 | DeepSeek | `ديب سيك/` | 🍪 | Hybrid Level 2: WAF + fetch() | Emailnator | Code 6 |
| 3 | Groq | `groq/` | 🔑 | Selenium + Emailnator | Emailnator | Magic Link |
| 4 | You.com | `you.com/` | 🔑 | Requests Level 1 (Descope) | Email+Mail.tm+Dropmailx | OTP 6 |
| 5 | Zo Computer | `zo.computer/` | 🍪 | Requests Level 1 (Magic Link) | Emailnator+Mail.tm | Magic Link |
| 6 | Runable | `Runable/` | 🍪 | Requests Level 1 | Emailnator+Dropmailx | Magic Link |
| 7 | Mistral | `mistral/` | 🍪 | Requests Level 1 (Ory Kratos) | Mail.tm | OTP 6 + SMS |
| 8 | AI21 | `AI21_Maestro/` | 🔑 | Requests Level 1 (Firebase) | Emailnator+Mail.tm | Email Link |
| 9 | Cohere | `cohereR/` | 🔑 | Requests Level 1 (BlobheartAPI) | BestTemp (Livewire) | Email Link |
| 10 | Perplexity | `Perplexity AI/` | 🔑 | curl_cffi (Android Mobile API) | Mail.tm+5 others | OTP 6 |
| 11 | Grok | `grok/` | 🍪 | Hybrid: gRPC + Turnstile | mailtm+emailnator | OTP 6 |
| 12 | ERNIE | `ernie.baidu/` | 🍪 | Playwright (osfuid fingerprint) | Emailnator | OTP 6 |
| 13 | Genspark | `Genspark_😎/` | 🍪 | Requests + Azure B2C + CAPTCHA | Mail.tm | OTP 6 |

## هيكل ملفات كل Provider:
```
provider_folder/
├── provider_register.py     # إنشاء حسابات (بـ provider prefix)
├── refresh.py               # def refresh(email) -> bool (بدون prefix!)
└── accounts_provider.json   # بـ provider prefix
```
