# TSK-504 — الحكم النهائي (Verdict)

## ✅ القرار: **يُطبَّق (APPLY)**

| البند | الحالة |
|-------|--------|
| `git apply --check` من جذر الريبو على base `91b8c4c` | ✅ نجح (exit 0) |
| mypy (نفس أعلام `scripts/check.sh`) على الملفين المعدّلين | ✅ Success: no issues |
| تحقق سلوكي معزول (4 اختبارات) | ✅ 4/4 PASS |
| تغيير عقود الإطارات / بنية الـ frames | ❌ لا يوجد — قيم نصية ملوّثة فقط تُنظَّف |
| كسر مسار قديم (بدون pool / بدون ctx) | ❌ لا يوجد — سقوط سلس للمسار الحرفي القديم |
| لمس اختبارات قائمة لتخضيرها (قاعدة 8) | ❌ لا يوجد — صفر تعديل على `tests/` |

### طريقة التطبيق (من طرف المالك)
```bash
cd <repo-root>
git apply --check TesT_-_ONE_-_Fable_-_ResultS/tasks/TSK-504_ansi-and-timeout/02_proposed.patch  # تحقق
git apply         TesT_-_ONE_-_Fable_-_ResultS/tasks/TSK-504_ansi-and-timeout/02_proposed.patch  # تطبيق
./scripts/check.sh   # البوابة الكاملة (mypy + pytest + coverage ratchet)
```

---

## ماذا يُصلح الباتش وماذا لا يُصلح

### يُصلح ✅
1. **RC-1 (تسرب ANSI):** أي إطار WS يمر عبر بوابة النقل الأوحد (`_WSAdapter._send`)
   تُعقَّم حقوله النصية المتجهة للمستخدم (`text/message/error/summary/reason`)
   من تسلسلات `\x1b[…m` — يغطي `delegate_error` و`error` و`chunk` وكل الأنواع،
   الحالية والمستقبلية، من أي مزود.
2. **RC-2 (لا failover في delegate):** نداءات LLM الثلاثة في دورة التفويض
   (brief → implement → review) تمر الآن عبر `_send_llm` الذي يفضّل
   `provider_pool.send_with_fallback` — فشل `glm-5.2-vercel` (مهلة curl)
   يفتح قاطع الدائرة (R-403 المدمج في `providers/pool.py`) ويحوّل تلقائيًا
   للمزود التالي في السلسلة بدل إسقاط الدورة كلها.

### لا يُصلح (بقرار موثق) ⚠️
3. **RC-3 (منبع المهلة 300s والتلوين):** داخل `providers/blackbox.py` —
   **ملف غير موجود بالريبو** ولا يجوز افتراض محتواه (قاعدة 7).
   الباتش الحالي يجعل الفشل *نظيف العرض* و*قابل التعافي*، لكن تقصير
   الـ 300s نفسها وإصلاح المنبع يتطلبان الملف — انظر «مطلوب من المالك»
   في `01_report.md` §6.
4. **الاستيرادات المكسورة** (`server.py:46-48` لملفات مفقودة):
   الحل الصحيح دفع الملفات لا حراسة try/except تخفي الكسر.

---

## المخاطر وتقييمها

| الخطر | الاحتمال | التخفيف |
|-------|----------|---------|
| نص مشروع يحتوي `\x1b[` (مثال: مستخدم يلصق لوج ملوّن ويطلب تحليله) يُنظَّف في العرض | منخفض | التعقيم في **العرض/النقل فقط** — النص الأصلي في التاريخ والجلسات لا يُمس؛ والعرض بدون ألوان أصلًا هو السلوك المرغوب في HTML |
| اختلاف عقد `send_with_fallback` (يرجع tuple) عن `provider.send` (يرجع str) | معدوم | `_send_llm` يفكّ الـ tuple داخليًا ويرجع `str` دائمًا — العقد الخارجي ثابت |
| اختبارات قائمة تبني `DelegateBridge` بـ ctx يحمل `provider_pool` وهمي بدون `send_with_fallback` | منخفض | فحص `hasattr(pool, "send_with_fallback")` قبل الاستخدام → سقوط للمسار القديم |
| أداء `_strip_ansi_frame` على كل إطار (streams عالية التردد) | معدوم تقريبًا | فحص `"\x1b[" in val` الرخيص قبل أي regex — الإطارات النظيفة تمر بلا كلفة substitution |
| تعارض مستقبلي لو طُبّق مرجع TSK-502 القديم فوق هذا الباتش | متوسط | هذا الباتش **يحل محل** hunk الـ strip_ansi في مرجع TSK-502 (نفس الفكرة، نقطة حقن أدق)؛ جزء الـ CircuitBreaker من TSK-502 لم يعد لازمًا لمسار delegate لأن قاطع R-403 المدمج في pool.py يغطيه |

## أثر البوابات (Gates)

- **mypy gate:** ✅ نظيف على الملفين (تم فعليًا بنفس الأعلام).
- **coverage ratchet ≥ 68.4%:** الباتش يضيف ~25 سطرًا تنفيذيًا؛ الاختباران
  المرجعيان أدناه يغطيانها بالكامل عند نقلهما لـ `tests/unit/` — لا خطر نزول.
