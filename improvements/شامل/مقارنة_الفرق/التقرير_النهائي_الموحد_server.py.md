# 🧠 التقرير النهائي الموحد لمقارنة وتحليل كود السيرفر (server.py)

مرحباً بك يا صاحبي! هذا التقرير يقدم مراجعة وتحليلاً تفصيلياً للفروقات والترقيات الجوهرية التي تمت على ملف `server.py` بين النسخة القديمة والجديدة. التغييرات الجديدة تنقل معمارية السيرفر (FastAPI/Flask) لمستويات متقدمة من التحكم، الأمان، وإدارة الخيوط المتوازية (Multithreading)، بالإضافة إلى دعم كامل ومؤمن لأنظمة المرفقات، الإيقاف الذكي، والتفويض (M6).

---

## 🚀 1. الميزات الهيكلية والخصائص الجديدة المضافة

تم دعم السيرفر بمجموعة من الميزات والترقيات الجوهرية:

1. **إيقاف الكاش أثناء التطوير (No-Cache Headers):**
   * السيرفر يقوم الآن بحقن هيدرات تمنع كاش المتصفح تلقائياً لملفات HTML وJS وCSS، مما يضمن ظهور تعديلات الواجهة فوراً.
2. **التبديل المركزي والآمن للمشروع (Atomic Project Switch):**
   * منع التبديل العشوائي للمجلدات أثناء تشغيل خيوط توليد (Active Chain) نشطة لتجنب تعارض الملفات.
3. **خيوط الاستقبال والإرسال المستقلة للـ WebSockets (Thread-Isolated I/O):**
   * تشغيل خيط استقبال منفصل (`_recv_worker`) للتخلص من حظر الاتصال (I/O blocking) والمحافظة على استجابة السيرفر.
4. **نظام التحقق الأمني من المرفقات (Security Verification & Traversal Guard):**
   * حماية الخادم من ثغرات حقن المسارات (Path Traversal) والتأكد من أمان المجلدات قبل معالجتها.
5. **نظام التفويض M6 مدمجاً في الـ WebSockets (Delegate Bridge integration):**
   * إرسال وإدارة أحداث التفويض وموافقة أو رفض المستخدم للتعديلات مباشرة عبر الـ WebSocket.

---

## 🛠️ 2. توضيح الأكواد بالتفصيل (قبل وبعد التعديل)

### 1️⃣ تعطيل كاش المتصفح ديناميكياً (Dev No-Cache Headers)
* **قبل التعديل:**
  كان السيرفر يرسل الملفات الثابتة (Static assets) بالإعدادات الافتراضية، مما يسبب احتفاظ المتصفح بنسخة قديمة من الأكواد ويستدعي عمل Hard Reload (Ctrl+F5) يدوياً بشكل متكرر.
* **بعد التعديل:**
  تم حقن فلتر `@app.after_request` مع ضبط الكاش لـ 0:
```python
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # ← لا cache للملفات الـ static

@app.after_request
def add_no_cache_headers(response):
    """منع الـ cache أثناء التطوير — يضمن تحميل آخر نسخة دائماً"""
    if "text/html" in response.content_type or \
       "javascript" in response.content_type or \
       "text/css" in response.content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response
```

---

### 2️⃣ التبديل المركزي الآمن والذري للمشاريع (_switch_project_internal)
* **قبل التعديل:**
  كان تغيير المجلد في الـ Endpoint `api_switch_project` يحدث بشكل مباشر وعشوائي، مما يعرض خيوط البث الـ Active للانهيار أو الكتابة في مجلد خطأ في نفس الوقت.
* **بعد التعديل:**
  تم عزل عملية التبديل داخل دالة ذرية مؤمنة بقفل `_active_chain_lock` لمنع التبديل أثناء تشغيل AI Chain:
```python
def _switch_project_internal(new_path: str):
    """تقوم بتبديل مجلد المشروع بشكل مركزي وآمن مع الحماية وتحديث الـ Session والـ Bridges"""
    global fm, cmd_runner, session_mgr, chain_bridge
    abs_path = os.path.normcase(os.path.realpath(new_path))
    if not os.path.isdir(abs_path):
        raise ValueError(f"المسار ليس مجلداً صالحاً: {abs_path}")

    # حماية الـ Chain لمنع التبديل المتزامن
    with _active_chain_lock:
        if _active_chain_run is not None:
            raise PermissionError("لا يمكن تغيير المشروع أثناء تشغيل Chain نشط!")

    # إنشاء الموارد محلياً للتأكد من نجاحها قبل الاستبدال (Atomic Swap)
    new_fm = FileManager(abs_path)
    new_cmd_runner = CommandRunner(cwd=abs_path, auto_approve=True)
    scan = new_fm.scan_project()

    # التبديل الذري الآمن
    fm = new_fm
    cmd_runner = new_cmd_runner

    if session_mgr:
        session_mgr.update_project_path(abs_path)
    if chain_bridge:
        chain_bridge._project_root = abs_path
        chain_bridge._runs_dir = pathlib.Path(abs_path) / ".ai_runs"

    return {
        "root": str(fm.root),
        "name": fm.root.name,
        "total_files": scan["total_files"],
        "total_size_kb": scan["total_size_kb"],
    }
```

