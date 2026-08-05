# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ACP Agent Process — دورة حياة عملية الوكيل الخارجي
  TSK-736b (القرار 8 من تسلسل D-19)

  يملك subprocess الوكيل ويربط stdio بـ ``AcpConnection``:
  spawn → initialize (بمهلة) → session/new → session/prompt →
  shutdown (terminate ثم kill — سابقة agent_tools
  ``_TIMEOUT_GRACE_SECONDS``: عملية معلّقة لا تُنتظر للأبد).

  **الأمر من config حصرًا** (القرار الواعي 4): ``command`` +
  ``args`` يكتبهما المالك بيده في ``acp.agents`` — سابقة hooks
  TSK-728 (``noqa: S603`` موثَّق هناك بنفس التعليل)؛ لا يمر عبر
  CommandPolicy لأنه ليس أمرًا اقترحه وكيل. لكن العملية **لا ترث**
  أي صلاحية كتابة: كتاباتها الوحيدة عبر GovernedFsHandler المُبوَّب.

  **الفصل الاختباري** (القرار الواعي 5): كل المنطق البروتوكولي في
  AcpConnection/GovernedFsHandler يُختبَر بـ FakeTransport؛ هذه
  الوحدة تُختبَر بوكيل دمية بايثون محلي (tests/fixtures) في اختبار
  التكامل فقط — لا تنزيل ولا شبكة أبدًا.

  **fail-closed**: فشل spawn/initialize ⇒ ``AcpAgentUnavailable``؛
  موت العملية أثناء الجلسة ⇒ AcpConnectionClosed من طبقة الاتصال
  (EOF يوقظ المنتظرين — 736a)؛ stderr يُصرَّف إلى DEVNULL (ضجيج
  وكيل خارجي ليس قناة بروتوكول ولا يُخزَّن).
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import pathlib
import subprocess
import threading
from typing import IO, Any, Callable

from .connection import AcpConnection, AcpError, Notification, Request

logger = logging.getLogger(__name__)

INITIALIZE_TIMEOUT = 20.0
SHUTDOWN_GRACE_SECONDS = 2.0   # سابقة agent_tools._TIMEOUT_GRACE_SECONDS
PROTOCOL_VERSION = 1


class AcpAgentUnavailable(AcpError):
    """تعذّر تشغيل/تهيئة الوكيل — الرسالة بلا تفاصيل بيئة."""


class _PipeTransport:
    """غلاف stdio العملية الفرعية بعقد Transport (736a).

    القراءة/الكتابة نصية UTF-8 (errors=replace — ضجيج بايتات لا
    يقتل الضخ؛ parse_line يتكفل برفض غير المفهوم fail-closed).
    """

    def __init__(self, stdin: IO[str], stdout: IO[str]) -> None:
        self._stdin = stdin
        self._stdout = stdout
        self._write_lock = threading.Lock()

    def read_line(self) -> str | None:
        try:
            line = self._stdout.readline()
        except (OSError, ValueError):
            return None
        if line == "":       # EOF — العملية أغلقت stdout/ماتت
            return None
        return line.rstrip("\r\n")

    def write_line(self, line: str) -> None:
        with self._write_lock:
            try:
                self._stdin.write(line + "\n")
                self._stdin.flush()
            except (OSError, ValueError):
                # الأنبوب انكسر — طبقة الاتصال ستلاحظ EOF في الضخ
                raise


