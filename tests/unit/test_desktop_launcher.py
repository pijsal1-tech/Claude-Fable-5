"""TSK-727b — اختبارات بنيوية لمُطلِق سطح المكتب desktop.py (ADR-006).

بيئة التطوير بلا GUI ⇒ لا فتح نافذة هنا؛ التحقق التشغيلي النهائي
على Windows بيد المالك (D-8-ب — OWNER_CHECKLIST.md). هذه الاختبارات
تثبت العقد البنيوي: import-safe بلا pywebview، منفذ حر صالح،
رسالة الغياب الإرشادية، صفر تعديل على server.py، جاهزية wait.
"""
from __future__ import annotations

import pathlib
import socket
import subprocess
import sys
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "desktop.py"
SRC = DESKTOP.read_text(encoding="utf-8")


# ═══════════════ import-safe (بلا pywebview) ═══════════════

class TestImportSafe:

    def test_module_imports_without_pywebview(self):
        """الاستيراد لا يمس webview — التبعية الاختيارية كسولة داخل main()."""
        code = (
            "import sys\n"
            "assert 'webview' not in sys.modules\n"
            "import desktop\n"
            "assert 'webview' not in sys.modules, 'استيراد webview يجب أن يكون كسولًا'\n"
            "assert 'server' not in sys.modules, 'استيراد server يجب أن يكون كسولًا'\n"
            "print('OK')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True,
            text=True, cwd=str(ROOT), timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "OK"

    def test_missing_pywebview_message_is_guiding(self):
        """غياب pywebview ⇒ رسالة عربية إرشادية + إحالة لوضع المتصفح + رمز 1."""
        code = (
            "import sys, types\n"
            "class _Blocker:\n"
            "    def find_module(self, name, path=None):\n"
            "        return self if name == 'webview' else None\n"
            "    def load_module(self, name):\n"
            "        raise ImportError('blocked for test')\n"
            "sys.meta_path.insert(0, _Blocker())\n"
            "sys.argv = ['desktop.py']\n"
            "import desktop\n"
            "rc = desktop.main()\n"
            "print('RC', rc)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True,
            text=True, cwd=str(ROOT), timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        assert "RC 1" in proc.stdout
        assert "pip install pywebview" in proc.stdout
        assert "python server.py" in proc.stdout  # الإحالة لوضع المتصفح


# ═══════════════ المنفذ الحر والجاهزية ═══════════════

class TestNetworkingHelpers:

    def test_find_free_port_is_bindable(self):
        import desktop
        port = desktop.find_free_port()
        assert 1024 < port < 65536
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))  # حر فعلًا

    def test_wait_until_ready_true_on_live_http(self):
        import desktop
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class _H(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), _H)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            url = f"http://127.0.0.1:{srv.server_port}"
            assert desktop.wait_until_ready(url, timeout=5.0) is True
        finally:
            srv.shutdown()

    def test_wait_until_ready_false_on_dead_port(self):
        import desktop
        port = desktop.find_free_port()  # لا أحد يستمع عليه
        assert desktop.wait_until_ready(
            f"http://127.0.0.1:{port}", timeout=1.0) is False


# ═══════════════ عقد ADR-006 (فحص نصي) ═══════════════

class TestContract:

    def test_server_py_untouched_by_727(self):
        """صفر تعديل على server.py: لا ذكر لـ desktop/webview فيه."""
        server_src = (ROOT / "server.py").read_text(encoding="utf-8")
        assert "webview" not in server_src
        assert "desktop" not in server_src

    def test_launcher_binds_localhost_only(self):
        assert '"127.0.0.1"' in SRC
        assert '"0.0.0.0"' not in SRC  # لا تعريض شبكي في وضع سطح المكتب

    def test_launcher_reuses_server_main(self):
        assert "server.main" in SRC          # إعادة استخدام لا نسخ
        assert "create_window" in SRC
        assert "daemon=True" in SRC          # خيط الخادم لا يمنع الإنهاء
