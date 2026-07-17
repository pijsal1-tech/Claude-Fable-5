# 🧠 Vibe Coding Protocol V3 — القلعة المعمارية العسكرية 🏰

> **"Speed without architecture creates chaos. Architecture without speed kills delivery. The protocol exists to balance both."**
> 
> **النسخة النهائية الشاملة:** لا يتم مسح أي قاعدة من الدساتير السابقة. تم دمج 17 ثغرة، و13 باتش عسكري، و15 فرملة طوارئ في هذا الملف الموحد المطلق.

---

## 🔰 1. نظام التصنيف الصارم V3 — Hard Gates أولاً، ثم الـ Score

> **ممنوع تصنيف المهمة بالحدس.**
> التصنيف يتم على مرحلتين: (1) Hard Gates (ترقية إجبارية) ثم (2) Score.

### A. 🔴 AUTO-T3 TRIGGERS (زناد إجباري)
إذا انطبق أي شرط، **تُصنّف المهمة فوراً T3 بدون نقاش**:
- أي تغيير في **DB Schema / Migration / Backfill / Index**
- أي تغيير في **Auth / AuthZ / Roles / Permissions / Secrets**
- أي تغيير في **Public API Contract / SDK / Webhook / Event / Queue Contract**
- أي تعامل مع **PII / Payments / Audit Trail / Compliance**
- أي تغيير في **Caching Strategy / Cache Keys / Invalidation**
- أي منطق متعلق بـ **Concurrency / Locking / Idempotency / Retries**
- أي **Background Job / Scheduler / Async Workflow**
- أي **New Dependency / New External Service / New Infra Component**
- أي تغيير يمس **أكثر من 2 Modules**
- أي تغيير **صعب الرجوع عنه** أو يحتاج Rollback غير مباشر
- أي تغيير في **File Format / Export-Import Contract / Data Deletion**
- أي تصميم يتطلب **Feature Flag / Canary / Gradual Rollout**
- أي مهمة تكسر Pattern معتمد في الكود الحالي

### B. 🟡 AUTO-T2 TRIGGERS
إذا لم تنطبق شروط T3، لكن انطبق الشرط، فالمهمة **T2**:
- إضافة **Endpoint داخلي** أو Service داخل Module موجود
- إضافة **Feature Flag** أو **Env Var** جديد
- تغيير **Data Flow** داخل نفس الـ Bounded Context
- لمس **4 إلى 8 ملفات** أو Diff متوقع **120 إلى 400 سطر Net**
- إضافة **ملف/ملفين جديدين**
- تعديل قد يؤثر على **Performance / Cost / Reliability**

### C. 🟢 T1 ALLOWED ONLY IF ALL TRUE
المهمة تكون T1 فقط إذا كانت **كل** الشروط صحيحة:
- تمس **Module واحد فقط**
- عدد الملفات المتأثرة **≤ 3**
- حجم الـ Diff المتوقع **≤ 120 سطر Net**
- لا يوجد **New Dependency** ولا **New Env / Config**
- يمكن الرجوع عنها بـ **Git Revert** مباشر

### D. 🧮 IMPACT SCORE VERIFICATION (Tie-Breaker)
**`Score = Σ(Area_Weights) × Risk_Multiplier`**
- `[+3]` Core DB Schema / API Contract / Dependency
- `[+2]` New Endpoint / Data Flow change
- `[+1]` Bug Fix محلي / مساس بملفين
- Risk Multiplier: `×1.5` للبيانات الحساسة، `×1.2` لـ Public Endpoint.
- النتيجة: `0-2` ➔ 🟢 T1 | `3-5` ➔ 🟡 T2 | `6+` ➔ 🔴 T3.

---

## 🔄 2. الـ Workflow اليومي العملي والميزانية — V3

