# -*- coding: utf-8 -*-
"""TSK-726a (P2-4 / FI-07 / D-10) — حارس التقسيم-التسلسلي المحافظ.

يتحقق آليًا من (معايير القبول — DEVELOPMENT_TASKS §TSK-726/726a):
  1. ترتيب التحميل في index.html: وحدات UMD-lite (static/js/*.js) ثم
     app.js ثم مقاطع static/js/app/NN بالترتيب الرقمي — CP_ACTIONS
     تقيّم مراجع دوال app.js عند التحميل فيلزم أن يسبقها (عقد
     eval-time المصحَّح في S103).
  2. كل مقطع app/NN مذكور في index.html (لا ملف يتيم لا يُحمَّل).
  3. كل دوال onclick المضمّنة في index.html معرَّفة top-level في
     مجموع الحزمة (app.js + المقاطع).
  4. لا ازدواج تعريف دالة top-level عبر ملفات الحزمة.
  5. node --check لكل ملف في الحزمة (صلاحية نحوية مستقلة).
  6. النقل حرفي: المقاطع لا تعيد تعريف state/الثوابت العامة.

يعمل بعد **كل** شريحة 726x — الحارس الدائم للتقسيم.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static" / "app.js"
APP_SPLIT_DIR = ROOT / "static" / "js" / "app"
INDEX_HTML = ROOT / "static" / "index.html"

node = shutil.which("node")


def _split_files() -> list[Path]:
    return sorted(APP_SPLIT_DIR.glob("*.js"))


def _bundle_files() -> list[Path]:
    return [APP_JS] + _split_files()


def _top_level_functions(src: str) -> list[str]:
    return re.findall(r"^(?:async )?function ([A-Za-z_]\w*)", src, re.M)


class TestLoadOrder:
    def test_split_dir_exists_with_files(self):
        assert APP_SPLIT_DIR.is_dir()
        assert _split_files(), "مجلد التقسيم فارغ؟"

    def test_index_order_umd_then_app_then_segments(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        app_pos = html.index("app.js?v=")
        # كل وحدات UMD-lite (static/js/*.js — ليست app/) قبل app.js
        for m in re.finditer(r'src="/static/js/([^"/]+\.js)\?', html):
            pos = m.start()
            assert pos < app_pos, f"وحدة UMD بعد app.js: {m.group(1)}"
        # كل مقاطع app/NN بعد app.js وبالترتيب الرقمي
        seg_positions = [
            (m.group(1), m.start())
            for m in re.finditer(r'src="/static/js/app/([^"]+\.js)\?', html)
        ]
        assert seg_positions, "لا مقاطع محمَّلة في index.html"
        names = [n for n, _ in seg_positions]
        assert names == sorted(names), "المقاطع ليست بالترتيب الرقمي"
        for name, pos in seg_positions:
            assert pos > app_pos, f"مقطع قبل app.js (خطر eval-time): {name}"

    def test_every_segment_file_is_loaded(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        for f in _split_files():
            assert f"/static/js/app/{f.name}?" in html, f"مقطع يتيم: {f.name}"


class TestGlobalsIntegrity:
    def test_all_onclick_functions_defined_in_bundle(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        wanted = set(re.findall(r'onclick="([A-Za-z_]\w*)\(', html))
        wanted.discard("document")
        assert wanted, "لا onclick في index.html؟"
        defined: set[str] = set()
        for f in _bundle_files():
            defined |= set(_top_level_functions(f.read_text(encoding="utf-8")))
        missing = wanted - defined
        assert not missing, f"دوال onclick بلا تعريف top-level: {sorted(missing)}"

    def test_no_duplicate_function_definitions_across_bundle(self):
        seen: dict[str, str] = {}
        dups: list[str] = []
        for f in _bundle_files():
            for fn in _top_level_functions(f.read_text(encoding="utf-8")):
                if fn in seen:
                    dups.append(f"{fn} ({seen[fn]} + {f.name})")
                else:
                    seen[fn] = f.name
        assert not dups, f"ازدواج تعريف: {dups}"

    def test_segments_do_not_redefine_core_state(self):
        for f in _split_files():
            src = f.read_text(encoding="utf-8")
            assert not re.search(r"^const state\b", src, re.M), \
                f"{f.name} يعيد تعريف state"
            assert "function sendMessage" not in src or f.name.startswith("9"), \
                f"{f.name} يحوي قلب الدردشة قبل 726e"


@pytest.mark.skipif(node is None, reason="node غير متوفر")
class TestSyntax:
    def test_node_check_every_bundle_file(self):
        for f in _bundle_files():
            proc = subprocess.run(
                [node, "--check", str(f)],
                capture_output=True, text=True, timeout=60,
            )
            assert proc.returncode == 0, f"{f.name}: {proc.stderr}"
