# 📖 EXAMPLES.md — Multi-Agent Review Test Cases

> 5 سيناريوهات حقيقية لاختبار الـ Orchestrator + Merge Engine

---

## 🧪 Case 1: Dedup بـ Fingerprint — 3 agents يشوفوا نفس الـ bug

### Input Code:
```python
@dataclass
class Config:
    timeout: int = 30

def save_file(cfg):
    prefix = cfg.save_prefix_q  # ← field مش موجود!
```

### Expected: 3 agents يبلّغوا — finding واحد بعد الـ merge

**مراجع أخطاء:**
```json
{"id": "BUG-001", "rule": "Undefined Attribute", "severity": "critical",
 "fingerprint": "config.py|Config|missing_field|save_prefix_q",
 "evidence": "line 6: cfg.save_prefix_q", "evidence_quality": "direct",
 "reported_by": ["مراجع_أخطاء"]}
```

**محقق عميق:**
```json
{"id": "ROOT-001", "rule": "Incomplete Contract", "severity": "high",
 "fingerprint": "config.py|Config|missing_field|save_prefix_q",
 "evidence": "line 6: AttributeError at runtime", "evidence_quality": "direct",
 "reported_by": ["محقق_أخطاء_عميق"]}
```

**مراجع الكود V4:**
```json
{"id": "A2", "rule": "Missing @dataclass Field", "severity": "critical",
 "fingerprint": "config.py|Config|missing_field|save_prefix_q",
 "evidence": "line 6: cfg.save_prefix_q — field not in dataclass", "evidence_quality": "direct",
 "reported_by": ["مراجع_الكود_الآمن_V4"]}
```

### ✅ After Merge (FUSION):
```json
{
  "id": "F-001",
  "rule": "Missing @dataclass Field",
  "severity": "critical",
  "fingerprint": "config.py|Config|missing_field|save_prefix_q",
  "evidence_quality": "direct",
  "confidence": "HIGH",
  "reported_by": ["مراجع_أخطاء", "محقق_أخطاء_عميق", "مراجع_الكود_الآمن_V4"]
}
```

**لماذا نجح:** الـ fingerprint متطابق → MERGE → finding واحد بـ 3 reporters → HIGH ✅

---

## 🧪 Case 2: Conflict Resolution — Security vs Quality

### Input Code:
```python
def process_input(data):
    query = f"SELECT * FROM users WHERE name = '{data}'"
    cursor.execute(query)
```

### Agent Outputs:

**مهندس أمان:**
```json
{"id": "SEC-001", "rule": "SQL Injection", "severity": "critical",
 "fingerprint": "db.py|process_input|sql_injection|unsanitized_input",
 "evidence": "line 2: f-string in SQL query", "evidence_quality": "direct",
 "reported_by": ["مهندس_أمان"]}
```

**محلل جودة:**
```json
{"id": "QUAL-005", "rule": "String Formatting", "severity": "medium",
 "fingerprint": "db.py|process_input|sql_injection|unsanitized_input",
 "evidence": "line 2: should use parameterized query", "evidence_quality": "inferred",
 "reported_by": ["محلل_جودة"],
 "note": "input might come from internal validated source"}
```

### ✅ Conflict Resolution:
```
⚡ CONFLICT F-002:
  ✅ مهندس أمان:  "SQL injection مؤكد" — evidence: 🟢 DIRECT
  ⚠️  محلل جودة:  "ممكن input آمن" — evidence: 🟡 INFERRED
  → Rule Applied: Rule 1 (direct evidence wins) + Rule 2 (specialist wins)
  → Verdict: CRITICAL ✅
  → Reason: line-level proof + security specialist confirms
```

---

## 🧪 Case 3: نفس الـ bug في ملفين مختلفين — CLUSTER مش MERGE

### Input Code:
```python
# file: register.py
resp = requests.post(url, timeout=None)

# file: refresh.py  
resp = requests.post(url, timeout=None)
```

### Agent Output:
```json
// Finding 1
{"fingerprint": "register.py|register|no_timeout|requests_post", ...}

// Finding 2
{"fingerprint": "refresh.py|refresh|no_timeout|requests_post", ...}
```

### ✅ Expected: CLUSTER (مش MERGE)
```
🧩 ROOT CAUSE CLUSTER:
  🟡 Cluster 1: Missing Timeout Pattern
  ├─ F-003: register.py|register — no timeout [2 agents]
  └─ F-004: refresh.py|refresh — no timeout [2 agents]
  📝 Pattern: requests.post() بدون timeout في أكتر من ملف
```

**لماذا Cluster مش Merge:** fingerprint مختلف (ملفات مختلفة) لكن root_cause واحد

---

## 🧪 Case 4: No-Fit Fallback — كود بسيط بدون triggers

### Input Code:
```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

### Expected:
- **Detection Tags:** ∅ (مفيش)
- **Mode:** Fast (5 mandatory فقط)
- **Agents:** الـ 5 الإلزاميين بس

```
╔═══════════════════════════════════════════╗
║  🎭 Pre-Flight Check                     ║
║  الكود فيه: [لا شيء مميز]               ║
║  هشتغل بـ 5 agents (Fast Mode):         ║
╠═══════════════════════════════════════════╣
║  ✅ مراجع أخطاء         — runtime bugs   ║
║  ✅ محقق أخطاء عميق     — root cause    ║
║  ✅ محلل جودة           — code quality   ║
║  ✅ مهندس أمان          — security       ║
║  ✅ مراجع الكود الآمن   — safety V4     ║
╚═══════════════════════════════════════════╝
```

---

## 🧪 Case 5: FUSION Report كامل — كود حساس

### Input Code:
```python
API_KEY = "sk-proj-abc123"  # hardcoded!

