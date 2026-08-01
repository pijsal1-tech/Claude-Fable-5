# -*- coding: utf-8 -*-
"""
===============================================================================
🐛 [TSK-501 / FIX-01-A] Reference Patch Code for ChatDispatch Workspace Path Detection
===============================================================================
This file contains the BEFORE (Problematic) and PROPOSED AFTER (Fixed) code
implementations for inspecting workspace directory paths in core/chat_dispatch.py.
===============================================================================
"""

import os
from pathlib import Path

# =============================================================================
# 🟢 PROPOSED AFTER: Smart Workspace Path Policy Helpers
# =============================================================================

def is_root_or_system_dir(p: Path) -> bool:
    """
    فحص ما إذا كان المسار هو جذر محرك مثل C:\\ أو D:\\ أو مجلد نظام حساس
    """
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
    فحص التبعية لشجرة المشروع المفتوح حالياً مع تجنب Substring Traps 
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
    except Exception:
        # عند أي استثناء في الفحص → افترض غير مرتبط كأمان
        return False

# =============================================================================
# 🔴 BEFORE vs 🟢 PROPOSED AFTER Integration Logic in ChatDispatch
# =============================================================================

"""
--- 🔴 BEFORE ---
# 1. Regex containing space that truncates Windows paths to drive root D:\:
win_paths = re.findall(r'[A-Za-z]:[\\/ ][^\s,;"\'>]+', user_text)

# 2. Blindly prompting user without workspace containment check:
if detected_dir and not skip_path_detection:
    if user_text.strip() == detected_dir:
        ...
        return
    req_id = msg.get("request_id") or str(uuid.uuid4())
    deps.store_pending_path_request(req_id, {...})
    sctx.send({
        "type": "path_detected_options",
        "request_id": req_id,
        "path": detected_dir
    })
    return

--- 🟢 PROPOSED AFTER ---
# 1. Skip text path scan if explicit attachments are present
if (msg.get("attachments") or msg.get("from_attachment")) and not skip_path_detection:
    skip_path_detection = True

# 2. Fixed Windows path Regex (without space character)
win_paths = re.findall(r'[A-Za-z]:[\\/][^\s,;"\'>]+', user_text)

# 3. Workspace containment check before dispatching option card
if detected_dir and not skip_path_detection:
    current_project_root = getattr(sctx.fm, "root", "")
    if is_related_to_workspace(detected_dir, current_project_root):
        pass  # Suppress card silently (user is already working inside/related to this workspace)
    else:
        req_id = msg.get("request_id") or str(uuid.uuid4())
        deps.store_pending_path_request(req_id, {...})
        sctx.send({
            "type": "path_detected_options",
            "request_id": req_id,
            "path": detected_dir
        })
        return
"""
