# مواصفة بروتوكول إطارات WebSocket — WebDev AI Editor

> **TSK-701 (FI-11)** — توثيق العقد الضمني الكامل لإطارات WS بين الواجهة والخادم.
> وثيقة **وصفية** (توثّق السلوك القائم بايت-بايت) وليست تصميمية — صفر تغيير كود.
> جميع الاستشهادات مؤرخة: `file:line @ 9e053de (2026-07-30)`.

---

## 1. طبقة النقل

| البند | القيمة | الدليل |
|---|---|---|
| المسار | `GET /ws` (flask-sock) | server.py:1716 @ 9e053de |
| الترميز | إطار نصي واحد = كائن JSON واحد (UTF-8، `ensure_ascii=False` للصادر) | server.py:311 @ 9e053de |
| حلقة الاستقبال | `ws.receive()` → `json.loads` → `_handle_ws_message` | server.py:1694–1705 @ 9e053de |
| إطار وارد تالف (خادم) | أي استثناء في receive/parse → **كسر الحلقة** وتنظيف `sctx.close()` (NF-14 §16) | server.py:1697–1710 @ 9e053de |
| إطار وارد تالف (واجهة) | `WSBackoff.safeParseFrame`: JSON مشوّه أو ليس كائنًا → log + تجاهل، **لا** قطع اتصال (TSK-402/NF-11) | static/js/ws_backoff.js:60 + static/app.js:174–182 @ 9e053de |
| موقع الإرسال الأوحد (خادم) | `_WSAdapter._send` — كل إطار صادر يمر عبر bus الاتصال ثم هذا الموقع حصرًا (T-047/R-604، يفرضه check.sh بالـ grep) | server.py:285–314 @ 9e053de |
| فشل الإرسال (خادم) | WS مقفول/معطوب → ابتلاع مقصود (عقد T-047، NF-14 §3) | server.py:308–314 @ 9e053de |

## 2. قاعدة التوجيه ومعالجة النوع المجهول

### 2.1 خادم (وارد)

التوجيه نقي عبر `core.ws_router.dispatch(handlers, ctx, sctx, msg)`:

- المفتاح = `msg.get("type", "")`؛ توقيع المقبض `handler(ctx, sctx, msg)`.
- **نوع غير معروف = لا شيء يحدث (no-op صامت)** — سلوك السلسلة الأصلية بلا `else`.
- الدليل: core/ws_router.py:23–34 + server.py:1678–1688 @ 9e053de.

### 2.2 واجهة (وارد)

`handleWSMessage(data)` → `switch (data.type)` **بلا `default`**:

- **نوع غير معروف = تجاهل صامت** (بعد مرور الإطار على مستهلكي الرصد
  StatusChip/SessionNarrative اللذين لا يغيّران مساره).
- الدليل: static/app.js:192–203 (بلا default حتى نهاية الـ switch) @ 9e053de.

> **التماثل**: الاتجاهان يطبقان نفس السياسة — إطار بنوع مجهول لا يكسر شيئًا.

## 3. إطارات الواجهة → الخادم (Client → Server)

المصدر الحاكم: جدول `WS_HANDLERS` (25 مفتاحًا) @ server.py:1649–1675 @ 9e053de.
الحقول = ما يقرؤه المقبض فعليًا من `msg` (استخراج آلي لكل `msg.get(...)` داخل جسم الدالة).