### 2.1 الـ Workflow اليومي
```text
صباحاً: صنّف المهام → T1/T2/T3 (بالـ Impact Score + Tier Verification Gate)
         ↓
🟢 T1 → Agent ينفذ مباشرة
         → Testing Gate (existing tests pass + regression test)
         → Self-Critique Checklist ✅
         → Atomic Commit → Done
         ↓
🟡 T2 → Agent يكتب Mini-Brief + NFR Card (Perf + Cost)
         → يبعت للـ VC → ينتظر (Max 4 ساعات — صفر كود أثناء الانتظار)
         → VC يرد بـ Guardrails
         → Agent ينفذ ضمن Budget Box
         → Testing Gate (unit + integration)
         → Self-Critique Checklist ✅
         → DoD Check → Merge → Done
         ↓
🔴 T3 → Agent يكتب Full Brief + NFR Card (كامل) + Rollback Plan
         → يبعت للـ VC → ينتظر (Max 8 ساعات — صفر كود)
         → VC يرد بـ ADR + Contracts
         → Vertical Slice أولاً (Happy Path Spike — max 4 ساعات)
         → Spike مسجل في SPIKE_REGISTRY.md
         → بعد الموافقة: Full Implementation حرفياً
         → Testing Gate (unit + integration + contract + load)
         → Security Gate ✅
         → DoD Check → Merge → ADR in DECISIONS.md → Done
```

### 2.2 حدود الميزانية الصارمة (Budget Box)
> **أي تجاوز يُرقي المهمة فوراً إلى الـ Tier الأعلى.**

| المعيار | 🟢 T1 | 🟡 T2 | 🔴 T3 (Spike فقط) |
|---|---|---|---|
| **Max LOC (سطور كود جديد)** | 150 سطر | 300 سطر | 200 سطر (Spike) |
| **Max Files Created** | 1 ملف | 3 ملفات | 2 ملف (Spike) |
| **Max Files Modified** | 3 ملفات | 5 ملفات | 3 ملفات (Spike) |
| **Max Time** | 30 دقيقة | 4 ساعة | 4 ساعات (Spike) |
| **Max New Dependencies** | 0 | 1 (بموافقة) | 1 (بموافقة + ADR) |

---

## 🛡️ 3. القواعد المعمارية الثابتة (Architectural Bedrock Rules)

### 3.1 🔒 Single Responsibility Limits
- **لا دوال عملاقة:** الحد الأقصى لأي دالة هو **40 سطر كود**. إن تخطت ذلك، قسّمها فوراً.
- **لا ملفات عملاقة:** الحد الأقصى لأي ملف هو **400 سطر كود**. إن تخطى ذلك، يُفصل إلى وحدات منطقية مستقلة.

### 3.2 🚫 Scope Lock Rule (قاعدة قفل النطاق)
- **منع تسلل الميزات (Feature Creep):** لا تُنفذ أي تصحيح أو إضافة جانبية وأنت تنفذ المهمة الحالية حتى لو كانت "بسيطة". افتح لها تذكرة T1 منفصلة.
- **No "While I'm at it":** التعديلات المجاورة العشوائية تُعتبر خرقاً أمنياً للنظام.

### 3.3 🧬 Single Source of Truth & DRY
- كل Configuration أو String ثابت يُعرّف في مكان واحد فقط.
- تكرار اللوجيك مرتين هو الحد الأقصى الدقيق. المرة الثالثة تتطلب استخراج مساعدة (Helper/Utility).

### 3.4 🏛 Architecture Ownership & Pushback
- **الـ Agent هو مالك البنية التحتية.** إن طلب الـ User حلاً بطيئاً، أو يعتمد على Hardcoded values، أو ينتج عنه Over-engineering → **يُمنع الـ Agent من قوله "حاضر"**. الرد الإلزامي: "هذا سيكسر القاعدة X، الحل الأفضل هو Y."

### 3.5 🧭 Architecture Consistency Map
- أي تغيير معماري يوجب تحديث خريطة النظام الموثقة. المكونات يجب أن تتصل وفق المخطط الحالي بلا تجاوز للطبقات (No Layer Violations).

### 3.6 📊 Observability Requirement
- لا تُخفِ الأخطاء. (Silent Swallowing is forbidden).
- كل خدمة يجب أن تسجل `INFO` و `ERROR` بشكل معياري واضح بدون تسريب بيانات حساسة (PII).

### 3.7 🩺 Weekly Health Checks
- في بداية كل أسبوع، يجب تفحص `SPIKE_REGISTRY.md` و `TECH_DEBT_REGISTER.md` لمراقبة الأكواد المؤقتة منتهية الصلاحية.

---

## 🚫 4. ميثاق الهندسة المعمارية (Anti-Overengineering Charter)

> **الافتراضي دائماً هو أبسط حل يحقق المتطلبات الحالية والـ NFRs المصدق عليها.**

