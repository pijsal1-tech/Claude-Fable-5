---
description: تشغيل Spec-Kit — Spec-Driven Development كامل ومتكامل مع قواعد صارمة
---

# 📋 SPEC-KIT — SYSTEM WORKFLOW
# نظام تطوير مبني على المواصفات (SDD) — مرجع كامل

> **⛔ HARD RULES — لا استثناءات — لا تجاوز — صفر مرونة**
> هذا الملف = قانون التطوير في المشروع. أي مخالفة = إعادة من الصفر.

---

## 🔴 STATE MACHINE — الحالات الإلزامية

```
UNINITIALIZED
    │
    ▼ [constitution] ← مرة واحدة فقط
FOUNDED
    │
    ▼ [specify --target "..."]
SPECIFIED
    │
    ▼ [clarify] ← اختياري لكن مُوصى به
    │ (if ambiguous)
    ▼ [plan]
PLANNED
    │
    ▼ [tasks]
TASKED
    │
    ▼ [analyze]
    │
    ├──[NEEDS_REVISION]──► back to SPECIFIED or PLANNED
    │
    └──[READY]
         │
         ▼ [implement]
    IMPLEMENTING
         │
         ▼ [checklist]
    DONE ✅
```

> **⛔ BLOCKED TRANSITIONS — باطلة ومرفوضة:**
> - ❌ FOUNDED → PLANNED (بدون specify)
> - ❌ SPECIFIED → TASKED (بدون plan)
> - ❌ TASKED → IMPLEMENTING (بدون analyze READY)
> - ❌ أي حالة → IMPLEMENTING بدون Verdict = READY

---

## 🔒 PRE-CONDITIONS — شروط ما قبل التنفيذ

| الأمر | يتطلب | ينتج |
|-------|--------|-------|
| `constitution` | — | `.speckit/constitution.md` |
| `specify` | constitution.md ✅ + `--target` | `.speckit/spec.md` |
| `clarify` | spec.md ✅ | أسئلة + إجابات في terminal |
| `plan` | spec.md ✅ | `.speckit/plan.md` |
| `tasks` | plan.md ✅ | `.speckit/tasks.md` |
| `analyze` | spec.md ✅ + plan.md ✅ + tasks.md ✅ | `.speckit/analysis.md` + Verdict |
| `implement` | analysis.md ✅ **Verdict=READY** | كود نفّذ |
| `checklist` | implement كاملة | `.speckit/checklist.md` |

---

## ⚡ الأوامر الكاملة — 8 Commands

### 🔍 0. Status — ابدأ هنا دايماً
```bash
# شوف وين أنت في الـ pipeline
python -m crew.speckit --command status
python -m crew.runner --speckit status
```
**يعرض:** كل ملفات .speckit/ + حجمها + الـ state الحالي + الخطوة الجاية

---

### 📜 1. Constitution — تأسيس المبادئ
> **⛔ يُنفَّذ مرة واحدة فقط — skip لو موجود**
> ⚡ TRIGGER: بداية أي مشروع جديد

```bash
python -m crew.speckit --command constitution
python -m crew.runner --speckit constitution

# مع موديل أقوى (مُوصى به للأساسيات):
python -m crew.speckit --command constitution --model gemini/gemini-2.0-pro
```

**ينتج:** `.speckit/constitution.md`
**يشمل:**
- المبادئ المعمارية الثابتة (5-7 مبادئ)
- القواعد التقنية (Non-Negotiable)
- الـ Stack المعتمد
- Anti-patterns الممنوعة

**✅ Verify:** لو `.speckit/constitution.md` موجودة → انتقل لـ specify

---

### 📋 2. Specify — كتابة المواصفات ⭐⭐⭐
> **⭐ أهم خطوة — الدقة هنا = جودة كل حاجة بعدها**
> ⚡ TRIGGER: عايز تبني فيتشر جديد

```bash
# الأمر الأساسي:
python -m crew.speckit --command specify --target "وصف الفيتشر بالتفصيل"
python -m crew.runner --speckit specify --target "وصف الفيتشر"

# مثال حقيقي:
python -m crew.speckit --command specify \
  --target "أضف نظام إدارة حسابات متعدد providers: يخزن الاكاونتات في JSON، يدعم CRUD، يعمل مع monitor.py، يفرق بين active/expired/banned"

# موديل أقوى للـ spec:
python -m crew.speckit --command specify --target "..." --model gemini/gemini-2.0-pro
```

