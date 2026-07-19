# -*- coding: utf-8 -*-
"""T-031 (R-303): Session ↔ Project Binding — unit tests.

Covers:
- project_fingerprint: stability, resolve-normalization, empty = unbound
- check_project_binding: full matrix (unbound / match / mismatch × policy)
  + unknown policy → loud ValueError
- SessionMeta stamping: create / set_project_path / rebuild_meta
- Legacy compat: meta JSON without ``project_id`` reads as unbound
"""
import json

import pytest

from sessions.store import (
    BINDING_POLICIES,
    BindingCheck,
    SessionMeta,
    SessionStore,
    check_project_binding,
    project_fingerprint,
)


# ── project_fingerprint ────────────────────────────────────────────

def test_fingerprint_stable_and_12_hex(tmp_path):
    fp1 = project_fingerprint(str(tmp_path))
    fp2 = project_fingerprint(str(tmp_path))
    assert fp1 == fp2
    assert len(fp1) == 12
    assert all(c in "0123456789abcdef" for c in fp1)


def test_fingerprint_resolve_normalization(tmp_path):
    """مسارات مختلفة نصيًا لنفس المجلد → نفس البصمة (resolve)."""
    sub = tmp_path / "proj"
    sub.mkdir()
    direct = str(sub)
    dotted = str(tmp_path / "proj" / "." )
    updown = str(tmp_path / "other" / ".." / "proj")
    assert project_fingerprint(direct) == project_fingerprint(dotted)
    assert project_fingerprint(direct) == project_fingerprint(updown)


def test_fingerprint_empty_path_is_unbound():
    assert project_fingerprint("") == ""


def test_fingerprint_differs_across_paths(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    a.mkdir(); b.mkdir()
    assert project_fingerprint(str(a)) != project_fingerprint(str(b))


# ── check_project_binding matrix ───────────────────────────────────

@pytest.mark.parametrize("policy", BINDING_POLICIES)
def test_unbound_session_always_silent(policy, tmp_path):
    chk = check_project_binding("", str(tmp_path), policy)
    assert chk == BindingCheck(bound=False, match=True,
                               policy=policy, action="none")


@pytest.mark.parametrize("policy", BINDING_POLICIES)
def test_matching_project_always_silent(policy, tmp_path):
    fp = project_fingerprint(str(tmp_path))
    chk = check_project_binding(fp, str(tmp_path), policy)
    assert chk.bound is True and chk.match is True
    assert chk.action == "none"


@pytest.mark.parametrize("policy", BINDING_POLICIES)
def test_mismatch_action_equals_policy(policy, tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    a.mkdir(); b.mkdir()
    chk = check_project_binding(project_fingerprint(str(a)), str(b), policy)
    assert chk.bound is True and chk.match is False
    assert chk.action == policy


def test_unknown_policy_raises_loudly(tmp_path):
    with pytest.raises(ValueError):
        check_project_binding("", str(tmp_path), "banana")
    with pytest.raises(ValueError):
        check_project_binding("deadbeef0000", str(tmp_path), "")


# ── SessionMeta stamping ───────────────────────────────────────────

def test_create_stamps_project_id(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    proj = tmp_path / "proj"; proj.mkdir()
    meta = store.create(str(proj))
    assert meta.project_id == project_fingerprint(str(proj))


def test_create_empty_path_is_unbound(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    meta = store.create("")
    assert meta.project_id == ""


def test_set_project_path_restamps(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    a = tmp_path / "a"; b = tmp_path / "b"
    a.mkdir(); b.mkdir()
    meta = store.create(str(a))
    store.set_project_path(meta.id, str(b))
    reread = store.read_meta(meta.id)
    assert reread.project_id == project_fingerprint(str(b))
    assert reread.project_path == str(b)


def test_rebuild_meta_preserves_project_id(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    proj = tmp_path / "proj"; proj.mkdir()
    meta = store.create(str(proj))
    store.append_message(meta.id, "user", "مرحبا")
    rebuilt = store.rebuild_meta(meta.id)
    assert rebuilt.project_id == project_fingerprint(str(proj))


def test_meta_roundtrip_json_includes_project_id(tmp_path):
    proj = tmp_path / "proj"; proj.mkdir()
    meta = SessionMeta(id="abc12345", project_path=str(proj),
                       project_id=project_fingerprint(str(proj)),
                       created_at="t", updated_at="t")
    back = SessionMeta.from_json(json.loads(json.dumps(meta.to_json())))
    assert back.project_id == meta.project_id


def test_legacy_meta_without_project_id_reads_unbound():
    """Sidecar قديم (قبل T-031) بلا project_id → جلسة غير مرتبطة."""
    legacy = {"format": 1, "id": "old00001", "title": "",
              "project_path": "/some/old/path",
              "created_at": "t", "updated_at": "t", "message_count": 0}
    meta = SessionMeta.from_json(legacy)
    assert meta.project_id == ""
    # وغير المرتبطة تمر بصمت تحت أي سياسة
    chk = check_project_binding(meta.project_id, "/new/path", "block")
    assert chk.action == "none"
