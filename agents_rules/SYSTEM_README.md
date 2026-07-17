# 🎭 Multi-Agent Code Review System — Master Index

> بناء بواسطة زيزو | V2.5 Hardened | minimum 5 agents | FUSION Report

---

## ⚡ Quick Start

```
"افحص [كود]"        → Standard mode (5 + auto)
"افحص [كود] -n 7"   → 7 agents بالظبط
"افحص -شامل [كود]"  → Critical mode (7-10 agents)
"افحص -سريع [كود]"  → Fast mode (5 mandatory فقط)
```

### 🎚️ Review Modes
```
⚡ Fast     = 5 mandatory — للكود الصغير
📋 Standard = 5 + auto-selected — الافتراضي
🔴 Critical = 7-10 agents — payments/auth/migrations/prod
```

---

## 🏗️ Architecture

```
User: "افحص [كود]"
          ↓
  🎭 مدير المراجعة (Orchestrator)
     1. يحلل الكود → يكتشف context tags
     2. يختار 5+ agents تلقائياً
     3. يعرض Pre-flight للمستخدم
     4. يشغّل الـ agents (بالتوازي)
     5. يدمج النتائج (Merge Engine)
     6. يطلع FUSION Report واحد
```

---

## 👑 الـ 5 Mandatory Agents (لا استثناء)

| # | الملف | الدور | Layer |
|---|-------|-------|-------|
| 1 | `سيستم/أنت مراجع أخطاء.md` | Runtime bugs, crashes, logic | fatal/logic |
| 2 | `سيستم/أنت محقق أخطاء عميق.md` | 5-Whys root cause | logic |
| 3 | `سيستم/أنت محلل جودة.md` | DRY, SOLID, maintainability | quality |
| 4 | `سيستم/أنت مهندس أمان.md` | Security vulnerabilities | security |
| 5 | `هندسة-تطبيقات/أنت مراجع الكود الآمن.md` | Safety triage V4 (52 rules, 12 layers) | all |

---

## ➕ Optional Agents (Context-Based Auto-Added)

| الشرط | Agent | الملف |
|-------|-------|-------|
| HTTP calls | 🌐 محلل API Flow | `سيستم/أنت محلل API Flow.md` |
| SQL/ORM | 🗄️ مهندس بيانات | `هندسة-تطبيقات/أنت مهندس بيانات.md` |
| async/await | ⚙️ مهندس Backend | `هندسة-تطبيقات/أنت مهندس Backend.md` |
| Dockerfile/deploy | 🐳 DevOps | `هندسة-تطبيقات/أنت مهندس DevOps.md` |
| selenium/CDP | 🤖 مراجع Vibe | `سيستم/أنت مراجع Vibe.md` |
| migration/ALTER | 🗄️ Migration Safety | PROMPT_ENGINE_PRO — migration section |
| pytest/unittest | 🔎 فاحص بأدلة | `سيستم/أنت فاحص بأدلة.md` |
| loops/O(n) | 🚀 محلل أداء | `سيستم/أنت محلل أداء.md` |

---

## 🎭 Orchestrator

**الملف:** `سيستم/أنت مدير المراجعة.md` — V2.5 Hardened

**يحتوي على:**
- Detection logic (Python pseudo-code)
- Agent selection algorithm
- Interactive Pre-flight display
- 3 Review Modes (Fast/Standard/Critical)
- Severity Normalization Map
- Fingerprint-based Dedup
- 5 Deterministic Conflict Rules
- Specialist Bonus + Evidence Quality
- FUSION Report w/ Blind Spots
- 4-level Verdict (APPROVE/APPROVE_WITH_CHANGES/REQUIRES_FIXES/BLOCK)

---

## 📐 Finding Schema — الصيغة الموحدة

كل agent يطلع findings بالصيغة دي:

```json
{
  "id": "BUG-001",
  "rule": "اسم القاعدة",
  "severity": "critical | high | medium | low",
  "layer": "fatal | logic | security | quality | ...",
  "fingerprint": "file|symbol|issue_type|root_cause",
  "evidence": "line X: snippet",
  "evidence_quality": "direct | inferred | heuristic",
  "root_cause": "لماذا حصل",
  "fix": "أصغر patch صح",
  "test": "regression test",
  "confidence": "confirmed | likely | needs_verification",
  "reported_by": ["agent_name"],
  "false_positive_guard": "متى ماينفعش تبلّغ"
}
```

---

## 📊 Merge Engine — 5 خطوات

```
0. Severity Normalization → تعريف موحد
1. Normalization  → JSON موحد + fingerprint + evidence_quality
2. Deduplication  → fingerprint-based (مش string)
3. Conflict       → 5 deterministic rules
4. Confidence     → base score + specialist bonus
```

### Severity Map
```
🔴 CRITICAL = security / data loss / prod outage
🟠 HIGH     = crash / wrong output / functional breakage
🟡 MEDIUM   = edge cases / maintainability
🟢 LOW      = style / readability
```

---

## 🔒 Security Rules

```
Security HALT → يمنع approval + بتكمل enumeration
لازم يتحل الأول قبل أي merge/approve
```

---

## 📁 File Structure الكاملة

```
.agents/
├── SYSTEM_README.md         ← أنت هنا
├── EXAMPLES.md              ← [TODO] test cases
├── سيستم/
│   ├── أنت مدير المراجعة.md     V2 ✅ Orchestrator
│   ├── أنت مراجع أخطاء.md       ✅ + JSON output
│   ├── أنت محقق أخطاء عميق.md  ✅ + JSON output
│   ├── أنت محلل جودة.md          ✅ + JSON output
│   ├── أنت مهندس أمان.md         ✅ + JSON output
│   ├── أنت محلل API Flow.md      ✅
│   ├── أنت محلل أداء.md           ✅
│   ├── أنت مراجع Vibe.md           ✅
│   ├── أنت فاحص بأدلة.md          ✅
│   └── PROMPT_ENGINE_PRO.md       ✅ 19 section
└── هندسة-تطبيقات/
    ├── أنت مراجع الكود الآمن.md  V4 ✅ (52 rules)
    ├── أنت مهندس Backend.md       ✅
    ├── أنت مهندس DevOps.md        ✅
    ├── أنت مهندس SRE.md           ✅
    └── أنت مهندس بيانات.md        ✅
```

---

## ✅ Acceptance Criteria للمطور

```
[ ] "افحص [كود]" → 5+ agents تلقائياً
[ ] كل agent يطلع JSON بالـ schema ده
[ ] Pre-flight قبل التنفيذ
[ ] Dedup: نفس السطر+نفس النوع = finding واحد
[ ] Confidence: HIGH(3+)/MEDIUM(2)/LOW(1)
[ ] FUSION Report واحد في الآخر
[ ] Security HALT يبلوك الـ approval
[ ] Agents بالتوازي مع fallback لو أي agent فشل
[ ] Timeout: 5 دقائق max
```

---

## 🚀 TODO اللي لسه ناقص (P1)

```
[ ] EXAMPLES.md — test cases حقيقية
[ ] JSON section في الـ optional agents (API Flow / أداء)
[ ] Integration test — تشغيل 5 agents فعلي
```
