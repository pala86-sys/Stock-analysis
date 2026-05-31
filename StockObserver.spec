# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包設定：台股多維度全方位觀測儀"""

block_cipher = None

hiddenimports = [
    "matplotlib.backends.backend_tkagg",
    "pandas",
    "yfinance",
    "requests",
    "certifi",
    "json",
    "tkinter",
    "tkinter.ttk",
    "stock_search",
    "stock_search_box",
    "http_client",
    "report_export",
    "fpdf",
    "fpdf.html",
    "valuation",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("data/stock_list.json", "data"),
        ("data/delisted_stock_ids.json", "data"),
        ("assets/fonts/NotoSansTC-Regular.otf", "assets/fonts"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="StockObserver",
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
    codesign_identity=None,
    entitlements_file=None,
)
