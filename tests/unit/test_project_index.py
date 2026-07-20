# -*- coding: utf-8 -*-
"""اختبارات T-049 (R-702): ProjectIndex — بناء/استعلام/ترتيب/إبطال/أداء.

تغطية معايير القبول:
- Unit: build / lookup / ranking / invalidation (notify_write + sweep).
- Perf: fixture بـ 5000 ملف — mention resolution < 10ms،
  **صفر نداءات rglob** (patched-assert).
- Freshness ×2: write-then-mention (عبر خطاف FileManager)،
  وout-of-band edit يُلتقط خلال sweep واحد.
- بوابة grep: لا ``.rglob(`` في context/.
"""
import pathlib
import subprocess
import time

import pytest

from actions.file_manager import FileManager
from context.engine import ContextEngine, ContextRequest, ProjectScan
from context.facade import gather_message_context
from context.index import IndexedScan, ProjectIndex
from context.sources.keyword import KeywordSource
from context.sources.mention import MentionSource

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ═══════════════════════ fixtures ═══════════════════════

@pytest.fixture()
def project(tmp_path):
    """مشروع صغير بهيكل واقعي."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "src" / "app.test.js").write_text("test", encoding="utf-8")
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "style.css").write_text("body{}", encoding="utf-8")
    (tmp_path / "notes.bin").write_text("x", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def fake_clock():
    """ساعة قابلة للتقديم — لاختبار sweep العمر دون sleep حقيقي."""
    class Clock:
        t = 1000.0
        def __call__(self):
            return self.t
        def advance(self, dt):
            self.t += dt
    return Clock()


# ═══════════════════════ build / lookup / ranking ═══════════════════════

class TestBuildAndLookup:
    def test_build_matches_projectscan_order(self, project):
        """قائمة الفهرس = قائمة ProjectScan بايت-بايت (عقد ترتيب T-017)."""
        idx = ProjectIndex(project)
        scan = ProjectScan(project)
        assert idx.files == scan.files

    def test_lookup_name_exact(self, project):
        idx = ProjectIndex(project)
        hits = idx.lookup_name("app.js")
        assert [str(p.relative_to(project)) for p in hits] == ["src/app.js"]

    def test_lookup_name_missing(self, project):
        assert ProjectIndex(project).lookup_name("nope.js") == []

    def test_lookup_stem_substring(self, project):
        idx = ProjectIndex(project)
        rels = [idx.rel(p) for p in idx.lookup_stem("app")]
        assert rels == ["src/app.js", "src/app.test.js"]

    def test_lookup_ext(self, project):
        idx = ProjectIndex(project)
        rels = [idx.rel(p) for p in idx.lookup_ext(".js")]
        assert rels == ["src/app.js", "src/app.test.js"]

    def test_ranked_lookup_exact_prefix_substring(self, tmp_path):
        (tmp_path / "app.js").write_text("a", encoding="utf-8")
        (tmp_path / "app.test.js").write_text("b", encoding="utf-8")
        (tmp_path / "webapp.js").write_text("c", encoding="utf-8")
        idx = ProjectIndex(tmp_path)
        # exact ("app.js") > prefix ("app.test.js") > substring ("webapp.js")
        assert idx.lookup("app.js") == ["app.js", "webapp.js"]  # exact ثم substring
        assert idx.lookup("app") == ["app.js", "app.test.js", "webapp.js"]

    def test_indexed_scan_is_drop_in(self, project):
        """IndexedScan يطابق عقد ProjectScan: root/files/rel/lookup_*."""
        idx = ProjectIndex(project)
        iscan = idx.scan()
        pscan = ProjectScan(project)
        assert isinstance(iscan, ProjectScan)
        assert iscan.root == pscan.root
        assert iscan.files == pscan.files
        assert iscan.rel(iscan.files[0]) == pscan.rel(pscan.files[0])
        assert ([iscan.rel(p) for p in iscan.lookup_name("app.js")]
                == [pscan.rel(p) for p in pscan.lookup_name("app.js")])
        assert ([iscan.rel(p) for p in iscan.lookup_stem("app")]
                == [pscan.rel(p) for p in pscan.lookup_stem("app")])


# ═══════════════════════ invalidation / freshness ═══════════════════════

class TestInvalidation:
    def test_notify_write_new_file_indexed_immediately(self, project, fake_clock):
        idx = ProjectIndex(project, clock=fake_clock)
        (project / "new.js").write_text("n", encoding="utf-8")
        idx.notify_write("new.js")
        assert [idx.rel(p) for p in idx.lookup_name("new.js")] == ["new.js"]
        # الترتيب العالمي محفوظ بعد الإدراج
        assert idx.files == sorted(idx.files)

    def test_notify_write_existing_file_noop(self, project, fake_clock):
        idx = ProjectIndex(project, clock=fake_clock)
        before = idx.rebuild_count
        idx.notify_write("index.html")
        assert idx.rebuild_count == before
        assert len(idx.lookup_name("index.html")) == 1  # لا تكرار

    def test_notify_write_missing_file_ignored(self, project, fake_clock):
        idx = ProjectIndex(project, clock=fake_clock)
        n = len(idx.files)
        idx.notify_write("ghost.js")
        assert len(idx.files) == n

    def test_sweep_rebuilds_only_when_stale(self, project, fake_clock):
        idx = ProjectIndex(project, max_age_seconds=2.0, clock=fake_clock)
        assert idx.rebuild_count == 1
        assert idx.refresh_if_stale() is False          # طازج
        fake_clock.advance(1.0)
        assert idx.refresh_if_stale() is False          # ما زال ≤ 2s
        fake_clock.advance(1.5)
        assert idx.refresh_if_stale() is True           # تجاوز العمر
        assert idx.rebuild_count == 2

    def test_freshness_write_then_mention_via_hook(self, project):
        """معيار قبول: write-then-mention — كتابة FileManager تظهر فورًا."""
        fm = FileManager(str(project))
        idx = ProjectIndex(project, max_age_seconds=3600)   # sweep معطّل عمليًا
        idx.attach(fm)
        fm.write_file("brandnew.js", "x = 1", backup=False)
        ctx = gather_message_context(project, "افتح brandnew.js", index=idx)
        assert "brandnew.js" in ctx.mentioned_files

    def test_freshness_out_of_band_edit_within_one_sweep(self, project, fake_clock):
        """معيار قبول: تعديل خارجي (بلا FileManager) يُلتقط خلال sweep واحد."""
        idx = ProjectIndex(project, max_age_seconds=2.0, clock=fake_clock)
        # كتابة خارجية مباشرة — لا خطاف يبلغ الفهرس
        (project / "external.js").write_text("e", encoding="utf-8")
        assert idx.lookup_name("external.js") == []     # الفهرس لا يعلم بعد
        fake_clock.advance(2.5)                          # يتجاوز العمر
        scan = idx.scan()                                # sweep واحد
        assert [scan.rel(p) for p in scan.lookup_name("external.js")] == ["external.js"]

    def test_attach_tolerates_fm_without_hooks(self, project):
        class BareFM:
            pass
        ProjectIndex(project).attach(BareFM())          # لا يرفع


# ═══════════════════════ FileManager hook contract ═══════════════════════

class TestFileManagerHooks:
    def test_write_file_invokes_hook_with_rel_path(self, project):
        fm = FileManager(str(project))
        calls = []
        fm.add_write_hook(calls.append)
        fm.write_file("src/hooked.js", "h", backup=False)
        assert calls == ["src/hooked.js"]

    def test_edit_file_covered_by_same_hook(self, project):
        fm = FileManager(str(project))
        calls = []
        fm.add_write_hook(calls.append)
        fm.edit_file("index.html", "<html></html>", "<html>x</html>",
                     backup=False)
        assert calls == ["index.html"]

    def test_broken_hook_does_not_fail_write(self, project):
        fm = FileManager(str(project))
        def boom(_rel):
            raise RuntimeError("hook broke")
        fm.add_write_hook(boom)
        assert fm.write_file("ok.js", "1", backup=False) == "ok.js"


# ═══════════════════════ engine integration ═══════════════════════

class TestEngineIntegration:
    def test_facade_with_index_matches_facade_without(self, project):
        """parity: نفس المخرجات بايت-بايت مع الفهرس وبدونه."""
        msg = "عدّل app.js و style في index.html"
        with_idx = gather_message_context(project, msg,
                                          index=ProjectIndex(project))
        without = gather_message_context(project, msg)
        assert with_idx == without

    def test_indexed_gather_does_no_tree_walk(self, project, monkeypatch):
        """صفر مشيات وقت الرسالة: rglob و os.walk محظوران بعد البناء."""
        import os as os_mod
        import context.index as index_mod
        idx = ProjectIndex(project, max_age_seconds=3600)

        def _forbidden(*a, **k):
            raise AssertionError("tree walk during per-message gather")
        monkeypatch.setattr(pathlib.Path, "rglob", _forbidden)
        monkeypatch.setattr(index_mod.os, "walk", _forbidden)

        engine = ContextEngine([MentionSource(), KeywordSource()],
                               scan_factory=lambda _root: idx.scan())
        bundle = engine.gather(ContextRequest(message="افتح app.js",
                                              project_root=project))
        assert any(it.path == "src/app.js" for it in bundle.items)


# ═══════════════════════ perf: 5k fixture ═══════════════════════

@pytest.fixture(scope="module")
def big_project(tmp_path_factory):
    """fixture بـ 5000 ملف موزعة على 50 مجلدًا."""
    root = tmp_path_factory.mktemp("big5k")
    for d in range(50):
        sub = root / f"pkg{d:02d}"
        sub.mkdir()
        for f in range(100):
            (sub / f"module_{d:02d}_{f:03d}.js").write_text("x", encoding="utf-8")
    (root / "target.js").write_text("hit", encoding="utf-8")
    return root


class TestPerf5k:
    def test_mention_resolution_under_10ms(self, big_project):
        """معيار قبول: <10ms mention resolution على 5k ملف (بعد البناء)."""
        idx = ProjectIndex(big_project, max_age_seconds=3600)
        src = MentionSource()
        request = ContextRequest(message="افتح target.js",
                                 project_root=big_project)
        scan = idx.scan()
        src.collect(request, scan)                       # إحماء
        t0 = time.perf_counter()
        items = src.collect(request, scan)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert any(it.path == "target.js" for it in items)
        assert elapsed_ms < 10, f"mention resolution {elapsed_ms:.2f}ms ≥ 10ms"

    def test_zero_rglob_calls_patched_assert(self, big_project, monkeypatch):
        """معيار قبول R-702: صفر نداءات rglob في مسار الرسالة (patched)."""
        idx = ProjectIndex(big_project, max_age_seconds=3600)

        def _no_rglob(*a, **k):
            raise AssertionError("rglob called in per-message path")
        monkeypatch.setattr(pathlib.Path, "rglob", _no_rglob)

        ctx = gather_message_context(big_project, "افتح target.js", index=idx)
        assert "target.js" in ctx.mentioned_files


# ═══════════════════════ grep gate ═══════════════════════

class TestGrepGate:
    def test_no_rglob_calls_in_context_package(self):
        """بوابة check.sh: لا ``.rglob(`` في context/ (تعليقات rglob مسموحة)."""
        result = subprocess.run(
            ["grep", "-rn", r"\.rglob(", "--include=*.py",
             str(REPO_ROOT / "context")],
            capture_output=True, text=True)
        assert result.returncode == 1, f"rglob call found:\n{result.stdout}"

    def test_check_sh_has_rglob_gate(self):
        content = (REPO_ROOT / "scripts" / "check.sh").read_text(encoding="utf-8")
        assert "rglob ban grep" in content
