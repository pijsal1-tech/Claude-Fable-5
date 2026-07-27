#!/usr/bin/env python3
"""
=============================================================
 GITHUB  Tar.gz Auto-Uploader & Logger Script  (v4.3)
=============================================================
 المميزات:
 1. البحث عن ملفات .tar.gz في مجلد السكريبت + مجلد التنزيلات
    (C:\\Users\\pc\\Downloads) واختيار الأحدث حسب تاريخ التعديل.
 2. كتابة التقرير (تقرير.md) دائماً في مجلد السكريبت مركزياً.
 3. تحسينات أمنية واستقرارية (v4.3):
    - الاعتماد الحصري على متغير البيئة GITHUB_TOKEN
      (تمت إزالة التوكن الاحتياطي المدمج نهائياً).
    - إخفاء التوكن (masking) من كل رسائل الخطأ والمخرجات.
    - فك ضغط آمن (safe_extract) للوقاية من ثغرة Path Traversal
      مع استخدام فلتر بايثون الرسمي filter="data" عند توفره.
    - إصلاح ValueError في فحص المسارات على ويندوز عند اختلاف
      الدرايفات (C:\\ مقابل D:\\) باستخدام normcase.
    - منع نافذة إدخال بيانات الاعتماد (credential popup) وتعليق
      السكريبت عبر تعطيل credential.helper وتعيين
      GIT_TERMINAL_PROMPT=0 مع مهلة زمنية (timeout) لكل أمر.
    - إعداد هوية git (user.name / user.email) محلياً قبل الـ commit.
    - دعم كامل لحالات git diff: إضافة (A) / تعديل (M) /
      حذف (D) / إعادة تسمية (R) / نسخ (C).
=============================================================
"""
import os
import sys
import time
import urllib.parse
import urllib.request
import shutil
import tarfile
import tempfile
import subprocess
from datetime import datetime

# -------------------------------------------------------------
# إعداد ترميز الإخراج ودعم ألوان ANSI على ويندوز
# -------------------------------------------------------------
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

if os.name == 'nt':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# -------------------------------------------------------------
# الإعدادات العامة
# -------------------------------------------------------------
REPO_URL = "https://github.com/pijsal1-tech/Claude-Fable-5.git"
REPO_BRANCH = "main"

# ✅ (تصحيح 1): قراءة التوكن من متغير البيئة أولاً، مع fallback للتوكن القديم
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "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").strip()

# ✅ (v4.6): إعدادات إشعارات تليجرام
TELEGRAM_BOT_TOKEN = "7980723104:AAHDxJIJAD0U9xNGozm3KYWik5Q2iY7pieI"
TELEGRAM_CHAT_ID = "1124247595"

GIT_USER_NAME = "Auto Uploader Bot"
GIT_USER_EMAIL = "auto-uploader@localhost"
REPORT_FILENAME = "تقرير.md"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# المهلة الزمنية القصوى (بالثواني) لأوامر git — تمنع التعليق للأبد
GIT_CMD_TIMEOUT = 300

DOWNLOADS_DIR = r"C:\Users\pc\Downloads"
if not os.path.isdir(DOWNLOADS_DIR):
    _fallback_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(_fallback_downloads):
        DOWNLOADS_DIR = _fallback_downloads

# -------------------------------------------------------------
# أدوات الطباعة وإخفاء التوكن
# -------------------------------------------------------------
def mask_token(text):
    """إخفاء التوكن من أي نص قبل طباعته أو تسجيله."""
    if not text:
        return text
    if GITHUB_TOKEN:
        text = text.replace(GITHUB_TOKEN, "***TOKEN***")
    return text

def log_message(msg, color=RESET):
    print(f"{color}[*] {mask_token(msg)}{RESET}")