---

### 3️⃣ معالجة الشات التفاعلي الموازي ودعم إيقاف التوليد (_process_ai_chat & Stop Mode)
* **قبل التعديل:**
  كان السيرفر يستقبل الرسائل وينتظر رد الـ API بالكامل وبشكل متزامن يمنع المستخدم من مقاطعة الـ AI أو إيقافه إذا بدأ بكتابة أكواد خاطئة.
* **بعد التعديل:**
  تم تحويل البث إلى خيط معالجة مستقل (`_stream_worker`) مع مراقبة مستمرة لـ `ws_msg_queue` لاستقبال وتفسير رسالة `stop` فوراً لقطع الاتصال ووقف التوليد:
```python
        # لوب البث ومراقبة رسالة الإيقاف
        while True:
            if ws_msg_queue is not None:
                try:
                    while not ws_msg_queue.empty():
                        ws_raw = ws_msg_queue.get_nowait()
                        if ws_raw is None:
                            termination = {"kind": "disconnected"}
                            cancel_event.set()
                            break
                        ws_data = json.loads(ws_raw)
                        if ws_data.get("type") == "stop":
                            ws_req_id = ws_data.get("request_id")
                            if ws_req_id == request_id:
                                # قطع البث وإشعار المستخدم بالإيقاف اليدوي
                                _safe_ws_send(ws, {"type": "chunk", "request_id": request_id, "text": "\n\n🛑 [تم إيقاف التوليد بواسطة المستخدم]"})
                                cancel_event.set()
                                termination = {"kind": "stopped"}
                                break
```

---

### 4️⃣ التحقق الأمني التام من المرفقات لمنع الـ Path Traversal (validate_attachment_files)
* **قبل التعديل:**
  لم يكن هناك أي فحص على السيرفر للمرفقات المرفوعة، مما يتيح إمكانية تمرير مسارات ملغومة تؤدي إلى قراءة أو كتابة خارج مجلد المشروع.
* **بعد التعديل:**
  تم حقن دالة تحقق متكاملة تطبق قيود الأمان وأحجام الملفات بدقة:
```python
def validate_attachment_files(files) -> tuple[bool, str]:
    if not isinstance(files, dict):
        return False, "تنسيق المرفقات غير صالح (يجب أن يكون Object)"
    if len(files) > 50:
        return False, "عدد الملفات يتجاوز الحد الأقصى المسموح به (50 ملف)"
        
    total_size = 0
    collision_registry = {}
    
    for path, content in files.items():
        # تطبيع المسار لمنع التلاعب
        norm_path = path.replace('\\', '/')
        norm_path = unicodedata.normalize('NFC', norm_path)
        norm_path = re.sub(r'/+', '/', norm_path).strip()
        
        # كشف ومنع محاولات الـ Path Traversal
        if (re.match(r'^[A-Za-z]:', norm_path) or norm_path.startswith('/') or '\0' in norm_path):
            return False, f"مسار ملف غير صالح أو مطلق: {path}"
            
        segments = norm_path.split('/')
        for segment in segments:
            if segment in ('.', '..'):
                return False, f"مسار غير آمن (يحتوي على .. أو .): {path}"
```

---

### 5️⃣ دمج عمليات التفويض وإرسال الأحداث M6 للـ WebSocket
* **قبل التعديل:**
  كانت عمليات الـ Agent تقتصر على الدردشة الخطية العادية دون إمكانية تفويض مهام مركبة تتطلب دورة حياة كاملة (مراجعة، رفض، إعادة توجيه).
* **بعد التعديل:**
  تم استقبال وتوجيه رسائل نظام التفويض M6 (`delegate_message`, `delegate_approve`, `delegate_reject`) وتشغيل خادم التفويض في خيط منعزل وإرسال أحداث التقدم حية للـ WebSocket:
```python
        elif msg_type == "delegate_message":
            user_text = data.get("text", "").strip()
            if not delegate_bridge:
                delegate_bridge = DelegateBridge(provider)
            ...
            def delegate_event_handler(event_type, event_data):
                try:
                    ws.send(json.dumps({"type": event_type, **event_data}))
                except Exception: pass

            # تشغيل التفويض في thread مستقل لعدم تعطيل السيرفر
            t = threading.Thread(target=lambda: delegate_bridge.run_delegation(
                user_request=user_text, files_context=files_context,
                project_context=project_context, on_event=delegate_event_handler
            ), daemon=True)
            t.start()
```

---

## 🔒 3. سد الثغرات الأمنية والأخطاء (Security & Bugs Resolved)

