# 🔴 Debug: Arena + Cohere + Zo.computer + AI21

---

## 🟢 Arena.ai — CDP Runtime.evaluate WINNER

### القاعدة الذهبية:
```python
def _cdp_eval(sb, js: str):
    """تشغيل JS في main world — userGesture=True هو السر"""
    return sb.driver.execute_cdp_cmd("Runtime.evaluate", {
        "expression": js, "returnByValue": True,
        "awaitPromise": False, "userGesture": True,
    }).get("result", {}).get("value")
```

> **17 طريقة اتجربت — واحدة بس اشتغلت!**

| الطريقة | النتيجة | السبب |
|---------|---------|-------|
| `sb.click()` / `uc_click()` | ❌ | WebDriver layer |
| `execute_script btn.click()` | ❌ | **isolated world** — React مش فيه |
| `Input.dispatchMouseEvent` | ❌ | React مش بيسمعه |
| ActionChains | ❌ | WebDriver layer |
| ⭐ `Runtime.evaluate + userGesture=True` | ✅ | **main world + trusted!** |

### القواعد:

| # | القاعدة | أهمية |
|---|---------|-------|
| 1 | `_cdp_eval()` = Strategy 1 دايماً — قبل أي طريقة تانية | 🔴 |
| 2 | Two-step login: Email → Continue → Password → Submit | 🔴 |
| 3 | `uc_open_with_reconnect` = browser exit! استخدم `uc_open + sleep(8)` | 🔴 |
| 4 | f-string + plain string في JS = `}}` silent bug → % formatting | 🔴 |
| 5 | CDP text search > CSS selector (الموقع بيغير الـ design) | 🟡 |
| 6 | Accept Cookies: dismiss مرتين + sleep(1) بينهم | 🟡 |
| 7 | Cookie injection refresh → hybrid_login fallback | 🟡 |
| 8 | `debug_login_btn.py` لطباعة buttons الموجودة قبل click | 🟡 |

---

## 🔵 Cohere — BlobheartAPI + SendGrid Redirect Chain

### Auth Flow:
```
BestTempEmail (Livewire) → create email
  ↓ POST RegisterWithEmail → send confirm email
  ↓ Poll inbox → regex "Confirm" button href (مش أول link!)
  ↓ SendGrid redirect chain (10 hops, allow_redirects=False):
      SendGrid → 302 dashboard/confirm-email?token=xxx
      → 307 /api/auth/confirm_email
      → 303 (sets access_token+refresh_token cookies)
  ↓ POST /api/auth/v2/create-api-key → API key!
```

### القواعد:

| # | القاعدة |
|---|---------|
| 1 | `allow_redirects=False` + loop 10 hops — check `r.cookies` كل hop |
| 2 | Verify email link: regex "Confirm" button href مش أول SendGrid link! |
| 3 | Livewire CSRF: `wire:snapshot` → `html.unescape` → JSON |
| 4 | Refresh = BlobheartAPI: `LoginWithEmail → Session → GetOrCreateDefaultAPIKey` |
| 5 | `_detect_provider`: besttemp domains (aboodbab/mamabood/mohemil) |

---

## 🟡 Zo.computer — Magic Link + SSE Signup

### Auth Flow:
```
Emailnator/Mail.tm → create email
  ↓ POST /api/email-login/request → Magic Link JWT (ES256, 20 min)
  ↓ Poll email → extract JWT from link
  ↓ POST /api/email-login/confirm → auth cookies (access_token + refresh_token)
  ↓ POST /signup/waitlist (SSE stream, timeout ≥ 300s!)
      account → computer → domain (2-4 minutes!)
  ↓ GET /signup/status → verify
```

### القواعد:

| # | القاعدة |
|---|---------|
| 1 | SSE timeout ≥ 300s — boot بياخد 2-4 دقايق |
| 2 | مفيش `/api/auth/refresh-token` — magic-link pattern دايماً |
| 3 | `REFRESH_LAYERS` list of tuples — قابل للتوسع (سطرين + function) |
| 4 | Mail.tm magic link بيوصل في 0-3s (API polling) vs 6-30s في Emailnator |

---

## 🔴 AI21 — Firebase Auth + oobCode

### Auth Flow:
```
Emailnator/Mail.tm → create email
  ↓ POST Firebase signUp → idToken + refreshToken
  ↓ Poll email → extract oobCode from spmailtechno.com/f/a/ redirect
  ↓ POST confirmEmailVerification (oobCode)
  ↓ POST Firebase signInWithPassword → fresh idToken
  ↓ GET /v1/studio-workspaces/all → workspace_id
  ↓ POST /admin/v1/api-key/create → key_value (مش api_key!)
```

### القواعد:

| # | القاعدة |
|---|---------|
| 1 | `key_value` مش `api_key` ولا `key` — الـ field اسمه `key_value`! |
| 2 | Workspaces = `{"workspaces": [...]}` dict مش list — handle الحالتين |
| 3 | Firebase refresh = `POST securetoken.googleapis.com` + `x-www-form-urlencoded` (مش JSON!) |
| 4 | Verify domain = `spmailtechno.com/f/a/` — redirect → oobCode في query string |
| 5 | `virgilian.com` + أي دومين مش gmail/ridermail = mailtm |
