# -*- coding: utf-8 -*-
"""ProjectMemoryStore (R-805 / T-112): ذاكرة مشروع دائمة عبر الجلسات.

**المشكلة:** كل جلسة تبدأ فاقدة الذاكرة عن المشروع — الأعراف المكتشفة
والقرارات المتخذة ونتائج التشغيلات السابقة يُعاد تعلمها (ويُعاد دفع
ثمنها بأدوات استكشاف) في كل مرة.

**الحل:** مخزن دائم لكل ``project_id`` — نفس بصمة R-303
(``sessions.store.project_fingerprint``: sha256 لمسار الجذر المحلول،
أول 12 hex) فهوية المشروع واحدة عبر الربط والذاكرة.

═══════════════════ مخطط المدخلة (Memory Entry Schema) ═══════════════════

الملف: ``<projects_dir>/<project_id>/memory.jsonl`` — ملحق-فقط، سطر
واحد = كائن JSON واحد (UTF-8، ``ensure_ascii=False``) ينتهي بـ ``\\n``.
نفس عائلة تنسيق SessionStore (R-301): الإلحاق O(1)، لا يُعدَّل سطر
مكتوب أبدًا.

حقول المدخلة::

    {
      "format":     1,            # إصدار المخطط — للهجرات المستقبلية
      "entry_id":   "<uuid hex>", # هوية فريدة (حذف/تعديل المستخدم لاحقًا)
      "kind":       str,          # ENTRY_KINDS: fact | convention |
                                  #   decision | run_summary
      "text":       str,          # نص الحقيقة/العرف/القرار (غير فارغ)
      "source":     str,          # مصدر الإدخال: "agent_tool" (remember_fact)
                                  #   أو "distillation" (T-113) أو "user"
      "run_id":     str,          # provenance: أي تشغيلة أكّدت هذه المدخلة
                                  #   ("" إذا كُتبت خارج run)
      "created_at": str,          # provenance: طابع ISO-8601 UTC
      "index_hash": str           # hash-link لحالة ProjectIndex وقت
                                  #   الاشتقاق ("" إذا لا فهرس متاح)
    }

**provenance** (بند المخاطر في R-805 — «حقائق خاطئة تبقى»): كل مدخلة
تحمل *من* أكّدها (``source`` + ``run_id``) و*متى* (``created_at``) —
أساس تدقيق المستخدم وتحريره (لوحة الذاكرة لاحقًا).

**hash-link** (``index_hash``): بصمة بنية ProjectIndex وقت الاشتقاق —
``sha256`` لقائمة المسارات النسبية المفروزة (أول 16 hex). ProjectIndex
يفهرس *البنية* لا المحتوى، فالبصمة بصمة بنية: إضافة/حذف/إعادة تسمية
ملف تغيّرها. كشف staleness الفعلي (علم + down-rank عند الانحراف)
مجال T-113 — هنا نسجّل الرابط فقط ليكون الانحراف قابلًا للقياس.

**التعافي من الصدمة** (نفس عقد SessionStore): صدمة أثناء الكتابة تُنتج
على الأكثر سطرًا أخيرًا ممزّقًا — القراءة تتخطاه، والكتابة التالية
تبتره أولًا (إصلاح الذيل). سطر تالف **ليس أخيرًا** = عبث خارجي ⇒
``CorruptMemoryError`` بصوت عالٍ.

**الحدود:** المخزن لا يستورد sessions ولا context — ``index`` يُمرَّر
duck-typed (يكفي ``files`` + ``rel``)؛ صفر اعتماد دائري.
"""
from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import os
import pathlib
import uuid
from dataclasses import dataclass
from typing import Any

FORMAT_VERSION = 1

# أنواع المدخلات — من نص R-805: architectural fact / convention /
# decision / run outcome summary. نوع مجهول = ValueError صاخب.
ENTRY_KINDS = ("fact", "convention", "decision", "run_summary")

# مصادر الإدخال المعروفة (توثيقية — لا تُفرض: مصادر جديدة قد تظهر
# في T-113+ دون هجرة؛ النوع kind هو المفروض بصرامة).
KNOWN_SOURCES = ("agent_tool", "distillation", "user")


class CorruptMemoryError(RuntimeError):
    """سطر تالف في وسط سجل الذاكرة — عبث خارجي، لا يُخفى."""


@dataclass(frozen=True)
class MemoryEntry:
    """مدخلة ذاكرة واحدة — راجع مخطط الوحدة أعلاه."""

    kind: str
    text: str
    entry_id: str
    created_at: str
    source: str = "agent_tool"
    run_id: str = ""
    index_hash: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ENTRY_KINDS:
            raise ValueError(
                f"نوع مدخلة غير معروف: {self.kind!r} — "
                f"الأنواع المتاحة: {', '.join(ENTRY_KINDS)}"
            )
        if not (self.text or "").strip():
            raise ValueError("نص المدخلة فارغ — لا تُحفظ ذاكرة بلا محتوى")

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["format"] = FORMAT_VERSION
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MemoryEntry":
        return cls(
            kind=str(d["kind"]),
            text=str(d["text"]),
            entry_id=str(d.get("entry_id", "")),
            created_at=str(d.get("created_at", "")),
            source=str(d.get("source", "agent_tool")),
            run_id=str(d.get("run_id", "")),
            index_hash=str(d.get("index_hash", "")),
        )


