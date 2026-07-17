# 🧩 Code Patterns — Patterns جاهزة للنسخ

## 1. react_type() — لما sb.type() مش بيحدث React state

```python
def react_type(sb, selector: str, text: str):
    """React controlled inputs بتاكل القيمة العادية — الحل: nativeInputValueSetter"""
    sb.execute_script("""
        const el = document.querySelector(arguments[0]);
        const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype, 'value').set;
        setter.call(el, arguments[1]);
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('blur', {bubbles: true}));
    """, selector, text)
```

## 2. clear_session() — Nuclear reset بين كل حساب

```python
def clear_session(sb):
    """⚠️ لازم بين كل حساب — sessionStorage بيفضل بين الحسابات!"""
    sb.execute_script("window.sessionStorage.clear();")
    sb.execute_script("window.localStorage.clear();")
    sb.delete_all_cookies()
    sb.open("about:blank")
```

## 3. collect_full_session() — لو بتحقن session

```python
def collect_full_session(sb) -> dict:
    return {
        "cookies": {c["name"]: c["value"] for c in sb.get_cookies()},
        "localStorage": sb.execute_script(
            "return Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))"
        ) or {},
    }
```

## 4. Pre-flight trick — لو بتحقن localStorage

```python
# ⚠️ مش تفتح الصفحة مباشرة — React بيكتشفك!
# الحل: افتح صفحة خفيفة → حقن → افتح الصفحة
sb.open(f"{BASE_URL}/robots.txt")  # خفيف مش بيحمل React
for k, v in session_data["localStorage"].items():
    sb.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", k, v)
sb.open(f"{BASE_URL}/chat")        # دلوقتي React بيلاقي الـ token ✅
```

## 5. force_click_submit() — 4 strategies

```python
def force_click_submit(sb, selector: str) -> bool:
    for fn in [
        lambda: sb.click(selector),
        lambda: sb.execute_script(f"const b=document.querySelector(arguments[0]);b.disabled=false;b.click()", selector),
        lambda: sb.send_keys(selector, "\n"),
        lambda: sb.execute_script("document.querySelector('form')?.submit()"),
    ]:
        try: fn(); return True
        except: pass
    return False
```

## 6. Error Recovery + Exponential Backoff

```python
for attempt in range(1, 4):
    try:
        result = do_register(session, email, password)
        if result: break
    except Exception as e:
        print(f"  ⚠️ محاولة {attempt}/3: {e}")
    time.sleep(2 * attempt)  # 2s → 4s → 6s
```

## 7. accept_checkboxes() — قبول Terms تلقائي

```python
def accept_checkboxes(sb) -> int:
    return sb.execute_script("""
        let c=0;
        for(const cb of document.querySelectorAll('input[type="checkbox"]')){
            if(cb.disabled||cb.checked)continue;
            const s=getComputedStyle(cb);
            if(s.display==='none'||s.visibility==='hidden')continue;
            cb.click();c++;
        }
        return c;
    """) or 0
```

## 8. mask_password() + human_delay()

```python
def mask_password(pwd: str) -> str:
    """Zz9kQe3... → Zz*****"""
    return pwd[:2] + "*" * (len(pwd) - 2) if len(pwd) > 2 else "**"

def human_delay(min_s=1.0, max_s=3.0):
    """delay عشوائي بين الخطوات — بيخلي البوت يبان بشري"""
    import random, time
    time.sleep(random.uniform(min_s, max_s))
```

## 9. Browser Restart (كل N حسابات)

```python
# ⚠️ Chrome بيتقل بعد 3-5 حسابات — memory leaks!
# success_streak أفضل من total count — الفشل يصفّر العداد
RESTART_EVERY = 5
if success_streak >= RESTART_EVERY:
    sb_ctx.__exit__(None, None, None)
    sb_ctx = SB(uc=True, headless=HEADLESS)
    sb = sb_ctx.__enter__()
    success_streak = 0
```

## 10. SeleniumBase Selector Template

```python
# ─── غيّر الـ Selectors دي بس لأي موقع ───────────
SITE_URL    = "https://YOUR_AI_SITE.com/login"
EMAIL_INPUT = "input[type='email']"
PASS_INPUT  = "input[type='password']"
SUBMIT_BTN  = "button[type='submit']"
MSG_INPUT   = "textarea"
REPLY_DONE  = "div.done-indicator"       # ← الأهم! مؤشر انتهاء الرد
MSG_CONTENT = "div.response"
TIMEOUT     = 15
# ─────────────────────────────────────────────────
```

### مؤشرات انتهاء الرد (حسب الموقع):

| الموقع | المؤشر | الطريقة |
|--------|--------|---------|
| DeepSeek | 5 أزرار `db183363` | Button Counting |
| ChatGPT | زرار Stop يختفي | `element_not_visible` |
| Claude | spinner يختفي | `element_not_visible` |
| Gemini | `aria-live` region | text stability |
| أي موقع جديد | افحص DevTools (F12) | اختار الأنسب |

## 11. JS Click — تخطي CSS hidden elements

```python
# ⚠️ المشكلة: عنصر موجود في DOM بس Selenium بيقول "not interactable"
# السبب: parent بيه class "hidden md:flex" (Tailwind responsive)
# الحل: JS click بيتخطى كل visibility checks
sb.execute_script("""
    arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});
    arguments[0].click();
""", sb.find_element(SELECTOR))
```

## 12. waiting() — عداد تنازلي ملوّن

```python
def waiting(seconds: int, msg: str = "انتظار"):
    """عداد تنازلي بين الخطوات — بيعرض الوقت المتبقي"""
    for i in range(seconds, 0, -1):
        print(f"\r  ⏳ {msg} ({i}s)...", end="", flush=True)
        time.sleep(1)
    print(f"\r  ✅ {msg} — خلص!         ")
```

> **📌** استخدمها بدل `time.sleep(N)` — المستخدم يشوف الوقت المتبقي!