async def charge_user(amount, user_id):
    resp = requests.post(PAYMENT_URL, json={"amount": amount})
    # no idempotency key!
    db.execute(f"UPDATE balance SET amount={amount} WHERE uid='{user_id}'")
```

### Expected Detection:
- Tags: `api`, `async`, `database`
- Mode: **Critical** (فيه payment + auth)
- Agents: 5 mandatory + محلل API + مهندس Backend + مهندس بيانات = **8**

### Expected FUSION Report:
```
╔══════════════════════════════════════════════════════════╗
║  🎭 FUSION Report — payment.py                          ║
║  Mode: Critical | Agents: 8 | Duration: 3m 15s          ║
╠══════════════════════════════════════════════════════════╣
║  🔴 Critical: 2 | 🟠 High: 2 | 🟡 Med: 1 | 🟢 Low: 0  ║
║  🏆 Confidence: 91/100 | 🎯 Unique: 5 (من أصل 12 raw)  ║
╚══════════════════════════════════════════════════════════╝

━━━ 🔴 CRITICAL ━━━

❌ F-001 — Hardcoded API Key
┌──────────────────────────────────────────────────────┐
│ 🔑 Fingerprint: payment.py|module|hardcoded_secret|api_key │
│ 📍 Evidence:    line 1: API_KEY = "sk-proj-abc123"   │
│ 📊 Ev.Quality:  🟢 DIRECT                           │
│ 👥 Confirmed:   3/8 (أمان + V4 + أخطاء)             │
│ 🎯 Confidence:  ✅ HIGH (+specialist bonus)          │
│ 💊 Fix:         API_KEY = os.getenv("API_KEY")       │
└──────────────────────────────────────────────────────┘
⛔ SECURITY HALT — approval BLOCKED

❌ F-002 — SQL Injection
┌──────────────────────────────────────────────────────┐
│ 🔑 Fingerprint: payment.py|charge_user|sql_injection|fstring │
│ 📍 Evidence:    line 6: f"UPDATE...{user_id}"        │
│ 📊 Ev.Quality:  🟢 DIRECT                           │
│ 👥 Confirmed:   2/8 (أمان + بيانات)                  │
│ 🎯 Confidence:  ✅ HIGH (+specialist: أمان+بيانات)   │
│ 💊 Fix:         db.execute("UPDATE...WHERE uid=?", (user_id,)) │
└──────────────────────────────────────────────────────┘

━━━ 🟠 HIGH ━━━

❌ F-003 — Missing Idempotency Key
┌──────────────────────────────────────────────────────┐
│ 🔑 Fingerprint: payment.py|charge_user|no_idempotency|payment_retry │
│ 📊 Ev.Quality:  🟡 INFERRED                         │
│ 👥 Confirmed:   2/8 (API Flow + V4)                  │
│ 🎯 Confidence:  ⚠️ MEDIUM                           │
└──────────────────────────────────────────────────────┘

❌ F-004 — Sync requests in async function
┌──────────────────────────────────────────────────────┐
│ 🔑 Fingerprint: payment.py|charge_user|sync_in_async|requests │
│ 📊 Ev.Quality:  🟢 DIRECT                           │
│ 👥 Confirmed:   2/8 (Backend + V4)                    │
│ 🎯 Confidence:  ✅ HIGH (+specialist: Backend)       │
└──────────────────────────────────────────────────────┘

━━━ 📊 FINAL VERDICT ━━━
┌──────────────────────────────────────────────────────┐
│ 🏆 Confidence: 91/100                                │
│ Evidence: 60% direct / 20% inferred / 20% heuristic │
│ 🚨 VERDICT: ⛔ BLOCK (security halt active)         │
└──────────────────────────────────────────────────────┘

  🛠️ FIX NOW:     F-001 (secret), F-002 (SQL injection)
  📅 THIS SPRINT: F-003 (idempotency), F-004 (async)
  👁️ MONITOR:     F-005 (minor)

━━━ 👁️ BLIND SPOTS ━━━
  - هل `amount` قيمة موالية أم مبلغ كامل
  - هل فيه retry middleware خارج الكود ده
  - اختبارات integration مش موجودة

  💡 الزتونة: الكود فيه 2 security HALT — hardcoded key + SQL injection.
     كمان فيه sync requests في async function ومفيش idempotency.
```

---

## ✅ Checklist — الـ 5 Cases بتختبر إيه

| Case | يختبر | Expected |
|------|-------|----------|
| 1 | Dedup بـ fingerprint | 3 findings → 1 merged |
| 2 | Conflict Resolution (Rule 1+2) | Specialist + direct evidence wins |
| 3 | Cluster vs Merge | Same root cause, different files = cluster |
| 4 | No-Fit Fallback | No tags → 5 mandatory only |
| 5 | Full FUSION Report | Critical mode + all features |
