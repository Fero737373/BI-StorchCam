# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
web = root / "bi_storchcam" / "web"
datas = [
    (str(web / "index.html"), "bi_storchcam/web"),
    (str(web / "style.css"), "bi_storchcam/web"),
    (str(web / "bluetooth.css"), "bi_storchcam/web"),
    (str(web / "app.js"), "bi_storchcam/web"),
    (str(web / "console.js"), "bi_storchcam/web"),
]

analysis = Analysis(
    [str(root / "launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="BI-StorchCam",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
