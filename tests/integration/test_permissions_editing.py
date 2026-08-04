# -*- coding: utf-8 -*-
"""TSK-734c (القرار 6 من تسلسل D-19) — تحرير الأذونات من الواجهة.

معايير القبول المثبَّتة (مواصفة TSK-734 في DEVELOPMENT_TASKS):
  1. **التحرير حي بلا إعادة تشغيل**: POST يقلب force_command_approval
     فورًا (`_force_command_approval()` يقرأ الفعال)، ويعيد ربط
     ``agent_tools.command_policy`` مباشرة (كائن حي).
  2. **fail-closed على كل مدخل غير صالح**: 400 مع **صفر تغيير حالة**
     — لا لمس لملف overrides ولا لسياسة agent_tools.
  3. **config.yaml لا يُكتب أبدًا**: سليم بايتًا-ببايت بعد كل POST.
  4. ``null`` لمفتاح = مسح الـ override (عودة لقيمة config.yaml)؛
     overrides ناتجة فارغة ⇒ حذف الملف الجانبي.
  5. GET يعكس الـ overrides المخزنة (الفعال لا الخام) — واستجابة
     POST بنفس شكل GET (اللوحة تعيد الرسم من الحقيقة المعادة).
  6. ملف overrides معطوب على القرص ⇒ fail-closed (يتصرف كغيابه).
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from core.permissions_overrides import (  # noqa: E402
    OVERRIDES_FILENAME, read_overrides)

CONFIG_TEXT = """\
# تعليق عربي يجب أن يبقى سليمًا بايتًا-ببايت (TSK-734 — قرار واعٍ)
force_command_approval: false
agent:
  command_allowlist:
    test: python -m pytest -q
    lint: ruff check .
  command_timeout_seconds: 45
