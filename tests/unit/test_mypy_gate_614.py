# -*- coding: utf-8 -*-
"""TSK-614 (QG-04 §R8, ADR-004): بوابة mypy الموسعة.

يثبّت:
  1. بنية سطر البوابة في check.sh: العلم --check-untyped-defs +
     الاستبعاد المفرد + النطاق الكامل (routes/ + server.py).
  2. **الاختبار السلبي الموثق (القبول نصًّا)**: نداء لدالة غير موجودة
     داخل دالة غير مُعنونة (نمط دوال routes الفعلي) يُفشل mypy
     بأعلام البوابة — ولا يُلتقط بدونها (يثبت ضرورة العلم: توسيع
     قائمة الملفات وحده بوابة شكلية).
  3. إصلاح NF-25: provider_pool/approval_gate محقونان في deps
     (server.py) ومستهلَكان عبر deps. في core/chat_dispatch.py —
     لا أسماء عارية غير معرّفة (فحص AST).
  4. إصلاح NF-26: مسار attach المجلد يستهلك dict[str, str] الذي
     يرجعه scan_folder_for_chain فعليًا — كل ملف يصل مسيَّجًا
     بمحتواه (وظيفيًا، كان يتدهور صامتًا بـ TypeError مبتلَع).
"""
import ast
import json
import pathlib
import subprocess
import sys

import pytest

import server

ROOT = pathlib.Path(server.__file__).parent
CHECK_SH = (ROOT / "scripts" / "check.sh").read_text(encoding="utf-8")
DISPATCH_SRC = (ROOT / "core" / "chat_dispatch.py").read_text(encoding="utf-8")
SERVER_SRC = pathlib.Path(server.__file__).read_text(encoding="utf-8")

GATE_FLAGS = ["--ignore-missing-imports", "--follow-imports=silent",
              "--check-untyped-defs"]


# ═══════════ 1) بنية سطر البوابة ═══════════

class TestGateLineStructure:
    def test_flag_check_untyped_defs_present(self):
        """بدون العلم أجسام الدوال غير المُعنونة لا تُفحص — القبول يسقط."""
        assert "--check-untyped-defs" in CHECK_SH

    def test_scope_includes_routes_and_server(self):
        assert "routes/ server.py" in CHECK_SH

    def test_documented_excludes_only(self):
        """الاستبعادات محصورة بالمسوَّغ الموثَّق: openai_shelby (خطأ قائم
        مسبقًا — ADR-004) + you_com/perplexity/blackbox (كود وارد خارج
        الحوكمة @ c9ab00c — TSK-CEV-102/D-13)؛ كلها providers/ خارج
        النطاق §0.8، وproviders/ نفسها باقية في النطاق."""
        assert (r"--exclude 'providers/(openai_shelby|you_com|perplexity"
                r"|blackbox)\.py'") in CHECK_SH
        # لا استبعاد لأي ملف داخل النطاق الداخلي (chain/core/...)
        assert "--exclude 'chain" not in CHECK_SH
        assert CHECK_SH.count("--exclude") == 1
        # providers/ ما زالت تُفحص (لم تُستبعد كلها)
        mypy_line_block = CHECK_SH[CHECK_SH.index("--check-untyped-defs"):]
        assert "providers/ chain/" in mypy_line_block


# ═══════════ 2) الاختبار السلبي الموثق (القبول) ═══════════

def _run_mypy(args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "mypy", *args],
        capture_output=True, text=True, cwd=str(cwd))


class TestNegativePlantedCall:
    """يزرع نداءً لدالة غير موجودة في ملف بنمط route غير مُعنون
    (كدوال routes/ الـ25 الفعلية: بلا `->` وبلا تعنوين معاملات)."""

    PLANTED = (
        "def api_planted_route():\n"
        "    _tsk614_nonexistent_function()\n"
        "    return 1\n"
    )

    def test_gate_flags_catch_planted_call(self, tmp_path):
        """بأعلام البوابة: exit=1 + [name-defined] — القبول متحقق."""
        f = tmp_path / "planted.py"
        f.write_text(self.PLANTED, encoding="utf-8")
        res = _run_mypy([*GATE_FLAGS, str(f)], tmp_path)
        assert res.returncode == 1
        assert "name-defined" in res.stdout

    def test_without_flag_planted_call_escapes(self, tmp_path):
        """بدون --check-untyped-defs: Success — يثبت أن توسيع قائمة
        الملفات وحده لا يحقق شرط القبول (لماذا العلم إلزامي)."""
        f = tmp_path / "planted.py"
        f.write_text(self.PLANTED, encoding="utf-8")
        res = _run_mypy(["--ignore-missing-imports",
                         "--follow-imports=silent", str(f)], tmp_path)
        assert res.returncode == 0


