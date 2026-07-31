# Demo Strategy Plugin — الحزمة المرجعية لمؤلّفي الإضافات (T-102 / R-801)

أبسط إضافة استراتيجية صالحة لـ WebDev AI Editor، قابلة للتثبيت كحزمة
مستقلة عبر pip. استخدمها قالبًا لإضافتك.

## التثبيت والتجربة

```bash
# من جذر المستودع (بيئة المضيف نفسها):
pip install ./examples/demo_strategy

# تحقق من الاكتشاف:
python -c "
from chain.plugin_registry import StrategyPluginRegistry
r = StrategyPluginRegistry(); r.discover()
print('loaded:', list(r.loaded), 'quarantined:', r.quarantined)
"

# الإزالة تعيد السلوك الأساسي حرفيًا:
pip uninstall -y webdev-ai-demo-strategy
```

## تشريح الإضافة

1. **entry point** في `pyproject.toml` تحت المجموعة
   `webdev_ai.strategies` — الاسم (`demo_echo`) هو اسم الاستراتيجية
   في السجل، والقيمة تشير إلى الصنف.
2. **الصنف** يجب أن يكون *صنفًا* (لا دالة) يكشف:
   - `build(ctx)` — تستلم `PluginContext` (العقد الكامل برأس
     `chain/plugin_api.py`) وترجع `chain.strategies.StrategyResult`
     (خطوات + `ExecutionPolicy`). إرجاع `None` = حجر صحي.
   - `routing_hints: dict` — متى تُرشَّح الإضافة:
     - `keywords: list[str]` — الطلب الحاوي أي كلمة (بدون حساسية
       حالة) يُرشَّح لهذه الإضافة.
     - `max_complexity: float` (اختياري) — لا ترشيح فوق هذا التعقيد.
3. **بوابة التحميل** (`chain/plugin_registry.py`): import → shape →
   dry-run على fixture ثابت. أي فشل ⇒ سجل حجر صحي، والمضيف يقلع
   دائمًا. المحجورون يُطبعون عند الإقلاع.
4. **نطاق الصلاحيات**: الإضافة ترى `PluginContext` فقط — لا مدير
   ملفات، لا جلسات، لا خادم. الكتابة تمر من مسار actions المحروس
   بالبوابة كأي استراتيجية مدمجة.

## متى تنفَّذ إضافتك؟

اختيار الاستراتيجية داخل الطبقة يتم في
`SmartOrchestrator.select_strategy`: بعد حساب التعقيد، إن طابق الطلبُ
`routing_hints` لإضافة محمّلة (ولم يكن هناك `force_strategy`) تُبنى
خطة الإضافة وتنفَّذ عبر مسار Runner الطبيعي نفسه (بوابة الموافقة،
checkpoints، الأحداث). أي استثناء من `build()` وقت التشغيل ⇒ سقوط
آمن للاختيار المدمج — الإضافة لا تُسقط الطلب أبدًا.

## ماذا يصلك في `ctx`؟ (TSK-730b)

عند البناء الحقيقي (لا dry-run) يصلك السياق مُثرًى:

- `ctx.run_id` — معرّف التشغيلة الفعلي (`run-xxxxxxxx`) الذي أنشأه
  ChainBridge قبل التخطيط؛ استخدمه لترقيم أي أثر تنتجه إضافتك.
  في dry-run البوابة يكون `"plugin-dry-run"`.
- `ctx.metadata["complexity"]` — نتيجة `analyze_complexity().to_dict()`
  كاملة (`total` وأخواتها) — نفس الأرقام التي رشّحتك عبر
  `max_complexity`. القاموس **نسخة دفاعية**: تعديلك عليه لا يمس شيئًا.
- **قيد `emit` وقت التخطيط**: `build()` يُنادى أثناء التخطيط المتزامن
  قبل انطلاق التشغيل — حقّاقة `emit` هناك noop بالتصميم (لا EventBus
  في الأوركستريتور). البث الحي (`event_bus_emitter`) متاح للسياقات
  التي تُبنى وقت التشغيل فقط.

## أين تظهر إضافتك؟ (TSK-730a)

- عند الإقلاع: سطر `🧩 Strategy plugins: ...` أو تحذير حجر صحي.
- في حزمة التشخيص `/api/diagnostics` (زر «تنزيل حزمة التشخيص» في
  لوحة الأوامر): مفتاح `plugins = {loaded, quarantined}` — أسماء
  ومراحل وأسباب فقط (عقد التطهير: لا مسارات، لا أسرار).
