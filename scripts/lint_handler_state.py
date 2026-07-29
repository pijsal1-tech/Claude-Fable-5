#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-048 (R-701): بوابة lint — ممنوع حالة وحدوية متغيّرة في الـ handlers.

القاعدة (قواعد نطاق الحالة كاملة في core/session_context.py):
دوال معالجة رسائل WS تأخذ ``(ctx, sctx, msg)`` — كل حالة المحادثة عبر
``sctx`` حصريًا. داخل أي دالة handler يُمنع:

1. أي عبارة ``global`` — الكتابة الوحدوية من handler هي جوهر خلل
   "تبويبان يخربان حالة بعضهما".
2. أي قراءة/كتابة لاسم وحدوي مربوط بقيمة قابلة للتغيير
   (list/dict/set literal أو نداء list()/dict()/set()) أو لاسم من
   قائمة حالة المحادثة المعروفة — حتى لو أُعيد ربطه لاحقًا في main().

المسموح: الثوابت UPPER_CASE، الدوال/الأصناف الوحدوية، ومعاملات الدالة
(``ctx``/``sctx``/``msg`` تظلّل أي اسم وحدوي مطابق).

الاستخدام:
    python3 scripts/lint_handler_state.py [ملف ...]
بلا وسائط يفحص server.py. يطبع الانتهاكات ويخرج 1 عند وجود أي انتهاك.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# دوال الـ handlers الخاضعة للقاعدة (أنماط prefix-match على اسم الدالة)
# TSK-611 (ADR-001): "_ws_" يلتقط مقابض جدول dispatch المستخرجة —
# نفس قاعدة T-048 تتبع المقابض أينما انتقلت.
HANDLER_NAMES = ("ws_handler", "_handle_ws_message", "_apply_single_action",
                 "_ws_")

# أسماء حالة المحادثة الوحدوية المعروفة — ممنوعة داخل الـ handlers حتى
# لو لم يلتقطها كشف الـ literals (تُربط في main() بقيم غير literal).
KNOWN_CONVERSATION_STATE = frozenset({
    "chat_history", "fm", "cmd_runner", "session_mgr", "provider",
    "_binding_banner", "delegate_bridge", "chain_bridge",
    "_active_agent_loop", "_backup_done_for_batch",
})

_MUTABLE_NODES = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp,
                  ast.SetComp)
_MUTABLE_CALLS = ("list", "dict", "set")


def _module_mutable_names(tree: ast.Module) -> set[str]:
    """أسماء وحدوية مربوطة بقيمة قابلة للتغيير (الثوابت UPPER مستثناة)."""
    names: set[str] = set()
    for node in tree.body:
        targets: list[ast.expr] = []
        value = None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        if value is None:
            continue
        mutable = isinstance(value, _MUTABLE_NODES) or (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in _MUTABLE_CALLS)
        if not mutable:
            continue
        for t in targets:
            if isinstance(t, ast.Name) and not t.id.isupper():
                names.add(t.id)
    return names


def _handler_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name.startswith(HANDLER_NAMES)]


def _local_bindings(fn: ast.FunctionDef) -> set[str]:
    """معاملات الدالة + كل اسم يُربط محليًا — تظليل مشروع."""
    bound = {a.arg for a in (fn.args.args + fn.args.posonlyargs
                             + fn.args.kwonlyargs)}
    if fn.args.vararg:
        bound.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        bound.add(fn.args.kwarg.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node is not fn:
                bound.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
    return bound


def lint_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    banned = _module_mutable_names(tree) | KNOWN_CONVERSATION_STATE
    violations: list[str] = []
    for fn in _handler_functions(tree):
        shadowed = _local_bindings(fn)
        for node in ast.walk(fn):
            if isinstance(node, ast.Global):
                violations.append(
                    f"{path}:{node.lineno}: `global {', '.join(node.names)}` "
                    f"داخل handler `{fn.name}` — الحالة عبر sctx حصريًا")
            elif isinstance(node, ast.Name) and node.id in banned \
                    and node.id not in shadowed:
                violations.append(
                    f"{path}:{node.lineno}: قراءة حالة وحدوية `{node.id}` "
                    f"داخل handler `{fn.name}` — انقلها إلى sctx")
    return violations


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] or [Path("server.py")]
    all_violations: list[str] = []
    for f in files:
        all_violations.extend(lint_file(f))
    if all_violations:
        print("handler module-level state violations:")
        for v in all_violations:
            print("  " + v)
        return 1
    print(f"handler state clean ({', '.join(str(f) for f in files)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
