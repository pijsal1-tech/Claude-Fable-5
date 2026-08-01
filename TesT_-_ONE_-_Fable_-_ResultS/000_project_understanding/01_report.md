# فهم المشروع — WebDev AI Editor (قراءة على base `91b8c4c`)

> محلل خارجي — Sandbox قراءة فقط • 2026-08-01
> كل ادعاء أدناه مسنود بمسار:سطر أو أمر فعلي (قاعدة 5).

## 1) ما هو المشروع

محرر/مساعد تطوير ويب بالذكاء الاصطناعي:
- **الخادم:** Python + Flask (`server.py` — 2000+ سطر) + WebSocket عبر
  `flask_sock` (`server.py:33`: `from flask_sock import Sock`).
- **الواجهة:** JS تحت `static/js/app/` — أبرزها `10_chat_ws_stream.js`
  (استقبال إطارات WS وعرضها في الشات).
- **البوابة:** `scripts/check.sh` — mypy بأعلام
  `--ignore-missing-imports --follow-imports=silent --check-untyped-defs`
  + pytest + coverage ratchet (زيادة-فقط، خط أساس في `coverage_baseline.txt`)
  + حارس grep يمنع `ws.send` خارج `_WSAdapter` (موثق في `server.py:353`).

## 2) خريطة المسارات المعمارية (المتعلقة بـ TSK-504)

```
[Frontend] 10_chat_ws_stream.js
     │  WS frame {"type":"message", ...}
     ▼
server.py: _ws_message → core/chat_dispatch.py (dispatch_chat_message)
     │  Smart Router → RoutingTier: DIRECT / CHAINED / DELEGATE
     ▼ (DELEGATE — chat_dispatch.py:371-395)
runners/delegate.py: DelegateRunner.run
     ▼
chain/delegate.py: DelegateBridge.run_delegation
     │  brief → implement → review  (3 نداءات LLM:
     │  delegate.py:321 / :351 / :390 — كلها self._provider.send)
     │  استثناء؟ → delegate.py:571-576 → emit("delegate_error", {"error": str(e)})
     ▼
server.py:442 _RunnerWSAdapter.emit → {"type": event.type, **event.data}  (بايت-بايت)
     ▼
server.py:369 _WSAdapter._send → ws.send(json.dumps(frame))   ← «موقع ws.send الأوحد»
     ▼
10_chat_ws_stream.js:507 case "delegate_error" → addChatMessage(..., data.error)
```

## 3) طبقة المزودات

- الموجود فعليًا في `providers/`:
  `__init__.py, alle_ai.py, base.py, budget.py, capacity.py, deepseek.py,
  genspark.py, openai_shelby.py, pool.py, registry.py, use_ai.py`
- **المستورَد في `server.py:46-48` وغير الموجود** (يكسر تشغيل main الحالي):
  `providers/you_com.py`, `providers/perplexity.py`, `providers/blackbox.py`
- `providers/pool.py` (388 سطرًا): `ProviderPool` مع قاطع دائرة مدمج
  (R-403 — `BreakerState` سطر 28، cooldown/half-open/recovery) و
  `send_with_fallback` (سطر 291) و`stream_with_fallback` (سطر 320)
  و`get_fallback_chain` (سطر 271: النشط أولًا ثم الباقي حسب الجودة).
- `core/app_context.py:101`: `provider_pool: Any = None` — الـ pool معروض
  على السياق التطبيقي؛ `AppContext.active_provider` (سطر 112) يُقرأ وقت النداء.
- الموديل موضوع الحادثة `glm-5.2-vercel` مسجّل تحت مزود `blackbox`
  (`server.py:930-947`).

## 4) عقود مهمة اكتُشفت أثناء القراءة

- **T-047 (R-604):** `_WSAdapter` (server.py:346) هو بوابة النقل الوحيدة؛
  check.sh يمنع `ws.send` خارجه — أي إصلاح «عرضي» يجب أن يُحقن هنا.
- **T-041 (R-501):** مسار إرسال واحد `RUNNERS[strategy](**deps).run(...)`
  (server.py:449-457) — كل الأوضاع خلف عقد Runner موحّد.
- **R-102 (T-008):** `DelegateBridge._provider` خاصية تُحلّ وقت النداء من
  `ctx.active_provider` (chain/delegate.py:235-238).
- **R-403:** دورة حياة الفشل ملك قاطع الدائرة داخل pool.py حصريًا
  (تعليق pool.py:355-357).

## 5) حالة تاريخية ذات صلة

- مجلد نتائج سابق `TesT_-_ONE_-_ResultS/` يحتوي `[FIX-02]` بمرجع كود
  `strip_ansi` + `ProviderCircuitBreaker` (TSK-502) — **لم يُطبَّق أي منهما
  على main**: `grep -rln strip_ansi` على كود الإنتاج → لا نتيجة،
  و`providers/circuit_breaker.py` / `core/circuit_breaker.py` غير موجودين.
- TSK-501 (كشف مسارات المشروع) مُطبَّق على main:
  `core/chat_dispatch.py` يحوي `classify_path_relation` و`ATTACHMENTS_MARKER`.

## 6) قيود بيئة التحليل الحالية

- الريبو **لا يعمل تشغيلًا** على snapshot main الحالي (استيرادات مفقودة §3) —
  فالتحقق تم بوحدات معزولة + mypy + `git apply --check` بدل تشغيل السيرفر.
- لا كتابة خارج `TesT_-_ONE_-_Fable_-_ResultS/`، لا git commit/push —
  كل أعمال توليد الباتش تمت في نسخ scratch تحت `/tmp` والريبو ظل نظيفًا
  (`git status --porcelain` فارغ قبل إنشاء مجلد النتائج).
