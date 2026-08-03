# 🎨 Terminal Output — CLI إلزامي في كل سكريبت

> **⛔ مفيش print() عادي بدون ألوان في أي سكريبت!**

## Setup الإلزامي (أول الملف):

```python
import sys, time, random
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class _F: CYAN=GREEN=RED=YELLOW=MAGENTA=WHITE=''
    class _S: BRIGHT=RESET_ALL=''
    Fore, Style = _F(), _S()

C=Fore.CYAN; G=Fore.GREEN; R=Fore.RED; Y=Fore.YELLOW
M=Fore.MAGENTA; W=Fore.WHITE; B=Style.BRIGHT; RST=Style.RESET_ALL
```

## الدوال الإلزامية:

```python
def banner(provider, mode, max_acc, delay, timeout, existing):
    print(f"\n{C}{B}{'═'*60}")
    print(f"  🚀 {provider} Account Creator")
    print(f"{'═'*60}{RST}")
    print(f"  {W}🔄 Mode    : {B}{Y}{mode}{RST}")
    if mode == 'Loop':
        limit = str(max_acc) if max_acc > 0 else "unlimited"
        print(f"  {W}🎯 Target  : {B}{Y}{limit}{RST}")
        print(f"  {W}⏱️  Delay   : {B}{delay}s{RST}")
    print(f"  {W}📁 Existing: {B}{G}{existing}{RST} accounts")
    print(f"{C}{B}{'═'*60}{RST}\n")

def account_header(num, provider, stats=""):
    """هيدر لكل حساب — بيعرض الرقم + provider + إحصائيات"""
    extra = f"  ({stats})" if stats else ""
    print(f"\n{Y}{B}{'─'*60}")
    print(f"  📧 Account #{num} — {provider}{extra}")
    print(f"{'─'*60}{RST}")

def step(num, total, msg):    print(f"  {C}[{num}/{total}]{RST} {msg}")
def ok(msg):                   print(f"  {G}{B}✅ {msg}{RST}")
def fail(msg):                 print(f"  {R}{B}❌ {msg}{RST}")
def warn(msg):                 print(f"  {Y}⚠️  {msg}{RST}")
def info(msg):                 print(f"  {M}ℹ️  {msg}{RST}")
def waiting(msg):              print(f"  {W}⏳ {msg}{RST}")

def final_stats(success, failed, total_saved, attempts):
    rate = (success / (success + failed) * 100) if (success + failed) > 0 else 0
    color = G if rate >= 70 else Y if rate >= 40 else R
    print(f"\n{C}{B}{'═'*60}")
    print(f"  🏁 Final Stats\n{'═'*60}{RST}")
    print(f"  {G}✅ Success : {B}{success}{RST}")
    print(f"  {R}❌ Failed  : {B}{failed}{RST}")
    print(f"  {color}📈 Rate    : {B}{rate:.0f}%{RST}")
    print(f"  {W}💾 Saved   : {B}{total_saved}{RST} total")
    print(f"{C}{B}{'═'*60}{RST}\n")
```

## Argparse القياسي:

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--max", type=int, default=MAX_ACCOUNTS)
parser.add_argument("--loop", action="store_true", default=LOOP_MODE)
parser.add_argument("--no-loop", dest="loop", action="store_false")
parser.add_argument("--delay", type=int, default=DELAY_BETWEEN)
parser.add_argument("--timeout", type=int, default=OTP_TIMEOUT)
parser.add_argument("--provider", default="mailtm",
    choices=["emailnator", "mailtm", "tempmail", "tempnet", "besttemp", "mix"])
parser.add_argument("--headless", action="store_true")
parser.add_argument("--list", action="store_true", help="عرض الحسابات")
parser.add_argument("--count", action="store_true", help="عدد الحسابات")
args = parser.parse_args()
```

## قواعد إلزامية:

- مسافات في الإحصائيات: `( ✅ 1 ❌ 0 )` مش `✅1 ❌0`
- Ctrl+C ملون: `print(f"\n\n  {R}{B}⛔ اتوقف بـ Ctrl+C{RST}")`
- الخطوات تبدأ من 1 مش 0: `step(1, 5, "...")` مش `step(0, 5, "...")`
