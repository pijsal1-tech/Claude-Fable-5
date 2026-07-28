# -*- coding: utf-8 -*-
"""
QA-T09 — عزل مجلدات التقييم (إعادة سيناريو T02 آليًا) — يغلق BUG-04.
Validates: TSK-202 (قائمة تجاهل موحّدة تشمل test---results — NF-23(4)).

Setup: مشروع فيه `test-results/answer.md` و`test---results/answer.md`
بمحتوى واسم فريد (canary string).
Assert: مسح file_manager + scan_folder_for_chain (bridge) +
tool_search_code / tool_list_dir (agent_tools) — كلها لا تُرجع
الـ canary من أي من المجلدين؛ والـ canary موجود فعليًا على القرص
(ضد false-negative). صفر نداءات AI خارجية.
"""
import pathlib

import pytest

from actions.file_manager import FileManager
from chain.bridge import scan_folder_for_chain
from chain.agent_tools import AgentTools
from core.ignore_rules import IGNORED_DIRS

CANARY = "QA_T09_CANARY_b04_zx91"


@pytest.fixture
def eval_project(tmp_path):
    """مشروع فيه مجلدا تقييم + ملف مشروع سليم."""
    root = tmp_path / "proj"
    root.mkdir()
    # ملف مشروع حقيقي — يجب أن يظهر في كل المسحات
    (root / "app.py").write_text(f"print('real project file')\n", encoding="utf-8")
    # مجلدا التقييم — كلاهما يحوي canary
    for dirname in ("test-results", "test---results"):
        d = root / dirname
        d.mkdir()
        (d / "answer.md").write_text(f"# {CANARY}\nleaked eval answer\n",
                                     encoding="utf-8")
    return root


class TestUnifiedSource:
    """grep واحد للمصدر الموحّد — معيار قبول TSK-202."""

    def test_unified_set_contains_required_members(self):
        for name in ("test---results", "test-results",
                     ".ai_runs", ".webdev_backups"):
            assert name in IGNORED_DIRS, f"{name} مفقود من القائمة الموحّدة"

    def test_consumers_alias_the_same_object(self):
        """file_manager وbridge يستهلكان نفس الكائن — لا قوائم مكررة."""
        from actions.file_manager import IGNORE_DIRS
        from chain.bridge import _IGNORE_DIRS
        assert IGNORE_DIRS is IGNORED_DIRS
        assert _IGNORE_DIRS is IGNORED_DIRS

    def test_no_duplicate_literal_lists_in_consumers(self):
        """لا تعريف حرفي مكرر لقائمة تجاهل في مواقع الاستهلاك الثلاثة."""
        repo = pathlib.Path(__file__).resolve().parents[2]
        for rel in ("actions/file_manager.py", "chain/bridge.py",
                    "chain/agent_tools.py"):
            src = (repo / rel).read_text(encoding="utf-8")
            # نمط القائمة الحرفية القديمة: تعريف مجموعة تبدأ بـ node_modules
            assert '"node_modules", ".git"' not in src, \
                f"{rel} ما زال يحمل قائمة تجاهل حرفية مكررة"


class TestCanaryOnDisk:
    """ضد false-negative: الـ canary موجود فعليًا على القرص."""

    def test_canary_files_exist(self, eval_project):
        for dirname in ("test-results", "test---results"):
            f = eval_project / dirname / "answer.md"
            assert f.is_file()
            assert CANARY in f.read_text(encoding="utf-8")


class TestFileManagerIsolation:
    """موقع 1: مسح file_manager (scan_project / get_project_tree)."""

    def test_scan_project_excludes_eval_dirs(self, eval_project):
        fm = FileManager(str(eval_project))
        scan = fm.scan_project()
        paths = [f["path"] for f in scan["files"]]
        assert "app.py" in paths  # الملف الحقيقي يظهر
        for p in paths:
            assert "test-results" not in p and "test---results" not in p

    def test_project_tree_excludes_eval_dirs(self, eval_project):
        fm = FileManager(str(eval_project))
        tree = fm.get_project_tree()
        assert "app.py" in tree
        assert "test-results" not in tree
        assert "test---results" not in tree


class TestBridgeIsolation:
    """موقع 2: scan_folder_for_chain (bridge)."""

    def test_scan_folder_excludes_eval_dirs(self, eval_project):
        files = scan_folder_for_chain(str(eval_project))
        assert any("app.py" in k for k in files)
        for path, content in files.items():
            assert "test-results" not in path
            assert "test---results" not in path
            assert CANARY not in content


class TestAgentToolsIsolation:
    """موقع 3: tool_search_code + tool_list_dir (agent_tools)."""

    def _tools(self, root):
        return AgentTools(project_root=str(root))

    def test_search_code_does_not_leak_canary(self, eval_project):
        tools = self._tools(eval_project)
        out = tools.tool_search_code(CANARY)
        assert CANARY not in out or "لا نتائج" in out
        assert "answer.md" not in out

    def test_search_code_still_finds_real_files(self, eval_project):
        tools = self._tools(eval_project)
        out = tools.tool_search_code("real project file")
        assert "app.py" in out

    def test_list_dir_excludes_eval_dirs(self, eval_project):
        tools = self._tools(eval_project)
        out = tools.tool_list_dir(".", depth=3)
        assert "app.py" in out
        assert "test-results" not in out
        assert "test---results" not in out
