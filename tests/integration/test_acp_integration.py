# -*- coding: utf-8 -*-
"""TSK-736c (القرار 8 من تسلسل D-19) — تكامل ACP بوكيل الدمية المحلي.

**اختبار التكامل الوحيد المسموح له subprocess حقيقي** (القرار الواعي
5): يشغّل tests/fixtures/acp_echo_agent.py بمفسر بايثون الحالي —
سكربت محلي خالص، لا تنزيل ولا شبكة أبدًا.

معايير القبول المثبَّتة (مواصفة TSK-736):
  1. وكيل معرَّف في config يظهر في /api/acp/agents (بادئة 🤝) —
     **بلا كشف command/args** (عقد عدم-الكشف).
  2. بلا قسم acp ⇒ قائمة فارغة (opt-in — صفر تغيير سلوك).
  3. الوكيل يجيب prompt عبر الجسر (initialize → session/new →
     session/prompt → ECHO) + إشعار session/update يصل.
  4. fs/read لسر denylist يُرفض — الكناري لا يصل الوكيل أبدًا.
  5. fs/write بلا موافقة (بوابة deny) لا يلمس القرص؛ بموافقة auto
     يهبط فعليًا.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from chain.acp.agent_process import AcpAgentProcess  # noqa: E402
from chain.acp.governed_fs import GovernedFsHandler  # noqa: E402
from chain.acp.protocol import (  # noqa: E402
    ERR_PATH_FORBIDDEN,
    ERR_PERMISSION_DENIED,
)
from core.approval import ApprovalGate  # noqa: E402

ECHO_AGENT = str(ROOT / "tests" / "fixtures" / "acp_echo_agent.py")
CANARY = "sk-CANARY-736c-never-reaches-agent"

CONFIG_WITH_ACP = """\
# بيئة اختبار TSK-736c
force_command_approval: true
acp:
  agents:
    - id: "echo"
      name: "وكيل الصدى"
      command: "python"
      args: ["tests/fixtures/acp_echo_agent.py"]
    - id: ""
      command: "broken"
    - id: "no_command_agent"
"""

CONFIG_WITHOUT_ACP = """\
force_command_approval: true
"""


@pytest.fixture()
def env_acp(monkeypatch, tmp_path):
    (tmp_path / "config.yaml").write_text(CONFIG_WITH_ACP, encoding="utf-8")
    monkeypatch.setattr(server, "_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def env_no_acp(monkeypatch, tmp_path):
    (tmp_path / "config.yaml").write_text(CONFIG_WITHOUT_ACP,
                                          encoding="utf-8")
    monkeypatch.setattr(server, "_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def workspace(tmp_path_factory):
    ws = tmp_path_factory.mktemp("acp-ws")
    (ws / "notes.txt").write_text("ملاحظات المشروع", encoding="utf-8")
    (ws / "provider_keys.json").write_text(
        '{"k": "' + CANARY + '"}', encoding="utf-8")
    return ws


def _agent(workspace, gate):
    handler = GovernedFsHandler(workspace, approval_gate=gate, source="acp")
    return AcpAgentProcess(
        command=sys.executable,
        args=[ECHO_AGENT],
        cwd=str(ROOT),
        on_request=handler,
    )


# ═══ REST: /api/acp/agents ═══

class TestAcpAgentsEndpoint:
    def test_configured_agent_listed_without_command(self, env_acp):
        resp = server.app.test_client().get("/api/acp/agents")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["agents"] == [{"id": "echo", "name": "🤝 وكيل الصدى"}]
        # عقد عدم-الكشف: لا command/args في الاستجابة الخام
        raw = resp.get_data(as_text=True)
        assert "command" not in raw
        assert "acp_echo_agent" not in raw

    def test_malformed_entries_dropped(self, env_acp):
        agents = server._acp_agents_config()
        assert set(agents) == {"echo"}

    def test_no_section_zero_behavior_change(self, env_no_acp):
        resp = server.app.test_client().get("/api/acp/agents")
        data = resp.get_json()
        assert data == {"ok": True, "agents": []}


# ═══ التكامل الحقيقي (subprocess الوحيد المسموح — وكيل دمية محلي) ═══

@pytest.mark.integration
class TestEchoAgentIntegration:
    @pytest.mark.timeout(30)
    def test_full_prompt_roundtrip_with_update_notification(self, workspace):
        updates = []
        handler = GovernedFsHandler(workspace, approval_gate=None)
        proc = AcpAgentProcess(
            command=sys.executable, args=[ECHO_AGENT], cwd=str(ROOT),
            on_request=handler, on_notification=lambda n: updates.append(n))
        try:
            init = proc.start()
            assert init.get("protocolVersion") == 1
            assert proc.alive
            sid = proc.new_session(str(workspace))
            assert sid == "echo-1"
            result = proc.prompt(sid, "مرحبا يا وكيل")
            assert result["text"] == "ECHO:مرحبا يا وكيل"
            assert result["stopReason"] == "end_turn"
            # إشعار session/update وصل عبر الجسر
            assert any(n.method == "session/update" for n in updates)
        finally:
            proc.stop()
        assert not proc.alive

    @pytest.mark.timeout(30)
    def test_normal_read_reaches_agent(self, workspace):
        proc = _agent(workspace, gate=None)
        try:
            proc.start()
            sid = proc.new_session(str(workspace))
            result = proc.prompt(sid, "READ:notes.txt")
            assert result["text"] == "READ_OK:ملاحظات المشروع"
        finally:
            proc.stop()

    @pytest.mark.timeout(30)
    def test_secret_read_denied_canary_never_reaches_agent(self, workspace):
        proc = _agent(workspace, gate=None)
        try:
            proc.start()
            sid = proc.new_session(str(workspace))
            result = proc.prompt(sid, "READ:provider_keys.json")
            assert result["text"] == f"READ_DENIED:{ERR_PATH_FORBIDDEN}"
            assert CANARY not in str(result)
        finally:
            proc.stop()

    @pytest.mark.timeout(30)
    def test_write_without_approval_never_touches_disk(self, workspace):
        proc = _agent(workspace, gate=ApprovalGate(mode="deny"))
        try:
            proc.start()
            sid = proc.new_session(str(workspace))
            result = proc.prompt(sid, "WRITE:evil.txt:غزو")
            assert result["text"] == f"WRITE_DENIED:{ERR_PERMISSION_DENIED}"
            assert not (workspace / "evil.txt").exists()
        finally:
            proc.stop()

    @pytest.mark.timeout(30)
    def test_approved_write_lands_on_disk(self, workspace):
        gate = ApprovalGate(mode="auto",
                            auto_whitelist=frozenset({"acp_write"}))
        proc = _agent(workspace, gate=gate)
        try:
            proc.start()
            sid = proc.new_session(str(workspace))
            result = proc.prompt(sid, "WRITE:approved.txt:محتوى معتمد")
            assert result["text"] == "WRITE_OK"
            assert (workspace / "approved.txt").read_text(
                encoding="utf-8") == "محتوى معتمد"
        finally:
            proc.stop()