# ═══════════ 3) NF-25: حقن provider_pool/approval_gate ═══════════

class TestNF25DepsInjection:
    def test_deps_namespace_includes_both(self):
        """server.py يحقن الرمزين في deps (استعادة دلالة ما قبل 612)."""
        assert "provider_pool=provider_pool" in SERVER_SRC
        assert "approval_gate=approval_gate," in SERVER_SRC

    def test_dispatch_consumes_via_deps(self):
        assert "deps.provider_pool" in DISPATCH_SRC
        assert "approval_gate=deps.approval_gate" in DISPATCH_SRC

    def test_no_undefined_module_names(self):
        """فحص AST: لا Name-load لأي من الرمزين عاريًا في chat_dispatch
        (كانا يرفعان NameError وقت تشغيل agent — NF-25)."""
        tree = ast.parse(DISPATCH_SRC)
        bare = [n.id for n in ast.walk(tree)
                if isinstance(n, ast.Name)
                and isinstance(n.ctx, ast.Load)
                and n.id in ("provider_pool", "approval_gate")]
        assert bare == []


# ═══════════ 4) NF-26: attach المجلد يستهلك dict ═══════════

class FakeWS:
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)


class _StubFM:
    def __init__(self, root):
        self.root = root


def _sctx(root="/tmp/x"):
    from core.app_context import ProjectHandle
    from core.session_context import SessionContext
    ws = FakeWS()
    send = lambda m: ws.send(json.dumps(m, ensure_ascii=False))
    sctx = SessionContext(
        send=send,
        project=ProjectHandle(root=str(root), fm=_StubFM(pathlib.Path(root))))
    return sctx, ws


class TestNF26FolderAttachConsumesDict:
    def test_attach_delivers_fenced_file_contents(self, monkeypatch,
                                                  tmp_path):
        """scan_folder_for_chain يرجع dict[str, str] — كل ملف يصل في
        attached_context بمفتاح attach_file: ومحتواه داخل السياج.
        قبل الإصلاح: TypeError (تقطيع dict) يبتلعه except ⇒ header
        فقط بلا أي محتوى (تدهور صامت — عكس قبول TSK-404)."""
        import chain.bridge as bridge_mod
        monkeypatch.setattr(
            bridge_mod, "scan_folder_for_chain",
            lambda path, **kw: {"a.py": "content_A", "sub/b.py": "content_B"})

        captured = {}

        def _capturing_dispatch(ctx, sctx, user_text, mode, msg, **kw):
            captured["attached"] = kw.get("attached_context")

        monkeypatch.setattr(server, "_dispatch_chat_message",
                            _capturing_dispatch)

        req_id = "tsk614-nf26"
        server.store_pending_path_request(req_id, {
            "path": str(tmp_path),
            "user_text": "اشرح المجلد",
            "mode": "chat",
            "msg": {},
        })
        sctx, _ws = _sctx(root=str(tmp_path))
        server._ws_confirm_path_action(
            None, sctx, {"request_id": req_id, "action": "attach"})

        attached = captured["attached"]
        assert attached, "attached_context لم يصل"
        keys = [k for k, _ in attached]
        assert keys[0].startswith("attach_folder:")
        file_keys = [k for k in keys if k.startswith("attach_file:")]
        assert file_keys == ["attach_file:a.py", "attach_file:sub/b.py"]
        payloads = dict(attached)
        assert "content_A" in payloads["attach_file:a.py"]
        assert "content_B" in payloads["attach_file:sub/b.py"]
        # التسييج (TSK-404) محفوظ
        assert payloads["attach_file:a.py"].startswith("<attached-content ")

    def test_cap_15_files(self, monkeypatch, tmp_path):
        """سقف الـ15 ملفًا (سلوك TSK-404 الأصلي المقصود) بعد الإصلاح."""
        import chain.bridge as bridge_mod
        many = {f"f{i:02d}.py": f"c{i}" for i in range(20)}
        monkeypatch.setattr(bridge_mod, "scan_folder_for_chain",
                            lambda path, **kw: many)
        captured = {}
        monkeypatch.setattr(
            server, "_dispatch_chat_message",
            lambda ctx, sctx, t, m, g, **kw: captured.update(
                attached=kw.get("attached_context")))
        req_id = "tsk614-nf26-cap"
        server.store_pending_path_request(req_id, {
            "path": str(tmp_path), "user_text": "x",
            "mode": "chat", "msg": {}})
        sctx, _ws = _sctx(root=str(tmp_path))
        server._ws_confirm_path_action(
            None, sctx, {"request_id": req_id, "action": "attach"})
        file_keys = [k for k, _ in captured["attached"]
                     if k.startswith("attach_file:")]
        assert len(file_keys) == 15