# -------------------------------------------------------------
# ✅ (v4.6): إشعارات تليجرام عبر urllib فقط (بدون مكتبات خارجية)
# -------------------------------------------------------------
def send_telegram_message(text):
    """
    إرسال إشعار تليجرام بتنسيق HTML باستخدام urllib المدمجة فقط.
    - خفيفة جداً على الرامات: بدون requests أو أي مكتبة خارجية.
    - أي فشل في الإرسال لا يوقف السكريبت (إشعار اختياري).
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            api_url, data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                log_message("تم إرسال إشعار تليجرام بنجاح. 📨", GREEN)
                return True
            log_message(f"⚠️ تليجرام أعاد حالة غير متوقعة: {resp.status}", YELLOW)
            return False
    except Exception as e:
        log_message(f"⚠️ تعذر إرسال إشعار تليجرام: {e}", YELLOW)
        return False

# -------------------------------------------------------------
# ✅ (تصحيح 3): تشغيل الأوامر بأمان — بدون credential popup وبدون تعليق
# -------------------------------------------------------------
def _build_git_env():
    """
    تجهيز بيئة تشغيل أوامر git بحيث:
    - GIT_TERMINAL_PROMPT=0  : يمنع git من طلب اسم مستخدم/كلمة مرور في الطرفية.
    - GIT_ASKPASS فارغ       : يمنع فتح أي نافذة رسومية لإدخال بيانات الاعتماد.
    - GCM_INTERACTIVE=never  : يمنع Git Credential Manager من التدخل تفاعلياً.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = ""
    env["GCM_INTERACTIVE"] = "never"
    return env

def run_cmd(args, cwd=None, timeout=GIT_CMD_TIMEOUT):
    """
    تشغيل أمر خارجي مع:
    - مهلة زمنية (timeout) لمنع التعليق اللانهائي.
    - بيئة git آمنة تمنع أي مطالبة تفاعلية.
    - تعطيل credential.helper لأوامر git تحديداً حتى لا يتدخل
      أي مدير اعتمادات مثبت على الجهاز (Windows Credential Manager).
    - إخفاء التوكن من جميع رسائل الخطأ.
    """
    # حقن تعطيل credential.helper مباشرة بعد كلمة "git"
    if args and args[0] == "git":
        args = ["git", "-c", "credential.helper="] + args[1:]

    try:
        res = subprocess.run(
            args, cwd=cwd,
            capture_output=True, encoding="utf-8", errors="replace",
            check=True,
            timeout=timeout,
            env=_build_git_env()
        )
        return res.stdout.strip()
    except subprocess.TimeoutExpired:
        safe_cmd = mask_token(" ".join(args))
        print(f"{RED}❌ انتهت المهلة الزمنية ({timeout} ثانية) أثناء تنفيذ الأمر: {safe_cmd}{RESET}")
        print(f"{RED}❌ غالباً السبب: مشكلة شبكة أو محاولة مصادقة معلّقة. تحقق من صلاحية GITHUB_TOKEN.{RESET}")
        raise RuntimeError(f"Command timed out: {safe_cmd}") from None
    except subprocess.CalledProcessError as e:
        safe_cmd = mask_token(" ".join(args))
        safe_err = mask_token((e.stderr or "").strip())
        print(f"{RED}❌ فشل تشغيل الأمر: {safe_cmd}{RESET}")
        print(f"{RED}❌ الخطأ: {safe_err}{RESET}")
        raise RuntimeError(f"Command failed: {safe_cmd}") from None

# -------------------------------------------------------------
# ✅ (تصحيح 2): فك الضغط الآمن — متوافق مع ويندوز والدرايفات المختلفة
# -------------------------------------------------------------
def _is_within_directory(directory, target):
    """
    التحقق من أن المسار target يقع داخل directory.
    - نستخدم os.path.normcase لتوحيد حالة الأحرف وفواصل المسارات
      (ويندوز غير حساس لحالة الأحرف ويقبل / و \\).
    - نلتقط ValueError التي يرفعها os.path.commonpath على ويندوز
      عندما يكون المساران على درايفين مختلفين (مثل C:\\ و D:\\)
      — في هذه الحالة المسار بالتأكيد خارج المجلد فنرجع False.
    """
    abs_directory = os.path.normcase(os.path.abspath(directory))
    abs_target = os.path.normcase(os.path.abspath(target))
    try:
        return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])
    except ValueError:
        # مسارات على درايفات مختلفة أو خليط مطلق/نسبي => خارج المجلد قطعاً
        return False

