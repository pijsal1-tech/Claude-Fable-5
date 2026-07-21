# -*- coding: utf-8 -*-
"""T-114 (R-805): Memory Panel — WS frames memory_list/memory_edit/
memory_delete + الحذف يشرَّف فورًا في مصدر السياق.

بنود القبول:
- اللوحة تعرض المدخلات بـ provenance كاملة + شارة staleness.
- التعديل يثبت في المخزن ويُخدم في الحزمة التالية.
- المدخلة المحذوفة لا تظهر أبدًا في الاسترجاع.
- الإطارات إضافية — لا مساس بأي إطار قائم (grep-guarded).

النمط: E2E عبر ``server._handle_ws_message(None, sctx, {...})`` مع
``SessionContext(send=sent.append)`` (نمط test_rollback) وعزل المخزن
بـ ``monkeypatch.setattr(server, "project_memory", ...)`` (نمط
test_ws_run_control مع execution_registry).
"""
from __future__ import annotations

import pathlib

import pytest

import server
from core.app_context import ProjectHandle
from core.project_memory import (
    ProjectMemoryStore, index_fingerprint, new_entry,
)
from core.session_context import SessionContext
from context.engine import ContextRequest, ProjectScan
from context.sources.project_memory import ProjectMemorySource
from sessions.store import project_fingerprint


# ═══════════════════════ العدة ═══════════════════════

