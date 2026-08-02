# AIA-5 — تصنيف newskells ودورة حياة المهارات (Skills Lifecycle)

| البند | القيمة |
|---|---|
| المهمة | AIA-5 (CEV-G8.5 §4-B) |
| التاريخ | 2026-08-02 (Session 108) |
| النطاق | `newskells/` — 17 ملفًا، مهارتان: `codex-delegate`, `opencode-delegate` |
| المرجع الجرد | `AIA_INVENTORY.md` (كتل 208–224: كلها REFERENCE) |
| قاعدة حاكمة | **الترقية REFERENCE→ACTIVE = قرار مالك حصريًا** — أنا أُرشِّح وأُدلِّل فقط (بنود FI) |

---

## 1) دورة الحياة المعتمدة

```
REFERENCE ──(ترشيح مُدلَّل: بند FI)──▶ CANDIDATE ──(قرار مالك فقط)──▶ ACTIVE ──(أمر مالك)──▶ DEPRECATED
```

| الحالة | المعنى | من يقرر الانتقال |
|---|---|---|
| **REFERENCE** | مصدر إلهام موثَّق؛ غير محمَّل runtime؛ يبقى في المستودع كمرجع | الوضع الافتراضي |
| **CANDIDATE** | رُشِّح للترقية ببند FI مكتوب (منفعة/كلفة/متطلب/أفق) | المنفِّذ يُرشِّح فقط |
| **ACTIVE** | دخل `agents_rules/manifest.yaml` ويُحمَّل فعليًا | **مالك حصريًا** |
| **DEPRECATED** | مؤرشف بأمر مالك | **مالك حصريًا** |

**ملاحظة تفسيرية:** «ترقية» هنا قد تعني (أ) تحميل الملف نفسه، أو (ب) **اقتباس منهجيته في كود editor_v4** كما حدث سابقًا مع نمط Brief→Implement→Review→Land. الترشيحات أدناه كلها من النوع (ب) — لا يوجد أي ترشيح لتحميل ملف newskells نفسه runtime.

---

## 2) الواقع المُثبَت: غير محمَّلة runtime (تحقق حي)

```
$ grep -rn newskells --include="*.py" .   (خارج tests/ و.git/)
chain/delegate.py:6:    مستوحى من delegate-skills (newskells/)
chain/strategies.py:419:    مستوحى من delegate-skills (newskells/).
```
تعليقان توثيقيان فقط — **صفر import، صفر قراءة ملف، صفر تنفيذ**. لا ذكر في tests/ إطلاقًا.

---

## 3) بطاقتا المهارتين

### بطاقة 1 — `codex-delegate`