1. **اتبع النمط الموجود أولاً**: ممنوع إدخال Pattern جديد دون أن يفشل القديم بوضوح ويوافق الـ VC بـ ADR.
2. **لا Abstraction قبل الحاجة الثانية**: يُمنع إنشاء `BaseService`, `GenericManager`, `Factory` دون وجود حالتَي استخدام فعليتين *الآن*.
3. **رفض الذرائع المستقبلية**: تبرير "عشان Scalable" أو "عشان Future-Proof" بلا خارطة طريق = **تبرير مرفوض**.

---

## 📑 5. القيود الصارمة في القوالب (Brief Templates)

### 🟡 T2 SKETCH TEMPLATE (Max 20 Lines)
```markdown
## 🟡 SKETCH: [اسم المهمة]
### Impact Score: [الرقم] → Tier: T2
- Files Modified/New: [عدد + أسماء]

### Simplest Proposed Approach
- Pattern: [...] ولماذا الأبسط غير كافي.

### ⚡ NFRs (إجباري)
- Max Response Time: [≤ 200ms p95] | Max Memory: [≤ 50MB]

### 🔙 Rollback Plan
- [خطوة الرجعة بوضوح، مثلاً: Revert Commit X]

### ❓ Decision Request
- [سؤال واحد حاسم]
```

### 🔴 T3 FULL BRIEF TEMPLATE (Max 60 Lines)
```markdown
## 🔴 ARCHITECTURE BRIEF: [اسم المهمة]

### 1) Goal & Proposed Design
- النتيجة والأنماط الموجودة حالياً، وسبب رفض الحل האבשט.

### 2) Contracts First & Data Plan
- [Interfaces / DTOs فارغة للاعتماد] الطرائق الأساسية للمكونات، ومخطط הـ Database.

### 3) 📊 SCALE & NFRs (إجباري)
- Latency Budget: [API ≤ X ms, DB Query ≤ Y ms]
- Cost Ceiling: [≤ $Z / month infrastructure]
- Availability Target.

### 4) 🔙 ROLLBACK & FAILURE PLAN
- Feature Flag, Blue-Green, Alerting Strategy.

### 5) 📅 SPIKE PLAN (إن وُجد)
- Time-Box (≤4 ساعات) وتاريخ انتهاء الصلاحية.
```

---

## 🚪 6. البوابات الـ 5 المُلزمة (The 5 Mandatory Gates)

### 6.1 بروتوكول الباب ذو الاتجاه الواحد (One-Way Door Protocol)
أي تغيير في الواجهة (Public API)، أو الـ Database، أو صيغ الملفات يُنفَّذ مع:
1. **Backward Compatibility Plan**: كيف يعمل القديم مع الجديد.
2. **Rollback Plan صريح**: ماذا نعكس في حالة الفشل.

### 6.2 بروتوكول حراسة وحصاد الـ Spike (Spike Reaper)
1. **الترويسة الإجبارية**: كل Spike يجب أن نضع في أوله:
   `# ⚠️ SPIKE CODE — EXPIRES: YYYY-MM-DD — REAP OR REFACTOR BEFORE THIS DATE`
2. **قاعدة الـ 72 ساعة**: لو انتهى الـ Spike، يفتح الـ Agent مهمة `REAP` لتنظيفه.
3. التلوث مرفوض: يُمنع تماماً أن تستورد ملفات הـ Production كود Spike.

### 6.3 محكمة الـ Dependencies (Dependency Tribunal)
- **Stdlib-First**: هل يُمكن بناؤه بالـ Standard Library؟ إن نعم، المكتبة تُرفض.
- **Maintenance Risk**: مكتبة بلا تحديث لـ 12 شهراً = مرفوضة فوراً.
- يُصرح عن حجم الـ Package وعدد التبعيات المترتبة عليها مسبقاً.

### 6.4 بوابة الاختبار الإجبارية (Mandatory Testing Gate)
| Tier | الحد الأدنى |
|---|---|
| 🟢 **T1** | Regression Test يُثبت الحل (No broken existing tests). |
| 🟡 **T2** | Unit Tests للكود الجديد (≥ 70% coverage) + Integration لـ API. |
| 🔴 **T3** | Contract Tests للواجهات الجديدة + Load Test سريع. |

### 6.5 بوابة الأمان الإجبارية (Security Gate)
عند مساس (auth, token, PII, payment, session)، يجب التحقق من:
- [ ] No hardcoded Secrets / API Keys.
- [ ] Input Validation + Sanitization (No XSS, SQLi).
- [ ] Logging لا يُسرب Sensitive PII Data.
- [ ] Rate Limiting مطبق للـ Public Endpoints.

