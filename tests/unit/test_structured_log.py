# -*- coding: utf-8 -*-
"""TSK-704 (FI-06 / NF-14) — اختبارات core/structured_log.

تغطي: صيغة JSON والحقول الثابتة، دمج structured، عدم الرفع أبدًا،
الصمت الافتراضي، idempotency للتفعيل، وعقد swallowed (لا تغيير تدفق).
"""
import io
import json
import logging

import pytest

from core import structured_log
from core.structured_log import (
    JsonFormatter, ROOT_LOGGER_NAME, configure, get_logger, swallowed,
)


@pytest.fixture
def clean_root():
    """جذر webdev نظيف قبل/بعد كل اختبار — لا تسريب handlers بين الاختبارات."""
    root = logging.getLogger(ROOT_LOGGER_NAME)
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_propagate = root.propagate
    root.handlers = []
    yield root
    root.handlers = saved_handlers
    root.setLevel(saved_level)
    root.propagate = saved_propagate


class TestJsonFormatter:
    def _record(self, msg="evt", structured=None, level=logging.DEBUG):
        rec = logging.LogRecord("webdev.t", level, "f.py", 1, msg, None, None)
        if structured is not None:
            rec.structured = structured
        return rec

    def test_fixed_fields(self):
        out = json.loads(JsonFormatter().format(self._record("hello")))
        assert out["event"] == "hello"
        assert out["level"] == "DEBUG"
        assert out["logger"] == "webdev.t"
        assert isinstance(out["ts"], float)

    def test_structured_fields_merged(self):
        rec = self._record("e", structured={"exc_type": "ValueError", "k": 1})
        out = json.loads(JsonFormatter().format(rec))
        assert out["exc_type"] == "ValueError"
        assert out["k"] == 1

    def test_single_line_output(self):
        rec = self._record("multi\nline", structured={"a": "x\ny"})
        formatted = JsonFormatter().format(rec)
        assert "\n" not in formatted  # json.dumps يهرّب \n — سطر واحد دائمًا

    def test_unserializable_values_stringified(self):
        rec = self._record("e", structured={"obj": object()})
        out = json.loads(JsonFormatter().format(rec))
        assert "object object" in out["obj"]

    def test_arabic_preserved_not_escaped(self):
        out = json.loads(JsonFormatter().format(self._record("حدث")))
        assert out["event"] == "حدث"


class TestConfigure:
    def test_installs_json_handler(self, clean_root):
        buf = io.StringIO()
        configure(stream=buf)
        get_logger("x").debug("evt1")
        line = buf.getvalue().strip()
        assert json.loads(line)["event"] == "evt1"

    def test_idempotent(self, clean_root):
        h1 = configure(stream=io.StringIO())
        h2 = configure(stream=io.StringIO())
        assert h1 is h2
        assert len(clean_root.handlers) == 1

    def test_no_propagation_to_global_root(self, clean_root):
        configure(stream=io.StringIO())
        assert clean_root.propagate is False


class TestGetLogger:
    def test_prefixes_under_root(self):
        assert get_logger("chain").name == "webdev.chain"

    def test_already_prefixed_untouched(self):
        assert get_logger("webdev.core").name == "webdev.core"
        assert get_logger().name == ROOT_LOGGER_NAME


class TestSwallowed:
    def test_silent_by_default(self, clean_root, capsys):
        # لا handler ولا تفعيل ⇒ صفر مخرجات على أي مجرى.
        swallowed("core/x.py:1", ValueError("boom"))
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err == ""

    def test_logs_when_enabled(self, clean_root):
        buf = io.StringIO()
        configure(stream=buf)
        swallowed("chain/bridge.py:372", ValueError("boom"), run_id="r1")
        out = json.loads(buf.getvalue().strip())
        assert out["event"] == "chain/bridge.py:372"
        assert out["exc_type"] == "ValueError"
        assert out["exc_msg"] == "boom"
        assert out["run_id"] == "r1"
        assert out["logger"] == "webdev.swallowed"

    def test_never_raises_on_hostile_exception(self, clean_root):
        class EvilExc(Exception):
            def __str__(self):
                raise RuntimeError("str explodes")

        buf = io.StringIO()
        configure(stream=buf)
        swallowed("core/x.py:2", EvilExc())  # يجب ألا يرفع أبدًا

    def test_never_raises_without_exception(self, clean_root):
        swallowed("core/x.py:3")  # exc=None مسموح

    def test_control_flow_unchanged(self, clean_root):
        # نفس نمط المواقع الموصولة: السجل قبل pass — التدفق كما هو حرفيًا.
        hits = []
        try:
            raise ValueError("x")
        except Exception as _exc:
            swallowed("core/x.py:4", _exc)
            pass
        hits.append("after")
        assert hits == ["after"]


class TestWiredSitesContract:
    """عقد التوصيل (TSK-704): كل موقع صامت في core/+chain/ موصول."""

    def test_no_remaining_silent_sites(self):
        import os
        import re
        silent = []
        for d in ("core", "chain"):
            for f in sorted(os.listdir(d)):
                if not f.endswith(".py"):
                    continue
                path = f"{d}/{f}"
                lines = open(path, encoding="utf-8").read().split("\n")
                for i, l in enumerate(lines):
                    if not re.search(r"except\s+Exception", l):
                        continue
                    indent = len(l) - len(l.lstrip())
                    stmts = []
                    for j in range(i + 1, min(i + 12, len(lines))):
                        s = lines[j]
                        if not s.strip():
                            continue
                        if (len(s) - len(s.lstrip())) <= indent:
                            break
                        if not s.strip().startswith("#"):
                            stmts.append(s.strip())
                    first = stmts[0] if stmts else "?"
                    if first in ("pass", "continue"):
                        silent.append(f"{path}:{i + 1}")
        # الاستثناء الوحيد المصرح به: حارس swallowed نفسه (منع العودية).
        allowed = {s for s in silent if s.startswith("core/structured_log.py:")}
        assert silent == sorted(allowed), (
            f"مواقع ابتلاع صامتة غير موصولة: {sorted(set(silent) - allowed)}"
        )
