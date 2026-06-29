# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('C:\\Users\\corncake\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\DLLs\\tcl86t.dll', '.'), ('C:\\Users\\corncake\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\DLLs\\tk86t.dll', '.'), ('C:\\Users\\corncake\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\DLLs\\_tkinter.pyd', '.')],
    datas=[('C:\\Users\\corncake\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\Lib\\tkinter', 'tkinter'), ('C:\\Users\\corncake\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\tcl\\tcl8.6', '_tcl_data'), ('C:\\Users\\corncake\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\tcl\\tk8.6', '_tk_data'), ('deploy_assets\\config.ini', '.'), ('template.xlsx', '.'), ('template_clean.xlsx', '.'), ('template_new.xlsx', '.'), ('template_nj.xlsx', '.'), ('templates', 'templates'), ('mappings', 'mappings')],
    hiddenimports=['_tkinter'],
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
    [],
    exclude_binaries=True,
    name='JL_Registry_Auto_Debug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JL_Registry_Auto_Debug',
)