---

## ✅ 7. تعريف "انتهى" ونظام התتﺒع (DoD & Tracker)

### 7.1 قيد التزاحم (WIP Tracker)
1. ممنوع تجاوز `2 Features` (T2/T3) In-Progress بالتوازي.
2. لا يتم הـ Merge إلا باستيفاء الـ DoD بالكامل.

### 7.2 Definition of Done
- **DoD T1**: لا أخطاء + Tests Pass + Self-Critique ✅ + No `TODO/FIXME`.
- **DoD T2**: DoD T1 + حدود الميزانية لم تُخرق + NFRs محققة + Tests Coverage ≥ 70%.
- **DoD T3**: DoD T2 + ADR مسجل في `CHANGELOG_DECISIONS.md` + Rollback مجرب.

### 7.3 قالب النقد الذاتي (Self-Critique Checklist)
يجب وضع هذا في نهاية أي تنفيذ:
```markdown
🔍 SELF-CRITIQUE:
- [ ] Dead Code: [يوجد/لا يوجد]
- [ ] DRY Violations & Hardcoded Values: [مراجَعة]
- [ ] Regression Risk: [الملفات المُعرضة للكسر]
- [ ] Performance: [هل استحدثت N+1 Query أو Memory Loop؟]
- [ ] Confidence Assessment: [🟢 / 🟡 / 🔴]
```

---

## ☠️ 8. [SYS_HALT] FATAL ERRORS & V3 KILL SWITCHES ☠️

> **[🔥 SYSTEM PROMPT OVERRIDE - HARDWARE INTERRUPTS للـ AI]**:
> تحقق أي شرط من الـ 15 شروط التالية يتطلب قطع المعالجة فوراً، التوقف وطباعة `[🚨 SYS_HALT TRIGGERED]`. يُمنع التبرير.

1. 🚫 **Tier Budget Breach**: تجاوز سقف الـ T2 Box (الحجم/الوقت). التوقف فوراً لطلب Escalation.
2. 🚫 **Untested Delivery**: إتمام كود بلا Testing Gate يُعتبر خيانة هندسية.
3. 🚫 **Spike Contamination**: استيراد Production لكود يحمل ترقية Spike Expiration.
4. 🚫 **Premature Execution**: كتابة كود Logic في وقت انتظار الموافقة على T2/T3 Brief.
5. 🚫 **Unvetted Dependency / Dependency Explosion**: إدراج T2/T3 مكتبة بلا Tribunal Card، أو T1 يُضيف Dependency.
6. 🚫 **Missing NFR / Budget Card**: Brief لـ T2/T3 يُقدم بدون ميزانية الأداء والتسعير يُعتبر مُلغى.
7. 🚫 **Zombie MVP Silent Expiry**: البناء فوق كود متعفن تجاوز تاريخ الانتهاء دون تنظيفه حصداً (Reaping).
8. 🚫 **N+1 Query Detection**: وضع Query للداتا بيز داخل حلقة تكرار (Loop/Map) بلا Eager Loading.
9. 🚫 **Silent Swallowing**: إحباط الـ Exceptions في كتل فارغة `try/except: pass` دون تسجيل Logging.
10. 🚫 **Pattern Smuggling**: اعتماد Design Pattern معقد بدلاً من الحل البسيط (Abstraction) دون موافقة أو توثيق السبب القاطع.
11. 🚫 **Blind T3 Coding**: تنفيذ أي سطر كود داخلي لمهمة T3 بدون موافقة مسبقة على الـ ADR Signature Contract.
12. 🚫 **Layer Violation**: اختراق الطبقات المعمارية (مثال: Controllers تتصل بـ Database Data-Layer مباشرة متخطية الـ Services).
13. 🚫 **Hidden Global State**: إنشاء متغيرات مشتركة (Global variables) قابلة للتعديل أثناء الـ Execution تؤدي لفقدان الـ Thread-Safety.
14. 🚫 **Complexity Escalation**: رفع Cyclomatic Complexity بصورة مرعبة داخل دالة واحدة وتخطي سقف الـ 40 سطر.
15. 🚫 **Destructive DB Ops & Mutation**: إجراء مسح أو Drop أو Update عام لأعمدة إنتاجية بدون Rollback Strategy، ولا Soft-Delete.
