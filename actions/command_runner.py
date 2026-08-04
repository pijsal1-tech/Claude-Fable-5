# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  CommandRunner — تنفيذ أوامر الطرفية بأمان
  يطلب إذن المستخدم قبل تنفيذ الأوامر الخطرة
  يعيد المحاولة تلقائيًا عند الأخطاء المؤقتة (Timeout/OSError)
═══════════════════════════════════════════════════════
"""
import subprocess
import shlex
import os
import re
import time
import traceback
from datetime import datetime

# ── colorama (اختياري) ──
try:
    from colorama import Fore, Style
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = MAGENTA = WHITE = BLUE = ""
    class Style:
        BRIGHT = RESET_ALL = ""


# ── أوامر آمنة (لا تحتاج إذن) ──
SAFE_COMMANDS = {
    "ls", "dir", "cat", "type", "echo", "pwd", "cd",
    "node", "python", "python3", "py",
    "git status", "git log", "git diff", "git branch",
    "npm list", "npm ls",
}

# ── أوامر تحتاج إذن دائماً ──
DANGEROUS_COMMANDS = {
    "rm", "rmdir", "del", "format",
    "drop", "delete", "truncate",
    "sudo", "chmod", "chown",
}


class CommandRunner:
    """تنفيذ أوامر الطرفية مع طلب إذن وإعادة محاولة عند الأخطاء المؤقتة"""

    def __init__(self, cwd: str = ".", auto_approve: bool = False,
                 max_retries: int = 2, retry_delay: float = 1.5,
                 hook_runner=None):
        self.cwd = os.path.abspath(cwd)
        self.auto_approve = auto_approve
        # TSK-728b (CP-4): خطّافات المالك بعقد تشديد-فقط — None ⇒ سلوك
        # اليوم حرفيًا (صفر subprocess إضافي). راجع core/hooks.py.
        self.hook_runner = hook_runner
        self.max_retries = max_retries       # عدد إعادات المحاولة الإضافية (غير المحاولة الأولى)
        self.retry_delay = retry_delay       # ثواني قبل أول إعادة محاولة (يتضاعف تصاعديًا)
        self._history: list[dict] = []

    def run(self, command: str, timeout: int = 60, need_approval: bool = True,
            retries=None, retry_delay=None, retry_on_nonzero: bool = False,
            force_approval: bool = False) -> dict:
        """
        تنفيذ أمر — يطلب إذن إلا إذا كان آمن أو auto_approve=True.

        TSK-502 (NF-16) — ``force_approval=True``: بوابة الموافقة إلزامية
        لكل أمر مهما كان ``auto_approve``/``SAFE_COMMANDS``/``need_approval``
        (الافتراضي False = التوافق السلوكي الكامل). تستهلكه راية
        ``force_command_approval`` في config.yaml عبر مواضع REST/apply
        في server.py — حارس DANGEROUS_COMMANDS الساكن لم يعد الخط
        الوحيد عند تفعيلها.
        يعيد المحاولة تلقائيًا عند:
          - Timeout / OSError (أخطاء مؤقتة في النظام)
          - كود خروج غير صفري إذا retry_on_nonzero=True

        Returns:
            {"success": bool, "output": str, "error": str, "code": int,
             "attempts": int, "timestamp": str}
        """
        if not command or not command.strip():
            return self._build_entry(command, False, "", "أمر فارغ", -1, 0)

        # 1. Enforce list arguments format & parse command safely
        import shlex
        try:
            # shlex split handling Windows vs POSIX
            args = shlex.split(command, posix=(os.name != "nt"))
        except Exception as e:
            return self._build_entry(command, False, "", f"❌ خطأ في صيغة الأمر: {e}", -1, 0)

        if not args:
            return self._build_entry(command, False, "", "أمر فارغ", -1, 0)

        # 2. Prevent raw shells / check shell operators
        blocked_operators = {"&&", "||", "|", ";", ">", ">>", "<", "`", "$("}
        has_blocked = False
        for op in blocked_operators:
            if op in command:
                has_blocked = True
                break
        if has_blocked:
            return self._build_entry(command, False, "", "❌ خطأ: استخدام معاملات الطرفية (operators) مثل && أو | أو ; غير مسموح به للأمان.", -1, 0)

        # TSK-728b (CP-4): خطّاف pre_command — تشديد-فقط، fail-closed.
        # يسبق كل فحوص الموافقة: الـ hook يستطيع الحجب فقط ولا يملك أي
        # قناة لمنح موافقة — ApprovalGate/الفحوص أدناه تبقى كما هي.
        if self.hook_runner is not None:
            _hook_allowed, _hook_reason = self.hook_runner.pre_command(command)
            if not _hook_allowed:
                return self._build_entry(command, False, "", _hook_reason, -1, 0)

        # فحص الأمان
        is_dangerous = self._is_dangerous(command)
        is_safe = self._is_safe(command)

        if is_dangerous:
            print(f"\n{Fore.RED}⛔ أمر خطير: {command}{Style.RESET_ALL}")
            if not self._ask_approval(command):
                return self._build_entry(command, False, "", "رفض المستخدم", -1, 0)
        elif force_approval:
            # TSK-502 (NF-16): الراية مفعّلة ⇒ موافقة إلزامية حتى للآمن
            # وحتى مع auto_approve — لا تجاوز للبوابة إطلاقًا.
            if not self._ask_approval(command):
                return self._build_entry(command, False, "", "رفض المستخدم", -1, 0)
        elif need_approval and not is_safe and not self.auto_approve:
            if not self._ask_approval(command):
                return self._build_entry(command, False, "", "رفض المستخدم", -1, 0)

        max_attempts = (self.max_retries if retries is None else max(0, retries)) + 1
        delay = self.retry_delay if retry_delay is None else retry_delay

        # 3. Environment secrets redaction
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        
        sensitive_patterns = {"key", "secret", "password", "token", "auth", "jwt", "pass", "private", "credential"}
        for k in list(env.keys()):
            k_lower = k.lower()
            if any(pat in k_lower for pat in sensitive_patterns):
                if env[k]:
                    env[k] = "[REDACTED]"

        # Redact secrets in the command args if any value matches
        for k, v in os.environ.items():
            k_lower = k.lower()
            if any(pat in k_lower for pat in sensitive_patterns):
                if v and len(v) > 5:
                    args = [arg.replace(v, "[REDACTED]") for arg in args]
                    command = command.replace(v, "[REDACTED]")

        # Handle shell built-ins on Windows when running shell=False
        if os.name == "nt" and args[0].lower() in ("dir", "echo", "cls", "copy", "del", "move", "mkdir", "rmdir", "type"):
            args = ["cmd.exe", "/c"] + args

        last_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                result = subprocess.run(
                    args,
                    shell=False,
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                )
                success = result.returncode == 0
                entry = self._build_entry(
                    command, success, result.stdout.strip(), result.stderr.strip(),
                    result.returncode, attempt,
                )

                # TSK-728c (CP-4): خطّاف post_run — الفعل وقع؛ الفشل
                # تحذير فقط (لا حجب ولا تغيير للنتيجة). يُنادى عن كل
                # تنفيذ فعلي (بما فيه إعادات المحاولة — كل واحدة تشغيلة).
                if self.hook_runner is not None:
                    for _w in self.hook_runner.post_run(command,
                                                        result.returncode):
                        print(_w)

                if success or not retry_on_nonzero or attempt == max_attempts:
                    self._history.append(entry)
                    return entry

                last_error = entry["error"] or f"كود خروج {result.returncode}"

            except subprocess.TimeoutExpired:
                last_error = f"انتهى الوقت المحدد ({timeout}s)"
            except FileNotFoundError as e:
                # البرنامج/الأمر غير موجود — إعادة المحاولة لن تفيد
                entry = self._build_entry(command, False, "", f"البرنامج غير موجود: {e}", -1, attempt)
                self._history.append(entry)
                return entry
            except PermissionError as e:
                entry = self._build_entry(command, False, "", f"صلاحيات غير كافية: {e}", -1, attempt)
                self._history.append(entry)
                return entry
            except OSError as e:
                # خطأ نظام مؤقت (مثل نفاد الموارد) — يستحق إعادة محاولة
                last_error = f"خطأ نظام: {e}"
            except Exception as e:
                if os.environ.get("DEBUG"):
                    traceback.print_exc()
                entry = self._build_entry(command, False, "", f"{type(e).__name__}: {e}", -1, attempt)
                self._history.append(entry)
                return entry

            if attempt == max_attempts:
                entry = self._build_entry(command, False, "", last_error, -1, attempt)
                self._history.append(entry)
                return entry

            print(f"{Fore.YELLOW}⚠ المحاولة {attempt}/{max_attempts} فشلت: {last_error}")
            print(f"  إعادة المحاولة بعد {delay:.1f}s...{Style.RESET_ALL}")
            time.sleep(delay)
            delay *= 2  # exponential backoff

    def run_safe(self, command: str, timeout: int = 30, retries=None) -> dict:
        """تنفيذ بدون طلب إذن (للأوامر الآمنة فقط)"""
        return self.run(command, timeout=timeout, need_approval=False, retries=retries)

    def get_history(self) -> list[dict]:
        return self._history.copy()

    # ── أدوات داخلية ──
    def _build_entry(self, command: str, success: bool, output: str,
                      error: str, code: int, attempts: int) -> dict:
        return {
            "command": command,
            "success": success,
            "output": output,
            "error": error,
            "code": code,
            "attempts": attempts,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    def _first_word(self, command: str) -> str:
        """أول كلمة فعلية في الأمر (بعد تفكيك صحيح، لا substring)"""
        stripped = command.strip()
        if not stripped:
            return ""
        try:
            tokens = shlex.split(stripped, posix=(os.name != "nt"))
            return tokens[0].lower() if tokens else stripped.split()[0].lower()
        except ValueError:
            # علامات اقتباس غير مغلقة مثلاً
            return stripped.split()[0].lower()

    def _is_safe(self, command: str) -> bool:
        """
        يتحقق أن الأمر يطابق أحد الأوامر الآمنة تمامًا (أول كلمة)،
        لا مجرد بادئة نصية — لمنع أوامر مثل "catfile_delete.exe"
        من اعتبارها آمنة لأنها تبدأ بحروف "cat".
        """
        cmd_lower = command.strip().lower()
        first_word = self._first_word(command)
        for safe in SAFE_COMMANDS:
            if " " in safe:  # عبارات متعددة الكلمات مثل "git status"
                if cmd_lower.startswith(safe):
                    return True
            elif first_word == safe:
                return True
        return False

    def _is_dangerous(self, command: str) -> bool:
        """
        يبحث عن كلمات خطيرة بحدود كلمة كاملة (\\b) لا substring —
        لمنع أوامر مثل "warmup.sh" أو "chownership.py" من اعتبارها
        خطيرة غلط لمجرد احتواء الحروف "rm" أو "chown" داخل الاسم.
        """
        cmd_lower = command.strip().lower()
        for danger in DANGEROUS_COMMANDS:
            if re.search(rf"\b{re.escape(danger)}\b", cmd_lower):
                return True
        return False

    def _ask_approval(self, command: str) -> bool:
        """طلب إذن المستخدم"""
        print(f"\n{Fore.YELLOW}{'─'*50}")
        print("⚡ أمر يحتاج موافقتك:")
        print(f"{Fore.CYAN}  $ {command}")
        print(f"{Fore.YELLOW}{'─'*50}{Style.RESET_ALL}")

        try:
            answer = input(f"{Fore.GREEN}  تنفيذ؟ (y/n): {Style.RESET_ALL}").strip().lower()
            return answer in ("y", "yes", "نعم", "اه", "")
        except (KeyboardInterrupt, EOFError):
            print()
            return False