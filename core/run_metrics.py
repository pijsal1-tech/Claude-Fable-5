# -*- coding: utf-8 -*-
"""RunMetrics (TSK-610 / PM-03 §R6): تجميع مقاييس الـ runs عبر الزمن.

المشكلة (MASTER_REVIEW.md:433): القياسات لحظية «تُبث وتُنسى» — بعد
TSK-609 كل مسار يبث `duration_ms` في حدث `run_finished` على bus
الرصد، لكن لا مشترك يجمعها: لا سجل runs، لا p50/p95، لا أساس لرصد
تدهور الأداء بين الإصدارات.

الحل هنا (إضافة صرفة — لا مساس بأي مسار قائم):
- ``RunMetricsStore``: مخزن JSONL ملحق-فقط (نمط ProjectMemoryStore —
  سطر JSON لكل run منتهٍ) + قارئ يلخّص p50/p95 بأسلوب nearest-rank
  (بلا تبعيات جديدة).
- ``RunMetricsRecorder``: مشترك على bus الرصد (T-047) — يلتقط
  `RunStarted` (mode) ويقرنه بـ `RunFinished` (status/duration_ms)
  بمفتاح run_id ثم يُلحق سطرًا واحدًا. نقطة التقاط واحدة تغطي
  المسارات الأربعة (direct/chain/agent/delegate).

قرارات موثّقة (§TSK-610):
- ملف واحد على مستوى التطبيق (``metrics/runs.jsonl``) — RunFinished
  لا يحمل هوية مشروع؛ ربط لكل-مشروع كان سيتطلب حالة إضافية هشة.
- فشل الكتابة لا يُسقط الـ run أبدًا: EventBus يعزل استثناءات
  المشتركين بالتصميم + try داخلي مع log (تصنيف NF-14: ابتلاع مقصود
  لمسار رصد اختياري).
- سقف ``_pending`` (أقدم-يُطرد) — run بدأ ولم ينتهِ (انهيار) لا يراكم
  ذاكرة بلا حد؛ RunFinished بلا RunStarted مقترن يُسجَّل بحقول فارغة.
"""
from __future__ import annotations

import json
import math
import pathlib
import threading
import time
from collections import OrderedDict
from typing import Any

from core.events import BusEvent, RunFinished, RunStarted

#: أقصى runs بادئة غير منتهية نتذكرها (انهيارات لا تراكم ذاكرة).
MAX_PENDING = 256

#: أقصى أسطر يقرأها الملخّص من ذيل الملف (سقف زمن القراءة).
MAX_TAIL_LINES = 5000


class RunMetricsStore:
    """مخزن JSONL ملحق-فقط لمقاييس الـ runs + ملخّص p50/p95.

    سطر واحد لكل run منتهٍ:
    ``{"ts", "run_id", "mode", "status", "duration_ms", "context_chars"}``
    — الحقول المجهولة وقت التسجيل تكون ``""``/``None`` (لا اختراع).
    """

    def __init__(self, path: str | pathlib.Path) -> None:
        self.path = pathlib.Path(path)
        self._write_lock = threading.Lock()

    # ── الكتابة ──

    def append(self, record: dict[str, Any]) -> None:
        """إلحاق سطر — O(1)؛ يرمي لو تعذّرت الكتابة (المستدعي يعزل)."""
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with self._write_lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()

    # ── القراءة ──

    def read_records(self, limit: int = MAX_TAIL_LINES) -> list[dict]:
        """آخر ``limit`` سطرًا صالحًا — الأسطر الممزّقة تُتخطى بصمت
        (ذيل مقطوع بانهيار لا يعطّل الملخّص)."""
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        records: list[dict] = []
        for raw in lines[-limit:]:
            try:
                rec = json.loads(raw)
            except ValueError:
                continue
            if isinstance(rec, dict):
                records.append(rec)
        return records

    @staticmethod
    def percentile(values: "list[int | float]", p: float) -> "float | None":
        """nearest-rank: أصغر قيمة يغطي ترتيبها ⌈p/100·N⌉ — None للفارغ."""
        if not values:
            return None
        ordered = sorted(values)
        rank = max(1, math.ceil((p / 100.0) * len(ordered)))
        return float(ordered[rank - 1])

    def summary(self) -> dict[str, Any]:
        """ملخّص جاهز للعرض: عدّادات + p50/p95 للمدة (كليًا ولكل mode)."""
        records = self.read_records()
        durations = [r["duration_ms"] for r in records
                     if isinstance(r.get("duration_ms"), (int, float))]
        by_mode: dict[str, list[float]] = {}
        status_counts: dict[str, int] = {}
        for r in records:
            status = str(r.get("status", ""))
            status_counts[status] = status_counts.get(status, 0) + 1
            d = r.get("duration_ms")
            if isinstance(d, (int, float)):
                by_mode.setdefault(str(r.get("mode", "")), []).append(d)
        return {
            "count": len(records),
            "status_counts": status_counts,
            "p50_duration_ms": self.percentile(durations, 50),
            "p95_duration_ms": self.percentile(durations, 95),
            "by_mode": {
                mode: {
                    "count": len(vals),
                    "p50_duration_ms": self.percentile(vals, 50),
                    "p95_duration_ms": self.percentile(vals, 95),
                }
                for mode, vals in sorted(by_mode.items())
            },
        }


class RunMetricsRecorder:
    """مشترك bus الرصد: يقرن RunStarted↔RunFinished ويُلحق سطر مقاييس.

    الاستدعاء: ``event_bus.subscribe(recorder)`` — الكائن قابل للنداء.
    استثناءات الكتابة تُبتلع مع log (NF-14: مسار رصد اختياري لا يجوز
    أن يُسقط الـ run؛ الـ bus يعزل أصلًا — دفاع مزدوج مقصود).
    """

    def __init__(self, store: RunMetricsStore,
                 max_pending: int = MAX_PENDING) -> None:
        self._store = store
        self._max_pending = max_pending
        self._pending: "OrderedDict[str, dict]" = OrderedDict()
        self._lock = threading.Lock()

    def __call__(self, event: BusEvent) -> None:
        if isinstance(event, RunStarted):
            with self._lock:
                self._pending[event.run_id] = {
                    "mode": event.mode,
                    "context_chars": event.payload.get("context_chars"),
                }
                while len(self._pending) > self._max_pending:
                    self._pending.popitem(last=False)
            return
        if not isinstance(event, RunFinished):
            return
        with self._lock:
            started = self._pending.pop(event.run_id, None) or {}
        record = {
            "ts": time.time(),
            "run_id": event.run_id,
            "mode": started.get("mode", ""),
            "status": event.status,
            "duration_ms": event.payload.get("duration_ms"),
            "context_chars": started.get("context_chars"),
        }
        try:
            self._store.append(record)
        except Exception as e:
            # NF-14 (ابتلاع مقصود — قرار TSK-610): فشل كتابة الرصد
            # (قرص/صلاحيات) لا يمس الـ run — يُسجَّل ويُتجاوز.
            print(f"  ⚠️ RunMetrics: فشل إلحاق سطر المقاييس: {e}")
