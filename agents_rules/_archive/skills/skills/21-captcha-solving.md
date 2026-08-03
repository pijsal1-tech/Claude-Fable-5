# 🔓 CAPTCHA Multi-Solver Pattern

> **📌 استراتيجية حل CAPTCHA لأي provider فيه captcha (Genspark, ERNIE, أي موقع جديد)**

---

## 🏗️ Architecture

```
Image → ThreadPoolExecutor (بالتوازي):
  ├─ Groq Vision (Maverick/Scout) — ~0.7s 🏆
  ├─ Pollinations (OpenAI Azure+Claude) — مجاني
  └─ OCR (ocr.z.ai) — fallback
          ↓
  Consensus Vote:
    - لو 2+ متفقين → الجواب
    - لو مختلفين → Judges (Perplexity x7)
          ↓
  CAPTCHA Text ✅
```

---

## 📐 الـ 4 Methods

```python
from captcha_solver import CaptchaService

svc = CaptchaService()

# 1. من URL
text = svc.solve_from_url("https://site.com/captcha.png")

# 2. من Base64 (Azure B2C CAPTCHA)
text = svc.solve_from_base64("data:image/jpeg;base64,/9j/...")

# 3. من ملف
text = svc.solve_from_file("captcha.png")

# 4. Crop (جزء من صورة)
text = svc.solve_from_crop(image_bytes, x=10, y=20, w=200, h=50)
```

---

## 🎯 الـ 3 Strategies

| Strategy | المكتبة | السرعة | الدقة | التكلفة |
|----------|---------|--------|-------|---------|
| `ocr` | ocr.z.ai API | ~1.5s | 70% | مجاني |
| `tesseract` | pytesseract (محلي) | ~0.5s | 50% | مجاني + محلي |
| `2captcha` | 2captcha.com API | ~10s | 95% | $2/1000 |

```python
# اختيار strategy:
svc = CaptchaService(strategy="ocr")       # default
svc = CaptchaService(strategy="tesseract") # محلي
svc = CaptchaService(strategy="2captcha")  # أعلى دقة
```

---

## 🧠 Multi-Solver (Genspark Pattern)

```python
from concurrent.futures import ThreadPoolExecutor

def solve_captcha_multi(image_b64: str) -> str:
    """3 solvers بالتوازي + consensus vote"""
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(groq_solve, image_b64): "groq",
            pool.submit(pollinations_solve, image_b64): "pollinations",
            pool.submit(ocr_solve, image_b64): "ocr",
        }
        results = {}
        for f in as_completed(futures):
            name = futures[f]
            try: results[name] = f.result()
            except: pass

    # Consensus
    from collections import Counter
    votes = Counter(r for r in results.values() if r)
    if votes:
        winner, count = votes.most_common(1)[0]
        if count >= 2:
            return winner  # 2+ متفقين ✅

    # Judges (Perplexity x7)
    return judge_vote(results)
```

---

## ⚡ تحسينات

| Pattern | الفايدة |
|---------|---------|
| Session Pooling (`requests.Session`) | أسرع 3x للطلبات المتتالية |
| SHA1 Hash Cache | نفس الصورة مرتين → cached بدون API |
| Image Preprocessing (grayscale + contrast 1.5x) | حجم أقل 20% + OCR أدق |
| `solve_batch()` بـ ThreadPoolExecutor | حل أكتر من CAPTCHA بالتوازي |
| Retry + Backoff (3 محاولات) | HTTP 429/500/503 |
| Groq token rotation (`random.sample`) | تخطي rate limit |

---

## 📍 المسار

```
بي ريييب/z.ai_ocr/
├── captcha_solver.py     # الـ Service الرئيسي (4 methods + 3 strategies)
├── captcha_client.py     # واجهة بسيطة (facade)
└── config.json           # اختياري — override فقط
```
