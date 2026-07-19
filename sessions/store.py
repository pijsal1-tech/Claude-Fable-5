# -*- coding: utf-8 -*-
"""SessionStore (R-301 / T-027): مخزن جلسات JSONL ملحق-فقط.

يقتل الـ O(n²): ``SessionManager.append_message`` القديم كان يعمل
load-كامل → append → إعادة كتابة كاملة مع fsync **لكل رسالة** — تكلفة
الرسالة تنمو خطيًا مع طول التاريخ. هنا الإلحاق O(1): سطر واحد يُكتب في
نهاية الملف، لا قراءة ولا إعادة كتابة.

═══════════════════ مواصفة التنسيق على القرص ═══════════════════

لكل جلسة ملفان داخل ``sessions_dir``:

1) ``session_<id>.jsonl`` — **سجل الرسائل، ملحق-فقط، وهو مصدر الحقيقة.**
   - كل سطر = كائن JSON واحد (UTF-8، ``ensure_ascii=False``) ينتهي بـ
     ``\\n``. لا يُعدَّل سطر مكتوب أبدًا ولا يُحذف.
   - السجل القياسي للرسالة: ``{"role": str, "content": str, "ts": iso8601}``
     — لكن أي كائن JSON (dict) مقبول عبر ``append_record`` (توسعة R-802:
     نفس التنسيق يدعم event sourcing لاحقًا).
   - **الصدمة تُنتج على الأكثر سطرًا أخيرًا ممزّقًا** (بلا ``\\n`` أو JSON
     ناقص). القراءة تتخطاه وتبلّغ عنه؛ والكتابة التالية تبتره أولًا
     (انظر "التعافي" أدناه). أي سطر تالف **ليس أخيرًا** يعني عبثًا خارجيًا
     بالملف ⇒ ``CorruptLogError`` بصوت عالٍ — لا إخفاء.

2) ``session_<id>.meta.json`` — **رأس الجلسة المتغيّر (sidecar) — مشتق،
   قابل لإعادة البناء، ليس مصدر حقيقة.**
   - كائن JSON واحد:
     ``{"format": 1, "id", "title", "project_path", "project_id",
        "created_at", "updated_at", "message_count"}``
   - ``project_id`` (R-303 / T-031): بصمة المشروع — ``sha256`` لمسار
     الجذر المحلول (أول 12 hex). تُختم عند الإنشاء وتتحدّث مع
     ``set_project_path``؛ الجلسات القديمة بلا بصمة تُقرأ كغير مرتبطة
     (``""``) — توافق خلفي كامل.
   - يُكتب فقط عند **تغيّر الرأس**: الإنشاء، أول عنوان (أول رسالة user)،
     ``set_project_path``، أو ``flush_meta()`` صراحةً — لا يُعاد كتابته
     لكل رسالة (وإلا عدنا لنمط rewrite-per-message الذي نقتله).
   - لذلك العدّادات (``message_count``/``updated_at``) قد تتأخر عن السجل
     بعد صدمة — وهذا مقبول بالتصميم (بند المخاطر في R-301): السجل هو
     الحقيقة، و``rebuild_meta()`` يعيد بناء الرأس منه عند أي شك.

سياسة الـ fsync (``fsync=``):
  - ``"always"`` (الافتراضي): fsync بعد كل سطر بيانات — أقصى أمان صدمات.
  - ``"never"``: flush بلا fsync — لدفعات الاستيراد/الترحيل والقياس.
  ملف الـ meta يُستبدل ذريًا (tmp + ``os.replace``) **بلا fsync** — مشتق
  ورخيص، وإعادة بنائه أرخص من مزامنته في المسار الساخن.

═══════════════════ التعافي من السطر الممزّق ═══════════════════

- **قراءةً** (``replay``/``tail``): السطر الأخير غير المكتمل يُتخطى
  ويُحتسب في ``torn_tail`` — لا استثناء.
- **كتابةً** (أول ``append`` على ملف قائم): لو آخر بايت ليس ``\\n``
  يُبتر الملف حتى آخر ``\\n`` سليم (الجزء الممزّق غير قابل للإنقاذ
  بالتعريف) ثم يُلحق السطر الجديد — فلا يلتحم سجلان أبدًا.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator, Literal, Optional

FORMAT_VERSION = 1

# حجم كتلة القراءة الخلفية في tail() — يوازن عدد الـ seeks مع الذاكرة
_TAIL_BLOCK = 64 * 1024

FsyncPolicy = Literal["always", "never"]


class CorruptLogError(Exception):
    """سطر تالف في **وسط** السجل — ليس تمزّق صدمة بل عبث/عطب خارجي."""


def _now_iso() -> str:
    return datetime.now().isoformat()


# ═══════════════════ ربط الجلسة بالمشروع (R-303 / T-031) ═══════════════════

def project_fingerprint(project_path: str) -> str:
    """بصمة مشروع مستقرة: sha256 لمسار الجذر المحلول (أول 12 hex).

    الحلّ عبر ``Path.resolve()`` يوحّد المسارات النسبية/الشرطة الزائدة/
    الوصلات الرمزية — نفس المشروع يعطي نفس البصمة مهما كُتب المسار.
    مسار فارغ = لا بصمة (جلسة غير مرتبطة).
    """
    if not project_path:
        return ""
    resolved = str(pathlib.Path(project_path).resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:12]


BINDING_POLICIES = ("warn", "fork", "block")


@dataclass(frozen=True)
class BindingCheck:
    """نتيجة فحص ربط الجلسة بالمشروع عند التبديل.

    ``action`` هو القرار النهائي الذي يطيعه المعالج:
    ``"none"`` (لا تعارض — جلسة غير مرتبطة أو نفس المشروع) أو إحدى
    السياسات الثلاث عند عدم التطابق: ``"warn"`` (بانر سياق — السلوك
    القديم يستمر صراحة)، ``"fork"`` (جلسة جديدة مرتبطة بالمشروع
    الجديد)، ``"block"`` (رفض التبديل).
    """
    bound: bool     # هل الجلسة مرتبطة بمشروع أصلًا؟
    match: bool     # هل المشروع الجديد هو نفسه المرتبط؟
    policy: str     # السياسة المطبقة (warn | fork | block)
    action: str     # none | warn | fork | block


def check_project_binding(bound_project_id: str, new_project_path: str,
                          policy: str) -> BindingCheck:
    """فحص الربط: بصمة الجلسة المختومة ضد المشروع المستهدف.

    جلسة غير مرتبطة (بصمة فارغة — تشمل جلسات legacy قبل T-031)
    أو تطابق البصمتين ⇐ ``action="none"`` (التبديل صامت).
    عدم التطابق ⇐ ``action=policy``. سياسة غير معروفة ⇐ ``ValueError``
    (بصوت عالٍ — خطأ إعداد لا يُبتلع).
    """
    if policy not in BINDING_POLICIES:
        raise ValueError(
            f"سياسة ربط غير معروفة: {policy!r} — المتاح: {BINDING_POLICIES}")
    if not bound_project_id:
        return BindingCheck(bound=False, match=True, policy=policy,
                            action="none")
    match = bound_project_id == project_fingerprint(new_project_path)
    return BindingCheck(bound=True, match=match, policy=policy,
                        action="none" if match else policy)


# ═══════════════════ نموذج البيانات ═══════════════════

@dataclass
class SessionMeta:
    """رأس الجلسة — انعكاس ``session_<id>.meta.json``."""
    id: str
    title: str = ""
    project_path: str = ""
    project_id: str = ""     # R-303 (T-031): بصمة المشروع — فارغة = غير مرتبطة
    created_at: str = ""
    updated_at: str = ""
    message_count: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "format": FORMAT_VERSION,
            "id": self.id,
            "title": self.title,
            "project_path": self.project_path,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "SessionMeta":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            project_path=str(data.get("project_path", "")),
            project_id=str(data.get("project_id", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            message_count=int(data.get("message_count", 0)),
        )


@dataclass
class ReplayResult:
    """نتيجة إعادة تشغيل السجل — التمزّق مرصود لا صامت."""
    records: list[dict[str, Any]] = field(default_factory=list)
    torn_tail: bool = False


# ═══════════════════ المخزن ═══════════════════

class SessionStore:
    """مخزن JSONL ملحق-فقط — راجع docstring الوحدة لمواصفة التنسيق."""

    def __init__(self, sessions_dir: str | pathlib.Path,
                 fsync: FsyncPolicy = "always") -> None:
        self.sessions_dir = pathlib.Path(sessions_dir).resolve()
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        if fsync not in ("always", "never"):
            raise ValueError(f"fsync policy غير معروفة: {fsync!r}")
        self._fsync: FsyncPolicy = fsync
        # كاش الرؤوس + الجلسات التي فُحص ذيلها للكتابة في عمر المخزن هذا
        self._meta_cache: dict[str, SessionMeta] = {}
        self._tail_checked: set[str] = set()

    # ── المسارات ──

    def data_path(self, session_id: str) -> pathlib.Path:
        return self.sessions_dir / f"session_{session_id}.jsonl"

    def meta_path(self, session_id: str) -> pathlib.Path:
        return self.sessions_dir / f"session_{session_id}.meta.json"

    # ── دورة الحياة ──

    def create(self, project_path: str = "") -> SessionMeta:
        """جلسة جديدة: ملف jsonl فارغ + كتابة الـ meta (تغيّر رأس)."""
        session_id = uuid.uuid4().hex[:8]
        now = _now_iso()
        meta = SessionMeta(id=session_id, project_path=project_path,
                           project_id=project_fingerprint(project_path),
                           created_at=now, updated_at=now)
        self.data_path(session_id).touch()
        self._meta_cache[session_id] = meta
        self._tail_checked.add(session_id)   # ملف جديد — ذيله سليم
        self._write_meta(meta)
        return meta

    def exists(self, session_id: str) -> bool:
        return self.data_path(session_id).is_file()

    def delete(self, session_id: str) -> bool:
        found = False
        for p in (self.data_path(session_id), self.meta_path(session_id)):
            if p.exists():
                p.unlink()
                found = True
        self._meta_cache.pop(session_id, None)
        self._tail_checked.discard(session_id)
        return found

    def list_ids(self) -> list[str]:
        return sorted(p.name[len("session_"):-len(".jsonl")]
                      for p in self.sessions_dir.glob("session_*.jsonl"))

    # ── الإلحاق (المسار الساخن — O(1)) ──

    def append_record(self, session_id: str, record: dict[str, Any]) -> None:
        """إلحاق سجل واحد — سطر JSON + ``\\n`` مع fsync حسب السياسة.

        لا قراءة للسجل ولا إعادة كتابة — التكلفة ثابتة مهما طال التاريخ.
        """
        path = self.data_path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"جلسة غير موجودة: {session_id}")
        self._ensure_clean_tail(session_id, path)

        line = json.dumps(record, ensure_ascii=False)
        if "\n" in line:   # json.dumps لا ينتج \n — حزام أمان للتنسيق
            raise ValueError("سجل JSONL لا يحوي سطرًا جديدًا داخليًا")
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            if self._fsync == "always":
                os.fsync(f.fileno())

        # تحديث الرأس في الذاكرة — الكتابة للقرص فقط عند تغيّر رأسي فعلي
        meta = self._load_meta(session_id)
        meta.message_count += 1
        meta.updated_at = _now_iso()
        if (not meta.title and record.get("role") == "user"
                and isinstance(record.get("content"), str)):
            content: str = record["content"]
            meta.title = content[:60].strip() + ("..." if len(content) > 60
                                                 else "")
            self._write_meta(meta)   # تغيّر رأس (أول عنوان) ⇒ يُكتب

    def append_message(self, session_id: str, role: str,
                       content: str) -> None:
        """السجل القياسي: role/content/ts — انظر مواصفة التنسيق."""
        self.append_record(session_id, {
            "role": role, "content": content, "ts": _now_iso(),
        })

    # ── القراءة ──

    def replay(self, session_id: str) -> ReplayResult:
        """كل السجلات بالترتيب — السطر الأخير الممزّق يُتخطى ويُبلَّغ.

        سطر تالف في الوسط = ``CorruptLogError`` (ليس نمط صدمة).
        """
        path = self.data_path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"جلسة غير موجودة: {session_id}")
        raw = path.read_bytes()
        result = ReplayResult()
        if not raw:
            return result
        lines = raw.split(b"\n")
        # split يترك عنصرًا أخيرًا: "" لو الملف منتهٍ بـ \n (سليم)،
        # وإلا فهو الذيل الممزّق (كُتب جزئيًا قبل الصدمة)
        torn = lines.pop()
        if torn:
            result.torn_tail = True
        for i, line_bytes in enumerate(lines):
            if not line_bytes.strip():
                continue
            try:
                result.records.append(json.loads(line_bytes.decode(
                    "utf-8", errors="strict")))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise CorruptLogError(
                    f"سطر تالف في وسط سجل {session_id} "
                    f"(سطر {i + 1}): {exc}") from exc
        return result

    def tail(self, session_id: str, n: int) -> ReplayResult:
        """آخر ``n`` سجلات **بدون قراءة الملف كاملًا** (نافذة R-304).

        قراءة خلفية بكتل ``_TAIL_BLOCK`` من نهاية الملف حتى تتجمع
        ``n`` أسطر مكتملة (أو نبلغ البداية). الذيل الممزّق يُتخطى ويُبلَّغ.
        """
        if n <= 0:
            return ReplayResult()
        path = self.data_path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"جلسة غير موجودة: {session_id}")

        result = ReplayResult()
        with open(path, "rb") as f:
            f.seek(0, io.SEEK_END)
            end = f.tell()
            if end == 0:
                return result
            buf = b""
            pos = end
            # نتراجع كتلةً كتلة حتى نملك n+1 فاصل سطر (يضمن n سطرًا كاملًا
            # قبل الذيل) أو نصل رأس الملف
            while pos > 0 and buf.count(b"\n") <= n:
                step = min(_TAIL_BLOCK, pos)
                pos -= step
                f.seek(pos)
                buf = f.read(step) + buf

        lines = buf.split(b"\n")
        if pos > 0:
            # أول عنصر جزء من سطر يمتد قبل نافذتنا — ليس سطرًا كاملًا
            lines = lines[1:]
        torn = lines.pop()   # "" لو انتهى الملف بـ \n، وإلا ذيل ممزّق
        if torn:
            result.torn_tail = True
        for line_bytes in lines[-n:]:
            if not line_bytes.strip():
                continue
            try:
                result.records.append(json.loads(line_bytes.decode(
                    "utf-8", errors="strict")))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise CorruptLogError(
                    f"سطر تالف داخل نافذة tail لجلسة {session_id}: {exc}"
                ) from exc
        return result

    # ── الـ meta ──

    def read_meta(self, session_id: str) -> SessionMeta:
        """رأس الجلسة — من الكاش ثم القرص (بلا إعادة بناء تلقائية)."""
        return self._load_meta(session_id)

    def set_project_path(self, session_id: str, project_path: str) -> None:
        """تغيّر رأسي ⇒ كتابة فورية للـ sidecar."""
        meta = self._load_meta(session_id)
        meta.project_path = project_path
        meta.project_id = project_fingerprint(project_path)   # R-303
        meta.updated_at = _now_iso()
        self._write_meta(meta)

    def flush_meta(self, session_id: str) -> None:
        """كتابة الرأس الحالي (بعدّاداته في-الذاكرة) للقرص صراحةً."""
        self._write_meta(self._load_meta(session_id))

    def rebuild_meta(self, session_id: str) -> SessionMeta:
        """إعادة بناء الرأس من السجل — السجل هو مصدر الحقيقة.

        يعالج بند مخاطر R-301 (انزياح data/meta): العدّادات والعنوان
        يُشتقان من إعادة التشغيل؛ ``created_at``/``project_path`` يُحفظان
        من الرأس القائم إن وُجد (غير قابلَين للاشتقاق من السجل).
        """
        # الرأس القديم يُقرأ من القرص مباشرة (best-effort) — ليس عبر
        # _load_meta الذي يستدعينا عند الغياب/التلف (تكرار لانهائي)
        old: Optional[SessionMeta] = self._meta_cache.get(session_id)
        if old is None:
            mpath = self.meta_path(session_id)
            if mpath.is_file():
                try:
                    old = SessionMeta.from_json(
                        json.loads(mpath.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, ValueError, TypeError):
                    old = None
        replayed = self.replay(session_id)

        title = ""
        for rec in replayed.records:
            if rec.get("role") == "user" and isinstance(
                    rec.get("content"), str):
                content = rec["content"]
                title = content[:60].strip() + ("..." if len(content) > 60
                                                else "")
                break
        last_ts = ""
        for rec in reversed(replayed.records):
            if isinstance(rec.get("ts"), str):
                last_ts = rec["ts"]
                break

        meta = SessionMeta(
            id=session_id,
            title=title,
            project_path=old.project_path if old else "",
            project_id=old.project_id if old else "",   # R-303: تُحفظ
            created_at=(old.created_at if old and old.created_at
                        else (replayed.records[0].get("ts", "")
                              if replayed.records else _now_iso())),
            updated_at=last_ts or _now_iso(),
            message_count=len(replayed.records),
        )
        self._meta_cache[session_id] = meta
        self._write_meta(meta)
        return meta

    # ── أدوات داخلية ──

    def _ensure_clean_tail(self, session_id: str,
                           path: pathlib.Path) -> None:
        """بتر الذيل الممزّق قبل أول إلحاق — يُفحص مرة لكل جلسة/مخزن."""
        if session_id in self._tail_checked:
            return
        self._tail_checked.add(session_id)
        size = path.stat().st_size
        if size == 0:
            return
        with open(path, "rb+") as f:
            f.seek(-1, io.SEEK_END)
            if f.read(1) == b"\n":
                return
            # ذيل ممزّق: نتراجع لآخر \n سليم ونبتر ما بعده
            pos = size - 1
            while pos > 0:
                step = min(_TAIL_BLOCK, pos)
                f.seek(pos - step)
                block = f.read(step)
                cut = block.rfind(b"\n")
                if cut != -1:
                    f.truncate(pos - step + cut + 1)
                    return
                pos -= step
            f.truncate(0)   # لا \n في الملف كله — السطر الوحيد ممزّق

    def _load_meta(self, session_id: str) -> SessionMeta:
        cached = self._meta_cache.get(session_id)
        if cached is not None:
            return cached
        mpath = self.meta_path(session_id)
        if mpath.is_file():
            try:
                meta = SessionMeta.from_json(
                    json.loads(mpath.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, ValueError, TypeError):
                # sidecar تالف — السجل هو الحقيقة، نعيد البناء منه
                return self.rebuild_meta(session_id)
        elif self.exists(session_id):
            # سجل بلا sidecar (نصف عملية/ترحيل ناقص) — نبنيه
            return self.rebuild_meta(session_id)
        else:
            raise FileNotFoundError(f"جلسة غير موجودة: {session_id}")
        self._meta_cache[session_id] = meta
        return meta

    def _write_meta(self, meta: SessionMeta) -> None:
        """استبدال ذري بلا fsync — الـ meta مشتق ورخيص الإصلاح."""
        mpath = self.meta_path(meta.id)
        tmp = mpath.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(meta.to_json(), ensure_ascii=False,
                                      indent=2), encoding="utf-8")
            os.replace(tmp, mpath)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise

    # ── أدوات مساعدة للاستهلاك المتدفق ──

    def iter_records(self, session_id: str) -> Iterator[dict[str, Any]]:
        """تكرار مريح فوق replay() — نفس دلالات التعافي."""
        yield from self.replay(session_id).records
