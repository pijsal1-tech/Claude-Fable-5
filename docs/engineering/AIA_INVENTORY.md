# AIA_INVENTORY — جرد أصول طبقة الذكاء (AIA-1)

> **الجلسة:** S108 | **الشجرة:** cd7260f | **المولِّد:** تقاطع برمجي
> manifest.yaml × rglob (لا تصنيف يدوي بلا دليل).
> **القاعدة الحاكمة:** AIA-R7 — لا أصل بلا تصنيف؛ الأرشفة/الحذف
> **قرار مالك حصري** (نمط EOP-1). هذا السجل لا يحذف شيئًا.

## المنهجية
- **ACTIVE** = يصل إليه مسار التشغيل الحي بدليل كود:
  manifest.yaml (21 دورًا / 20 ملفًا فريدًا — «أنت محلل جودة.md»
  مشترك بين code_analyzer وquality_reviewer) يستهلكه
  chain/agent_loader.py:97-98؛ chain/prompts/base_*.md fallback
  (agent_loader.py:99)؛ delegate_brief/review.md
  (chain/delegate.py:228-229)؛ prompts/web_system.md + templates.py
  (templates.py:13-16,51 — يشمل INJECTION_GUARD_INSTRUCTION خط NF-18).
- **REFERENCE** = newskells/ كاملة: مثبت حيًا أنها غير محمَّلة runtime
  (grep -r newskells *.py = تعليقان فقط: chain/delegate.py:6،
  chain/strategies.py:419 «مستوحى من»). بطاقات دورة الحياة = AIA-5:
  **مقفلة** — انظر `AIA_SKILLS_LIFECYCLE.md` (17/17 بطاقة؛ 4 ملفات
  رُقّيت لحالة CANDIDATE ببندي FI-13/FI-14 — الترقية قرار مالك).
- **STALE** = غير مستهلَك + أدلة إرث مشاريع سابقة في الرؤوس:
  «AI_PROVIDERS / C__cursor» (memory/PROJECT_VISION.md:1،
  skills/00-SKILLS.md:1، AGENT.md:2، سيستم/USER_PROFILE.md:2)،
  «AI_MDULE» (GEMINI.md:1)، «.agents عام لكل المشاريع» (AGENTS.md:2،
  tools/vibe_bridge.py:4)، أو برومبتات أدوار غير مسجلة بالمانيفست
  (مرشّحة تسجيل/أرشفة — قرار مالك).
- **DUMP** = نفايات ميكانيكية: نسخ .bak (×2)، .resolved (×1)،
  لصق محادثات («سيستم/تشغيل ملف» = خرج تثبيت CrewAI،
  «سيستم/من جينيص» = روابط منسوخة).

## الأرقام
| النطاق | إجمالي | ACTIVE | REFERENCE | STALE | DUMP |
|---|---|---|---|---|---|
| agents_rules | 201 | 21 | 0 | 175 | 5 |
| prompts | 2 | 2 | 0 | 0 | 0 |
| chain/prompts | 6 | 6 | 0 | 0 | 0 |
| newskells | 17 | 0 | 17 | 0 | 0 |
| **الكل** | **226** | **29** | **17** | **175** | **5** |

## قِسمة STALE حسب المنشأ (أدلة الرؤوس)
| كتلة | عدد | الدليل | التوصية (قرار مالك) |
|---|---|---|---|
| memory/ | 31 | PROJECT_VISION.md:1 «AI_PROVIDERS / C__cursor» + سجلات جلسات مشروع آخر | أرشفة خارج الشجرة |
| skills/ (كل الفروع) | 72 | 00-SKILLS.md:1 «AI_PROVIDERS»؛ skills/skills = 26 ملف debug مزوّدين (you.com/mistral/perplexity…) | أرشفة |
| workflows/ | 15 | add-provider/debug-provider/new-provider = onboarding مزوّدين للمشروع القديم | أرشفة |
| rules/ | 15 | قواعد vibe-coding عامة للمشروع القديم | أرشفة أو دمج انتقائي بقرار مالك |
| tools/ | 3 | vibe_bridge.py:4 «.agents/tools» — غير مستورَد في أي .py بالمشروع (grep = صفر) | أرشفة |
| وثائق الجذر ×7 | 7 | AGENT.md (AI_PROVIDERS)، GEMINI.md 135KB (AI_MDULE)، AGENTS.md 46KB (.agents)، ANTIGRAVITY_SESSION_STARTER، HELP، EXAMPLES، SYSTEM_README | أرشفة |
| برومبتات أدوار غير مسجلة | 32 | سيستم ×14 غير مسجل (خبير Burp/v2/المحرك/حماية، كاتب برومبت/تقني، مختبر API، مراقب، مفتش التوافق، منسق المشاريع، PLANNING_*/USER_PROFILE/PROMPT_ENGINE_PRO)، هندسة-تطبيقات ×4 (Blockchain/DevOps/SRE/بيانات)، تسويق ×4، تصميم ×3، بحث ×2، تخطيط ×1، تطوير-ألعاب ×2، بناء ×1، اراء ×1 (تاسك = برومبت Spec-Kit) | تسجيل بالمانيفست **أو** أرشفة — لكل ملف قرار مالك (AIA-R9 لاحقًا) |

