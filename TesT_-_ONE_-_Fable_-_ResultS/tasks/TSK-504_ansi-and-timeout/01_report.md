# TSK-504 — تقرير الاكتشاف: تسرب رموز ANSI + مهلة 300s بدون Failover

> **الوضع:** محلل خارجي — Sandbox قراءة فقط
> **التاريخ:** 2026-08-01
> **القاعدة (Base) المُعلنة** (قاعدة 9) — ناتج `git log --oneline -3` الفعلي:
> ```
> 91b8c4c Delete TesT_-_ONE_-_ResultS/1
> 58d7458 Delete TesT_-_ONE_-_ResultS/TesT_-_ONE_-_ResultS directory
> c7a80af Add files via upload
> ```

---

## 1) الأعراض (من السكرين شوت)

أثناء تشغيل `delegate` على موديل `glm-5.2-vercel` ظهرت في الشات رسالة بهذا الشكل:

```
[91m❌ [Blackbox AI] خطأ في الاتصال: Failed to perform, curl: (28)
Operation timed out after 300004 milliseconds with 0 bytes received[0m
```

عَرَضان منفصلان:

| # | العرض | التصنيف |
|---|-------|---------|
| A | `[91m` و `[0m` ظاهرة كنص خام في واجهة الويب | تسرب تسلسلات ANSI (ألوان تيرمنال) لواجهة HTML |
| B | تعليق 300 ثانية كاملة (`300004 ms`) ثم فشل نهائي بلا تحويل لمزود بديل | غياب failover في مسار التفويض |

---

## 2) الأدلة (path:line + اقتباس حرفي أو أمر + ناتج فعلي)

### دليل E1 — لا يوجد أي تعقيم ANSI في الريبو إطلاقًا

الأمر الفعلي وناتجه:
```
$ grep -rln "strip_ansi" --include="*.py" server.py providers/ chain/ core/ runners/
NONE   (لا نتيجة — exit بدون أي ملف)
```
وكذلك البحث عن أي استخدام لتسلسلات ANSI أو تنظيفها:
```
$ grep -rn "strip_ansi\|_sanitize_for_web\|\\033\[\|\x1b\[\|\[91m" --include="*.py" --include="*.js" server.py providers/ chain/ core/ runners/ static/js/
(لا نتيجة)
```
> ⚠️ ملاحظة مهمة: باتش TSK-502 السابق (الموجود كمرجع في
> `TesT_-_ONE_-_ResultS/[FIX-02].../patch_code_reference.py` والذي يعرّف
> `strip_ansi` + `ProviderCircuitBreaker`) **غير مُطبَّق فعليًا على main** —
> الكود المرجعي موجود في مجلد النتائج فقط ولم يدخل `server.py` قط.

### دليل E2 — مصدر الرسالة: مزود Blackbox (ملف مفقود من الريبو)

- `server.py:48` — اقتباس حرفي:
  ```python
  from providers.blackbox import BlackboxProvider, BlackboxConfig
  ```
- الأمر وناتجه:
  ```
  $ ls providers/
  __init__.py alle_ai.py base.py budget.py capacity.py deepseek.py
  genspark.py openai_shelby.py pool.py registry.py use_ai.py
  $ wc -l providers/blackbox.py
  wc: providers/blackbox.py: No such file or directory
  ```
- `server.py:930-947` — الموديل `glm-5.2-vercel` مسجّل تحت مزود Blackbox:
  ```python
  {
      "id": "blackbox",
      "name": "⬛ Blackbox AI",
      "models": [
          ...
          "glm-5.2-vercel",
          "glm-5.2",
          ...
  ```
- `server.py:1018-1020` — إنشاء المزود:
  ```python
  elif prov_id == "blackbox":
      cfg = BlackboxConfig(model=model_name)
      provider = BlackboxProvider(cfg)
  ```
- التسجيل: `register_provider("blackbox", BlackboxProvider)` (داخل نطاق server.py:2065-2100).

