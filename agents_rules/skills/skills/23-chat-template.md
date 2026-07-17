# 💬 Chat Script Template — SSE + CLI + Rotation

> **📌 Template جاهز لأي chat.py — زي ما `02-requests-level1.md` للـ register.py**

---

## 📐 Template chat.py:

```python
#!/usr/bin/env python3
"""💬 [Provider] Chat Client — SSE Streaming + Interactive CLI"""
from __future__ import annotations
import sys, json, time, argparse, logging
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from colorama import Fore, Style, init; init(autoreset=True)
except ImportError:
    class _F: CYAN=GREEN=RED=YELLOW=MAGENTA=WHITE=''
    class _S: BRIGHT=RESET_ALL=''
    Fore, Style = _F(), _S()

from curl_cffi import requests as cffi

C=Fore.CYAN; G=Fore.GREEN; R=Fore.RED; Y=Fore.YELLOW
M=Fore.MAGENTA; W=Fore.WHITE; B=Style.BRIGHT; RST=Style.RESET_ALL

ACCOUNTS_FILE = Path(__file__).resolve().parent / "accounts_PROVIDER.json"

# ─── Config ────────────────────────────────────
@dataclass
class Config:
    model: str = "default-model"          # الموديل الافتراضي
    timeout: int = 120                     # ثواني
    stream: bool = True                    # SSE streaming
    max_history: int = 20                  # عدد الرسائل المحفوظة
    persist_history: bool = True           # حفظ بين الـ runs

# ─── Account Rotation (TokenManager) ──────────
class TokenManager:
    """بيحمّل tokens من JSON + auto-switch لو 401/403"""
    def __init__(self, path: Path):
        self._path = path
        self._accounts = json.loads(path.read_text("utf-8")) if path.exists() else []
        self._idx = 0

    @property
    def current(self) -> dict | None:
        active = [a for a in self._accounts if a.get("status") == "active"]
        return active[self._idx % len(active)] if active else None

    def next(self):
        """بينقل للحساب التالي — بيترجع True لو في حساب"""
        self._idx += 1
        return self.current is not None

    def mark_failed(self):
        if acc := self.current:
            acc["status"] = "expired"
            self._save()

    def _save(self):
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._accounts, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self._path)

# ─── SSE Parser (3 formats) ──────────────────
def parse_sse_stream(response) -> str:
    """Universal SSE parser — يدعم 3 formats"""
    full_text = ""
    for line in response.iter_lines():
        line = line.strip()
        if not line or line == "data: [DONE]":
            continue

        # Format 1: OpenAI delta
        if line.startswith("data: "):
            data = line[6:]
            try:
                j = json.loads(data)
                # OpenAI: {"choices":[{"delta":{"content":"text"}}]}
                if "choices" in j:
                    chunk = j["choices"][0].get("delta", {}).get("content", "")
                # Shorthand: {"v": "text"}
                elif "v" in j:
                    chunk = j["v"]
                # Direct: {"text": "..."}
                elif "text" in j:
                    chunk = j["text"]
                else:
                    chunk = ""
                if chunk:
                    print(chunk, end="", flush=True)
                    full_text += chunk
            except json.JSONDecodeError:
                # Format 3: plain text
                print(data, end="", flush=True)
                full_text += data
    print()  # سطر جديد بعد البث
    return full_text

# ─── Chat API ────────────────────────────────
def send_message(session, token: str, message: str, cfg: Config,
                 history: list) -> str:
    """بيبعت رسالة ويرجع الرد"""
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "model": cfg.model,
        "messages": history + [{"role": "user", "content": message}],
        "stream": cfg.stream,
    }
    r = session.post("https://SITE.com/api/chat",
        json=body, headers=headers, stream=cfg.stream, timeout=cfg.timeout)

    if r.status_code in (401, 403):
        return None  # → TokenManager.next()
    r.raise_for_status()

    if cfg.stream:
        return parse_sse_stream(r)
    return r.json().get("content", r.text)

# ─── Persistent History ──────────────────────
HISTORY_FILE = Path(__file__).resolve().parent / "history.json"

def _load_history() -> list:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text("utf-8"))
    return []

def _save_history(history: list):
    tmp = HISTORY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(history[-50:], ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(HISTORY_FILE)

# ─── Interactive CLI ──────────────────────────
COMMANDS = {
    "/help":    "عرض الأوامر",
    "/clear":   "مسح المحادثة",
    "/model":   "تغيير الموديل",
    "/status":  "حالة الحساب",
    "/history": "عرض المحادثة",
    "/stats":   "إحصائيات",
    "/exit":    "خروج",
}

def interactive_loop(cfg: Config, tm: TokenManager):
    session = cffi.Session(impersonate="chrome124")
    history = _load_history() if cfg.persist_history else []
    stats = {"messages": 0, "tokens_est": 0, "start": time.time()}

    print(f"\n{C}{B}💬 [Provider] Chat — {cfg.model}{RST}")
    print(f"{W}اكتب /help للأوامر{RST}\n")

    while True:
        try:
            q = input(f"{G}{B}أنت: {RST}").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not q: continue

        # Commands
        if q == "/help":
            for cmd, desc in COMMANDS.items():
                print(f"  {C}{cmd:10}{W}{desc}{RST}")
            continue
        elif q == "/clear":
            history.clear(); print(f"  {G}✅ تم المسح{RST}"); continue
        elif q == "/model":
            cfg.model = input(f"  {W}الموديل الجديد: {RST}").strip(); continue
        elif q == "/status":
            acc = tm.current
            print(f"  {W}📧 {acc['email']}  📊 {acc.get('status','?')}{RST}"); continue
        elif q == "/history":
            for m in history[-10:]:
                role = "🧑" if m["role"] == "user" else "🤖"
                print(f"  {role} {m['content'][:80]}"); continue
        elif q == "/stats":
            elapsed = time.time() - stats["start"]
            print(f"  {W}📊 {stats['messages']} msgs | ~{stats['tokens_est']} tokens | {elapsed:.0f}s{RST}")
            continue
        elif q == "/exit": break

        # Send
        acc = tm.current
        if not acc:
            print(f"  {R}❌ مفيش حسابات متاحة!{RST}"); break

        print(f"{M}{B}🤖: {RST}", end="")
        reply = send_message(session, acc.get("token",""), q, cfg, history)

        if reply is None:  # 401/403 → switch
            print(f"\n  {Y}⚠️ Token expired — switching...{RST}")
            if not tm.next():
                print(f"  {R}❌ كل الحسابات expired!{RST}"); break
            reply = send_message(session, tm.current.get("token",""), q, cfg, history)

        if reply:
            history.append({"role": "user", "content": q})
            history.append({"role": "assistant", "content": reply})
            if len(history) > cfg.max_history * 2:
                history = history[-(cfg.max_history * 2):]
            if cfg.persist_history:
                _save_history(history)
            stats["messages"] += 1
            stats["tokens_est"] += len(reply) // 4

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="default-model")
    parser.add_argument("--no-stream", dest="stream", action="store_false", default=True)
    parser.add_argument("--no-history", dest="persist", action="store_false", default=True)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        accs = json.loads(ACCOUNTS_FILE.read_text("utf-8")) if ACCOUNTS_FILE.exists() else []
        for i, a in enumerate(accs, 1):
            print(f"  {i}. {a['email']} [{a.get('status','?')}]")
        return

    cfg = Config(model=args.model, stream=args.stream, persist_history=args.persist)
    tm = TokenManager(ACCOUNTS_FILE)
    interactive_loop(cfg, tm)

if __name__ == "__main__":
    main()
```

---

## 🔑 Patterns المشتركة بين كل Chat Scripts:

| Pattern | الوصف | مثال |
|---------|-------|------|
| SSE Parser | 3 formats: OpenAI/field_name/direct | `parse_sse_stream()` |
| TokenManager | rotation + auto-switch 401/403 | `tm.next()` |
| /commands | interactive CLI (help/clear/model/exit) | `COMMANDS dict` |
| Persistent History | `history.json` بين الـ runs | `_load/_save_history()` |
| Stats | messages + tokens + time | `stats dict` |
| Model Selection | `--model` CLI + `/model` command | `cfg.model` |

---

## ⚠️ خصّصها حسب الـ Provider:

| Provider | التغيير |
|----------|---------|
| DeepSeek | +PoW solver + `parent_message_id` |
| ERNIE | +event type tracking (thought/step/message) |
| Uncensored | +WebSocket بدل SSE + `end_of_stream` |
| Genspark | +`ask_proxy` endpoint + 3 SSE formats |
| Pollinations | +sk_ key creation + `history.json` |
