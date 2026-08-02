# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Получаем путь к проекту
PROJECT_DIR = Path.cwd()

# Добавляем путь для импорта версии
sys.path.insert(0, str(PROJECT_DIR))
from chronojudge.version import VERSION

APP_NAME = f"ChronoJudge_v{VERSION}"

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[
        ('version.txt', '.'),
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
    strip=False,        # strip недоступен в окружении
    upx=False,          # upx недоступен в окружении
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # окно без консоли (GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon не указываем - используем стандартную
)