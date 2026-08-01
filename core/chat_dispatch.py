"""TSK-612 (QG-02 §R8، ADR-002): مسار إرسال رسالة الشات — مستخرج من server.py.

المشكلة: `_dispatch_chat_message` كانت أكبر كتلة متبقية في g1
(server.py:1549..2034 — 486 سطرًا): كشف مسارات + جمع سياق + توجيه
(router/chain/delegate) + Agent + direct fallback — خارج بوابة mypy.

الحل (ADR-002): الجسم هنا حرفيًا؛ رموز server (RUNNERS، parser،
event_bus، `_begin_run_ticket`…) والقابلة للترقيع في الاختبارات
(gather_message_context) والمتغيّرة وقت التشغيل (request_router،
agent_tools) تصل عبر كائن ``deps`` يبنيه غلاف
`server._dispatch_chat_message` **وقت كل نداء** (late binding) —
فيبقى monkeypatch على فضاء server فعّالًا ولا دورة استيراد.

ملاحظة سلوكية: إطار ``scan_start`` الفوري (TSK-403/NF-12) يُرسله
الغلاف في server.py قبل النداء هنا — الفحص البنيوي
(test_scan_start.py) يثبّته هناك؛ صفر تغيير في ترتيب الإطارات.
"""
import os
import re
import threading
import time
import uuid

from chain.agent_loop import AgentLoop
from context.budget import CharsPerTokenEstimator
from core.events import RoutingDecided
# RP-04/TSK-626: كل مواقع بناء RunRequest في هذا الملف (chain/delegate/
# agent/direct) لا تمرر proposed_actions عمدًا — فرع الموافقة المسبقة في
# الـ runners test-only (تصونه عقود RunnerContractMixin) ولا يُحسب طبقة
# أمان فعلية؛ توصيله بمستهلك إنتاجي = قرار منتج لاحق. (تعليق مقابل عند
# موقع delegate في server.py.)
from core.runner import RESULT_COMPLETED, RESULT_FAILED, RunRequest
from core.strategy import RoutingTier
from prompts.templates import build_prompt, fence_attached, get_system_prompt
from providers.base import Message
from core.structured_log import swallowed as _slog_swallowed


# ── TSK-501: تصنيف قرابة مسار مكتشف بالمشروع المفتوح ──
# الكارت path_detected_options كان يُرفع لأي مجلد مكتشف بلا فحص
# قرابة: سحب ملف من نفس المشروع المفتوح أو ذكر مجلد أب (مثل D:\)
# كان يوقف الرسالة بسؤال بلا معنى (أو خطر: توسيع النطاق لدرايف
# كامل). السؤال مشروع فقط لمسار خارج شجرة المشروع تمامًا.
PATH_REL_SAME = "same"          # نفس جذر المشروع المفتوح
PATH_REL_INSIDE = "inside"      # مجلد ولد تحت المشروع
PATH_REL_ANCESTOR = "ancestor"  # مجلد أب للمشروع (مثل جذر الدرايف)
PATH_REL_OUTSIDE = "outside"    # خارج الشجرة — الوحيد الذي يستحق السؤال

# TSK-501 (عيب 3): الواجهة تدمج محتوى المرفقات الصريحة في نص
# الرسالة تحت هذا العنوان (10_chat_ws_stream.js) — كشف المسارات
# كان يمسح المحتوى المدموج كله (عشرات KB من كود قد يحوي
# "D:\\" حرفيًا) فيرفع كارت مسار زائفًا. المسح يقتصر الآن على
# ما قبل العلامة (كلام المستخدم نفسه فقط) — المرفق يُقرأ
# مباشرة كمحتوى، لا يُعاد البحث النصي داخله.
ATTACHMENTS_MARKER = "[📎 ملفات مرفقة]:"