1. **منع ثغرة الـ Path Traversal والوصول للملفات الحساسة:**
   * **المشكلة:** عدم وجود فحص في الكود القديم على أسماء المرفقات، مما يتيح إرسال مسارات تحتوي على `../` أو أقراص مطلقة مثل `C:` للوصول لملفات النظام خارج مجلد المشروع.
   * **الحل:** الفحص الصارم للمسارات وتطبيعها عبر `unicodedata.normalize` وحظر وجود الأحرف الصفرية (`\0`) أو النقاط المزدوجة النسبية.
2. **ثغرة تسريب الخيوط والـ WebSockets المقطوعة (Thread Leak & Connection Crashes):**
   * **المشكلة:** إذا قام المستخدم بإنعاش الصفحة أو قطع النت أثناء بث الـ AI، كان الـ `ws.send` القديم ينهار مسبباً كراش أو تسريب خيوط المعالجة الخلفية (Thread Leak) التي تظل معلقة بالذاكرة دون توقف.
   * **الحل:** استخدام دالة `_safe_ws_send` لامتصاص استثناءات قطع الاتصال، ووضع خيط الاستقبال `_recv_worker` الذي يرسل إشارة `None` للـ Queue في حالة انقطاع الاتصال، مما يفعل الـ `cancel_event` تلقائياً ليقفل الـ `_stream_worker` ويحرر موارد النظام فوراً.
3. **تضارب تداخل المشاريع أثناء التوليد (Race Condition on Switch):**
   * **المشكلة:** لو طلب المستخدم تغيير مجلد المشروع أثناء تشغيل AI chain، كان السيرفر يستجيب فوراً مما يفسد قراءة/كتابة الملفات للعمليات الجارية.
   * **الحل:** استخدام قفل الحماية المركزي `_active_chain_lock` لمنع التبديل ورمي `PermissionError` فورية لحماية التوليد النشط.
4. **ثغرة التعارض الهيكلي وتطابق الأحرف (Prefix & Case-insensitive Path Collision):**
   * **المشكلة:** في نظام ويندوز، المسارات غير حساسة لحالة الأحرف (Case-insensitive)، مما قد يسبب تضارباً برفع ملفين مثل `File.py` و `file.py`. أيضاً قد يحاول المستخدم رفع ملف بمسار يتعارض مع مجلد قائم (مثلاً رفع ملف باسم `src/utils.py` ومجلد فرعي باسم `src/utils.py/helper.js` معاً).
   * **الحل:** استخدام سجل التعارض `collision_registry` داخل دالة `validate_attachment_files` لتخزين المسارات بالحروف الصغيرة (lowercase) والتحقق من تداخل البادئات (Prefix check) لمنع استخدام أي مسار كملف ومجلد في نفس الوقت.
5. **تضارب مسار المجلد الخارجي المكتشف (Auto-Switch Conflict):**
   * **المشكلة:** في النسخة القديمة، بمجرد ذكر أي مسار مجلد في الشات، كان السيرفر يغير المشروع فوراً. ده كان بيعمل مشاكل وتضارب لو المستخدم بيكتب المسار لمجرد المناقشة ومش عايز يغير بيئة العمل فعلياً.
   * **الحل:** السيرفر مبقاش يغير المجلد تلقائياً؛ بقى بيخزن الطلب مؤقتاً في `pending_path_requests` ويبعت للواجهة رسالة `path_detected_options` عشان يظهر للمستخدم 3 خيارات واضحة للموافقة والتحكم:
     * **`switch`** (تغيير مجلد العمل للمسار المكتشف).
     * **`attach`** (إرفاق سياق ملفات المجلد كـ context للطلب الحالي دون تغيير المشروع).
     * **`continue`** (الاستمرار كدردشة عادية وتجاهل المسار).

---

## 💡 4. توصيات الأداء والاستقرار الفني

1. **مشكلة استهلاك الذاكرة وتضخم الـ Payload (OOM Guard):**
   * **المشكلة:** رفع مرفقات ضخمة جداً كان ممكن يسبب انهيار الرام بالكامل (Out Of Memory) للسيرفر.
   * **الحل:** السيرفر بقى بيطبق حد أقصى صارم لحجم رسالة الـ WebSocket المستقبلة بـ `250MB` من خلال خيط الاستقبال `_recv_worker` لمنع تضخم الـ payload. وبالمثل، تمنع دالة التحقق معالجة أي مرفقات تتجاوز إجمالاً `200MB`.
2. **تنظيف الذاكرة التلقائي (TTL Memory Sweep):**
   * دالة `_clean_expired_pending_requests` تقوم بتنظيف طلبات تغيير المسار المعلقة تلقائياً كل 5 دقائق (TTL = 300s) أو بمجرد تجاوز عددها 50 طلباً، لمنع أي تسريب ذاكرة (Memory Leak) في السيرفر.
3. **مشكلة الـ Cache وتأخر التحديثات:**
   * تم القضاء على مشكلة احتفاظ المتصفح بملفات الـ CSS/JS القديمة من خلال تصفير كاش الـ Flask وحقن هيدرات الـ `Cache-Control` لتجربة تطوير فورية وسلسة.
