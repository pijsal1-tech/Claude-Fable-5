#!/usr/bin/env python3
"""TSK-738b (القرار 11 / D-21) — عدة قياس رجفة الأداء CEV-F-006.

الغرض: تشغيل **نفس قياسات الأداء** التي تُجرى في بيئة الاختبار
(Sandbox 2 vCPU) على جهاز حقيقي، لحسم سؤال CEV-F-006: هل الرجفة
الملحوظة بيئية (مزاحمة CPU في الـSandbox) أم انحدار حقيقي في الكود؟

ما يقيسه (بلا أي خادم شبكي ولا اتصال خارجي):
  1. زمن استيراد server.py — البديل الآلي لـ«زمن فتح المحرر»
     (يشمل استيراد Flask وكل سلاسل core/chain/routes).
  2. مساري البحث على مستودع اصطناعي 5000 ملف — **نفس مواصفة**
     fixture `big_project` في tests/integration/test_search_perf.py
     حرفيًا (50 مجلدًا × 100 ملف، الإبرة MAGIC_NEEDLE_QA_T13 في
     pkg25/mod_050.py)، وبنفس عقد القياس أفضل-من-3 (TSK-CEV-119)
     ونفس عتبة الحكم < 1.0s.
  3. لقطة عتاد وذاكرة: عدد الأنوية + الذاكرة الكلية/المتاحة +
     ذروة RSS للعملية.

الاستخدام:
    python scripts/perf_probe.py            # تقرير نصي
    python scripts/perf_probe.py --json     # + سطر JSON للمقارنة الآلية

ملاحظة FPS: واجهة المحرر HTML/JS تعمل في متصفح المستخدم — قياس FPS
يُجرى يدويًا عبر DevTools (انظر docs/perf_probe_runbook.md)؛ لا
تدّعي هذه العدة قياسه آليًا (نفس روح P-11: لا ادعاء قياس ما يتطلب
بيئة لا نملكها).

حدود واعية: سكربت تشخيصي قراءة-فقط خارج مسار الإنتاج — لا يستورد
منه أي كود إنتاجي، ولا يكتب إلا في مجلد مؤقت يُحذف تلقائيًا.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
THRESHOLD_S = 1.0  # عتبة QA-T13 الحرفية — لا تُعدَّل هنا أبدًا


def _best_of(n: int, fn):
    """أفضل قياس من n تشغيلات — نفس عقد TSK-CEV-119 في test_search_perf."""
    best_dt, best_out = float("inf"), None
    for _ in range(n):
        t0 = time.perf_counter()
        out = fn()
        dt = time.perf_counter() - t0
        if dt < best_dt:
            best_dt, best_out = dt, out
    return best_dt, best_out


def measure_server_import() -> float:
    """زمن استيراد server.py في عملية بايثون نظيفة (بديل «فتح المحرر»)."""
    code = (
        "import time; t0=time.perf_counter(); import server; "
        "print(time.perf_counter()-t0)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"فشل استيراد server.py:\n{proc.stderr[-2000:]}")
    return float(proc.stdout.strip().splitlines()[-1])


def build_big_project(root: Path) -> None:
    """مستودع اصطناعي 5000 ملف — مطابق حرفيًا لـfixture big_project."""
    n_dirs, per_dir = 50, 100
    for d in range(n_dirs):
        sub = root / f"pkg{d:02d}"
        sub.mkdir()
        for f in range(per_dir):
            body = (f"# module {d}-{f}\n"
                    f"def fn_{d}_{f}():\n"
                    f"    return 'payload_{d}_{f}'\n" + "x = 1\n" * 10)
            if d == 25 and f == 50:
                body += "MAGIC_NEEDLE_QA_T13 = True\n"
            (sub / f"mod_{f:03d}.py").write_text(body, encoding="utf-8")


def measure_search_paths(big_root: Path) -> dict:
    """نفس مساري TestPerf5k: api_search + tool_search_code (أفضل-من-3)."""
    sys.path.insert(0, str(REPO_ROOT))
    from actions.file_manager import MAX_FILE_SIZE, WEB_EXTENSIONS
    from chain.agent_tools import AgentTools
    from context.index import ProjectIndex
    from context.search import shared_search

    api_content_exts = {'.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css',
                        '.json', '.md', '.yml', '.yaml', '.txt'}

    index = ProjectIndex(str(big_root))
    svc = shared_search(index)
    svc.search_project("payload_25", walk_exts=WEB_EXTENSIONS,
                       max_size=MAX_FILE_SIZE, content_exts=api_content_exts)
    api_dt, api_res = _best_of(3, lambda: svc.search_project(
        "MAGIC_NEEDLE_QA_T13", walk_exts=WEB_EXTENSIONS,
        max_size=MAX_FILE_SIZE, content_exts=api_content_exts))
    api_found = any(r["type"] == "content" and "MAGIC_NEEDLE_QA_T13" in r["snippet"]
                    for r in api_res)

    tools = AgentTools(project_root=str(big_root))
    tools.tool_search_code("payload_10", ".")
    tool_dt, tool_out = _best_of(
        3, lambda: tools.tool_search_code("MAGIC_NEEDLE_QA_T13", "."))
    tool_found = "MAGIC_NEEDLE_QA_T13" in (tool_out or "")

    return {"api_search_s": api_dt, "api_found": api_found,
            "tool_search_s": tool_dt, "tool_found": tool_found}


def hardware_snapshot() -> dict:
    snap: dict = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    try:  # Linux فقط — على Windows تُترك None
        meminfo = Path("/proc/meminfo").read_text()
        for key, name in (("MemTotal", "mem_total_mb"),
                          ("MemAvailable", "mem_available_mb")):
            for line in meminfo.splitlines():
                if line.startswith(key + ":"):
                    snap[name] = int(line.split()[1]) // 1024
    except OSError:
        snap["mem_total_mb"] = snap["mem_available_mb"] = None
    try:
        import resource
        peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        snap["peak_rss_mb"] = peak_kb // 1024
    except ImportError:  # Windows بلا resource
        snap["peak_rss_mb"] = None
    return snap


def main() -> int:
    parser = argparse.ArgumentParser(description="عدة قياس CEV-F-006 (TSK-738b)")
    parser.add_argument("--json", action="store_true",
                        help="طباعة سطر JSON إضافي للمقارنة الآلية")
    args = parser.parse_args()

    print("== perf_probe (TSK-738b / D-21 القرار 11) ==")
    hw = hardware_snapshot()
    print(f"العتاد: {hw['cpu_count']} أنوية · "
          f"RAM {hw.get('mem_total_mb')}MB (متاح {hw.get('mem_available_mb')}MB) · "
          f"{hw['platform']} · Python {hw['python']}")

    print("\n[1/2] زمن استيراد server.py (عملية نظيفة)...")
    import_s = measure_server_import()
    print(f"      import server = {import_s:.2f}s")

    print("[2/2] بناء مستودع 5k ملف + قياس مساري البحث (أفضل-من-3)...")
    tmp = Path(tempfile.mkdtemp(prefix="perf_probe_5k_"))
    try:
        build_big_project(tmp)
        search = measure_search_paths(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    hw = hardware_snapshot()  # ذروة RSS بعد العمل الفعلي
    api_ok = search["api_search_s"] < THRESHOLD_S and search["api_found"]
    tool_ok = search["tool_search_s"] < THRESHOLD_S and search["tool_found"]
    print(f"      api_search       = {search['api_search_s']:.3f}s "
          f"({'✅' if api_ok else '❌'} عتبة {THRESHOLD_S}s، "
          f"الإبرة {'وُجدت' if search['api_found'] else 'غابت!'})")
    print(f"      tool_search_code = {search['tool_search_s']:.3f}s "
          f"({'✅' if tool_ok else '❌'} عتبة {THRESHOLD_S}s، "
          f"الإبرة {'وُجدت' if search['tool_found'] else 'غابت!'})")
    print(f"      ذروة RSS للعملية = {hw.get('peak_rss_mb')}MB")

    verdict_ok = api_ok and tool_ok
    print("\n== الحكم ==")
    if verdict_ok:
        print("كل القياسات دون العتبة — إن كانت الرجفة قد ظهرت في بيئة أخرى")
        print("فهي بيئية على الأرجح (قارن بجدول خط الأساس في docs/perf_probe_runbook.md).")
    else:
        print("قياس تجاوز العتبة على هذا الجهاز ⇒ مؤشر مشكلة أداء حقيقية —")
        print("أرسل هذا التقرير كاملًا ليُفتح لها تكليف إصلاح (TSK).")

    if args.json:
        print(json.dumps({"import_server_s": round(import_s, 3),
                          "api_search_s": round(search["api_search_s"], 4),
                          "tool_search_s": round(search["tool_search_s"], 4),
                          "threshold_s": THRESHOLD_S,
                          "verdict_ok": verdict_ok, **hw},
                         ensure_ascii=False))
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    sys.exit(main())
