# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: pyinstaller --noconfirm --clean hvac_calculator.spec   (ejecutar en Windows para obtener .exe)
import os
ROOT = os.path.abspath(SPECPATH)
datas = [
    ("config/settings.json", "config"), ("config/settings.default.json", "config"),
    ("database/defaults", "database/defaults"),
    ("assets", "assets"), ("examples/nave_industrial_4_campanas.hvac.json", "examples"),
    ("examples/curva_ventilador_ejemplo.csv", "examples"), ("docs", "docs"),
]
datas = [(os.path.join(ROOT, source), target) for source, target in datas]
a = Analysis(
    [os.path.join(ROOT, "main.py")], pathex=[ROOT], binaries=[], datas=datas,
    hiddenimports=["scipy.optimize", "scipy.interpolate", "matplotlib.backends.backend_qtagg",
                   "reportlab.graphics.barcode.common", "openpyxl.cell._writer"],
    hookspath=[], runtime_hooks=[], hooksconfig={"matplotlib": {"backends": ["QtAgg", "Agg"]}},
    excludes=["CoolProp", "pytest", "tkinter", "pandas", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="HVAC_Calculator", debug=False, strip=False, upx=False,
          console=False, icon=os.path.join(ROOT, "assets/icon.ico"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="HVAC_Calculator")
