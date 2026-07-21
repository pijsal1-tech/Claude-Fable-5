# -*- coding: utf-8 -*-
"""T-112 (R-805): ProjectMemoryStore + remember_fact Tool.

المصفوفة (بنود القبول الثلاثة نصًّا):
- durability: المدخلات تنجو من إعادة التحميل (مخزن جديد على نفس الدليل)
  مفتاحة بـ project_id؛ عزل بين المشاريع؛ ترتيب الإلحاق محفوظ.
- tool round-trip: remember_fact من تشغيلة fixture يُنزل مدخلة سليمة
  البنية بكل حقول الـ provenance (source/run_id/created_at).
- hash-link: index_hash مسجّل مقابل حالة ProjectIndex الحالية —
  حتمي، وحساس لتغيّر بنية الشجرة.
+ الصلابة: schema صارم (نوع مجهول/نص فارغ = ValueError)، تعافي الذيل
  الممزّق (نفس عقد SessionStore)، سطر تالف في الوسط = CorruptMemoryError.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from core.project_memory import (
    ENTRY_KINDS,
    FORMAT_VERSION,
    CorruptMemoryError,
    MemoryEntry,
    ProjectMemoryStore,
    index_fingerprint,
    new_entry,
)


PID = "abc123def456"          # بصمة مشروع صناعية (شكل R-303: 12 hex)


def _store(tmp_path: pathlib.Path) -> ProjectMemoryStore:
    return ProjectMemoryStore(tmp_path / "projects")


# ═══════════════════ Schema + provenance ═══════════════════

class TestEntrySchema:

    def test_new_entry_stamps_id_and_timestamp(self):
        e = new_entry("fact", "الخادم Flask")
        assert len(e.entry_id) == 32          # uuid4 hex
        assert "T" in e.created_at            # ISO-8601
        assert e.created_at.endswith("+00:00")  # UTC صريح

    def test_provenance_fields_carried(self):
        e = new_entry("decision", "نعتمد JSONL", source="agent_tool",
                      run_id="run-42", index_hash="ff" * 8)
        d = e.to_dict()
        assert d["source"] == "agent_tool"
        assert d["run_id"] == "run-42"
        assert d["index_hash"] == "ff" * 8
        assert d["format"] == FORMAT_VERSION

    @pytest.mark.parametrize("kind", ENTRY_KINDS)
    def test_all_documented_kinds_accepted(self, kind):
        assert new_entry(kind, "x").kind == kind

    def test_unknown_kind_loud(self):
        with pytest.raises(ValueError):
            new_entry("gossip", "كلام")

    def test_empty_text_loud(self):
        with pytest.raises(ValueError):
            new_entry("fact", "   ")

    def test_roundtrip_dict(self):
        e = new_entry("convention", "أسماء snake_case", run_id="r1")
        assert MemoryEntry.from_dict(e.to_dict()) == e


# ═══════════════════ Durability (بند القبول 1) ═══════════════════

class TestDurability:

    def test_entries_survive_reload_keyed_by_project_id(self, tmp_path):
        s1 = _store(tmp_path)
        s1.append(PID, new_entry("fact", "حقيقة 1"))
        s1.append(PID, new_entry("convention", "عرف 2"))
        # مخزن جديد كليًا على نفس الدليل = «جلسة ثانية»
        s2 = _store(tmp_path)
        got = s2.entries(PID)
        assert [e.text for e in got] == ["حقيقة 1", "عرف 2"]
        assert [e.kind for e in got] == ["fact", "convention"]

    def test_projects_isolated(self, tmp_path):
        s = _store(tmp_path)
        s.append(PID, new_entry("fact", "لمشروع أ"))
        s.append("fedcba987654", new_entry("fact", "لمشروع ب"))
        assert [e.text for e in s.entries(PID)] == ["لمشروع أ"]
        assert [e.text for e in s.entries("fedcba987654")] == ["لمشروع ب"]

    def test_missing_project_reads_empty(self, tmp_path):
        assert _store(tmp_path).entries(PID) == []

    def test_append_only_one_json_line_per_entry(self, tmp_path):
        s = _store(tmp_path)
        s.append(PID, new_entry("fact", "سطر"))
        raw = s.memory_path(PID).read_text(encoding="utf-8")
        assert raw.endswith("\n") and raw.count("\n") == 1
        json.loads(raw)                      # سطر JSON صالح

    def test_bad_project_id_loud(self, tmp_path):
        s = _store(tmp_path)
        for bad in ("", "../etc", "a/b", ".hidden"):
            with pytest.raises(ValueError):
                s.memory_path(bad)


# ═══════════════════ Crash recovery (عقد SessionStore) ═══════════════════

class TestCrashRecovery:

    def test_torn_tail_skipped_on_read(self, tmp_path):
        s = _store(tmp_path)
        s.append(PID, new_entry("fact", "سليمة"))
        with open(s.memory_path(PID), "a", encoding="utf-8") as f:
            f.write('{"kind": "fact", "text": "ممز')   # صدمة منتصف كتابة
        assert [e.text for e in _store(tmp_path).entries(PID)] == ["سليمة"]

    def test_torn_tail_truncated_before_next_write(self, tmp_path):
        s = _store(tmp_path)
        s.append(PID, new_entry("fact", "أولى"))
        with open(s.memory_path(PID), "a", encoding="utf-8") as f:
            f.write('{"مقطوع')
        s2 = _store(tmp_path)
        s2.append(PID, new_entry("fact", "ثانية"))
        got = s2.entries(PID)
        assert [e.text for e in got] == ["أولى", "ثانية"]
        # الملف نظيف: كل الأسطر JSON صالح
        for line in s2.memory_path(PID).read_text(
                encoding="utf-8").splitlines():
            json.loads(line)

    def test_corrupt_middle_line_loud(self, tmp_path):
        s = _store(tmp_path)
        s.append(PID, new_entry("fact", "أولى"))
        with open(s.memory_path(PID), "a", encoding="utf-8") as f:
            f.write("ليس json إطلاقًا\n")
            f.write(json.dumps(new_entry("fact", "أخيرة").to_dict(),
                               ensure_ascii=False) + "\n")
        with pytest.raises(CorruptMemoryError):
            _store(tmp_path).entries(PID)


# ═══════════════════ Hash-link (بند القبول 3) ═══════════════════

class _FakeIndex:
    """واجهة ProjectIndex الدنيا: files + rel — duck-typed كما المخزن."""

    def __init__(self, root: pathlib.Path, rels: list[str]):
        self.root = root
        self.files = [root / r for r in rels]

    def rel(self, p: pathlib.Path) -> str:
        return str(p.relative_to(self.root)).replace("\\", "/")


class TestHashLink:

    def test_fingerprint_deterministic(self, tmp_path):
        idx = _FakeIndex(tmp_path, ["a.py", "b/c.py"])
        assert index_fingerprint(idx) == index_fingerprint(idx)
        assert len(index_fingerprint(idx)) == 16

    def test_fingerprint_changes_on_structure_drift(self, tmp_path):
        before = index_fingerprint(_FakeIndex(tmp_path, ["a.py"]))
        after = index_fingerprint(_FakeIndex(tmp_path, ["a.py", "new.py"]))
        assert before != after

    def test_fingerprint_order_insensitive(self, tmp_path):
        f1 = index_fingerprint(_FakeIndex(tmp_path, ["a.py", "b.py"]))
        f2 = index_fingerprint(_FakeIndex(tmp_path, ["b.py", "a.py"]))
        assert f1 == f2                       # الفرز داخلي — البنية لا الترتيب

    def test_no_index_empty_link(self):
        assert index_fingerprint(None) == ""
        assert index_fingerprint(object()) == ""

    def test_real_project_index_compatible(self, tmp_path):
        """الرابط يعمل مع ProjectIndex الحقيقي (T-049) لا الـ fake فقط."""
        from context.index import ProjectIndex
        (tmp_path / "app.py").write_text("x = 1", encoding="utf-8")
        idx = ProjectIndex(tmp_path)
        fp = index_fingerprint(idx)
        assert len(fp) == 16
        # إضافة ملف + إعادة بناء ⇒ بصمة مختلفة
        (tmp_path / "extra.py").write_text("y = 2", encoding="utf-8")
        idx.refresh_if_stale(force=True)
        assert index_fingerprint(idx) != fp

    def test_remember_records_hash_link(self, tmp_path):
        s = _store(tmp_path)
        idx = _FakeIndex(tmp_path, ["a.py"])
        entry = s.remember(PID, "fact", "مرتبطة", index=idx)
        assert entry.index_hash == index_fingerprint(idx)
        # ومحفوظة على القرص أيضًا
        assert _store(tmp_path).entries(PID)[0].index_hash \
            == index_fingerprint(idx)


# ═══════════════════ remember_fact tool (بند القبول 2) ═══════════════════

from types import SimpleNamespace

from chain.agent_tools import (
    ALL_TOOLS,
    SAFE_TOOLS,
    AgentTools,
    parse_tool_calls,
)
from core.execution import ExecutionRegistry
from sessions.store import project_fingerprint


class TestRememberFactTool:

    def _tools(self, tmp_path, with_ctx_index=False):
        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        (proj / "app.py").write_text("x = 1", encoding="utf-8")
        store = ProjectMemoryStore(tmp_path / "projects")
        ctx = None
        if with_ctx_index:
            from context.index import ProjectIndex
            ctx = SimpleNamespace(project=SimpleNamespace(
                root=str(proj), fm=None, cmd_runner=None,
                index=ProjectIndex(proj)))
        tools = AgentTools(project_root=str(proj), ctx=ctx,
                           memory_store=store)
        return tools, store, proj

    def test_registered_as_safe_tool(self):
        """آمنة (لا shell ولا كتابة workspace) — تنفيذ فوري بلا بوابة."""
        assert "remember_fact" in SAFE_TOOLS
        assert "remember_fact" in ALL_TOOLS

    def test_roundtrip_from_fixture_run_with_provenance(self, tmp_path):
        """بند القبول نصًّا: remember_fact من تشغيلة fixture يُنزل
        مدخلة سليمة البنية بكل حقول الـ provenance."""
        tools, store, proj = self._tools(tmp_path)
        registry = ExecutionRegistry()
        ticket = registry.register("agent")
        tools.run_ticket = ticket
        # نفس مسار الإنتاج: رد AI → parse_tool_calls → execute
        ai_response = ("سأحفظ هذا.\n"
                       "```TOOL: remember_fact\n"
                       "kind: convention\n"
                       "text: الاختبارات تعيش في tests/unit\n"
                       "```")
        calls = parse_tool_calls(ai_response)
        assert len(calls) == 1 and not calls[0].needs_approval
        result = tools.execute(calls[0])
        assert result.startswith("✅")
        pid = project_fingerprint(str(proj))
        entries = store.entries(pid)
        assert len(entries) == 1
        e = entries[0]
        assert e.kind == "convention"
        assert e.text == "الاختبارات تعيش في tests/unit"
        assert e.source == "agent_tool"            # provenance: من
        assert e.run_id == ticket.run_id           # provenance: أي تشغيلة
        assert e.created_at                        # provenance: متى
        ticket.finish("completed")

    def test_hash_link_recorded_against_live_index(self, tmp_path):
        """بند القبول 3 عبر الأداة: index_hash من ctx.project.index الحي."""
        tools, store, proj = self._tools(tmp_path, with_ctx_index=True)
        from chain.agent_tools import ToolCall
        result = tools.execute(ToolCall(
            tool="remember_fact",
            args={"kind": "fact", "text": "الجذر يحوي app.py"}))
        assert result.startswith("✅")
        pid = project_fingerprint(str(proj))
        e = store.entries(pid)[0]
        assert e.index_hash == index_fingerprint(
            tools._ctx.project.index)
        assert len(e.index_hash) == 16

    def test_no_store_clear_refusal(self, tmp_path):
        """بلا مخزن مهيأ = اعتذار واضح (لا صمت ولا استثناء)."""
        proj = tmp_path / "p"
        proj.mkdir()
        tools = AgentTools(project_root=str(proj))
        from chain.agent_tools import ToolCall
        result = tools.execute(ToolCall(
            tool="remember_fact", args={"kind": "fact", "text": "x"}))
        assert result.startswith("❌")

    def test_empty_text_refused(self, tmp_path):
        tools, store, proj = self._tools(tmp_path)
        from chain.agent_tools import ToolCall
        result = tools.execute(ToolCall(
            tool="remember_fact", args={"kind": "fact", "text": "  "}))
        assert result.startswith("❌")
        assert store.entries(project_fingerprint(str(proj))) == []

    def test_bad_kind_refused_not_raised(self, tmp_path):
        """نوع مجهول يعود رسالة ❌ للـ AI ليصحح — لا استثناء يقتل الحلقة."""
        tools, store, proj = self._tools(tmp_path)
        from chain.agent_tools import ToolCall
        result = tools.execute(ToolCall(
            tool="remember_fact", args={"kind": "gossip", "text": "كلام"}))
        assert result.startswith("❌")
        assert store.entries(project_fingerprint(str(proj))) == []

    def test_outside_run_empty_run_id(self, tmp_path):
        """خارج تشغيلة (لا ticket): المدخلة تُحفظ وrun_id فارغ صراحة."""
        tools, store, proj = self._tools(tmp_path)
        from chain.agent_tools import ToolCall
        result = tools.execute(ToolCall(
            tool="remember_fact",
            args={"kind": "decision", "text": "قرار خارج run"}))
        assert result.startswith("✅")
        e = store.entries(project_fingerprint(str(proj)))[0]
        assert e.run_id == ""

    def test_second_session_reads_first_session_memory(self, tmp_path):
        """جوهر R-805: أدوات جلسة ثانية (مخزن جديد) ترى ذاكرة الأولى."""
        tools1, _store1, proj = self._tools(tmp_path)
        from chain.agent_tools import ToolCall
        tools1.execute(ToolCall(
            tool="remember_fact",
            args={"kind": "fact", "text": "من الجلسة الأولى"}))
        # «جلسة ثانية»: مخزن + أدوات جديدة كليًا على نفس الجذر
        store2 = ProjectMemoryStore(tmp_path / "projects")
        got = store2.entries(project_fingerprint(str(proj)))
        assert [e.text for e in got] == ["من الجلسة الأولى"]