| النوع | المقبض @ سطر | الحقول المقروءة (كلها اختيارية بـ `.get`) | مرسل الواجهة |
|---|---|---|---|
| `ping` | `_ws_ping` :1122 | — | لا مرسل حاليًا |
| `agent_approval_response` | `_ws_agent_approval_response` :1130 | `approval_request_id`, `approved`, `payload_hash` | app.js:805 |
| `cancel_agent` | `_ws_cancel_agent` :1142 | — | لا مرسل حاليًا |
| `confirm_path_action` | `_ws_confirm_path_action` :1150 | `action`, `request_id` | app.js:3432 |
| `chain_approval_response` | `_ws_chain_approval_response` :1217 | `approved`, `payload_hash`, `request_id` | diff_panel.js:196 (`decisionFrame`) عبر app.js:1758 |
| `rollback_run` | `_ws_rollback` :1232 | `run_id` (+ `type` للتمييز) | run_history.js:133 عبر app.js:3543 |
| `rollback_file` | `_ws_rollback` :1232 | `run_id`, `path` (+ `type` للتمييز) | run_history.js:135 عبر app.js:3543 |
| `message` | `_ws_message` :1263 | `text`, `mode` | app.js:3190 |
| `apply_action` | `_ws_apply_action` :1275 | `action` (كائن إجراء — §5) | app.js:1348/1415/1422 |
| `apply_all_actions` | `_ws_apply_batch` :1282 | `actions` (مصفوفة كائنات إجراء) | لا مرسل حاليًا |
| `execute_plan` | `_ws_apply_batch` :1282 | `actions` | app.js:3402 |
| `chain_message` | `_ws_chain_message` :1304 | `text`, `strategy`, `files`, `file_path`, `file_content`, `folder_path` | app.js:869 |
| `chain_cancel` | `_ws_chain_cancel` :1384 | `reason` | app.js:1186 |
| `chain_status` | `_ws_chain_status` :1403 | — | app.js (طلب حالة) |
| `resume_scan` | `_ws_resume_scan` :1413 | — | لا مرسل حاليًا |
| `resume_run` | `_ws_resume_run` :1424 | `run_id` | لا مرسل حاليًا |
| `discard_run` | `_ws_discard_run` :1454 | `run_id` | لا مرسل حاليًا |
| `list_runs` | `_ws_list_runs` :1472 | — | لا مرسل حاليًا |
| `cancel_run` | `_ws_cancel_run` :1477 | `run_id`, `reason` | لا مرسل حاليًا |
| `delegate_message` | `_ws_delegate_message` :1489 | `text` | لا مرسل حاليًا |
| `delegate_approve` | `_ws_delegate_approve` :1561 | — (الواجهة ترسل `request_id` أيضًا؛ المقبض لا يقرؤه) | app.js:3400 |
| `delegate_reject` | `_ws_delegate_reject` :1616 | `reason` (الواجهة ترسل `request_id` أيضًا) | app.js:3414 |
| `memory_list` | `_ws_memory_list` :1628 | — | memory_panel.js:137 عبر app.js:3578 |
| `memory_edit` | `_ws_memory_edit` :1634 | `entry_id`, `kind`, `text` | memory_panel.js:141 عبر app.js:3614 |
| `memory_delete` | `_ws_memory_delete` :1642 | `entry_id` | memory_panel.js:148 عبر app.js:3598 |

### 3.1 حالة خاصة موثقة: `stop`

الواجهة ترسل `{type: "stop", request_id}` عند إيقاف بث غير-chain
(static/app.js:1188 @ 9e053de) لكن **لا مقبض له في `WS_HANDLERS`** →
no-op صامت على الخادم (قاعدة §2.1). الواجهة تعوّض بمؤقت أمان 6 ثوانٍ
يعيد حالتها (app.js:1192). **عدم تماثل قائم ومحفوظ** — أي تغيير فيه
قرار منتج، ليس ضمن هذه الوثيقة التوثيقية.

### 3.2 أنواع مخدومة بلا مرسل واجهة حاليًا

`ping`, `cancel_agent`, `apply_all_actions`, `resume_scan`, `resume_run`,
`discard_run`, `list_runs`, `cancel_run`, `delegate_message` — قدرات خادم
قائمة (تغطيها الاختبارات) لا تستهلكها الواجهة الحالية. تبقى جزءًا من
العقد: أي عميل يرسلها يحصل على السلوك الموثّق.

## 4. إطارات الخادم → الواجهة (Server → Client)

كل إطار صادر شكله `{"type": <نوع>, ...حمولة}`. المصدر: `_frame_publisher`
يحوّل الإطار حرفيًا لحدث bus (`type` → `frame_type`، الباقي `payload`)
و`_WSAdapter` يعيد بناءه بايت-بايت (server.py:307–341 @ 9e053de).
إطارات الموافقة (`_APPROVAL_FRAME_TYPES` = `approval_request`,
`chain_approval_request`, `agent_approval_request` @ server.py:281)
تُنشر `ApprovalRequested`؛ البقية `StepProgress` — **بلا فرق على السلك**.

المجموع المرصود: **49 نوعًا** تصدرها الوحدات؛ الواجهة تستهلك **38** منها
(switch @ app.js:203)؛ **11** تصل وتُتجاهل صامتًا (§4.7)؛ **صفر** أنواع
تستهلكها الواجهة ولا يصدرها الخادم.