# TSK-501 (عيب 2): نمط مسارات Windows — ثابت وحدة ليُفحص مباشرة
# في الاختبارات. الفاصل بعد النقطتين \\ أو / فقط (لا مسافة —
# النمط القديم كان يلتقط "D: كلام" مسارًا زائفًا)، والمقاطع تقبل
# مسافات مفردة داخل أسماء المجلدات (القديم كان يقطع عند أول
# مسافة: "D:\\My Projects\\app" ← "D:\\My").
WIN_PATH_RE = r'[A-Za-z]:[\\/](?:[^\s,;"\'<>|*?]+(?: [^\s,;"\'<>|*?]+)*)?'

# مسارات POSIX مطلقة (تبدأ بـ /) — نفس مبدأ المسافات المفردة؛
# فرع تقسيم الكلمات القديم كان يقطع عند المسافة بنفس الطريقة.
POSIX_PATH_RE = r'(?<![\w/])/(?:[^\s,;"\'<>|*?]+(?: [^\s,;"\'<>|*?]+)*)'


def iter_path_candidates(text: str):
    """TSK-501 (عيب 2): مرشحو مسارات (Windows + POSIX) من النص.

    المسافة مبهمة بطبعها: قد تكون داخل اسم مجلد ("My Projects")
    أو فاصلًا قبل كلام عادي ("D:\\app دلوقتي") — لا يحسمها regex.
    التصميم: مطابقة جشعة (تسمح بمسافات مفردة) ثم قصّ المقاطع
    المفصولة بمسافة من اليمين تدريجيًا — المستهلك يحسم بالقرص
    (isdir/isfile) ويأخذ أول مرشح موجود فعليًا (الأطول أولًا).
    """
    for pattern in (WIN_PATH_RE, POSIX_PATH_RE):
        for m in re.findall(pattern, text):
            m = m.strip().rstrip('.,;?)')
            if not m:
                continue
            parts = m.split(' ')
            for i in range(len(parts), 0, -1):
                cand = ' '.join(parts[:i]).rstrip('.,;?)')
                if cand:
                    yield cand


# توافق خلفي — الاسم الأول قبل تعميم POSIX.
iter_win_path_candidates = iter_path_candidates


def classify_path_relation(detected: str, project_root: str) -> str:
    """TSK-501: أين يقع ``detected`` بالنسبة لـ ``project_root``؟

    المقارنة بعد تطبيع مطلق + normcase (لا حساسية حالة على
    Windows — نفس مبدأ ProjectHandle.project_id). لا وصول للقرص.
    """
    d = os.path.normcase(os.path.normpath(os.path.abspath(detected)))
    r = os.path.normcase(os.path.normpath(os.path.abspath(project_root)))
    if d == r:
        return PATH_REL_SAME
    # حدود الفاصل — جذر نظام الملفات ("/" أو "D:\\") ينتهي بالفاصل
    # أصلًا — إلحاق os.sep أعمى كان ينتج "//" فيفلت الجذر من ancestor.
    d_pfx = d if d.endswith(os.sep) else d + os.sep
    r_pfx = r if r.endswith(os.sep) else r + os.sep
    if d.startswith(r_pfx):
        return PATH_REL_INSIDE
    if r.startswith(d_pfx):
        return PATH_REL_ANCESTOR
    return PATH_REL_OUTSIDE