"""


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """بيئة معزولة: config.yaml في tmp + ثقة مفعّلة + agent_tools وهمي."""
    (tmp_path / "config.yaml").write_text(CONFIG_TEXT, encoding="utf-8")
    monkeypatch.setattr(server, "_DIR", tmp_path)
    # الثقة مفعّلة كي لا يعلو fail-closed الخاص بـ TSK-725b على القراءة.
    monkeypatch.setattr(server, "_workspace_trusted", lambda: True)

    class FakeAgentTools:
        command_policy = None
    fake = FakeAgentTools()
    from chain.agent_tools import command_policy_from
    fake.command_policy = command_policy_from(server._effective_config())
    monkeypatch.setattr(server, "agent_tools", fake)
    return tmp_path, fake


def _client():
    return server.app.test_client()


def _post(c, overrides):
    return c.post("/api/permissions", json={"overrides": overrides})


# ═════════════ 1. التحرير الحي بلا إعادة تشغيل (القبول) ═════════════

class TestLiveEditing:
    def test_force_flag_flips_live(self, env):
        """config يقول false؛ POST true ⇒ `_force_command_approval()`
        يقلب فورًا بلا إعادة تشغيل — ثم null يعيد قيمة config."""
        assert server._force_command_approval() is False  # من config
        with _client() as c:
            r = _post(c, {"force_command_approval": True})
            assert r.status_code == 200
            assert r.get_json()["permissions"][
                "force_command_approval"] is True
        assert server._force_command_approval() is True  # حي!
        with _client() as c:
            _post(c, {"force_command_approval": None})
        assert server._force_command_approval() is False  # عاد لـ config

    def test_allowlist_rebinds_agent_tools_live(self, env):
        """POST allowlist ⇒ ``agent_tools.command_policy`` يُستبدل
        مباشرة بسياسة جديدة من الفعال (كائن حي — بلا إعادة تشغيل)."""
        _, fake = env
        before = fake.command_policy
        assert set(before.allowlist) == {"test", "lint"}
        with _client() as c:
            r = _post(c, {"agent.command_allowlist": {"fmt": "black ."}})
            assert r.status_code == 200
        after = fake.command_policy
        assert after is not before  # أعيد الربط فعلًا
        assert after.allowlist == {"fmt": "black ."}
        # مفاتيح agent الأخرى من config تمر (timeout من config.yaml).
        assert after.timeout_seconds == 45

    def test_get_reflects_stored_overrides(self, env):
        """GET يعرض الفعال (config + overrides) لا الخام."""
        with _client() as c:
            _post(c, {"agent.command_allowlist": {"only": "echo hi"}})
            data = c.get("/api/permissions").get_json()
        al = data["permissions"]["command_allowlist"]
        assert al["entries"] == {"only": "echo hi"}
        assert al["timeout_seconds"] == 45  # من config — لم يُمس

    def test_post_response_same_shape_as_get(self, env):
        """استجابة POST = شكل GET حرفيًا (اللوحة ترسم من الحقيقة المعادة)."""
        with _client() as c:
            post_data = _post(c, {"force_command_approval": True}).get_json()
            get_data = c.get("/api/permissions").get_json()
        assert post_data == get_data


# ═════════════ 2. fail-closed — صفر تغيير حالة عند الرفض ═════════════

class TestFailClosed:
    @pytest.mark.parametrize("bad_body", [
        {},                                       # بلا overrides
        {"overrides": {}},                        # dict فارغ
        {"overrides": "str"},                     # ليس dict
        {"overrides": {"unknown_key": True}},     # مفتاح خارج whitelist
        {"overrides": {"force_command_approval": "yes"}},   # نوع خاطئ
        {"overrides": {"agent.command_allowlist": {"t": ""}}},  # قيمة فارغة
        {"overrides": {"agent.command_allowlist": ["t"]}},  # ليس dict
    ])
    def test_invalid_post_400_zero_state_change(self, env, bad_body):
        tmp_path, fake = env
        policy_before = fake.command_policy
        force_before = server._force_command_approval()
        with _client() as c:
            r = c.post("/api/permissions", json=bad_body)
        assert r.status_code == 400
        assert r.get_json()["ok"] is False
        # صفر تغيير حالة: لا ملف، لا إعادة ربط، لا قلب راية.
        assert not (tmp_path / OVERRIDES_FILENAME).exists()
        assert fake.command_policy is policy_before
        assert server._force_command_approval() == force_before

    def test_invalid_post_preserves_existing_overrides(self, env):
        """رفض التحديث لا يمس overrides المخزنة سابقًا."""
        tmp_path, _ = env
        with _client() as c:
            _post(c, {"force_command_approval": True})
            on_disk_before = (tmp_path / OVERRIDES_FILENAME).read_bytes()
            r = _post(c, {"evil": 1})
        assert r.status_code == 400
        assert (tmp_path / OVERRIDES_FILENAME).read_bytes() == on_disk_before

    def test_broken_overrides_file_fail_closed(self, env):
        """ملف overrides معطوب على القرص ⇒ يتصرف كغيابه (قيم config)."""
        tmp_path, _ = env
        (tmp_path / OVERRIDES_FILENAME).write_text("{broken", encoding="utf-8")
        assert server._force_command_approval() is False  # قيمة config
        with _client() as c:
            data = c.get("/api/permissions").get_json()
        assert data["permissions"]["command_allowlist"]["entries"] == {
            "test": "python -m pytest -q", "lint": "ruff check ."}


# ═════════════ 3. config.yaml لا يُكتب أبدًا + دورة الملف الجانبي ═════════════

class TestSideFileLifecycle:
    def test_config_yaml_byte_identical_after_edits(self, env):
        """التعليقات العربية في config.yaml سليمة بايتًا-ببايت."""
        tmp_path, _ = env
        raw_before = (tmp_path / "config.yaml").read_bytes()
        with _client() as c:
            _post(c, {"force_command_approval": True,
                      "agent.command_allowlist": {"x": "echo x"}})
            _post(c, {"force_command_approval": None})
            _post(c, {"evil": 1})  # مرفوض
        assert (tmp_path / "config.yaml").read_bytes() == raw_before

    def test_null_clears_and_empty_deletes_file(self, env):
        """null يمسح المفتاح؛ آخر مفتاح يُمسح ⇒ الملف الجانبي يُحذف."""
        tmp_path, _ = env
        side = tmp_path / OVERRIDES_FILENAME
        with _client() as c:
            _post(c, {"force_command_approval": True,
                      "agent.command_allowlist": {"x": "echo x"}})
            assert side.exists()
            _post(c, {"agent.command_allowlist": None})
            assert read_overrides(tmp_path) == {"force_command_approval": True}
            _post(c, {"force_command_approval": None})
        assert not side.exists()  # عودة كاملة لـ config.yaml

    def test_side_file_shape_on_disk(self, env):
        """شكل الملف الجانبي: {version, overrides} — عقد الوحدة النقية."""
        tmp_path, _ = env
        with _client() as c:
            _post(c, {"force_command_approval": True})
        data = json.loads((tmp_path / OVERRIDES_FILENAME).read_text(
            encoding="utf-8"))
        assert data == {"version": 1,
                        "overrides": {"force_command_approval": True}}

    def test_merge_preserves_other_key(self, env):
        """تحديث مفتاح لا يمسح الآخر (دمج فوق المخزن لا استبدال)."""
        tmp_path, _ = env
        with _client() as c:
            _post(c, {"force_command_approval": True})
            _post(c, {"agent.command_allowlist": {"y": "echo y"}})
        assert read_overrides(tmp_path) == {
            "force_command_approval": True,
            "agent.command_allowlist": {"y": "echo y"}}
