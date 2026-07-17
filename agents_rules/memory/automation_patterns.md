# ⚙️ Automation Patterns — الـ Flows والـ Sequences

> الـ AI يقرأ الملف ده لما الطلب فيه automation أو تسلسل عمليات

## 🔄 Registration Flow Pattern (إلزامي)

```
1. إنشاء email مؤقت (emailnator/tempnet/mailtm)
2. تسجيل في الموقع بالـ email
3. انتظار OTP/رابط التحقق
4. تأكيد البريد
5. حفظ cookies + credentials في accounts_*.json (atomic)
6. تكرار (LOOP_MODE = True بـ default)
```

## 🔃 Refresh Flow Pattern

```
1. قرأ accounts_*.json
2. فلتر active + expired (تخطي banned)
3. لكل حساب: جرب refresh session
   - نجح → حدث cookies + last_updated + status=active
   - فشل بـ 401 → جرب re-login كامل
   - فشل بـ 403 → status=banned
   - فشل بـ 429 → wait + retry
4. احفظ النتائج (atomic)
5. اطبع stats: refreshed/failed/skipped
```

## 🖥️ Browser Automation Rules

```
✅ الترتيب الصح:
1. جرب pure requests أول
2. لو Cloudflare → curl_cffi
3. لو JS-heavy → SeleniumBase + uc=True
4. لو React buttons → CDP Runtime.evaluate + userGesture=True
5. مش execute_script — React مش بيشوفه
```

## 📐 Script Structure Pattern

```python
# 1. Constants (module-level)
LOOP_MODE = True
MAX_ACCOUNTS = 50
DELAY_MIN, DELAY_MAX = 2.0, 5.0

# 2. Config @dataclass
@dataclass
class Config: ...

# 3. Email provider functions
# 4. Registration logic
# 5. Main loop
# 6. Stats + banner
```

## 🔗 Integration Chain

```
register.py → refresh.py → monitor.py → scheduler.py
     ↓              ↓           ↓
accounts.json   cookies     health score
```

---
*[AI: ضيف هنا أي pattern جديد اكتشفته]*
