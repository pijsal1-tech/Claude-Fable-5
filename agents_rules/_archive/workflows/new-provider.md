---
description: How to create a new AI provider registration script (Level 1 = pure requests)
---

# New Provider Registration Script — القواعد الإلزامية

> **IMPORTANT**: Read `UNIVERSAL_PROVIDER_PROMPT.md` FIRST before writing any code!

## 1. Structure (copy from `you.com/you.com_register.py`)

// turbo-all

### Required Imports
```python
import argparse
import pathlib
from dataclasses import dataclass
```

### Required Components
1. **Config dataclass** — all settings in one place
2. **`_BASE_DIR = pathlib.Path(__file__).resolve().parent`** — no `os.path`
3. **argparse CLI** with these flags:
   - `--max` (int) — number of accounts
   - `--loop` (bool) — infinite loop mode
   - `--delay` (int) — delay between accounts
   - `--timeout` (int) — max seconds per account
   - `--provider` — email provider: `mailtm|emailnator|dropmailx|besttemp|tempnet|mix` or combo
4. **Banner + Colors** — colorama with fallback
5. **Helper functions**: `step()`, `ok()`, `fail()`, `warn()`, `info()`, `waiting()`
6. **Arabic comments on ALL config variables** — إلزامي:
```python
LOOP_MODE       = False           # True = loop مستمر | False = حساب واحد وبس
DELAY_BETWEEN   = 15              # ثواني بين كل حساب
ACCOUNT_TIMEOUT = 180             # ثواني ماكس لإنشاء حساب واحد
MAX_ACCOUNTS    = 0               # 0 = unlimited | رقم = يقف بعد كذا حساب
OTP_TIMEOUT     = 60              # ثواني ماكس مستنى الـ OTP code
```

## 2. Email Client (at least one)
- `MailTmClient` — always include (pure requests)
- `EmailnatorClient` — optional (Gmail aliases, pure requests)
- `TempMailOrgClient` — optional (curl_cffi + impersonate)
- `BestTempEmailClient` — optional (Livewire, no captcha)
- `TemporaryMailNetClient` — optional (cloudscraper, Gmail aliases, Cloudflare bypass)

## 3. Account Timeout
```python
def _timed_out(step_name: str) -> bool:
    if config.ACCOUNT_TIMEOUT <= 0:
        return False
    elapsed = time.time() - start_time
    if elapsed >= config.ACCOUNT_TIMEOUT:
        fail(f"Account timeout! ({int(elapsed)}s) at {step_name}")
        return True
    return False
```

## 4. Save Account (Atomic Write + Rollback)
```python
def save_account(...):
    path = pathlib.Path(config.ACCOUNTS_FILE)
    accounts = load_accounts()
    # ... build entry dict ...
    tmp = path.with_suffix('.tmp')
    try:
        tmp.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(path)
    except OSError as e:
        fail(f"Save failed: {e}")
        tmp.unlink(missing_ok=True)
```

### Required Fields in Saved Account:
- `email`, `password`, `provider` (auto-detect from domain)
- `api_key`, `key_name` (if applicable)
- `status`: "active"
- `expires_in`: hours (0 = no expiry)
- `last_updated`: datetime string
- `cookies`: full session cookies dict
- `email_creds`: provider-specific (e.g., `password_mailtm`, `token_mailtm`)

## 5. Main Loop
- `list_accounts()` — formatted account list
- `KeyboardInterrupt` handler — colored `⛔ اتوقف بـ Ctrl+C`
- `final_stats()` — success/fail/rate

## 6. After Completion
1. Update `UNIVERSAL_PROVIDER_PROMPT.md`:
   - Add provider to **providers table**
   - Add **live rules** specific to this provider
   - Add **full problems documentation** section (flow map, APIs, problems, rules)
2. Test: `python script.py --list`
3. Test: single account creation

## 7. Naming Convention
- Script: `{provider}_register.py`
- Accounts file: `accounts_{provider}.json`
- Folder: `d:\SMS\Deep Ai\{provider}\`
