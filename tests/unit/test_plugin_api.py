# -*- coding: utf-8 -*-
"""T-101 (R-801): PluginContext — سطح صلاحيات مقيّد + بوابة grep.

يغطي (بنود قبول T-101):
- **اختبار السطح (attribute surface)**: الإضافة المستلمة PluginContext
  تقرأ عروض السياق وتبث أحداثًا، ولا يوجد على السطح أي مسار لمدير
  الملفات الخام / مخزن الجلسات / الخادم (أسماء السمات تُفحص حرفيًا).
- **دورة emit كاملة (round-trip)**: emit من داخل build() تصل
  كـ StepProgress مكتوب النوع على EventBus حقيقي بنفس run_id.
- **بوابة check.sh**: موجودة نصًا في السكريبت، ونسخة الفحص هنا
  ترفض انتهاكًا مزروعًا في ملف مؤقت وتقبل الوحدتين الحقيقيتين
  (نفس نمط بوابات rglob/الألوان — تفشل الحزمة لا السكريبت فقط).

+ عزل frozen (لا استبدال حقّاقات)، نسخ دفاعية (metadata/الحمولات)،
  fixture_context ثابت، وتكامل السجل: dry-run يسلّم PluginContext.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.plugin_api import (  # noqa: E402
    FIXTURE_REQUEST,
    PluginContext,
    event_bus_emitter,
    fixture_context,
)
from context.bundle import ContextBundle, ContextItem  # noqa: E402
from core.events import EventBus, StepProgress  # noqa: E402


# ═══════════════ أدوات ═══════════════

def _bundle(*items):
    b = ContextBundle()
    b.extend(items)
    return b


def _ctx(**kwargs):
    defaults = dict(user_request="fix the header", run_id="run-7")
    defaults.update(kwargs)
    return PluginContext(**defaults)


# ═══════════════ 1) اختبار السطح — لا مسار لـ fm ═══════════════

# الأسماء الممنوعة على سطح PluginContext (بند القبول: "no path to
# raw fm" — نفحص السمات العامة والخاصة معًا).
_FORBIDDEN_SURFACE = re.compile(
    r"fm|file_manager|filemanager|session_store|sessionstore"
    r"|server|provider|pool|write|delete|apply",
    re.IGNORECASE)


class TestAttributeSurface:
    def test_surface_has_no_forbidden_handles(self):
        ctx = _ctx()
        surface = [a for a in dir(ctx) if not a.startswith("__")]
        offenders = [a for a in surface if _FORBIDDEN_SURFACE.search(a)]
        assert offenders == [], f"forbidden surface attrs: {offenders}"

    def test_surface_is_exactly_the_contract(self):
        """السطح العام = العقد الموثق حرفيًا — أي إضافة سمة عامة
        جديدة يجب أن تمر من هنا (قرار واعٍ لا تسريب)."""
        ctx = _ctx()
        public = sorted(a for a in dir(ctx) if not a.startswith("_"))
        assert public == sorted([
            "user_request", "run_id", "metadata",
            "context_paths", "context_content", "context_items",
            "emit",
        ])

    def test_context_is_frozen(self):
        ctx = _ctx()
        with pytest.raises(Exception):
            ctx.user_request = "hijacked"  # type: ignore[misc]
        with pytest.raises(Exception):
            ctx._emit_fn = lambda t, p: None  # type: ignore[misc]

    def test_metadata_is_defensive_copy(self):
        ctx = _ctx(_metadata={"complexity": 5})
        view = ctx.metadata
        view["complexity"] = 999
        view["evil"] = True
        assert ctx.metadata == {"complexity": 5}


# ═══════════════ 2) عروض السياق للقراءة فقط ═══════════════

class TestContextViews:
    def test_paths_and_content_lookup(self):
        ctx = _ctx(_bundle=_bundle(
            ContextItem("mention", "src/app.py", "print('hi')"),
            ContextItem("keyword", "docs/big.bin", None),
        ))
        assert ctx.context_paths() == ["src/app.py", "docs/big.bin"]
        assert ctx.context_content("src/app.py") == "print('hi')"
        # عنصر بلا محتوى (huge-file quirk) والمجهول كلاهما None.
        assert ctx.context_content("docs/big.bin") is None
        assert ctx.context_content("nope.txt") is None

    def test_items_pairs_in_bundle_order(self):
        ctx = _ctx(_bundle=_bundle(
            ContextItem("mention", "a.py", "A"),
            ContextItem("keyword", "b.py", "B"),
        ))
        assert ctx.context_items() == [("a.py", "A"), ("b.py", "B")]

    def test_views_are_copies(self):
        ctx = _ctx(_bundle=_bundle(ContextItem("mention", "a.py", "A")))
        paths = ctx.context_paths()
        paths.append("evil.py")
        assert ctx.context_paths() == ["a.py"]


# ═══════════════ 3) دورة emit الكاملة ═══════════════

class TestEmitRoundTrip:
    def test_emit_reaches_event_bus_as_step_progress(self):
        bus = EventBus()
        received = []
        bus.subscribe(received.append)
        ctx = _ctx(run_id="run-42",
                   _emit_fn=event_bus_emitter(bus, "run-42"))

        class Plugin:
            routing_hints = {}

            def build(self, c, **kwargs):
                c.emit("plugin_progress", {"pct": 50})
                return {"steps": []}

        Plugin().build(ctx)
        (ev,) = received
        assert isinstance(ev, StepProgress)
        assert ev.run_id == "run-42"
        assert ev.frame_type == "plugin_progress"
        assert ev.payload == {"pct": 50}

    def test_emitted_payload_is_copied(self):
        seen = []
        ctx = _ctx(_emit_fn=lambda t, p: seen.append(p))
        original = {"step": 1}
        ctx.emit("x", original)
        original["step"] = 999
        assert seen == [{"step": 1}]
        assert seen[0] is not original

    def test_fixture_context_is_stable(self):
        ctx = fixture_context()
        assert ctx.user_request == FIXTURE_REQUEST
        assert ctx.run_id == "plugin-dry-run"
        assert ctx.context_paths() == []
        ctx.emit("noop", {})  # حقّاقة مهملة — لا انفجار


# ═══════════════ 4) بوابة check.sh ═══════════════

_GATE_PATTERN = (r'\bfm\b|file_manager|FileManager|SessionStore'
                 r'|session_store|import server')


class TestCheckShGate:
    def test_check_sh_has_plugin_capability_gate(self):
        content = (REPO_ROOT / "scripts" / "check.sh").read_text(
            encoding="utf-8")
        assert "plugin capability grep" in content
        assert "chain/plugin_registry.py" in content
        assert "chain/plugin_api.py" in content

    def test_real_modules_pass_the_gate(self):
        proc = subprocess.run(
            ["grep", "-rnE", _GATE_PATTERN,
             "chain/plugin_registry.py", "chain/plugin_api.py"],
            cwd=REPO_ROOT, capture_output=True, text=True)
        assert proc.returncode != 0, (
            f"gate should find nothing, found:\n{proc.stdout}")

    def test_gate_rejects_seeded_violation(self, tmp_path):
        """انتهاك مزروع (استيراد FileManager) يُلتقط بنفس النمط."""
        bad = tmp_path / "evil_plugin_api.py"
        bad.write_text(
            "from actions.file_manager import FileManager\n"
            "fm = FileManager('/tmp')\n", encoding="utf-8")
        proc = subprocess.run(
            ["grep", "-rnE", _GATE_PATTERN, str(bad)],
            capture_output=True, text=True)
        assert proc.returncode == 0
        assert "FileManager" in proc.stdout


# ═══════════════ 5) تكامل السجل (T-100 → T-101) ═══════════════

class TestRegistryIntegration:
    def test_registry_dry_run_hands_plugin_context(self):
        from chain.plugin_registry import StrategyPluginRegistry
        seen = []

        class Spy:
            routing_hints = {}

            def build(self, ctx, **kwargs):
                seen.append(ctx)
                return {"steps": []}

        class EP:
            name = "spy"

            def load(self):
                return Spy

        reg = StrategyPluginRegistry(
            entry_points_fn=lambda *, group: [EP()])
        reg.discover()
        assert reg.get("spy") is Spy
        (ctx,) = seen
        assert isinstance(ctx, PluginContext)
        assert ctx.user_request == FIXTURE_REQUEST


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
