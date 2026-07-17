---
description: إضافة provider جديد لـ monitor.py — خطوات الدمج مع المراقب المركزي
---

# /add-to-monitor — دمج Provider مع monitor.py

> بعد ما تعمل `{provider}_register.py` + `refresh.py` → أضفه للمراقب
> 📍 **قبل البدء:** راجع `.agents/memory/provider_knowledge.md`

// turbo-all

## المتطلبات قبل البدء

```
✅ {provider}_register.py يشتغل
✅ refresh.py موجود ويشتغل
✅ refresh.py فيه: def refresh(email: str) -> bool
✅ accounts_{provider}.json فيه حسابات
```

## [خطوة 1/4] أضف entry في monitor.py

```python
# افتح monitor.py → PROVIDERS dict
# أضف في الآخر (قبل القوس الأخير):

PROVIDERS = {
    # ... باقي الـ providers ...

    "{provider}": {
        "accounts": BASE_DIR / "{folder}" / "accounts_{provider}.json",
        "refresh_module": str(BASE_DIR / "{folder}" / "refresh.py"),
        "expires_default": 24,   # ساعات — غيّر حسب الـ provider
        "skip_status": ["inactive", "banned", "❌"],
    },
}
```

### القيم المهمة:
| الحقل | الوصف | أمثلة |
|-------|-------|-------|
| `expires_default` | عمر الـ session بالساعات | 24 (يوم), 48 (يومين), 720 (شهر), 2160 (3 شهور) |
| `skip_status` | الحالات اللي بيتخطاها | `["inactive", "banned", "❌", "refresh_failed"]` |

## [خطوة 2/4] تأكد إن refresh.py compatible

```python
# refresh.py لازم يكون فيه:
def refresh(email: str) -> bool:
    """
    تجديد session لحساب واحد.
    Returns True لو نجح, False لو فشل.
    """
    # ... كود التجديد ...
    return True  # أو False
```

## [خطوة 3/4] اختبر

```bash
# فحص provider واحد بدون تجديد
python monitor.py --provider {provider} --dry-run

# فحص provider واحد مع تجديد
python monitor.py --provider {provider}

# فحص الكل
python monitor.py

# فحص دوري (كل 5 دقائق)
python monitor.py --loop --interval 5
```

## [خطوة 4/4] تأكد من scheduler

```bash
# scheduler بيشغل monitor كل ساعة تلقائي
# مش محتاج تعمل حاجة إضافية

# لاختبار يدوي:
python scheduler.py --once monitor
```
