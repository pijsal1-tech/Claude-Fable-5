# -*- coding: utf-8 -*-
"""
QA-T13 — أداء البحث (TSK-501: فهرس بحث مشترك فوق ProjectIndex).
Validates: NF-20 (api_search بلا scan_project لكل ضغطة) +
NF-21 (tool_search_code بلا rglob لكل نداء).

- مستودع اصطناعي 5k ملف: مسار api_search (search_project) ومسار
  tool_search_code — كلاهما < 1s في الحالة المستقرة.
- تكافؤ ذهبي: نتائج الخدمة المشتركة تطابق حرفيًا مخرجات الخوارزميتين
  القديمتين (المعاد بناؤهما هنا كمرجع ذهبي) على عينة مشروع مختلطة.
- بنيوي: زوال scan_project من api_search وزوال rglob من
  tool_search_code (مصدرًا).

صفر نداءات AI خارجية.
"""
import pathlib
import time

import pytest

from actions.file_manager import FileManager, MAX_FILE_SIZE, WEB_EXTENSIONS
from chain.agent_tools import AgentTools
from context.index import ProjectIndex
from context.search import SearchService, shared_search

REPO = pathlib.Path(__file__).resolve().parents[2]

# نفس مجموعة امتدادات المحتوى في api_search (منسوخة عمدًا — عقد ذهبي)
API_CONTENT_EXTS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css',
                    '.json', '.md', '.yaml', '.yml', '.txt', '.sh', '.c',
                    '.cpp', '.h', '.cs', '.php', '.go', '.rs'}


# ═══════════════ المراجع الذهبية (الخوارزميتان القديمتان حرفيًا) ═══════════════

def legacy_api_search(fm: FileManager, q: str) -> list[dict]:
    """إعادة بناء حرفية لخوارزمية api_search القديمة (قبل TSK-501)."""
    q_lower = q.lower()
    results = []
    scan = fm.scan_project(max_files=10000)
    files = scan.get("files", [])
    for f in files:
        rel_path = f.get("rel_path") or f.get("path") or ""
        if not rel_path:
            continue
        if q_lower in rel_path.lower():
            results.append({"type": "file", "path": rel_path,
                            "name": pathlib.Path(rel_path).name,
                            "match": rel_path})
            if len(results) >= 25:
                break
    if len(results) < 20 and len(q) >= 2:
        for f in files:
            rel_path = f.get("rel_path") or f.get("path") or ""
            if not rel_path or any(r["path"] == rel_path and r["type"] == "file"
                                   for r in results):
                continue
            ext = pathlib.Path(rel_path).suffix.lower()
            if ext in API_CONTENT_EXTS:
                try:
                    content = fm.read_file(rel_path, with_line_numbers=False)
                    for idx, line in enumerate(content.splitlines(), 1):
                        if q_lower in line.lower():
                            results.append({"type": "content", "path": rel_path,
                                            "name": pathlib.Path(rel_path).name,
                                            "line": idx,
                                            "snippet": line.strip()[:100]})
                            if len(results) >= 35:
                                break
                except Exception:
                    pass
            if len(results) >= 35:
                break
    return results


def legacy_search_code(root: pathlib.Path, query: str,
                       max_results: int = 20) -> set[str]:
    """إعادة بناء حرفية لحالة-المجلد في tool_search_code القديمة.

    ترتيب rglob عبر اتحاد الامتدادات كان غير حتمي ⇒ المقارنة الذهبية
    كمجموعة (والاختبار يستخدم عينات لا تلمس سقف max_results حتى لا
    يؤثر الترتيب على العضوية).
    """
    from chain.path_policy import is_secret_file
    from core.ignore_rules import IGNORED_DIRS
    text_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
                 ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".cfg",
                 ".sh", ".bat", ".ps1", ".env", ".gitignore"}
    files = []
    for ext in text_exts:
        files.extend(root.rglob(f"*{ext}"))
    results = []
    for fpath in files:
        if any(p in IGNORED_DIRS for p in fpath.parts):
            continue
        if is_secret_file(fpath):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.split("\n"), 1):
                if query.lower() in line.lower():
                    rel = fpath.relative_to(root)
                    results.append(f"{rel}:{i}: {line.strip()}")
                    if len(results) >= max_results:
                        break
        except Exception:
            continue
        if len(results) >= max_results:
            break
    return set(results)


