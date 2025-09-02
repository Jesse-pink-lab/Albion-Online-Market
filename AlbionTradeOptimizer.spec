# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Add project root to path
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[('resources/windows/albiondata-client.exe', 'resources/windows')],
    datas=[
        ('config.yaml', '.'),
        ('recipes/*.json', 'recipes'),
        ('README.md', '.'),
        ('engine/config_schema.yaml', 'engine'),
        ('bin/uploader-windows.exe', 'bin'),
        ('bin/uploader-linux', 'bin'),
        ('bin/uploader-macos', 'bin'),
        ('bin/LICENSE.txt', 'bin'),
        ('bin/LICENSE.albiondata-client.txt', 'resources/windows'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.pool',
        'yaml',
        'requests',
        'pandas',
        'numpy',
        'jinja2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pytest',
    ],
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
    name='AlbionTradeOptimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    versrsrc='version_info.txt',
    icon=None,
)
