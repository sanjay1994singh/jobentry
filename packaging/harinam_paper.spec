import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Project Root & Entry Script
PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
ENTRY_SCRIPT = os.path.join(PROJECT_ROOT, "start_desktop.py")

hiddenimports = (
    collect_submodules("harinam_paper")
    + collect_submodules("core")
    + collect_submodules("job_entry")
    + [
        "whitenoise",
        "whitenoise.middleware",
        "whitenoise.storage",
        "waitress",
        "reportlab",
        "openpyxl",
        "PIL",
    ]
)

# Sirf unhi folders ko add karein jo physically exist karte hain
datas = []
potential_datas = [
    ("templates", "templates"),
    ("core/templates", "core/templates"),
    ("job_entry/templates", "job_entry/templates"),
    ("staticfiles", "staticfiles"),
    ("static", "static"),
]

for src, dest in potential_datas:
    full_path = os.path.join(PROJECT_ROOT, src.replace("/", os.sep))
    if os.path.exists(full_path):
        datas.append((full_path, dest))

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "django.contrib.gis",
        "django.contrib.gis.admin",
        "django.contrib.gis.db",
        "django.contrib.gis.forms",
        "django.contrib.gis.gdal",
        "django.contrib.gis.geos",
        "django.contrib.gis.sitemaps",
        "django.contrib.gis.utils",
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
    [],                      # Yahan a.binaries ki jagah [] hoga
    exclude_binaries=True,   # Yeh line add karni zaroori hai
    name="HarinamPaper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,              # Binaries yahan aayengi
    a.zipfiles,              # Zipfiles yahan aayengi
    a.datas,                 # Datas yahan aayengi
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HarinamPaper",
)