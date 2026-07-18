# -*- coding: utf-8 -*-
"""T-021 (R-202): ContextBundle — sha256 dedupe + provenance + renderer.

المعايير (DEVELOPMENT_TASKS T-021):
- dedup unit: مصدران، نفس الملف → **جسد واحد + إحالة واحدة**.
- عقد T-018 محفوظ: هوية (source_kind, path) أولى-تكسب؛ items/paths/len
  بلا تغيير دلالي (الـ facade وgoldens T-017/T-019 يظلان بايت-بايت).
- renderer golden: بلوك البرومبت يحتوي كل جسد مرة واحدة بالضبط.
"""
from __future__ import annotations

import hashlib

from context.bundle import (
    BundleEntry,
    ContextBundle,
    ContextItem,
    content_hash,
)
from context.engine import ContextEngine, ContextRequest


# ═══════════════════════ hash + dedupe الهوية (عقد T-018) ═══════════════════════

def test_content_hash_is_sha256():
    assert content_hash("abc") == hashlib.sha256(b"abc").hexdigest()


def test_identity_dedupe_first_wins_unchanged():
    """نفس دلالات T-018: مفتاح الهوية يرفض، items تحفظ الأول."""
    b = ContextBundle()
    assert b.add(ContextItem("mention", "a.py", "v1")) is True
    assert b.add(ContextItem("mention", "a.py", "v2")) is False
    assert len(b) == 1
    assert b.items[0].content == "v1"


# ═══════════════════════ dedupe المحتوى (T-021) ═══════════════════════

def test_same_file_two_sources_one_body_one_reference():
    """معيار القبول الحرفي: مصدران، نفس الملف → جسد واحد + إحالة."""
    b = ContextBundle()
    body = "def main():\n    pass\n"
    b.add(ContextItem("mention", "src/app.py", body))
    b.add(ContextItem("keyword", "src/app.py", body))

    entries = b.entries
    assert len(entries) == 2
    assert entries[0].is_reference is False
    assert entries[1].is_reference is True
    assert entries[1].duplicate_of == "src/app.py"
    assert entries[0].content_hash == entries[1].content_hash

    block = b.render_prompt_block()
    assert block.count(body.strip()) == 1          # الجسد مرة واحدة
    assert "لم يُكرَّر" in block                    # وملاحظة الإحالة موجودة


def test_same_content_different_paths_is_reference():
    """ملفان مختلفان بنفس المحتوى (نسخة منسوخة) → الثاني إحالة للأول."""
    b = ContextBundle()
    b.add(ContextItem("mention", "a/config.json", '{"x": 1}'))
    b.add(ContextItem("mention", "b/config.json", '{"x": 1}'))
    assert b.entries[1].is_reference is True
    assert b.entries[1].duplicate_of == "a/config.json"


def test_different_content_not_reference():
    b = ContextBundle()
    b.add(ContextItem("mention", "a.py", "one"))
    b.add(ContextItem("mention", "b.py", "two"))
    assert all(not e.is_reference for e in b.entries)


def test_none_content_never_hashed_nor_reference():
    """huge-file quirk: content=None بلا hash وليس إحالة أبدًا."""
    b = ContextBundle()
    b.add(ContextItem("mention", "big1.js", None))
    b.add(ContextItem("mention", "big2.js", None))
    assert [e.content_hash for e in b.entries] == [None, None]
    assert all(not e.is_reference for e in b.entries)


def test_facade_contract_surface_unchanged_by_references():
    """items/paths تُظهر الإحالات كعناصر عادية — عقد الـ facade محفوظ."""
    b = ContextBundle()
    b.add(ContextItem("mention", "x.py", "same"))
    b.add(ContextItem("keyword", "x.py", "same"))
    assert b.paths() == ["x.py", "x.py"]
    assert b.paths("keyword") == ["x.py"]
    assert [it.content for it in b.items] == ["same", "same"]


# ═══════════════════════ renderer golden ═══════════════════════

def test_render_prompt_block_golden():
    """شكل البلوك مثبّت: جسد → إحالة → تخطي None."""
    b = ContextBundle()
    b.add(ContextItem("mention", "app.py", "print('hi')"))
    b.add(ContextItem("keyword", "app.py", "print('hi')"))
    b.add(ContextItem("mention", "big.js", None))

    expected = (
        "📄 [mention: app.py]:\nprint('hi')"
        "\n\n"
        "📎 [keyword: app.py] — المحتوى مطابق لملف مرفق أعلاه (app.py)،"
        " لم يُكرَّر."
    )
    assert b.render_prompt_block() == expected


def test_render_truncates_long_bodies():
    b = ContextBundle()
    b.add(ContextItem("mention", "long.txt", "x" * 9000))
    block = b.render_prompt_block(max_item_len=100)
    assert "مقطوع — 9000 حرف" in block
    assert len(block) < 300


def test_render_empty_bundle():
    assert ContextBundle().render_prompt_block() == ""


# ═══════════════════════ provenance / debug_dump ═══════════════════════

def test_debug_dump_provenance():
    b = ContextBundle()
    b.add(ContextItem("mention", "a.py", "body"))
    b.add(ContextItem("keyword", "a.py", "body"))
    b.add(ContextItem("mention", "big.js", None))

    dump = b.debug_dump()
    assert [d["index"] for d in dump] == [0, 1, 2]
    assert dump[0]["content_hash"] == content_hash("body")
    assert dump[0]["chars"] == 4 and dump[0]["is_reference"] is False
    assert dump[1]["is_reference"] is True
    assert dump[1]["duplicate_of"] == "a.py"
    assert dump[2]["content_hash"] is None and dump[2]["chars"] is None

    import json
    json.dumps(dump)   # JSON-serializable — صالح للـ logging


# ═══════════════════════ التكامل مع المحرّك ═══════════════════════

def test_engine_returns_deduped_bundle(tmp_path):
    """المحرّك يرجع الحاوية الجديدة: mention+keyword لنفس الملف → إحالة."""
    (tmp_path / "shared.py").write_text("VALUE = 1\n", encoding="utf-8")

    class _EchoSource:
        def __init__(self, kind):
            self.kind = kind

        def collect(self, request, scan):
            return [ContextItem(self.kind, "shared.py",
                                scan.files[0].read_text(encoding="utf-8"))]

    bundle = ContextEngine(
        [_EchoSource("mention"), _EchoSource("keyword")]
    ).gather(ContextRequest(message="shared", project_root=tmp_path))

    assert isinstance(bundle, ContextBundle)
    assert len(bundle) == 2
    assert bundle.entries[1].is_reference is True
    assert bundle.render_prompt_block().count("VALUE = 1") == 1


def test_bundle_entry_is_frozen():
    e = BundleEntry(item=ContextItem("mention", "a.py", "x"),
                    content_hash=content_hash("x"))
    try:
        e.is_reference = True   # type: ignore[misc]
        assert False, "BundleEntry يجب أن يكون frozen"
    except AttributeError:
        pass
