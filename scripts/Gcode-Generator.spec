# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\farno\\OneDrive\\Documents\\GitHub\\Gcode-Generator\\GUI.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\farno\\OneDrive\\Documents\\GitHub\\Gcode-Generator\\images', 'images'), ('C:\\Users\\farno\\OneDrive\\Documents\\GitHub\\Gcode-Generator\\translations.json', '.'), ('C:\\Users\\farno\\OneDrive\\Documents\\GitHub\\Gcode-Generator\\config.json', '.')],
    hiddenimports=[],
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
    name='Gcode-Generator',
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
