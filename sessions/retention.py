# -*- coding: utf-8 -*-
"""RetentionPolicy — دورة حياة صادقة لـ artifacts الـ runs (R-305 / T-033).

المشكلة: مجلدات الـ runs (``.ai_runs/run-*``) تتراكم للأبد — «مقبرة
artifacts للكتابة فقط». جلسات المحادثة لها TTL (30 يومًا في
SessionManager)، أما آثار الـ runs فبلا أي سياسة.

هنا: ``RetentionPolicy`` (أقصى عدد / أقصى عمر / مثبتات) يطبَّق بمسح
``sweep()`` — يُستدعى عند الإقلاع (startup GC pass). أول إصدار يعمل
**dry-run افتراضيًّا** (بند مخاطر R-305: «حذف artifacts أرادها
المستخدم» — السياسة مرئية في config ومع تسجيل dry-run أولًا):
المسح يسجّل ما *كان سيُحذف* دون حذف فعلي حتى يفعّل المستخدم
``retention.dry_run: false``.

**دلالات الإبقاء (بترتيب التفوق):**

1. **المثبت** (``pinned``): ينجو دائمًا — فوق العدد وفوق العمر.
2. ``max_count``: أحدث N عناصر تبقى (بترتيب mtime تنازليًّا؛
   المثبتات لا تستهلك من العدّ — تفوقها لا يُزاحم غيرها).
3. ``max_age_days``: ما تجاوز العمر يسقط حتى لو داخل العدد.
   (العنصر يبقى فقط إذا نجا من **كلا** الحدّين المفعّلين.)
4. حدّ None = غير مفعّل. سياسة بلا أي حد مفعّل = لا حذف أبدًا.

المسح **idempotent**: تشغيله مرتين متتاليتين يعطي نفس البقايا،
والثاني لا يجد شيئًا يحذفه.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class RetentionPolicy:
    """سياسة الاستبقاء — الحدود None = غير مفعّلة (لا حذف من هذا النوع).

    ``pinned``: أسماء عناصر (basename لمجلد الـ run) تنجو دائمًا.
    ``dry_run``: True (الافتراضي الآمن) = تسجيل فقط، لا حذف فعلي.
    """
    max_count: Optional[int] = None
    max_age_days: Optional[float] = None
    pinned: frozenset[str] = frozenset()
    dry_run: bool = True

    def __post_init__(self) -> None:
        if self.max_count is not None and self.max_count < 0:
            raise ValueError("max_count لا يكون سالبًا")
        if self.max_age_days is not None and self.max_age_days < 0:
            raise ValueError("max_age_days لا يكون سالبًا")


@dataclass(frozen=True)
class SweepReport:
    """نتيجة مسح — ما بقي وما حُذف (أو كان سيُحذف تحت dry-run)."""
    kept: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    dry_run: bool = True

    @property
    def would_delete(self) -> list[str]:
        """اسم أصدق لقائمة الحذف تحت dry-run."""
        return self.deleted


def plan_sweep(entries: list[tuple[str, float]], policy: RetentionPolicy,
               now: Optional[float] = None) -> tuple[list[str], list[str]]:
    """نواة القرار النقية: (name, mtime) ⇒ (kept, deleted) — بلا I/O.

    قابلة للاختبار المصفوفي مباشرة (بند R-305: policy matrix).
    الترتيب داخل القائمتين: الأحدث أولًا.
    """
    now = time.time() if now is None else now
    ordered = sorted(entries, key=lambda e: e[1], reverse=True)

    kept: list[str] = []
    deleted: list[str] = []
    unpinned_kept = 0
    for name, mtime in ordered:
        if name in policy.pinned:          # المثبت ينجو دائمًا
            kept.append(name)
            continue
        over_count = (policy.max_count is not None
                      and unpinned_kept >= policy.max_count)
        age_days = (now - mtime) / 86400.0
        over_age = (policy.max_age_days is not None
                    and age_days > policy.max_age_days)
        if over_count or over_age:
            deleted.append(name)
        else:
            kept.append(name)
            unpinned_kept += 1
    return kept, deleted


def sweep(runs_dir: str | Path, policy: RetentionPolicy,
          pattern: str = "run-*", now: Optional[float] = None,
          log: Optional[Callable[[str], None]] = None) -> SweepReport:
    """مسح GC على مجلد الـ runs — يُستدعى عند الإقلاع.

    يجمع المداخل المطابقة لـ ``pattern`` (ملفات أو مجلدات) بعمر
    mtime، يقرر عبر ``plan_sweep``، ثم يحذف — أو يسجّل فقط تحت
    dry-run. أخطاء حذف عنصر واحد لا توقف المسح (best-effort:
    العنصر يُستثنى من deleted كي يبقى التقرير صادقًا).
    """
    root = Path(runs_dir)
    if not root.is_dir():
        return SweepReport(dry_run=policy.dry_run)

    entries: list[tuple[str, float]] = []
    for p in root.glob(pattern):
        try:
            entries.append((p.name, p.stat().st_mtime))
        except OSError:
            continue   # اختفى أثناء المسح — تجاهل

    kept, planned = plan_sweep(entries, policy, now=now)

    deleted: list[str] = []
    for name in planned:
        target = root / name
        if policy.dry_run:
            if log:
                log(f"🧹 [retention dry-run] كان سيُحذف: {target}")
            deleted.append(name)
            continue
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
            deleted.append(name)
            if log:
                log(f"🧹 [retention] حُذف: {target}")
        except OSError:
            kept.append(name)   # فشل الحذف ⇒ ما زال موجودًا — تقرير صادق

    return SweepReport(kept=kept, deleted=deleted, dry_run=policy.dry_run)


def policy_from_config(cfg: dict | None) -> RetentionPolicy:
    """بناء السياسة من قسم ``retention`` في config.yaml — أخطاء صاخبة.

    غياب القسم كله ⇒ السياسة الافتراضية (بلا حدود مفعّلة + dry-run):
    سلوك ما-قبل-T-033 نفسه، صفر حذف.
    """
    if not cfg:
        return RetentionPolicy()
    if not isinstance(cfg, dict):
        raise ValueError(f"قسم retention يجب أن يكون خريطة — وجد: {cfg!r}")
    max_count = cfg.get("max_count")
    max_age = cfg.get("max_age_days")
    return RetentionPolicy(
        max_count=int(max_count) if max_count is not None else None,
        max_age_days=float(max_age) if max_age is not None else None,
        pinned=frozenset(str(x) for x in (cfg.get("pinned") or [])),
        dry_run=bool(cfg.get("dry_run", True)),
    )
