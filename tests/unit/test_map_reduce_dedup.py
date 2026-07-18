# -*- coding: utf-8 -*-
"""T-022 (R-202): map_reduce عبر ContextBundle — ≥40% تخفيض على fixture الازدواج.

المعايير (DEVELOPMENT_TASKS T-022):
- ≥40% assertion: برومبت mr_execute أصغر بـ 40%+ من صيغة legacy على
  fixture ملفات مكررة المحتوى.
- output parity: نفس مجموعة المعلومات تصل الموديل — كل جسد فريد مرة
  واحدة + إحالة صريحة لكل مكرر (لا فقدان، لا تكرار).
- map_reduce E2E: السلسلة كاملة تنفَّذ عبر ChainExecutor بلا انحدار.
"""
from __future__ import annotations

import pytest

from chain.strategies import build_map_reduce


# ═══════════════════════ fixture الازدواج ═══════════════════════

_SHARED_BODY = ("import os\n\n" + "\n".join(
    f"def handler_{i}(request):\n"
    f"    # boilerplate خط أنابيب متكرر عبر الخدمات\n"
    f"    return request.copy()\n"
    for i in range(30)
))   # ~2KB جسد واحد


@pytest.fixture()
def duplication_files() -> dict[str, str]:
    """fixture الازدواج: 5 ملفات، 4 منها نسخ حرفية من الأول."""
    return {
        "services/a/handlers.py": _SHARED_BODY,
        "services/b/handlers.py": _SHARED_BODY,
        "services/c/handlers.py": _SHARED_BODY,
        "services/d/handlers.py": _SHARED_BODY,
        "services/e/handlers.py": _SHARED_BODY,
    }


def _legacy_files_block(files: dict[str, str]) -> str:
    """صيغة legacy الحرفية (قبل T-022) — تعيد تضمين كل الأجساد."""
    block = ""
    for path, content in files.items():
        block += (
            f"\n\n📄 ملف: {path}\n"
            f"======== START OF SOURCE CODE ========\n"
            f"{content}\n"
            f"======== END OF SOURCE CODE ========"
        )
    return block


def _mr_execute_prompt(files: dict[str, str]) -> str:
    result = build_map_reduce("وحّد الـ handlers", files)
    step = next(s for s in result.steps if s.id == "mr_execute")
    return step.build_prompt({"mr_reduce": "الخطة: وحّد الدوال المشتركة"})


# ═══════════════════════ ≥40% assertion ═══════════════════════

def test_dedup_reduces_execute_prompt_by_40_percent(duplication_files):
    """معيار القبول الحرفي: برومبت mr_execute أصغر ≥40% من legacy."""
    new_prompt = _mr_execute_prompt(duplication_files)

    legacy_prompt = (
        "نفذ التعديلات بناءً على الخطة التالية:\n"
        "الطلب: وحّد الـ handlers\n\n"
        "\n\n[Result from mr_reduce]:\nالخطة: وحّد الدوال المشتركة\n\n"
        "[الملفات الأصلية للتعديل]:"
        + _legacy_files_block(duplication_files)
    )

    reduction = 1 - (len(new_prompt) / len(legacy_prompt))
    assert reduction >= 0.40, (
        f"التخفيض {reduction:.1%} أقل من 40% "
        f"(legacy={len(legacy_prompt)} → new={len(new_prompt)})"
    )


def test_no_dedupe_when_contents_differ():
    """ملفات بمحتويات مختلفة → لا إحالات، الكتلة كاملة كما legacy."""
    files = {"a.py": "AAA", "b.py": "BBB"}
    result = build_map_reduce("طلب", files)
    step = next(s for s in result.steps if s.id == "mr_execute")
    assert "AAA" in step.prompt_template
    assert "BBB" in step.prompt_template
    assert "لم يُكرَّر" not in step.prompt_template
    assert result.metadata["dedupe_refs"] == 0


# ═══════════════════════ output parity ═══════════════════════

def test_parity_each_unique_body_exactly_once(duplication_files):
    """الجسد الفريد يظهر مرة واحدة بالضبط في برومبت mr_execute."""
    prompt = _mr_execute_prompt(duplication_files)
    assert prompt.count(_SHARED_BODY) == 1


def test_parity_every_file_still_mentioned(duplication_files):
    """كل مسار ملف حاضر في البرومبت — كجسد أو كإحالة صريحة (لا فقدان)."""
    prompt = _mr_execute_prompt(duplication_files)
    for path in duplication_files:
        assert path in prompt
    # 4 إحالات لأصل الجسد
    assert prompt.count("لم يُكرَّر") == 4
    assert prompt.count("services/a/handlers.py") == 5  # الجسد + 4 duplicate_of


def test_map_steps_untouched_by_dedup(duplication_files):
    """خطوات الـ map لكل ملف تحمل جسدها كاملًا — الإزالة في mr_execute فقط
    (نتائج الـ dependencies لا تُزال أبدًا — بند المخاطر في R-202)."""
    result = build_map_reduce("طلب", duplication_files)
    map_steps = [s for s in result.steps if s.id.startswith("map_")]
    assert len(map_steps) == 5
    for s in map_steps:
        assert _SHARED_BODY in s.prompt_template


def test_metadata_reports_dedupe_refs(duplication_files):
    result = build_map_reduce("طلب", duplication_files)
    assert result.metadata["dedupe_refs"] == 4
    assert result.metadata["file_count"] == 5


# ═══════════════════════ map_reduce E2E ═══════════════════════

def test_map_reduce_e2e_executes_with_dedup(duplication_files):
    """السلسلة كاملة (5 map + reduce + execute) تُنفَّذ عبر ChainExecutor."""
    from chain.executor import ChainExecutor
    from tests.fakes.fake_provider import FakeProvider

    provider = FakeProvider(
        responder=lambda prompt, history, sys: f"OK ({len(prompt)} chars)"
    )
    result = build_map_reduce("وحّد الـ handlers", duplication_files)
    run = result.to_chain_run("t022-e2e")

    ChainExecutor(provider).execute(run)

    assert run.status == "completed"
    assert all(s.status == "success" for s in run.steps)

    # آخر نداء للمزود هو mr_execute — برومبته المُرسل فعليًا فيه الجسد مرة
    # واحدة والإحالات الأربع (نفس ما بنته build_prompt).
    sent_prompts = [c.prompt for c in provider.calls]
    exec_prompt = sent_prompts[-1]
    assert exec_prompt.count(_SHARED_BODY) == 1
    assert exec_prompt.count("لم يُكرَّر") == 4