> ملاحظة تقاطع: مجلدات skills/<role>/SKILL.md (قوالب «vibe» شخصيات)
> تكرر وظيفيًا أدوار المانيفست بصياغة أقدم — ليست المصدر الحي.

## ملحق: التصنيف الكامل ملفًا-ملفًا (صفر غير مصنَّف)
| # | الملف | التصنيف |
|---|---|---|
| 1 | `agents_rules/AGENT.md` | STALE |
| 2 | `agents_rules/AGENTS.md` | STALE |
| 3 | `agents_rules/ANTIGRAVITY_SESSION_STARTER.md` | STALE |
| 4 | `agents_rules/EXAMPLES.md` | STALE |
| 5 | `agents_rules/GEMINI.md` | STALE |
| 6 | `agents_rules/HELP.md` | STALE |
| 7 | `agents_rules/MICRO_WORKER_SYSTEM_PROMPT.md` | ACTIVE |
| 8 | `agents_rules/SYSTEM_README.md` | STALE |
| 9 | `agents_rules/manifest.yaml` | ACTIVE |
| 10 | `agents_rules/memory/00-EXAMPLES.md` | STALE |
| 11 | `agents_rules/memory/AGENT_RULES.md` | STALE |
| 12 | `agents_rules/memory/AGENT_SYNC.md` | STALE |
| 13 | `agents_rules/memory/AUTO_APMS_SYNC_RULES.md` | STALE |
| 14 | `agents_rules/memory/CHANGELOG_DECISIONS.md` | STALE |
| 15 | `agents_rules/memory/CHATGAI_POST_MORTEM.md` | STALE |
| 16 | `agents_rules/memory/CODE_QUALITY_KEYWORDS.md` | STALE |
| 17 | `agents_rules/memory/DOMAIN_NOTES.md` | STALE |
| 18 | `agents_rules/memory/HANDOVER_COLAB.md` | STALE |
| 19 | `agents_rules/memory/LOG.md` | STALE |
| 20 | `agents_rules/memory/PROJECT_VISION.md` | STALE |
| 21 | `agents_rules/memory/README.md` | STALE |
| 22 | `agents_rules/memory/SYNC_DESK.md` | STALE |
| 23 | `agents_rules/memory/WAF_BOT_DIAGNOSTIC_MASTER_PROMPT.md` | STALE |
| 24 | `agents_rules/memory/ai_state.json` | STALE |
| 25 | `agents_rules/memory/automation_patterns.md` | STALE |
| 26 | `agents_rules/memory/decisions_log.md` | STALE |
| 27 | `agents_rules/memory/genspark_500_error_fix.md` | STALE |
| 28 | `agents_rules/memory/genspark_chat_lessons.md` | STALE |
| 29 | `agents_rules/memory/genspark_continue_conv_fix.md` | STALE |
| 30 | `agents_rules/memory/genspark_fusion_report.md` | STALE |
| 31 | `agents_rules/memory/genspark_problems_solutions.md` | STALE |
| 32 | `agents_rules/memory/handoff_templates.md` | STALE |
| 33 | `agents_rules/memory/planning_prompt_master.md` | STALE |
| 34 | `agents_rules/memory/project-assumptions.md` | STALE |
| 35 | `agents_rules/memory/promptcowboy_knowledge.md` | STALE |
| 36 | `agents_rules/memory/provider_knowledge.md` | STALE |
| 37 | `agents_rules/memory/sessions/handshake_b.txt` | STALE |
| 38 | `agents_rules/memory/style_prefs.md` | STALE |
| 39 | `agents_rules/memory/vibe_5whys_chaos_guide.md` | STALE |
| 40 | `agents_rules/memory/أنت مفتش التوافق.md` | STALE |
| 41 | `agents_rules/rules/00-RULES.md` | STALE |
| 42 | `agents_rules/rules/00-project-vision.md` | STALE |
| 43 | `agents_rules/rules/01-double-check.md` | STALE |
| 44 | `agents_rules/rules/01-double-review.md` | STALE |
| 45 | `agents_rules/rules/01-user-context.md` | STALE |
| 46 | `agents_rules/rules/02-agents-index.md` | STALE |
| 47 | `agents_rules/rules/02-vibe-coding-mode-v3.md` | STALE |
| 48 | `agents_rules/rules/02-vibe-coding-mode.md` | STALE |
| 49 | `agents_rules/rules/03-vibe-coder-master-prompt.md` | STALE |
| 50 | `agents_rules/rules/04-naming-conventions.md` | STALE |
| 51 | `agents_rules/rules/REVIEW_CHECKLIST.md` | STALE |
| 52 | `agents_rules/rules/brainsyncory.md` | STALE |
| 53 | `agents_rules/rules/failure-policy.md` | STALE |
| 54 | `agents_rules/rules/scope-boundaries.md` | STALE |
| 55 | `agents_rules/rules/test-and-verify.md` | STALE |
| 56 | `agents_rules/skills/00-SKILLS.md` | STALE |
| 57 | `agents_rules/skills/00-evidence-inspector/SKILL.md` | STALE |
| 58 | `agents_rules/skills/00-provider-index.md` | STALE |
| 59 | `agents_rules/skills/01-logical-deduction.md` | STALE |
| 60 | `agents_rules/skills/01-micro-tasker/SKILL.md` | STALE |
| 61 | `agents_rules/skills/02-har-analysis.md` | STALE |
| 62 | `agents_rules/skills/02-planning-system/SKILL.md` | STALE |
| 63 | `agents_rules/skills/03-provider-checklist.md` | STALE |
| 64 | `agents_rules/skills/04-provider-requests.md` | STALE |
| 65 | `agents_rules/skills/05-provider-hybrid.md` | STALE |
| 66 | `agents_rules/skills/06-live-rules.md` | STALE |
| 67 | `agents_rules/skills/07-refresh-pattern.md` | STALE |
| 68 | `agents_rules/skills/24-prompt-engine.md` | STALE |
| 69 | `agents_rules/skills/api-analyzer/SKILL.md` | STALE |
| 70 | `agents_rules/skills/api-tester/SKILL.md` | STALE |
| 71 | `agents_rules/skills/architect/SKILL.md` | STALE |
| 72 | `agents_rules/skills/auto/config/SKILL.md` | STALE |
| 73 | `agents_rules/skills/auto/convention/SKILL.md` | STALE |
| 74 | `agents_rules/skills/auto/project/SKILL.md` | STALE |
| 75 | `agents_rules/skills/auto/python/SKILL.md` | STALE |
| 76 | `agents_rules/skills/auto/root-updater/SKILL.md` | STALE |
| 77 | `agents_rules/skills/auto/skills-manifest.json` | STALE |
| 78 | `agents_rules/skills/auto/tool-pattern/SKILL.md` | STALE |
| 79 | `agents_rules/skills/bug-reviewer/SKILL.md` | STALE |
| 80 | `agents_rules/skills/burp-expert/SKILL.md` | STALE |
| 81 | `agents_rules/skills/compatibility-reviewer/SKILL.md` | STALE |
| 82 | `agents_rules/skills/compliance-inspector/SKILL.md` | STALE |
| 83 | `agents_rules/skills/deep-debugger/SKILL.md` | STALE |
| 84 | `agents_rules/skills/engine-expert/SKILL.md` | STALE |
| 85 | `agents_rules/skills/expert-v2/SKILL.md` | STALE |
| 86 | `agents_rules/skills/micro-tasker/SKILL.md` | STALE |
| 87 | `agents_rules/skills/monitor-agent/SKILL.md` | STALE |
| 88 | `agents_rules/skills/orchestrator/SKILL.md` | STALE |
| 89 | `agents_rules/skills/performance-analyzer/SKILL.md` | STALE |
| 90 | `agents_rules/skills/planner/SKILL.md` | STALE |
| 91 | `agents_rules/skills/project-coordinator/SKILL.md` | STALE |
| 92 | `agents_rules/skills/prompt-writer/SKILL.md` | STALE |
| 93 | `agents_rules/skills/protection-expert/SKILL.md` | STALE |
| 94 | `agents_rules/skills/quality-analyzer/SKILL.md` | STALE |
| 95 | `agents_rules/skills/quality-guard/SKILL.md` | STALE |
| 96 | `agents_rules/skills/request-analyzer/SKILL.md` | STALE |
| 97 | `agents_rules/skills/review-manager/SKILL.md` | STALE |
| 98 | `agents_rules/skills/security-engineer/SKILL.md` | STALE |
| 99 | `agents_rules/skills/skills/00-INDEX.md` | STALE |
| 100 | `agents_rules/skills/skills/01-new-provider-checklist.md` | STALE |
| 101 | `agents_rules/skills/skills/02-requests-level1.md` | STALE |
| 102 | `agents_rules/skills/skills/03-hybrid-level2.md` | STALE |
| 103 | `agents_rules/skills/skills/04-code-patterns.md` | STALE |
| 104 | `agents_rules/skills/skills/05-email-providers.md` | STALE |
| 105 | `agents_rules/skills/skills/06-terminal-output.md` | STALE |
| 106 | `agents_rules/skills/skills/07-after-task.md` | STALE |
| 107 | `agents_rules/skills/skills/08-debug-you-com.md` | STALE |
| 108 | `agents_rules/skills/skills/09-debug-mistral.md` | STALE |
| 109 | `agents_rules/skills/skills/10-debug-perplexity.md` | STALE |
| 110 | `agents_rules/skills/skills/11-debug-deepseek.md` | STALE |
| 111 | `agents_rules/skills/skills/12-debug-genspark-uncensored.md` | STALE |
| 112 | `agents_rules/skills/skills/13-anti-patterns.md` | STALE |
| 113 | `agents_rules/skills/skills/14-doc-template.md` | STALE |
| 114 | `agents_rules/skills/skills/15-live-rules-full.md` | STALE |
| 115 | `agents_rules/skills/skills/16-input-formats.md` | STALE |
| 116 | `agents_rules/skills/skills/17-philosophy.md` | STALE |
| 117 | `agents_rules/skills/skills/18-advanced-lessons.md` | STALE |
| 118 | `agents_rules/skills/skills/19-debug-ernie-grok.md` | STALE |
| 119 | `agents_rules/skills/skills/20-debug-arena-cohere-zo-ai21.md` | STALE |
| 120 | `agents_rules/skills/skills/21-captcha-solving.md` | STALE |
| 121 | `agents_rules/skills/skills/22-shared-monitor.md` | STALE |
| 122 | `agents_rules/skills/skills/23-chat-template.md` | STALE |
| 123 | `agents_rules/skills/skills/23-debug-cursor.md` | STALE |
| 124 | `agents_rules/skills/skills/SKILL.md` | STALE |
| 125 | `agents_rules/skills/team-manager/SKILL.md` | STALE |
| 126 | `agents_rules/skills/tech-writer/SKILL.md` | STALE |
| 127 | `agents_rules/skills/vibe-reviewer/SKILL.md` | STALE |
| 128 | `agents_rules/tools/factory_rules.yaml` | STALE |
| 129 | `agents_rules/tools/init_root.py` | STALE |
| 130 | `agents_rules/tools/vibe_bridge.py` | STALE |
| 131 | `agents_rules/workflows/00-CODE_QUALITY_KEYWORDS.md` | STALE |
| 132 | `agents_rules/workflows/00-ask-council.md` | STALE |
| 133 | `agents_rules/workflows/00-micro-tasking.md` | STALE |
| 134 | `agents_rules/workflows/00-planning.md` | STALE |
| 135 | `agents_rules/workflows/00-sequential-requests.md` | STALE |
| 136 | `agents_rules/workflows/00-speckit.md` | STALE |
| 137 | `agents_rules/workflows/00-vibe_5whys_chaos_guide.md` | STALE |
| 138 | `agents_rules/workflows/activate.md` | STALE |
| 139 | `agents_rules/workflows/add-chat.md` | STALE |
| 140 | `agents_rules/workflows/add-provider.md` | STALE |
| 141 | `agents_rules/workflows/add-refresh.md` | STALE |
| 142 | `agents_rules/workflows/add-to-monitor.md` | STALE |
| 143 | `agents_rules/workflows/debug-provider.md` | STALE |
| 144 | `agents_rules/workflows/new-provider.md` | STALE |
| 145 | `agents_rules/workflows/update-docs.md` | STALE |
| 146 | `agents_rules/اراء/تاسك` | STALE |
| 147 | `agents_rules/بحث/أنت باحث أكاديمي.md` | STALE |
| 148 | `agents_rules/بحث/أنت باحث بيانات.md` | STALE |
| 149 | `agents_rules/بناء/أنت بناء MCP Server.md` | STALE |
| 150 | `agents_rules/تخطيط/أنت مخطط احترافي شامل.md` | STALE |
| 151 | `agents_rules/تخطيط/أنت مخطط احترافي شامل.md.bak` | DUMP |
| 152 | `agents_rules/تسويق/أنت استراتيجي المبيعات.md` | STALE |
| 153 | `agents_rules/تسويق/أنت باحث السوق.md` | STALE |
| 154 | `agents_rules/تسويق/أنت خبير نمو.md` | STALE |
| 155 | `agents_rules/تسويق/أنت صانع محتوى.md` | STALE |
| 156 | `agents_rules/تصميم/أنت باحث UX.md` | STALE |
| 157 | `agents_rules/تصميم/أنت كاتب برومبتات صور.md` | STALE |
| 158 | `agents_rules/تصميم/أنت مصمم واجهات.md` | STALE |
| 159 | `agents_rules/تطوير-ألعاب/أنت مصمم ألعاب.md` | STALE |
| 160 | `agents_rules/تطوير-ألعاب/أنت مطور Unity.md` | STALE |
| 161 | `agents_rules/سيستم/PLANNING_TEMPLATES.md` | STALE |
| 162 | `agents_rules/سيستم/PLANNING_TRACKER.md` | STALE |
| 163 | `agents_rules/سيستم/PROMPT_ENGINE_PRO.md` | STALE |
| 164 | `agents_rules/سيستم/PROMPT_ENGINE_PRO.md.bak` | DUMP |
| 165 | `agents_rules/سيستم/USER_PROFILE.md` | STALE |
| 166 | `agents_rules/سيستم/implementation_plan.md.resolved` | DUMP |
| 167 | `agents_rules/سيستم/أنت حارس الجودة.md` | ACTIVE |
| 168 | `agents_rules/سيستم/أنت خبير Burp.md` | STALE |
| 169 | `agents_rules/سيستم/أنت خبير v2.md` | STALE |
| 170 | `agents_rules/سيستم/أنت خبير المحرك.md` | STALE |
| 171 | `agents_rules/سيستم/أنت خبير حماية.md` | STALE |
| 172 | `agents_rules/سيستم/أنت فاحص بأدلة.md` | ACTIVE |
| 173 | `agents_rules/سيستم/أنت كاتب برومبت.md` | STALE |
| 174 | `agents_rules/سيستم/أنت كاتب تقني.md` | STALE |
| 175 | `agents_rules/سيستم/أنت محقق أخطاء عميق.md` | ACTIVE |
| 176 | `agents_rules/سيستم/أنت محلل API Flow.md` | ACTIVE |
| 177 | `agents_rules/سيستم/أنت محلل أداء.md` | ACTIVE |
| 178 | `agents_rules/سيستم/أنت محلل جودة.md` | ACTIVE |
| 179 | `agents_rules/سيستم/أنت محلل طلبات.md` | ACTIVE |
| 180 | `agents_rules/سيستم/أنت مختبر API.md` | STALE |
| 181 | `agents_rules/سيستم/أنت مخطط.md` | ACTIVE |
| 182 | `agents_rules/سيستم/أنت مدير الأوركسترا.md` | ACTIVE |
| 183 | `agents_rules/سيستم/أنت مدير المراجعة.md` | ACTIVE |
| 184 | `agents_rules/سيستم/أنت مدير فريق.md` | ACTIVE |
| 185 | `agents_rules/سيستم/أنت مراجع Vibe.md` | ACTIVE |
| 186 | `agents_rules/سيستم/أنت مراجع أخطاء.md` | ACTIVE |
| 187 | `agents_rules/سيستم/أنت مراجع توافق.md` | ACTIVE |
| 188 | `agents_rules/سيستم/أنت مراقب.md` | STALE |
| 189 | `agents_rules/سيستم/أنت مفتش التوافق.md` | STALE |
| 190 | `agents_rules/سيستم/أنت منسق المشاريع.md` | STALE |
| 191 | `agents_rules/سيستم/أنت مهندس أمان.md` | ACTIVE |
| 192 | `agents_rules/سيستم/أنت مهندس معماري.md` | ACTIVE |
| 193 | `agents_rules/سيستم/تشغيل ملف` | DUMP |
| 194 | `agents_rules/سيستم/من جينيص` | DUMP |
| 195 | `agents_rules/هندسة-تطبيقات/أنت مراجع الكود الآمن.md` | ACTIVE |
| 196 | `agents_rules/هندسة-تطبيقات/أنت مطور Blockchain.md` | STALE |
| 197 | `agents_rules/هندسة-تطبيقات/أنت مطور Frontend.md` | ACTIVE |
| 198 | `agents_rules/هندسة-تطبيقات/أنت مهندس Backend.md` | ACTIVE |
| 199 | `agents_rules/هندسة-تطبيقات/أنت مهندس DevOps.md` | STALE |
| 200 | `agents_rules/هندسة-تطبيقات/أنت مهندس SRE.md` | STALE |
| 201 | `agents_rules/هندسة-تطبيقات/أنت مهندس بيانات.md` | STALE |
| 202 | `chain/prompts/base_analyze.md` | ACTIVE |
| 203 | `chain/prompts/base_execute.md` | ACTIVE |
| 204 | `chain/prompts/base_plan.md` | ACTIVE |
| 205 | `chain/prompts/base_review.md` | ACTIVE |
| 206 | `chain/prompts/delegate_brief.md` | ACTIVE |
| 207 | `chain/prompts/delegate_review.md` | ACTIVE |
| 208 | `newskells/.gitignore` | REFERENCE |
| 209 | `newskells/AGENTS.md` | REFERENCE |
| 210 | `newskells/LICENSE` | REFERENCE |
| 211 | `newskells/README.md` | REFERENCE |
| 212 | `newskells/skills.sh.json` | REFERENCE |
| 213 | `newskells/skills/codex-delegate/SKILL.md` | REFERENCE |
| 214 | `newskells/skills/codex-delegate/references/dispatch-and-poll.md` | REFERENCE |
| 215 | `newskells/skills/codex-delegate/references/multi-task-queues.md` | REFERENCE |
| 216 | `newskells/skills/codex-delegate/references/review-and-land.md` | REFERENCE |
| 217 | `newskells/skills/codex-delegate/references/writing-the-brief.md` | REFERENCE |
| 218 | `newskells/skills/codex-delegate/scripts/relay.mjs` | REFERENCE |
| 219 | `newskells/skills/opencode-delegate/SKILL.md` | REFERENCE |
| 220 | `newskells/skills/opencode-delegate/references/dispatch-and-poll.md` | REFERENCE |
| 221 | `newskells/skills/opencode-delegate/references/multi-task-queues.md` | REFERENCE |
| 222 | `newskells/skills/opencode-delegate/references/review-and-land.md` | REFERENCE |
| 223 | `newskells/skills/opencode-delegate/references/writing-the-brief.md` | REFERENCE |
| 224 | `newskells/skills/opencode-delegate/scripts/relay.mjs` | REFERENCE |
| 225 | `prompts/templates.py` | ACTIVE |
| 226 | `prompts/web_system.md` | ACTIVE |
