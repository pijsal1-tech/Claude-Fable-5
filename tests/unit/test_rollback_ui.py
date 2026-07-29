# -*- coding: utf-8 -*-
"""T-066 (R-902/R-906) — Rollback UI + شريحة الرصد: E2E + عقود + خنق.

يتحقق من:
  1. **Rollback E2E عبر أطر الواجهة الفعلية**: apply حقيقي عبر البوابة ثم
     الإطار الذي تبنيه وحدة RunHistory (node) يُغذّى لمسار WS الحقيقي
     (server._handle_ws_message) — rollback_run يستعيد البايتات في ≤2
     نقرة، وrollback_file يترك الأشقاء.
  2. **تقرير التعارض مقروء**: تعديل خارجي ⇒ rollback_result refused ⇒
     conflictReportHTML يعرض السبب نصًا (وليس JSON خامًا) و
     applyRollbackResult يعلّم الملف/المدخل.
  3. **History/Preview endpoints**: run_summaries (الأحدث أولًا، seal
     مضموم، أعلام الإنشاء) وsnapshot_text (نص ما-قبل-الكتابة / absent).
  4. **شريحة الرصد (R-906)**: noteFrame يلتقط routing من chain_started
     الموجود، breakerSummary/renderChip/renderPanel من نفس مخططات
     RoutingDecision/CapacityReport، والخنق يُبقي عدد الرسومات مقيّدًا
     تحت دفقة أحداث (بند قبول R-906).
  5. **Regression (استهلاك فقط)**: لا أطر WS جديدة — أوامر التنفيذ هي
     rollback_run/rollback_file (T-054) حرفيًا وتُبنى في الوحدة فقط؛
     ترتيب تحميل السكربتات وmarkup اللوحة مثبتان.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RH_MODULE = ROOT / "static" / "js" / "run_history.js"
SC_MODULE = ROOT / "static" / "js" / "status_chip.js"
APP_JS = ROOT / "static" / "app.js"
INDEX_HTML = ROOT / "static" / "index.html"

sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from actions.file_manager import FileManager  # noqa: E402
from actions.response_parser import ResponseParser  # noqa: E402
from chain.action_applier import ActionApplier  # noqa: E402
from chain.bridge import ChainBridge  # noqa: E402
from core.approval import ApprovalGate  # noqa: E402
from core.checkpoint import CheckpointManager  # noqa: E402
from core.session_context import SessionContext  # noqa: E402
from tests.fakes.fake_provider import FakeProvider  # noqa: E402

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node غير متوفر")

JOIN_TIMEOUT = 10.0

AI_RESPONSE_2_FILES = (
    "تم:\n"
    "```FILE: one.txt\nNEW ONE\n```\n"
    "```FILE: made/new.txt\nBRAND NEW\n```\n"
)


def run_node(script: str) -> str:
    proc = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, timeout=60,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _make_bridge(tmp_path: pathlib.Path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    (project / "one.txt").write_text("ORIG ONE", encoding="utf-8")
    fm = FileManager(str(project))
    applier = ActionApplier(parser=ResponseParser(), file_manager=fm,
                            auto_backup=False)
    gate = ApprovalGate(mode="auto",
                        auto_whitelist={"write", "edit", "command"})
    bridge = ChainBridge(
        provider=FakeProvider(responses=[AI_RESPONSE_2_FILES]),
        project_root=str(project),
        runs_dir=tmp_path / "runs",
        action_applier=applier,
        approval_gate=gate,
    )
    return bridge, project


def _run_and_join(bridge: ChainBridge) -> str:
    frames: list[dict] = []
    run_id = bridge.start_chain(frames.append, "اكتب الملفات",
                                force_strategy="direct")
    assert run_id
    thread = bridge._active_thread
    assert thread is not None
    thread.join(timeout=JOIN_TIMEOUT)
    assert not thread.is_alive()
    return run_id


def _history_entries_json(bridge, monkeypatch) -> list[dict]:
    """رد /api/rollback/history الفعلي → RunHistory.buildEntries (node)."""
    monkeypatch.setattr(server, "chain_bridge", bridge)
    body = server.app.test_client().get("/api/rollback/history").get_json()
    assert body["ok"] is True
    out = run_node(
        "const RH=require('./static/js/run_history.js');"
        f"const runs={json.dumps(body['runs'])};"
        "console.log(JSON.stringify(RH.buildEntries(runs, 1e10)));"
    )
    return json.loads(out)


def _ui_frame(entry: dict, file_idx=None) -> dict:
    """الإطار الذي تبنيه الوحدة الفعلية — rollbackFrame في node."""
    fi = "null" if file_idx is None else str(file_idx)
    out = run_node(
        "const RH=require('./static/js/run_history.js');"
        f"const e={json.dumps(entry)};"
        f"console.log(JSON.stringify(RH.rollbackFrame(e,{fi})));"
    )
    return json.loads(out)


def _dispatch(bridge, frame: dict) -> list[dict]:
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)
    sctx.chain_bridge = bridge
    server._handle_ws_message(None, sctx, frame)
    return [f for f in sent if f.get("type") == "rollback_result"]


# ═══════════════ 1. Rollback E2E عبر أطر الواجهة ═══════════════

class TestRollbackE2E:
    def test_rollback_run_via_ui_frame_restores_bytes(self, tmp_path,
                                                      monkeypatch):
        bridge, project = _make_bridge(tmp_path)
        run_id = _run_and_join(bridge)
        assert (project / "one.txt").read_text(
            encoding="utf-8").strip() == "NEW ONE"

        entries = _history_entries_json(bridge, monkeypatch)
        entry = next(e for e in entries if e["run_id"] == run_id)
        frame = _ui_frame(entry, None)
        # الأمر الموجود منذ T-054 حرفيًا — لا نوع إطار جديد
        assert frame == {"type": "rollback_run", "run_id": run_id}

        results = _dispatch(bridge, frame)
        assert len(results) == 1 and results[0]["status"] == "success"
        assert (project / "one.txt").read_text(encoding="utf-8") == "ORIG ONE"
        assert not (project / "made" / "new.txt").exists()

    def test_rollback_file_via_ui_frame_leaves_siblings(self, tmp_path,
                                                        monkeypatch):
        bridge, project = _make_bridge(tmp_path)
        run_id = _run_and_join(bridge)
        entries = _history_entries_json(bridge, monkeypatch)
        entry = next(e for e in entries if e["run_id"] == run_id)
        idx = next(i for i, f in enumerate(entry["files"])
                   if f["path"].endswith("one.txt"))
        frame = _ui_frame(entry, idx)
        assert frame["type"] == "rollback_file"
        assert frame["path"] == entry["files"][idx]["path"]

        results = _dispatch(bridge, frame)
        assert results[0]["status"] == "success"
        assert (project / "one.txt").read_text(encoding="utf-8") == "ORIG ONE"
        assert (project / "made" / "new.txt").exists()  # الشقيق لم يُمسّ

    def test_created_file_flagged_and_preview_absent(self, tmp_path,
                                                     monkeypatch):
        bridge, project = _make_bridge(tmp_path)
        run_id = _run_and_join(bridge)
        entries = _history_entries_json(bridge, monkeypatch)
        entry = next(e for e in entries if e["run_id"] == run_id)
        created = next(f for f in entry["files"]
                       if f["path"].endswith("new.txt"))
        assert created["created"] is True  # pre_sha256=None ⇒ أنشأه الـ run

        monkeypatch.setattr(server, "chain_bridge", bridge)
        body = server.app.test_client().get(
            "/api/rollback/preview",
            query_string={"run_id": run_id, "path": created["path"]},
        ).get_json()
        assert body["ok"] is True and body["absent"] is True

        pre = next(f for f in entry["files"] if f["path"].endswith("one.txt"))
        body2 = server.app.test_client().get(
            "/api/rollback/preview",
            query_string={"run_id": run_id, "path": pre["path"]},
        ).get_json()
        assert body2["absent"] is False and body2["snapshot"] == "ORIG ONE"


# ═══════════════ 2. تقرير التعارض مقروء ═══════════════

class TestConflictRender:
    def test_external_edit_refused_and_report_human_readable(self, tmp_path,
                                                             monkeypatch):
        bridge, project = _make_bridge(tmp_path)
        run_id = _run_and_join(bridge)
        (project / "one.txt").write_text("HUMAN EDIT", encoding="utf-8")

        entries = _history_entries_json(bridge, monkeypatch)
        entry = next(e for e in entries if e["run_id"] == run_id)
        idx = next(i for i, f in enumerate(entry["files"])
                   if f["path"].endswith("one.txt"))
        results = _dispatch(bridge, _ui_frame(entry, idx))
        frame = results[0]
        assert frame["status"] == "refused"
        assert frame["conflicts"][0]["reason"]  # سبب نصي موجود

        out = run_node(
            "const RH=require('./static/js/run_history.js');"
            f"const entries={json.dumps(entries)};"
            f"const frame={json.dumps(frame)};"
            "const e=RH.applyRollbackResult(entries,frame);"
            "const html=RH.conflictReportHTML(frame);"
            "console.log(JSON.stringify({state:e.state,"
            "fstate:e.files.map(f=>f.state),html:html}));"
        )
        res = json.loads(out)
        assert res["state"] == "refused"
        assert "conflict" in res["fstate"]
        # مقروء: السبب معروض نصًا، وليس JSON خامًا للتقرير
        assert "externally" in res["html"] or "تغيّرت" in res["html"]
        assert "expected_sha256" not in res["html"]
        assert "rh-conflict-report" in res["html"]

    def test_success_marks_entry_rolled_back(self, tmp_path, monkeypatch):
        bridge, project = _make_bridge(tmp_path)
        run_id = _run_and_join(bridge)
        entries = _history_entries_json(bridge, monkeypatch)
        entry = next(e for e in entries if e["run_id"] == run_id)
        frame = dict(_dispatch(bridge, _ui_frame(entry, None))[0])
        out = run_node(
            "const RH=require('./static/js/run_history.js');"
            f"const entries={json.dumps(entries)};"
            f"const frame={json.dumps(frame)};"
            "const e=RH.applyRollbackResult(entries,frame);"
            "console.log(JSON.stringify({state:e.state,"
            "html:RH.renderPanelHTML(entries,'')}));"
        )
        res = json.loads(out)
        assert res["state"] == "rolled_back"
        assert "مُستعاد" in res["html"] and "disabled" in res["html"]


# ═══════════════ 3. History summaries — الوحدة والرندر ═══════════════

class TestHistorySummaries:
    def test_run_summaries_newest_first_with_seals(self, tmp_path):
        mgr = CheckpointManager(tmp_path / "ck")
        f1 = tmp_path / "a.txt"
        f1.write_text("v1", encoding="utf-8")
        mgr.snapshot("run-old", [f1])
        f1.write_text("v2", encoding="utf-8")
        mgr.seal("run-old", [f1])
        mgr.snapshot("run-new", [f1])
        summaries = mgr.run_summaries()
        assert [s["run_id"] for s in summaries] == ["run-new", "run-old"]
        old = summaries[1]["files"][0]
        assert old["pre_sha256"] and old["post_sha256"]  # seal مضموم
        assert summaries[0]["files"][0]["post_sha256"] is None
        assert mgr.snapshot_text("run-old", f1) == "v1"
        assert mgr.snapshot_text("run-old", tmp_path / "ghost.txt") is None

    def test_render_panel_html_golden(self):
        entries_js = json.dumps([{
            "run_id": "run-9", "ts": 0, "age": "الآن", "state": "available",
            "files": [
                {"path": "/p/app.py", "size": 10, "created": False,
                 "state": "available"},
                {"path": "/p/new.js", "size": 5, "created": True,
                 "state": "available"},
            ],
        }])
        out = run_node(
            "const RH=require('./static/js/run_history.js');"
            f"console.log(RH.renderPanelHTML({entries_js},'/p'));"
        )
        assert "#icon-python" in out and "#icon-js" in out  # أيقونات T-063
        assert "أنشأه الـ run" in out
        assert 'data-run="run-9"' in out
        assert "rh-rollback-run" in out and "rh-rollback-file" in out
        assert ">app.py<" in out  # المسار مُقصّر عن الجذر
        out_empty = run_node(
            "const RH=require('./static/js/run_history.js');"
            "console.log(RH.renderPanelHTML([],''));"
        )
        assert "rh-empty" in out_empty  # المُقلَّم/الفارغ = رسالة، لا أزرار

    def test_confirm_actions_reuse_t065_panel_schema(self):
        entry = json.dumps({
            "run_id": "r1", "files": [
                {"path": "/p/a.py", "created": False, "state": "available"},
                {"path": "/p/b.py", "created": True, "state": "available"},
            ],
        })
        out = run_node(
            "const RH=require('./static/js/run_history.js');"
            f"const e={entry};"
            "const built=RH.confirmActions(e,null,"
            "{'/p/a.py':{absent:false,snapshot:'OLD'},"
            "'/p/b.py':{absent:true,snapshot:''}},"
            "{'/p/a.py':'CUR','/p/b.py':'X'});"
            "const DP=require('./static/js/diff_panel.js');"
            "const st=DP.openState({request_id:'',payload_hash:'',run_id:'r1',"
            "actions:built.actions},built.oldContents);"
            "console.log(JSON.stringify({kinds:built.actions.map(a=>a.kind),"
            "payloads:built.actions.map(a=>a.payload),"
            "rows:st.files.map(f=>f.rows?f.rows.length:null)}));"
        )
        res = json.loads(out)
        # write بمحتوى الـ snapshot للاستعادة + delete للمُنشأ — لوحة
        # T-065 تفتح الحالة مباشرة (rows محسوبة = تأكيد بصري حقيقي).
        assert res["kinds"] == ["write", "delete"]
        assert res["payloads"][0] == "OLD"
        assert all(r is not None and r > 0 for r in res["rows"])


# ═══════════════ 4. شريحة الرصد R-906 ═══════════════

CAPACITY = {
    "total_available": 12, "healthy_count": 2, "estimated": True,
    "providers": [
        {"name": "alpha", "healthy": True, "breaker_state": "closed",
         "remaining_calls": 8, "effective_calls": 8, "estimated": False},
        {"name": "beta", "healthy": False, "breaker_state": "open",
         "remaining_calls": 0, "effective_calls": 0, "estimated": False},
        {"name": "gamma", "healthy": True, "breaker_state": "half_open",
         "remaining_calls": 4, "effective_calls": 4, "estimated": True},
    ],
}

ROUTING = {"strategy": "auto_chain", "provider_name": "alpha",
           "chain_strategy": "pipeline", "max_steps": 5,
           "downgraded": True, "downgrade_reason": "نقص حسابات",
           "complexity_score": 7.3}


class TestStatusChip:
    def test_note_frame_captures_routing_from_existing_frame(self):
        out = run_node(
            "const SC=require('./static/js/status_chip.js');"
            "const st=SC.createState();"
            f"const c1=SC.noteFrame(st,{{type:'chain_started',text:'x',routing:{json.dumps(ROUTING)}}});"
            "const c2=SC.noteFrame(st,{type:'chunk',text:'y'});"
            "console.log(JSON.stringify({c1:c1,c2:c2,"
            "strategy:st.routing.strategy}));"
        )
        res = json.loads(out)
        assert res == {"c1": True, "c2": False, "strategy": "auto_chain"}

    def test_render_from_real_schemas(self):
        out = run_node(
            "const SC=require('./static/js/status_chip.js');"
            "const st=SC.createState();"
            f"SC.noteFrame(st,{{type:'chain_started',routing:{json.dumps(ROUTING)}}});"
            f"SC.updateCapacity(st,{json.dumps(CAPACITY)});"
            "console.log(JSON.stringify({chip:SC.renderChipHTML(st),"
            "panel:SC.renderPanelHTML(st),"
            "b:SC.breakerSummary(st.capacity)}));"
        )
        res = json.loads(out)
        assert res["b"] == {"open": 1, "half": 1}
        chip = res["chip"]
        assert "auto_chain" in chip and "2/3" in chip
        assert "🔴 1" in chip and "≈" in chip and "⬇" in chip
        panel = res["panel"]
        assert "pipeline" in panel and "7.3" in panel
        assert "نقص حسابات" in panel  # سبب التنزيل من السجل نفسه
        assert "قاطع مفتوح" in panel and "تقديري" in panel
        assert "alpha" in panel and "gamma" in panel

    def test_throttling_bounds_renders_under_burst(self):
        # 100 إطار في 1000ms — الرسومات المسموحة ≤ 3 (كل 500ms) + pending
        out = run_node(
            "const SC=require('./static/js/status_chip.js');"
            "const st=SC.createState();let renders=0;"
            "for(let i=0;i<100;i++){"
            "  SC.noteFrame(st,{type:'chain_started',routing:{strategy:'direct'}});"
            "  if(SC.shouldRender(st, 1+i*10)) renders++;"
            "}"
            "console.log(JSON.stringify({renders:renders,"
            "pending:SC.hasPending(st),"
            "interval:SC.MIN_RENDER_INTERVAL_MS}));"
        )
        res = json.loads(out)
        assert res["renders"] <= 3
        assert res["pending"] is True  # الرسم اللاحق يلتقط آخر حالة
        assert res["interval"] == 500


# ═══════════════ 5. Regression: استهلاك فقط + التوصيل ═══════════════

class TestConsumeOnlyAndWiring:
    def test_no_new_ws_command_types(self):
        """أوامر التنفيذ هي rollback_run/rollback_file (T-054) حرفيًا —
        الوحدة لا تخترع نوع إطار جديد، وapp.js لا يبنيها يدويًا."""
        rh = RH_MODULE.read_text(encoding="utf-8")
        assert '"rollback_run"' in rh and '"rollback_file"' in rh
        app = APP_JS.read_text(encoding="utf-8")
        assert "RunHistory.rollbackFrame(" in app
        # لا بناء يدوي لإطار rollback في app.js خارج الوحدة
        stripped = app.replace("RunHistory.rollbackFrame", "")
        assert 'type: "rollback_run"' not in stripped
        assert 'type: "rollback_file"' not in stripped
        # الشريحة قراءة فقط: لا ws.send في وحدتها
        assert "ws.send" not in SC_MODULE.read_text(encoding="utf-8")

    def test_server_rollback_handler_unchanged_frames(self):
        src = (ROOT / "server.py").read_text(encoding="utf-8")
        # TSK-611: النوعان يوجَّهان لنفس المقبض عبر جدول dispatch
        # (ADR-001) — نفس ضمان "معالجة موحّدة للنوعين".
        assert '"rollback_run": _ws_rollback,' in src
        assert '"rollback_file": _ws_rollback,' in src
        # endpoints الجديدة قراءة فقط (GET بلا methods=POST)
        for ep in ('"/api/rollback/history"', '"/api/rollback/preview"'):
            line = next(ln for ln in src.splitlines() if ep in ln)
            assert "methods" not in line

    def test_index_wiring_and_load_order(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        for needle in ('id="run-history-panel"', 'id="run-history-list"',
                       'id="run-history-report"', 'id="run-history-btn"',
                       'id="status-chip-label"', 'id="status-chip-panel"'):
            assert needle in html, needle
        pos = [html.find("/static/js/file_icons.js"),
               html.find("/static/js/run_history.js"),
               html.find("/static/js/status_chip.js"),
               html.find("/static/app.js")]
        assert -1 not in pos and pos == sorted(pos)

    def test_app_js_glue_wired(self):
        app = APP_JS.read_text(encoding="utf-8")
        assert 'case "rollback_result"' in app
        assert "RunHistory.buildEntries(" in app
        assert "RunHistory.conflictReportHTML(" in app
        assert "StatusChip.noteFrame(" in app
        assert "StatusChip.shouldRender(" in app
        # تأكيد الاستعادة يعيد استخدام لوحة T-065 ويعترض قرارها
        assert "consumeRollbackDecision(overrideAll)" in app
        assert "DiffPanel.openState(" in app