### 4.1 مجموعة البث الأساسي (المحادثة/الخطة/الإجراءات)

| النوع | مصدر(مصادر) الإصدار @ 9e053de | مستهلك واجهة؟ |
|---|---|---|
| `start` | chat_dispatch.py:322/444، server.py:1578 | ✅ |
| `chunk` | server.py:347/378/1581، agent_loop.py:184 | ✅ |
| `done` | chat_dispatch.py:373/381/411/502، server.py:1593/1607 | ✅ |
| `error` | 19 موقعًا (server.py:1180/1268/1308/… ، chat_dispatch.py:137/372/380/474) | ✅ |
| `warning` | chat_dispatch.py:112 | ✅ |
| `plan` | chat_dispatch.py:402/493 | ✅ |
| `pong` | server.py:1125 | ✅ |
| `busy` | server.py:439 | ❌ (§4.7) |
| `scan_start` | server.py:1098/1313 | ✅ |
| `folder_scanned` | server.py:1330 | ✅ |
| `project_switched` | server.py:1171، chat_dispatch.py:128 | ✅ |
| `path_detected_options` | chat_dispatch.py:149 | ✅ |
| `confirm_path_failed` | server.py:1155 | ✅ |
| `task_progress` | server.py:1758/1760 | ✅ |
| `action_result` | server.py:1279 | ✅ |
| `all_actions_done` | server.py:1767 | ✅ |

### 4.2 مجموعة دورة حياة الـ runs

| النوع | مصدر الإصدار | مستهلك واجهة؟ |
|---|---|---|
| `runs_list` | server.py:474 | ❌ |
| `resumable_runs` | server.py:1417/1421 | ❌ |
| `cancel_run_result` | server.py:487/494 | ❌ |
| `discard_result` | server.py:1463 | ❌ |
| `rollback_result` | server.py:1236/1242/1251/1259 | ✅ |

### 4.3 مجموعة `chain_*`

| النوع | مصدر الإصدار | مستهلك واجهة؟ |
|---|---|---|
| `chain_started` | bridge.py:86، chat_dispatch.py:223 | ✅ |
| `chain_step` | bridge.py:94/104/114/123 | ✅ |
| `chain_retry` | bridge.py:131 | ✅ |
| `chain_warning` | bridge.py:140 | ✅ |
| `chain_cancelled` | bridge.py:146 | ✅ |
| `chain_finished` | bridge.py:157 | ✅ |
| `chain_error` | bridge.py:167/320/442/450/459 | ❌ |
| `chain_resume_refused` | bridge.py:470 | ❌ |
| `chain_resumed` | bridge.py:483 | ❌ |
| `chain_actions_staged` | bridge.py:554 | ❌ |
| `chain_approval_request` | bridge.py:565 | ✅ |
| `chain_approval_verdict` | bridge.py:569 | ✅ |
| `chain_apply_result` | bridge.py:584 | ❌ |
| `chain_status` | server.py:1407/1409 (ردّ على طلب `chain_status` الوارد) | ✅ |
| `chain_cancel_result` | server.py:1395 | ✅ |

### 4.4 مجموعة `agent_*`

| النوع | مصدر الإصدار | مستهلك واجهة؟ |
|---|---|---|
| `agent_thinking` | agent_loop.py:139 | ✅ |
| `agent_step` | agent_loop.py:198/213/240/260/516/569/595 | ✅ |
| `agent_done` | agent_loop.py:164/292 | ✅ |

**تدفق موافقة الطرفية (run_command)**: لا يوجد إطار يُبث فعليًا بنوع
`agent_approval_request` — الطلب يصل كـ `agent_step` بحقل
`status: "awaiting_approval"` مع `approval_request_id`/`payload_hash`/
`expires_at` (agent_loop.py:513–526 @ 9e053de)، والواجهة تعرض بطاقة
الموافقة عليه (app.js:646–728) وترد بـ `agent_approval_response` (§3).
الاسمان `approval_request` (افتراضي `ApprovalRequested.frame_type` @
core/events.py:80) و`agent_approval_request` **محجوزان تصنيفيًا** في
`_APPROVAL_FRAME_TYPES` ولا يظهران على السلك حاليًا.

### 4.5 مجموعة `delegate_*`

تصدر من `chain/delegate.py` عبر `_emit(on_event, type, data)` (:643)
ويحوّلها `DelegateRunner._on_event` → `stream.emit` إطارًا بنفس الاسم
(runners/delegate.py:79–84 @ 9e053de).

