# -*- coding: utf-8 -*-
"""HookRunner (TSK-728, CP-4): خطّافات المالك بعقد «تشديد-فقط».

لماذا توجد هذه الوحدة
---------------------
قسم ``hooks:`` اختياري في config.yaml يسمح للمالك بحقن فحوص إضافية عند
أحداث محددة (``pre_command`` / ``post_write`` / ``post_run``) — بعقد
صارم لا يقبل التفاوض:

1. الـ hook يستطيع **رفع الصرامة فقط**: حجب أمر قبل تنفيذه
   (``pre_command`` بخروج ≠ 0) أو تسجيل تحذير بعد فعلٍ وقع
   (``post_write`` / ``post_run``). لا توجد أي قناة يمنح بها الـ hook
   موافقة — ApprovalGate (core/approval.py) تبقى مصدر الحقيقة الوحيد.
2. **fail-closed** لـ ``pre_command``: استثناء أو مهلة أو خروج ≠ 0 من
   الـ hook ⇒ الأمر محجوب. الشك يُفسَّر منعًا لا سماحًا.
3. غياب قسم ``hooks:`` (أو كونه فارغًا/فاسدًا) ⇒ HookRunner فارغ ⇒
   **صفر subprocess** ⇒ سلوك المشروع حرفيًا كما قبل TSK-728.

شكل التهيئة في config.yaml::

    hooks:
      pre_command:
        - command: "python scripts/my_guard.py"
          timeout: 10
      post_write:
        - command: "python scripts/lint_on_write.py"

تُنفَّذ الخطّافات عبر ``subprocess.run`` **مباشرة** — أبدًا ليس عبر
CommandRunner (منع العودّية: hook يشغّل أمرًا يستدعي hooks...). حمولة
الحدث تصل للـ hook في متغيرات بيئة: ``HOOK_EVENT`` و``HOOK_COMMAND``
و``HOOK_PATH``.
"""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field

# الأحداث المدعومة — أي مفتاح آخر في hooks: يُتجاهَل مع تحذير عند البناء
VALID_EVENTS = frozenset({"pre_command", "post_write", "post_run"})

# مهلة افتراضية للخطّاف الواحد (ثوانٍ) — قابلة للضبط لكل hook عبر timeout
DEFAULT_TIMEOUT_SECONDS = 10.0

# سقف صلب للمهلة: hook معلّق لا يجوز أن يجمّد الخادم دقائق
MAX_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class HookSpec:
    """مواصفة خطّاف واحد كما وردت في config.yaml (بعد التحقق)."""

    command: str
    timeout: float = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class HookResult:
    """نتيجة تشغيل خطّاف واحد — سجل تدقيق لا قرار.

    ``ok`` تعني «الخطّاف مرّ» (خروج 0). القرار النهائي (حجب/تحذير)
    مسؤولية HookRunner حسب نوع الحدث، لا مسؤولية هذا السجل.
    """

    event: str
    command: str
    ok: bool
    detail: str = ""


def _parse_specs(raw: object) -> list[HookSpec]:
    """تحويل قائمة خام من config إلى HookSpec مُتحقَّق منها.

    تسامحية مع الشكل (مدخل فاسد يُسقَط) لأن config.yaml بيد المالك —
    لكن **غير** تسامحية وقت التشغيل (فشل hook صالح = fail-closed).
    """
    specs: list[HookSpec] = []
    if not isinstance(raw, list):
        return specs
    for item in raw:
        if not isinstance(item, dict):
            continue
        cmd = item.get("command")
        if not isinstance(cmd, str) or not cmd.strip():
            continue
        timeout_raw = item.get("timeout", DEFAULT_TIMEOUT_SECONDS)
        try:
            timeout = float(timeout_raw)
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT_SECONDS
        if timeout <= 0:
            timeout = DEFAULT_TIMEOUT_SECONDS
        timeout = min(timeout, MAX_TIMEOUT_SECONDS)
        specs.append(HookSpec(command=cmd.strip(), timeout=timeout))
    return specs


