# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  T-042 (R-502): Agent Manifest — تعريفات الأسطول كبيانات

  يغطي:
  - parity: الأدوار الـ 21 القديمة تُحلّ عبر الـ manifest
    الحقيقي بنفس الملفات/المراحل تمامًا (بوابة القبول)
  - schema: manifest مكسور يُرفض برسائل تحمل أرقام الأسطر
  - fail-fast: manifest مفقود/ملف لا يُحلّ ⇒ ManifestError
    عند الإقلاع
  - أدوار غير معروفة ⇒ UnknownAgentRoleError (لا fallback صامت)
  - fallback: base المعلن فقط يسمح بغياب الملف
  - hot-reload: تغيّر mtime يعيد بناء السجل ذرّيًا؛
    تعديل مكسور يُبقي السجل القديم
  - كاش (path, mtime): تعديل ملف وكيل يسري فورًا
═══════════════════════════════════════════════════════
"""
import os
import pathlib

import pytest

from chain.agent_loader import (
    AgentLoader,
    ManifestError,
    UnknownAgentRoleError,
)


# ═══════════════════════════════════════════════════════
#   الأدوار القديمة الـ 21 (نسخة حرفية من ROLE_MAP المحذوفة)
#   — هذا هو الـ baseline الذي تقيس عليه بوابة parity
# ═══════════════════════════════════════════════════════
LEGACY_ROLE_MAP = {
    "code_analyzer":     "سيستم/أنت محلل جودة.md",
    "bug_analyzer":      "سيستم/أنت مراجع أخطاء.md",
    "api_analyzer":      "سيستم/أنت محلل API Flow.md",
    "security_analyzer": "سيستم/أنت مهندس أمان.md",
    "perf_analyzer":     "سيستم/أنت محلل أداء.md",
    "deep_debugger":     "سيستم/أنت محقق أخطاء عميق.md",
    "request_analyzer":  "سيستم/أنت محلل طلبات.md",
    "quality_guard":     "سيستم/أنت حارس الجودة.md",
    "planner":           "سيستم/أنت مخطط.md",
    "architect":         "سيستم/أنت مهندس معماري.md",
    "executor":          "MICRO_WORKER_SYSTEM_PROMPT.md",
    "backend_dev":       "هندسة-تطبيقات/أنت مهندس Backend.md",
    "frontend_dev":      "هندسة-تطبيقات/أنت مطور Frontend.md",
    "code_reviewer":     "هندسة-تطبيقات/أنت مراجع الكود الآمن.md",
    "quality_reviewer":  "سيستم/أنت محلل جودة.md",
    "vibe_reviewer":     "سيستم/أنت مراجع Vibe.md",
    "evidence_reviewer": "سيستم/أنت فاحص بأدلة.md",
    "compat_reviewer":   "سيستم/أنت مراجع توافق.md",
    "orchestrator":      "سيستم/أنت مدير الأوركسترا.md",
    "review_manager":    "سيستم/أنت مدير المراجعة.md",
    "team_manager":      "سيستم/أنت مدير فريق.md",
}

LEGACY_ROLE_STAGE_MAP = {
    "code_analyzer": "analyze", "bug_analyzer": "analyze",
    "api_analyzer": "analyze", "security_analyzer": "analyze",
    "perf_analyzer": "analyze", "deep_debugger": "analyze",
    "request_analyzer": "analyze", "quality_guard": "analyze",
    "planner": "plan", "architect": "plan",
    "executor": "execute", "backend_dev": "execute",
    "frontend_dev": "execute",
    "code_reviewer": "review", "quality_reviewer": "review",
    "vibe_reviewer": "review", "evidence_reviewer": "review",
    "compat_reviewer": "review",
    "orchestrator": "meta", "review_manager": "meta",
    "team_manager": "meta",
}

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def _sha16(path: pathlib.Path) -> str:
    import hashlib
    content = path.read_text(encoding="utf-8", errors="replace")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ═══════════════════════════════════════════════════════
#   أدوات بناء manifest مؤقت
# ═══════════════════════════════════════════════════════

def _write_agents_dir(tmp_path, manifest_text: str,
                      files: dict[str, str] | None = None) -> pathlib.Path:
    """يبني agents_rules مؤقتًا: manifest + ملفات prompts."""
    agents = tmp_path / "agents_rules"
    agents.mkdir(exist_ok=True)
    for rel, content in (files or {}).items():
        p = agents / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (agents / "manifest.yaml").write_text(manifest_text, encoding="utf-8")
    return agents


MINIMAL_MANIFEST = """\
version: 1
agents:
  executor:
    file: worker.md
    stage: execute