# ═══════════════ المشاريع الاصطناعية ═══════════════

@pytest.fixture
def golden_project(tmp_path):
    """مشروع صغير مختلط: تطابقات اسم + محتوى + مجلد تجاهل + ملف سري."""
    root = tmp_path / "gold"
    root.mkdir()
    (root / "widget_alpha.py").write_text(
        "def alpha():\n    return 'needle in alpha'\n", encoding="utf-8")
    (root / "beta.js").write_text(
        "// needle here too\nconst x = 1;\n", encoding="utf-8")
    (root / "notes.md").write_text(
        "# widget docs\nno match line\nneedle again\n", encoding="utf-8")
    sub = root / "src"
    sub.mkdir()
    (sub / "widget_core.py").write_text(
        "class WidgetCore:\n    pass\n", encoding="utf-8")
    (sub / "styles.css").write_text(
        "body { color: var(--x); } /* needle css */\n", encoding="utf-8")
    ig = root / "node_modules"
    ig.mkdir()
    (ig / "leak.py").write_text("needle LEAKED\n", encoding="utf-8")
    (root / ".env").write_text("SECRET_needle=1\n", encoding="utf-8")
    (root / "data.bin").write_bytes(b"\x00needle\x00")   # امتداد غير نصي
    return root


@pytest.fixture(scope="module")
def big_project(tmp_path_factory):
    """مستودع اصطناعي 5000 ملف — معيار قبول QA-T13."""
    root = tmp_path_factory.mktemp("big5k")
    n_dirs, per_dir = 50, 100          # 50 × 100 = 5000
    for d in range(n_dirs):
        sub = root / f"pkg{d:02d}"
        sub.mkdir()
        for f in range(per_dir):
            body = (f"# module {d}-{f}\n"
                    f"def fn_{d}_{f}():\n"
                    f"    return 'payload_{d}_{f}'\n" + "x = 1\n" * 10)
            if d == 25 and f == 50:
                body += "MAGIC_NEEDLE_QA_T13 = True\n"
            (sub / f"mod_{f:03d}.py").write_text(body, encoding="utf-8")
    return root


# ═══════════════ التكافؤ الذهبي ═══════════════

class TestGoldenParityApiSearch:
    """نتائج search_project ≡ خوارزمية api_search القديمة حرفيًا."""

    @pytest.mark.parametrize("q", ["widget", "needle", "css", "zz_nomatch",
                                   "e", "WIDGET_ALPHA"])
    def test_parity(self, golden_project, q):
        fm = FileManager(str(golden_project))
        legacy = legacy_api_search(fm, q)
        index = ProjectIndex(str(golden_project))
        svc = SearchService(index)
        new = svc.search_project(q, walk_exts=WEB_EXTENSIONS,
                                 max_size=MAX_FILE_SIZE,
                                 content_exts=API_CONTENT_EXTS)
        assert new == legacy

    def test_ignored_and_secret_never_leak(self, golden_project):
        index = ProjectIndex(str(golden_project))
        svc = SearchService(index)
        res = svc.search_project("needle", walk_exts=WEB_EXTENSIONS,
                                 max_size=MAX_FILE_SIZE,
                                 content_exts=API_CONTENT_EXTS)
        paths = {r["path"] for r in res}
        assert not any("node_modules" in p for p in paths)
        assert ".env" not in paths


class TestGoldenParitySearchCode:
    """نتائج tool_search_code الجديدة ≡ عضوية النتائج القديمة."""

    @pytest.mark.parametrize("q", ["needle", "WidgetCore", "zz_nomatch"])
    def test_parity_membership(self, golden_project, q):
        legacy = legacy_search_code(golden_project, q, max_results=100)
        tools = AgentTools(project_root=str(golden_project))
        out = tools.tool_search_code(q, ".", max_results=100)
        if not legacy:
            assert out == f"(لا نتائج لـ '{q}' في .)"
        else:
            assert set(out.split("\n")) == legacy

    def test_single_file_contract_unchanged(self, golden_project):
        tools = AgentTools(project_root=str(golden_project))
        out = tools.tool_search_code("needle", "beta.js")
        assert out == "beta.js:1: // needle here too"
        # الملف السري يُرفض مبكرًا في _resolve_path (سلوك قديم مطابق) —
        # المهم أنه رفض صريح ولا يسرّب المحتوى
        secret_out = tools.tool_search_code("x", ".env")
        assert secret_out.startswith("❌")
        assert "SECRET" not in secret_out
        assert tools.tool_search_code("q", "no/such/dir").startswith("❌")

    def test_write_then_search_freshness(self, golden_project):
        """write-through: ملف جديد يظهر في البحث فورًا (بلا انتظار sweep)."""
        tools = AgentTools(project_root=str(golden_project))
        tools.tool_search_code("needle", ".")           # يبني الفهرس
        fresh = golden_project / "brand_new.py"
        fresh.write_text("fresh_needle_token = 1\n", encoding="utf-8")
        tools._fallback_index.notify_write("brand_new.py")
        out = tools.tool_search_code("fresh_needle_token", ".")
        assert "brand_new.py:1:" in out


