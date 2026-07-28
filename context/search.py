# -*- coding: utf-8 -*-
"""SearchService (TSK-501): بحث مشترك فوق ProjectIndex — يغلق NF-20 + NF-21.

═══════════════════ Design Note ═══════════════════

**المشكلة (NF-20):** ``server.py:api_search`` كان ينفّذ
``scan_project(max_files=10000)`` — مشية شجرية كاملة — ثم يقرأ محتوى كل
ملف نصي تسلسليًا **لكل ضغطة بحث**؛ لا فهرس، لا كاش، لا مهلة.

**المشكلة (NF-21):** ``chain/agent_tools.py:tool_search_code`` كان ينفّذ
``rglob`` منفصلًا لكل امتداد + قراءة كاملة لكل ملف **لكل نداء أداة** —
وحلقة الـ Agent تنادي البحث حتى 6 مرات في الرسالة الواحدة (سجل A1:
«search_code ×8 بطيء/فشل»).

**الحل:** خدمة بحث واحدة فوق ``ProjectIndex`` القائم أصلًا (يُبنى مرة
عند فتح المشروع، يبقى طازجًا بخطافات write-through + ``refresh_if_stale``
— انظر context/index.py):

1. **تعداد المرشحين من الفهرس** — صفر مشيات شجرية وقت الاستعلام
   (لا ``scan_project`` ولا ``rglob``)؛ الفلترة (تجاهل/سرّية/امتداد/حجم)
   تجري في الذاكرة على قائمة الفهرس المفروزة عالميًا.
2. **كاش محتوى بمفتاح (mtime_ns, size)** — أسطر الملف تُقرأ مرة واحدة
   وتُعاد من الذاكرة ما لم يتغيّر الملف؛ تعديل الملف يُبطل مدخله ذاتيًا
   (المفتاح يتغيّر). ⇒ زمن البحث في الحالة المستقرة (لكل ضغطة/لكل نداء
   أداة) < 1s على مستودع 5k ملف — معيار قبول QA-T13.

**تكافؤ ذهبي (Accept):** الخدمة تحافظ حرفيًا على عقد المستهلكيْن:

- ``search_project`` (واجهة api_search): نفس أشكال النتائج
  ``{"type": "file"|"content", ...}``، نفس السقوف (25 اسمًا / بوابة 20 /
  إجمالي 35)، نفس بوابة ``len(q) >= 2``، نفس فلاتر scan_project القديمة
  (مجلدات التجاهل الموحّدة + المجلدات المخفية + سرّية الملف + امتدادات
  الويب + سقف الحجم + سقف 10000 ملف) وبنفس الترتيب العالمي (فرز Path
  بالأجزاء = ترتيب DFS المفروز القديم — عقد goldens T-017).
- ``search_code`` (واجهة tool_search_code — حالة المجلد): نفس صيغة السطر
  ``rel:i: line.strip()``، نفس مطابقة endswith للامتداد (تحفظ سلوك
  ``rglob("*{ext}")`` القديم مع ``.env``/``.gitignore``)، نفس فحص
  ``IGNORED_DIRS`` على أجزاء المسار الكامل، ونفس سقف max_results.
  فارق موثّق وحيد: الترتيب صار **حتميًا** (الترتيب العالمي المفروز)
  بدل ترتيب اتحاد rglob غير الحتمي عبر مجموعة الامتدادات.

**حدود صارمة:** لا ``rglob`` هنا إطلاقًا (بوابة grep في scripts/check.sh
تمنعه في حزمة context/)؛ ولا استيراد من actions/ أو server (الوحدة تبقى
ورقة تقريبًا — المستهلكون يمرّرون ثوابتهم كوسائط).
═══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import pathlib
from typing import Callable, Iterable

from chain.path_policy import is_secret_file
from core.ignore_rules import IGNORED_DIRS

# سقف حجم الملف المقروء في بحث المحتوى لواجهة search_project —
# نفس MAX_FILE_SIZE في actions/file_manager (fm.read_file كان يرفض أكبر).
_PROJECT_READ_CAP = 500 * 1024
# لا نكاشي الملفات الأضخم من هذا (تُقرأ مباشرة بلا كاش) — سقف ذاكرة.
_CACHE_FILE_CAP = 1024 * 1024
# سقف مدخلات الكاش — عنده يُفرَّغ بالكامل (أبسط من LRU ويكفي للنطاق).
_CACHE_MAX_ENTRIES = 20000


class SearchService:
    """بحث مشترك فوق ProjectIndex — تعداد فهرسي + كاش محتوى بمفتاح mtime."""

    def __init__(self, index) -> None:
        self._index = index
        # حدود القراءة (R-204): كل قراءة محتوى داخل context/ تمر من
        # SafeReader — لا قراءة خام (بوابة test_safe_reader_routing).
        # السقف الضخم مقصود: سقوف الحجم الفعلية يحكمها المستهلك
        # (max_size في read_lines) حفظًا للعقد القديم لكل مسار.
        # فارق موثّق: ملف يحجبه SafeReader (denylist/sniff) يُتخطى من
        # البحث بدل أن يُقرأ خامًا — تشديد أمني مقصود (لا تسريب
        # أسرار في نتائج بحث تصل للموديل/الواجهة)؛ المساران القديمان
        # كانا يفلتران is_secret_file قبل القراءة أصلًا فالتكافؤ الذهبي
        # على الملفات غير السرية محفوظ حرفيًا.
        from context.safe_reader import SafeReader
        self._reader = SafeReader(index.root, max_file_size=1 << 40)
        # (path(str), splitter) → (mtime_ns, size, lines: list[str])
        # splitter يُحفظ في المفتاح لأن المستهلكيْن القديمين اختلفا:
        # api_search استخدم splitlines()، tool_search_code استخدم
        # split("\n") — أرقام الأسطر قد تختلف على نهايات أسطر شاذة،
        # والتكافؤ الذهبي يلزمنا بحفظ سلوك كلٍّ منهما حرفيًا.
        self._cache: dict[tuple[str, str], tuple[int, int, list[str]]] = {}

    # ═══════════════ قراءة محتوى مكاشاة ═══════════════

    def read_lines(self, p: pathlib.Path,
                   max_size: int | None = None,
                   splitter: str = "splitlines") -> list[str] | None:
        """أسطر الملف من الكاش (مفتاح mtime_ns+size) أو من القرص.

        يعيد None إذا تعذّرت القراءة أو تجاوز الحجم ``max_size``.
        نفس فك الترميز القديم في المسارين: utf-8 مع errors="replace".
        ``splitter``: "splitlines" (عقد api_search القديم) أو "nl"
        (عقد tool_search_code القديم: ``split("\\n")``).
        """
        try:
            st = p.stat()
        except OSError:
            return None
        if max_size is not None and st.st_size > max_size:
            return None
        key = (str(p), splitter)
        hit = self._cache.get(key)
        if hit is not None and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
            return hit[2]
        # القراءة عبر حدود SafeReader (نفس فك الترميز: utf-8 + replace)؛
        # محجوب (سري) أو فاشل ⇒ None (الملف يُتخطى من البحث).
        result = self._reader.read_text(str(p))
        if not result.ok or result.redacted or result.content is None:
            return None
        text = result.content
        lines = text.split("\n") if splitter == "nl" else text.splitlines()
        if st.st_size <= _CACHE_FILE_CAP:
            if len(self._cache) >= _CACHE_MAX_ENTRIES:
                self._cache.clear()
            self._cache[key] = (st.st_mtime_ns, st.st_size, lines)
        return lines

    # ═══════════════ واجهة api_search (NF-20) ═══════════════

    def project_candidates(self, walk_exts: Iterable[str],
                           max_size: int,
                           max_files: int = 10000) -> list[pathlib.Path]:
        """مرشّحو scan_project القدامى — من الفهرس بلا مشية شجرية.

        نفس فلاتر ``FileManager._walk`` حرفيًا: تجاهل موحّد + مجلدات
        مخفية، سرّية الملف، suffix ضمن امتدادات الويب، حجم ≤ السقف،
        وسقف عدد الملفات — وبنفس الترتيب العالمي المفروز.
        """
        self._index.refresh_if_stale()
        exts = set(walk_exts)
        out: list[pathlib.Path] = []
        root_depth = len(self._index.root.parts)
        for p in self._index.files:
            dir_parts = p.parts[root_depth:-1]   # المجلدات تحت الجذر فقط
            if any(d in IGNORED_DIRS or d.startswith(".") for d in dir_parts):
                continue
            if p.suffix not in exts:
                continue
            if is_secret_file(p):
                continue
            try:
                if p.stat().st_size > max_size:
                    continue
            except OSError:
                continue
            out.append(p)
        # تكافؤ ترتيب حرفي مع scan_project القديم: مشية DFS بـ
        # sorted(iterdir) عند كل مستوى ≡ فرز lexicographic على أجزاء
        # المسار (tuple parts) — يختلف عن فرز النص الكامل في حالات
        # البادئة (مثل `test.py` قبل/بعد `test/`)؛ الفرز هنا يحسمها
        # لصالح العقد القديم. O(n log n) على قائمة ذاكرة — زهيد.
        out.sort(key=lambda p: p.parts)
        return out[:max_files]

    def search_project(self, q: str, *,
                       walk_exts: Iterable[str],
                       max_size: int,
                       content_exts: set[str],
                       name_limit: int = 25,
                       content_gate: int = 20,
                       total_limit: int = 35,
                       max_files: int = 10000) -> list[dict]:
        """بحث api_search الكامل — نفس عقد النتائج القديم حرفيًا."""
        q_lower = q.lower()
        results: list[dict] = []
        candidates = self.project_candidates(walk_exts, max_size, max_files)
        rel_of = {id(p): self._index.rel(p) for p in candidates}

        # 1. مطابقة أسماء الملفات ومساراتها (سقف name_limit)
        for p in candidates:
            rel_path = rel_of[id(p)]
            if q_lower in rel_path.lower():
                results.append({
                    "type": "file",
                    "path": rel_path,
                    "name": pathlib.Path(rel_path).name,
                    "match": rel_path,
                })
                if len(results) >= name_limit:
                    break

        # 2. مطابقة المحتوى إذا كان البحث حرفين فأكثر (نفس البوابة القديمة)
        if len(results) < content_gate and len(q) >= 2:
            file_hits = {r["path"] for r in results if r["type"] == "file"}
            for p in candidates:
                rel_path = rel_of[id(p)]
                if rel_path in file_hits:
                    continue
                if pathlib.Path(rel_path).suffix.lower() not in content_exts:
                    continue
                lines = self.read_lines(p, max_size=_PROJECT_READ_CAP)
                if lines is None:
                    # NF-14 §5 (ابتلاع مقصود): ملف غير مقروء أثناء بحث
                    # المحتوى — يُتخطى (إسقاط البحث كله لملف تالف واحد
                    # أسوأ للمستخدم).
                    continue
                for idx, line in enumerate(lines, 1):
                    if q_lower in line.lower():
                        results.append({
                            "type": "content",
                            "path": rel_path,
                            "name": pathlib.Path(rel_path).name,
                            "line": idx,
                            "snippet": line.strip()[:100],
                        })
                        if len(results) >= total_limit:
                            break
                if len(results) >= total_limit:
                    break
        return results

    # ═══════════════ واجهة tool_search_code (NF-21) ═══════════════

    def search_code(self, query: str, search_root: pathlib.Path, *,
                    exts: Iterable[str],
                    max_results: int = 20,
                    is_secret: Callable[[pathlib.Path], bool] = is_secret_file,
                    ) -> list[str]:
        """بحث grep لحالة المجلد — نفس عقد tool_search_code القديم.

        - مطابقة الامتداد بـ ``name.endswith(ext)`` (تكافؤ حرفي مع نمط
          ``rglob("*{ext}")`` القديم: يلتقط ``.env``/``.gitignore``
          الحرفيين رغم أن suffix لهما فارغ).
        - فحص ``IGNORED_DIRS`` على **أجزاء المسار الكامل** (نفس فحص
          ``fpath.parts`` القديم).
        - صيغة السطر: ``f"{rel}:{i}: {line.strip()}"`` والنسبية إلى
          ``search_root``.
        """
        self._index.refresh_if_stale()
        ext_tuple = tuple(exts)
        root = pathlib.Path(search_root).resolve()
        results: list[str] = []
        for p in self._index.files:
            if not p.name.endswith(ext_tuple):
                continue
            try:
                rel = p.relative_to(root)
            except ValueError:
                continue                      # خارج مجلد البحث
            if any(part in IGNORED_DIRS for part in p.parts):
                continue
            if is_secret(p):
                continue
            lines = self.read_lines(p, splitter="nl")
            if lines is None:
                continue
            for i, line in enumerate(lines, 1):
                if query.lower() in line.lower():
                    results.append(f"{rel}:{i}: {line.strip()}")
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break
        return results


def shared_search(index) -> SearchService:
    """الخدمة المشتركة لفهرس معيّن — تُنشأ مرة وتُكاشى على الفهرس نفسه.

    كلا المستهلكيْن (api_search / tool_search_code) يمرّان من هنا ⇒
    كاش محتوى واحد لكل مشروع مفتوح (عمر الكاش = عمر الفهرس = عمر
    ProjectHandle — يُستبدل كوحدة عند تبديل المشروع).
    """
    svc = getattr(index, "_search_service", None)
    if svc is None:
        svc = SearchService(index)
        index._search_service = svc
    return svc
