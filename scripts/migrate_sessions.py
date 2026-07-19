#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""migrate_sessions (R-301/R-305 / T-028): ترحيل جلسات JSON القديمة إلى JSONL.

لكل ``<id>.json`` قديم (مستند واحد فيه ``messages`` مضمّنة) يُنتج زوج
تنسيق T-027:

- ``session_<id>.jsonl``     — سطر لكل رسالة: ``{"role","content","ts"}``
  (``ts`` يحمل قيمة ``timestamp`` القديمة حرفيًا — لا فقدان).
- ``session_<id>.meta.json`` — الرأس من المستند القديم حرفيًا
  (id/title/project_path/created_at/updated_at) + ``message_count``.

الضمانات:
- **بلا فقدان (lossless):** تسلسل الرسائل يعود بايت-قيمةً كما كان
  (role/content/timestamp) عند إعادة التشغيل عبر ``SessionStore.replay``.
- **Idempotent:** وجود ``session_<id>.jsonl`` = الجلسة مُرحَّلة ⇒ تُتخطى.
  إعادة تشغيل السكربت no-op (تُثبته الاختبارات بمقارنة mtime).
- **الملف القديم لا يُمس** افتراضيًا (الحذف قرار المستخدم بعد التحقق —
  ``--remove-legacy`` إن رغب). ملف قديم تالف يُتخطى مع تبليغ ولا يُفشل
  بقية الترحيل.

═══════════════════ Runbook — دليل الترحيل ═══════════════════

1) ترحيل (آمن، يُبقي الملفات القديمة):
       python3 scripts/migrate_sessions.py sessions/
   إعادة التشغيل آمنة دائمًا (no-op لما رُحّل).

2) تحقق: السكربت يتحقق ذاتيًا من كل جلسة (إعادة تشغيل + مطابقة العدد
   والمحتوى) ويطبع ملخصًا. تحقق يدوي إضافي إن شئت:
       python3 -c "from sessions.store import SessionStore; \\
                   print(SessionStore('sessions').read_meta('<id>'))"

3) أوقف تسريب الجلسات إلى git (R-305) — على جهازك:
       git rm --cached 'sessions/*.json'
   (ملاحظة: ``.gitignore`` يستهدف ملفات **بيانات** الجلسات فقط —
   ``sessions/*.json`` و``*.jsonl`` و``*.meta.json`` — لا المجلد كله،
   لأن ``sessions/__init__.py`` و``sessions/store.py`` كود إنتاجي يجب
   أن يبقى متتبَّعًا. تنظيف التاريخ نفسه مهمة T-050.)

4) بعد التحقق يمكن حذف القديم:
       python3 scripts/migrate_sessions.py sessions/ --remove-legacy
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass, field

# السكربت يعمل من جذر المستودع أو من scripts/ — نضمن الاستيراد
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sessions.store import SessionMeta, SessionStore  # noqa: E402


@dataclass
class MigrationReport:
    """ملخص تشغيلة ترحيل واحدة — قابل للفحص برمجيًا في الاختبارات."""
    migrated: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_bad: list[tuple[str, str]] = field(default_factory=list)
    removed_legacy: list[str] = field(default_factory=list)

    @property
    def is_noop(self) -> bool:
        return not self.migrated and not self.removed_legacy


def _is_legacy_session(path: pathlib.Path) -> bool:
    """ملفات ``<id>.json`` فقط — لا ``*.meta.json`` (تنسيق جديد)."""
    return (path.suffix == ".json"
            and not path.name.endswith(".meta.json")
            and not path.name.endswith(".tmp"))


def migrate_one(store: SessionStore, legacy_path: pathlib.Path,
                report: MigrationReport) -> None:
    """ترحيل جلسة واحدة + تحقق ذاتي من المطابقة."""
    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
        session_id = str(data["id"])
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError("حقل messages ليس قائمة")
    except Exception as exc:   # ملف تالف — تبليغ وتخطٍّ، لا إفشال الكل
        report.skipped_bad.append((legacy_path.name, str(exc)))
        return

    data_path = store.data_path(session_id)
    if data_path.exists():   # idempotency: مُرحَّلة سابقًا
        report.skipped_existing.append(session_id)
        return

    # كتابة السجل — تنسيق T-027 حرفيًا (سطر JSON + \n)، دفعة واحدة
    lines = []
    for msg in messages:
        lines.append(json.dumps({
            "role": msg.get("role", ""),
            "content": msg.get("content", ""),
            "ts": msg.get("timestamp", ""),
        }, ensure_ascii=False))
    tmp = data_path.with_suffix(".jsonl.tmp")
    try:
        tmp.write_text("".join(line + "\n" for line in lines),
                       encoding="utf-8")
        tmp.replace(data_path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise

    # الرأس من المستند القديم حرفيًا — لا نعيد اشتقاق العنوان
    meta = SessionMeta(
        id=session_id,
        title=str(data.get("title", "")),
        project_path=str(data.get("project_path", "")),
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
        message_count=len(messages),
    )
    store.meta_path(session_id).write_text(
        json.dumps(meta.to_json(), ensure_ascii=False, indent=2),
        encoding="utf-8")

    # تحقق ذاتي: إعادة تشغيل ومطابقة التسلسل قيمةً-قيمة
    replayed = store.replay(session_id)
    assert not replayed.torn_tail
    assert len(replayed.records) == len(messages), \
        f"{session_id}: عدد غير مطابق بعد الترحيل"
    for rec, msg in zip(replayed.records, messages):
        assert rec["role"] == msg.get("role", ""), session_id
        assert rec["content"] == msg.get("content", ""), session_id
        assert rec["ts"] == msg.get("timestamp", ""), session_id

    report.migrated.append(session_id)


def migrate_dir(sessions_dir: str | pathlib.Path,
                remove_legacy: bool = False) -> MigrationReport:
    """ترحيل كل الجلسات القديمة في مجلد — نقطة الدخول البرمجية."""
    dir_path = pathlib.Path(sessions_dir)
    store = SessionStore(dir_path, fsync="never")   # دفعة — لا fsync لكل سطر
    report = MigrationReport()
    for legacy in sorted(dir_path.glob("*.json")):
        if not _is_legacy_session(legacy):
            continue
        migrate_one(store, legacy, report)
        if remove_legacy and not any(
                legacy.name == bad for bad, _ in report.skipped_bad):
            # لا نحذف إلا ما له jsonl مطابق (مُرحَّل الآن أو سابقًا)
            sid = legacy.stem
            if store.data_path(sid).exists():
                legacy.unlink()
                report.removed_legacy.append(sid)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sessions_dir", nargs="?", default="sessions",
                        help="مجلد الجلسات (افتراضي: sessions/)")
    parser.add_argument("--remove-legacy", action="store_true",
                        help="حذف <id>.json القديم بعد التحقق من ترحيله")
    args = parser.parse_args(argv)

    report = migrate_dir(args.sessions_dir, remove_legacy=args.remove_legacy)

    print(f"مُرحَّل الآن: {len(report.migrated)}")
    print(f"مُرحَّل سابقًا (تُخطي): {len(report.skipped_existing)}")
    if report.removed_legacy:
        print(f"ملفات قديمة حُذفت: {len(report.removed_legacy)}")
    if report.skipped_bad:
        print(f"⚠ ملفات تالفة تُخطيت ({len(report.skipped_bad)}):")
        for name, err in report.skipped_bad:
            print(f"  - {name}: {err}")
    if report.is_noop and not report.skipped_bad:
        print("لا شيء للترحيل — no-op.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
