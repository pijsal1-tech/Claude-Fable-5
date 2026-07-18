# -*- coding: utf-8 -*-
"""StructureSource (R-201 / T-019): بنية المشروع كسياق.

يعوّض السطر ``project_context = fm.get_project_context()`` في كتلة
legacy — نفس المخرجات حرفيًا (يفوّض لـ ``FileManager.get_project_context``
الذي تثبّته goldens T-017 في الحقل ``project_context``).

عنصر واحد بمسار رمزي ``<project_structure>`` ومحتواه النص الكامل؛
فشل البناء = عنصر بمحتوى ``""`` (نفس تسامح legacy: سلسلة فارغة).
"""
from __future__ import annotations

from actions.file_manager import FileManager
from context.engine import ContextItem, ContextRequest, ProjectScan

STRUCTURE_PATH = "<project_structure>"


class StructureSource:
    """مصدر بنية المشروع — عنصر واحد بملخص get_project_context()."""

    kind = "structure"

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        try:
            summary = FileManager(str(scan.root)).get_project_context()
        except Exception:
            summary = ""
        return [ContextItem(source_kind=self.kind, path=STRUCTURE_PATH,
                            content=summary)]
