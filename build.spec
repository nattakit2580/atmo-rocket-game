# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

datas = []
datas += collect_data_files("mediapipe")
datas += [("models/pose_landmarker_lite.task", "models")]

hiddenimports = []
hiddenimports += collect_submodules("mediapipe")

binaries = []
binaries += collect_dynamic_libs("mediapipe")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AtmoRocketGame",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
