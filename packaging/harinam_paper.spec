# Run from project root:
# .\.venv\Scripts\python.exe -m PyInstaller packaging\harinam_paper.spec --clean --noconfirm
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


block_cipher = None
project_root = Path(SPECPATH).parent

hiddenimports = (
    collect_submodules("harinam_paper")
    + collect_submodules("core")
    + collect_submodules("job_entry")
    + [
        "whitenoise",
        "whitenoise.middleware",
        "whitenoise.storage",
        "waitress",
        "webview",
    ]
)

a = Analysis(
    [str(project_root / "start_desktop.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "core" / "templates"), "core/templates"),
        (str(project_root / "job_entry" / "templates"), "job_entry/templates"),
        (str(project_root / "staticfiles"), "staticfiles"),
    ],
    hiddenimports=hiddenimports,
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
    name="HarinamPaper",
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
