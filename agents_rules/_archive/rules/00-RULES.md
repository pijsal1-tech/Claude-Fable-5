# Hard Rules

## Safety
- Never run destructive actions without explicit user approval.
- Never remove files, database tables, or production assets casually.
- Never overwrite working logic unless the new logic is verified.
- Never assume missing behavior without evidence.

## Engineering Principles
- Keep it DRY.
- Prefer one source of truth.
- Keep modules small and focused.
- Avoid duplicated logic.
- Prefer explicit over implicit behavior.
- Prefer maintainable over clever.
- Prefer readable over compact when the tradeoff matters.

## Review Rules
- Every change must be checked twice before final approval.
- Every new function must be validated for:
  - input handling
  - output correctness
  - failure cases
  - integration impact
- Every change must be checked against the project vision and user journey.

## Meta-AI Review Protocol & Early Termination (Meta-AI Loop)
- **Continuous Team Review:** When developing or modifying a layer, leverage the user's AI team (`team_runner.py` via `chat_send.txt`). Submit your newly written code/logic to the team and read `00-All-Responses.md` for peer review, architecture hints, or syntax validation before finalizing.
- **Early Termination Hack (The Golden Rule):** NEVER wait for the entire AI team (especially slow models like DeepSeek R1) to finish their review unless explicitly needed. You MUST ask the user: *"أشغل فريق المراجعة لحد ما الفريق كله يخلص؟ ولا أوقفه بدري (Early Kill) بمجرد ما أسرع موديلين يردوا عشان منضيعش وقت؟"*. If the user opts for early termination, aggressively kill the `team_runner.py` process once 1-2 models have delivered their feedback, and continue your work immediately.

## Logical Reasoning Rules
- Every step must have a reason.
- Every architectural choice must answer: why this and not the simpler alternative?
- Every dependency must be justified.
- Every UI/UX change must improve the user journey.

## Quality Gates
- No code without a review pass.
- No review without a checklist.
- No checklist without confirming the project goal.
- No final answer without checking regression risk.

## Learning & Grounding Rules
- **Changelog Updates:** Whenever you solve a complex bug or make a major architectural decision, you MUST document the issue and the solution in `.agents/memory/CHANGELOG_DECISIONS.md` to prevent future regressions.
- **No Hallucination (Strict Grounding):** When generating repetitive code patterns (like Config Classes), you are FORBIDDEN from inventing structures from scratch. You MUST read `.agents/memory/00-EXAMPLES.md` and strictly follow the reference implementation provided there.
- **Flexibility with Secrets:** The user is allowed to store API keys and secrets freely in scripts, JSON, or text files during experiments. Do not block or warn the user about this.

---

## Provider-Specific Rules (إلزامية)

### Monitor Interface
- كل `refresh.py` **لازم** يحتوي على: `def refresh(email: str) -> bool`
- لو الملف فيه دالة باسم تاني → ضيف wrapper في الآخر
- `monitor.py` بيستدعي `refresh(email)` — مش أي اسم تاني

### Accounts Storage
- `accounts.json` = **atomic write** دايماً: `.tmp` → `.replace()`
- `expires_in` ممكن ييجي كـ `str` ('24h', '2d') — parse يشيل الـ units
- مسار كل provider: `.AAA_GGG_iii_VIBE_CODING/<provider>/`
- `monitor.py` BASE_DIR = `.AAA_GGG_iii_VIBE_CODING` — مش الـ root

### Browser Automation
- `uc=True` إلزامي لأي موقع فيه Cloudflare
- `user_data_dir` ممنوع — بيسبب port conflict
- React buttons → **CDP Runtime.evaluate + userGesture=True**
- `execute_script()` ممنوع لـ React — بيشتغل في isolated world

### Async Safety
- Selenium في async context → `asyncio.to_thread()` إلزامي
- `sleep()` ممنوع — استخدم `wait_for_element_visible()` بدله

### WAF & Bot Diagnostics (إلزامي جديد)
- لمهام تجاوز الحمايات (Cloudflare/Akamai/Datadome)، 403، 429، فشل WebSocket/gRPC، أو مشاكل OTP Block:
- **يُمنع التخمين أو تغيير الـ Headers عشوائياً.**
- **إلزامي:** يجب قراءة المرجع الهندسي `memory/WAF_BOT_DIAGNOSTIC_MASTER_PROMPT.md` وتطبيق الـ Playbook الموجود فيه قبل كتابة أو تعديل أي كود.

### Script & UI Architecture (Single File Pattern)
- جميع سكريبتات الأتمتة (مثل SMS Blasters) **يجب** أن تكون في ملف بايثون واحد (Single Self-Contained File).
- يُمنع إنشاء ملفات خارجية للواجهة مثل `cli_ux.py` لمنع تشتيت المشروع (إلا إذا طُلب صراحة).

### TLS & Fingerprint OPSEC
- بصمة التشفير (TLS Impersonation) يجب أن تتطابق 100% مع هيدر `User-Agent`.
- يُمنع دمج بصمة `Safari` مع هيدر `Chrome` أو العكس نهائياً، لأن هذا الخطأ يُكشف فوراً من أنظمة الحماية ويؤدي للـ Block السريع. استخدم حزمة بصمات/هيدرات من نفس العائلة (مثل Chrome فقط).

### Data Parsers & Libraries
- يجب الاعتماد الكلي على المكتبات الرسمية للمعالجة المعقدة (مثل الكشف عن الدولة برقم الهاتف باستخدام `phonenumbers`).
- يُمنع كتابة بدائل تعتمد على Regex يدوي أو قواميس Hardcoded كـ "Fallback" لأنها تخلق Tech Debt عالي وتبسط الأداء.