@pytest.fixture()
def project(tmp_path):
    """مشروع حقيقي على القرص + مخزن معزول مركَّب في server."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
    store = ProjectMemoryStore(str(tmp_path / "projects"), fsync="never")
    return root, store


@pytest.fixture()
def wired(project, monkeypatch):
    """يركّب المخزن كـ service global ويعيد (root, store, project_id)."""
    root, store = project
    monkeypatch.setattr(server, "project_memory", store)
    return root, store, project_fingerprint(str(root))


def _sctx(root, index=None):
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)
    sctx.project = ProjectHandle(root=str(root), index=index)
    return sctx, sent


def _frames(sent, ftype):
    return [f for f in sent if f.get("type") == ftype]


# ═══════════════════════ memory_list ═══════════════════════

def test_list_empty_project(wired):
    root, _store, pid = wired
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {"type": "memory_list"})
    frames = _frames(sent, "memory_list_result")
    assert len(frames) == 1
    assert frames[0]["entries"] == []
    assert frames[0]["project_id"] == pid
    assert "error" not in frames[0]


def test_list_shows_provenance_fields(wired):
    root, store, pid = wired
    e = store.remember(pid, "fact", "المشروع يستخدم flask",
                       source="agent_tool", run_id="run-9")
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {"type": "memory_list"})
    entry = _frames(sent, "memory_list_result")[0]["entries"][0]
    assert entry["entry_id"] == e.entry_id
    assert entry["kind"] == "fact"
    assert entry["text"] == "المشروع يستخدم flask"
    assert entry["source"] == "agent_tool"
    assert entry["run_id"] == "run-9"
    assert entry["created_at"] == e.created_at
    assert entry["stale"] is False


def test_list_stale_badge_from_live_index(wired):
    """بصمة قديمة + فهرس حي متغيّر ⇒ stale=True (شارة اللوحة)."""
    root, store, pid = wired
    old_scan = ProjectScan(root)
    store.remember(pid, "fact", "بنية قديمة", index=old_scan)
    (root / "new_file.py").write_text("x = 1\n", encoding="utf-8")
    live = ProjectScan(root)
    sctx, sent = _sctx(root, index=live)
    server._handle_ws_message(None, sctx, {"type": "memory_list"})
    entry = _frames(sent, "memory_list_result")[0]["entries"][0]
    assert entry["stale"] is True


def test_list_no_index_means_no_judgement(wired):
    root, store, pid = wired
    store.append(pid, new_entry("fact", "بلا فهرس",
                                index_hash="deadbeefdeadbeef"))
    sctx, sent = _sctx(root, index=None)
    server._handle_ws_message(None, sctx, {"type": "memory_list"})
    entry = _frames(sent, "memory_list_result")[0]["entries"][0]
    assert entry["stale"] is False


def test_list_without_store_is_tolerant(wired, monkeypatch):
    root, _store, _pid = wired
    monkeypatch.setattr(server, "project_memory", None)
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {"type": "memory_list"})
    frame = _frames(sent, "memory_list_result")[0]
    assert frame["error"] == "memory_unavailable"
    assert frame["entries"] == []


def test_list_without_project_is_tolerant(wired):
    root, _store, _pid = wired
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)   # sctx.project = None
    server._handle_ws_message(None, sctx, {"type": "memory_list"})
    frame = _frames(sent, "memory_list_result")[0]
    assert frame["error"] == "memory_unavailable"


# ═══════════════════════ memory_edit ═══════════════════════

def test_edit_round_trips_to_store(wired):
    """بند القبول: التعديل يثبت ويُخدم في الحزمة/القائمة التالية."""
    root, store, pid = wired
    e = store.remember(pid, "fact", "نص قديم")
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {
        "type": "memory_edit", "entry_id": e.entry_id,
        "text": "نص محرَّر", "kind": "convention"})
    frame = _frames(sent, "memory_edit_result")[0]
    assert frame["acknowledged"] is True
    assert frame["entry"]["text"] == "نص محرَّر"
    assert frame["entry"]["kind"] == "convention"
    assert frame["entry"]["source"] == "user"       # provenance التعديل
    assert frame["entry"]["entry_id"] == e.entry_id  # الهوية تبقى
    # ثبات في المخزن — قائمة تالية تعكسه
    persisted = store.entries(pid)[0]
    assert persisted.text == "نص محرَّر"
    assert persisted.source == "user"


def test_edit_restamps_index_hash_clears_staleness(wired):
    """تعديل المستخدم إعادة تأكيد ⇒ الفهرس الحي يمسح شارة staleness."""
    root, store, pid = wired
    old_scan = ProjectScan(root)
    e = store.remember(pid, "fact", "حقيقة", index=old_scan)
    (root / "drift.py").write_text("y = 2\n", encoding="utf-8")
    live = ProjectScan(root)
    sctx, sent = _sctx(root, index=live)
    server._handle_ws_message(None, sctx, {"type": "memory_list"})
    assert _frames(sent, "memory_list_result")[0]["entries"][0]["stale"] is True
    server._handle_ws_message(None, sctx, {
        "type": "memory_edit", "entry_id": e.entry_id, "text": "حقيقة مؤكدة"})
    frame = _frames(sent, "memory_edit_result")[0]
    assert frame["entry"]["stale"] is False
    assert store.entries(pid)[0].index_hash == index_fingerprint(live)


def test_edit_unknown_entry(wired):
    root, _store, _pid = wired
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {
        "type": "memory_edit", "entry_id": "nope", "text": "x"})
    frame = _frames(sent, "memory_edit_result")[0]
    assert frame["acknowledged"] is False
    assert frame["error"] == "not_found"


def test_edit_missing_entry_id(wired):
    root, _store, _pid = wired
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {"type": "memory_edit"})
    frame = _frames(sent, "memory_edit_result")[0]
    assert frame["error"] == "missing_entry_id"


def test_edit_bad_kind_is_loud_but_tolerant(wired):
    """نوع مجهول = ValueError في المخزن ⇒ حقل error، لا استثناء يفلت."""
    root, store, pid = wired
    e = store.remember(pid, "fact", "نص")
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {
        "type": "memory_edit", "entry_id": e.entry_id, "kind": "bogus"})
    frame = _frames(sent, "memory_edit_result")[0]
    assert frame["acknowledged"] is False
    assert frame.get("error")
    assert store.entries(pid)[0].kind == "fact"   # لم يمس


# ═══════════════════════ memory_delete ═══════════════════════

def test_delete_removes_from_store(wired):
    root, store, pid = wired
    e = store.remember(pid, "decision", "قرار ملغي")
    keep = store.remember(pid, "fact", "تبقى")
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {
        "type": "memory_delete", "entry_id": e.entry_id})
    frame = _frames(sent, "memory_delete_result")[0]
    assert frame["acknowledged"] is True
    assert frame["entry_id"] == e.entry_id
    remaining = store.entries(pid)
    assert [x.entry_id for x in remaining] == [keep.entry_id]


def test_delete_unknown_entry(wired):
    root, _store, _pid = wired
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {
        "type": "memory_delete", "entry_id": "ghost"})
    frame = _frames(sent, "memory_delete_result")[0]
    assert frame["acknowledged"] is False
    assert frame["error"] == "not_found"


def test_deleted_entry_never_appears_in_retrieval(wired):
    """بند القبول: مصدر ContextEngine يشرّف الحذف فورًا — المصدر يقرأ
    المخزن عند كل collect فلا كاش يُبقي المحذوف حيًّا."""
    root, store, pid = wired
    e = store.remember(pid, "fact", "المشروع يستخدم redis للطوابير")
    source = ProjectMemorySource(store, pid)
    request = ContextRequest(message="redis الطوابير",
                             project_root=pathlib.Path(root))
    scan = ProjectScan(root)
    before = source.collect(request, scan)
    assert any(e.entry_id in item.path for item in before)
    # الحذف عبر إطار WS نفسه (المسار الكامل E2E)
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {
        "type": "memory_delete", "entry_id": e.entry_id})
    assert _frames(sent, "memory_delete_result")[0]["acknowledged"] is True
    after = source.collect(request, scan)
    assert all(e.entry_id not in item.path for item in after)
    assert after == []


# ═══════════════════════ إضافية الإطارات ═══════════════════════

def test_frames_are_additive_no_existing_frame_changes():
    """grep-guard: أنواع الإطارات الجديدة لا تلمس القائمة القديمة —
    ولا تعديل على إطارَي T-016 (بايت-بايت عبر الدوال نفسها)."""
    frame = server._list_runs_frame()
    assert frame == {"type": "runs_list", "runs": []}
    cancel = server._cancel_run_frame("")
    assert cancel == {"type": "cancel_run_result",
                      "acknowledged": False,
                      "error": "missing_run_id"}
    # الأنواع الجديدة أسماء جديدة كليًا — لا تظليل لأنواع قائمة
    new_types = {"memory_list_result", "memory_edit_result",
                 "memory_delete_result"}
    existing = {"runs_list", "cancel_run_result", "rollback_result",
                "chain_approval_request", "done", "error"}
    assert not (new_types & existing)


def test_unknown_message_type_still_ignored(wired):
    """رسالة مجهولة تمر بصمت — إضافة الـ elifs لم تغيّر السلوك."""
    root, _store, _pid = wired
    sctx, sent = _sctx(root)
    server._handle_ws_message(None, sctx, {"type": "definitely_unknown"})
    assert sent == []