- **حارس `ws.send` في check.sh:** الباتش لا يضيف أي `ws.send` جديد —
  التعديل داخل `_WSAdapter._send` نفسه.
- **pytest الكامل:** لم يُشغَّل في الـ sandbox (بيئة بلا تبعيات مثبتة + قيود
  الكتابة)؛ التحقق تم بوحدات معزولة. يُشغَّل عند المالك عبر `./scripts/check.sh`.

---

## مرجع كود الاختبار (قاعدة 6 — fences بدل ملفات .py)

> للمالك: انسخ إلى `tests/unit/test_tsk504_ansi_and_failover.py` **بعد** تطبيق الباتش.

```python
# -*- coding: utf-8 -*-
"""TSK-504: تعقيم ANSI عند بوابة النقل + failover لنداءات delegate."""
import pytest


# ═══ الجزء 1: strip_ansi / _strip_ansi_frame (server.py) ═══

@pytest.fixture()
def srv():
    import server
    return server


class TestStripAnsi:
    RAW = ("\x1b[91m❌ [Blackbox AI] خطأ في الاتصال: Failed to perform, "
           "curl: (28) Operation timed out after 300004 milliseconds "
           "with 0 bytes received\x1b[0m")

    def test_strips_color_codes(self, srv):
        out = srv.strip_ansi(self.RAW)
        assert "\x1b" not in out and "[91m" not in out and "[0m" not in out
        assert out.startswith("❌ [Blackbox AI]")

    def test_non_string_passthrough(self, srv):
        assert srv.strip_ansi(123) == 123
        assert srv.strip_ansi(None) is None

    def test_clean_text_unchanged(self, srv):
        assert srv.strip_ansi("سلام نظيف") == "سلام نظيف"

    def test_multiple_sequences(self, srv):
        s = "\x1b[1m\x1b[32mOK\x1b[0m done \x1b[91mERR\x1b[0m"
        assert srv.strip_ansi(s) == "OK done ERR"


class TestStripAnsiFrame:
    def test_delegate_error_frame_sanitized(self, srv):
        frame = {"type": "delegate_error", "run_id": "r1",
                 "error": "\x1b[91mcurl: (28) timeout\x1b[0m"}
        out = srv._strip_ansi_frame(frame)
        assert out["error"] == "curl: (28) timeout"
        assert out["type"] == "delegate_error" and out["run_id"] == "r1"

    def test_structure_preserved_and_safe_types(self, srv):
        assert srv._strip_ansi_frame({"type": "done"}) == {"type": "done"}
        f = {"type": "chunk", "text": 42}
        assert srv._strip_ansi_frame(f)["text"] == 42

    def test_only_user_facing_keys(self, srv):
        f = {"type": "x", "payload_id": "\x1b[91mkeep\x1b[0m"}
        # مفتاح غير نصّي-للمستخدم لا يُمس
        assert srv._strip_ansi_frame(dict(f))["payload_id"] == f["payload_id"]


# ═══ الجزء 2: DelegateBridge._send_llm — failover (chain/delegate.py) ═══

from chain.delegate import DelegateBridge


class _OKProvider:
    def send(self, prompt, history=None, system_prompt=""):
        return f"direct:{prompt}"


class _FailingProvider:
    def send(self, prompt, history=None, system_prompt=""):
        raise RuntimeError("\x1b[91mcurl: (28) timeout\x1b[0m")


class _FakePool:
    def __init__(self):
        self.calls = 0
    def send_with_fallback(self, prompt, history=None, system_prompt=""):
        self.calls += 1
        return ("رد من مزود بديل", "deepseek")


class TestDelegateSendLLM:
    def test_pool_preferred_failover(self):
        class Ctx:
            active_provider = _FailingProvider()
            provider_pool = _FakePool()
        ctx = Ctx()
        b = DelegateBridge(provider=_FailingProvider(), ctx=ctx)
        assert b._send_llm("اختبار", "sys") == "رد من مزود بديل"
        assert ctx.provider_pool.calls == 1

    def test_no_ctx_legacy_path(self):
        b = DelegateBridge(provider=_OKProvider(), ctx=None)
        assert b._send_llm("hi") == "direct:hi"

    def test_ctx_without_pool_legacy_path(self):
        class Ctx:
            active_provider = _OKProvider()
        b = DelegateBridge(provider=_OKProvider(), ctx=Ctx())
        assert b._send_llm("x") == "direct:x"

    def test_pool_without_contract_legacy_path(self):
        class BadPool:  # بلا send_with_fallback
            pass
        class Ctx:
            active_provider = _OKProvider()
            provider_pool = BadPool()
        b = DelegateBridge(provider=_OKProvider(), ctx=Ctx())
        assert b._send_llm("y") == "direct:y"
```

> ملاحظة تشغيل: اختبارات الجزء 1 تستورد `server` — تتطلب وجود
> `providers/blackbox.py` و`you_com.py` و`perplexity.py` (المفقودة حاليًا،
> انظر `01_report.md` §6). اختبارات الجزء 2 تعمل فورًا حتى بدونها.
