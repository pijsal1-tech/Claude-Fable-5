# -*- coding: utf-8 -*-
"""
QA-T08 (جزء TSK-305) — تضييق مواضع except الحرجة + log (NF-14).
Validates: TSK-305.

معيار القبول الحرفي: فشل قراءة ملف مكتشف → المستخدم يرى تنبيهًا
(إطار ``warning``)؛ لا تغيير سلوك آخر. + حارسا نظافة (grep-guards):
لا ``except:`` عارية في server.py، وكل ابتلاع صامت مصنّف بتعليق
NF-14 §مرقّم. صفر نداءات AI خارجية.
"""
import json
import pathlib
import re

import builtins

import pytest

import server

SERVER_SRC = pathlib.Path(server.__file__).read_text(encoding="utf-8")


class _Stop(BaseException):
    """يوقف _dispatch_chat_message بعد بلوك الملف المكتشف مباشرة —
    BaseException عمدًا كي لا تبتلعه except Exception (§7)."""


class FakeWS:
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)


def _sctx():
    from core.session_context import SessionContext
    ws = FakeWS()
    send = lambda m: ws.send(json.dumps(m, ensure_ascii=False))
    return SessionContext(send=send), ws


def _frames(ws):
    return [json.loads(p) for p in ws.sent]


def _dispatch_until_context(monkeypatch, user_text):
    """يشغّل _dispatch_chat_message ويوقفه عند gather_message_context."""
    def _raiser(*a, **k):
        raise _Stop()

    monkeypatch.setattr(server, "gather_message_context", _raiser)
    sctx, ws = _sctx()
    with pytest.raises(_Stop):
        server._dispatch_chat_message(None, sctx, user_text, "chat", {})
    return ws


class TestAcceptCriterion:
    """معيار القبول: فشل قراءة ملف مكتشف → إطار تنبيه للمستخدم."""

    def test_unreadable_detected_file_sends_warning(self, monkeypatch,
                                                    tmp_path):
        target = tmp_path / "secret.py"
        target.write_text("x = 1", encoding="utf-8")
        real_open = builtins.open

        def _failing_open(file, *a, **k):
            if str(file) == str(target):
                raise OSError("Permission denied (fake)")
            return real_open(file, *a, **k)

        monkeypatch.setattr(builtins, "open", _failing_open)
        ws = _dispatch_until_context(monkeypatch, f'اشرح "{target}"')

        warnings = [f for f in _frames(ws) if f["type"] == "warning"]
        assert len(warnings) == 1
        assert "تعذّرت قراءة الملف" in warnings[0]["text"]
        assert str(target) in warnings[0]["text"]

    def test_readable_detected_file_no_warning(self, monkeypatch, tmp_path):
        """لا تغيير سلوك آخر: القراءة الناجحة بلا أي إطار جديد."""
        target = tmp_path / "ok.py"
        target.write_text("y = 2", encoding="utf-8")
        ws = _dispatch_until_context(monkeypatch, f'اشرح "{target}"')
        assert _frames(ws) == []  # صفر إطارات — نفس السلوك القديم

    def test_no_detected_file_no_warning(self, monkeypatch):
        ws = _dispatch_until_context(monkeypatch, "اشرح المشروع")
        assert _frames(ws) == []


class TestExceptHygiene:
    """جرد NF-14: لا except عارية، وكل ابتلاع صامت مصنّف بتعليق مرقّم."""

    def test_no_bare_except_in_server(self):
        """صفر ``except:`` عارية (كانت واحدة عند الإقلاع — ضُيّقت)."""
        bare = [ln for ln in SERVER_SRC.splitlines()
                if re.match(r"^\s*except\s*:", ln)]
        assert bare == []

    def test_all_silent_pass_sites_classified(self):
        """كل ``except Exception`` متبوعة بـ ``pass`` لها تعليق NF-14 §N
        (تصنيف: ابتلاع مقصود / يحتاج log) — لا ابتلاع مجهول الهوية."""
        lines = SERVER_SRC.splitlines()
        unclassified = []
        for i, ln in enumerate(lines):
            m = re.match(r"^\s*except\s+\w[\w.]*(\s+as\s+\w+)?\s*:\s*$", ln)
            one_liner = re.match(r"^\s*except\s+\w[\w.]*\s*:\s*pass\s*$", ln)
            if not (m or one_liner):
                continue
            # حدد أول سطر تنفيذي داخل البلوك
            body_is_pass = bool(one_liner)
            window = []
            if m:
                for j in range(i + 1, min(i + 6, len(lines))):
                    stripped = lines[j].strip()
                    window.append(stripped)
                    if stripped.startswith("#") or not stripped:
                        continue
                    body_is_pass = stripped == "pass"
                    break
            if not body_is_pass:
                continue
            # ابتلاع صامت — لازم تصنيف NF-14 (قبل except أو بين except وpass)
            context = lines[max(0, i - 3):i] + window
            if not any("NF-14" in c for c in context):
                unclassified.append(f"L{i+1}: {ln.strip()}")
        assert unclassified == [], (
            "مواضع ابتلاع صامت بلا تصنيف NF-14:\n" + "\n".join(unclassified))

    def test_warning_frame_type_is_new(self):
        """نوع الإطار الجديد ``warning`` لا يظلل نوعًا قائمًا في الواجهة."""
        app_js = (pathlib.Path(server.__file__).parent
                  / "static" / "app.js").read_text(encoding="utf-8")
        assert 'case "warning":' in app_js  # الواجهة تتعامل معه (toast)
