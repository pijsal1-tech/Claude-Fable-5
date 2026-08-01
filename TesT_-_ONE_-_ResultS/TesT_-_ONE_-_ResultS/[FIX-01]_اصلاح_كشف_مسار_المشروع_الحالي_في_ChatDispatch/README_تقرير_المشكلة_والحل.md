# 🐛 [TSK-501 / FIX-01-A] تقرير هندسي نهائي: إصلاح كشف مسار المشروع في `ChatDispatch`

---

## 📌 1. المتاع والمعرّف التوثيقي (Metadata)
- **رمز المهمة**: `TSK-501` (المعروف بـ `FIX-01-A`)
- **المكون المتأثر**: `core/chat_dispatch.py` (مع تكامل `chain/path_policy.py`)
- **السياسة المتبعة**: D-8-ب (Windows أولًا — معيار فحص المسارات وحالة الحروف)
- **إصدار التحديث المرتقب**: `v1.0.0-rc.2` (تحت قسم `[Fixed]` في `CHANGELOG.md`)
- **التصنيف**: `[Debug]` / `[UI-UX]` / `[Logic-Fix]` / `[SafeReader]`

---

## 🔍 2. الأدلة الحية المقتبسة من الكود (Verified Code Evidence)

من كود `core/chat_dispatch.py` المباشر (الأسطر 51-89 و 119-155):

### أ. الـ Regex المتسبب في اقتطاع المسار عند المسافة:
```python
# السطر 65 في core/chat_dispatch.py:
win_paths = re.findall(r'[A-Za-z]:[\\/ ][^\s,;"\'>]+', user_text)
```
> ⚠️ **الدليل**: الصنف `[\\/ ]` يحتوي على مسافة، مما يقطع المسار المطلق عند أول مسافة أو يقتطعه لحرف المحرك `D:\` فقط إذا تلاه مسافة أو رمز فصل.

### ب. الكتلة المنطقية المسببة للسؤال الصامت (الأسطر 119-155):
```python
# السطر 120 في core/chat_dispatch.py:
if detected_dir and not skip_path_detection:
    if user_text.strip() == detected_dir:
        # كتابة المسار بمفرده تعني فتح مباشر للمجلد
        ...
        return

    req_id = msg.get("request_id") or str(uuid.uuid4())
    deps.store_pending_path_request(req_id, {...})
    sctx.send({
        "type": "path_detected_options",
        "request_id": req_id,
        "path": detected_dir
    })
    return  # ← يوقف التنفيذ ويظهر كارت السؤال فوراً بدون المقارنة بالمشروع المفتوح!
```

---

## 🧩 3. التحليل الهندسي الشامل ومنطق تجربة المستخدم (UX Logic Matrix)

| المسار المكتشف | السلوك المنطقي المتوقع | السلوك الحالي قبل الإصلاح |
|---|---|---|
| **نفس مشروعك المفتوح** (`d == r`) | ⏭️ تجاهل صامت (المستخدم يعمل داخله) | ❌ يظهر كارت السؤال |
| **جزء منه** (مجلد فرعي تحت المشروع) | ⏭️ تجاهل صامت | ❌ يظهر كارت السؤال |
| **أب له أو جذور المحركات** (`D:\`, `C:\`, `C:\Windows`) | 🛑 حظر عرض الكارت وتجاهل صامت (منع فتح الدرايف كاملاً) | ❌ يظهر كارت السؤال |
| **مسار خارجي غريب عن الشجرة** | ⚠️ إظهار كارت السؤال للمستخدم | ✅ يظهر كارت السؤال |

---

## 🔧 4. التكنيك الهندسي المحكم للإصلاح (Production Patch Architecture)

### أ. خطوة الحظر المبكر للمرفقات الرسمية (Early Skip for Attachments):
إذا كان الإطار يحمل مرفقاً رسمياً (`attachments` أو `from_attachment: true`)، يتم تخطي كشف المسارات النصية بالكامل في البداية:

```python
# في بداية chat_dispatch.py:
if (msg.get("attachments") or msg.get("from_attachment")) and not skip_path_detection:
    skip_path_detection = True
```

### ب. دالة الفحص المحكمة بـ `Path` الصريحة وحظر درايف الجذر (Drive Root Guard):
تجنب الفخاخ النصية مثل (`startswith` التي تضلل بين `E:\app` و `E:\apple`) مع دعم `normcase` للأمان في Windows ومعالجة الاستثناءات:

```python
import os
from pathlib import Path
from chain.path_policy import resolve_workspace_path