**ينتج:** `.speckit/spec.md`
**يجب أن يشمل:**
- User Stories (As a / I want / So that)
- Acceptance Criteria (قابل للقياس)
- Functional Requirements (FR-01, FR-02, ...)
- Non-Functional Requirements (performance/security/...)
- Inputs & Outputs (جدول)
- Edge Cases
- Out of Scope (مهم جداً)

**❌ مش مقبول:**
- وصف مبهم أو عام جداً
- بدون Acceptance Criteria
- بدون Out of Scope

**⚡ بعده:** شغّل clarify لو في غموض — أو plan مباشرة

---

### ❓ 3. Clarify — أسئلة توضيحية (اختياري لكن مُوصى به)
> **💡 يوفر وقت أكتر مما بياخد — شغّله دايماً لو مش متأكد**
> ⚡ TRIGGER: spec.md فيها نقاط غامضة أو قرارات غير محسومة

```bash
python -m crew.speckit --command clarify
python -m crew.runner --speckit clarify
```

**يعرض:** 5-7 أسئلة محددة + سبب أهمية كل سؤال
**الـ Action:** جاوب الأسئلة ثم حدّث spec.md يدوياً أو شغّل specify تاني

---

### 🏗️ 4. Plan — التخطيط التقني ⭐⭐
> **⛔ يتطلب spec.md**
> ⚡ TRIGGER: بعد ما spec جاهزة ومحسومة

```bash
python -m crew.speckit --command plan
python -m crew.runner --speckit plan

# للمشاريع الكبيرة — موديل أثقل:
python -m crew.speckit --command plan --model gemini/gemini-2.0-pro
```

**ينتج:** `.speckit/plan.md`
**يجب أن يشمل:**
- Architecture Decision + Justification
- Files (NEW) + Files (MODIFY) — بمسارات كاملة
- Data Models (dataclasses/schemas)
- API Design (لو محتاج)
- Dependencies الجديدة + سببها
- Migration & Breaking Changes
- Success Criteria (قابلة للقياس)

**⛔ BLOCKED لو:**
- spec.md مش موجودة → `constitution` + `specify` أولاً
- spec.md أكبر من 7 أيام قديمة → راجع

---

### 📝 5. Tasks — تقسيم المهام ⭐⭐
> **⛔ يتطلب plan.md**
> ⚡ TRIGGER: بعد ما plan جاهزة ومراجعة

```bash
python -m crew.speckit --command tasks
python -m crew.runner --speckit tasks
```

**ينتج:** `.speckit/tasks.md`
**يجب أن يشمل:**
- TASK-01..N بترقيم تسلسلي
- Priority: P0 (critical) / P1 (important) / P2 (nice-to-have)
- الملف المتأثر بمسار كامل
- الـ Agent المناسب (من 30 agent)
- Effort: S (< 1h) / M (1-4h) / L (> 4h)
- Depends on: [TASK-IDs]
- Execution Order واضح

**✅ Definition of "Done" task:**
- محددة (ملف + سطر تقريبي)
- قابلة للاختبار (معروف إزاي تتحقق منها)
- مستقلة أو تبعياتها واضحة

---

### 🔍 6. Analyze — مراجعة التناسق ⭐⭐⭐ MANDATORY
> **⛔⛔⛔ إلزامي قبل أي تنفيذ — لا استثناء**
> ⚡ TRIGGER: بعد tasks — وقبل implement

```bash
python -m crew.speckit --command analyze
python -m crew.runner --speckit analyze
```

**ينتج:** `.speckit/analysis.md`
**يفحص:**
1. هل الـ spec تغطيها الـ plan 100%؟
2. هل الـ tasks تغطي الـ plan 100%؟
3. هل في تعارضات بين الـ artifacts؟
4. هل الـ Acceptance Criteria قابلة للقياس؟
5. هل ترتيب الـ tasks مع الـ dependencies صح؟
6. هل في risks غير محسوبة؟

**🏁 Verdict — حكم نهائي:**
```
✅ READY         → امضي للـ implement
⚠️ NEEDS_REVISION → ارجع لـ specify أو plan
❌ BLOCKED       → مشكلة كبيرة — ابدأ من البداية
```