def new_entry(kind: str, text: str, *, source: str = "agent_tool",
              run_id: str = "", index_hash: str = "") -> MemoryEntry:
    """مصنع مدخلة: يختم entry_id (uuid) + created_at (ISO-8601 UTC)."""
    return MemoryEntry(
        kind=kind,
        text=text,
        entry_id=uuid.uuid4().hex,
        created_at=datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds"),
        source=source,
        run_id=run_id,
        index_hash=index_hash,
    )


def index_fingerprint(index: Any) -> str:
    """بصمة بنية ProjectIndex: sha256 لمسارات ``files`` النسبية المفروزة.

    duck-typed: يكفي ``index.files`` (قائمة Path) و``index.rel(p)``.
    ``None`` أو فهرس بلا الواجهة المطلوبة ⇒ ``""`` (لا رابط — مقبول:
    الذاكرة تعمل بلا فهرس، فقط بلا كشف staleness لاحقًا).
    """
    if index is None:
        return ""
    files = getattr(index, "files", None)
    rel = getattr(index, "rel", None)
    if files is None or not callable(rel):
        return ""
    try:
        rels = sorted(rel(p) for p in files)
    except Exception:
        return ""
    joined = "\n".join(rels)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


class ProjectMemoryStore:
    """مخزن JSONL ملحق-فقط لذاكرة المشاريع — مفتاحه ``project_id``."""

    def __init__(self, projects_dir: str | pathlib.Path,
                 fsync: str = "always") -> None:
        self.projects_dir = pathlib.Path(projects_dir).resolve()
        if fsync not in ("always", "never"):
            raise ValueError(f"fsync policy غير معروفة: {fsync!r}")
        self._fsync = fsync
        # إصلاح الذيل مرة واحدة لكل مسار في عمر المخزن (نمط SessionStore)
        self._tail_checked: set[str] = set()

    # ── المسارات ──

    @staticmethod
    def _check_project_id(project_id: str) -> str:
        """التحقق أن المعرّف اسم مجلد آمن — لا مسارات، لا فراغ."""
        pid = (project_id or "").strip()
        if not pid or any(c in pid for c in ("/", "\\", "..")) \
                or pid.startswith("."):
            raise ValueError(f"project_id غير صالح: {project_id!r}")
        return pid

    def memory_path(self, project_id: str) -> pathlib.Path:
        pid = self._check_project_id(project_id)
        return self.projects_dir / pid / "memory.jsonl"

    # ── الكتابة ──

    def append(self, project_id: str, entry: MemoryEntry) -> None:
        """إلحاق مدخلة — O(1)، إصلاح ذيل ممزّق قبل أول كتابة."""
        path = self.memory_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._repair_tail(path)
        line = json.dumps(entry.to_dict(), ensure_ascii=False,
                          sort_keys=True) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            if self._fsync == "always":
                os.fsync(f.fileno())

    def remember(self, project_id: str, kind: str, text: str, *,
                 source: str = "agent_tool", run_id: str = "",
                 index: Any = None) -> MemoryEntry:
        """بناء مدخلة كاملة الـ provenance + hash-link ثم إلحاقها."""
        entry = new_entry(kind, text, source=source, run_id=run_id,
                          index_hash=index_fingerprint(index))
        self.append(project_id, entry)
        return entry

    # ── القراءة ──

    def entries(self, project_id: str) -> list[MemoryEntry]:
        """قراءة كل المدخلات — تتخطى سطرًا أخيرًا ممزّقًا فقط.

        Raises:
            CorruptMemoryError: سطر تالف ليس الأخير (عبث خارجي).
        """
        path = self.memory_path(project_id)
        if not path.exists():
            return []
        raw_lines = path.read_text(encoding="utf-8").splitlines()
        out: list[MemoryEntry] = []
        for i, raw in enumerate(raw_lines):
            if not raw.strip():
                continue
            try:
                d = json.loads(raw)
                out.append(MemoryEntry.from_dict(d))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                if i == len(raw_lines) - 1:
                    continue          # ذيل ممزّق بعد صدمة — يُتخطى
                raise CorruptMemoryError(
                    f"سطر ذاكرة تالف (سطر {i + 1} من "
                    f"{len(raw_lines)}) في {path}: {e}"
                ) from e
        return out

    # ── التعافي ──

    def _repair_tail(self, path: pathlib.Path) -> None:
        """بتر ذيل ممزّق (بلا ``\\n`` نهائي) قبل أول كتابة على المسار."""
        key = str(path)
        if key in self._tail_checked:
            return
        self._tail_checked.add(key)
        if not path.exists():
            return
        data = path.read_bytes()
        if not data or data.endswith(b"\n"):
            return
        cut = data.rfind(b"\n")
        with open(path, "wb") as f:
            if cut >= 0:
                f.write(data[: cut + 1])
            f.flush()
            os.fsync(f.fileno())
