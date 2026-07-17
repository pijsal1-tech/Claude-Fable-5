╔══════════════════════════════════════════════════════════╗
║ 🎭 FUSION REPORT — تقرير مدمج                           ║
║ Agents: 8 | Mode: Auto | Strict                          ║
╠══════════╦══════════╦══════════╦══════════╗
║ 🔴 Fatal ║ 🟠 High  ║ 🟡 Medium║ 🟢 Low   ║
║    0     ║    3     ║    4     ║    2     ║
╚══════════╩══════════╩══════════╩══════════╝
🏆 Confidence Score: 82/100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pre-Flight — Agents المختارة (8 Agents)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ مراجع أخطاء         — Runtime bugs + ownership logic
  ✅ محقق أخطاء عميق     — Root cause analysis للـ 500
  ✅ محلل جودة           — Code smells + duplication
  ✅ مهندس أمان          — Security on cookies/sessions
  ✅ مراجع الكود الآمن   — Safety triage (Mandatory)
  ✅ محلل API Flow       — HTTP/Genspark API patterns
  ✅ مهندس Backend       — Architecture + async design
  ✅ فاحص بأدلة          — Evidence-based verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• أخطر مشكلة: مفيش "account rotation" حقيقي — نفس الحساب مقفول على project_id
• الحالة: READY WITH FIXES — الكود شغال لكن محتاج تحسينات
• الأولوية: Fix 3 High + حل مشكلة "نفس الحساب"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 AGENT CONTRIBUTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🐛 مراجع أخطاء       → 3 findings | أهمهم: F-002 (no rotation)
  🔍 محقق أخطاء عميق   → 2 findings | Root: ownership lock behavior
  📊 محلل جودة         → 2 findings | Code duplication in picker logic
  🔒 مهندس أمان        → 2 findings | Cookies في json بدون تشفير
  🛡️ مراجع الكود       → 1 findings | history exposure in recovery
  🌐 محلل API Flow     → 2 findings | force:true + 204 handling
  ⚙️ مهندس Backend     → 1 findings | load_accounts() يتعمل مرتين
  🔎 فاحص بأدلة        → 1 findings | cooldown logic edge case

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟠 HIGH FINDINGS (3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ⚠️ #F-001 — نفس الحساب دايماً = مش rotation حقيقي
  ┌──────────────────────────────────────────────────────────┐
  │ 📍 Evidence:   pick_best_project يختار أول حساب صاحب   │
  │               project — حتى لو رصيده 50 وفيه 100       │
  │ 🔍 Root Cause: locked_email = first match (sorted)       │
  │               مش best match بين كل الـ candidates       │
  │ ⚡ Impact:     نفس الحساب يبعت → رصيده يخلص بسرعة       │
  │ 👥 Confirmed:  5/8 agents (HIGH confidence ✅)          │
  │ 💊 Fix:        Find ALL accounts with projects → sort    │
  │               by balance → pick HIGHEST balance owner    │
  │ 🧪 Test:       2 accounts own projects → highest wins    │
  │ 📅 Priority:   THIS SPRINT                              │
  └──────────────────────────────────────────────────────────┘

  ⚠️ #F-002 — load_accounts() مرتين في نفس الـ flow
  ┌──────────────────────────────────────────────────────────┐
  │ 📍 Evidence:   سطر 1893: load_accounts(cfg) مرة         │
  │               سطر 1961: load_accounts(cfg) مرة تانية    │
  │ 🔍 Root Cause: عدم تمرير accounts للـ outer scope        │
  │ ⚡ Impact:     I/O overhead + race condition لو الملف    │
  │               اتغير بين القرءتين                         │
  │ 👥 Confirmed:  3/8 agents (HIGH confidence ✅)          │
  │ 💊 Fix:        حمّل accounts مرة واحدة قبل الـ if/elif  │
  │ 📅 Priority:   THIS SPRINT                              │
  └──────────────────────────────────────────────────────────┘

  ⚠️ #F-003 — cookies محفوظة plain text في JSON
  ┌──────────────────────────────────────────────────────────┐
  │ 📍 Evidence:   accounts_genspark.json → "cookies": {...} │
  │ 🔍 Root Cause: مفيش encryption layer                     │
  │ ⚡ Impact:     أي شخص يفتح الملف يقدر يسرق الـ sessions  │
  │ 👥 Confirmed:  2/8 agents (MEDIUM confidence ⚠️)        │
  │ 💊 Fix:        Base64 أو keyring لتشفير الـ cookies       │
  │ 📅 Priority:   THIS SPRINT (لو shared environment)       │
  └──────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 MEDIUM FINDINGS (4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  💛 #F-004 — force:true بيتبعت حتى لو project جديد
  ┌──────────────────────────────────────────────────────────┐
  │ 📍 Evidence:   سطر ~1007: _is_continue = bool(project_id)│
  │               force:true لو project_id موجود             │
  │ 🔍 Note:      بعد auto-recovery → project_id=None        │
  │               → force: False ✅ (اتصلح تلقائياً)        │
  │ 📅 Priority:   MONITOR                                   │
  └──────────────────────────────────────────────────────────┘

  💛 #F-005 — history في recovery قد تحتوي owner messages
  ┌──────────────────────────────────────────────────────────┐
  │ 📍 Evidence:   history بتتحفظ عند recovery              │
  │               لكن لو الـ project الجديد = حساب مختلف    │
  │               → الـ history فيها messages من الـ owner   │
  │ 💊 Fix:       مش مشكلة فعلية — Genspark بيقرأ history    │
  │               بس كـ context مش كـ ownership proof        │
  │ 📅 Priority:   MONITOR                                   │
  └──────────────────────────────────────────────────────────┘

  💛 #F-006 — cooldown 29h يأثر على pick_best_project
  ┌──────────────────────────────────────────────────────────┐
  │ 📍 Evidence:   pick_best_project مش بتشيك الـ cooldown   │
  │               لكن pick_account بتشيكه                    │
  │ ⚡ Impact:     يمكن تختار owner لكن هو في cooldown        │
  │               → زودة في الـ balance deduction            │
  │ 💊 Fix:       sync cooldown check مع owner selection     │
  │ 📅 Priority:   THIS SPRINT                              │
  └──────────────────────────────────────────────────────────┘

  💛 #F-007 — الـ locked_email مش بيتتحول لـ active_email
  ┌──────────────────────────────────────────────────────────┐
  │ 📍 Evidence:   lock_email يتحدد → acc يتحدد             │
  │               لكن run_once loop بيستخدم active_email     │
  │               اللي اتحدد من pick_account                 │
  │ 💊 Fix:       sync active_email من locked_email          │
  │ 📅 Priority:   THIS SPRINT                              │
  └──────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 LOW FINDINGS (2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💚 #F-008 — URL list تحفظ آخر 10 روابط فقط
             الـ owner_email للـ projects الأقدم بيتمسح
             → قد تضيع معلومات rotation تاريخية
             Priority: IGNORE (10 كافي للاستخدام اليومي)

  💚 #F-009 — مفيش retry delay بين المحاولات
             بعد 500 البقية بتيجي فوراً
             Priority: MONITOR

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧩 ROOT CAUSE CLUSTERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔴 Cluster: Ownership Lock (Design Decision)
  ├─ F-001: نفس الحساب دايماً [5 agents]
  └─ F-006: Cooldown conflict مع owner selection [2 agents]

  🟠 Cluster: Code Efficiency
  ├─ F-002: double load_accounts() [3 agents]
  └─ F-007: locked_email ≠ active_email sync [2 agents]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ CONFLICTS RESOLVED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚡ F-005 (history في recovery):
    🛡️ مراجع الكود: "خطر — data leak"
    🌐 محلل API:   "مش مشكلة — Genspark يقبلها كـ context"
    ✅ القرار:     MONITOR فقط — مش تغيير [API behavior confirmed]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ PRIORITIZED ACTION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FIX NOW:        —  (مفيش Fatal!)
  THIS SPRINT:    F-001, F-002, F-006, F-007
  MONITOR:        F-004, F-005, F-009
  IGNORE:         F-008

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 FIX GUIDE: F-001 — Account Rotation الحقيقي
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
المشكلة: نفس الحساب صاحب كل الـ projects → دايماً يتاخد

الفهم الصح:
  Genspark projects = owner-locked
  → مفيش "rotation" على project موجود
  → الـ rotation بيحصل فقط لما بتعمل project جديد!

الحل: عند project جديد (project_id=None) → pick_account يختار
أعلى رصيد تلقائياً ✅ (شغال بالفعل!)

لو عايز rotation حقيقية:
  → زود max_retries مع cooldown per-account
  → كل project جديد → حساب مختلف تلقائياً بعد الـ cooldown

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏁 FINAL VERDICT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ READY WITH FIXES
  الكود شغال صح والـ continuation مثبت (3 runs متتالية).
  محتاج: F-001 explanation + F-002 + F-006 + F-007
  Confidence Score: 82/100
