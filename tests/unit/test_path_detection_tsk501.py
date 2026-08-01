# -*- coding: utf-8 -*-
"""TSK-501 — كشف المسارات في الشات: بوابة قرابة + regex المسافات + المرفقات.

Validates: TSK-501.

الـ Bug الأصلي (ثلاثة عيوب):
  1. كارت ``path_detected_options`` كان يُرفع لأي مجلد مكتشف بلا فحص
     قرابة بالمشروع المفتوح — سحب ملف من نفس المشروع (أو ذكر مجلد
     أب مثل ``D:\\``) كان يوقف الرسالة بسؤال بلا معنى/خطر.
  2. نمط مسارات Windows القديم ``[A-Za-z]:[\\/ ][^\\s,;"'>]+`` كان
     يقبل المسافة فاصلًا بعد النقطتين (``D: كلام`` ⇒ مسار زائف)
     ويقطع المسار عند أول مسافة (``D:\\My Projects`` ⇒ ``D:\\My``).
  3. محتوى المرفقات الصريحة المدموج في نص الرسالة كان يُمسح نصيًا
     بحثًا عن مسارات (عشرات KB قد تحوي ``D:\\`` حرفيًا ⇒ كارت زائف).

معيار القبول:
  - نفس المشروع / مجلد ولد / مجلد أب ⇒ تجاهل صامت (لا كارت، الرسالة
    تكمل للـ AI).
  - خارج الشجرة تمامًا ⇒ الكارت يُرفع (السلوك القائم محفوظ).
  - الرسالة = مسار مجلد خارجي وحده ⇒ فتح مباشر كالسابق (لا تغيير).
  - regex: لا التقاط لـ ``D: كلام``؛ التقاط كامل لمسار بمسافات.
  - ما بعد ATTACHMENTS_MARKER خارج نطاق الكشف؛ إطار message الحامل
    ``has_attachments`` يمر بلا كشف أصلًا.

صفر نداءات AI خارجية — التنفيذ يُوقف عند gather_message_context
(نفس نمط test_prompt_fencing.py حرفيًا).
"""
import json
import pathlib
import re

import pytest

import server
from core.chat_dispatch import (
    ATTACHMENTS_MARKER,
    PATH_REL_ANCESTOR,
    PATH_REL_INSIDE,
    PATH_REL_OUTSIDE,
    PATH_REL_SAME,
    WIN_PATH_RE,
    classify_path_relation,
    iter_win_path_candidates,
)


class _Stop(BaseException):
    """يوقف التنفيذ بعد بوابة كشف المسارات — BaseException كي لا
    تبتلعه except Exception."""


class FakeWS:
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)

    def frames(self):
        return [json.loads(p) for p in self.sent]

    def frame_types(self):
        return [f.get("type") for f in self.frames()]


class _StubFM:
    def __init__(self, root):
        self.root = root


def _sctx(root):
    from core.app_context import ProjectHandle
    from core.session_context import SessionContext
    ws = FakeWS()
    send = lambda m: ws.send(json.dumps(m, ensure_ascii=False))
    sctx = SessionContext(
        send=send,
        project=ProjectHandle(root=str(root), fm=_StubFM(pathlib.Path(root))))
    return sctx, ws


def _dispatch_until_gather(monkeypatch, sctx, user_text, msg=None):
    """يشغّل المسار حتى gather_message_context ثم يوقف — يرجع هل
    وصل التنفيذ لما بعد كشف المسارات (True) أم توقف قبلها (False)."""
    reached = {"gather": False}

    def _stop_gather(*a, **k):
        reached["gather"] = True
        raise _Stop()

    monkeypatch.setattr(server, "gather_message_context", _stop_gather)
    try:
        server._dispatch_chat_message(None, sctx, user_text, "chat",
                                      msg or {})
    except _Stop:
        pass
    return reached["gather"]