| الحقل | القيمة |
|---|---|
| **الاسم** | codex-delegate (`newskells/skills/codex-delegate/`, 6 ملفات) |
| **الغرض** | تفويض مهمة برمجية لـOpenAI Codex CLI كمنفِّذ خلفي: الـorchestrator يكتب brief مكتفيًا ذاتيًا → `relay.mjs` يشغّل `codex exec` ويكتب `result.json` → المراجعة والـcommit تبقى بيد الـorchestrator (SKILL.md:19–22) |
| **الحالة** | **REFERENCE** (ملفان منها مرشَّحان CANDIDATE — انظر الجدول §4 وبندي FI-13/FI-14) |
| **ما اقتُبس فعليًا (بالاستشهاد)** | (1) **الـloop الكامل** Brief→Implement→Review→Land → `chain/delegate.py:7` (`DelegateBridge`) و`chain/strategies.py:415–419` (`build_delegate`)، والمراحل الأربع مواقعها `chain/delegate.py:163–168` (`DelegatePhase: brief/implement/review/land`). (2) **مبدأ «العامل بلا سياق»** من `references/writing-the-brief.md:3–8` («no memory… only the text you send») → `chain/prompts/delegate_brief.md:5` («العامل يرى **فقط** ما تكتبه») وقاعدة «لا تفترض سياق» (سطر 9). (3) **بنية XML للـbrief** من `writing-the-brief.md:15–33` (`<task>/<verification_loop>`) → `delegate_brief.md:18–31` (`<task>/<files>/<verification>`). (4) **قائمة «ما يجب تركه» ضد التوسع** من `writing-the-brief.md:19–20` → `delegate_brief.md:11` («العامل يميل للتوسع، فحدد الحدود»). (5) **حكم المراجعة scope/creep** من `references/review-and-land.md` → `delegate_review.md:18–35` (APPROVE/REWORK/REJECT مع `no creep` و`scope creep`). (6) **التقرير المهيكل** من `writing-the-brief.md:37–40` (`structured_output_contract`) → `delegate_review.md:41–50` (`[VERDICT]/[SUMMARY]/[SCOPE_CHECK]/[RISKS]`) |
| **قيمة الترقية** | الملفان المتبقيان غير المقتبسين يحملان قيمة متفاوتة: `multi-task-queues.md` (انضباط الطوابير — غير موجود إطلاقًا: `grep -in queue chain/delegate.py chain/strategies.py` = صفر) و`review-and-land.md` §«Check the tests before trusting the gates» (حراس العبث بالاختبارات — غائبة عن معايير `delegate_review.md`). أما `relay.mjs`/`dispatch-and-poll.md` فقيمتهما منخفضة: تفويض عبر CLI خارجي يناقض تصميم editor_v4 (مزودون داخليون مباشرة — `delegate.py:9`: «بدون CLI خارجي») |
| **كلفة الترقية** | FI-13 (طوابير): متوسطة — حالة تسلسل + ترحيل قيود بين المهام في `DelegateBridge`. FI-14 (حراس الاختبارات): منخفضة — سطور معايير تُضاف لـ`delegate_review.md` + اختبار fencing. تحميل `relay.mjs` نفسه: مرتفعة ورافضة تصميميًا (Node runtime + CLI خارجي + مصادقة) |
| **المتطلب القبلي** | قرار مالك (بندا FI-13/FI-14)؛ ولـFI-13 تحديدًا: AIA-6 (router) مقفلة كي يكون توجيه المهام المتسلسلة حتميًا قابلًا للاختبار (P-11) |

### بطاقة 2 — `opencode-delegate`

| الحقل | القيمة |
|---|---|
| **الاسم** | opencode-delegate (`newskells/skills/opencode-delegate/`, 6 ملفات) |
| **الغرض** | نفس loop التفويض لكن المنفِّذ OpenCode CLI (SKILL.md:17–20)؛ الفارق الجوهري الوحيد: **اختيار موديل إلزامي** — «OpenCode has no safe default… the relay requires `--model` on every fresh run» والإنسان يملك قائمة الموديلات المسموحة (SKILL.md:44–50) |
| **الحالة** | **REFERENCE** (ملفان منها مرشَّحان CANDIDATE — توأمة محتوى مع codex-delegate؛ يغطيهما نفس بندي FI-13/FI-14) |
| **ما اقتُبس فعليًا (بالاستشهاد)** | نفس الاقتباسات الستة أعلاه — محتوى references/ متوأم بين المهارتين (فروق تخص CLI فقط). **الإضافة الفريدة غير المقتبسة**: مبدأ «الإنسان يملك أي الموديلات مسموحة» (SKILL.md:48–50) — editor_v4 يحقق مكافئه بنيويًا عبر إعداد المزود/الموديل في التهيئة، فلا فجوة فعلية |
| **قيمة الترقية** | مطابقة لبطاقة codex-delegate (التوأمة)؛ لا قيمة إضافية مستقلة سوى توثيق مبدأ اختيار الموديل، وهو محقَّق بالفعل |
| **كلفة الترقية** | مطابقة لبطاقة codex-delegate؛ بندا FI-13/FI-14 يغطيان التوأمين معًا (لا ازدواج بنود) |
| **المتطلب القبلي** | مطابق لبطاقة codex-delegate |

---

## 4) جدول 17/17 — حالة كل ملف