**⛔ إذا Verdict ≠ READY → ممنوع تمسّ الكود**

---

### ⚙️ 7. Implement — التنفيذ
> **⛔ يتطلب Verdict = READY في analysis.md**
> ⚡ TRIGGER: بعد analyze READY

```bash
# عرض الـ tasks الجاهزة:
python -m crew.speckit --command implement

# تنفيذ عبر الأوركسترا (الموصى به):
python -m crew.runner --orchestrate review --target .speckit/plan.md
python -m crew.runner --orchestrate spec-kit --target "وصف الفيتشر"
python -m crew.runner --orchestrate factory --target "وصف المنتج"

# تفويض A2A لـ agent مناسب:
python -c "from crew.a2a import delegate_task; delegate_task('architect', 'نفذ TASK-01')"
```

**قواعد التنفيذ — إلزامية:**
```bash
# ← قبل أي تغيير
git add -A && git commit -m "📸 Backup before implement: [اسم الفيتشر]"

# ← بعد كل task
git add -A && git commit -m "✅ TASK-XX: [عنوان المهمة]"
```

**⛔ ممنوع:**
- تنفيذ أكثر من task في نفس الوقت بدون commit بينهم
- تجاوز الـ plan أو الـ tasks
- تعديل constitution.md أثناء التنفيذ

---

### ☑️ 8. Checklist — قوائم الجودة
> **آخر خطوة — إلزامية قبل merge**
> ⚡ TRIGGER: بعد كل implement tasks

```bash
python -m crew.speckit --command checklist
python -m crew.runner --speckit checklist
```

**ينتج:** `.speckit/checklist.md`
**يشمل 3 قوائم:**
- Pre-implementation (للتأكد تم التخطيط صح)
- Implementation (DRY / Types / Error Handling / Tests)
- Post-implementation (Criteria met / Performance / Security / Docs)
- Definition of Done

**✅ متى يُعتبر الفيتشر منتهي:**
- كل Acceptance Criteria ✅
- كل P0 tasks ✅
- checklist كاملة ✅
- git commit نظيف ✅
- مفيش TODO مفتوح ✅

---

## 🚀 ALL-IN-ONE — كل الـ Pipeline أمر واحد

```bash
# الـ Full Pipeline دفعة واحدة:
python -m crew.speckit --command all --target "وصف الفيتشر"
python -m crew.runner --speckit all --target "أضف نظام إدارة tokens بـ auto-refresh"
```

> ⚠️ يشغّل: constitution → specify → plan → tasks → analyze → checklist
> موديل أقوى مُوصى به للـ all command:
```bash
python -m crew.speckit --command all \
  --target "وصف الفيتشر" \
  --model gemini/gemini-2.0-pro
```

---

## 📁 بنية .speckit/ الكاملة

```
.speckit/
├── constitution.md    ← المبادئ الثابتة (مرة واحدة)
├── spec.md           ← المواصفات الحالية
├── plan.md           ← الخطة التقنية
├── tasks.md          ← قائمة المهام
├── analysis.md       ← تقرير التناسق + Verdict
├── checklist.md      ← قوائم الجودة
└── state.json        ← الـ State الحالي (لا تمسحه!)
```

> ⛔ `.speckit/` مش في `.gitignore` — commit كل الـ artifacts
> ✅ كل artifact = وثيقة حية تُراجع وتُحدَّث

---

## 🔗 الربط مع الأوركسترا (6 Patterns)

```bash
# مراجعة الـ plan قبل التنفيذ:
python -m crew.runner --orchestrate review --target .speckit/plan.md

# Spec-Kit orchestration pattern كامل:
python -m crew.runner --orchestrate spec-kit --target "وصف الفيتشر"

# Software Factory (للمنتجات الكبيرة):
python -m crew.runner --orchestrate factory --target "وصف المنتج"

# فحص أمني على الكود الجديد:
python -m crew.runner --orchestrate security --target <new_file.py>
```

---

## 🧠 الربط مع A2A (Agent-to-Agent)

