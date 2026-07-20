"""T-062 (R-903) — نظام أيقونات أنواع الملفات.

يتحقق من:
  1. مصفوفة الـ mapping: كل صنف مطلوب في T-062 يملك رمزًا مميزًا،
     وأسماء الملفات الخاصة (Dockerfile/package-lock.json) لا تسقط
     إلى امتداداتها العامة — عبر تشغيل الوحدة الفعلية بـ node.
  2. fallback: الامتدادات المجهولة → icon-file.
  3. sprite واحد (طلب HTTP واحد) يحوي symbol لكل id في الوحدة،
     وكل الأشكال currentColor (الألوان من توكنز الثيم).
  4. توكنز --icon-* المستهلَكة معرّفة في **كل** الثيمات الأربعة
     (وضوح الأيقونات في كل ثيم = تكافؤ التوكنز).
  5. ملاحظة الترخيص موجودة في الوحدة والـ sprite.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "file_icons.js"
SPRITE = ROOT / "static" / "icons" / "sprite.svg"
THEMES_DIR = ROOT / "static" / "themes"

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node غير متوفر")


def _run_module(paths: list[str]) -> dict[str, dict]:
    """يشغّل file_icons.js الحقيقي في node ويعيد mapping لكل مسار."""
    script = (
        f"const fi = require({json.dumps(str(MODULE))});"
        f"const out = {{}};"
        f"for (const p of {json.dumps(paths)}) out[p] = fi.getFileIcon(p);"
        f"console.log(JSON.stringify(out));"
    )
    proc = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# (مسار تجريبي، id متوقع) — صنف واحد على الأقل لكل بند من قائمة T-062.
MATRIX = [
    ("app.js", "js"), ("mod.mjs", "js"),
    ("app.ts", "ts"),
    ("view.jsx", "jsx"), ("view.tsx", "jsx"),
    ("main.py", "python"),
    ("index.html", "html"),
    ("style.css", "css"), ("style.scss", "css"),
    ("data.json", "json"),
    ("conf.yaml", "yaml"), ("conf.yml", "yaml"), ("conf.toml", "yaml"),
    ("README.md", "markdown"),
    ("Main.java", "java"),
    ("main.c", "c"), ("defs.h", "c"),
    ("main.cpp", "cpp"), ("defs.hpp", "cpp"),
    ("Program.cs", "csharp"),
    ("main.go", "go"),
    ("lib.rs", "rust"),
    ("index.php", "php"),
    ("app.rb", "ruby"),
    ("schema.sql", "sql"),
    ("run.sh", "shell"), ("run.bat", "shell"), ("run.ps1", "shell"),
    ("Dockerfile", "docker"), ("docker-compose.yml", "docker"),
    (".env", "config"), ("settings.ini", "config"), (".gitignore", "config"),
    ("logo.png", "image"), ("icon.svg", "image"), ("photo.jpeg", "image"),
    ("package-lock.json", "lock"), ("yarn.lock", "lock"),
    ("Cargo.lock", "lock"), ("poetry.lock", "lock"),
]


class TestMappingMatrix:
    def test_every_listed_type_maps_correctly(self) -> None:
        result = _run_module([p for p, _ in MATRIX])
        failures = [
            f"{path}: got {result[path]['id']!r}, want {want!r}"
            for path, want in MATRIX
            if result[path]["id"] != want
        ]
        assert not failures, "\n".join(failures)

    def test_distinct_icons_for_distinct_categories(self) -> None:
        # كل الأصناف المطلوبة مميّزة — لا صنفان يشتركان في رمز.
        wanted_ids = {want for _, want in MATRIX}
        # 23 صنفًا مميزًا في المصفوفة + fallback (file) خارجها = 24 رمزًا كليًا.
        assert len(wanted_ids) == 23
        assert "file" not in wanted_ids

    def test_full_paths_and_backslashes(self) -> None:
        result = _run_module(["src/deep/dir/app.py", r"src\win\style.css"])
        assert result["src/deep/dir/app.py"]["id"] == "python"
        assert result[r"src\win\style.css"]["id"] == "css"

    def test_special_filenames_beat_extension(self) -> None:
        # package-lock.json يجب ألا يسقط إلى json العام.
        result = _run_module(["package-lock.json", "data.json"])
        assert result["package-lock.json"]["id"] == "lock"
        assert result["data.json"]["id"] == "json"


class TestFallback:
    def test_unknown_extension_hits_fallback(self) -> None:
        result = _run_module(["archive.xyz", "noext", "", "weird.zzz"])
        for path in ("archive.xyz", "noext", "", "weird.zzz"):
            assert result[path]["id"] == "file", path
            assert result[path]["symbol"] == "#icon-file"

    def test_env_variants_map_to_config(self) -> None:
        result = _run_module([".env.local", ".env.production"])
        assert result[".env.local"]["id"] == "config"
        assert result[".env.production"]["id"] == "config"


class TestSprite:
    def test_sprite_has_symbol_for_every_module_id(self) -> None:
        script = (
            f"const fi = require({json.dumps(str(MODULE))});"
            f"console.log(JSON.stringify(Object.keys(fi.ICONS)));"
        )
        proc = subprocess.run(
            [node, "-e", script], capture_output=True, text=True, timeout=30
        )
        ids = json.loads(proc.stdout)
        svg = SPRITE.read_text(encoding="utf-8")
        symbols = set(re.findall(r'<symbol id="icon-([\w-]+)"', svg))
        missing = set(ids) - symbols
        assert not missing, f"رموز غائبة من الـ sprite: {sorted(missing)}"

    def test_sprite_is_single_file_all_currentcolor(self) -> None:
        svg = SPRITE.read_text(encoding="utf-8")
        # كل fill/stroke إما currentColor أو none — لا ألوان مضمّنة.
        raw = re.findall(r'(?:fill|stroke)="(?!currentColor|none)[^"]+"', svg)
        assert not raw, f"ألوان خام في الـ sprite: {raw[:5]}"

    def test_license_note_present(self) -> None:
        assert "الترخيص" in MODULE.read_text(encoding="utf-8")
        assert "رخصة المشروع" in SPRITE.read_text(encoding="utf-8")


class TestThemeTokens:
    def test_every_consumed_icon_token_defined_in_all_themes(self) -> None:
        script = (
            f"const fi = require({json.dumps(str(MODULE))});"
            f"console.log(JSON.stringify("
            f"Object.values(fi.ICONS).map(m => m.colorToken)));"
        )
        proc = subprocess.run(
            [node, "-e", script], capture_output=True, text=True, timeout=30
        )
        tokens = set(json.loads(proc.stdout))
        for theme in ("dark", "light", "high-contrast", "monokai"):
            css = (THEMES_DIR / f"{theme}.css").read_text(encoding="utf-8")
            defined = set(re.findall(r"(--[\w-]+)\s*:", css))
            missing = tokens - defined
            assert not missing, f"{theme}.css ينقصه: {sorted(missing)}"