class AcpAgentProcess:
    """عملية وكيل ACP واحدة بدورة حياة كاملة.

    Args:
        command: أمر التشغيل (المالك كتبه في config — القرار 4).
        args: وسائطه.
        cwd: مجلد العمل (workspace عادةً).
        on_request: معالج الطلبات العكسية (GovernedFsHandler).
        on_notification: معالج الإشعارات (بث session/update — 736c).
        request_timeout: مهلة انتظار ردود الوكيل.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: str | pathlib.Path | None = None,
        on_request: Callable[[Request], Any] | None = None,
        on_notification: Callable[[Notification], None] | None = None,
        request_timeout: float = 60.0,
    ) -> None:
        self._command = command
        self._args = list(args or [])
        self._cwd = str(cwd) if cwd else None
        self._on_request = on_request
        self._on_notification = on_notification
        self._request_timeout = request_timeout

        self._proc: subprocess.Popen[str] | None = None
        self._conn: AcpConnection | None = None
        self._pump_thread: threading.Thread | None = None
        self._init_result: dict[str, Any] | None = None

    # ─── دورة الحياة ───

    def start(self) -> dict[str, Any]:
        """spawn + initialize بمهلة — يرفع AcpAgentUnavailable عند الفشل."""
        if self._proc is not None:
            raise AcpAgentUnavailable("الوكيل يعمل بالفعل")
        try:
            # أمر المالك من config حرفيًا (سابقة hooks TSK-728)
            self._proc = subprocess.Popen(  # noqa: S603
                [self._command, *self._args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,   # ضجيج — ليس قناة بروتوكول
                cwd=self._cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,                   # line-buffered
            )
        except OSError as exc:
            # لا نردّد الأمر/المسار في الرسالة (قد يحمل تفاصيل بيئة)
            raise AcpAgentUnavailable(
                f"تعذّر تشغيل الوكيل ({type(exc).__name__})")
        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        transport = _PipeTransport(self._proc.stdin, self._proc.stdout)
        self._conn = AcpConnection(
            transport,
            on_request=self._on_request,
            on_notification=self._on_notification,
            timeout_seconds=self._request_timeout,
        )
        self._pump_thread = threading.Thread(
            target=self._conn.pump_forever,
            name="acp-pump",
            daemon=True,
        )
        self._pump_thread.start()
        try:
            result = self._conn.request(
                "initialize",
                {"protocolVersion": PROTOCOL_VERSION},
                timeout=INITIALIZE_TIMEOUT,
            )
        except AcpError as exc:
            self.stop()
            raise AcpAgentUnavailable(
                f"فشلت تهيئة الوكيل ({type(exc).__name__})")
        self._init_result = result if isinstance(result, dict) else {}
        return dict(self._init_result)

    def stop(self) -> None:
        """إيقاف نظيف: إغلاق stdin ⇒ مهلة ⇒ terminate ⇒ مهلة ⇒ kill
        (fail-closed — لا انتظار أبديًّا لعملية معلّقة)."""
        conn, proc = self._conn, self._proc
        self._conn, self._proc = None, None
        if conn is not None:
            conn.close()
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            proc.wait(timeout=SHUTDOWN_GRACE_SECONDS)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=SHUTDOWN_GRACE_SECONDS)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.kill()
        try:
            proc.wait(timeout=SHUTDOWN_GRACE_SECONDS)
        except subprocess.TimeoutExpired:  # pragma: no cover — kill لا يفشل عمليًا
            logger.error("acp: العملية لم تمت حتى بعد kill")

    # ─── الجلسة ───

    @property
    def alive(self) -> bool:
        return (self._proc is not None and self._proc.poll() is None
                and self._conn is not None and not self._conn.closed)

    def new_session(self, workspace_root: str = "") -> str:
        """session/new — يعيد معرّف الجلسة (سلسلة، fail-closed لغير dict)."""
        conn = self._require_conn()
        result = conn.request("session/new",
                              {"cwd": workspace_root} if workspace_root else {})
        if isinstance(result, dict) and isinstance(result.get("sessionId"),
                                                   str):
            return result["sessionId"]
        return ""

    def prompt(self, session_id: str, text: str,
               timeout: float | None = None) -> Any:
        """session/prompt — الرد النهائي؛ البث يصل عبر on_notification."""
        conn = self._require_conn()
        return conn.request(
            "session/prompt",
            {"sessionId": session_id,
             "prompt": [{"type": "text", "text": text}]},
            timeout=timeout,
        )

    def _require_conn(self) -> AcpConnection:
        if self._conn is None or self._conn.closed:
            raise AcpAgentUnavailable("الوكيل غير مهيأ أو مات")
        return self._conn
