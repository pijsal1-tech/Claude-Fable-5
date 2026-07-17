# 📊 PLANNING TRACKER — V4
# ADR + Pre-mortem + RICE + Google Metrics + Amazon PR/FAQ

> **انسخ لكل مشروع. حدّثه بعد كل محادثة. الصقه في أي AI للاستمرار.**

---

## 📰 Amazon Working Backwards — PR/FAQ

```
العنوان: [...]
الفئة المستهدفة: [...]
المشكلة: [...]
الحل: [...]
النتيجة: [...]
اقتباس افتراضي: "[...]"

FAQ:
Q1: [أصعب سؤال تقني؟] → A: [...]
Q2: [التكلفة/الوقت؟] → A: [...]
Q3: [المخاطرة الأكبر؟] → A: [...]
```

---

## 🎯 Scope Definition

```
✅ Goals:
• G1: [...]
• G2: [...]

❌ Non-Goals (خارج الـ scope — عمداً):
• NG1: [...] — السبب: [...]
• NG2: [...] — السبب: [...]
```

---

## 📊 Key Metrics for Success

| الميتريك | Target | طريقة القياس | الحالة |
|---------|--------|-------------|--------|
| [M1] | [X] | [إزاي] | ⏳ |
| [M2] | [Y] | [إزاي] | ⏳ |
| Counter-metric | لا نتجاوز [Z] | [إزاي] | ⏳ |

---

## ❓ Open Questions

| # | السؤال | المالك | ETA | الحالة |
|---|--------|--------|-----|--------|
| OQ1 | [...] | [...] | [...] | 🔴 مفتوح |
| OQ2 | [...] | [...] | [...] | 🟡 جار |

---

## 📊 RICE Scoring

```
RICE = (Reach × Impact × Confidence%) ÷ Effort

┌──────────────┬───────┬───────┬────────┬────────┬──────────┐
│ ADR/Feature  │Reach  │Impact │Confid. │Effort  │RICE Score│
├──────────────┼───────┼───────┼────────┼────────┼──────────┤
│ ADR-01       │       │       │   %    │        │          │
│ ADR-02       │       │       │   %    │        │          │
└──────────────┴───────┴───────┴────────┴────────┴──────────┘
Priority Order: 1st=[ADR-X] | 2nd=[ADR-Y] | 3rd=[ADR-Z]
```

---

## 📋 ADR Log

### ADR-01: [عنوان]

```
Status: [Proposed/Accepted/Superseded/Deprecated]
RICE: [score]
Context: [...]
Decision: [...]
  MUST: [...] | SHOULD: [...] | MUST NOT: [...]
Rationale: [...]
Consequences: ✅[...] ❌[...] ⚠️[...]
Metric Impact: [M1: +X% / —]
Superseded By: [ADR-X / —]
```

### ADR-02: [عنوان]
[نفس الهيكل]

---

## ⚡ Risk Matrix

```
┌─────────────────┬──────────┬──────────┬───────────┐
│ ADR             │Likelihood│  Impact  │Risk Level │
├─────────────────┼──────────┼──────────┼───────────┤
│ ADR-01          │    L     │    M     │    🟢     │
│ ADR-02          │    M     │    H     │    🔴     │
├─────────────────┼──────────┼──────────┼───────────┤
│ Overall         │          │          │    🟡     │
└─────────────────┴──────────┴──────────┴───────────┘
```

---

## 💀 Pre-mortem

```
"تخيل الفشل بعد 3 شهور"

1. [السبب] | ADR يحميه: [X/—] | الوقاية: [...]
2. [السبب] | ADR يحميه: [Y/—] | الوقاية: [...]
3. [السبب] | ADR يحميه: [Z/—] | الوقاية: [...]

Pre-mortem Score: [X/3]
```

---

## 📁 سجل المحادثات

| # | AI Tool | الموضوع | ADRs | آخر ADR |
|---|---------|---------|------|---------|
| 1 | [...] | [...] | 01-03 | ADR-03 |

---

## ✅ Execution Gates

```
Gate 1: [ ] PR/FAQ مكتوبة وواضحة
Gate 2: [ ] كل ADRs Critical → Accepted
Gate 3: [ ] Pre-mortem Score ≥ 2/3
Gate 4: [ ] Non-Goals محددة
Gate 5: [ ] Overall Risk 🟢 أو 🟡
Gate 6: [ ] موافقة "ابدأ التنفيذ"

Planning Quality: [X/10]
Top RICE: ADR-[X] = [score]
```

---

## 🚀 نسخة لـ AI التالي

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
من PLANNING_TRACKER V4:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
المشروع: [...]
PR/FAQ: "[عنوان] — [الحل المختصر]"
Goals: [...] | Non-Goals: [...]
Key Metrics: M1=[target] M2=[target]
RICE Top: ADR-[X]=[score]

ADR Log:
ADR-01: [عنوان] → Accepted | RICE=[X]
ADR-02: [عنوان] → Superseded → ADR-03

Pre-mortem: [X/3] | Risk: 🟡
آخر سؤال: رقم [X]
الطلب الجديد: [...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