**الاستنتاج المقيَّد (بدون افتراض كود لم أره — قاعدة 7):** نص الخطأ في السكرين شوت
(`❌ [Blackbox AI] خطأ في الاتصال: ... curl: (28) ... 300004 milliseconds`)
غير موجود في أي ملف بالريبو:
```
$ grep -rn "خطأ في الاتصال\|Blackbox AI" --include="*.py" .   (باستثناء مجلدات النتائج)
./server.py:931:            "name": "⬛ Blackbox AI",     ← اسم عرض فقط، ليس رسالة خطأ
```
إذن الرسالة الملوّنة بأكواد ANSI **تنشأ داخل `providers/blackbox.py` المفقود**
(على جهاز المالك)، ونمط `curl: (28)` + مهلة 300s يطابق عميل curl/curl_cffi
بـ timeout يساوي 300 ثانية داخل ذلك الملف. لا أستطيع الجزم بمحتواه — انظر
قسم «مطلوب من المالك».

### دليل E3 — الاستيراد غير محمي: السنابشوت الحالي على main لا يعمل أصلًا

- `server.py:46-48` — ثلاث استيرادات على مستوى الموديول بلا try/except:
  ```python
  from providers.you_com import YouComProvider, YouComConfig
  from providers.perplexity import PerplexityProvider, PerplexityConfig
  from providers.blackbox import BlackboxProvider, BlackboxConfig
  ```
- الأمر وناتجه:
  ```
  $ for f in providers/blackbox.py providers/you_com.py providers/perplexity.py \
        core/circuit_breaker.py providers/circuit_breaker.py; do
      [ -f "$f" ] && echo "EXISTS: $f" || echo "MISSING: $f"; done
  MISSING: providers/blackbox.py
  MISSING: providers/you_com.py
  MISSING: providers/perplexity.py
  MISSING: core/circuit_breaker.py
  MISSING: providers/circuit_breaker.py
  ```
- النتيجة: `python server.py` على snapshot الـ main الحالي سيسقط بـ
  `ModuleNotFoundError: No module named 'providers.you_com'` عند السطر 46
  قبل الوصول لأي شيء. (السيرفر يعمل عند المالك لأن النسخ المحلية موجودة
  على جهازه لكنها غير مدفوعة للريبو.)

### دليل E4 — مسار وصول الخطأ الخام للواجهة (سلسلة كاملة موثقة)

1. **نقطة النداء** — `chain/delegate.py:321` و`:351` و`:390` (ثلاث مواقع متطابقة):
   ```python
   response = self._provider.send(
       self._to_prompt_history(messages), system_prompt=system)
   ```
   `_provider` (السطر 235-238) يُحلّ إلى `ctx.active_provider` — **مزود واحد، بلا pool**.

2. **التقاط الاستثناء الخام** — `chain/delegate.py:571-576`:
   ```python
   except Exception as e:
       run.status = "failed"
       self._emit(on_event, "delegate_error", {
           "run_id": run.run_id,
           "error": str(e),
       })
   ```
   `str(e)` يحمل نص الخطأ **كما هو** — بما فيه `\x1b[91m…\x1b[0m` لو المزود ضمّنها.

3. **العبور بلا تعديل** — `runners/delegate.py:153-157` يجمّع نصوص
   `delegate_error` حرفيًا، و`server.py:442` (`_RunnerWSAdapter.emit`):
   ```python
   self._send({"type": event.type, **event.data})
   ```
   أي «بايت-بايت» بحسب توثيق الصنف نفسه (server.py:411: «الإطار الأصلي كما كان — بايت-بايت»).

4. **بوابة النقل الأخيرة** — `server.py:369-372` (`_WSAdapter._send`):
   ```python
   def _send(self, frame: dict) -> None:
       try:
           with self._lock:
               self._ws.send(json.dumps(frame, ensure_ascii=False))
   ```
   توثيق الصنف (server.py:347): «بوابة النقل الوحيدة — **موقع ws.send الأوحد** …
   check.sh يمنع بالـ grep أي ws.send خارج هذا الصنف». **لا يوجد أي تعقيم هنا.**

5. **العرض في المتصفح** — `static/js/app/10_chat_ws_stream.js:507-508`:
   ```javascript
   case "delegate_error":
       addChatMessage("assistant", `❌ خطأ في التفويض: ${data.error}`);
   ```
   المتصفح لا يفسّر `\x1b` فيعرض الباقي (`[91m`, `[0m`) كنص — **وهذا بالضبط ما في السكرين شوت**.

### دليل E5 — البنية التحتية للـ failover موجودة لكن مسار delegate يتجاهلها

