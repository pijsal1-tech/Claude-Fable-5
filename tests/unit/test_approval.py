# -*- coding: utf-8 -*-
"""T-011 (R-104): ApprovalGate unit tests — mode matrix, timeout, audit.

Covers the acceptance criteria:
- all three modes (auto / interactive / deny) incl. timeout→deny
- payload-hash verification on resolve (stale/forged responses rejected)
- audit entries complete for every verdict path
"""
from __future__ import annotations

import threading
import time

import pytest

from core.approval import (
    ApprovalGate,
    ApprovalRequest,
    ProposedAction,
    Verdict,
    compute_actions_hash,
)


def _req(kinds: list[str] | None = None, source: str = "test") -> ApprovalRequest:
    kinds = kinds or ["write"]
    return ApprovalRequest(
        actions=[ProposedAction(kind=k, target=f"file_{i}.py", payload="x")
                 for i, k in enumerate(kinds)],
        source=source,
        run_id="run-1",
    )


# ═══════════════ construction / validation ═══════════════

def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        ApprovalGate(mode="yolo")


def test_empty_request_rejected():
    with pytest.raises(ValueError):
        ApprovalRequest(actions=[])


def test_payload_hash_deterministic():
    a = [ProposedAction(kind="write", target="a.py", payload="hi")]
    b = [ProposedAction(kind="write", target="a.py", payload="hi")]
    assert compute_actions_hash(a) == compute_actions_hash(b)
    c = [ProposedAction(kind="write", target="a.py", payload="DIFFERENT")]
    assert compute_actions_hash(a) != compute_actions_hash(c)


# ═══════════════ deny mode ═══════════════

def test_deny_mode_denies_everything():
    gate = ApprovalGate(mode="deny")
    v = gate.request(_req(["read"]))
    assert isinstance(v, Verdict)
    assert v.approved is False
    assert v.reason == "deny_mode"


# ═══════════════ auto mode ═══════════════

def test_auto_approves_whitelisted_kinds():
    gate = ApprovalGate(mode="auto", auto_whitelist={"read", "format"})
    v = gate.request(_req(["read", "format"]))
    assert v.approved is True
    assert v.reason == "auto_whitelist"


def test_auto_denies_non_whitelisted_without_callback():
    gate = ApprovalGate(mode="auto", auto_whitelist={"read"})
    v = gate.request(_req(["write"]))
    assert v.approved is False
    assert v.reason == "non_whitelisted_kind"


def test_auto_mixed_kinds_one_bad_blocks_all():
    """فعل واحد غير معتمد يمنع الحزمة كلها — لا approve جزئي."""
    gate = ApprovalGate(mode="auto", auto_whitelist={"read"})
    v = gate.request(_req(["read", "delete"]))
    assert v.approved is False


def test_auto_falls_back_to_interactive_with_callback():
    """نوع غير معتمد + قناة interactive موجودة ⇒ يسأل المستخدم."""
    emitted: list[dict] = []
    gate = ApprovalGate(mode="auto", auto_whitelist={"read"},
                        on_request=emitted.append, timeout_seconds=5.0)
    req = _req(["write"])

    def approve_soon():
        deadline = time.time() + 3
        while time.time() < deadline:
            rid = gate.pending_request_id()
            if rid:
                assert gate.resolve(rid, True, payload_hash=req.payload_hash)
                return
            time.sleep(0.01)

    t = threading.Thread(target=approve_soon)
    t.start()
    v = gate.request(req)
    t.join()
    assert v.approved is True
    assert v.reason == "user_approved"
    assert len(emitted) == 1
    assert emitted[0]["request_id"] == req.request_id


# ═══════════════ interactive mode ═══════════════

def test_interactive_user_approves():
    gate = ApprovalGate(mode="interactive", timeout_seconds=5.0)
    req = _req(["write"])

    def respond():
        while gate.pending_request_id() != req.request_id:
            time.sleep(0.01)
        gate.resolve(req.request_id, True, payload_hash=req.payload_hash)

    t = threading.Thread(target=respond)
    t.start()
    v = gate.request(req)
    t.join()
    assert v.approved is True
    assert v.reason == "user_approved"


