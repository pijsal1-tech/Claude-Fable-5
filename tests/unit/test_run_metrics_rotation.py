# -*- coding: utf-8 -*-
"""TSK-720 (P1-3) — عقد تدوير metrics/runs.jsonl بالحجم عند الإقلاع.

معايير القبول (DEVELOPMENT_TASKS §BATCH-P1 / TSK-720):
- ملف فوق السقف يُدوَّر (→ .1) ويبدأ ملف جديد مع أول append.
- تحت السقف لا يُمس.
- idempotent: نداء ثانٍ متتالٍ لا يفعل شيئًا.
- غائب ⇒ لا شيء، بلا استثناء.
- الجيل الأسبق يُستبدل (جيل واحد فقط).
"""
import json

from core.run_metrics import ROTATE_MAX_BYTES, RunMetricsStore


def _store(tmp_path):
    return RunMetricsStore(tmp_path / "metrics" / "runs.jsonl")


def test_oversized_file_is_rotated(tmp_path):
    st = _store(tmp_path)
    st.append({"run_id": "old", "mode": "direct"})
    st.path.write_text("x" * 100, encoding="utf-8")   # حجم معلوم
    assert st.rotate_if_oversized(max_bytes=50) is True
    assert not st.path.exists()
    rotated = st.path.with_name(st.path.name + ".1")
    assert rotated.is_file() and rotated.stat().st_size == 100
    # أول append بعد التدوير يبدأ ملفًا جديدًا نظيفًا.
    st.append({"run_id": "new", "mode": "chain"})
    recs = st.read_records()
    assert [r["run_id"] for r in recs] == ["new"]


def test_under_cap_untouched(tmp_path):
    st = _store(tmp_path)
    st.append({"run_id": "r1"})
    before = st.path.read_bytes()
    assert st.rotate_if_oversized(max_bytes=ROTATE_MAX_BYTES) is False
    assert st.path.read_bytes() == before
    assert not st.path.with_name(st.path.name + ".1").exists()


def test_idempotent_second_call_noop(tmp_path):
    st = _store(tmp_path)
    st.path.parent.mkdir(parents=True)
    st.path.write_text("y" * 100, encoding="utf-8")
    assert st.rotate_if_oversized(max_bytes=50) is True
    assert st.rotate_if_oversized(max_bytes=50) is False   # الملف غاب


def test_missing_file_noop_no_raise(tmp_path):
    st = _store(tmp_path)
    assert st.rotate_if_oversized() is False


def test_single_generation_replaces_previous(tmp_path):
    st = _store(tmp_path)
    st.path.parent.mkdir(parents=True)
    rotated = st.path.with_name(st.path.name + ".1")
    rotated.write_text("ancient", encoding="utf-8")
    st.path.write_text("z" * 100, encoding="utf-8")
    assert st.rotate_if_oversized(max_bytes=50) is True
    assert rotated.read_text(encoding="utf-8") == "z" * 100  # اُستبدل


def test_default_cap_is_5mb():
    assert ROTATE_MAX_BYTES == 5 * 1024 * 1024


def test_summary_reads_current_file_only(tmp_path):
    st = _store(tmp_path)
    st.append({"run_id": "a", "mode": "direct", "status": "ok",
               "duration_ms": 10})
    st.path.rename(st.path.with_name(st.path.name + ".1"))
    st.append({"run_id": "b", "mode": "direct", "status": "ok",
               "duration_ms": 20})
    recs = st.read_records()
    assert [r["run_id"] for r in recs] == ["b"]   # القارئ = الحالي فقط
