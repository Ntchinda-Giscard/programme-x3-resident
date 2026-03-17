# -*- mode: python ; coding: utf-8 -*-

# --- API Analysis ---
api_a = Analysis(
    ['api.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'sqlalchemy.ext.baked',
        'pyodbc'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

api_pyz = PYZ(api_a.pure)

api_exe = EXE(
    api_pyz,
    api_a.scripts,
    [],
    exclude_binaries=True,
    name='api',
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

# --- Service Analysis ---
svc_a = Analysis(
    ['src/windowsService/service.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/windowsService/service.py', 'src/windowsService'),
        ('src/windowsService/scheduler.py', 'src/windowsService'),
    ],
    hiddenimports=[
        'win32serviceutil',
        'win32service',
        'win32timezone',
        'pywintypes',
        'win32net',
        'win32netcon',
        'win32api',
        'sqlite3',
        'pyodbc',
        'smtplib'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

svc_pyz = PYZ(svc_a.pure)

svc_exe = EXE(
    svc_pyz,
    svc_a.scripts,
    [],
    exclude_binaries=True,
    name='wazapos_service',
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
    api_exe,
    api_a.binaries,
    api_a.datas,
    svc_exe,
    svc_a.binaries,
    svc_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='api',
)
