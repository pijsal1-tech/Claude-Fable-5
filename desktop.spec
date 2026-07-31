# -*- mode: python ; coding: utf-8 -*-
# desktop.spec — تغليف PyInstaller لوضع سطح المكتب (TSK-727c — ADR-006)
#
# البناء على Windows (بيد المالك — الخطوات الكاملة في
# docs/desktop/WINDOWS_BUILD.md):
#   pip install -r requirements.txt pywebview pyinstaller
#   pyinstaller desktop.spec
# الناتج: dist/WebDevAIEditor/WebDevAIEditor.exe

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# بيانات التطبيق التي يقرأها الخادم وقت التشغيل نسبةً إلى _DIR:
# static/ (الواجهة كاملة بما فيها themes/ + js/app/ المقاطع)،
# agents_rules/ (تعريفات الوكلاء YAML)، config.yaml (الإعدادات).
datas = [
    ("static", "static"),
    ("agents_rules", "agents_rules"),
    ("config.yaml", "."),
]

# flask-sock/simple-websocket تُحمَّل ديناميكيًا جزئيًا — نجمعها صراحة.
hiddenimports = (
    collect_submodules("flask_sock")
    + collect_submodules("simple_websocket")
    + collect_submodules("yaml")
)

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WebDevAIEditor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,   # نافذة WebView بلا كونسول؛ اجعلها True لتشخيص الإقلاع
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="WebDevAIEditor",
)
