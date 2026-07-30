#!/usr/bin/env python3
"""desktop.py — مُطلِق سطح المكتب (TSK-727b — ADR-006).

يشغّل خادم Flask القائم (server.main) في خيط خلفي على منفذ حر، ثم
يفتح نافذة WebView أصلية (pywebview) على العنوان المحلي. إغلاق
النافذة يُنهي العملية.

العقد (ADR-006):
- صفر تعديل على server.py — إعادة استخدام main() كما هي.
- pywebview تبعية اختيارية: غيابها ⇒ رسالة عربية إرشادية + الإحالة
  لوضع المتصفح (python server.py) — المسار الأول غير المُمَسّ.
- التحقق التشغيلي النهائي على Windows بيد المالك (D-8-ب —
  docs/desktop/OWNER_CHECKLIST.md).

الاستخدام:  python desktop.py [--project MSAR]
"""
from __future__ import annotations

import os
import signal
import socket
import sys
import threading
import time
import urllib.request

APP_TITLE = "WebDev AI Editor"
_READY_TIMEOUT_S = 30.0


def find_free_port() -> int:
    """منفذ TCP حر من نظام التشغيل (bind على 0)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _patch_signal_for_thread() -> None:
    """server.main() يسجّل SIGTERM/SIGINT — وهذا يرفع ValueError خارج
    الخيط الرئيسي. نغلّف signal.signal بغلاف يبتلع هذه الحالة حصريًا
    (الإنهاء هنا مسؤولية النافذة لا الإشارات) — دون لمس server.py."""
    original = signal.signal

    def _safe_signal(signalnum, handler):  # type: ignore[no-untyped-def]
        try:
            return original(signalnum, handler)
        except ValueError:  # ليس في الخيط الرئيسي — متوقع ومقبول هنا
            return None

    signal.signal = _safe_signal  # type: ignore[assignment]


def start_server_thread(port: int, project: str) -> threading.Thread:
    """تشغيل server.main() بخيط خلفي على المنفذ المحدد."""
    # argparse داخل main() يقرأ sys.argv — نضبطه قبل الإقلاع.
    sys.argv = [
        "server.py",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--project", project,
    ]
    _patch_signal_for_thread()
    import server  # استيراد كسول: بعد ضبط argv وقبل الخيط

    th = threading.Thread(target=server.main, name="flask-server", daemon=True)
    th.start()
    return th


def wait_until_ready(url: str, timeout: float = _READY_TIMEOUT_S) -> bool:
    """انتظار جاهزية الخادم (استطلاع HTTP) قبل فتح النافذة."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def main() -> int:
    try:
        import webview  # pywebview — تبعية اختيارية (ADR-006)
    except ImportError:
        print(
            "❌ pywebview غير مثبَّتة — وضع سطح المكتب يتطلبها.\n"
            "   التثبيت:  pip install pywebview\n"
            "   أو استخدم وضع المتصفح (المسار الأول):  python server.py"
        )
        return 1

    # --project تُمرَّر كما هي لوضع المتصفح؛ الافتراضي المجلد الحالي.
    project = "."
    argv = sys.argv[1:]
    if "--project" in argv:
        idx = argv.index("--project")
        if idx + 1 < len(argv):
            project = argv[idx + 1]

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    start_server_thread(port, project)

    if not wait_until_ready(url):
        print(f"❌ الخادم لم يجهز خلال {_READY_TIMEOUT_S:.0f} ثانية — إنهاء.")
        return 2

    webview.create_window(APP_TITLE, url, width=1280, height=800)
    webview.start()          # يحجز حتى إغلاق النافذة
    os._exit(0)              # إنهاء فوري: خيط الخادم daemon


if __name__ == "__main__":
    raise SystemExit(main())
