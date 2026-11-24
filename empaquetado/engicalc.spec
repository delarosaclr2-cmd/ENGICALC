# Compilar desde Windows; las rutas no dependen del directorio actual.
import json
import runpy
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.config import CONF

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT))
from calculadoras.aplicaciones import APLICACIONES
casos = Path(CONF['workpath']) / 'casos_verificacion.json'
casos.parent.mkdir(parents=True, exist_ok=True)
casos.write_text(json.dumps(runpy.run_path(str(ROOT / 'tests/casos.py'))['CASOS'],
                           ensure_ascii=False), encoding='utf-8')
datas = [(str(ROOT / 'recursos'), 'recursos'),
         (str(ROOT / 'config/configuracion.json'), 'config'),
         (str(ROOT / 'docs'), 'docs'),
         (str(casos), 'verificacion')]
datas += collect_data_files('calculadoras', excludes=['**/tests/**', '**/__pycache__/**'])
datas += collect_data_files('CoolProp', includes=['**/*.json'])
hidden = collect_submodules('calculadoras', filter=lambda name: '.tests' not in name)
for app in APLICACIONES:
    if app.modulo:
        # Las seis aplicaciones viven bajo paquetes de espacio de nombres.
        # El recorrido de calculadoras por sí solo no descubre esos módulos.
        hidden += collect_submodules(app.modulo.rsplit('.', 1)[0])
hidden += ['CoolProp.CoolProp', 'reportlab.graphics.barcode.common', 'openpyxl.cell._writer']
a = Analysis([str(ROOT / 'menu_principal.py')], pathex=[str(ROOT)], datas=datas,
             hiddenimports=hidden, binaries=[],
             hooksconfig={'matplotlib': {'backends': ['TkAgg', 'Agg']}},
             excludes=['PySide6', 'PyQt5', 'PyQt6', 'scipy', 'pandas', 'pytest', 'tests', 'IPython'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ENGICALC', console=False,
          debug=False, strip=False, upx=False, icon=str(ROOT / 'recursos/Nueva etiqueta RMR.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ENGICALC')
