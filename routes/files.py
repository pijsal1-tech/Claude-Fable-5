"""routes/files.py — TSK-613 (ADR-003): blueprint الملفات والمجلدات والبحث.

أجسام الدوال منقولة **حرفيًا** من server.py؛ حالة الخادم تُقرأ
حيًّا عبر ``_srv`` (كائن وحدة server يُحقن في ``register()``) —
نفس دلالة globals الأصلية (late binding، نمط ADR-002).
"""
from flask import Blueprint, jsonify, request
import os

bp = Blueprint("files", __name__)
_srv = None  # كائن وحدة server — يُحقن عند register() (ADR-003)


def register(app, srv):
    """يحقن كائن وحدة server ويسجّل الـ blueprint على التطبيق."""
    global _srv
    _srv = srv
    app.register_blueprint(bp)


@bp.route("/api/files")
def api_files():
    """قائمة ملفات المشروع"""
    try:
        scan = _srv.fm.scan_project(max_files=10000)
        tree = _srv.fm.get_project_tree(max_depth=4)
        return jsonify({"ok": True, "scan": scan, "tree": tree})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/search")
def api_search():
    """البحث الشامل في ملفات المشروع ومحتوياتها.

    TSK-501 (NF-20): كان ينفّذ ``scan_project(max_files=10000)`` ثم يقرأ
    محتوى كل ملف نصي تسلسليًا لكل ضغطة بحث. الآن يمر عبر
    ``SearchService`` (context/search.py) فوق ProjectIndex — صفر مشيات
    شجرية + كاش محتوى بمفتاح mtime — مع نفس عقد النتائج حرفيًا
    (أشكال file/content، سقوف 25/20/35، بوابة len(q)>=2، فلاتر
    scan_project القديمة والترتيب العالمي المفروز) — بوابة QA-T13.
    """
    from actions.file_manager import MAX_FILE_SIZE, WEB_EXTENSIONS
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": True, "results": []})

    try:
        svc = _srv._search_service()
        text_exts = {'.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.json', '.md', '.yaml', '.yml', '.txt', '.sh', '.c', '.cpp', '.h', '.cs', '.php', '.go', '.rs'}
        results = svc.search_project(
            q,
            walk_exts=WEB_EXTENSIONS,
            max_size=MAX_FILE_SIZE,
            content_exts=text_exts,
            name_limit=25,
            content_gate=20,
            total_limit=35,
            max_files=10000,
        )
        return jsonify({"ok": True, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/file/<path:filepath>")
def api_read_file(filepath):
    """قراءة محتوى ملف"""
    try:
        content = _srv.fm.read_file(filepath, with_line_numbers=False)
        content_numbered = _srv.fm.read_file(filepath, with_line_numbers=True)
        return jsonify({
            "ok": True,
            "path": filepath,
            "content": content,
            "content_numbered": content_numbered,
            "lines": len(content.splitlines())
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 404


@bp.route("/api/folder/<path:folderpath>")
def api_read_folder(folderpath):
    """قراءة محتوى مجلد كامل — للـ drag and drop"""
    try:
        from chain.bridge import scan_folder_for_chain
        full_path = _srv.fm._resolve(folderpath)
        if not os.path.isdir(str(full_path)):
            return jsonify({"ok": False, "error": "ليس مجلداً"}), 404
        files = scan_folder_for_chain(str(full_path))
        return jsonify({
            "ok": True,
            "path": folderpath,
            "files": files,
            "count": len(files),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/file/<path:filepath>", methods=["POST"])
def api_write_file(filepath):
    """كتابة/تعديل ملف"""
    data = request.get_json()
    content = data.get("content", "")
    try:
        saved_path = _srv.fm.write_file(filepath, content)
        return jsonify({"ok": True, "path": saved_path})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/file/<path:filepath>", methods=["DELETE"])
def api_delete_file(filepath):
    """حذف ملف (مع backup)"""
    try:
        full = _srv.fm._resolve(filepath)
        if full.exists():
            _srv.fm.create_backup(filepath)
            full.unlink()
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "ملف غير موجود"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/new-file", methods=["POST"])
def api_new_file():
    """إنشاء ملف جديد فارغ"""
    data = request.get_json()
    filepath = data.get("path", "").strip()
    content = data.get("content", "")
    if not filepath:
        return jsonify({"ok": False, "error": "اسم الملف مطلوب"}), 400
    try:
        saved = _srv.fm.write_file(filepath, content, backup=False)
        return jsonify({"ok": True, "path": saved})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/new-folder", methods=["POST"])
def api_new_folder():
    """إنشاء مجلد جديد"""
    data = request.get_json()
    folder_name = data.get("path", "").strip()
    if not folder_name:
        return jsonify({"ok": False, "error": "اسم المجلد مطلوب"}), 400
    try:
        full = _srv.fm._resolve(folder_name)
        full.mkdir(parents=True, exist_ok=True)
        return jsonify({"ok": True, "path": folder_name})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