def dispatch_chat_message(deps, ctx, sctx, user_text: str, mode: str, msg: dict, skip_path_detection: bool = False, attached_context: list | None = None):
    """إرسال ومعالجة رسالة الشات مع الـ AI (جمع السياق والتوجيه).

    TSK-103 (BUG-03): ``attached_context`` = قائمة ``(key, text)`` لمحتوى
    مرفق (مجلد attach من confirm_path_action) — يمر لـ
    gather_message_context ليُحزم تحت ContextBudget بدل الإلحاق الخام.
    ``deps``: مراجع server الحية (ADR-002) — انظر docstring الوحدة."""
    attached_context = list(attached_context) if attached_context else []
    # ── 1. كشف ذكي للمسارات (ملفات + مجلدات) ──
    import re
    detected_dir = None
    detected_file = None

    # TSK-501 (عيب 3): المسح على كلام المستخدم فقط — محتوى المرفقات
    # المدموج بعد العلامة خارج نطاق كشف المسارات (بيانات لا أوامر).
    scan_text = user_text.split(ATTACHMENTS_MARKER, 1)[0]

    # البحث عن مسارات بين علامات التنصيص
    quoted = re.findall(r'["\']([^"\']+)["\']', scan_text)
    for p in quoted:
        p_clean = p.strip()
        if os.path.isdir(p_clean):
            detected_dir = os.path.abspath(p_clean)
            break
        elif os.path.isfile(p_clean):
            detected_file = os.path.abspath(p_clean)
            break

    # البحث في الكلمات عن مسارات (مع دعم Windows backslash)
    if not detected_dir and not detected_file:
        # كشف مسارات Windows مثل D:\path\to\file
        # TSK-501 (عيب 2): النمط القديم [A-Za-z]:[\\/ ][^\s,;"'>]+ كان:
        #   أ) يقبل مسافة بعد النقطتين — فـ "D: كلام" يُلتقط مسارًا زائفًا؛
        #   ب) يقطع عند أول مسافة داخل المسار — "D:\My Projects\app"
        #      يصبح "D:\My" (غير موجود) ثم ينهار لـ "D:\" عبر فروع
        #      أخرى. الآن: الفاصل بعد النقطتين \\ أو / فقط، والمقاطع
        #      التالية تسمح بمسافات مفردة داخل أسماء المجلدات (لا
        #      مسافة في الذيل — نهاية المسار لا تكون مسافة).
        for wp in iter_path_candidates(scan_text):
            if os.path.isdir(wp):
                detected_dir = os.path.abspath(wp)
                break
            elif os.path.isfile(wp):
                detected_file = os.path.abspath(wp)
                break

    if not detected_dir and not detected_file:
        for w in scan_text.split():
            w_clean = w.strip('.,;?()[]{}"\'')
            if os.path.isdir(w_clean):
                detected_dir = os.path.abspath(w_clean)
                break
            elif os.path.isfile(w_clean):
                detected_file = os.path.abspath(w_clean)
                break

    if not detected_dir and not detected_file and os.path.isdir(scan_text.strip()):
        detected_dir = os.path.abspath(scan_text.strip())
    elif not detected_dir and not detected_file and os.path.isfile(scan_text.strip()):
        detected_file = os.path.abspath(scan_text.strip())

    # ── معالجة ملف مكتشف: قراءة محتواه وإرفاقه ──
    # TSK-103 (BUG-03): لا إلحاق خام في user_text — المحتوى يدخل
    # attached_context ليُحزم تحت ContextBudget في gather_message_context.
    if detected_file:
        try:
            with open(detected_file, 'r', encoding='utf-8', errors='replace') as df:
                file_content = df.read(deps.MAX_SMART_FILE_SIZE)
            file_ext = os.path.splitext(detected_file)[1]
            # TSK-404 (NF-18): المحتوى المكتشف يدخل البرومبت مسيّجًا
            # بأغلفة حدود صريحة — بيانات لا أوامر (تعليمة system).
            attached_context.append((
                f"detected_file:{detected_file}",
                fence_attached(
                    f"detected_file:{detected_file}",
                    f"[📄 محتوى الملف: {detected_file}]:\n```{file_ext.lstrip('.')}\n{file_content}\n```"),
            ))
        except Exception as e:
            # NF-14 §6 (TSK-305 — الموضع الحرج): كان pass صامتًا — المستخدم
            # ذكر ملفًا وفشلت قراءته فيُرسل الطلب للـ AI **بدون** محتواه
            # بلا أي إشارة. الآن: إطار warning للواجهة + log — التدفق
            # يكمل كالسابق (لا تغيير سلوك آخر — معيار القبول).
            print(f"  ⚠️ فشل قراءة الملف المكتشف {detected_file}: {e}")
            sctx.send({
                "type": "warning",
                "text": (f"⚠️ تعذّرت قراءة الملف المكتشف {detected_file} — "
                         f"سيُرسل طلبك بدون محتواه ({e})"),
            })
        detected_file = None  # لا نغير المجلد

    # ── معالجة مجلد مكتشف: عدم التبديل التلقائي إلا إذا كان نص الرسالة هو المسار فقط ──
    # TSK-501 (عيب 1 — الجذر الرئيسي): بوابة قرابة قبل الكارت —
    # مسار داخل المشروع المفتوح (نفسه/ولد) أو أبٌ له ← تجاهل صامت
    # والرسالة تكمل للـ AI طبيعيًا. كارت السؤال يُرفع فقط لمسار
    # خارج الشجرة تمامًا (outside). استثناء: الرسالة = المسار وحده
    # وهو مجلد مختلف فعليًا ← فتح مباشر كالسابق (لا تغيير سلوك).
    if detected_dir and not skip_path_detection:
        _root = getattr(getattr(sctx, "fm", None), "root", None)
        if _root is not None:
            _rel = classify_path_relation(detected_dir, str(_root))
            if _rel != PATH_REL_OUTSIDE:
                # نفس المشروع / ولد / أب — لا كارت ولا تبديل: المستخدم
                # واقف هنا أصلًا، وـ ancestor (مثل D:\) توسيعٌ خطر.
                print(f"  📍 مسار مكتشف {_rel} للمشروع المفتوح — "
                      f"تجاهل صامت: {detected_dir}")
                detected_dir = None
    if detected_dir and not skip_path_detection:
        if user_text.strip() == detected_dir:
            # كتابة مسار المجلد بمفرده تعني أمر فتح مباشر للمجلد
            try:
                sctx.switch_project(detected_dir)
                scan = sctx.fm.scan_project()
                if sctx.session_mgr:
                    sctx.session_mgr.update_project_path(detected_dir)
                sctx.send({
                    "type": "project_switched",
                    "project": {
                        "root": str(sctx.fm.root),
                        "name": sctx.fm.root.name,
                        "total_files": scan["total_files"],
                        "total_size_kb": scan["total_size_kb"],
                    }
                })
            except Exception as e:
                sctx.send({"type": "error", "text": f"فشل فتح المجلد: {e}"})
            return

        req_id = msg.get("request_id") or str(uuid.uuid4())
        deps.store_pending_path_request(req_id, {
            "path": detected_dir,
            "user_text": user_text,
            "mode": mode,
            "msg": msg,
            "timestamp": time.time()
        })
        sctx.send({
            "type": "path_detected_options",
            "request_id": req_id,
            "path": detected_dir
        })
        return  # ← وقف التنفيذ — لا يُرسل للـ AI حتى يختار المستخدم

    # ── 2. جمع السياق — ContextEngine (T-019, R-201) ──
    # TSK-103 (BUG-03): attached يمرر المحتوى المكتشف/المرفق ليُحزم
    # تحت سقف config.yaml:context_budget — أي إسقاط مرصود لا صامت.
    try:
        _msg_ctx = deps.gather_message_context(sctx.fm.root, user_text,
                                          index=sctx.project.index,
                                          attached=attached_context or None)
        mentioned_files = _msg_ctx.mentioned_files
        user_text_with_files = _msg_ctx.user_text_with_files
        project_context = _msg_ctx.project_context
        if _msg_ctx.dropped_attached:
            print(f"  ⚖️ ContextBudget: أُسقط من المرفقات: {_msg_ctx.dropped_attached}")
    except Exception as e:
        # NF-14 §7 (يحتاج log — أضيف): فشل جمع السياق كاملًا كان صامتًا —
        # الرسالة تمضي بلا سياق مشروع (fallback مقصود) لكن السبب يُسجّل.
        print(f"  ⚠️ gather_message_context فشل — مواصلة بلا سياق: {e}")
        mentioned_files = []
        user_text_with_files = user_text
        project_context = ""

    # R-303 (T-031): حقن بانر تنبيه الربط (سياسة warn) في السياق
    if sctx.binding_banner:
        project_context = (
            f"{sctx.binding_banner}\n\n{project_context}"
            if project_context else sctx.binding_banner
        )

    # ═══════════════════════════════════════
    # 🧠 Smart Routing — RequestRouter يقرر المسار
    # ═══════════════════════════════════════
    if deps.request_router and mode != "chat":
        try:
            # جمع محتوى الملفات المذكورة كـ dict
            files_dict = None
            if mentioned_files:
                files_dict = {}
                for f_path in mentioned_files[:5]:
                    try:
                        files_dict[f_path] = sctx.fm.read_file(f_path)
                    except Exception as _exc:
                        _slog_swallowed("core/chat_dispatch.py:194", _exc)
                        # NF-14 §8 (ابتلاع مقصود): ملف مذكور غير مقروء — التوجيه
                        # يكمل ببقية الملفات (إثراء اختياري للراوتر).
                        pass

            # اتخاذ القرار
            file_content_for_routing = None
            if mentioned_files and len(mentioned_files) == 1:
                try:
                    file_content_for_routing = sctx.fm.read_file(mentioned_files[0])
                except Exception as _exc:
                    _slog_swallowed("core/chat_dispatch.py:204", _exc)
                    # NF-14 §9 (ابتلاع مقصود): نفس §8 — إثراء اختياري للراوتر.
                    pass

            routing = deps.request_router.route(
                user_request=user_text,
                file_content=file_content_for_routing,
                files=files_dict,
                mode=mode,
            )

            # ── إبلاغ المستخدم بالقرار ──
            routing_tier = routing.tier
            deps.event_bus.publish(RoutingDecided(
                run_id=f"route-{uuid.uuid4().hex[:8]}",
                strategy=str(routing.strategy),
                payload=routing.to_dict()))
            if routing_tier is not RoutingTier.DIRECT:
                sctx.send({
                    "type": "chain_started",
                    "text": (
                        f"🧠 Smart Router: اختار **{routing.strategy}** "
                        f"(complexity: {routing.complexity_score:.1f})"
                        + (f"\n⚠️ {routing.downgrade_reason}" if routing.downgraded else "")
                    ),
                    "routing": routing.to_dict(),
                })

            # ── توجيه لـ sctx.chain_bridge ──
            if routing_tier is RoutingTier.CHAINED:
                chain_ticket = deps._begin_run_ticket(
                    "chain",
                    lambda m: sctx.send(m), sctx=sctx)
                if chain_ticket is None:
                    return
                _ws_send = sctx.send

                sctx.chat_history.append(Message(role="user", content=user_text))
                if sctx.session_mgr:
                    sctx.session_mgr.append_message("user", user_text)

                _chain_req = RunRequest(
                    mode="chain",
                    message=user_text_with_files,
                    context={
                        "file_content": file_content_for_routing,
                        "files": files_dict,
                    },
                    metadata={
                        "force_strategy": routing.chain_strategy,
                    },
                )
                threading.Thread(
                    target=deps._chain_runner_for_dispatch(
                        sctx.chain_bridge).run,
                    args=(_chain_req, chain_ticket,
                          deps._RunnerWSAdapter(_ws_send)),
                    daemon=True,
                    name=f"runner-chain-{chain_ticket.run_id}",
                ).start()
                return

            # ── توجيه لـ sctx.delegate_bridge ──
            if routing_tier is RoutingTier.DELEGATE and sctx.delegate_bridge:
                _delegate_event_frame = sctx.send

                sctx.chat_history.append(Message(role="user", content=user_text))
                if sctx.session_mgr:
                    sctx.session_mgr.append_message("user", user_text)

                delegate_ticket = deps._begin_run_ticket(
                    "delegate",
                    lambda m: sctx.send(m), sctx=sctx)
                if delegate_ticket is None:
                    return
                deps.RUNNERS["delegate"](bridge=sctx.delegate_bridge).run(
                    RunRequest(
                        mode="delegate",
                        message=user_text,
                        context={
                            "files": files_dict or {},
                            "project_context": project_context,
                        },
                    ),
                    delegate_ticket,
                    deps._RunnerWSAdapter(_delegate_event_frame),
                )
                return

        except Exception as e:
            print(f"  ⚠️ Router error: {e}")

    # ═══════════════════════════════════════
    # 🤖 Agent Loop — لكل الأوضاع
    # ═══════════════════════════════════════
    if deps.agent_tools and mode in ("build", "edit", "chat", "plan"):
        try:
            _ws_lock = threading.Lock()

            def _agent_ws_send(msg_dict):
                try:
                    with _ws_lock:
                        sctx.send(msg_dict)
                except Exception as e:
                    print(f"  ⚠️ Agent WS send error: {e}")

            def _agent_send_fn(prompt_text, hist, sys_prompt):
                if deps.provider_pool:
                    result, used_name = deps.provider_pool.send_with_fallback(
                        prompt_text, hist, sys_prompt
                    )
                    return result
                return sctx.active_provider().send(prompt_text, hist, sys_prompt)

            sctx.chat_history.append(Message(role="user", content=user_text))
            if sctx.session_mgr:
                sctx.session_mgr.append_message("user", user_text)

            sctx.send({"type": "start"})
            print(f"  🤖 Agent Loop started (mode={mode})")

            agent_ticket = deps._begin_run_ticket("agent", _agent_ws_send,
                                             sctx=sctx)
            if agent_ticket is None:
                return

            def _agent_loop_factory(frame_sink):
                return AgentLoop(
                    tools=deps.agent_tools,
                    send_fn=_agent_send_fn,
                    ws_send_fn=frame_sink,
                    system_prompt=get_system_prompt(),
                    max_iterations=6,
                    approval_gate=deps.approval_gate,
                )

            def _publish_agent_loop(loop):
                sctx.active_agent_loop = loop

            _agent_req = RunRequest(
                mode="agent",
                message=user_text_with_files,
                context={
                    # TSK-104 (NF-07): سقف تاريخ الحمولة وفق config
                    "history": deps._payload_history(sctx),
                    "project_context": project_context,
                },
            )
            _agent_runner = deps.RUNNERS["agent"](
                loop_factory=_agent_loop_factory,
                on_loop=_publish_agent_loop,
            )
            _agent_sink = deps._RunnerWSAdapter(_agent_ws_send)

            def _run_agent():
                # TSK-609 (PM-01/02 §R6): توقيت دورة الوكيل كاملة +
                # تقدير توكنز المخرج — حقول إضافية فقط على plan/done
                # (الواجهة تتجاهل المجهول)، نفس نمط chain (executor.py).
                _t0 = time.monotonic()
                try:
                    result = _agent_runner.run(
                        _agent_req, agent_ticket, _agent_sink)
                finally:
                    sctx.active_agent_loop = None
                _duration_ms = int((time.monotonic() - _t0) * 1000)

                if result.status == RESULT_FAILED:
                    print(f"  ❌ Agent Loop error: {result.error}")
                    _agent_ws_send({"type": "error", "text": result.error})
                    _agent_ws_send({"type": "done", "options": []})
                    return

                full_response = result.text or ""
                print(f"  ✅ Agent Loop done — {len(full_response)} chars")

                if not full_response:
                    _agent_ws_send({"type": "error", "text": "لم يتم الحصول على رد من الـ AI"})
                    _agent_ws_send({"type": "done", "options": []})
                    return

                sctx.chat_history.append(Message(role="assistant", content=full_response))
                if sctx.session_mgr:
                    sctx.session_mgr.append_message("assistant", full_response)

                parsed = deps.parser.parse(full_response, mode=mode)
                actions = deps._parsed_to_actions(parsed)  # TSK-601: التحويل المشترك
                # TSK-101 (BUG-01): وضع chat لا يُصدر إجراءات إطلاقًا —
                # app.js يعرض شريط الإجراءات لأي actions غير فارغة بلا فحص للوضع.
                if mode == "chat":
                    actions = []

                options = deps._parsed_options(parsed)

                # TSK-609 (PM-01): تقدير محلي (chars÷4) — نفس مقدّر
                # الميزانية المركزي، لا ثوابت جديدة.
                _tok = CharsPerTokenEstimator().estimate(full_response)
                if actions:
                    _agent_ws_send({
                        "type": "plan",
                        "actions": actions,
                        "options": options,
                        "summary": parsed.summary(),
                        "duration_ms": _duration_ms,
                        "token_estimate": _tok,
                    })
                else:
                    _agent_ws_send({
                        "type": "done",
                        "options": options,
                        "duration_ms": _duration_ms,
                        "token_estimate": _tok,
                    })

            sctx.backup_done_for_batch = False
            threading.Thread(
                target=_run_agent,
                daemon=True,
                name=f"runner-agent-{agent_ticket.run_id}",
            ).start()
            return

        except Exception as e:
            sctx.active_agent_loop = None
            print(f"  ⚠️ Agent Loop error: {e}")
            import traceback
            traceback.print_exc()

    # المسار العادي (direct/chat) — بناء البرومبت
    prompt = build_prompt(
        mode=mode,
        user_request=user_text_with_files,
        project_context=project_context
    )

    sctx.chat_history.append(Message(role="user", content=user_text))
    if sctx.session_mgr:
        sctx.session_mgr.append_message("user", user_text)

    system_prompt = get_system_prompt()

    sctx.send({"type": "start"})

    direct_ticket = deps._begin_run_ticket("direct", sctx.send, sctx=sctx)
    if direct_ticket is None:
        return
    _direct_req = RunRequest(
        mode="direct",
        message=prompt,
        system_prompt=system_prompt,
        # TSK-104 (NF-07): سقف تاريخ الحمولة وفق config
        context={"history": deps._payload_history(sctx)},
    )

    # TSK-606 (RF-01/RP-02/UXF-03): تشغيل الـ runner المباشر صار على
    # خيط عامل — كان متزامنًا على خيط حلقة استقبال WS فلا يُقرأ إطار
    # cancel_run من نفس الاتصال أثناء البث أبدًا. ما قبل هذا السطر
    # (إطار start + فحص busy للتذكرة) بقي متزامنًا حفاظًا على ترتيب
    # الإطارات؛ نفس نمط agent (_run_agent أعلاه) حرفيًا.
    def _run_direct():
        # TSK-609 (PM-01/02 §R6): توقيت المسار المباشر + تقدير توكنز
        # المخرج — حقول إضافية فقط على plan/done، نفس نمط chain.
        _t0 = time.monotonic()
        _direct_result = deps.RUNNERS["direct"](
            stream_fn=lambda p, h, s: sctx.active_provider().stream(p, h, s)
        ).run(_direct_req, direct_ticket, deps._RunnerWSAdapter(sctx.send))
        _duration_ms = int((time.monotonic() - _t0) * 1000)

        full_response = _direct_result.text
        if _direct_result.status != RESULT_COMPLETED:
            sctx.send({
                "type": "error",
                "text": _direct_result.error or "الرد لم يكتمل",
            })

        sctx.chat_history.append(Message(role="assistant", content=full_response))
        if sctx.session_mgr:
            sctx.session_mgr.append_message("assistant", full_response)

        parsed = deps.parser.parse(full_response, mode=mode)

        actions = deps._parsed_to_actions(parsed)  # TSK-601: التحويل المشترك
        options = deps._parsed_options(parsed)

        sctx.backup_done_for_batch = False

        # TSK-609 (PM-01): تقدير محلي (chars÷4) — نفس مقدّر الميزانية.
        _tok = CharsPerTokenEstimator().estimate(full_response)
        if mode in ("plan", "build", "edit") and actions:
            sctx.send({
                "type": "plan",
                "actions": actions,
                "options": options,
                "summary": parsed.summary(),
                "duration_ms": _duration_ms,
                "token_estimate": _tok,
            })
        else:
            sctx.send({
                "type": "done",
                # TSK-101 (BUG-01): إطار done في وضع chat لا يحمل إجراءات أبدًا —
                # الواجهة تعرض شريط الإجراءات لأي actions غير فارغة.
                "actions": [] if mode == "chat" else actions,
                "options": options,
                "summary": parsed.summary(),
                "duration_ms": _duration_ms,
                "token_estimate": _tok,
            })

    threading.Thread(
        target=_run_direct,
        daemon=True,
        name=f"runner-direct-{direct_ticket.run_id}",
    ).start()


