# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Crash Resume — T-044 (R-601)

  إحياء آلية الاستكمال الميتة: ‎``can_resume``/``load_state``
  (chain/executor.py) كانت بلا أي مستدعٍ إنتاجي — هذه الوحدة
  تعطيها مستدعيها الأول.

  ── Resume Runbook ─────────────────────────────────────
  1. **الاكتشاف (startup scan):** عند إقلاع السيرفر يُفحص
     ``runs_dir`` عبر ``scan_resumable`` — أي run حالته في
     ‎``state.json`` غير نهائية (``running`` = انهيار منتصف
     التنفيذ، ``failed`` = توقّف قابل للإعادة) يُدرج ويُطبع.
     من الواجهة: رسالة WS ‏``resume_scan`` ترجع إطار
     ``resumable_runs``.
  2. **الاستكمال:** رسالة WS ‏``resume_run`` ‏(+‏``run_id``).
     المسار: تحقق انشغال → ``can_resume`` → ``load_state`` →
     **تحقق الانجراف** → ``rebuild_run`` → تنفيذ عبر نفس مسار
     ``start_chain`` (نفس الأحداث، نفس البوابة، نفس التذكرة).
  3. **تحقق الانجراف (drift):** بصمات ``project_snapshot.
     relevant_file_hashes`` (sha256 حقيقية — T-033/R-305)
     تُقارن ببصمات الملفات الحالية على القرص. أي ملف متغيّر
     أو مفقود ⇒ **رفض** بإطار ``chain_resume_refused`` يحمل
     تقرير الانجراف الكامل (matched/changed/missing) — لا
     استكمال أعمى ضد ملفات تغيّرت. البديل بعد الرفض: discard.
  4. **exactly-once:** ‏``rebuild_run`` يعيد الخطوات الناجحة
     بحالتها ونتائجها (من ``results``)، ويعيد ضبط غير الناجح
     (``running``/``error``/``skipped``) إلى ``pending`` —
     ‏``get_ready_steps`` بعدها لا يرشّح إلا المتبقي، فالخطوات
     المكتملة لا تُنفَّذ ثانية أبدًا.
  5. **الميزانية:** تُبنى ميزانية جديدة من الـ policy للرِجل
     المستأنفة (قرار واعٍ — العدّادات القديمة في state.json
     للتدقيق، والاستكمال يستحق نافذته الخاصة).
  6. **التنظيف (discard):** رسالة WS ‏``discard_run`` تحذف
     مجلد الـ run بالكامل — بعدها ``can_resume`` = False
     ويختفي من ``scan_resumable``.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass, field

from .executor import ChainExecutor
from .models import (
    ChainRun, ChainStep, ExecutionPolicy,
    ProviderSnapshot, ProjectSnapshot,
)


# ═══════════════════════════════════════════════════════
#   Drift Report
# ═══════════════════════════════════════════════════════

@dataclass(frozen=True)
class DriftReport:
    """نتيجة مقارنة بصمات اللقطة ببصمات القرص الحالية."""
    matched: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.changed or self.missing)

    def to_dict(self) -> dict:
        return {
            "matched": list(self.matched),
            "changed": list(self.changed),
            "missing": list(self.missing),
            "has_drift": self.has_drift,
        }


def _hash_text(content: str) -> str:
    """نفس دالة بصمة اللقطة حرفيًّا (bridge._build_project_snapshot)."""
    return hashlib.sha256(
        content.encode("utf-8", errors="replace")).hexdigest()


def check_drift(project_snapshot: dict | None,
                project_root: str) -> DriftReport:
    """يقارن بصمات اللقطة المحفوظة بمحتوى الملفات الحالي على القرص.

    - مفتاح اللقطة قد يكون نسبيًّا (يُحلّ على project_root) أو مطلقًا.
    - ملف غير قابل للقراءة/غير موجود ⇒ ``missing``.
    - بصمة مختلفة ⇒ ``changed``.
    - لقطة غائبة أو فارغة ⇒ لا شيء نتحقق منه ⇒ تقرير فارغ (لا انجراف).
    """
    matched: list[str] = []
    changed: list[str] = []
    missing: list[str] = []

    hashes = (project_snapshot or {}).get("relevant_file_hashes") or {}
    root = pathlib.Path(project_root) if project_root else None

    for rel_path, saved_hash in hashes.items():
        p = pathlib.Path(rel_path)
        if not p.is_absolute() and root is not None:
            p = root / rel_path
        try:
            current = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing.append(rel_path)
            continue
        if _hash_text(current) == saved_hash:
            matched.append(rel_path)
        else:
            changed.append(rel_path)

    return DriftReport(matched=matched, changed=changed, missing=missing)