- `providers/pool.py:291-318` — `ProviderPool.send_with_fallback` كامل وجاهز:
  ```python
  def send_with_fallback(self, prompt, history=None, system_prompt="") -> tuple[str, str]:
      chain = self.get_fallback_chain()
      for name, provider in chain:
          try:
              result = provider.send(prompt, history, system_prompt)
              self._breakers[name].record_success()
              return result, name
          except Exception as e:
              last_error = f"{name}: {e}"
              self._breakers[name].record_failure()
              continue
      raise RuntimeError(f"كل المزودين فشلوا — آخر خطأ: {last_error}")
  ```
- قاطع الدائرة (Circuit Breaker) مدمج داخليًا: `providers/pool.py:28`
  (`class BreakerState(StrEnum)` — R-403) مع cooldown → half-open → recovery.
- الـ pool متاح على السياق: `core/app_context.py:101` — `provider_pool: Any = None`،
  و`DelegateBridge` يستلم `ctx` بالفعل (`chain/delegate.py:216`,
  `server.py:1653`: `DelegateBridge(sctx.active_provider(), ctx=ctx)`).
- **لكن**: `grep -n "provider_pool\|send_with_fallback" chain/delegate.py` → **لا نتيجة**.
  المسار يستدعي `self._provider.send` مباشرة، فأي فشل (مهلة curl 300s) =
  استثناء واحد → `delegate_error` → نهاية الدورة، بلا أي محاولة على مزود آخر.

---

## 3) الأسباب الجذرية (خلاصة)

| # | السبب الجذري | الموقع | الأثر |
|---|--------------|--------|-------|
| RC-1 | لا توجد أي طبقة تعقيم ANSI بين نصوص المزودات وإطارات WS — وباتش TSK-502 المرجعي لم يُطبَّق على main | `server.py:369` (بوابة النقل) + السلسلة E4 كاملة | `[91m…[0m` تظهر كنص خام في الشات |
| RC-2 | `DelegateBridge` يستدعي مزودًا واحدًا (`self._provider.send`) في 3 مواقع ويتجاهل `ProviderPool.send_with_fallback` الجاهز | `chain/delegate.py:321,351,390` مقابل `providers/pool.py:291` | فشل المزود النشط = فشل دورة التفويض كلها؛ لا failover ولا قاطع دائرة يعمل لهذا المسار |
| RC-3 | مهلة 300s ورسالة الخطأ الملوّنة تنشآن داخل `providers/blackbox.py` — **ملف غير موجود بالريبو** (مستورَد في `server.py:48` بلا حماية) | ملف مفقود + E2/E3 | لا يمكن إصلاح منبع المشكلة ولا مراجعة قيمة الـ timeout بدون الملف |

---

## 4) الإصلاح المقترح (ملخص — التفاصيل في `02_proposed.patch`)

**قرار هندسي:** التعقيم في **طبقة النقل** وليس داخل كل مزود، لسببين موثقين:
1. `server.py:347-353` يعلن `_WSAdapter` «موقع ws.send الأوحد» ويحرسه `check.sh` بالـ grep —
   نقطة خنق (choke point) مثالية تغطي كل الإطارات الحالية والمستقبلية.
2. أحد المزودات المصدرية (`blackbox.py`) غير متاح أصلًا للتعديل (RC-3).

**Hunk 1 — `server.py`** (إصلاح RC-1):
- `import re` (السطر 12).
- `_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")` + `strip_ansi()` +
  `_strip_ansi_frame()` فوق `_WSAdapter` مباشرة — تعقيم الحقول النصية المتجهة
  للمستخدم فقط (`text/message/error/summary/reason`) مع مسار سريع
  (`"\x1b[" in val`) فلا كلفة على الإطارات النظيفة.
- سطر واحد داخل `_WSAdapter._send`: `frame = _strip_ansi_frame(frame)`.

**Hunk 2 — `chain/delegate.py`** (إصلاح RC-2):
- دالة جديدة `DelegateBridge._send_llm(prompt, system)`:
  تفضّل `ctx.provider_pool.send_with_fallback` عند توفره (failover + قاطع دائرة
  مجانًا من R-403)، وتسقط للمسار القديم `self._provider.send` حرفيًا عند غياب
  الـ pool — **صفر كسر** للاختبارات والعقود القائمة.
- استبدال مواقع النداء الثلاثة (`:321/:351/:390`) بـ `self._send_llm(...)`.

