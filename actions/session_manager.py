# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  SessionManager — حفظ واستعادة جلسات المحادثة
  حفظ فوري incremental مع حماية من الصدمات
═══════════════════════════════════════════════════════
"""
import os
import json
import uuid
import pathlib
from datetime import datetime, timedelta



class SessionManager:
    """مدير جلسات المحادثة — حفظ تلقائي فوري واستعادة"""

    def __init__(self, sessions_dir: str, max_age_days: int = 30):
        self.sessions_dir = pathlib.Path(sessions_dir).resolve()
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_days = max_age_days
        self.current_session_id = None
        self._current_path = None

    # ════════════════════════════════════════════
    # إنشاء جلسة جديدة
    # ════════════════════════════════════════════
    def new_session(self, project_path: str = "") -> dict:
        """بدء جلسة جديدة"""
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        session = {
            "id": session_id,
            "project_path": project_path,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "title": "",  # يتحدد لاحقاً من أول رسالة
        }

        self.current_session_id = session_id
        self._current_path = self.sessions_dir / f"{session_id}.json"
        self._save_full(session)
        self._cleanup_old()

        return session

    # ════════════════════════════════════════════
    # إضافة رسالة (حفظ فوري)
    # ════════════════════════════════════════════
    def append_message(self, role: str, content: str) -> None:
        """إضافة رسالة وحفظها فوراً (crash-safe)"""
        if not self.current_session_id or not self._current_path:
            return

        session = self._load(self._current_path)
        if not session:
            return

        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        session["updated_at"] = datetime.now().isoformat()

        # تحديد عنوان الجلسة من أول رسالة user
        if not session["title"] and role == "user":
            session["title"] = content[:60].strip()
            if len(content) > 60:
                session["title"] += "..."

        self._save_full(session)

    # ════════════════════════════════════════════
    # تحميل جلسة
    # ════════════════════════════════════════════
    def load_session(self, session_id: str) -> dict | None:
        """تحميل جلسة بالـ ID"""
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None

        session = self._load(path)
        if session:
            self.current_session_id = session_id
            self._current_path = path
        return session

    # ════════════════════════════════════════════
    # قائمة الجلسات
    # ════════════════════════════════════════════
    def list_sessions(self) -> list[dict]:
        """قائمة كل الجلسات (مرتبة من الأحدث للأقدم)"""
        sessions = []
        for f in self.sessions_dir.glob("*.json"):
            try:
                data = self._load(f)
                if data:
                    sessions.append({
                        "id": data["id"],
                        "title": data.get("title", "محادثة بدون عنوان"),
                        "project_path": data.get("project_path", ""),
                        "message_count": len(data.get("messages", [])),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                    })
            except Exception:
                continue

        # ترتيب من الأحدث للأقدم
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions

    # ════════════════════════════════════════════
    # حذف جلسة
    # ════════════════════════════════════════════
    def delete_session(self, session_id: str) -> bool:
        """حذف جلسة"""
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            if self.current_session_id == session_id:
                self.current_session_id = None
                self._current_path = None
            return True
        return False

    # ════════════════════════════════════════════
    # تحديث مسار المشروع
    # ════════════════════════════════════════════
    def update_project_path(self, project_path: str) -> None:
        """تحديث مسار المشروع في الجلسة الحالية"""
        if not self._current_path or not self._current_path.exists():
            return
        session = self._load(self._current_path)
        if session:
            session["project_path"] = project_path
            self._save_full(session)

    # ════════════════════════════════════════════
    # الحصول على رسائل الجلسة الحالية
    # ════════════════════════════════════════════
    def get_current_messages(self) -> list[dict]:
        """إرجاع رسائل الجلسة الحالية"""
        if not self._current_path or not self._current_path.exists():
            return []
        session = self._load(self._current_path)
        return session.get("messages", []) if session else []

    # ════════════════════════════════════════════
    # أدوات داخلية
    # ════════════════════════════════════════════
    def _save_full(self, session: dict) -> None:
        """حفظ آمن مع fsync (مضاد للصدمات)"""
        path = self.sessions_dir / f"{session['id']}.json"
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise

    def _load(self, path: pathlib.Path) -> dict | None:
        """تحميل ملف JSON"""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _cleanup_old(self) -> None:
        """حذف الجلسات الأقدم من max_age_days"""
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        for f in self.sessions_dir.glob("*.json"):
            try:
                data = self._load(f)
                if data:
                    updated = datetime.fromisoformat(data.get("updated_at", ""))
                    if updated < cutoff:
                        f.unlink()
            except Exception:
                continue
