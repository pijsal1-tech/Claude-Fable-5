# Worker Runbook — تشغيل وضع `dispatch: worker` (T-110, R-804)

دليل تشغيل عملية الـ worker المنفصلة: متى تحتاجها، كيف تشغّلها، وكيف
تشخّص أعطالها. المعمارية والمسوّغات في `docs/phase8_plan.md` §3.

---

## 1. متى تحتاج هذا الوضع؟

- **لا تحتاجه افتراضيًّا.** `dispatch: in-proc` (الافتراضي) هو السلوك
  التاريخي حرفيًّا: الـ runner يعمل في thread داخل عملية الخادم —
  أحادي-العملية درجة أولى (عقد R-804).
- تحتاج `dispatch: worker` عندما تجوّع التشغيلات الثقيلة حلقة الـ WS
  أو تريد scale-out أفقيًّا: التنفيذ ينتقل لعمليات worker منفصلة
  تستهلك قائمة عمل Redis وتبث الأحداث رجوعًا.

## 2. المتطلبات

| المتطلب | التفصيل |
|---|---|
| Redis | نسخة standalone واحدة (لا Cluster/Sentinel في v1) |
| العنوان | متغير البيئة `REDIS_URL` (افتراضي `redis://localhost:6379/0`) |
| الـ extra | `pip install "redis>=5.0"` — اختياري؛ بدونه in-proc يعمل بلا مساس |
| config | `dispatch: "worker"` في `config.yaml` (قيمة مجهولة = فشل إقلاع صاخب) |

## 3. التشغيل

```bash
# 1) Redis (إن لم يكن يعمل)
redis-server --port 6379 --daemonize yes

# 2) worker واحد أو أكثر (كل واحد بهوية تلقائية فريدة)
python worker.py                       # حلقة مستمرة (Ctrl-C للإيقاف)
python worker.py --worker-id w-alpha   # هوية صريحة (تظهر في الحجوزات)
python worker.py --once                # دورة واحدة ثم خروج (فحص يدوي)
python worker.py --redis-url redis://redis-host:6379/1
python worker.py --lease-ttl-ms 30000  # عمر حجز المشروع (الافتراضي 30s)

# 3) الخادم — بعد ضبط dispatch: "worker"
python server.py   # البانر يعرض: 📮 Dispatch: worker
```

## 4. دورة الحياة (ما الذي يحدث فعلًا)

```
الخادم (WorkerDispatchClient)            العامل (Worker)
──────────────────────────────           ─────────────────────────────
enqueue → wq:runs (XADD)          ──►    claim (XREADGROUP — يدخل PEL)
                                         lease.acquire (SET NX PX)
                                           ├─ فشل: requeue + ack
                                           └─ نجاح: خيط تجديد (ثلث TTL)
متابعة ذيلية ev:<run_id> (XREAD)  ◄──    تنفيذ Runner → بث الأحداث
إعادة بث على _RunnerWSAdapter            RunFinished(+result)
ticket.finish(status)                    ack (XACK) + lease.release
```

- **الحجز**: `lease:<project_id>` = «مشروع واحد = worker واحد» عابر
  للعمليات. التجديد والتحرير مشروطان بالملكية (Lua) — عامل لا يمس
  حجز غيره أبدًا.
- **الـ failover**: موت worker = توقف التجديد ⇒ الحجز ينقضي بعد TTL
  ويستحوذ عامل آخر؛ مدخلته غير المؤكَّدة تبقى في PEL حتى يستعيدها
  آخر بـ `reclaim` (XAUTOCLAIM) — تسليم at-least-once.

## 5. التشخيص

```bash
redis-cli XLEN wq:runs                     # عمق قائمة العمل
redis-cli XPENDING wq:runs workers         # مدخلات مُستلَمة بلا ack
redis-cli GET "lease:<project_id>"         # من يحمل حجز المشروع؟
redis-cli PTTL "lease:<project_id>"        # كم تبقى من عمر الحجز؟
redis-cli XRANGE "ev:<run_id>" - + COUNT 20  # أحداث تشغيلة بعينها
```

| العرَض | السبب المرجح | العلاج |
|---|---|---|
| الخادم ينتظر حتى المهلة (failed: مهلة انتظار العامل) | لا worker يعمل / REDIS_URL مختلف بين الطرفين | شغّل worker وتأكد من نفس العنوان |
| `pending` يتراكم | worker انهار قبل ack | worker جديد يستعيد عبر `reclaim` بعد `min_idle_ms` |
| تشغيلات مشروع تُعاد باستمرار (requeued) | حجز عالق لعامل ميت | انتظر انقضاء TTL؛ أو `redis-cli DEL lease:<project_id>` (ملاذ أخير — تأكد أن العامل ميت فعلًا) |
| فشل إقلاع الخادم بـ ValueError عن dispatch | قيمة مجهولة في config | القيم الصالحة: `in-proc` / `worker` فقط |

## 6. حدود النطاق الحالية (T-110)

- **الـ runner الافتراضي في العامل هو EchoRunner المرجعي** — ربط
  runners الإنتاج (ChainRunner فوق ChainBridge كامل) يتطلب إقلاع سياق
  المشروع داخل العامل، وهو مجال نشر لاحق؛ درزة الحقن جاهزة
  (`Worker(runner_factory=...)`).
- بوابات الموافقة لا تعبر العمليات بعد (الحمولة JSON-آمنة فقط).
- إلغاء الخادم يُنهي الانتظار محليًّا؛ العامل يكمل مدخلته الجارية.
- توازي الإطارات بايت-بايت يُثبته T-111 (frame-parity harness).