```bash
# عرض كل الـ agents وقدراتهم:
python -m crew.a2a

# تفويض مهمة لأنسب agent تلقائياً:
python -c "
from crew.a2a import delegate_task
# تخطيط:
result = delegate_task('plan', 'خطط لإضافة OAuth2 لـ Genspark provider')
# توثيق:
result = delegate_task('document', 'وثّق الـ API endpoints الجديدة')
# مراجعة أمنية:
result = delegate_task('security-audit', 'افحص token storage المضاف')
"
```

---

## 🔌 الربط مع MCP Server

```bash
# تشغيل MCP Server (Cursor / Claude Code / AntiGravity يستخدمه مباشرة):
python -m crew.mcp_server

# MCP config في .mcp.json أو claude_desktop_config.json:
```
```json
{
  "mcpServers": {
    "ai-providers-crew": {
      "command": "python",
      "args": ["-m", "crew.mcp_server"],
      "cwd": "D:\\SMS\\AI_PROVIDERS"
    }
  }
}
```

**5 MCP Tools متاحة:**
- `read_project_file` — قراءة أي ملف
- `inspect_accounts` — فحص حسابات provider
- `project_map` — خريطة المشروع
- `list_agents` — عرض 30 agent
- `orchestrate` — تشغيل الأوركسترا

---

## 💾 الربط مع Memory System

```bash
# عرض الجلسات السابقة:
python -m crew.memory

# بحث في الذاكرة:
python -c "
from crew.memory import AgentMemory
mem = AgentMemory()
results = mem.recall('spec-kit genspark')
for r in results:
    print(r['target'])
"
```

---

## 🛠️ تثبيت Specify CLI الرسمي (اختياري)

> للاستخدام مع Cursor / Claude Code / AntiGravity مباشرة

```bash
# تثبيت دائم عبر uv (مُوصى به):
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# تهيئة في المشروع الحالي:
specify init --here --ai agy      # AntiGravity
specify init --here --ai gemini   # Gemini CLI
specify init --here --ai claude   # Claude Code
specify init --here --ai cursor-agent  # Cursor

# التحقق من التثبيت:
specify check

# تحديث:
uv tool upgrade specify-cli
```

> بعد التهيئة: `/speckit.constitution`, `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement` متاحة مباشرة في الـ AI agent

---

## ⚡ Shortcuts — اختصارات عملية

```bash
# التحقق من الحالة:
python -m crew.speckit --command status

# إعادة analyze لو عدّلت spec أو plan:
python -m crew.speckit --command analyze

# إعادة tasks بعد تعديل plan:
python -m crew.speckit --command tasks && python -m crew.speckit --command analyze
```

---

## 🚨 RED FLAGS — توقّف فوراً

```
❌ بدأت implement وـ Verdict ≠ READY
❌ كتبت كود قبل tasks
❌ تجاوزت analyze
❌ plan.md مش موجودة وبدأت tasks
❌ spec.md مش موجودة وبدأت plan
❌ constitution مش موجودة وبدأت specify
❌ حذفت .speckit/state.json
❌ عدّلت constitution.md أثناء التنفيذ
❌ فيه TODO مفتوح في الكود وعملت merge
❌ مفيش git commit قبل implement
```

**الحل دايماً:** `python -m crew.speckit --command status` وابدأ من الخطوة الصح

---

## 📊 Metrics — مقاييس الجودة

| Metric | Target | Command |
|--------|--------|---------|
| Time spec→plan | < 30 دقيقة | — |
| Tasks P0 completion | 100% | checklist |
| Acceptance Criteria met | 100% | checklist |
| Analyze Verdict | READY أول مرة | analyze |
| Git commits per task | ≥ 1 | implement |
| Dead code added | 0 | review |

---

## 🔄 Recovery — لو حاجة اتكسرت

```bash
# شوف الحالة:
python -m crew.speckit --command status

# Rollback لـ spec وابدأ من plan:
# 1. عدّل .speckit/spec.md يدوياً
# 2. شغّل:
python -m crew.speckit --command plan
python -m crew.speckit --command tasks
python -m crew.speckit --command analyze

# لو محتاج ترجع للكود:
git log --oneline -10
git checkout <commit-hash> -- <file>

# لو .speckit/ اتحذفت:
python -m crew.speckit --command constitution
python -m crew.speckit --command specify --target "[نفس الوصف]"
# وكمّل من هناك
```
