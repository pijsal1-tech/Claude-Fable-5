# -*- coding: utf-8 -*-
"""T-048 migration: extract ws_handler ladder -> _handle_ws_message(ctx, sctx, msg)."""
import ast
import re

SRC = "server.py"
src = open(SRC, encoding="utf-8").read()
lines = src.split("\n")

# ── dynamic anchors (AST) ──
tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
          and n.name == "ws_handler")
loop = next(n for n in fn.body if isinstance(n, ast.While))
msg_ln = next(i + 1 for i, l in enumerate(lines)
              if l.strip() == 'msg_type = data.get("type", "")')
ladder_start = msg_ln + 1                 # line after msg_type (blank)
ladder_end = loop.body[-1].end_lineno     # last stmt of while body
fn_end = fn.end_lineno                    # end of ws_handler (old cleanup)


class V(ast.NodeVisitor):
    def __init__(self):
        self.d = 0
        self.cont = []
        self.gl = []

    def visit_For(self, n):
        self.d += 1
        self.generic_visit(n)
        self.d -= 1

    def visit_While(self, n):
        self.d += 1
        self.generic_visit(n)
        self.d -= 1

    def visit_Continue(self, n):
        if self.d == 0:
            self.cont.append(n.lineno)

    def visit_FunctionDef(self, n):
        for x in ast.walk(n):
            if isinstance(x, ast.Global):
                self.gl.append(x.lineno)


v = V()
for s in loop.body:
    v.visit(s)
CONTINUES = set(v.cont)
GLOBAL_STMTS = set(v.gl)

ladder = []
for n in range(ladder_start, ladder_end + 1):
    l = lines[n - 1]
    if n in GLOBAL_STMTS:
        continue
    if n in CONTINUES:
        assert l.strip().startswith("continue"), (n, l)
        l = l.replace("continue", "return", 1)
    if l.startswith("    "):
        l = l[4:]
    ladder.append(l)
body = "\n".join(ladder)

# ── switch-project block rewrite (before generic substitutions) ──
old_block = """            try:
                # R-102 (T-008): switch through the composition root.
                if ctx is not None:
                    _handle = ctx.switch_project(detected_dir)
                    fm = _handle.fm
                    cmd_runner = _handle.cmd_runner
                else:
                    fm = FileManager(detected_dir)
                    cmd_runner = CommandRunner(cwd=detected_dir, auto_approve=True)"""
new_block = """            try:
                # T-048 (R-701): تبديل مشروع **هذا الاتصال فقط** — مقبض
                # التبويبات الأخرى يبقى صالحًا (ctx.project لا يُبدَّل).
                if ctx is not None:
                    sctx.switch_project(detected_dir)
                else:
                    sctx.project = ProjectHandle(
                        root=detected_dir,
                        fm=FileManager(detected_dir),
                        cmd_runner=CommandRunner(cwd=detected_dir,
                                                 auto_approve=True))"""
assert old_block in body, "switch block not found"
body = body.replace(old_block, new_block)

# ── name sweep: conversation state -> sctx ──
subs = [
    (r"\b_ws_frame\(", "sctx.send("),
    (r"_json_sender\(ws\)", "sctx.send"),
    (r"(?<!\.)\bchat_history\b", "sctx.chat_history"),
    (r"(?<!\.)\bsession_mgr\b", "sctx.session_mgr"),
    (r"(?<!\.)\b_binding_banner\b", "sctx.binding_banner"),
    (r"(?<!\.)\b_active_agent_loop\b", "sctx.active_agent_loop"),
    (r"(?<!\.)\bdelegate_bridge\b", "sctx.delegate_bridge"),
    (r"(?<!\.)\bchain_bridge\b", "sctx.chain_bridge"),
    (r"(?<!\.)\b_backup_done_for_batch\b", "sctx.backup_done_for_batch"),
    (r"\b_active_provider\(\)", "sctx.active_provider()"),
    (r"(?<!\.)\bfm\.(?=[A-Za-z_])", "sctx.fm."),
    (r"_apply_single_action\(action\)", "_apply_single_action(action, sctx)"),
    (r"(?<!\.)\bdata\b", "msg"),
]
for pat, rep in subs:
    body = re.sub(pat, rep, body)