"""


_MTIME_OFFSET = [0]


def _bump_mtime(path: pathlib.Path) -> None:
    """
    يضمن تغيّر mtime حتى على أنظمة ملفات بدقة ثانية.
    الإزاحة متزايدة رتيبًا: كتابتان متتاليتان في نفس الثانية
    (mtime خام متساوٍ) تحصلان على mtime نهائي مختلف دائمًا —
    وإلا فقد يتساوى mtime+ثابت قبل التعديل وبعده فلا يُكتشف.
    """
    _MTIME_OFFSET[0] += 2
    st = path.stat()
    os.utime(path, (st.st_atime, st.st_mtime + _MTIME_OFFSET[0]))


# ═══════════════════════════════════════════════════════
#   Parity — بوابة القبول: الأدوار الـ 21 تُحلّ مطابقة
# ═══════════════════════════════════════════════════════

class TestLegacyParity:
    """كل دور من ROLE_MAP القديمة يُحلّ عبر الـ manifest الحقيقي مطابقًا."""

    @pytest.fixture(scope="class")
    def loader(self):
        return AgentLoader()

    def test_registry_covers_exactly_legacy_roles(self, loader):
        assert set(loader._registry) == set(LEGACY_ROLE_MAP)

    @pytest.mark.parametrize("role", sorted(LEGACY_ROLE_MAP))
    def test_role_resolves_identically(self, loader, role):
        prompt = loader.load(role)
        legacy_path = REPO_ROOT / "agents_rules" / LEGACY_ROLE_MAP[role]
        assert prompt.source == "agents_rules", \
            f"{role}: يجب أن يُحلّ من agents_rules لا {prompt.source}"
        assert prompt.stage == LEGACY_ROLE_STAGE_MAP[role]
        assert prompt.content_hash == _sha16(legacy_path), \
            f"{role}: المحتوى لا يطابق الملف القديم {LEGACY_ROLE_MAP[role]}"

    def test_get_role_stage_matches_legacy(self, loader):
        for role, stage in LEGACY_ROLE_STAGE_MAP.items():
            assert loader.get_role_stage(role) == stage

    def test_get_available_roles_all_present(self, loader):
        assert loader.get_available_roles() == sorted(LEGACY_ROLE_MAP)

    def test_definitions_carry_metadata(self, loader):
        d = loader.get_definition("planner")
        assert d.stage == "plan"
        assert d.file == LEGACY_ROLE_MAP["planner"]
        assert d.tier in ("core", "specialist")


# ═══════════════════════════════════════════════════════
#   Schema rejection — أخطاء برقم السطر
# ═══════════════════════════════════════════════════════

class TestSchemaRejection:

    def test_missing_manifest_fails_fast(self, tmp_path):
        (tmp_path / "agents_rules").mkdir()
        with pytest.raises(ManifestError, match="غير موجود"):
            AgentLoader(agents_dir=tmp_path / "agents_rules")

    def test_yaml_syntax_error_carries_line(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path, "version: 1\nagents:\n  x: [unclosed\n")
        with pytest.raises(ManifestError, match=r"manifest\.yaml:\d+"):
            AgentLoader(agents_dir=agents)

    def test_missing_version_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path, "agents:\n  a:\n    file: f.md\n    stage: plan\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError, match="version مفقود"):
            AgentLoader(agents_dir=agents)

    def test_wrong_version_rejected_with_line(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path, "version: 2\nagents:\n  a:\n    file: f.md\n    stage: plan\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError, match=r"manifest\.yaml:1: version"):
            AgentLoader(agents_dir=agents)

    def test_missing_file_key_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path, "version: 1\nagents:\n  a:\n    stage: plan\n")
        with pytest.raises(ManifestError, match="'file' مفقود"):
            AgentLoader(agents_dir=agents)

    def test_invalid_stage_rejected_with_line(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: bogus\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError, match=r"manifest\.yaml:5: .+stage غير صالح"):
            AgentLoader(agents_dir=agents)

    def test_unknown_agent_key_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n    color: red\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError, match="مفتاح غير معروف: 'color'"):
            AgentLoader(agents_dir=agents)

    def test_empty_agents_rejected(self, tmp_path):
        agents = _write_agents_dir(tmp_path, "version: 1\nagents: {}\n")
        with pytest.raises(ManifestError, match="غير فارغ"):
            AgentLoader(agents_dir=agents)

    def test_invalid_fallback_value_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "    fallback: silent\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError, match='"base"'):
            AgentLoader(agents_dir=agents)

    def test_path_traversal_rejected_at_startup(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: ../../etc/passwd\n    stage: plan\n")
        with pytest.raises(ManifestError, match="path traversal"):
            AgentLoader(agents_dir=agents)

    def test_multiple_errors_all_reported(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n"
            "  a:\n    stage: bogus\n"
            "  b:\n    file: missing.md\n    stage: plan\n")
        with pytest.raises(ManifestError) as exc_info:
            AgentLoader(agents_dir=agents)
        # خطآن على الأقل: file مفقود + stage غير صالح (لدور a)
        assert len(exc_info.value.errors) >= 2


# ═══════════════════════════════════════════════════════
#   Missing role / missing file — صاخب لا صامت
# ═══════════════════════════════════════════════════════

class TestLoudFailures:

    def test_unknown_role_raises(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ"})
        loader = AgentLoader(agents_dir=agents)
        with pytest.raises(UnknownAgentRoleError, match="no_such_role"):
            loader.load("no_such_role")

    def test_missing_file_without_fallback_fails_startup(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: gone.md\n    stage: plan\n")
        with pytest.raises(ManifestError, match="غير موجود: 'gone.md'"):
            AgentLoader(agents_dir=agents)

    def test_declared_fallback_allows_missing_file(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: gone.md\n    stage: plan\n"
            "    fallback: base\n")
        base = tmp_path / "prompts"
        base.mkdir()
        (base / "base_plan.md").write_text("خطة أساسية", encoding="utf-8")
        loader = AgentLoader(agents_dir=agents, base_prompts_dir=base)
        prompt = loader.load("a")
        assert prompt.source == "base"
        assert prompt.content == "خطة أساسية"

    def test_declared_fallback_last_resort_synthetic(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: gone.md\n    stage: plan\n"
            "    fallback: base\n")
        empty_base = tmp_path / "prompts"
        empty_base.mkdir()
        loader = AgentLoader(agents_dir=agents, base_prompts_dir=empty_base)
        prompt = loader.load("a")
        assert prompt.source == "fallback"

    def test_file_vanishing_after_startup_is_loud(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ"})
        loader = AgentLoader(agents_dir=agents)
        (agents / "worker.md").unlink()
        with pytest.raises(ManifestError, match="غير قابل للتحميل"):
            loader.load("executor")


# ═══════════════════════════════════════════════════════
#   Hot-reload — mtime يعيد بناء السجل ذرّيًا
# ═══════════════════════════════════════════════════════

class TestHotReload:

    def test_manifest_edit_takes_effect(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ",
                                          "planner.md": "خطط"})
        loader = AgentLoader(agents_dir=agents)
        with pytest.raises(UnknownAgentRoleError):
            loader.load("planner")

        manifest = agents / "manifest.yaml"
        manifest.write_text(
            MINIMAL_MANIFEST + "  planner:\n    file: planner.md\n    stage: plan\n",
            encoding="utf-8")
        _bump_mtime(manifest)

        prompt = loader.load("planner")
        assert prompt.content == "خطط"
        assert loader.last_reload_error is None

    def test_broken_edit_keeps_old_registry(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ"})
        loader = AgentLoader(agents_dir=agents)
        assert loader.load("executor").content == "نفّذ"

        manifest = agents / "manifest.yaml"
        manifest.write_text("version: 1\nagents: {}\n", encoding="utf-8")
        _bump_mtime(manifest)

        # السجل القديم ما زال يخدم — والخطأ مسجّل
        assert loader.load("executor").content == "نفّذ"
        assert loader.last_reload_error is not None
        assert "غير فارغ" in loader.last_reload_error

    def test_fixing_broken_edit_recovers(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ",
                                          "fixed.md": "مُصلح"})
        loader = AgentLoader(agents_dir=agents)
        manifest = agents / "manifest.yaml"

        manifest.write_text("broken: [", encoding="utf-8")
        _bump_mtime(manifest)
        assert loader.load("executor").content == "نفّذ"
        assert loader.last_reload_error is not None

        manifest.write_text(
            "version: 1\nagents:\n  executor:\n    file: fixed.md\n"
            "    stage: execute\n", encoding="utf-8")
        _bump_mtime(manifest)
        assert loader.load("executor").content == "مُصلح"
        assert loader.last_reload_error is None

    def test_unchanged_mtime_serves_cached_registry(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ"})
        loader = AgentLoader(agents_dir=agents)
        r1 = loader._current_registry()
        r2 = loader._current_registry()
        assert r1 is r2   # لا إعادة parse بلا تغيّر


# ═══════════════════════════════════════════════════════
#   تكامل: تعديل ملف وكيل يسري في التحميل التالي
#   (الكاش بمفتاح path+mtime — R-502 core authoring workflow)
# ═══════════════════════════════════════════════════════

class TestPromptFileHotEdit:

    def test_edited_agent_file_served_fresh(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "النسخة الأولى"})
        loader = AgentLoader(agents_dir=agents)
        p1 = loader.load("executor")
        assert p1.content == "النسخة الأولى"

        worker = agents / "worker.md"
        worker.write_text("النسخة المحدثة", encoding="utf-8")
        _bump_mtime(worker)

        p2 = loader.load("executor")
        assert p2.content == "النسخة المحدثة"
        assert p2.content_hash != p1.content_hash

    def test_untouched_file_served_from_cache(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "ثابت"})
        loader = AgentLoader(agents_dir=agents)
        p1 = loader.load("executor")
        p2 = loader.load("executor")
        assert p1 is p2   # نفس الكائن — cache hit

    def test_load_by_stage_unaffected(self, tmp_path):
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ"})
        base = tmp_path / "prompts"
        base.mkdir()
        (base / "base_review.md").write_text("راجع", encoding="utf-8")
        loader = AgentLoader(agents_dir=agents, base_prompts_dir=base)
        prompt = loader.load_by_stage("review")
        assert prompt.source == "base"
        assert prompt.content == "راجع"


# ═══════════════════════════════════════════════════════
#   ADR-007 (AIA-4) — حقول التوجيه الاختيارية
#   قديم يمر / جديد يمر / مجهول يُرفض / مرجع ميت يُرفض /
#   نوع خاطئ يُرفض / التحقق المرجعي
# ═══════════════════════════════════════════════════════

ADR007_FULL_MANIFEST = """\
version: 1
agents:
  analyzer:
    file: a.md
    stage: analyze
  executor:
    file: worker.md
    stage: execute
    when_to_use: تنفيذ خطوة كود واحدة
    when_not_to_use: التخطيط أو المراجعة
    languages: [ar, ar-EG, en, mixed]
    domains: [web, cli, any]
    model_notes: يحتاج نافذة سياق متوسطة
    depends_on: [analyzer]
    conflicts_with: [analyzer]
    last_reviewed: "2026-08-02"