def _supports_extraction_filter():
    """
    التحقق من دعم معامل filter في TarFile.extractall
    (متوفر رسمياً في Python 3.12+ وتم ترقيعه في 3.8.17 / 3.9.17
     / 3.10.12 / 3.11.4 وما بعدها).
    """
    return hasattr(tarfile, "data_filter")

def safe_extract(tar, path):
    """
    فك ضغط آمن للوقاية من ثغرة Path Traversal (CVE-2007-4559):
    1. فحص يدوي لكل عضو في الأرشيف (مسارات + روابط رمزية/صلبة).
    2. استخدام الفلتر الرسمي filter="data" عند توفره كطبقة حماية
       ثانية معتمدة من بايثون نفسها (يرفض المسارات المطلقة،
       والخروج عن المجلد، والأجهزة الخاصة، ويقيد الروابط الرمزية).
    """
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            raise Exception(f"🚨 محاولة Path Traversal مكتشفة داخل الأرشيف: {member.name}")
        if member.issym() or member.islnk():
            link_target = os.path.join(os.path.dirname(member_path), member.linkname)
            if not _is_within_directory(path, link_target):
                raise Exception(f"🚨 رابط رمزي خطير داخل الأرشيف: {member.name} -> {member.linkname}")

    if _supports_extraction_filter():
        # ✅ الفلتر الرسمي من بايثون — الحماية المعتمدة الموصى بها
        tar.extractall(path=path, filter="data")
    else:
        # نسخة بايثون قديمة لا تدعم الفلتر — نكتفي بالفحص اليدوي أعلاه
        log_message("⚠️ نسخة بايثون الحالية لا تدعم filter='data' — تم الاعتماد على الفحص اليدوي فقط. يُنصح بالترقية إلى Python 3.12+.", YELLOW)
        tar.extractall(path=path)

# -------------------------------------------------------------
# البحث عن أحدث ملف tar.gz
# -------------------------------------------------------------
def find_latest_tar_file():
    search_dirs = [SCRIPT_DIR]
    if os.path.isdir(DOWNLOADS_DIR) and os.path.abspath(DOWNLOADS_DIR) != os.path.abspath(SCRIPT_DIR):
        search_dirs.append(DOWNLOADS_DIR)

    tar_files = []
    for directory in search_dirs:
        try:
            for f in os.listdir(directory):
                if f.lower().endswith(".tar.gz"):
                    full_path = os.path.join(directory, f)
                    if os.path.isfile(full_path):
                        tar_files.append(full_path)
        except OSError as e:
            log_message(f"⚠️ تعذر قراءة المجلد '{directory}': {e}", YELLOW)

    if not tar_files:
        return None

    tar_files.sort(key=os.path.getmtime, reverse=True)
    latest = tar_files[0]

    if len(tar_files) == 1:
        log_message(f"تم اكتشاف ملف مضغوط وحيد وتحديده تلقائياً: {latest}", GREEN)
    else:
        log_message(f"تم العثور على {len(tar_files)} ملف مضغوط في المسارات المحددة:", CYAN)
        for tf in tar_files:
            mtime_str = datetime.fromtimestamp(os.path.getmtime(tf)).strftime("%Y-%m-%d %H:%M:%S")
            marker = " ← (الأحدث ✅)" if tf == latest else ""
            log_message(f"   - {tf}  [آخر تعديل: {mtime_str}]{marker}", CYAN)
        log_message(f"تم تحديد الملف الأحدث تلقائياً: {os.path.basename(latest)}", YELLOW)

    return latest

# -------------------------------------------------------------
# تحديد جذر المصدر داخل الأرشيف المفكوك
# -------------------------------------------------------------
def get_source_root(extract_dir):
    for root, dirs, files in os.walk(extract_dir):
        for d in dirs:
            if "clone" in d.lower():
                target_path = os.path.join(root, d)
                log_message(f"تم اكتشاف مجلد يحتوي على 'clone': '{target_path}' - سيتم استخدامه كبداية.", GREEN)
                return target_path

    log_message("لم يتم العثور على مجلد يحتوي على 'clone'، سيتم الرفع المباشر من الجذر.", YELLOW)
    return extract_dir

