# -*- coding: utf-8 -*-
"""TSK-706 (FI-08 / NF-24): حارس دورات الاستيراد — AST-based.

NF-24 وثّق «صفر دورات استيراد» (82 موديولًا) كأصل معماري محمي، وFD-3
جعله baseline يُعاد فحصه بعد كل milestone. هذا السكربت يحوّل الفحص
اليدوي إلى بوابة آلية في check.sh: يبني رسم الاستيرادات الداخلية عبر
AST (بلا تنفيذ أي كود) ويكتشف أي دورة بـ DFS ثلاثي الألوان.

النطاق: كل ملفات .py في حزم المشروع الإنتاجية + server.py — الاختبارات
والسكربتات خارج الرسم (ليست كود إنتاج).

Exit 0 = لا دورات؛ Exit 1 = دورة (تُطبع بمسارها الكامل).
"""
from __future__ import annotations

import ast
import os
import sys

# الحزم الإنتاجية (نفس نطاق بوابة mypy في check.sh + actions/prompts/runners)
PACKAGES = (
    "actions", "chain", "context", "core", "prompts",
    "providers", "routes", "runners", "sessions",
)
TOP_MODULES = ("server",)  # ملفات مفردة على الجذر


def collect_modules(root: str) -> dict[str, str]:
    """اسم الموديول المنقّط → مساره. حزم + ملفات الجذر المفردة."""
    mods: dict[str, str] = {}
    for pkg in PACKAGES:
        pkg_dir = os.path.join(root, pkg)
        if not os.path.isdir(pkg_dir):
            continue
        for dirpath, _dirnames, filenames in os.walk(pkg_dir):
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root)
                dotted = rel[:-3].replace(os.sep, ".")
                if dotted.endswith(".__init__"):
                    dotted = dotted[: -len(".__init__")]
                mods[dotted] = path
    for m in TOP_MODULES:
        p = os.path.join(root, m + ".py")
        if os.path.isfile(p):
            mods[m] = p
    return mods


def internal_imports(path: str, module: str, known: set[str]) -> set[str]:
    """الاستيرادات الداخلية للموديول (تُحل لأقرب موديول معروف)."""
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except SyntaxError as exc:  # ملف إنتاجي لا يُعرب = فشل صريح
        print(f"SYNTAX ERROR in {path}: {exc}", file=sys.stderr)
        sys.exit(1)
    out: set[str] = set()

    def resolve(name: str) -> str | None:
        # أقرب سلف معروف: a.b.c → a.b.c ثم a.b ثم a
        parts = name.split(".")
        for k in range(len(parts), 0, -1):
            cand = ".".join(parts[:k])
            if cand in known:
                return cand
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                r = resolve(alias.name)
                if r and r != module:
                    out.add(r)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # استيراد نسبي — يُحل ضد حزمة الموديول
                base = module.split(".")
                base = base[: len(base) - node.level]
                prefix = ".".join(base)
                name = f"{prefix}.{node.module}" if node.module else prefix
            else:
                name = node.module or ""
            r = resolve(name)
            if r and r != module:
                out.add(r)
            # from X import Y حيث Y موديول فرعي
            for alias in node.names:
                r2 = resolve(f"{name}.{alias.name}" if name else alias.name)
                if r2 and r2 != module:
                    out.add(r2)
    return out


def find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """DFS ثلاثي الألوان — يعيد أول دورة كمسار، أو None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {m: WHITE for m in graph}
    stack: list[str] = []

    def dfs(u: str) -> list[str] | None:
        color[u] = GRAY
        stack.append(u)
        for v in sorted(graph.get(u, ())):
            if color.get(v, WHITE) == GRAY:
                return stack[stack.index(v):] + [v]
            if color.get(v, WHITE) == WHITE:
                found = dfs(v)
                if found:
                    return found
        stack.pop()
        color[u] = BLACK
        return None

    for m in sorted(graph):
        if color[m] == WHITE:
            found = dfs(m)
            if found:
                return found
    return None


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mods = collect_modules(root)
    known = set(mods)
    graph = {
        m: internal_imports(p, m, known) for m, p in sorted(mods.items())
    }
    cycle = find_cycle(graph)
    if cycle:
        print("IMPORT CYCLE DETECTED (NF-24 violated):")
        print("  " + " -> ".join(cycle))
        return 1
    edges = sum(len(v) for v in graph.values())
    print(f"import graph acyclic: {len(graph)} modules, {edges} edges, 0 cycles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
