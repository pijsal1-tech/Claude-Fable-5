# -*- coding: utf-8 -*-
"""TSK-615 (ASF-05/NF-27): طلبات موافقة متزامنة — خريطة مفتاحية بدل الخانة المفردة.

بند القبول: طلبان متداخلان → كلاهما قابل للحل بلا موت بمهلة؛
fail-closed يبقى (مهلة لكل طلب).

NF-27 (المكتشَف في أدلة S71): الخانة المفردة + Event المشترك جعلا اعتماد
طلبٍ يعتمد الآخر زورًا (fail-OPEN) — الاختبارات هنا تثبّت العزل نهائيًا.
"""
import threading
import time

from core.approval import ApprovalGate, ApprovalRequest, ProposedAction


def _req(kind: str, target: str, source: str) -> ApprovalRequest:
    return ApprovalRequest(
        actions=[ProposedAction(kind=kind, target=target)], source=source)


def _overlap(gate, r1, r2):
    """يشغّل طلبين متداخلين على خيطين وينتظر تعليقهما معًا.

    يرجع (verdicts, t1, t2) — verdicts يمتلئ عند خروج كل خيط.
    """
    verdicts = {}
    t1 = threading.Thread(
        target=lambda: verdicts.setdefault("r1", gate.request(r1)), daemon=True)
    t2 = threading.Thread(
        target=lambda: verdicts.setdefault("r2", gate.request(r2)), daemon=True)
    t1.start()
    _wait_pending(gate, r1.request_id)
    t2.start()
    _wait_pending(gate, r2.request_id)
    return verdicts, t1, t2


def _wait_pending(gate, request_id, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if request_id in gate.pending_request_ids():
            return
        time.sleep(0.005)
    raise AssertionError(f"الطلب {request_id} لم يُسجَّل معلّقًا خلال {timeout}s")


class TestConcurrentResolution:
    """بند القبول الحرفي: طلبان متداخلان يُحلان مستقلين."""

    def test_both_overlapping_requests_resolvable_independently(self):
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=5.0)
        r1 = _req("write", "a.txt", "chain")
        r2 = _req("command", "ls", "agent")
        verdicts, t1, t2 = _overlap(gate, r1, r2)

        assert len(gate.pending_request_ids()) == 2

        # اعتماد r2 ثم رفض r1 — كلاهما يطابق مدخله المستقل
        assert gate.resolve(r2.request_id, True, payload_hash=r2.payload_hash)
        assert gate.resolve(r1.request_id, False, payload_hash=r1.payload_hash)
        t1.join(timeout=3.0)
        t2.join(timeout=3.0)
        assert not t1.is_alive() and not t2.is_alive()

        assert verdicts["r2"].approved is True
        assert verdicts["r2"].reason == "user_approved"
        assert verdicts["r1"].approved is False
        assert verdicts["r1"].reason == "user_denied"

    def test_no_phantom_approval_nf27(self):
        """NF-27: اعتماد r2 يجب ألا يعتمد r1 (كان fail-OPEN بالخانة المفردة)."""
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=1.5)
        r1 = _req("write", "a.txt", "chain")
        r2 = _req("command", "ls", "agent")
        verdicts, t1, t2 = _overlap(gate, r1, r2)

        assert gate.resolve(r2.request_id, True, payload_hash=r2.payload_hash)
        # r1 لم يُحل — يجب أن يموت بمهلته الخاصة (deny) لا أن يرث موافقة r2
        t1.join(timeout=4.0)
        t2.join(timeout=4.0)
        assert verdicts["r2"].approved is True
        assert verdicts["r1"].approved is False
        assert verdicts["r1"].reason == "timeout"

    def test_first_request_resolvable_after_second_arrives_asf05(self):
        """ASF-05: الطلب الأول كان يُكتب فوقه فيستحيل حلّه — الآن يُحل."""
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=5.0)
        r1 = _req("write", "a.txt", "chain")
        r2 = _req("command", "ls", "agent")
        verdicts, t1, t2 = _overlap(gate, r1, r2)

        # حلّ r1 (الأقدم) أولًا — كان matched=False قبل TSK-615
        assert gate.resolve(r1.request_id, True, payload_hash=r1.payload_hash)
        t1.join(timeout=3.0)
        assert verdicts["r1"].approved is True
        # r2 ما زال معلّقًا ومستقلًا
        assert gate.pending_request_ids() == [r2.request_id]
        assert gate.resolve(r2.request_id, False, payload_hash=r2.payload_hash)
        t2.join(timeout=3.0)
        assert verdicts["r2"].approved is False