handler_src = '''def _build_session_context(ws):
    """T-048 (R-701): موقع التركيب — يبني SessionContext لاتصال WS جديد.

    هذا **ليس** handler: قراءات globals الوحدة هنا هي نقطة الربط
    الوحيدة المسموحة (بذر الحالة المشتركة وقت الاتصال) — بعدها كل
    وصول الـ handlers للحالة عبر sctx حصريًا (يفرضه
    scripts/lint_handler_state.py). قواعد نطاق الحالة كاملة في
    core/session_context.py.
    """
    bus = EventBus()
    adapter = _WSAdapter(ws, bus)
    project = None
    if ctx is not None:
        project = ctx.project
    elif fm is not None:
        project = ProjectHandle(root=str(fm.root), fm=fm,
                                cmd_runner=cmd_runner)
    return SessionContext(
        send=_frame_publisher(bus),
        ctx=ctx,
        bus=bus,
        adapter=adapter,
        project=project,
        chat_history=list(chat_history),
        session_mgr=session_mgr,
        chain_bridge=chain_bridge,
        delegate_bridge=delegate_bridge,
        provider_source=_active_provider,
        banner_source=lambda: _binding_banner,
    )


def _handle_ws_message(ctx, sctx, msg):
    """T-048 (R-701): معالجة رسالة WS واحدة — كل حالة المحادثة عبر sctx.

    ``ctx`` خدمات العملية المشتركة (composition root)؛ ``sctx`` حالة
    هذا الاتصال (تاريخ، مقبض مشروع، موافقات، موديل، إرسال). ممنوع
    ``global`` وأي كتابة حالة محادثة وحدوية هنا — تفرضه بوابة
    scripts/lint_handler_state.py في check.sh.
    """
    msg_type = msg.get("type", "")

''' + body + '''

def ws_handler(ws):
    """WebSocket للتواصل الحي مع AI — T-048: الحالة في SessionContext."""
    sctx = _build_session_context(ws)
    try:
        while True:
            try:
                raw = ws.receive()
                if not raw:
                    break
                data = json.loads(raw)
            except Exception:
                break
            _handle_ws_message(ctx, sctx, data)
    finally:
        # ── WebSocket Disconnected Cleanup (T-048: idempotent عبر sctx) ──
        print("🔌 WebSocket disconnected. Cleaning up and cancelling active tasks...")
        sctx.close()
'''

new_lines = (lines[:fn.lineno - 1] + handler_src.split("\n")
             + lines[fn_end:])
text = "\n".join(new_lines)

# ── _apply_single_action: sctx-scoped ──
old_apply = '''def _apply_single_action(action: dict) -> dict:
    """تطبيق إجراء واحد — مع باك-أب إلزامي قبل أي تعديل"""
    global _backup_done_for_batch
    act_type = action.get("action", "")

    try:
        # باك-أب كامل قبل أول تعديل في الـ batch
        if not _backup_done_for_batch and act_type in ("create_file", "edit_file"):
            try:
                backup_path = fm.create_full_backup()
                _backup_done_for_batch = True
                if backup_path:
                    print(f"🛡️ Full backup created: {backup_path}")
            except Exception as e:
                print(f"⚠️ Backup warning: {e}")
                _backup_done_for_batch = True  # لا نوقف التنفيذ بسبب فشل الباك-أب

        if act_type == "create_file":
            path = action["path"]
            content = action["content"]
            saved = fm.write_file(path, content)
            return {"ok": True, "message": f"تم حفظ: {saved}"}

        elif act_type == "edit_file":
            path = action["path"]
            fm.edit_file(path, action["old_text"], action["new_text"])
            return {"ok": True, "message": f"تم تعديل: {path}"}

        elif act_type == "run_command":
            result = cmd_runner.run(action["command"], need_approval=False)
            return {"ok": result["success"], "message": result["output"] or result["error"]}'''
new_apply = '''def _apply_single_action(action: dict, sctx) -> dict:
    """تطبيق إجراء واحد — مع باك-أب إلزامي قبل أي تعديل.

    T-048 (R-701): يعمل على مشروع الاتصال (sctx.fm/cmd_runner) وعلم
    الباك-أب لكل اتصال — لا حالة وحدوية.
    """
    act_type = action.get("action", "")

    try:
        # باك-أب كامل قبل أول تعديل في الـ batch
        if not sctx.backup_done_for_batch and act_type in ("create_file", "edit_file"):
            try:
                backup_path = sctx.fm.create_full_backup()
                sctx.backup_done_for_batch = True
                if backup_path:
                    print(f"🛡️ Full backup created: {backup_path}")
            except Exception as e:
                print(f"⚠️ Backup warning: {e}")
                sctx.backup_done_for_batch = True  # لا نوقف التنفيذ بسبب فشل الباك-أب

        if act_type == "create_file":
            path = action["path"]
            content = action["content"]
            saved = sctx.fm.write_file(path, content)
            return {"ok": True, "message": f"تم حفظ: {saved}"}

        elif act_type == "edit_file":
            path = action["path"]
            sctx.fm.edit_file(path, action["old_text"], action["new_text"])
            return {"ok": True, "message": f"تم تعديل: {path}"}

        elif act_type == "run_command":
            result = sctx.cmd_runner.run(action["command"], need_approval=False)
            return {"ok": result["success"], "message": result["output"] or result["error"]}'''
assert old_apply in text, "_apply_single_action not found"
text = text.replace(old_apply, new_apply)

# ── delete swept module globals ──
old_g1 = "_backup_done_for_batch = False  # علامة لمنع تكرار الباك-أب في نفس الـ batch\n"
assert old_g1 in text
text = text.replace(old_g1, "")
old_g2 = "_active_agent_loop: AgentLoop = None        # Agent Loop النشط حالياً\n"
assert old_g2 in text
text = text.replace(old_g2, "")

# ── import SessionContext ──
old_imp = "from core.execution import ExecutionRegistry"
assert old_imp in text
text = text.replace(old_imp,
                    old_imp + "\nfrom core.session_context import SessionContext",
                    1)

open(SRC, "w", encoding="utf-8").write(text)
print("migration written OK")
