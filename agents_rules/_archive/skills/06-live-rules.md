---
description: Live Rules - القواعد الحية المستخلصة من كل المشاكل السابقة
globs: "**/*.py"
---
# 🔴 القواعد الحية — مستخلصة من 67+ مشكلة حقيقية

> **المصدر الكامل:** `UNIVERSAL_PROVIDER_PROMPT.md` — فيه كل القواعد بالتفصيل.
> الملف ده = نسخة مضغوطة للاستخدام السريع.

## 🚨 القواعد الحمراء (Critical — أي خطأ فيها = فشل كامل):

| # | القاعدة | Tag |
|---|---------|-----|
| 1 | `curl_cffi` مش `requests` عادي لأي موقع فيه bot detection | [Auth] |
| 2 | كل token لازم يتاخد ديناميكياً من response السابق (مفيش hardcoded!) | [API] |
| 3 | Session واحد طول العملية — بيحافظ على الكوكيز تلقائياً | [Auth] |
| 4 | Next.js Server Actions = `multipart/form-data` + `accept: text/x-component` | [Next.js] |
| 5 | لو Next.js → response فـ RSC format مش JSON → لازم regex parse | [Parsing] |
| 6 | Descope: `stepId` في root level مش nested تحت screen | [Descope] |
| 7 | GET الصفحة قبل POST أي action مهم (subscription activation) | [SaaS] |
| 8 | `uc_open` + `sleep(8)` بدل `uc_open_with_reconnect` (بيتعطل!) | [Selenium] |
| 9 | CDP `Runtime.evaluate` + `userGesture=True` للـ React buttons | [CDP] |
| 10 | UTF-8 fix إلزامي: `sys.stdout.reconfigure(encoding="utf-8")` | [Script] |
| 11 | Atomic write: `.tmp` → `.replace()` لأي save لـ accounts.json | [Config] |
| 12 | `colorama` + fallback إلزامي — مفيش `print()` عادي | [Script] |

## 🟡 القواعد الصفراء (مهمة لكن مش فاتل):

| # | القاعدة | Tag |
|---|---------|-----|
| 13 | `provider` في JSON = auto-detect من الدومين (gmail→emailnator) | [Config] |
| 14 | Mail.tm domains بتتغير ديناميك — مفيش hardcoded domain list | [Mail] |
| 15 | كل سكريبت لازم يكون فيه argparse: `--max`, `--loop`, `--delay` | [CLI] |
| 16 | `LOOP_MODE = True` هو الـ Default — `--no-loop` للغاء | [CLI] |
| 17 | WAF_REUSE_LIMIT = 5 (يعيد فتح البراوزر كل 5 accounts) | [Selenium] |

## 🚫 Anti-Patterns — الأخطاء الأكثر شيوعاً:

| الخطأ | الصح |
|-------|------|
| `time.sleep(3)` fixed | `sb.wait_for_element_visible(s, timeout=15)` |
| `except Exception: pass` | `except Exception as e: log.error(e)` |
| `sb.execute_script(f"...{var}")` | `sb.execute_script("...", var)` |
| Token hardcoded | استخرجه من response |
| `requests` عادي مع Cloudflare | `curl_cffi` impersonate chrome |