"""


class TestADR007RoutingFields:
    """توسيع schema v1 بحقول التوجيه الاختيارية — رجعي التوافق."""

    def test_old_manifest_without_new_fields_still_passes(self, tmp_path):
        """توافق رجعي: manifest بلا الحقول الجديدة يمر بقيم محايدة."""
        agents = _write_agents_dir(tmp_path, MINIMAL_MANIFEST,
                                   files={"worker.md": "نفّذ"})
        loader = AgentLoader(agents_dir=agents)
        d = loader.definition("executor")
        assert d.when_to_use == ""
        assert d.when_not_to_use == ""
        assert d.languages == ()
        assert d.domains == ()
        assert d.model_notes == ""
        assert d.depends_on == ()
        assert d.conflicts_with == ()
        assert d.last_reviewed == ""

    def test_new_fields_parsed_into_definition(self, tmp_path):
        agents = _write_agents_dir(tmp_path, ADR007_FULL_MANIFEST,
                                   files={"a.md": "حلّل",
                                          "worker.md": "نفّذ"})
        loader = AgentLoader(agents_dir=agents)
        d = loader.definition("executor")
        assert d.when_to_use == "تنفيذ خطوة كود واحدة"
        assert d.when_not_to_use == "التخطيط أو المراجعة"
        assert d.languages == ("ar", "ar-EG", "en", "mixed")
        assert d.domains == ("web", "cli", "any")
        assert d.model_notes == "يحتاج نافذة سياق متوسطة"
        assert d.depends_on == ("analyzer",)
        assert d.conflicts_with == ("analyzer",)
        assert d.last_reviewed == "2026-08-02"

    def test_real_manifest_still_valid_after_extension(self):
        """الـ manifest الحقيقي يمر عبر schema الموسَّع دون تعديل."""
        loader = AgentLoader(agents_dir=REPO_ROOT / "agents_rules")
        assert set(LEGACY_ROLE_MAP) <= set(loader.get_available_roles())

    def test_unknown_key_still_rejected_with_line(self, tmp_path):
        """التوسيع لا يفتح الباب: مفتاح خارج القائمة يُرفض كالمعتاد."""
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "    priority: high\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError,
                           match=r"manifest\.yaml:6: .+مفتاح غير معروف: 'priority'"):
            AgentLoader(agents_dir=agents)

    def test_list_field_wrong_type_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "    domains: web\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError,
                           match="domains يجب أن تكون قائمة نصوص"):
            AgentLoader(agents_dir=agents)

    def test_scalar_field_empty_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "    when_to_use: \"\"\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError,
                           match="'when_to_use' يجب أن يكون نصًا غير فارغ"):
            AgentLoader(agents_dir=agents)

    def test_dead_depends_on_reference_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "    depends_on: [ghost]\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError,
                           match=r"depends_on يشير لدور غير معر.*'ghost'"):
            AgentLoader(agents_dir=agents)

    def test_dead_conflicts_with_reference_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "    conflicts_with: [phantom]\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError,
                           match=r"conflicts_with يشير لدور غير معر.*'phantom'"):
            AgentLoader(agents_dir=agents)

    def test_self_reference_rejected(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "    depends_on: [a]\n",
            files={"f.md": "x"})
        with pytest.raises(ManifestError,
                           match="depends_on يشير للدور نفسه"):
            AgentLoader(agents_dir=agents)

    def test_valid_cross_reference_passes(self, tmp_path):
        agents = _write_agents_dir(
            tmp_path,
            "version: 1\nagents:\n  a:\n    file: f.md\n    stage: plan\n"
            "  b:\n    file: g.md\n    stage: review\n    depends_on: [a]\n",
            files={"f.md": "x", "g.md": "y"})
        loader = AgentLoader(agents_dir=agents)
        assert loader.definition("b").depends_on == ("a",)
