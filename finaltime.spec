# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Получаем путь к проекту
PROJECT_DIR = Path.cwd()

# Добавляем путь для импорта версии
sys.path.insert(0, str(PROJECT_DIR))
from finaltime.version import VERSION

APP_NAME = f"FinalTime_v{VERSION}"
ICON_PATH = str(PROJECT_DIR / "finaltime" / "assets" / "icon.ico")

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[
        ('version.txt', '.'),
        ('finaltime/assets/icon.ico', 'assets'),
        ('finaltime/assets/manual.pdf', 'assets'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'openpyxl',
        'dateutil',
        'dateutil.parser',
        'dateutil.tz',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=ICON_PATH,
    codesign_identity=None,
    entitlements_file=None,
)