def test_interactive_user_denies():
    gate = ApprovalGate(mode="interactive", timeout_seconds=5.0)
    req = _req(["write"])

    def respond():
        while gate.pending_request_id() != req.request_id:
            time.sleep(0.01)
        gate.resolve(req.request_id, False, payload_hash=req.payload_hash)

    t = threading.Thread(target=respond)
    t.start()
    v = gate.request(req)
    t.join()
    assert v.approved is False
    assert v.reason == "user_denied"


def test_interactive_timeout_denies():
    gate = ApprovalGate(mode="interactive", timeout_seconds=0.1)
    v = gate.request(_req(["write"]))
    assert v.approved is False
    assert v.reason == "timeout"


def test_interactive_emits_request_payload():
    emitted: list[dict] = []
    gate = ApprovalGate(mode="interactive", on_request=emitted.append,
                        timeout_seconds=0.1)
    req = _req(["write"])
    gate.request(req)
    assert len(emitted) == 1
    frame = emitted[0]
    assert frame["request_id"] == req.request_id
    assert frame["payload_hash"] == req.payload_hash
    assert frame["actions"][0]["kind"] == "write"


def test_interactive_callback_exception_does_not_hang_gate():
    def boom(_frame: dict) -> None:
        raise RuntimeError("WS down")

    gate = ApprovalGate(mode="interactive", on_request=boom,
                        timeout_seconds=0.1)
    v = gate.request(_req(["write"]))
    assert v.approved is False
    assert v.reason == "timeout"


# ═══════════════ hash verification (anti stale/forged) ═══════════════

def test_resolve_rejects_wrong_hash():
    gate = ApprovalGate(mode="interactive", timeout_seconds=0.3)
    req = _req(["write"])
    result: list[Verdict] = []

    def forged_then_nothing():
        while gate.pending_request_id() != req.request_id:
            time.sleep(0.01)
        # hash خاطئ ⇒ يجب أن يُرفض ولا يفك الانتظار
        assert gate.resolve(req.request_id, True, payload_hash="deadbeef") is False

    t = threading.Thread(target=forged_then_nothing)
    t.start()
    v = gate.request(req)
    t.join()
    assert v.approved is False
    assert v.reason == "timeout"  # الرد المزوّر لم يُحتسب


def test_resolve_rejects_wrong_request_id():
    gate = ApprovalGate(mode="interactive", timeout_seconds=0.3)
    req = _req(["write"])

    def wrong_id():
        while gate.pending_request_id() != req.request_id:
            time.sleep(0.01)
        assert gate.resolve("someone-else", True,
                            payload_hash=req.payload_hash) is False

    t = threading.Thread(target=wrong_id)
    t.start()
    v = gate.request(req)
    t.join()
    assert v.approved is False


def test_resolve_with_no_pending_is_noop():
    gate = ApprovalGate(mode="interactive")
    assert gate.resolve("ghost", True, payload_hash="x") is False


# ═══════════════ audit log ═══════════════

def test_audit_records_every_verdict_path():
    fake_now = 1_000_000.0
    gate = ApprovalGate(mode="deny", clock=lambda: fake_now)
    req1 = _req(["write"], source="chain")
    gate.request(req1)

    entries = gate.audit_entries()
    assert len(entries) == 1
    e = entries[0]
    # اكتمال الحقول — معيار القبول
    assert e["request_id"] == req1.request_id
    assert e["source"] == "chain"
    assert e["run_id"] == "run-1"
    assert e["payload_hash"] == req1.payload_hash
    assert e["action_kinds"] == ["write"]
    assert e["action_count"] == 1
    assert e["mode"] == "deny"
    assert e["approved"] is False
    assert e["reason"] == "deny_mode"
    assert e["decided_at"] == fake_now


def test_audit_accumulates_in_order():
    gate = ApprovalGate(mode="auto", auto_whitelist={"read"})
    r1, r2 = _req(["read"]), _req(["write"])
    gate.request(r1)
    gate.request(r2)
    entries = gate.audit_entries()
    assert [e["request_id"] for e in entries] == [r1.request_id, r2.request_id]
    assert entries[0]["approved"] is True
    assert entries[1]["approved"] is False


def test_audit_timeout_entry():
    gate = ApprovalGate(mode="interactive", timeout_seconds=0.05)
    req = _req(["write"])
    gate.request(req)
    e = gate.audit_entries()[-1]
    assert e["approved"] is False and e["reason"] == "timeout"
