# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Automatické posbírání všeho pro problematické knihovny
datas_ctk, binaries_ctk, hidden_ctk = collect_all('customtkinter')
datas_pd, binaries_pd, hidden_pd = collect_all('pandas')

block_cipher = None

a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=binaries_ctk + binaries_pd,
    datas=[('data/lol_draft.db', 'data')] + datas_ctk + datas_pd,
    hiddenimports=hidden_ctk + hidden_pd + ['PIL.ImageResampling'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DraftAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # Necháme True pro ladění chyb
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_architecture=None,
    codesign_identity=None,
    entitlements_file=None,
)