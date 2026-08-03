# 🚫 Anti-Patterns + إعدادات افتراضية

## الأخطاء الشائعة:

| الغلط | المشكلة | الصح |
|-------|---------|------|
| `except Exception: pass` | بتخبي الأخطاء | `except Exception as e: log.error(e)` |
| `time.sleep(3)` في Selenium | static wait = fragile | `sb.wait_for_element_visible(SEL, timeout=15)` |
| `sb.execute_script(f"...{var}")` | JS injection crash | `arguments[0]` + `arguments[1]` |
| `len(result)` بدون None check | crash لو None | `len(result or "")` |
| selector hardcoded في نص الكود | صعب الصيانة | constants في أول الملف |
| `ACCOUNTS = "file.json"` | CWD مش script dir | `Path(__file__).resolve().parent / "file.json"` |

## إعدادات افتراضية (مش محتاج تحددها):

| الإعداد | القيمة |
|---------|--------|
| `headless` | `false` |
| `timeout` | `20s` |
| `default_password` | `"A9!k@e3#Qz1$Lp"` |
| `delay_between` | `5-15s` random |
| `expires_in` | `24h` |
| `max_accounts` | `0` (unlimited) |
| `session_format` | `full` |

## Red Flags — لو شفت أي حاجة من دول تقف فوراً:

- ❌ تكرار نفس الكود في أكتر من مكان
- ❌ Hardcoded Values (أرقام/مفاتيح/مسارات)
- ❌ `except Exception: pass` بدون logging
- ❌ ملفات > 500 سطر بدون سبب
- ❌ مزج `f-string` مع `plain string` في JS code للـ CDP
- ❌ `uc_open_with_reconnect` — استخدم `uc_open` + `sleep(8)`
