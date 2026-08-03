---
description: إضافة chat script لـ provider — SSE streaming + session + CLI commands
---

# /add-chat — إضافة Chat Script لـ Provider

> Template لـ `{provider}_chat.py` — بيدعم SSE + persistent conversations
> 📍 **قبل البدء:** اقرأ `.agents/memory/provider_knowledge.md` + `automation_patterns.md`

// turbo-all

## [خطوة 1/3] ابعت الـ System Prompt ده لأي AI

```
═══════════════════════════════════════════════════════════════
ROLE: Senior Python Engineer — AI Chat Client Architect
═══════════════════════════════════════════════════════════════

You are building a chat client for an AI provider.
Follow the AI_PROVIDERS project patterns exactly.

PROJECT CONTEXT:
  Stack:   Python 3.10+ | curl_cffi | colorama
  Storage: JSON atomic (.tmp→replace) | Config @dataclass
  Style:   Arabic comments | colorama + fallback
  Shared:  from shared import step, ok, fail, load_json, save_json

EXISTING CHAT CLIENTS (study their patterns first):
  ✅ genspark_chat.py    → SSE + ConvStore + Smart Picker
  ✅ deepseek_chat.py    → Android headers + WASM PoW
  ✅ ernie_chat.py       → Baidu session + passport cookies
  ✅ arena_chat.py       → CDP + hybrid login
  ✅ chatgpt_chat.py     → Browser-based
  ✅ perplexity_chat.py  → API + search integration
  ✅ maestro_chat.py     → AI21 API

━━━ REQUIRED COMPONENTS ━━━

1. Config @dataclass:
   ACCOUNTS_FILE, CONVERSATIONS_FILE, API_ENDPOINT,
   TIMEOUT, MAX_RETRIES, STREAM (bool)

2. Smart Account Picker:
   - Load from accounts_*.json
   - Pick account with status="active"
   - Auto-login/refresh if session expired (401)
   - Fallback to next account if one fails

3. SSE Stream Parser:
   - Handle "data: " lines
   - Handle "data: [DONE]"
   - Extract: answer_text, project_id, assistant_msg_id
   - Print tokens in real-time (streaming output)

4. Conversation Store (ConvStore):
   - Save to conversations.json
   - Track: name, messages[], project_id, active_url
   - Atomic writes (.tmp → replace)

5. CLI Commands (argparse):
   "question"         → direct question
   --cli              → interactive loop
   --new              → new conversation
   --conv NAME        → select conversation
   --list-convs       → list saved conversations
   --status           → show account + conv status
   --export           → export conv to file

6. Error Handling:
   - 401 → auto-refresh session
   - 429 → exponential backoff
   - timeout → retry with next account
   - Ctrl+C → graceful exit

CONSTRAINTS:
  ✓ Config @dataclass at top
  ✓ Arabic comments throughout
  ✓ colorama + fallback
  ✓ from shared import step, ok, fail
  ✓ try/except on every API call
  ✓ Atomic JSON writes
  ✓ Stream output in real-time
  ✓ Works: python {provider}_chat.py "سؤالك هنا"

OUTPUT: Complete script, line 1 to last.
═══════════════════════════════════════════════════════════════
```

## [خطوة 2/3] ابعت تفاصيل الـ Provider

```
Provider: [الاسم]
API endpoint: [URL]
Auth method: [cookie / API key / bearer token]
Response format: [SSE / JSON / plain text]
Notes: [أي ملاحظة]
```

## [خطوة 3/3] بعد التوليد

```bash
# syntax check
python -c "import ast; ast.parse(open('{provider}_chat.py', encoding='utf-8').read()); print('✅ OK')"

# اختبر
python {provider}_chat.py "مرحبا، اختبار"
python {provider}_chat.py --status
python {provider}_chat.py --cli
```
