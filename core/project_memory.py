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

═══════════════ التقطير ما-بعد-الـ-run (T-113 / R-805) ═══════════════

``distill_and_record(store, project_id, episode, index=...)`` هو خطاف
ما-بعد-الـ-run: يقترح مدخلات ذاكرة من سجل حلقة T-103 (``EpisodeRecord``
— duck-typed هنا: يكفي ``run_id/goal/outcome/files_touched/
key_decisions``؛ لا استيراد من context ⇒ لا دورة اعتماد):

- ``run_summary`` واحدة: الهدف → النتيجة (+ الملفات الملموسة) —
  إعادة استخدام ملخص T-103 حرفيًا (بند R-805: reuses summaries).
- ``decision`` لكل قرار من ``key_decisions`` (بحد
  ``MAX_DISTILLED_DECISIONS`` — التقطير ضغط لا نسخ).

كل مدخلة مقطّرة تحمل ``source="distillation"`` + ``run_id`` الحلقة
(provenance كامل) + hash-link لحالة الفهرس وقت التقطير.

**عقد التدهور** (نفس عقد ``EpisodicLayer.summarize_and_record``):
التقطير مشتق اختياري — أي فشل ⇒ ما كُتب حتى الآن يُعاد **بلا
استثناء يتسرب**؛ فقدان مدخلة أرخص من إسقاط run.

═══════════════ دلالات الـ staleness (T-113 / R-805) ═══════════════

``is_stale(entry, index)`` = بصمة الفهرس الحي تخالف ``index_hash``
المسجّل وقت الاشتقاق. القاعدة (بند مخاطر R-805 — «حقائق خاطئة تبقى»):
مدخلة قديمة **تُعلَّم وتُنزَّل رتبتها، لا تُقدَّم كطازجة بصمت أبدًا**
— ولا تُحذف: المستخدم (لوحة T-114) هو من يقرر مصيرها.

حالتا «لا حكم» صريحتان (ليستا staleness):
- ``entry.index_hash == ""`` — المدخلة كُتبت بلا فهرس ⇒ لا رابط
  أصلًا فلا انحراف يُقاس.
- بصمة الفهرس الحي ``""`` (لا فهرس متاح الآن) ⇒ لا مرجع للمقارنة.
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


# حد قرارات الحلقة المقطّرة — التقطير ضغط لا نسخ ثانية من الحلقة
MAX_DISTILLED_DECISIONS = 3


def is_stale(entry: MemoryEntry, index: Any) -> bool:
    """هل انحرفت بنية المشروع عن رابط المدخلة؟ (دلالات برأس الوحدة).

    ``True`` فقط عند بصمتين حاضرتين **مختلفتين** — غياب أي طرف
    (``index_hash`` فارغ أو لا فهرس متاح) = «لا حكم» ⇒ ``False``.
    """
    if not entry.index_hash:
        return False
    live = index_fingerprint(index)
    if not live:
        return False
    return live != entry.index_hash


def distill_episode(episode: Any) -> list[tuple[str, str]]:
    """اقتراح مدخلات ``(kind, text)`` من سجل حلقة — نقي بلا كتابة.

    ``episode`` duck-typed (يكفي ``run_id/goal/outcome/files_touched/
    key_decisions`` — شكل ``EpisodeRecord`` من T-103). حلقة بلا هدف
    ولا نتيجة ⇒ لا اقتراحات (لا ذاكرة بلا محتوى).
    """
    goal = str(getattr(episode, "goal", "") or "").strip()
    outcome = str(getattr(episode, "outcome", "") or "").strip()
    proposals: list[tuple[str, str]] = []
    if goal or outcome:
        summary = f"run: {goal or '(بلا هدف)'} → {outcome or '(بلا نتيجة)'}"
        files = tuple(getattr(episode, "files_touched", ()) or ())
        if files:
            summary += " · files: " + ", ".join(str(f) for f in files)
        proposals.append(("run_summary", summary))
    decisions = tuple(getattr(episode, "key_decisions", ()) or ())
    for decision in decisions[:MAX_DISTILLED_DECISIONS]:
        text = str(decision or "").strip()
        if text:
            proposals.append(("decision", text))
    return proposals