@dataclass
class HookRunner:
    """مشغّل الخطّافات — يُبنى مرة واحدة من config ويُحقن حيث يلزم.

    الاستخدام::

        runner = HookRunner.from_config(cfg)   # cfg = dict من config.yaml
        allowed, reason = runner.pre_command("pip install x")
        if not allowed: ...حجب...
        warnings = runner.post_write("src/app.py")
    """

    hooks: dict[str, list[HookSpec]] = field(default_factory=dict)
    audit: list[HookResult] = field(default_factory=list)

    # ──── البناء ────

    @classmethod
    def from_config(cls, cfg: object) -> "HookRunner":
        """بناء من جذر config.yaml — غياب/فساد القسم ⇒ runner فارغ."""
        hooks: dict[str, list[HookSpec]] = {}
        if isinstance(cfg, dict):
            section = cfg.get("hooks")
            if isinstance(section, dict):
                for event, raw in section.items():
                    if event not in VALID_EVENTS:
                        continue  # مفتاح غريب — يُتجاهَل (تشديد-فقط: لا مفاجآت)
                    specs = _parse_specs(raw)
                    if specs:
                        hooks[event] = specs
        return cls(hooks=hooks)

    @property
    def is_empty(self) -> bool:
        """True ⇒ صفر خطّافات ⇒ مسارات الحقن ترجع فورًا بلا subprocess."""
        return not self.hooks

    # ──── التنفيذ ────

    def _run_one(self, event: str, spec: HookSpec,
                 env_extra: dict[str, str]) -> HookResult:
        """تشغيل خطّاف واحد — لا يرمي أبدًا؛ يرجع HookResult دائمًا."""
        import os
        env = os.environ.copy()
        env["HOOK_EVENT"] = event
        env.update(env_extra)
        try:
            args = shlex.split(spec.command)
            if not args:
                return HookResult(event, spec.command, ok=False,
                                  detail="empty_command")
            proc = subprocess.run(  # noqa: S603 — أمر المالك من config.yaml
                args, capture_output=True, text=True,
                timeout=spec.timeout, env=env, shell=False,
            )
            ok = proc.returncode == 0
            detail = "" if ok else (
                f"exit={proc.returncode}: "
                f"{(proc.stderr or proc.stdout or '').strip()[:400]}"
            )
            result = HookResult(event, spec.command, ok=ok, detail=detail)
        except subprocess.TimeoutExpired:
            result = HookResult(event, spec.command, ok=False,
                                detail=f"timeout>{spec.timeout}s")
        except Exception as exc:  # فشل الإطلاق نفسه = فشل الخطّاف
            result = HookResult(event, spec.command, ok=False,
                                detail=f"{type(exc).__name__}: {exc}")
        self.audit.append(result)
        return result

    def pre_command(self, command: str) -> tuple[bool, str]:
        """فحص قبل تنفيذ أمر — **fail-closed**.

        Returns:
            (allowed, reason): ``allowed=False`` ⇒ على المستدعي حجب
            الأمر. ``reason`` رسالة عربية جاهزة للعرض/السجل.
        """
        for spec in self.hooks.get("pre_command", []):
            result = self._run_one("pre_command", spec,
                                   {"HOOK_COMMAND": command})
            if not result.ok:
                return False, (
                    f"⛔ حُجب الأمر بواسطة hook (تشديد-فقط، fail-closed): "
                    f"{spec.command} — {result.detail or 'خروج غير صفري'}"
                )
        return True, ""

    def post_write(self, path: str) -> list[str]:
        """إشعار بعد كتابة ملف — الفعل وقع؛ الفشل تحذير فقط."""
        warnings: list[str] = []
        for spec in self.hooks.get("post_write", []):
            result = self._run_one("post_write", spec, {"HOOK_PATH": path})
            if not result.ok:
                warnings.append(
                    f"⚠️ hook post_write أخفق: {spec.command} — "
                    f"{result.detail}"
                )
        return warnings

    def post_run(self, command: str, exit_code: int) -> list[str]:
        """إشعار بعد اكتمال تشغيل أمر — الفشل تحذير فقط."""
        warnings: list[str] = []
        for spec in self.hooks.get("post_run", []):
            result = self._run_one(
                "post_run", spec,
                {"HOOK_COMMAND": command, "HOOK_EXIT_CODE": str(exit_code)},
            )
            if not result.ok:
                warnings.append(
                    f"⚠️ hook post_run أخفق: {spec.command} — {result.detail}"
                )
        return warnings