| # جرد | الملف | الحالة | التسويغ |
|---|---|---|---|
| 208 | `newskells/.gitignore` | REFERENCE | ميتاداتا حزمة؛ لا معنى لترقيتها |
| 209 | `newskells/AGENTS.md` | REFERENCE | دليل مساهمة للمستودع الأصلي (مفردات delegate/relay — AGENTS.md:10–15)؛ قيمة داخلية فقط |
| 210 | `newskells/LICENSE` | REFERENCE | MIT — يبقى وجوبًا ما دام المجلد محفوظًا |
| 211 | `newskells/README.md` | REFERENCE | وصف الحزمة والتثبيت عبر skills.sh؛ لا صلة بـruntime |
| 212 | `newskells/skills.sh.json` | REFERENCE | ميتاداتا فهرسة skills.sh |
| 213 | `codex-delegate/SKILL.md` | REFERENCE | جوهره (الـloop) مقتبس بالفعل — بطاقة 1 بند (1) |
| 214 | `codex-delegate/references/dispatch-and-poll.md` | REFERENCE | خاص بميكانيكا `codex exec`/binary على PATH — لا ينطبق على مزودي editor_v4 الداخليين |
| 215 | `codex-delegate/references/multi-task-queues.md` | **CANDIDATE** | انضباط الطوابير (تسلسل + commit لكل مهمة + ترحيل القيود — الأسطر 9–25) غير مقتبس؛ **بند FI-13** |
| 216 | `codex-delegate/references/review-and-land.md` | **CANDIDATE** | حراس العبث بالاختبارات (الأسطر 8–19: skips/loosened assertions) غائبة عن `delegate_review.md`؛ **بند FI-14** |
| 217 | `codex-delegate/references/writing-the-brief.md` | REFERENCE | مقتبس فعليًا — بطاقة 1 بنود (2)(3)(4)(6) |
| 218 | `codex-delegate/scripts/relay.mjs` | REFERENCE | dispatch عبر CLI خارجي (relay.mjs:5–10) يناقض `delegate.py:9` «بدون CLI خارجي» |
| 219 | `opencode-delegate/SKILL.md` | REFERENCE | توأم 213؛ مبدأ اختيار الموديل محقَّق بنيويًا |
| 220 | `opencode-delegate/references/dispatch-and-poll.md` | REFERENCE | توأم 214 (ميكانيكا `opencode run`) |
| 221 | `opencode-delegate/references/multi-task-queues.md` | **CANDIDATE** | توأم 215؛ يغطيه نفس **بند FI-13** |
| 222 | `opencode-delegate/references/review-and-land.md` | **CANDIDATE** | توأم 216؛ يغطيه نفس **بند FI-14** |
| 223 | `opencode-delegate/references/writing-the-brief.md` | REFERENCE | توأم 217 — مقتبس فعليًا |
| 224 | `opencode-delegate/scripts/relay.mjs` | REFERENCE | توأم 218 |

**المحصلة:** 17/17 لها بطاقة وحالة — 13 REFERENCE + 4 CANDIDATE (توأمان × بندا FI) + 0 ACTIVE + 0 DEPRECATED.

---

## 5) الترشيحات (قرار مالك — بنود FI مسجَّلة)

| ترشيح | الملفات | بند FI | الخلاصة |
|---|---|---|---|
| انضباط طوابير التفويض | 215 + 221 | **FI-13** | تسلسل + commit لكل مهمة + ترحيل القيود المقررة → توسيع `DelegateBridge` لطوابير متعددة المهام |
| حراس العبث بالاختبارات في المراجعة | 216 + 222 | **FI-14** | معايير صريحة في `delegate_review.md`: تعديل اختبارات غير مطلوب في الـbrief = REWORK/REJECT |

**بوابة الإغلاق (محققة):** 17/17 بطاقة وحالة ✅ | بند FI لكل CANDIDATE ✅ (FI-13/FI-14 في `FUTURE_IMPROVEMENTS.md`) | صفر تحميل runtime جديد دون أمر مالك ✅ (لم يُلمس أي كود تحميل).
