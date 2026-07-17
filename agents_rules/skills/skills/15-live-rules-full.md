# ⚡ جدول القواعد الحية الكامل — 70 قاعدة

> **🤖 كل سطر = درس اتعلمناه من مشكلة حقيقية. الجدول بيكبر مع كل provider جديد.**

## Tags المتاحة:
`[Auth]` `[Descope]` `[Firebase]` `[Next.js]` `[RSC]` `[Emailnator]` `[API]` `[Parsing]` `[Network]` `[SaaS]` `[Selenium]` `[Cookies]` `[Headers]` `[Subscription]` `[Config]` `[CLI]` `[Mail]` `[DRY]` `[CDP]` `[Debug]` `[Script]` `[Hybrid]` `[Refresh]` `[Playwright]` `[Cloudflare]`

---

## 📧 Email & Config (قواعد 1, 13-17, 21-22, 28, 31-34, 39, 42, 44-45, 50-51, 55, 64, 66-67, 70)

| # | القاعدة | Tag | أهمية |
|---|---------|-----|-------|
| 1 | Emailnator timeout ≥ 30s + retry 3x | [Emailnator] | 🟡 |
| 13 | `provider` في JSON = auto-detect من الدومين: gmail→emailnator, ridermail→dropmailx, باقي→mailtm | [Config] | 🟡 |
| 14 | Mail.tm = الوحيد اللي ليه credentials (password+token+account_id) → حفظ في `email_creds` | [Mail.tm] | 🔴 |
| 15 | `email_creds` keys suffixed: `password_mailtm`, `token_mailtm` | [Config] | 🟡 |
| 16 | تسمية: register=بـ prefix / refresh=بدون / accounts=بـ prefix | [Config] | 🟡 |
| 17 | Module اسمه فيه `.` → `importlib.util.spec_from_file_location()` | [Config] | 🟡 |
| 21 | Config variables لازم تعليق عربي: `DELAY = 15  # ثواني` | [Config] | 🟡 |
| 22 | كل سكربت: argparse + Config dataclass + EMAIL_PROVIDER (rotation) + pathlib + atomic write | [Config] [CLI] | 🔴 |
| 28 | Mail.tm domains ديناميك — أي مش gmail/ridermail = mailtm. مفيش hardcoded! | [Config] | 🟡 |
| 31 | LOOP CONFIG constants = defaults في argparse — `--no-loop` flag لـ override | [Config] [CLI] | 🔴 |
| 32 | Terminal output: مفيش print() عادي + colorama fallback + مسافات في stats | [Config] [CLI] | 🔴 |
| 33 | temp-mail.org: `curl_cffi` + `impersonate="chrome124"`. POST /mailbox | [Config] [Mail] | 🟡 |
| 34 | Dynamic domain cache: `set()` module-level بيتملى من create(). ممنوع hardcoded! | [Config] [Mail] | 🔴 |
| 39 | `shared/` library: `from shared import step, ok, fail` — DRY! | [Config] [DRY] | 🔴 |
| 42 | gmail = emailnator **أو** tempnet — بيتحدد من `--provider` CLI | [Config] [Mail] | 🟡 |
| 44 | monitor.py: PROVIDERS dict **مرة واحدة بس** — copy-paste = truncate! | [Config] [DRY] | 🔴 |
| 45 | Email provider choices = classes فعلية! مفيش phantom choices | [Config] [Mail] | 🔴 |
| 50 | PowerShell Set-Content بيضيف BOM → استخدم Python لـ JSON | [Config] [Debug] | 🟡 |
| 51 | `datetime.fromisoformat()` أفضل من strptime | [Script] | 🟡 |
| 55 | accounts.json: `provider` field + `expires_in > 0` + atomic write | [Config] | 🟡 |
| 64 | UTF-8 fix: `sys.stdout.reconfigure(encoding="utf-8")` إلزامي | [Script] [Config] | 🔴 |
| 66 | `actual_provider` من `email_info.get("provider")` مش `_detect_provider` | [Config] | 🔴 |
| 67 | Config dataclass ≠ SSOT تلقائي — لازم تمرر params صريحة | [Config] [CLI] | 🔴 |
| 70 | PowerShell `-c` بيكسر Arabic — اكتب script في `C:\tmp\` | [Debug] | 🟡 |

---

## 🔐 Auth Patterns (قواعد 2-10, 18-20, 23-27, 29-30, 46-47, 56-58)

| # | القاعدة | Tag | Provider |
|---|---------|-----|----------|
| 2 | Descope SDK headers (`x-descope-*`) إلزاميين | [Descope] | You.com |
| 3 | `stepId` في root level مش nested | [Descope] | You.com |
| 4 | `flow/next` → interactionId + componentsVersion + isCustomScreen | [Descope] | You.com |
| 5 | OTP interactionId = HTML element ID | [Descope] | You.com |
| 6 | Descope tokens في 3 أماكن: authInfo/response/session cookies | [Descope] [Cookies] | You.com |
| 7 | Next.js Server Actions → RSC format → regex parse | [Next.js] [RSC] | You.com |
| 8 | GET الصفحة قبل POST لتفعيل features | [SaaS] | You.com |
| 9 | `next-action` hash = build-specific → auto-discover | [Next.js] | You.com |
| 10 | Server Actions = multipart/form-data + text/x-component | [Next.js] | You.com |
| 18 | Ory Kratos: `Accept: application/json` إلزامي | [Auth] [Headers] | Mistral |
| 19 | Django CSRF: x-csrftoken + Referer + Origin | [Auth] [Cookies] | Mistral |
| 20 | Mistral domain = `admin.mistral.ai` مش `console` | [API] [Config] | Mistral |
| 23 | Mistral refresh = Ory Kratos password login | [Auth] [Refresh] | Mistral |
| 24 | AI21 verify = `spmailtechno.com/f/a/` redirect → oobCode | [Auth] [Firebase] | AI21 |
| 25 | Firebase refresh = POST securetoken + `x-www-form-urlencoded` | [Auth] [Firebase] | AI21 |
| 29 | AI21 api_key response = `key_value` مش `api_key` | [API] | AI21 |
| 30 | AI21 workspaces = `{workspaces: [...]}` dict مش list | [API] | AI21 |
| 46 | Grok gRPC: binary protobuf + OTP `.replace("-","").upper()` | [Auth] [API] | Grok |
| 47 | ERNIE osfuid من jnmq (SHA1 fingerprint) — Playwright كامل | [Auth] [Playwright] | ERNIE |
| 56 | Arena two-step login: React nativeSetter + verify_typed | [Auth] [Hybrid] | Arena |
| 57 | CDP Runtime.evaluate = WINNER للـ React. userGesture=True | [Selenium] [CDP] | Arena |
| 58 | Azure B2C: csrf+transId from HTML + PKCE code_challenge | [Auth] [API] | Genspark |

---

## 🔧 Selenium & Hybrid (قواعد 11-12, 35-41, 43, 48-49, 52-54, 59-63, 65, 68-69)

| # | القاعدة | Tag | Provider |
|---|---------|-----|----------|
| 11 | Magic Link auth: POST request → JWT في email → POST confirm | [Auth] | Zo Computer |
| 12 | SSE signup: stream=True + iter_lines + timeout ≥ 300s | [SSE] | Zo Computer |
| 35 | Livewire: CSRF meta + wire:snapshot + html.unescape → JSON | [API] [Livewire] | Cohere |
| 36 | Cohere redirect chain: allow_redirects=False + loop 10 hops | [Auth] [Redirect] | Cohere |
| 37 | Email verify link: regex near "Confirm" مش أول link | [Parsing] [Mail] | Cohere |
| 38 | Template Compose: regex swap أولاً → AI fallback + Length Guard | [Code Gen] | v2 |
| 40 | temporary-mail.net: cloudscraper + data-code SHA256 | [API] [Mail] | Cohere |
| 41 | tempnet data-code: reload بعد activate إلزامي! lang="" | [API] [Mail] | Cohere |
| 43 | Cohere refresh = BlobheartAPI: LoginWithEmail → rawKey | [Auth] [Refresh] | Cohere |
| 48 | WAF-Reuse: SeleniumBase مفتوح + fetch() + WAF_REUSE_LIMIT=5 | [Selenium] [Cloudflare] | DeepSeek |
| 49 | refresh.py: كل الكوكيز مع بعض مش واحدة بس | [Cookies] | ERNIE |
| 52 | Hybrid Reset: 3 layers (cache→requests→browser) | [Auth] [Refresh] | DeepSeek |
| 53 | ai_engine.py: --input-file + --output-dir + ThreadPoolExecutor global | [Config] | ai_engine |
| 54 | 3-Layer Refresh: REFRESH_LAYERS list — الأسرع أولاً | [Script] [Refresh] | Zo.computer |
| 59 | CAPTCHA Multi-Solver: ThreadPoolExecutor + Consensus vote | [Script] | Genspark |
| 60 | CDP f-string bug: مزج f-string + plain = `}}` صامت → % formatting | [CDP] [Debug] | Arena |
| 61 | uc_open_with_reconnect = browser exit! استخدم uc_open + sleep(8) | [Selenium] | Arena |
| 62 | CDP Text Search > CSS Selector. getBoundingClientRect للـ visibility | [CDP] | Arena |
| 63 | CDP debug: طبع visible elements قبل click | [Debug] [CDP] | Arena |
| 65 | Refresh Fallback: cookie injection → hybrid_login fallback | [Script] [Auth] | Arena |
| 68 | `refresh_failed` في skip_status — monitor يتخطاه | [Config] [Refresh] | All |
| 69 | `check_balance()` يرجع 3 حالات: ≥0 / -2 (401) / -1 (خطأ) | [API] [Refresh] | Genspark |

---

## 📌 Code Gen (قواعد 26-27)

| # | القاعدة | Tag | أهمية |
|---|---------|-----|-------|
| 26 | Template Composer: golden script → بدّل name+URLs | [Code Gen] | 🟡 |
| 27 | Length Guard: auto-fix أقصر 50%+ → ارفض. Template>200L → generated/ | [Code Gen] | 🔴 |

<!-- ⬆️ ضيف القواعد الجديدة هنا ⬆️ -->
