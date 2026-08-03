# 📦 shared/ Library + monitor.py Integration

---

## 📁 shared/ — مكتبة مشتركة

```
shared/
├── __init__.py   # re-exports: from shared import step, ok, fail
├── ui.py         # Banner + step + ok + fail + warn + info + waiting + account_header + final_stats
├── io.py         # atomic_save + load_accounts + upsert_account + list_accounts
└── delay.py      # human_delay + random delay
```

### الاستخدام:
```python
from shared import step, ok, fail, warn, banner, final_stats
from shared import load_accounts, atomic_save, upsert_account
from shared import human_delay
```

> **DRY:** بدل ما كل سكريبت يكتب step/ok/fail → import من shared!

---

## 🧠 monitor.py — المراقب المركزي

### إضافة provider جديد:
```python
# في monitor.py → PROVIDERS dict:
"new_provider": {
    "accounts": BASE_DIR / "folder_name" / "accounts_provider.json",
    "refresh_module": str(BASE_DIR / "folder_name" / "refresh.py"),
    "expires_default": 24,           # ساعات
    "skip_status": ["inactive", "banned", "❌", "refresh_failed"],
},
```

### الـ Flow:
```
monitor.py --provider deepseek
  ↓ load accounts.json
  ↓ لكل حساب:
      needs_refresh()? → last_updated + expires_default
      ↓ yes → import refresh.py → refresh(email)
      ↓ no → skip
  ↓ print stats
```

### أوامر monitor:
```bash
python monitor.py --provider deepseek     # provider واحد
python monitor.py --all                   # كل الـ providers
python monitor.py --watch                 # مراقبة مستمرة
python monitor.py --dry-run               # تجربة بدون تنفيذ
```

---

## 🔄 refresh.py — الأنماط المتاحة

### Pattern 1: Requests Only (الأبسط)
```python
def refresh(email: str) -> bool:
    """Ory Kratos password login / Firebase token refresh"""
    acc = _find_account(email)
    session = get_session()
    # ... login بالباسورد → كوكيز جديدة
    acc["last_updated"] = datetime.now().isoformat()
    _save(accounts)
    return True
```

### Pattern 2: Hybrid (الأذكى)
```python
def refresh(email: str) -> bool:
    """Layer 0 → 1 → 2"""
    # Layer 0: Token cache check (~0s)
    if _is_fresh(acc): return True

    # Layer 1: Requests login (~2s)
    if _requests_login(acc): return True

    # Layer 2: Browser fallback (~30s)
    return _browser_login(acc)
```

### Pattern 3: Magic Link (لو مفيش password)
```python
def refresh(email: str) -> bool:
    """Magic Link re-auth — محتاج email provider"""
    mail_client = _create_mail_client(acc["provider"])
    # ... request magic link → poll email → confirm
```

### Pattern 4: 3-Layer (Zo.computer)
```python
REFRESH_LAYERS = [
    ("token_check", _try_token, "0s"),
    ("magic_link_mailtm", _try_mailtm, "~3s"),
    ("magic_link_emailnator", _try_emailnator, "~15s"),
]
```

---

## 📋 القواعد:

| # | القاعدة |
|---|---------|
| 1 | `refresh.py` = بدون prefix! (Register بـ prefix) |
| 2 | `def refresh(email: str) -> bool` — Signature ثابت |
| 3 | `skip_status` فيها `refresh_failed` — monitor يتخطاه |
| 4 | `last_updated` يتحدث عند كل refresh ناجح |
| 5 | `expires_default` = ساعات (مش أيام) |
| 6 | Atomic write للـ accounts.json بعد كل refresh |
| 7 | لو refresh فشل → `status = "refresh_failed"` مش بيتمسح! |
| 8 | `check_balance()` يرجع 3 حالات: `≥0` (OK) / `-2` (401) / `-1` (خطأ) |

---

## 🛡️ Quarantine + Auto-Revive

```python
# ─── في monitor.py ────────────────────────────
QUARANTINE_MINUTES = 15

# لو provider فشل 3 مرات متتالية:
if fail_count >= 3:
    provider["status"] = "quarantined"
    provider["quarantined_at"] = datetime.now().isoformat()

# Auto-Revive: بعد 15 دقيقة يرجع يجرب
if provider.get("status") == "quarantined":
    dt = datetime.fromisoformat(provider["quarantined_at"])
    if (datetime.now() - dt).total_seconds() > QUARANTINE_MINUTES * 60:
        provider["status"] = "active"  # يرجع يجرب!
```

> **📌** Quarantine أفضل من Disable الدائم — بيدي الـ provider فرصة يرجع!

---

## 🔧 force_refresh Logic

```python
# monitor.py بيحدد مين محتاج refresh:
def needs_refresh(acc, expires_hrs):
    status = acc.get("status", "")

    # ⚠️ دول لازم force_refresh فوراً:
    if status in ("no_cookie", "refresh_failed", "expired"):
        return True  # مفيش بديل — لازم يجدد!

    # عادي: last_updated + expires_default
    last = acc.get("last_updated", "")
    if not last: return True
    dt = datetime.fromisoformat(last)
    return (datetime.now() - dt).total_seconds() > expires_hrs * 3600
```

