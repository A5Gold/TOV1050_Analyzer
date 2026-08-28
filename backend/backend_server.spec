# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for TOV640 Analyzer Backend Server
"""

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Get the backend directory path
BACKEND_DIR = os.path.dirname(os.path.abspath(SPECPATH))

# Collect submodules
uvicorn_imports = collect_submodules('uvicorn')
starlette_imports = collect_submodules('starlette')
fastapi_imports = collect_submodules('fastapi')
pydantic_imports = collect_submodules('pydantic')

block_cipher = None

a = Analysis(
    ['app/main.py'],
    pathex=[BACKEND_DIR],  # Add backend directory to path
    binaries=[],
    datas=[
        ('app', 'app'),  # Include the entire app package
        # REMOVED: ('../config', 'config') - config now in resources/config/ managed by Electron
    ],
    hiddenimports=[
        # App modules
        'app',
        'app.main',
        'app.api',
        'app.api.endpoints',
        'app.api.endpoints.analysis',
        'app.api.endpoints.metadata',
        'app.core',
        'app.core.config',
        'app.core.analyzers',
        'app.core.data_ingestion',
        'app.core.exporter',
        'app.core.metadata',
        'app.core.metadata_service',
        'app.core.repeated_finder',
        # Uvicorn
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
        # Data processing
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'openpyxl',
        'numpy',
        'intervaltree',
    ] + uvicorn_imports + starlette_imports + fastapi_imports + pydantic_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name='backend_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Show console for debugging
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
    upx=True,
    upx_exclude=[],
    name='backend_server',
)