# ═══════════════════════════════════════════════════════
#   Run Reconstruction
# ═══════════════════════════════════════════════════════

def _step_from_dict(d: dict) -> ChainStep:
    """يعيد بناء ChainStep من قاموس state.json (عكس to_dict + prompt_template)."""
    return ChainStep(
        id=d.get("id", ""),
        name=d.get("name", ""),
        stage=d.get("stage", ""),
        agent_role=d.get("agent_role", ""),
        prompt_template=d.get("prompt_template", ""),
        depends_on=list(d.get("depends_on", [])),
        context_policy=d.get("context_policy", "selective"),
        critical=bool(d.get("critical", True)),
        status=d.get("status", "pending"),
        error_message=d.get("error_message", ""),
        duration_ms=int(d.get("duration_ms", 0)),
        provider_calls=int(d.get("provider_calls", 0)),
    )


def rebuild_run(state: dict) -> ChainRun:
    """يعيد بناء ChainRun قابل للتنفيذ من state.json.

    عقد exactly-once:
    - خطوة ``success`` تبقى success ونتيجتها تُسترد من ``results``
      ⇒ لن ينفّذها ``get_ready_steps`` ثانية أبدًا.
    - خطوة غير نهائية-ناجحة (``running`` وقت الانهيار، ``error``،
      ``skipped``) تُعاد إلى ``pending`` بمسح رسالة الخطأ ⇒ تُنفَّذ
      في الرِجل المستأنفة مرة واحدة.
    - حالة الـ run تعود ``pending`` (المنفّذ ينقلها running بنفسه).
    - الميزانية جديدة من الـ policy (تُبنى في ``__post_init__``).
    """
    steps = [_step_from_dict(d) for d in state.get("steps", [])]
    results = dict(state.get("results", {}))

    for step in steps:
        if step.status == "success":
            step.result = results.get(step.id, step.result)
        else:
            step.status = "pending"
            step.error_message = ""

    run = ChainRun(
        run_id=state.get("run_id", ""),
        steps=steps,
        policy=ExecutionPolicy.from_dict(state.get("policy") or {}),
        status="pending",
    )
    run.results = results

    ps = state.get("provider_snapshot")
    if ps:
        run.provider_snapshot = ProviderSnapshot(
            provider_name=ps.get("provider_name", ""),
            model_name=ps.get("model_name"),
            configuration_hash=ps.get("configuration_hash", ""),
            capabilities_snapshot=dict(ps.get("capabilities_snapshot") or {}),
        )
    proj = state.get("project_snapshot")
    if proj:
        run.project_snapshot = ProjectSnapshot(
            project_root=proj.get("project_root", ""),
            project_id=proj.get("project_id", ""),
            relevant_file_hashes=dict(proj.get("relevant_file_hashes") or {}),
        )

    return run


# ═══════════════════════════════════════════════════════
#   Startup / On-demand Scan
# ═══════════════════════════════════════════════════════

def scan_resumable(runs_dir: str | pathlib.Path) -> list[dict]:
    """يمسح ``runs_dir`` ويرجع ملخص كل run قابل للاستكمال.

    ``ChainExecutor.can_resume`` هو الحكم (state.json موجود وحالته
    غير نهائية) — أول مستدعٍ إنتاجي له (R-601).
    """
    root = pathlib.Path(runs_dir)
    if not root.is_dir():
        return []

    found: list[dict] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if not ChainExecutor.can_resume(child):
            continue
        state = ChainExecutor.load_state(child)
        if state is None:
            continue
        steps = state.get("steps", [])
        found.append({
            "run_id": state.get("run_id", child.name),
            "status": state.get("status", ""),
            "steps_done": sum(1 for s in steps if s.get("status") == "success"),
            "steps_total": len(steps),
            "started_at": state.get("started_at", 0),
        })
    return found