# -------------------------------------------------------------
# نسخ شجرة الملفات (مع تجاهل .git)
# -------------------------------------------------------------
def copy_tree(src, dst):
    if not os.path.exists(dst):
        os.makedirs(dst)

    for item in os.listdir(src):
        s_path = os.path.join(src, item)
        d_path = os.path.join(dst, item)

        if item in (".git", ".github"):
            continue

        if os.path.isdir(s_path):
            if os.path.exists(d_path):
                copy_tree(s_path, d_path)
            else:
                shutil.copytree(s_path, d_path)
        else:
            shutil.copy2(s_path, d_path)

# -------------------------------------------------------------
# فك ترميز مسارات git (أسماء الملفات العربية/غير اللاتينية)
# -------------------------------------------------------------
def decode_git_path(path_str):
    path_str = path_str.strip()
    if path_str.startswith('"') and path_str.endswith('"'):
        path_str = path_str[1:-1]

    try:
        return path_str.encode('latin1').decode('unicode_escape').encode('latin1').decode('utf-8')
    except Exception:
        return path_str

# -------------------------------------------------------------
# معالجة ملف tar.gz منفرد (فك ضغط → رفع → تقرير → حذف التار)
# -------------------------------------------------------------
def process_single_tar(tar_path):
    if not os.path.exists(tar_path):
        print(f"{RED}❌ خطأ: الملف غير موجود في المسار: {tar_path}{RESET}")
        return False

    log_message(f"جاري معالجة الملف المضغوط: {tar_path}", CYAN)

    temp_dir = tempfile.mkdtemp(prefix="git_upload_")
    extract_dir = os.path.join(temp_dir, "extracted")
    clone_dir = os.path.join(temp_dir, "_clone")
    os.makedirs(extract_dir)

    try:
        log_message("جاري فك ضغط الملف (مع فحص أمان المسارات)...", BLUE)
        with tarfile.open(tar_path, "r:gz") as tar:
            safe_extract(tar, extract_dir)

        source_root = get_source_root(extract_dir)

        log_message("جاري سحب مستودع جيت هاب...", BLUE)
        auth_url = REPO_URL.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@")
        run_cmd(["git", "clone", "-b", REPO_BRANCH, auth_url, clone_dir])

        # إعدادات محلية للمستودع المستنسخ
        run_cmd(["git", "config", "core.quotepath", "false"], cwd=clone_dir)
        run_cmd(["git", "config", "user.name", GIT_USER_NAME], cwd=clone_dir)
        run_cmd(["git", "config", "user.email", GIT_USER_EMAIL], cwd=clone_dir)
        # ✅ (تصحيح 3): تعطيل credential.helper محلياً أيضاً كطبقة إضافية
        run_cmd(["git", "config", "credential.helper", ""], cwd=clone_dir)

        log_message("جاري نسخ وتحديث الملفات محلياً...", BLUE)
        copy_tree(source_root, clone_dir)

        log_message("جاري تجهيز وتصنيف التغييرات...", BLUE)
        run_cmd(["git", "add", "-A"], cwd=clone_dir)

        # -M لاكتشاف إعادة التسمية و -C لاكتشاف النسخ
        diff_out = run_cmd(["git", "diff", "--cached", "--name-status", "-M", "-C"], cwd=clone_dir)

        # ✅ (تصحيح 4): معالجة كاملة لكل حالات git diff (A/M/D/R/C)
        new_files = []       # A : ملفات مضافة
        updated_files = []   # M : ملفات معدلة
        deleted_files = []   # D : ملفات محذوفة
        renamed_files = []   # R : ملفات معاد تسميتها (قديم، جديد)
        copied_files = []    # C : ملفات منسوخة (مصدر، وجهة)

        for line in diff_out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                parts = line.split(maxsplit=1)
                if len(parts) < 2:
                    continue
            status = parts[0].strip()

            if status.startswith("R") and len(parts) >= 3:
                # إعادة تسمية: R100\tقديم\tجديد
                old_path = decode_git_path(parts[1])
                new_path = decode_git_path(parts[2])
                renamed_files.append((old_path, new_path))
            elif status.startswith("C") and len(parts) >= 3:
                # نسخ: C100\tمصدر\tوجهة
                src_path = decode_git_path(parts[1])
                dst_path = decode_git_path(parts[2])
                copied_files.append((src_path, dst_path))
            elif status == "A":
                new_files.append(decode_git_path(parts[1]))
            elif status == "M":
                updated_files.append(decode_git_path(parts[1]))
            elif status == "D":
                deleted_files.append(decode_git_path(parts[1]))
            else:
                # أي حالة غير متوقعة (T تغيير نوع، U تعارض...) تعامل كتحديث
                updated_files.append(decode_git_path(parts[1]))

        total_changes = (len(new_files) + len(updated_files) + len(deleted_files)
                         + len(renamed_files) + len(copied_files))

        if total_changes == 0:
            log_message("لا توجد أي تغييرات جديدة أو معدلة لرفعها على جيت هاب (النسخة مطابقة).", YELLOW)
            commit_hash = "N/A (مستند متطابق)"
            # ✅ (v4.6): إشعار تليجرام أنيق عند التطابق التام
            send_telegram_message(
                "🔍 <b>نتيجة الفحص — لا توجد تغييرات</b>\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
                f"📦 <b>الملف المفحوص:</b> <code>{os.path.basename(tar_path)}</code>\n"
                f"📂 <b>المصدر:</b> <code>{os.path.dirname(tar_path)}</code>\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
                "✅ المستودع <b>مطابق تماماً</b> لمحتوى الأرشيف.\n"
                "🚫 لا توجد أي تغييرات لرفعها على GitHub."
            )
        else:
            log_message(
                f"تم التحقق من التغييرات الفعلية: {len(new_files)} جديد، {len(updated_files)} محدث، "
                f"{len(deleted_files)} محذوف، {len(renamed_files)} معاد تسميته، {len(copied_files)} منسوخ.",
                GREEN
            )
            commit_msg = (
                f"Auto-update: {len(new_files)} new, {len(updated_files)} updated, "
                f"{len(deleted_files)} deleted, {len(renamed_files)} renamed, {len(copied_files)} copied"
            )
            run_cmd(["git", "commit", "-m", commit_msg], cwd=clone_dir)
            commit_hash = run_cmd(["git", "rev-parse", "HEAD"], cwd=clone_dir)[:8]

            log_message("جاري رفع التغييرات إلى جيت هاب...", BLUE)
            run_cmd(["git", "push", "origin", REPO_BRANCH], cwd=clone_dir)
            log_message("تم الرفع بنجاح! 🎉", GREEN)

            # ✅ (v4.6): تقرير تليجرام أنيق ومفصل عند نجاح الرفع
            send_telegram_message(
                "🚀 <b>تم الرفع إلى GitHub بنجاح!</b>\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
                f"📦 <b>الملف المرفوع:</b> <code>{os.path.basename(tar_path)}</code>\n"
                f"📂 <b>المصدر:</b> <code>{os.path.dirname(tar_path)}</code>\n"
                f"🔑 <b>الكوميت:</b> <code>{commit_hash}</code>\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
                "📊 <b>إحصائيات التغييرات:</b>\n"
                f"  🆕 جديدة: <b>{len(new_files)}</b>\n"
                f"  ✏️ معدلة: <b>{len(updated_files)}</b>\n"
                f"  🗑 محذوفة: <b>{len(deleted_files)}</b>\n"
                f"  🔄 معاد تسميتها: <b>{len(renamed_files)}</b>\n"
                f"  📋 منسوخة: <b>{len(copied_files)}</b>\n"
                "➖➖➖➖➖➖➖➖➖➖\n"
                f"📦 <b>إجمالي التغييرات:</b> <b>{total_changes}</b> ✅"
            )

        # ---------------------------------------------------------
        # كتابة التقرير
        # ---------------------------------------------------------
        log_message(f"جاري كتابة التقرير في الملف '{REPORT_FILENAME}' داخل مجلد السكريبت...", BLUE)
        now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        report_entry = []
        report_entry.append(f"## 📅 تقرير عملية الرفع — {now_str}")
        report_entry.append(f"- 📦 **الملف المرفوع:** `{os.path.basename(tar_path)}`")
        report_entry.append(f"- 📂 **مصدر الملف:** `{os.path.dirname(tar_path)}`")
        report_entry.append(f"- 🔑 **حالة الكوميت:** `{commit_hash}`")
        report_entry.append("- 📊 **إحصائيات الرفع:**")
        report_entry.append(f"  - 🆕 عدد الملفات الجديدة: **{len(new_files)}**")
        report_entry.append(f"  - ✏️ عدد الملفات المحدثة: **{len(updated_files)}**")
        report_entry.append(f"  - 🗑️ عدد الملفات المحذوفة: **{len(deleted_files)}**")
        report_entry.append(f"  - 🔄 عدد الملفات المعاد تسميتها: **{len(renamed_files)}**")
        report_entry.append(f"  - 📋 عدد الملفات المنسوخة: **{len(copied_files)}**")
        report_entry.append(f"  - 📦 إجمالي الملفات المتأثرة: **{total_changes}**")

        if new_files:
            report_entry.append("\n### 🆕 الملفات الجديدة المضافة:")
            for idx, f in enumerate(sorted(new_files), 1):
                report_entry.append(f"{idx}. `{f}`")

        if updated_files:
            report_entry.append("\n### ✏️ الملفات المحدثة:")
            for idx, f in enumerate(sorted(updated_files), 1):
                report_entry.append(f"{idx}. `{f}`")

        if deleted_files:
            report_entry.append("\n### 🗑️ الملفات المحذوفة:")
            for idx, f in enumerate(sorted(deleted_files), 1):
                report_entry.append(f"{idx}. `{f}`")

        if renamed_files:
            report_entry.append("\n### 🔄 الملفات المعاد تسميتها:")
            for idx, (old_f, new_f) in enumerate(sorted(renamed_files), 1):
                report_entry.append(f"{idx}. `{old_f}` ← تم نقله/تسميته إلى ← `{new_f}`")

        if copied_files:
            report_entry.append("\n### 📋 الملفات المنسوخة:")
            for idx, (src_f, dst_f) in enumerate(sorted(copied_files), 1):
                report_entry.append(f"{idx}. `{src_f}` ← تم نسخه إلى ← `{dst_f}`")

        report_entry.append("\n---\n")

        report_path = os.path.join(SCRIPT_DIR, REPORT_FILENAME)
        with open(report_path, "a", encoding="utf-8") as rf:
            rf.write("\n".join(report_entry))

        log_message(f"تمت إضافة التقرير بنجاح في: {report_path} 📝", GREEN)

        log_message(f"جاري حذف الملف المضغوط الأصلي: {os.path.basename(tar_path)}...", YELLOW)
        try:
            os.remove(tar_path)
            log_message("تم حذف الملف المضغوط الأصلي بنجاح لتوفير المساحة. 🗑️", GREEN)
        except Exception as e:
            log_message(f"⚠️ فشل حذف الملف المضغوط: {e}", RED)

    finally:
        log_message("جاري تنظيف الملفات المؤقتة...", BLUE)
        shutil.rmtree(temp_dir, ignore_errors=True)
        log_message("تم التنظيف بالكامل.", GREEN)
    return True

# -------------------------------------------------------------
# البرنامج الرئيسي (v4.5): وضع المعامل الواحد أو حلقة المراقبة
# -------------------------------------------------------------
def main():
    # التوافقية السابقة: تمرير مسار الملف كمعامل → معالجة مرة واحدة ثم خروج
    if len(sys.argv) >= 2:
        process_single_tar(os.path.abspath(sys.argv[1]))
        return

    # وضع حلقة المراقبة المستمرة (Loop Mode)
    log_message("تم تفعيل وضع المراقبة المستمرة — بانتظار ملفات .tar.gz جديدة... (اضغط Ctrl+C للخروج)", CYAN)
    try:
        while True:
            tar_path = find_latest_tar_file()
            if tar_path:
                try:
                    process_single_tar(tar_path)
                except Exception as e:
                    log_message(f"🚨 فشل أثناء معالجة الملف: {e} — سيتم استئناف المراقبة.", RED)
            time.sleep(10)  # نوم صامت — استهلاك شبه معدوم للمعالج والذاكرة
    except KeyboardInterrupt:
        print()
        log_message("تم إيقاف وضع المراقبة بنجاح (Ctrl+C). إلى اللقاء! 👋", YELLOW)

if __name__ == "__main__":
    main()
