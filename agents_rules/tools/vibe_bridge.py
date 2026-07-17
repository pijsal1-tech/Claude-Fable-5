"""
🌉 vibe_bridge.py — كوبري التواصل الآلي بين Antigravity والفريق
==============================================================
الموقع الصح: .agents/tools/vibe_bridge.py  (أداة عامة لكل المشاريع)

الاستخدام:
    python .agents/tools/vibe_bridge.py "سؤالك هنا"
    python .agents/tools/vibe_bridge.py --file brief.md
    python .agents/tools/vibe_bridge.py --read-last
    python .agents/tools/vibe_bridge.py --tier T3 "خطة معمارية"

نظام الـ 3 بوابات (T1/T2/T3):
    🟢 T1 — بسيط   → سؤال مباشر، مفيش Brief
    🟡 T2 — متوسط  → Mini-Brief (اختياري)
    🔴 T3 — خطير   → Full Brief إلزامي — ينتظر ADR
"""

import sys
import subprocess
import argparse
import json
import logging
import datetime
import time
from pathlib import Path

# ─── إصلاح الـ encoding في Windows ───────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("VibeBridge")

# ─── المسارات الثابتة ──────────────────────────────────────────────────────
TOOLS_DIR   = Path(__file__).parent                         # .agents/tools/
AGENTS_DIR  = TOOLS_DIR.parent                              # .agents/
WORKSPACE   = AGENTS_DIR.parent                             # المجلد الجذر للـ workspace

# مجلد شغل فريق (بيختلف حسب الـ workspace)
TEAM_DIR = None
for candidate in WORKSPACE.iterdir():
    if candidate.is_dir() and "شغل فريق" in candidate.name:
        TEAM_DIR = candidate
        break

if TEAM_DIR is None:
    log.error("❌ مش لاقي مجلد 'شغل فريق'! تأكد من هيكل الـ workspace.")
    sys.exit(1)

CHAT_FILE       = TEAM_DIR / "chat_send.txt"
RUNNER          = TEAM_DIR / "team_runner.py"
RESPONSES_FILE  = TEAM_DIR / "00-All-Responses.md"
LOG_FILE        = TOOLS_DIR / "vibe_bridge.log"

# ai_state.json — بيتحدد من أول Root/ موجود في الـ workspace
def find_state_file() -> Path | None:
    for p in WORKSPACE.rglob("ai_state.json"):
        return p
    return None

# ─── الدوال ────────────────────────────────────────────────────────────────

def write_brief(text: str) -> None:
    """1️⃣ اكتب الـ Brief في chat_send.txt"""
    try:
        CHAT_FILE.write_text(text.strip(), encoding="utf-8")
        log.info(f"✅ Brief اتكتب ({len(text)} حرف) → {CHAT_FILE.name}")
    except Exception as e:
        log.error(f"❌ فشل كتابة Brief: {e}")
        raise

def update_state(brief: str, phase: str = "before_query") -> None:
    """🔄 حدّث ai_state.json (مرتين: قبل وبعد الاستشارة)"""
    state_path = find_state_file()
    if state_path is None:
        log.warning("⚠️ مش لاقي ai_state.json — هتخطي تحديث الحالة")
        return
    state = {}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        state = {}

    state["vibe_bridge"] = {
        "phase":        phase,
        "last_brief":   brief[:300],
        "timestamp":    datetime.datetime.now().isoformat(),
    }
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    log.info(f"🔄 ai_state.json تحديث [{phase}] → {state_path}")