# ═══════════════ الأداء (معيار قبول QA-T13) ═══════════════

class TestPerf5k:
    """مستودع 5k ملف: كلا المسارين < 1s في الحالة المستقرة."""

    def test_api_search_path_under_1s(self, big_project):
        index = ProjectIndex(str(big_project))
        svc = shared_search(index)
        # إحماء (يملأ كاش المحتوى — يحاكي الضغطة الأولى)
        svc.search_project("payload_25", walk_exts=WEB_EXTENSIONS,
                           max_size=MAX_FILE_SIZE,
                           content_exts=API_CONTENT_EXTS)
        t0 = time.perf_counter()
        res = svc.search_project("MAGIC_NEEDLE_QA_T13",
                                 walk_exts=WEB_EXTENSIONS,
                                 max_size=MAX_FILE_SIZE,
                                 content_exts=API_CONTENT_EXTS)
        dt = time.perf_counter() - t0
        assert dt < 1.0, f"api_search على 5k ملف استغرق {dt:.2f}s (≥ 1s)"
        assert any(r["type"] == "content" and "MAGIC_NEEDLE_QA_T13" in r["snippet"]
                   for r in res)

    def test_tool_search_code_path_under_1s(self, big_project):
        tools = AgentTools(project_root=str(big_project))
        tools.tool_search_code("payload_10", ".")        # إحماء الكاش
        t0 = time.perf_counter()
        out = tools.tool_search_code("MAGIC_NEEDLE_QA_T13", ".")
        dt = time.perf_counter() - t0
        assert dt < 1.0, f"tool_search_code على 5k ملف استغرق {dt:.2f}s (≥ 1s)"
        assert "MAGIC_NEEDLE_QA_T13" in out

    def test_repeated_calls_reuse_index_and_cache(self, big_project):
        """نداءات متكررة (نمط AgentLoop ×6) لا تعيد بناء الفهرس كل مرة."""
        tools = AgentTools(project_root=str(big_project))
        tools.tool_search_code("payload_0", ".")
        idx = tools._fallback_index
        builds_before = idx.rebuild_count
        for i in range(5):
            tools.tool_search_code(f"payload_{i+1}", ".")
        assert tools._fallback_index is idx
        # يسمح بـ sweep طزاجة واحدًا كحد أقصى خلال الدفعة — لا rebuild لكل نداء
        assert idx.rebuild_count - builds_before <= 1


# ═══════════════ بنيوي: زوال الأنماط القديمة من المسارين الساخنين ═══════════════

class TestStructural:
    def test_api_search_no_scan_project(self):
        src = (REPO / "server.py").read_text(encoding="utf-8")
        start = src.index("def api_search()")
        end = src.index("def api_read_file", start)
        body = src[start:end]
        # نداء المسح الفعلي (fm.scan_project) — ذكره في docstring مسموح
        assert "fm.scan_project(" not in body, \
            "api_search ما زال يمسح الشجرة لكل ضغطة (NF-20)"
        assert "search_project(" in body

    def test_tool_search_code_no_rglob(self):
        src = (REPO / "chain" / "agent_tools.py").read_text(encoding="utf-8")
        start = src.index("def tool_search_code(")
        end = src.index("def tool_get_file_info(", start)
        body = src[start:end]
        assert ".rglob(" not in body, \
            "tool_search_code ما زال يمشي rglob لكل نداء (NF-21)"
        assert "_search_service()" in body

    def test_context_search_no_rglob(self):
        """بوابة check.sh: لا rglob في حزمة context/ (تشمل search.py)."""
        src = (REPO / "context" / "search.py").read_text(encoding="utf-8")
        assert ".rglob(" not in src
