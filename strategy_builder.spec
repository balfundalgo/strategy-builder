# strategy_builder.spec
# ──────────────────────────────────────────────────────────────────
# PyInstaller spec for Balfund Strategy Builder
# Produces a single .exe with no console window.
#
# Build command:
#   pyinstaller strategy_builder.spec --clean
#
# Output: dist/BalfundStrategyBuilder.exe
# ──────────────────────────────────────────────────────────────────

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect pandas_ta data files
datas = []
datas += collect_data_files("pandas_ta")

# Hidden imports that PyInstaller might miss
hiddenimports = [
    "pandas_ta",
    "pandas_ta.momentum",
    "pandas_ta.trend",
    "pandas_ta.volatility",
    "pandas_ta.volume",
    "pandas_ta.overlap",
    "pandas_ta.performance",
    "pandas_ta.statistics",
    "pyotp",
    "websocket",
    "schedule",
    "pkg_resources.py2_warn",
]
hiddenimports += collect_submodules("pandas_ta")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "IPython", "jupyter"],
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
    name="BalfundStrategyBuilder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No black console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # Add icon path here when you have one: "assets/icon.ico"
    version=None,
)
