"""T-065 (R-901) — لوحة مراجعة الـ Diff: عقد WS + الرندر + الأداء.

يتحقق من:
  1. **عقد WS (contract)**: أطر القرار الصادرة من الوحدة تطابق حرفيًا ما
     تتوقعه ApprovalGate الفعلية — نُشغّل البوابة الحقيقية (core.approval)
     في وضع interactive، نُمرر إطار chain_approval_request الفعلي للوحدة
     (node)، ونُعيد إطارها الناتج إلى gate.resolve: قبول الدفعة، رفض
     الدفعة، per-file toggles (كلها مقبولة ⇒ approved، أي رفض ⇒ deny)،
     وأن request_id/payload_hash يُعادان **حرفيًا** (تلاعب ⇒ لا مطابقة).
  2. **golden render**: طلب مختلط من 5 ملفات (write جديد/معدّل/كبير +
     delete + command) — بنية HTML مثبتة: رؤوس بأيقونات T-063 وعدادات
     +/−، صفوف ctx/add/del بأرقام أسطر صحيحة، صياغة hljs تحت طبقة
     add/del، ووضعا unified/split.
  3. **perf**: diff لملف 3000 سطر (تعديل متناثر) يُحسب سريعًا ونافذة
     الـ virtualization ترسم 80 صفًا فقط مهما كبر الملف، مع spacers
     تحفظ الارتفاع (rowCount يطابق مجموع الصفوف).
  4. **Regression (auto mode)**: البوابة في وضع auto مع whitelist تُصدر
     verdict بلا أي إطار للواجهة — اللوحة لا تُفتح أصلًا (قناة on_request
     لا تُستدعى)، أي أن الوضع التلقائي غير متأثر باللوحة.
  5. **schema موثّق ومثبّت**: رأس diff_panel.js يوثّق شكل الإطارين
     (request/response) — وحقول الإطار الفعلي من ApprovalRequest.to_dict
     تطابق ما يستهلكه openState.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "static" / "js" / "diff_panel.js"
APP_JS = ROOT / "static" / "app.js"
APP_SPLIT_DIR = ROOT / "static" / "js" / "app"


def _app_bundle() -> str:
    """TSK-726 (FI-07): «حزمة app» = app.js + مقاطع app/NN بالترتيب —
    المكافئ الحرفي لتسلسل app.js قبل التقسيم (التأكيدات كما هي)."""
    parts = [APP_JS.read_text(encoding="utf-8")]
    for f in sorted(APP_SPLIT_DIR.glob("*.js")):
        parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)
INDEX_HTML = ROOT / "static" / "index.html"
STYLE_CSS = ROOT / "static" / "style.css"

sys.path.insert(0, str(ROOT))

from core.approval import ApprovalGate, ApprovalRequest, ProposedAction  # noqa: E402

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node غير متوفر")


def run_node(script: str) -> str:
    proc = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def make_request() -> ApprovalRequest:
    return ApprovalRequest(
        actions=[
            ProposedAction(kind="write", target="app/main.py",
                           payload="x = 1\nprint(x)\n", summary="تعديل main"),
            ProposedAction(kind="delete", target="old/util.js",
                           payload="", summary="حذف قديم"),
        ],
        source="chain", run_id="run-77",
    )


def panel_decision(frame: dict, script_body: str) -> dict:
    """يفتح الحالة في الوحدة الفعلية وينفّذ script_body ثم يطبع الإطار."""
    out = run_node(
        "const DP=require('./static/js/diff_panel.js');"
        f"const frame={json.dumps(frame)};"
        "const st=DP.openState(frame,{'app/main.py':'x = 0\\n','old/util.js':'old();\\n'});"
        + script_body +
        "console.log(JSON.stringify(out));"
    )
    return json.loads(out)


class TestWSContract:
    """أطر اللوحة ↔ ApprovalGate الفعلية — 1:1."""

    def _run_gate(self, decision_script: str,
                  tamper=None) -> tuple[bool, str]:
        """يشغّل البوابة الحقيقية interactive ويحلّها بإطار اللوحة."""
        import threading

        gate = ApprovalGate(mode="interactive", timeout_seconds=10)
        req = make_request()
        captured: dict = {}

        def on_request(frame: dict) -> None:
            captured.update(frame)

        result: dict = {}

        def runner() -> None:
            result["verdict"] = gate.request(req, on_request=on_request)

        t = threading.Thread(target=runner)
        t.start()
        # انتظر التقاط الإطار (البوابة أرسلته قبل wait)
        for _ in range(100):
            if captured:
                break
            t.join(timeout=0.05)
        assert captured, "البوابة لم تُصدر إطار طلب"

        # نفس ما يفعله bridge: يضيف type فوق req.to_dict()
        ws_frame = {"type": "chain_approval_request", **captured}
        panel_frame = panel_decision(ws_frame, decision_script)
        assert panel_frame["type"] == "chain_approval_response"
        if tamper:
            panel_frame = tamper(panel_frame)
        # نفس ما يفعله server.py مع chain_approval_response
        matched = gate.resolve(
            request_id=panel_frame.get("request_id", ""),
            approved=panel_frame.get("approved", False),
            payload_hash=panel_frame.get("payload_hash", ""),
        )
        t.join(timeout=10)
        verdict = result["verdict"]
        return (verdict.approved if matched else None), verdict.reason

    def test_batch_approve_all_maps_to_user_approved(self) -> None:
        approved, reason = self._run_gate("const out=DP.decisionFrame(st,true);")
        assert approved is True and reason == "user_approved"

    def test_batch_reject_all_maps_to_user_denied(self) -> None:
        approved, reason = self._run_gate("const out=DP.decisionFrame(st,false);")
        assert approved is False and reason == "user_denied"

    def test_per_file_all_accepted_confirm_approves(self) -> None:
        approved, reason = self._run_gate(
            "DP.setFileDecision(st,0,true);DP.setFileDecision(st,1,true);"
            "const out=DP.decisionFrame(st,null);"
        )
        assert approved is True and reason == "user_approved"

    def test_per_file_any_rejected_confirm_denies(self) -> None:
        approved, reason = self._run_gate(
            "DP.setFileDecision(st,1,false);const out=DP.decisionFrame(st,null);"
        )
        assert approved is False and reason == "user_denied"

    def test_tampered_hash_does_not_match_gate(self) -> None:
        def tamper(f: dict) -> dict:
            f["payload_hash"] = "0" * 64
            return f
        approved, reason = self._run_gate(
            "const out=DP.decisionFrame(st,true);", tamper=tamper)
        # لا مطابقة ⇒ resolve أعاد False ⇒ البوابة انتهت timeout/رفض
        assert approved is None
        assert reason == "timeout"

    def test_frame_echoes_ids_verbatim(self) -> None:
        req = make_request()
        ws_frame = {"type": "chain_approval_request", **req.to_dict()}
        frame = panel_decision(ws_frame, "const out=DP.decisionFrame(st,true);")
        assert frame["request_id"] == req.request_id
        assert frame["payload_hash"] == req.payload_hash


GOLDEN_ACTIONS = [
    {"kind": "write", "target": "src/app.py",
     "payload": "def f():\n    return 2\n", "summary": "تعديل"},
    {"kind": "write", "target": "src/new.js",
     "payload": "const a = 1;\n", "summary": "ملف جديد"},
    {"kind": "delete", "target": "src/dead.css", "payload": "", "summary": "حذف"},
    {"kind": "command", "target": "pytest -q", "payload": "pytest -q",
     "summary": "تشغيل الاختبارات"},
    {"kind": "write", "target": "docs/README.md",
     "payload": "# Title\nnew line\n", "summary": "توثيق"},
]
GOLDEN_OLD = {
    "src/app.py": "def f():\n    return 1\n",
    "src/new.js": "",
    "src/dead.css": ".x { color: var(--t) }\n",
    "docs/README.md": "# Title\n",
}


class TestGoldenRender:
    def _state_and_render(self) -> dict:
        out = run_node(
            "const DP=require('./static/js/diff_panel.js');"
            f"const frame={{request_id:'g1',payload_hash:'h',actions:{json.dumps(GOLDEN_ACTIONS)}}};"
            f"const st=DP.openState(frame,{json.dumps(GOLDEN_OLD)});"
            "const headers=st.files.map((f,i)=>DP.renderFileHeaderHTML(f,i,st));"
            "const unified=st.files.map(f=>f.rows?DP.renderUnifiedRowsHTML(f,0,999):null);"
            "const split=st.files.map(f=>f.rows?DP.renderSplitRowsHTML(f,0,999):null);"
            "console.log(JSON.stringify({counts:st.files.map(f=>[f.addCount,f.delCount]),"
            "langs:st.files.map(f=>f.lang),headers,unified,split}));"
        )
        return json.loads(out)

    def test_golden_counts_and_langs(self) -> None:
        r = self._state_and_render()
        # app.py: سطر بُدّل (del+add)؛ new.js: سطر + سطر فارغ ختامي (\n نهائي)؛
        # dead.css: حذف سطر + الختامي؛ command: بلا rows؛ README: إضافة سطر
        # (الختامي الفارغ مشترك فيُقص كـ suffix).
        assert r["counts"] == [[1, 1], [2, 0], [0, 2], [0, 0], [1, 0]]
        assert r["langs"] == ["python", "javascript", "css", None, "markdown"]

    def test_golden_headers_icons_counts_decisions(self) -> None:
        r = self._state_and_render()
        for i, h in enumerate(r["headers"]):
            if GOLDEN_ACTIONS[i]["kind"] in ("write", "delete"):
                assert '<svg class="file-icon"' in h, f"header {i} بلا أيقونة"
                assert "sprite.svg#icon-" in h
            else:
                assert "diff-kind-badge" in h  # command ⇒ شارة نوع
            assert "diff-file-decision accepted" in h  # افتراضيًا مقبول
        assert "+1" in r["headers"][0] and "−1" in r["headers"][0]

    def test_golden_unified_rows_structure(self) -> None:
        r = self._state_and_render()
        app_py = r["unified"][0]
        # ctx ثم del(القديم) ثم add(الجديد) — بأرقام أسطر صحيحة
        assert app_py.index('diff-row ctx') < app_py.index('diff-row del')
        assert app_py.index('diff-row del') < app_py.index('diff-row add')
        assert "hljs-keyword" in app_py  # صياغة تحت طبقة add/del
        assert 'class="diff-sign">+' in app_py.replace("&#x2212;", "−") or ">+<" in app_py
        # الحذف الكامل: dead.css صف del فقط
        assert 'diff-row del' in r["unified"][2]
        assert 'diff-row add' not in r["unified"][2]
        # command بلا rows
        assert r["unified"][3] is None

    def test_golden_split_rows_pair_del_with_add(self) -> None:
        r = self._state_and_render()
        app_py_split = r["split"][0]
        rows = app_py_split.count('diff-row split')
        # ctx + زوج (del|add) مصفوف جنبًا لجنب + ctx فارغ ختامي = 3 صفوف
        # (الزوج أقل من unified الذي يفرد del ثم add في صفين)
        assert rows == 3
        u_rows = r["unified"][0].count('diff-row ')
        assert u_rows == 4  # ctx + del + add + ctx
        assert app_py_split.count("diff-split-side") == 2 * rows

    def test_rows_escape_html_in_code(self) -> None:
        out = run_node(
            "const DP=require('./static/js/diff_panel.js');"
            "const f=DP.buildFile({kind:'write',target:'a.xyz',"
            "payload:'<script>alert(1)</script>'},'');"
            "console.log(DP.renderUnifiedRowsHTML(f,0,10));"
        )
        assert "<script>alert" not in out
        assert "&lt;script&gt;" in out


class TestVirtualizationPerf:
    def test_3k_line_diff_fast_and_windowed(self) -> None:
        out = run_node(
            "const DP=require('./static/js/diff_panel.js');"
            "const oldT=Array.from({length:3000},(_,i)=>'line '+i).join('\\n');"
            "const newT=Array.from({length:3000},(_,i)=>i%9===4?'CHANGED '+i:'line '+i).join('\\n');"
            "const t0=Date.now();"
            "const f=DP.buildFile({kind:'write',target:'big.py',payload:newT},oldT);"
            "const buildMs=Date.now()-t0;"
            "const t1=Date.now();"
            "const win=DP.renderUnifiedRowsHTML(f,1600,80);"
            "const renderMs=Date.now()-t1;"
            "console.log(JSON.stringify({buildMs,renderMs,"
            "total:DP.rowCount(f,'unified'),"
            "winRows:(win.match(/diff-row/g)||[]).length,"
            "adds:f.addCount,dels:f.delCount}));"
        )
        r = json.loads(out)
        assert r["buildMs"] < 2000, f"diff بطيء: {r['buildMs']}ms"
        assert r["renderMs"] < 200, f"نافذة بطيئة: {r['renderMs']}ms"
        assert r["winRows"] == 80  # النافذة فقط — لا الملف كله
        assert r["adds"] == r["dels"] > 300  # التعديل المتناثر كله مرصود
        assert r["total"] == 3000 + r["adds"]  # spacers تحفظ الإجمالي

    def test_row_count_split_vs_unified(self) -> None:
        out = run_node(
            "const DP=require('./static/js/diff_panel.js');"
            "const f=DP.buildFile({kind:'write',target:'a.py',"
            "payload:'x\\ny2\\nz'},'x\\ny\\nz');"
            "console.log(JSON.stringify({u:DP.rowCount(f,'unified'),"
            "s:DP.rowCount(f,'split')}));"
        )
        r = json.loads(out)
        assert r["u"] == 4  # ctx + del + add + ctx
        assert r["s"] == 3  # ctx + زوج(del|add) + ctx


class TestKeyboardShortcuts:
    def test_key_map(self) -> None:
        out = run_node(
            "const DP=require('./static/js/diff_panel.js');"
            "const st={files:[1,2,3],activeFile:1};"
            "const keys=['a','r','Enter','Escape','u','x','j','k','q'];"
            "console.log(JSON.stringify(keys.map(k=>DP.handleKey(st,k))));"
        )
        acts = json.loads(out)
        assert acts[0] == {"action": "approve_all"}
        assert acts[1] == {"action": "reject_all"}
        assert acts[2] == {"action": "confirm"}
        assert acts[3] == {"action": "reject_all"}
        assert acts[4] == {"action": "toggle_mode"}
        assert acts[5] == {"action": "toggle_file", "idx": 1}
        assert acts[6] == {"action": "focus_file", "idx": 2}
        assert acts[7] == {"action": "focus_file", "idx": 0}
        assert acts[8] is None  # مفتاح غير معروف ⇒ لا فعل

    def test_focus_clamped_at_bounds(self) -> None:
        out = run_node(
            "const DP=require('./static/js/diff_panel.js');"
            "console.log(JSON.stringify(["
            "DP.handleKey({files:[1],activeFile:0},'j'),"
            "DP.handleKey({files:[1],activeFile:0},'k')]));"
        )
        acts = json.loads(out)
        assert acts[0]["idx"] == 0 and acts[1]["idx"] == 0


class TestAutoModeRegression:
    def test_auto_whitelist_emits_no_ui_frame(self) -> None:
        # الوضع التلقائي: قرار فوري بلا إطار واجهة ⇒ اللوحة لا تُفتح.
        gate = ApprovalGate(mode="auto", auto_whitelist={"write", "delete"})
        frames: list[dict] = []
        verdict = gate.request(make_request(), on_request=frames.append)
        assert verdict.approved is True and verdict.reason == "auto_whitelist"
        assert frames == []  # صفر أُطر ⇒ ما فيش chain_approval_request أصلًا


class TestSchemaAndWiring:
    def test_payload_schema_pinned_in_module_docs(self) -> None:
        text = MODULE.read_text(encoding="utf-8")
        # التوثيق المثبّت يذكر الإطارين وكل حقول العقد
        for token in ("chain_approval_request", "chain_approval_response",
                      "request_id", "payload_hash", "approved",
                      "kind", "target", "payload", "summary"):
            assert token in text, f"schema doc ناقص: {token}"

    def test_request_frame_fields_match_gate_to_dict(self) -> None:
        req = make_request()
        d = req.to_dict()
        assert set(d.keys()) == {"request_id", "source", "run_id",
                                 "payload_hash", "actions"}
        assert set(d["actions"][0].keys()) == {"kind", "target",
                                               "payload", "summary"}

    def test_app_js_wires_request_and_verdict(self) -> None:
        text = _app_bundle()
        assert 'case "chain_approval_request"' in text
        assert 'case "chain_approval_verdict"' in text
        assert "DiffPanel.decisionFrame(" in text
        assert "chain_approval_response" not in text.replace(
            "DiffPanel.decisionFrame", ""), (
            "إطار الرد يُبنى في الوحدة فقط — لا بناء يدوي في app.js")

    def test_index_html_panel_markup_and_load_order(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="diff-panel-overlay"' in html
        assert 'id="diff-approve-all"' in html
        assert 'id="diff-reject-all"' in html
        assert 'id="diff-confirm"' in html
        pos = [
            html.find("/static/js/code_highlight.js"),
            html.find("/static/js/diff_panel.js"),
            html.find("/static/app.js"),
        ]
        assert -1 not in pos and pos == sorted(pos)

    def test_css_row_height_matches_module_constant(self) -> None:
        # virtualization يعتمد تطابق ROW_HEIGHT مع CSS حرفيًا.
        css = STYLE_CSS.read_text(encoding="utf-8")
        assert ".diff-row" in css and "height: 20px" in css
        out = run_node(
            "console.log(require('./static/js/diff_panel.js').ROW_HEIGHT);")
        assert out.strip() == "20"