**خارج نطاق هذا الباتش (بقرار):** حراسة استيرادات server.py:46-48 بـ try/except —
لأن الحل الصحيح هو دفع الملفات المفقودة نفسها (انظر §6)، وأي حراسة الآن
ستخفي كسرًا حقيقيًا في main.

---

## 5) التحقق الفعلي (أوامر + نواتج حقيقية)

- **صلاحية الباتش ضد main الحالي (قاعدة 3):**
  ```
  $ cd <repo-root> && git apply --check TesT_-_ONE_-_Fable_-_ResultS/tasks/TSK-504_ansi-and-timeout/02_proposed.patch
  ✅ (exit 0 — بلا أي خرج)
  $ git status --porcelain        ← الريبو ظل نظيفًا (لم يُطبَّق شيء)
  ```
- **تحقق سلوكي في نسخة معزولة بـ /tmp** (الريبو الحقيقي لم يُمسّ) — 4/4 نجاح:
  ```
  ✅ Test A  (strip_ansi frame): إطار delegate_error الحقيقي من السكرين شوت
             يخرج نظيفًا "❌ [Blackbox AI] خطأ في الاتصال: …" بلا \x1b ولا [91m؛
             قيم غير نصية ومفاتيح غائبة آمنة؛ النص النظيف لا يُمس.
  ✅ Test B1 (pool preferred): مزود نشط يرمي timeout → _send_llm يرجع رد
             المزود البديل من send_with_fallback (نداء واحد للـ pool).
  ✅ Test B2 (no ctx → legacy): بدون ctx يمر النداء عبر self._provider.send كما كان.
  ✅ Test B3 (ctx بلا pool → legacy): getattr آمن، سقوط سلس للمسار القديم.
  ```
- **mypy** (نفس أعلام `scripts/check.sh`):
  ```
  $ mypy --ignore-missing-imports --follow-imports=silent --check-untyped-defs chain/delegate.py
  Success: no issues found in 1 source file
  $ mypy --ignore-missing-imports --follow-imports=silent --check-untyped-defs server.py
  Success: no issues found in 1 source file
  ```
- **AST parse** للملفين المعدّلين: نجاح.

كود الاختبارات الكامل (قابل للنقل إلى `tests/unit/` من طرف المالك) موجود
كـ code fences في `03_verdict.md` §«مرجع كود الاختبار» — التزامًا بقاعدة 6
(لا ملفات `.py` داخل مجلد النتائج).

---

## 6) 📌 مطلوب من المالك (قاعدة 7 — ملفات لا أستطيع افتراض محتواها)

| الملف | لماذا مطلوب |
|-------|-------------|
| `providers/blackbox.py` | **الأهم** — منبع رسالة ANSI وقيمة الـ timeout=300s. بدون قراءته لا يمكن: (أ) إزالة التلوين من المنبع، (ب) ضبط timeout أقصر/قابل للتهيئة، (ج) رفع أخطاء مصنّفة (`ProviderTimeoutError` من `providers/base.py`) بدل نص خام. وهو مستورَد في `server.py:48` — الريبو مكسور بدونه. |
| `providers/you_com.py` | مستورَد في `server.py:46` وغير موجود — main لا يعمل بدونه. |
| `providers/perplexity.py` | مستورَد في `server.py:47` وغير موجود — نفس المشكلة. |
| (اختياري) لقطة من لوج السيرفر وقت الحادثة | لتأكيد أن الاستثناء مرّ عبر `chain/delegate.py:571` تحديدًا وليس مسارًا آخر. |

**التوصية:** دفع الملفات الثلاثة للريبو (بعد تنظيف أي مفاتيح/أسرار منها)،
وبعدها يمكن إصدار TSK-504b لإصلاح المنبع (timeout قابل للتهيئة + أخطاء مصنّفة بلا ANSI).

---

## 7) حدود التحليل

- لم أشغّل السيرفر كاملًا (يتطلب الملفات المفقودة E3) — التحقق تم على مستوى
  الوحدات المعزولة + mypy + git apply --check.
- سلوك `providers/blackbox.py` وقت التشغيل استُدل عليه من نص الخطأ في السكرين شوت
  ومن مسار السلسلة E4 الموثق بالكود — وليس من قراءة الملف نفسه (غير موجود).
- الباتش لا يغيّر أي عقد إطارات: البنية والمفاتيح كما هي، التعقيم يمس **قيم
  نصية تحتوي `\x1b[` فقط**.
