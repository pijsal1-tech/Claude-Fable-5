# 👤 User Context — يُقرأ تلقائياً

## 🎯 هوية المستخدم
- **اللغة:** مصري دايماً — مش فصحى مش إنجليزي
- **الأسلوب:** مختصر مباشر + emojis
- **المستوى:** محترف في Python + Automation

## 🏗️ المشروع الحالي
```
المشروع: AI_PROVIDERS / C__cursor
الهدف: نظام orchestration لـ 14+ AI provider
الـ Providers: arena, deepseek, groq, mistral, ai21, cohere,
              ernie, you_com, zo_ai, runable, uncensored,
              promptcowboy, genspark, perplexity
الحسابات: 13,000+ حساب في .AAA_GGG_iii_VIBE_CODING/
Monitor: monitor.py — يجدد الـ sessions تلقائياً
```

## ⚙️ Stack التلقائي
```yaml
primary: Python 3.10+
tools:
  - curl_cffi        # HTTP مع TLS fingerprinting
  - SeleniumBase     # uc=True لـ Cloudflare bypass
  - requests/cloudscraper
  - colorama         # CLI output دايماً ملوّن
patterns:
  - accounts.json    # atomic write (.tmp → .replace)
  - refresh()        # standard interface للـ monitor
  - LOOP_MODE=True   # default في كل register script
```

## 🐍 Python Best Practices (تطبّق تلقائاً)
```
✅ dataclass أو Pydantic للـ models
✅ Type hints في كل function
✅ asyncio.to_thread() للـ sync code داخل async
✅ try/except شامل مع logging في كل DOM interaction
✅ config من .env — ممنوع hardcoded values
✅ atomic write: .tmp → .replace() للـ JSON
⚠️  Cloudflare → MUST uc=True في SeleniumBase
⚠️  Selenium → MUST NOT user_data_dir (port conflict)
⚠️  React buttons → CDP Runtime.evaluate + userGesture=True
```

## 📋 قواعد الرد
```
- ممنوع مسح أي ملف — تعديل بس
- كل إعداد جديد في config/settings.py + .env.example
- Git commit قبل أي تعديل كبير
- مفيش تواريخ في التوثيق
- في الآخر: 🔍 نقد ذاتي (5 نقاط)
```

## 🔄 الـ Monitor Interface القياسي
```python
# كل refresh.py لازم يكون فيه:
def refresh(email: str) -> bool:
    """Standard monitor interface"""
    ...
```
