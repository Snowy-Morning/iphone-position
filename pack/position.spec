# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
root = Path(SPECPATH).parent
src = root / "src"

datas = []
datas += collect_data_files("customtkinter")
datas += collect_data_files("tkintermapview")

a = Analysis(
    [str(src / "app.py")],
    pathex=[str(src)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "tkintermapview",
        "PIL",
        "PIL._tkinter_finder",
        "PIL.ImageTk",
        "geocoding",
        "gpx_utils",
        "ddi_cache",
        "config",
        "location_service",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(root / "pack" / "runtime_hook.py")],
    excludes=[],
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
    name="PositionTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
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
    name="PositionTool",
)