# ═══════════════════════════════════════════════════════════
# عيب 1 — بوابة القرابة (classify_path_relation)
# ═══════════════════════════════════════════════════════════
class TestClassifyPathRelation:
    def test_same_root(self, tmp_path):
        assert classify_path_relation(str(tmp_path), str(tmp_path)) \
            == PATH_REL_SAME

    def test_same_root_trailing_sep_and_dots(self, tmp_path):
        import os
        assert classify_path_relation(
            str(tmp_path) + os.sep, str(tmp_path)) == PATH_REL_SAME
        assert classify_path_relation(
            str(tmp_path / "x" / ".."), str(tmp_path)) == PATH_REL_SAME

    def test_child_inside(self, tmp_path):
        assert classify_path_relation(
            str(tmp_path / "src" / "app"), str(tmp_path)) == PATH_REL_INSIDE

    def test_parent_ancestor(self, tmp_path):
        proj = tmp_path / "projects" / "my_app"
        assert classify_path_relation(str(tmp_path), str(proj)) \
            == PATH_REL_ANCESTOR

    def test_filesystem_root_is_ancestor(self, tmp_path):
        # مكافئ D:\ على Windows — جذر نظام الملفات أبٌ دائمًا.
        import os
        assert classify_path_relation(os.path.abspath(os.sep),
                                      str(tmp_path)) == PATH_REL_ANCESTOR

    def test_sibling_outside(self, tmp_path):
        a = tmp_path / "project_a"
        b = tmp_path / "project_b"
        assert classify_path_relation(str(b), str(a)) == PATH_REL_OUTSIDE

    def test_prefix_name_not_inside(self, tmp_path):
        """`/p/app2` ليس داخل `/p/app` — الفحص بحدود الفاصل لا بـ
        startswith خام."""
        a = tmp_path / "app"
        b = tmp_path / "app2"
        assert classify_path_relation(str(b), str(a)) == PATH_REL_OUTSIDE


class TestDispatchRelationGate:
    """التكامل: مجلد مكتشف قريب ⇒ لا كارت والرسالة تكمل؛ بعيد ⇒ كارت."""

    def test_same_project_dir_silently_ignored(self, monkeypatch, tmp_path):
        sctx, ws = _sctx(tmp_path)
        reached = _dispatch_until_gather(
            monkeypatch, sctx, f"قولي اي مشكلة في {tmp_path} ؟؟")
        assert reached, "الرسالة توقفت رغم أن المسار هو المشروع المفتوح نفسه"
        assert "path_detected_options" not in ws.frame_types()

    def test_child_dir_silently_ignored(self, monkeypatch, tmp_path):
        child = tmp_path / "src"
        child.mkdir()
        sctx, ws = _sctx(tmp_path)
        reached = _dispatch_until_gather(
            monkeypatch, sctx, f"راجع المجلد {child} كويس")
        assert reached
        assert "path_detected_options" not in ws.frame_types()

    def test_ancestor_dir_silently_ignored(self, monkeypatch, tmp_path):
        """مكافئ سيناريو D:\\ الأصلي — الأب لا يعرض توسيع النطاق."""
        proj = tmp_path / "SMS" / "my_app"
        proj.mkdir(parents=True)
        sctx, ws = _sctx(proj)
        reached = _dispatch_until_gather(
            monkeypatch, sctx, f"شوف الملف اللي جبته من {tmp_path} ده")
        assert reached
        assert "path_detected_options" not in ws.frame_types()
        assert "project_switched" not in ws.frame_types(), \
            "الأب لا يجب أن يبدّل المشروع أبدًا"

    def test_outside_dir_still_asks(self, monkeypatch, tmp_path):
        """Regression عكسي: السلوك القائم لمسار خارجي محفوظ."""
        proj = tmp_path / "proj"
        other = tmp_path / "other"
        proj.mkdir()
        other.mkdir()
        sctx, ws = _sctx(proj)
        server.pending_path_requests.clear()
        reached = _dispatch_until_gather(
            monkeypatch, sctx, f"افتحلي {other} وشوفه")
        assert not reached, "مسار خارجي يجب أن يوقف الرسالة بكارت السؤال"
        assert "path_detected_options" in ws.frame_types()
        server.pending_path_requests.clear()

    def test_bare_outside_dir_opens_directly(self, monkeypatch, tmp_path):
        """الرسالة = مسار مجلد خارجي وحده ⇒ يظل فتحًا مباشرًا (لا كارت).

        فتح المجلد يتطلب AppContext (switch_project) — نتحقق أن
        المسار لم يصل للكارت ولا لـ gather (توقف في فرع الفتح)."""
        proj = tmp_path / "proj"
        other = tmp_path / "other"
        proj.mkdir()
        other.mkdir()
        sctx, ws = _sctx(proj)
        reached = _dispatch_until_gather(monkeypatch, sctx, str(other))
        assert not reached
        assert "path_detected_options" not in ws.frame_types()


