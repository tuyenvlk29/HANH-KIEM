# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('quy_tac/TIEU_CHI_HANH_KIEM.xlsx', 'quy_tac'),
        ('app/convert_legacy_doc.ps1', 'app'),
        ('app/convert_legacy_xls.ps1', 'app'),
        ('app/license_client.py', 'app'),
        ('app/license_ui.py', 'app'),
        ('.env', '.'),
    ],
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
    name='HeThong_HanhKiem_RenLuyen_TuyenBui',
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