def distill_and_record(store: "ProjectMemoryStore", project_id: str,
                       episode: Any, *, index: Any = None
                       ) -> list[MemoryEntry]:
    """خطاف ما-بعد-الـ-run: تقطير حلقة وإلحاق المقترحات بالمخزن.

    كل مدخلة تحمل ``source="distillation"`` + ``run_id`` الحلقة +
    hash-link لحالة الفهرس وقت التقطير. **لا يرفع أبدًا** (عقد
    التدهور برأس الوحدة): أي فشل ⇒ يعيد ما كُتب حتى الآن.
    """
    written: list[MemoryEntry] = []
    try:
        run_id = str(getattr(episode, "run_id", "") or "")
        for kind, text in distill_episode(episode):
            written.append(store.remember(
                project_id, kind, text,
                source="distillation", run_id=run_id, index=index,
            ))
    except Exception:
        pass          # التقطير مشتق اختياري — فقدانه أرخص من إسقاط run
    return written


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

    # ── التحرير (T-114 / R-805: الذاكرة ملك المستخدم) ──
    #
    # التعديل/الحذف يعيدان كتابة الملف **ذرّيًّا** (tmp + fsync +
    # os.replace) — الإلحاق يبقى O(1) للمسار الساخن، والتحرير عملية
    # مستخدم نادرة على ملف صغير؛ الذرّية تحفظ عقد «لا سطر ممزّق إلا
    # ذيل صدمة» حرفيًّا (لا حالة وسطى مرئية أبدًا).

    def edit(self, project_id: str, entry_id: str, *,
             text: str | None = None, kind: str | None = None,
             index: Any = None) -> MemoryEntry | None:
        """تعديل مدخلة بهويتها — يعيد المدخلة الجديدة أو None إن غابت.

        provenance التعديل: ``source="user"`` (المستخدم أكّدها الآن)
        مع الإبقاء على ``entry_id``/``created_at``/``run_id`` الأصلية
        (تاريخ المنشأ لا يُزوَّر). ``index`` الحي (اختياري) يعيد ختم
        ``index_hash`` — تعديل المستخدم إعادة تأكيد على البنية الحالية
        (يمسح علم staleness قديمًا عن قصد). نص فارغ/نوع مجهول =
        ``ValueError`` صاخب (نفس صرامة المخطط).
        """
        current = self.entries(project_id)
        updated: MemoryEntry | None = None
        out: list[MemoryEntry] = []
        for e in current:
            if e.entry_id == entry_id:
                updated = MemoryEntry(
                    kind=kind if kind is not None else e.kind,
                    text=text if text is not None else e.text,
                    entry_id=e.entry_id,
                    created_at=e.created_at,
                    source="user",
                    run_id=e.run_id,
                    index_hash=(index_fingerprint(index)
                                if index is not None else e.index_hash),
                )
                out.append(updated)
            else:
                out.append(e)
        if updated is None:
            return None
        self._rewrite(project_id, out)
        return updated

    def delete(self, project_id: str, entry_id: str) -> bool:
        """حذف مدخلة بهويتها — يعيد True إن وُجدت وحُذفت."""
        current = self.entries(project_id)
        out = [e for e in current if e.entry_id != entry_id]
        if len(out) == len(current):
            return False
        self._rewrite(project_id, out)
        return True

    def _rewrite(self, project_id: str, entries: list[MemoryEntry]) -> None:
        """إعادة كتابة ذرّية: tmp بجوار الملف → fsync → os.replace."""
        path = self.memory_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False,
                                   sort_keys=True) + "\n")
            f.flush()
            if self._fsync == "always":
                os.fsync(f.fileno())
        os.replace(tmp, path)

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
