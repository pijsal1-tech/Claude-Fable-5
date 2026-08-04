# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ActionApplier — تطبيق نتائج Chain تلقائياً

  يسد الفجوة بين Chain System (الذي يحفظ النتائج كنص)
  و FileManager (الذي يطبق التعديلات على الملفات).

  يأخذ ناتج كل chain step → يحلله بـ ResponseParser →
  يطبق الـ FILE/EDIT/CMD actions.

  يُستخدم من:
  - ChainExecutor: بعد كل step ناجح
  - server.py: عند chain_finished
═══════════════════════════════════════════════════════
"""
import time
from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING
from core.structured_log import swallowed as _slog_swallowed

if TYPE_CHECKING:
    from actions.file_manager import FileManager
    from actions.command_runner import CommandRunner
    from actions.response_parser import ResponseParser
    from core.checkpoint import CheckpointManager


# ═══════════════════════════════════════════════════════
#   Action Result
# ═══════════════════════════════════════════════════════

@dataclass
class ActionResult:
    """نتيجة تطبيق إجراء واحد"""
    action_type: str       # create_file | edit_file | run_command
    path: str = ""         # مسار الملف (أو الأمر)
    success: bool = True
    error: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "path": self.path,
            "success": self.success,
            "error": self.error,
            **self.details,
        }


@dataclass
class ApplyResult:
    """نتيجة تطبيق كل الإجراءات من step واحد"""
    step_id: str
    total_actions: int = 0
    applied: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[ActionResult] = field(default_factory=list)
    parsed_summary: str = ""
    duration_ms: int = 0

    @property
    def success(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "total_actions": self.total_actions,
            "applied": self.applied,
            "failed": self.failed,
            "skipped": self.skipped,
            "parsed_summary": self.parsed_summary,
            "duration_ms": self.duration_ms,
            "results": [r.to_dict() for r in self.results],
        }


# ═══════════════════════════════════════════════════════
#   ActionApplier
# ═══════════════════════════════════════════════════════

class ActionApplier:
    """
    يحلل ناتج AI step ويطبق الـ actions على الملفات.

    الاستخدام:
        applier = ActionApplier(parser, file_manager, cmd_runner)
        result = applier.apply_step("step_1", ai_response_text)
        # result.applied == 3, result.failed == 0
    """

    def __init__(self,
                 parser: "ResponseParser",
                 file_manager: "FileManager | None" = None,
                 command_runner: "CommandRunner | None" = None,
                 auto_backup: bool = True,
                 on_action: Callable[[ActionResult], None] | None = None,
                 ctx=None):
        """
        Args:
            parser: ResponseParser لاستخراج FILE/EDIT/CMD
            file_manager: FileManager لتطبيق الملفات
            command_runner: CommandRunner لتنفيذ الأوامر
            auto_backup: هل يعمل backup تلقائي قبل التعديل
            on_action: callback بعد كل إجراء
            ctx: AppContext — لو موجود، fm/cmd يُحلّان وقت الاستدعاء (R-102)
        """
        self._parser = parser
        # R-102 (T-007) — pattern: "resolve at call time". With ctx set,
        # _fm/_cmd are properties reading ctx.project.* per access; the
        # static args remain a fallback for ctx-less construction.
        self._ctx = ctx
        self._static_fm = file_manager
        self._static_cmd = command_runner
        self._auto_backup = auto_backup
        self._on_action = on_action
        self._backup_done = False

    @property
    def _fm(self):
        if self._ctx is not None:
            return self._ctx.project.fm
        return self._static_fm

    @property
    def _cmd(self):
        if self._ctx is not None:
            return self._ctx.project.cmd_runner
        return self._static_cmd

    def apply_step(self, step_id: str, ai_response: str,
                   dry_run: bool = False, run_id: str = "",
                   checkpoint: "CheckpointManager | None" = None) -> ApplyResult:
        """
        يحلل ناتج AI step ويطبق الإجراءات.

        Args:
            step_id: معرف الخطوة
            ai_response: نص رد AI الكامل
            dry_run: لو True — يحلل بس ولا يطبق
            run_id: معرف الـ run — مفتاح الـ checkpoint (T-054, R-106)
            checkpoint: CheckpointManager — لو موجود مع run_id، تُلتقط
                snapshot لحالة ملفات الـ batch **قبل** أي كتابة وseal
                بعدها — rollback_run/rollback_file يستعيدان منها.

        Returns:
            ApplyResult مع تفاصيل كل إجراء
        """
        start = time.monotonic()

        # ── 1. تحليل الرد ──
        parsed = self._parser.parse(ai_response)
        result = ApplyResult(
            step_id=step_id,
            parsed_summary=parsed.summary(),
        )

        # ── 2. جمع الإجراءات ──
        actions = []
        for fb in parsed.files:
            actions.append({
                "type": "create_file",
                "path": fb.path,
                "content": fb.content,
                "language": fb.language,
            })
        for eb in parsed.edits:
            actions.append({
                "type": "edit_file",
                "path": eb.path,
                "old_text": eb.old_text,
                "new_text": eb.new_text,
            })
        for cb in parsed.commands:
            actions.append({
                "type": "run_command",
                "command": cb.command,
            })

        result.total_actions = len(actions)

        if not actions:
            result.duration_ms = int((time.monotonic() - start) * 1000)
            return result

        # ── 2.5 Checkpoint: snapshot ما-قبل-الكتابة (T-054, R-106) ──
        # كل مسارات الملفات تُلتقط قبل أول كتابة؛ الأوامر لا تُلتقط.
        ckpt_paths: list = []
        if checkpoint is not None and run_id and not dry_run:
            from chain.path_policy import resolve_workspace_path
            _fm_root = getattr(self._fm, "root", None)
            for a in actions:
                _p = a.get("path")
                if not _p or _fm_root is None:
                    continue
                try:
                    ckpt_paths.append(resolve_workspace_path(
                        _fm_root, _p, must_exist=False, allow_symlinks=False))
                except Exception:
                    continue  # مسار مرفوض — الكتابة نفسها ستفشل بنفس السبب
            if ckpt_paths:
                try:
                    checkpoint.snapshot(run_id, ckpt_paths)
                except Exception:
                    ckpt_paths = []  # فشل snapshot لا يمنع الـ apply (الباك-أب موجود)

        # ── 3. Backup تلقائي (مرة واحدة لكل batch) ──
        if self._auto_backup and not self._backup_done and self._fm and not dry_run:
            try:
                self._fm.backup_all()
                self._backup_done = True
            except Exception as _exc:
                _slog_swallowed("chain/action_applier.py:214", _exc)
                pass  # مش حرج

        # ── 4. تطبيق الإجراءات ──
        for action in actions:
            if dry_run:
                ar = ActionResult(
                    action_type=action["type"],
                    path=action.get("path", action.get("command", "")),
                    success=True,
                    details={"dry_run": True},
                )
                result.results.append(ar)
                result.skipped += 1
                continue

            ar = self._apply_action(action)
            result.results.append(ar)
            if ar.success:
                result.applied += 1
            else:
                result.failed += 1

            # Callback
            if self._on_action:
                try:
                    self._on_action(ar)
                except Exception as _exc:
                    _slog_swallowed("chain/action_applier.py:241", _exc)
                    pass

        # ── 4.5 Checkpoint: seal ما-بعد-الكتابة (T-054, R-106) ──
        # hash ما-بعد-الكتابة يثبت لاحقًا أن الملف لم يُعدَّل خارجيًا،
        # والـ blob المخزّن يتيح عرض diff قبل/بعد من المخزن وحده.
        if checkpoint is not None and ckpt_paths:
            try:
                checkpoint.seal(run_id, ckpt_paths)
            except Exception as _exc:
                _slog_swallowed("chain/action_applier.py:250", _exc)
                pass  # فشل الـ seal يجعل rollback يرفض بأمان — لا كسر للـ apply

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def apply_chain_results(self, step_results: dict[str, str],
                            dry_run: bool = False) -> list[ApplyResult]:
        """
        يطبق نتائج كل خطوات Chain دفعة واحدة.

        Args:
            step_results: {step_id: ai_response_text}

        Returns:
            list of ApplyResult لكل step
        """
        self._backup_done = False  # reset per chain
        results = []
        for step_id, response_text in step_results.items():
            result = self.apply_step(step_id, response_text, dry_run)
            results.append(result)
        return results

    def get_parsed_actions(self, ai_response: str) -> list[dict]:
        """
        يرجع الإجراءات بدون تطبيق — للعرض في الواجهة.
        """
        parsed = self._parser.parse(ai_response)
        actions = []
        for fb in parsed.files:
            actions.append({
                "action": "create_file",
                "path": fb.path,
                "content": fb.content,
                "language": fb.language,
            })
        for eb in parsed.edits:
            actions.append({
                "action": "edit_file",
                "path": eb.path,
                "old_text": eb.old_text,
                "new_text": eb.new_text,
            })
        for cb in parsed.commands:
            actions.append({
                "action": "run_command",
                "command": cb.command,
            })
        return actions

    # ═══════════════════════════════════════════════════
    #   Internal: Apply Single Action
    # ═══════════════════════════════════════════════════

    def _apply_action(self, action: dict) -> ActionResult:
        """يطبق إجراء واحد"""
        action_type = action["type"]

        if action_type == "create_file":
            return self._apply_create_file(action)
        elif action_type == "edit_file":
            return self._apply_edit_file(action)
        elif action_type == "run_command":
            return self._apply_run_command(action)
        else:
            return ActionResult(
                action_type=action_type,
                success=False,
                error=f"نوع إجراء غير معروف: {action_type}",
            )

    def _apply_create_file(self, action: dict) -> ActionResult:
        """إنشاء/كتابة ملف"""
        path = action.get("path", "")
        content = action.get("content", "")

        if not self._fm:
            return ActionResult(
                action_type="create_file", path=path,
                success=False, error="FileManager غير متاح",
            )

        try:
            self._fm.write_file(path, content)
            return ActionResult(
                action_type="create_file", path=path,
                success=True,
                details={"size": len(content)},
            )
        except Exception as e:
            return ActionResult(
                action_type="create_file", path=path,
                success=False, error=str(e),
            )

    def _apply_edit_file(self, action: dict) -> ActionResult:
        """تعديل جراحي"""
        path = action.get("path", "")
        old_text = action.get("old_text", "")
        new_text = action.get("new_text", "")

        if not self._fm:
            return ActionResult(
                action_type="edit_file", path=path,
                success=False, error="FileManager غير متاح",
            )

        try:
            result = self._fm.apply_edit(path, old_text, new_text)
            return ActionResult(
                action_type="edit_file", path=path,
                success=result.get("ok", False),
                error=result.get("error", ""),
                details=result,
            )
        except Exception as e:
            return ActionResult(
                action_type="edit_file", path=path,
                success=False, error=str(e),
            )

    def _apply_run_command(self, action: dict) -> ActionResult:
        """تنفيذ أمر"""
        command = action.get("command", "")

        if not self._cmd:
            return ActionResult(
                action_type="run_command", path=command,
                success=False, error="CommandRunner غير متاح",
            )

        try:
            result = self._cmd.run(command)
            return ActionResult(
                action_type="run_command", path=command,
                success=result.get("exit_code", 1) == 0,
                details={
                    "exit_code": result.get("exit_code"),
                    "output_length": len(result.get("output", "")),
                },
            )
        except Exception as e:
            return ActionResult(
                action_type="run_command", path=command,
                success=False, error=str(e),
            )