def run_team(retries: int = 2, timeout: int = 500) -> bool:
    """2️⃣ شغّل team_runner.py مع retry تلقائي"""
    if not RUNNER.exists():
        log.error(f"❌ مش لاقي team_runner.py في: {TEAM_DIR}")
        return False

    for attempt in range(1, retries + 1):
        log.info(f"🚀 تشغيل الفريق (محاولة {attempt}/{retries})...")
        try:
            result = subprocess.run(
                [sys.executable, str(RUNNER)],
                cwd=str(TEAM_DIR),
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            if result.returncode == 0:
                log.info("✅ الفريق خلّص بنجاح!")
                return True
            else:
                log.warning(f"⚠️ الفريق خلّص بـ returncode={result.returncode}")
                if attempt < retries:
                    log.info(f"⏳ انتظر 5 ثواني قبل المحاولة التالية...")
                    time.sleep(5)
        except subprocess.TimeoutExpired:
            log.error(f"⏰ Timeout بعد {timeout} ثانية! (محاولة {attempt})")
            if attempt < retries:
                time.sleep(5)
        except Exception as e:
            log.error(f"❌ خطأ غير متوقع: {e}")
            break

    log.error("❌ فشل تشغيل الفريق بعد كل المحاولات!")
    return False

def read_responses(max_chars: int = 4000) -> str:
    """3️⃣ اقرأ ردود الفريق من 00-All-Responses.md"""
    if not RESPONSES_FILE.exists():
        return "❌ مفيش ملف ردود بعد — شغّل الفريق الأول!"
    try:
        content = RESPONSES_FILE.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n... [مقتطع — الملف الكامل: {RESPONSES_FILE}]"
        return content
    except Exception as e:
        return f"❌ فشل قراءة الردود: {e}"

def log_to_file(brief: str, response_preview: str) -> None:
    """📝 سجّل العملية في vibe_bridge.log"""
    try:
        entry = (
            f"\n{'='*60}\n"
            f"[{datetime.datetime.now().isoformat()}]\n"
            f"BRIEF: {brief[:200]}\n"
            f"RESPONSE PREVIEW: {response_preview[:400]}\n"
        )
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        log.info(f"📝 عملية مسجلة في: {LOG_FILE.name}")
    except Exception as e:
        log.warning(f"⚠️ فشل التسجيل في log: {e}")

# ─── المدخل الرئيسي ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🌉 Vibe Bridge — Antigravity ↔ Vibe Coder Team",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("question", nargs="?",
                        help="البريف/السؤال مباشرة")
    parser.add_argument("--file",  metavar="F",
                        help="اقرأ الـ Brief من ملف")
    parser.add_argument("--read-last", action="store_true",
                        help="اقرأ آخر ردود بس، بدون تشغيل الفريق")
    parser.add_argument("--tier", choices=["T1", "T2", "T3"], default="T2",
                        help="مستوى المهمة: T1=بسيط T2=متوسط T3=خطير (default: T2)")
    parser.add_argument("--max",  type=int, default=4000,
                        help="أقصى عدد حروف للردود (default: 4000)")
    parser.add_argument("--retries", type=int, default=2,
                        help="عدد محاولات إعادة التشغيل (default: 2)")
    args = parser.parse_args()

    print(f"\n{'🌉'*20}")
    print(f"  Vibe Bridge — Tier: {args.tier}")
    print(f"{'🌉'*20}\n")

    # وضع: بس اقرأ آخر الردود
    if args.read_last:
        print(read_responses(args.max))
        return

    # استخراج الـ Brief
    if args.file:
        try:
            brief = Path(args.file).read_text(encoding="utf-8")
            log.info(f"📄 Brief من ملف: {args.file}")
        except Exception as e:
            log.error(f"❌ فشل قراءة الملف: {e}")
            return
    elif args.question:
        brief = args.question
    else:
        if CHAT_FILE.exists() and CHAT_FILE.read_text(encoding="utf-8").strip():
            brief = CHAT_FILE.read_text(encoding="utf-8")
            log.info(f"📄 هستخدم المحتوى الموجود في {CHAT_FILE.name}")
        else:
            log.error("❌ مفيش سؤال! استخدم:\n  python vibe_bridge.py 'سؤالك'\n  python vibe_bridge.py --file brief.md")
            return

    # T1: شغّل بدون انتظار موافقة
    # T2: شغّل مع brief
    # T3: شغّل مع full brief وانتظر ADR
    if args.tier == "T3":
        log.warning("🔴 T3 — قرار معماري خطير! الفريق هيشتغل ومحتاج تراجع الـ ADR قبل ما Antigravity ينفذ أي كود!")

    # ─── التسلسل الرئيسي ─────────────────────────────────────────────────
    # خطوة 1: حدّث الـ state قبل الإرسال
    update_state(brief, phase="before_query")

    # خطوة 2: اكتب الـ Brief
    write_brief(brief)

    # خطوة 3: شغّل الفريق
    success = run_team(retries=args.retries)

    # خطوة 4: حدّث الـ state بعد الاستجابة
    update_state(brief, phase="after_response" if success else "after_failure")

    # خطوة 5: اقرأ وعرض الردود
    print(f"\n{'='*60}\n📬 ردود الفريق:\n{'='*60}")
    response = read_responses(args.max)
    print(response)

    # خطوة 6: سجّل في الـ log
    log_to_file(brief, response)

    if args.tier == "T3":
        print(f"\n{'🔴'*20}")
        print("  T3 REMINDER: لازم تراجع الـ ADR قبل ما Antigravity ينفذ أي كود!")
        print(f"{'🔴'*20}\n")

if __name__ == "__main__":
    main()
