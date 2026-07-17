---
description: إضافة refresh.py لـ provider — تجديد sessions والـ cookies
---

# /add-refresh — إضافة Refresh Script لـ Provider

> Template لـ `refresh.py` — تجديد sessions/cookies/tokens
> 📍 **قبل البدء:** اقرأ `.agents/memory/provider_knowledge.md` + `automation_patterns.md`

// turbo-all

## [خطوة 1/3] ابعت الـ System Prompt ده لأي AI

```
═══════════════════════════════════════════════════════════════
ROLE: Senior Python Engineer — Session Management Architect
═══════════════════════════════════════════════════════════════

You are building a session refresh script for an AI provider.
Follow the AI_PROVIDERS project patterns exactly.

PROJECT CONTEXT:
  Stack:   Python 3.10+ | curl_cffi | colorama
  Storage: JSON atomic (.tmp→replace) | Config @dataclass
  Style:   Arabic comments | colorama + fallback
  Shared:  from shared import step, ok, fail, load_json, save_json

EXISTING REFRESH SCRIPTS (study their patterns!):
  ✅ groq/refresh.py       → API key refresh
  ✅ genspark/refresh.py   → Cookie re-login
  ✅ arena/refresh.py      → Cookie injection + hybrid_login fallback
  ✅ deepseek/refresh.py   → Android v3 curl_cffi token refresh
  ✅ mistral/refresh.py    → Bearer token refresh
  ✅ cohere/refresh.py     → API session refresh
  ✅ ernie/refresh.py      → Baidu passport session refresh

━━━ REQUIRED COMPONENTS ━━━

1. Config @dataclass:
   ACCOUNTS_FILE, LOGIN_URL, TIMEOUT, MAX_RETRIES

2. refresh_account(account) → bool:
   - Extract cookies/tokens from account
   - Try to refresh session (API call / re-login)
   - On success → update cookies + last_updated + status="active"
   - On failure → mark status="expired"

3. refresh_all(accounts_file):
   - Load all accounts
   - Filter status="active" or status="expired"
   - Try refresh each one
   - Save updated accounts (atomic)
   - Print stats: refreshed / failed / skipped

4. Integration with monitor.py:
   - refresh_all() must be callable from monitor.py
   - Return: {"refreshed": N, "failed": N, "total": N}

5. CLI:
   --all          → refresh all accounts
   --email EMAIL  → refresh specific account
   --expired-only → refresh only expired ones
   --dry-run      → show what would happen without doing it
   --list         → show current account statuses

6. Error Handling:
   - 401 → try full re-login
   - 403 → account probably banned, mark status="banned"
   - 429 → wait + retry
   - Network error → skip, try next

CONSTRAINTS:
  ✓ Config @dataclass at top
  ✓ Arabic comments throughout
  ✓ colorama + fallback
  ✓ from shared import step, ok, fail
  ✓ try/except on every API call
  ✓ Atomic JSON writes
  ✓ Compatible with monitor.py (importable function)
  ✓ Works: python refresh.py --all

OUTPUT: Complete script, line 1 to last.
═══════════════════════════════════════════════════════════════
```

## [خطوة 2/3] ابعت تفاصيل الـ Provider

```
Provider: [الاسم]
Login URL: [رابط تسجيل الدخول]
Auth type: [cookie / bearer / API key]
Refresh method: [re-login / refresh_token / API call]
Notes: [أي ملاحظة]
```

## [خطوة 3/3] بعد التوليد

```bash
# syntax check
python -c "import ast; ast.parse(open('refresh.py', encoding='utf-8').read()); print('✅ OK')"

# اختبر على حساب واحد
python refresh.py --email "test@example.com"

# اختبر الكل
python refresh.py --all --dry-run
python refresh.py --all

# تأكد إن monitor.py يقدر يستورده
python -c "from refresh import refresh_all; print('✅ importable')"
```
