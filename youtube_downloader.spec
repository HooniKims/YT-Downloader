# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files


customtkinter_datas = collect_data_files('customtkinter')


a = Analysis(
    ['youtube_downloader.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ffmpeg.exe', '.'),
        ('ffprobe.exe', '.'),
        ('youricon.ico', '.'),
        ('fonts/Paperlogy-4Regular.ttf', 'fonts'),
        ('fonts/Paperlogy-6SemiBold.ttf', 'fonts'),
    ] + customtkinter_datas,
    hiddenimports=['yt_dlp', 'PIL', 'PIL.Image', 'PIL.ImageTk', 'customtkinter'],
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
    name='youtube_downloader',
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
    icon=['youricon.ico'],
)
