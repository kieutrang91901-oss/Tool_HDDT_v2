# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec — Đóng gói Tool HDDT v2 thành 1 file EXE.

Sử dụng: pyinstaller hddt_v2.spec
"""

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bao gồm customtkinter theme files
        # ('path/to/customtkinter', 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'tksheet',
        'PIL',
        'PIL._tkinter_finder',
        'httpx',
        'httpx._transports',
        'httpx._transports.default',
        'lxml',
        'lxml.etree',
        'openpyxl',
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'pytest', 'unittest', 'doctest',
        'tkinter.test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Thêm customtkinter data
import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)
a.datas += Tree(ctk_path, prefix='customtkinter', excludes=['*.pyc'])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HDDT_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Ẩn console khi chạy
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # Thêm icon khi có
)
