# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: pyinstaller --noconfirm --clean hvac_calculator.spec   (ejecutar en Windows para obtener .exe)
import os
block_cipher = None
ROOT = os.path.abspath(".")
datas = [
    ("config/settings.json", "config"), ("config/settings.default.json", "config"),
    ("database/defaults", "database/defaults"),
    ("assets", "assets"), ("examples/nave_industrial_4_campanas.hvac.json", "examples"),
    ("examples/curva_ventilador_ejemplo.csv", "examples"), ("docs", "docs"),
]
a = Analysis(
    ["main.py"], pathex=[ROOT], binaries=[], datas=datas,
    hiddenimports=["scipy.optimize", "scipy.interpolate", "matplotlib.backends.backend_qtagg",
                   "reportlab.graphics.barcode.common", "openpyxl.cell._writer"],
    hookspath=[], runtime_hooks=[],
    excludes=["CoolProp", "pytest", "tkinter", "pandas", "IPython"],
    cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="HVAC_Calculator", debug=False, strip=False, upx=False,
          console=False, icon="assets/icon.ico")
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name="HVAC_Calculator")
