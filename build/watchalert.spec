# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: один файл, Linux / Windows."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("WATCHALERT_ROOT", Path(SPECPATH).parent.parent)).resolve()

a = Analysis(
    [str(ROOT / "watchalert_onefile.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PIL._tkinter_finder",
        "mss",
        "mss.linux",
        "mss.windows",
        "pygame",
        "pygame.mixer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WatchAlert",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