def is_root_or_system_dir(p: Path) -> bool:
    """فحص ما إذا كان المسار هو جذر محرك مثل C:\ أو D:\ أو مجلد نظام حساس"""
    resolved = p.resolve()
    # جذر المحرك في Windows يكون parent الخاص به هو نفسه
    if resolved.parent == resolved or len(resolved.parts) <= 1:
        return True
    norm = os.path.normcase(str(resolved))
    if norm in [os.path.normcase(r"C:\windows"), os.path.normcase(r"C:\users")]:
        return True
    return False

def is_related_to_workspace(detected_path: str, project_root: str) -> bool:
    """
    فحص التبعية لشجرة المشروع مع تجنب Substring Traps 
    ومعالجة الأخطاء الاستثنائية بـ Safety Fallback.
    """
    try:
        detected = Path(detected_path).resolve()
        root = Path(project_root).resolve()
        
        # 1. حظر جذور المحركات والأب
        if is_root_or_system_dir(detected):
            return True
            
        # 2. فحص المساواة الصريحة بـ Path
        if detected == root:
            return True
            
        # 3. فحص التبعية المتبادلة بواسطة relative_to النظيفة
        for sub, base in ((detected, root), (root, detected)):
            try:
                sub.relative_to(base)
                return True
            except ValueError:
                continue
                
        return False
    except (OSError, ValueError, Exception):
        # عند أي استثناء في الفحص → افترض غير مرتبط كأمان
        return False
```

---

## 🧪 5. مصفوفة حالات الاختبار الـ 10 الحرجـة (10 Required Critical Test Cases)

| # | حالة الاختبار | السيناريو والمحتوى | النتيجة المتوقعة |
|:---:|---|---|---|
| **1** | `test_same_project` | `detected_dir == root` | ⏭️ عدم إظهار الكارت |
| **2** | `test_child_subfolder` | `root / "src"` | ⏭️ عدم إظهار الكارت |
| **3** | `test_parent_drive_root` | `D:\` مقابل `D:\SMS\project` | 🛑 عدم إظهار الكارت |
| **4** | `test_windows_case_insensitive` | `d:\sms` مقابل `D:\SMS` | ⏭️ عدم إظهار الكارت |
| **5** | `test_external_path` | `E:\other_project` | ⚠️ إظهار كارت السؤال |
| **6** | `test_substring_trap_protection` | `E:\app` مقابل `E:\apple` | ⚠️ إظهار الكارت دون تضليل |
| **7** | `test_formal_attachment_skip` | `msg.attachments` موجود | ⏭️ تخطي الفحص النصي بالكامل |
| **8** | `test_e2e_attachment_read` | بعد كتم الكارت | ✅ قراءة محتوى الملف وإرفاقه لـ AI |
| **9** | `test_trailing_slash_parity` | `D:\proj\` مقابل `D:\proj` | ⏭️ عدم التأثر بالفواصل |
| **10** | `test_malformed_path_resilience` | مسار به رموز غريبة أو يتجاوز الطول | 🛡️ معالجة الاستثناء بـ `False` |

---

## 🔬 6. مطابقة معايير جودة المشروع (Quality & CI Standards)

1. **اختبار التجميع والدمج (Integration Harness)**:
   - كتابة اختبار integration يمر عبر `server._handle_ws_message` محاكياً جلسة حقيقية (`SessionContext`).
2. **بوابة حماية الـ Regex (Grep Gate)**:
   - إضافة اختبار `TestPathDetectionGrep` لمنع العودة لـ Regex القديم أو قذف استثناءات صامتة.
3. **بوابة CI والـ Coverage Ratchet**:
   - إنجاز التعديل مع تشغيل `./scripts/check.sh` بنجاح قاطع **ALL GREEN**، والحفاظ على نسبة التغطية فوق أرضية `coverage_baseline.txt` دون أي هبوط.

---

## 🏷️ 7. توثيق السجل والإصدار (Release Governance)
عند اعتماد الـ Patch وتطبيقه، يتم توثيقه في `CHANGELOG.md`:

```markdown
### Fixed
- **TSK-501 (FIX-01-A)**: Suppress path detection card for workspace-related detected directories (`same/child/drive-root`) and skip text path scan when explicit attachments are present.
```

---

## ✅ 8. الحل المؤقت المتبع حالياً (Workaround)
عند سحب ملف ينتمي لنفس المشروع:
- الضغط على **"تجاهل والمتابعة"** في البطاقة، وسيستمر النظام في قراءة سياق الملف وإرساله للـ AI بشكل طبيعي كلياً.
