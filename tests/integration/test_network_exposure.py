# -*- coding: utf-8 -*-
"""TSK-737b (القرار 9 من تسلسل D-19 — الأخير) — توصيل حارس التعريض.

معايير القبول المثبَّتة (مواصفة TSK-737):
  1. إقلاع ``--host`` غير loopback بلا راية ⇒ رفض SystemExit(2)
     برسالة شارحة — **قبل** أي تهيئة ثقيلة.
  2. الوضع المحلي (غياب host في ctx.config أو loopback) ⇒ صفر تغيير
     سلوك (الانحدار القائم يغطيه).
  3. تحت التعريض: POST /api/permissions = 403 (GET يبقى)؛
     WS acp_prompt ⇒ acp_error؛ force_command_approval = True قسرًا
     (يعلو على false الصريحة وعلى overrides).

**صفر شبكة/subprocess** (القرار الواعي 7): التعريض يُحقَن عبر
monkeypatch لـ ``server.ctx`` (fake بحقل config) — لا ربط فعلي؛
حارس الإقلاع يُختبَر in-process (يرفع قبل أي تهيئة ثقيلة).
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402

CONFIG_TEXT = """\
# config اختباري — false صريحة كي يثبت أن القسر يعلو عليها
force_command_approval: false
agent:
  command_allowlist:
    test: python -m pytest -q
"""


class _FakeCtx:
    """بديل AppContext بأدنى سطح — config فقط (ما يقرؤه الحارس)."""

    def __init__(self, host=None):
        self.config = {} if host is None else {"host": host}


@pytest.fixture()
def local_env(monkeypatch, tmp_path):
    """بيئة محلية: config في tmp + ثقة مفعّلة + ctx بربط loopback."""
    (tmp_path / "config.yaml").write_text(CONFIG_TEXT, encoding="utf-8")
    monkeypatch.setattr(server, "_DIR", tmp_path)
    monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
    monkeypatch.setattr(server, "ctx", _FakeCtx("127.0.0.1"))
    return tmp_path


@pytest.fixture()
def exposed_env(monkeypatch, tmp_path):
    """بيئة معرَّضة: نفس المحلية لكن ctx بربط 0.0.0.0."""
    (tmp_path / "config.yaml").write_text(CONFIG_TEXT, encoding="utf-8")
    monkeypatch.setattr(server, "_DIR", tmp_path)
    monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
    monkeypatch.setattr(server, "ctx", _FakeCtx("0.0.0.0"))
    return tmp_path


def _client():
    return server.app.test_client()


class TestNetworkExposedPredicate:
    """_network_exposed — الحكم بواقعة الربط (القرار الواعي 5)."""

    def test_ctx_none_is_local(self, monkeypatch):
        """سياق اختبار/قبل-main ⇒ محلي (صفر تغيير سلوك للانحدار)."""
        monkeypatch.setattr(server, "ctx", None)
        assert server._network_exposed() is False

    def test_missing_host_key_is_local(self, monkeypatch):
        monkeypatch.setattr(server, "ctx", _FakeCtx())
        assert server._network_exposed() is False

    @pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
    def test_loopback_hosts_local(self, monkeypatch, host):
        monkeypatch.setattr(server, "ctx", _FakeCtx(host))
        assert server._network_exposed() is False

    @pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.5"])
    def test_non_loopback_hosts_exposed(self, monkeypatch, host):
        monkeypatch.setattr(server, "ctx", _FakeCtx(host))
        assert server._network_exposed() is True


class TestBootGuard:
    """حارس الإقلاع fail-closed — يرفع قبل أي تهيئة ثقيلة."""

    def test_exposed_host_without_flag_refuses(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv",
                            ["server.py", "--host", "0.0.0.0"])
        with pytest.raises(SystemExit) as exc_info:
            server.main()
        assert exc_info.value.code == 2
        out = capsys.readouterr().out
        assert "--unsafe-expose-network" in out
        assert "0.0.0.0" in out
        # الرسالة تذكر المسار السليم (نفق SSH ينتهي إلى loopback).
        assert "SSH" in out

    def test_ipv6_any_without_flag_refuses(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["server.py", "--host", "::"])
        with pytest.raises(SystemExit) as exc_info:
            server.main()
        assert exc_info.value.code == 2


class TestForcedApprovalUnderExposure:
    """القرار الواعي 4 — القسر يعلو على false الصريحة وعلى overrides."""

    def test_local_respects_explicit_false(self, local_env):
        assert server._force_command_approval() is False

    def test_exposed_forces_true(self, exposed_env):
        assert server._force_command_approval() is True

    def test_exposed_overrides_cannot_flip(self, exposed_env):
        """حتى override جانبي بـ false لا يُقلِّب القسر."""
        from core.permissions_overrides import write_overrides
        assert write_overrides(exposed_env,
                               {"force_command_approval": False})
        assert server._force_command_approval() is True


class TestPermissionsLockedUnderExposure:
    """القرار الواعي 3-أ — T1 أخطر مسار (RCE عبر قلب الأذونات)."""

    def test_post_permissions_403(self, exposed_env):
        resp = _client().post(
            "/api/permissions",
            json={"overrides": {"force_command_approval": False}})
        assert resp.status_code == 403
        body = resp.get_json()
        assert body["ok"] is False
        assert "localhost" in body["error"]

    def test_post_403_zero_state_change(self, exposed_env):
        """403 بصفر لمس للقرص — لا ملف overrides يُنشأ."""
        from core.permissions_overrides import overrides_path
        _client().post(
            "/api/permissions",
            json={"overrides": {"force_command_approval": False}})
        assert not overrides_path(exposed_env).exists()

    def test_get_permissions_still_works(self, exposed_env):
        """GET يبقى — قراءة glass-box لا تُغيّر حالة."""
        resp = _client().get("/api/permissions")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_post_works_locally_regression(self, local_env):
        """الوضع المحلي: POST يعمل كما كان (صفر تغيير سلوك)."""
        resp = _client().post(
            "/api/permissions",
            json={"overrides": {"force_command_approval": True}})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


class _FakeSctx:
    """سياق WS وهمي — يجمع الإطارات المُرسلة."""

    def __init__(self):
        self.frames = []
        self.project = None

    def send(self, frame):
        self.frames.append(frame)


class TestAcpRejectedUnderExposure:
    """القرار الواعي 3-جـ — T3: لا subprocess بقيادة نظير شبكي."""

    def test_acp_prompt_rejected_when_exposed(self, exposed_env):
        sctx = _FakeSctx()
        server._ws_acp_prompt(None, sctx,
                              {"agent_id": "echo", "text": "hi"})
        assert len(sctx.frames) == 1
        frame = sctx.frames[0]
        assert frame["type"] == "acp_error"
        assert "localhost" in frame["text"]

    def test_acp_prompt_normal_validation_locally(self, local_env):
        """محليًا: يمر لفحص المدخلات المعتاد (صفر تغيير سلوك)."""
        sctx = _FakeSctx()
        server._ws_acp_prompt(None, sctx, {"agent_id": "", "text": ""})
        assert sctx.frames[0]["type"] == "acp_error"
        assert "مطلوبان" in sctx.frames[0]["text"]
