#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
init_root.py — إنشاء مجلد Root/ لأي مشروع جديد
الاستخدام:
    python .agents/tools/init_root.py --project "اسم المشروع" --desc "وصف المشروع"
    python .agents/tools/init_root.py --project nexus --desc "Nexus AI Orchestrator"
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent  # d:\SMS\.hRhRhRhRhRhR\

def create_root(project_name: str, description: str, tech_stack: str = "Python"):
    project_path = WORKSPACE / project_name
    root_path = project_path / "Root"

    if not project_path.exists():
        print(f"❌ المجلد {project_path} مش موجود!")
        return False

    if root_path.exists():
        print(f"⚠️ Root/ موجود بالفعل في {project_name}")
        answer = input("   هل تريد الكتابة فوقه؟ (y/n): ").strip().lower()
        if answer != "y":
            print("   تم الإلغاء.")
            return False

    root_path.mkdir(exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")

    # ── ai_state.json ──────────────────────────────────────────
    ai_state = {
        "project": project_name,
        "description": description,
        "tech_stack": tech_stack,
        "current_tag": "[READING]",
        "CURRENT_PHASE": "Phase 0 — Setup",
        "PROGRESS": "0%",
        "CURRENT_BLOCKER": "",
        "NEXT_ACTION": "اقرأ README.md وابدأ",
        "LATEST_WINS": [],
        "last_action": "تم إنشاء Root/",
        "last_message_summary": "session جديدة",
        "last_updated": now
    }
    (root_path / "ai_state.json").write_text(
        json.dumps(ai_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── tasks.md ────────────────────────────────────────────────
    (root_path / "tasks.md").write_text(f"""# 📋 المهام — {project_name}

## ✅ المهام المنجزة
- [x] إنشاء مجلد Root/

## 🔄 المهام الجارية
- [ ] قراءة README.md وفهم المشروع

## 📋 المهام القادمة
<!-- أضف المهام هنا -->
""", encoding="utf-8")

    # ── memory.md ───────────────────────────────────────────────
    (root_path / "memory.md").write_text(f"""# 🧠 الذاكرة الحية — {project_name}

## 📌 الحقائق الأساسية
- **الهدف:** {description}
- **التكنولوجيا:** {tech_stack}

---

## 🔓 اكتشافات مهمة
<!-- أضف هنا الاكتشافات المؤكدة بدليل -->

---

## ❌ محاولات فاشلة (لا تكررها!)
<!-- أضف هنا اللي جربته وفشل -->

---

## 💡 دروس مستفادة
<!-- أضف هنا الدروس -->
""", encoding="utf-8")

    # ── decisions.md ────────────────────────────────────────────
    (root_path / "decisions.md").write_text(f"""# 📝 القرارات المعمارية — {project_name}

| # | القرار | السبب | البديل المرفوض |
|---|--------|-------|----------------|
| DEC-001 | | | |
""", encoding="utf-8")

    # ── SESSION_LOG.md ──────────────────────────────────────────
    (root_path / "SESSION_LOG.md").write_text(f"""# 📜 Session Log — {project_name}

## Session الأولى ({now[:10]})
- تم إنشاء Root/ للمشروع
""", encoding="utf-8")

    # ── AGENTS.md (pointer) ─────────────────────────────────────
    (root_path / "AGENTS.md").write_text(f"""> ⭐ **القواعد الكاملة في:** `.agents/AGENTS.md` — المرجع الموحد
> **اقرأه أول كل session**

---

## 📁 ملفات هذا المشروع (Root/)

| الملف | الوظيفة |
|-------|---------|
| `ai_state.json` | ⭐ حالة المشروع — يتحدث بعد كل رسالة |
| `tasks.md` | المهام (✅ / 🔄 / 📋) |
| `memory.md` | الذاكرة الحية — اكتشافات + حقائق |
| `decisions.md` | القرارات المعمارية (ADRs) |
| `SESSION_LOG.md` | سجل الجلسات |

---

## 📌 معلومات المشروع
- **الاسم:** {project_name}
- **الهدف:** {description}
- **التقنية:** {tech_stack}
""", encoding="utf-8")

    print(f"\n✅ تم إنشاء Root/ لمشروع: {project_name}")
    print(f"   المسار: {root_path}")
    print(f"   الملفات: ai_state.json, tasks.md, memory.md, decisions.md, SESSION_LOG.md, AGENTS.md")
    return True


def validate_root(project_name: str):
    """تحقق إن Root/ فيه الملفات الأساسية"""
    root_path = WORKSPACE / project_name / "Root"
    required = ["ai_state.json", "tasks.md", "memory.md", "decisions.md", "SESSION_LOG.md", "AGENTS.md"]
    
    print(f"\n🔍 فحص Root/ في: {project_name}")
    all_ok = True
    for f in required:
        exists = (root_path / f).exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {f}")
        if not exists:
            all_ok = False
    
    if all_ok:
        print("   ✅ كل الملفات موجودة!")
    else:
        print("   ❌ فيه ملفات ناقصة — شغّل init_root لإنشاءها")
    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="إنشاء Root/ لمشروع جديد")
    parser.add_argument("--project", required=True, help="اسم مجلد المشروع")
    parser.add_argument("--desc", default="مشروع جديد", help="وصف المشروع")
    parser.add_argument("--tech", default="Python", help="التكنولوجيا المستخدمة")
    parser.add_argument("--validate", action="store_true", help="فحص Root/ فقط بدون إنشاء")
    args = parser.parse_args()

    if args.validate:
        validate_root(args.project)
    else:
        create_root(args.project, args.desc, args.tech)
