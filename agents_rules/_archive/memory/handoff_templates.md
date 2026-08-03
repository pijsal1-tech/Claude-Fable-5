# 📋 Handoff Templates — نماذج تسليم بين الـ Agents

## 1. Standard Handoff (تسليم عادي)
```
═══ 📋 HANDOFF ═══
From:    [Agent اللي خلّص]
To:      [Agent اللي هيكمل]
Task:    [وصف المهمة]
Status:  [done / partial]

Context:
  [إيه اللي اتعمل]

Files:
  - [file1.py] — [وصف]
  - [file2.py] — [وصف]

Deliverable:
  [إيه المطلوب من الـ agent الجاي]

Acceptance:
  □ [criterion 1]
  □ [criterion 2]
═══════════════════
```

## 2. QA PASS
```
═══ ✅ QA PASS ═══
Task:    [اسم المهمة]
Dev:     [Agent اللي عمل الكود]
QA:      [Agent اللي فحص]
Attempt: [N]/3

Evidence:
  📸 Screenshots: [N]
  📋 Tests: [passed/total]
  📊 Performance: [time]

Criteria:
  ✅ [criterion 1] — verified
  ✅ [criterion 2] — verified

→ Next: [proceed to next task]
═══════════════════
```

## 3. QA FAIL
```
═══ ❌ QA FAIL ═══
Task:    [اسم المهمة]
Dev:     [Agent]
QA:      [Agent]
Attempt: [N]/3

Issues:
  1. 🔴 [Issue] — L[line] — [fix instruction]
  2. 🟡 [Issue] — L[line] — [fix instruction]

Criteria:
  ✅ [criterion 1] — passed
  ❌ [criterion 2] — FAILED (see Issue 1)

→ Action: [Retry / Escalate]
═══════════════════
```

## 4. Escalation
```
═══ ⛔ ESCALATION ═══
Task:    [اسم المهمة]
Reason:  3 retries exhausted
Agent:   [اللي فشل]

History:
  Attempt 1: FAIL — [السبب]
  Attempt 2: FAIL — [السبب]
  Attempt 3: FAIL — [السبب]

Recommendation:
  [اقتراح حل مختلف أو agent تاني]

→ To: مدير الأوركسترا
═══════════════════════
```