class TestFailClosedPreserved:
    """fail-closed يبقى: مهلة لكل طلب + رفض hash خاطئ + قيود تدقيق سليمة."""

    def test_per_request_timeout_fail_closed(self):
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=0.8)
        r1 = _req("write", "a.txt", "chain")
        r2 = _req("command", "ls", "agent")
        verdicts, t1, t2 = _overlap(gate, r1, r2)

        # لا حلّ إطلاقًا — كل طلب يموت بمهلته المستقلة (deny)
        t1.join(timeout=3.0)
        t2.join(timeout=3.0)
        assert verdicts["r1"].approved is False
        assert verdicts["r1"].reason == "timeout"
        assert verdicts["r2"].approved is False
        assert verdicts["r2"].reason == "timeout"
        # الخريطة نظيفة بعد الخروج — لا تسرّب مداخل
        assert gate.pending_request_ids() == []

    def test_wrong_hash_rejected_per_entry(self):
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=0.8)
        r1 = _req("write", "a.txt", "chain")
        r2 = _req("command", "ls", "agent")
        verdicts, t1, t2 = _overlap(gate, r1, r2)

        # hash صحيح لكن لطلب آخر — يجب الرفض (لا مطابقة متقاطعة)
        assert not gate.resolve(r1.request_id, True, payload_hash=r2.payload_hash)
        assert not gate.resolve(r2.request_id, True, payload_hash=r1.payload_hash)
        t1.join(timeout=3.0)
        t2.join(timeout=3.0)
        assert verdicts["r1"].reason == "timeout"
        assert verdicts["r2"].reason == "timeout"

    def test_audit_attributes_verdicts_to_correct_requests(self):
        """C (أدلة S71): رفض r2 كان يسجّل user_denied زورًا على r1 —
        الآن كل قيد تدقيق ينسب القرار لطلبه الصحيح."""
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=1.5)
        r1 = _req("write", "a.txt", "chain")
        r2 = _req("command", "ls", "agent")
        verdicts, t1, t2 = _overlap(gate, r1, r2)

        gate.resolve(r2.request_id, False, payload_hash=r2.payload_hash)
        t1.join(timeout=4.0)
        t2.join(timeout=4.0)

        by_id = {e["request_id"]: e for e in gate.audit_entries()}
        assert by_id[r2.request_id]["reason"] == "user_denied"
        assert by_id[r1.request_id]["reason"] == "timeout"


class TestSingleRequestBehaviorUnchanged:
    """حفظ السلوك: مسار الطلب الواحد كما كان حرفيًا."""

    def test_pending_request_id_single_pending_same_as_before(self):
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=2.0)
        assert gate.pending_request_id() is None
        r1 = _req("write", "a.txt", "chain")
        verdicts = {}
        t1 = threading.Thread(
            target=lambda: verdicts.setdefault("r1", gate.request(r1)), daemon=True)
        t1.start()
        _wait_pending(gate, r1.request_id)
        assert gate.pending_request_id() == r1.request_id
        assert gate.pending_request_ids() == [r1.request_id]
        gate.resolve(r1.request_id, True, payload_hash=r1.payload_hash)
        t1.join(timeout=3.0)
        assert gate.pending_request_id() is None
        assert verdicts["r1"].approved is True

    def test_resolve_with_no_pending_still_noop(self):
        gate = ApprovalGate(mode="interactive", timeout_seconds=1.0)
        assert gate.resolve("ghost", True, payload_hash="x") is False

    def test_late_resolve_after_timeout_still_rejected(self):
        gate = ApprovalGate(mode="interactive", on_request=lambda f: None,
                            timeout_seconds=0.3)
        r1 = _req("write", "a.txt", "chain")
        verdict = gate.request(r1)  # يموت بمهلة متزامنًا
        assert verdict.approved is False and verdict.reason == "timeout"
        # المدخل أُزيل في finally — الرد المتأخر لا يطابق شيئًا
        assert gate.resolve(r1.request_id, True,
                            payload_hash=r1.payload_hash) is False
