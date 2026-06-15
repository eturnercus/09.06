# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: один файл, Linux / Windows."""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


def _find_root() -> Path:
    env = os.environ.get("WATCHALERT_ROOT", "").strip()
    candidates = [
        Path(env) if env else None,
        Path(SPECPATH).resolve().parent.parent,
        Path.cwd(),
    ]
    for p in candidates:
        if p and (p / "watchalert_onefile.py").is_file():
            return p.resolve()
    return Path.cwd().resolve()


ROOT = _find_root()

hiddenimports = collect_submodules("mss") + collect_submodules("jeepney") + [
    "PIL._tkinter_finder",
    "pygame",
    "pygame.mixer",
    "watchalert",
    "watchalert.app",
    "watchalert.audio",
    "watchalert.brand",
    "watchalert.capture_backends",
    "watchalert.capture_env",
    "watchalert.capture_portal",
    "watchalert.main",
    "watchalert.monitor",
    "watchalert.region",
    "watchalert.runtime_check",
    "watchalert.screen_capture",
    "watchalert.selector",
]

datas = collect_data_files("pygame")

# Tcl/Tk — обязательно для tkinter в one-file сборке.
try:
    import tkinter as _tk

    _root = _tk.Tk()
    _root.withdraw()
    tcl_dir = _root.tk.eval("info library")
    tk_dir = _root.tk.eval("set tk_library")
    _root.destroy()
    datas += [(tcl_dir, "tcl"), (tk_dir, "tk")]
except Exception:
    pass

a = Analysis(
    [str(ROOT / "watchalert_onefile.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    upx=not sys.platform.startswith("win"),
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
