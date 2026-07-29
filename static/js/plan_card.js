/* TSK-619 (CP-1/UXF-01 §R9): بطاقة الخطة التفاعلية — منطق نقي (UMD-lite،
 * قابل للاختبار في node). الـ DOM glue في app.js فقط.
 *
 * ── الفكرة ─────────────────────────────────────────────────────────────
 * ترقية بطاقة الخطة إلى artifact تفاعلي: لكل خطوة checkbox تفعيل/تعطيل
 * قبل «نفّذ» — executePlan يرسل **المفعّل فقط** (subset من نفس القائمة
 * بنفس الترتيب). server.py لا يتغير: _apply_batch يمر على ما وصله.
 *
 * ── ضمان حفظ السلوك (بند Gates حرفيًا) ────────────────────────────────
 * createState(actions) يبدأ بكل الخطوات مفعّلة؛ enabledActions على حالة
 * كاملة التفعيل تعيد نفس عناصر actions بنفس الترتيب ⇒ الافتراضي
 * (لا لمس) = payload التنفيذ القديم حرفيًا.
 *
 * ── الواجهة ────────────────────────────────────────────────────────────
 * createState(actions)        → { actions, enabled: [true, ...] }
 * toggle(state, i)            → يقلب علم الخطوة i (خارج النطاق: لا شيء)
 * setEnabled(state, i, flag)  → ضبط صريح للعلم
 * isEnabled(state, i)         → قراءة العلم (خارج النطاق: false)
 * enabledActions(state)       → subset الخطوات المفعّلة بترتيبها الأصلي
 * enabledCount(state)         → عدد المفعّل (0 ⇒ الغراء يمنع الإرسال،
 *                               نفس حارس executePlan القائم على القائمة
 *                               الفارغة)
 */
(function (global) {
    "use strict";

    function createState(actions) {
        var list = Array.isArray(actions) ? actions : [];
        var enabled = [];
        for (var i = 0; i < list.length; i++) enabled.push(true);
        return { actions: list, enabled: enabled };
    }

    function _inRange(state, i) {
        return !!state && typeof i === "number" &&
            i >= 0 && i < state.enabled.length;
    }

    function toggle(state, i) {
        if (_inRange(state, i)) state.enabled[i] = !state.enabled[i];
    }

    function setEnabled(state, i, flag) {
        if (_inRange(state, i)) state.enabled[i] = !!flag;
    }

    function isEnabled(state, i) {
        return _inRange(state, i) ? state.enabled[i] : false;
    }

    function enabledActions(state) {
        if (!state) return [];
        var out = [];
        for (var i = 0; i < state.actions.length; i++) {
            if (state.enabled[i]) out.push(state.actions[i]);
        }
        return out;
    }

    function enabledCount(state) {
        if (!state) return 0;
        var n = 0;
        for (var i = 0; i < state.enabled.length; i++) {
            if (state.enabled[i]) n++;
        }
        return n;
    }

    var PlanCard = {
        createState: createState,
        toggle: toggle,
        setEnabled: setEnabled,
        isEnabled: isEnabled,
        enabledActions: enabledActions,
        enabledCount: enabledCount,
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = PlanCard;
    }
    global.PlanCard = PlanCard;
})(typeof globalThis !== "undefined" ? globalThis : this);