# ═══════════════════════════════════════════════════════════
# عيب 2 — regex مسارات Windows
# ═══════════════════════════════════════════════════════════
class TestWindowsPathRegex:
    """المسافة مبهمة (داخل اسم مجلد أم فاصل قبل كلام؟) — لا يحسمها
    regex وحده. العقد: النمط لا يلتقط زائفًا بعد "D: "، والمرشحون
    (iter_win_path_candidates) يشملون كل بادئات القصّ عند المسافات
    من الأطول للأقصر — الحسم النهائي بالقرص (isdir/isfile)."""

    def test_no_false_positive_on_colon_space(self):
        """النمط القديم كان يلتقط "D: كلام" — الجديد يرفضه."""
        assert re.findall(WIN_PATH_RE, "المسار D: كلام عادي") == []
        assert list(iter_win_path_candidates("المسار D: كلام عادي")) == []

    def test_candidates_include_full_path_with_spaces(self):
        cands = list(iter_win_path_candidates(
            r"افتح D:\My Projects\app دلوقتي"))
        assert cands[0] == r"D:\My Projects\app دلوقتي"  # الأطول أولًا
        assert r"D:\My Projects\app" in cands            # المسار الحقيقي مرشح
        assert cands[-1] == r"D:\My"                     # وأقصر بادئة أيضًا

    def test_candidates_simple_path_first(self):
        cands = list(iter_win_path_candidates(
            r"شوف D:\SMS\project\file.txt كده"))
        assert r"D:\SMS\project\file.txt" in cands

    def test_forward_slash_variant(self):
        cands = list(iter_win_path_candidates("افتح D:/work/repo هنا"))
        assert "D:/work/repo" in cands

    def test_bare_drive_root_detected(self):
        r"""D:\ وحدها تُلتقط (جذر درايف) — بوابة القرابة (ancestor)
        هي ما يمنع الكارت، لا إخفاء الالتقاط."""
        got = re.findall(WIN_PATH_RE, r"جبته من D:\ يعني")
        assert got and got[0].startswith("D:\\")

    def test_disk_resolution_picks_real_dir_with_space(self, tmp_path,
                                                       monkeypatch,
                                                       tmp_path_factory):
        """التكامل الحاسم: مجلد حقيقي باسم فيه مسافة يُكتشف كاملًا
        (القديم كان يقطع عند المسافة فلا يجده أبدًا)."""
        proj = tmp_path / "proj"
        spaced = tmp_path / "My Projects" / "app"
        proj.mkdir()
        spaced.mkdir(parents=True)
        sctx, ws = _sctx(proj)
        server.pending_path_requests.clear()
        reached = _dispatch_until_gather(
            monkeypatch, sctx, f"افتح {spaced} وشوفه")
        assert not reached, "المجلد ذو المسافة لم يُكتشف — قُطع عند المسافة"
        frames = ws.frames()
        card = [f for f in frames if f.get("type") == "path_detected_options"]
        assert card and card[0]["path"] == str(spaced)
        server.pending_path_requests.clear()


# ═══════════════════════════════════════════════════════════
# عيب 3 — المرفقات الصريحة
# ═══════════════════════════════════════════════════════════
class TestAttachmentsSkipDetection:
    def test_marker_body_not_scanned(self, monkeypatch, tmp_path):
        """محتوى مدموج بعد العلامة يحوي مسار مجلد خارجي حقيقي —
        لا كارت: الكشف يمسح كلام المستخدم فقط."""
        proj = tmp_path / "proj"
        other = tmp_path / "other"
        proj.mkdir()
        other.mkdir()
        sctx, ws = _sctx(proj)
        text = (f"قولي اي مشكلة هنا؟؟\n\n{ATTACHMENTS_MARKER}\n\n"
                f"📄 **big.py**\n```py\nBASE = r'{other}'\n```")
        reached = _dispatch_until_gather(monkeypatch, sctx, text)
        assert reached
        assert "path_detected_options" not in ws.frame_types()

    def test_user_portion_before_marker_still_scanned(self, monkeypatch,
                                                      tmp_path):
        """كلام المستخدم نفسه (قبل العلامة) يظل مشمولًا بالكشف."""
        proj = tmp_path / "proj"
        other = tmp_path / "other"
        proj.mkdir()
        other.mkdir()
        sctx, ws = _sctx(proj)
        server.pending_path_requests.clear()
        text = f"افتح {other}\n\n{ATTACHMENTS_MARKER}\n\nمحتوى"
        reached = _dispatch_until_gather(monkeypatch, sctx, text)
        assert not reached
        assert "path_detected_options" in ws.frame_types()
        server.pending_path_requests.clear()

    def test_has_attachments_flag_skips_detection(self, monkeypatch,
                                                  tmp_path):
        """إطار message مع has_attachments=true — عبر _ws_message —
        لا كشف مسارات إطلاقًا حتى لمسار خارجي في كلام المستخدم."""
        proj = tmp_path / "proj"
        other = tmp_path / "other"
        proj.mkdir()
        other.mkdir()
        sctx, ws = _sctx(proj)
        reached = {"gather": False}

        def _stop_gather(*a, **k):
            reached["gather"] = True
            raise _Stop()

        monkeypatch.setattr(server, "gather_message_context", _stop_gather)
        with pytest.raises(_Stop):
            server._ws_message(None, sctx, {
                "text": f"بص على {other}",
                "mode": "chat",
                "has_attachments": True,
            })
        assert reached["gather"]
        assert "path_detected_options" not in ws.frame_types()