| النوع | مصدر الإصدار (delegate.py) | مستهلك واجهة؟ |
|---|---|---|
| `delegate_started` | :433 | ✅ |
| `delegate_phase` | :447/453/466/472/485/491 | ✅ |
| `delegate_review` | :502/534 | ✅ |
| `delegate_rejected` | :544/551/558/629 | ✅ |
| `delegate_cancelled` | :566 | ❌ |
| `delegate_error` | :572 | ✅ |
| `delegate_landed` | :608 | ✅ |

### 4.6 مجموعة `memory_*` (ردود)

| النوع | مصدر الإصدار | مستهلك واجهة؟ |
|---|---|---|
| `memory_list_result` | server.py:524 | ✅ (app.js + memory_panel.js) |
| `memory_edit_result` | server.py:555 | ✅ |
| `memory_delete_result` | server.py:593 | ✅ |

### 4.7 أنواع تُبث ولا تستهلكها الواجهة (11)

`busy`, `runs_list`, `resumable_runs`, `cancel_run_result`,
`discard_result`, `chain_error`, `chain_resume_refused`, `chain_resumed`,
`chain_actions_staged`, `chain_apply_result`, `delegate_cancelled` —
تصل الواجهة وتسقط صامتة عبر قاعدة §2.2 (لا `default` في الـ switch).
بعضها ردود على أنواع §3.2 التي لا ترسلها الواجهة أصلًا (تناظر منطقي)،
وبعضها (`chain_error`, `delegate_cancelled`) **فجوة عرض قائمة** —
توثيقها هنا لا يغيّرها؛ معالجتها قرار منتج مستقل.

## 5. أنواع **ليست** إطارات WS (توضيح إزالة لبس)

| السلسلة | حقيقتها | الدليل |
|---|---|---|
| `create_file` / `edit_file` / `run_command` | أنواع **كائنات إجراء** داخل حقل `actions`/`action` في حمولات `plan`/`apply_action`/`execute_plan`/`chain_actions_staged` — مخطط حمولة وليست أنواع إطارات | chain/action_applier.py:164/171/178 @ 9e053de |
| `snapshot` / `seal` | أنواع **سجلات journal** في ملف checkpoints على القرص — لا علاقة لها بـ WS إطلاقًا | core/checkpoint.py:24/29/95/269 @ 9e053de |
| `ctx` / `add` / `del` | أنواع صفوف عرض diff داخلية في الواجهة فقط | static/js/diff_panel.js:113–143 @ 9e053de |
| `approve_all`/`reject_all`/`confirm`/`toggle_file`/`toggle_mode`/`focus_file` | سلاسل `data-action` لعناصر UI — ليست إطارات | static/js (مسح TSK-701) |

### 5.1 مخطط كائن الإجراء (الحمولة المشتركة)

```
{"type": "create_file", "path": str, "content": str, "language": str}
{"type": "edit_file",   "path": str, "old_text": str, "new_text": str}
{"type": "run_command", "command": str}
```
الدليل: chain/action_applier.py:162–180 @ 9e053de.

## 6. تحقق مزدوج الاتجاه (Close-out TSK-701)

نُفّذ @ 9e053de (2026-07-30):

1. **C2S المواصفة→الكود**: كل الأنواع الـ 25 في §3 موجودة مفاتيح في
   `WS_HANDLERS` (server.py:1649–1675). ✓
2. **C2S الكود→المواصفة**: `grep 'type: ' static/**.js` بعد استبعاد
   أنواع §5 = 16 نوعًا مرسلًا؛ 15 منها في §3 + `stop` موثق §3.1. ✓
3. **S2C المواصفة→الكود**: كل نوع في §4 له سطر إصدار مذكور، وكلها
   تحققت بـ `grep '"type": "<اسم>"'` في وحدته. ✓
4. **S2C الكود→المواصفة**: مسح `grep -rn '"type": "' server.py core/
   chain/ runners/` (باستثناء الاختبارات وcheckpoint.py) = 49 نوع إطار،
   كلها في §4؛ الفائض المرصود كله مصنّف §5. ✓
5. **استهلاك الواجهة**: 38 حالة `case` في switch الواجهة — كلها في §4
   بعلامة ✅؛ صفر حالة بلا مصدر إصدار خادمي. ✓
