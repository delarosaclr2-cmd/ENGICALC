"""Ejecuta el paquete con PATH limitado a Windows y comprueba sus evidencias."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def verificar(app: Path, salida: Path) -> None:
    app, salida = app.resolve(), salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    entorno = dict(os.environ)
    for nombre in ('PYTHONHOME', 'PYTHONPATH', 'TCL_LIBRARY', 'TK_LIBRARY', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM'):
        entorno.pop(nombre, None)
    windows = os.environ.get('SYSTEMROOT', r'C:\Windows')
    entorno['PATH'] = os.path.join(windows, 'System32') + os.pathsep + windows
    entorno['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    python_en_path = shutil.which('python', path=entorno['PATH'])
    if python_en_path:
        raise RuntimeError(f'La prueba no debe encontrar Python en PATH: {python_en_path}')
    inicio = time.monotonic()
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    proceso = subprocess.run([str(app / 'ENGICALC.exe'), '--verificar-instalacion', str(salida)],
                             cwd=app.parent, env=entorno, capture_output=True,
                             timeout=240, creationflags=flags)
    resultado = salida / 'resultado.json'
    informe = json.loads(resultado.read_text(encoding='utf-8')) if resultado.exists() else {}
    resumen = {'codigo': proceso.returncode, 'python_en_path': python_en_path,
               'segundos': round(time.monotonic() - inicio, 2),
               'herramientas': len(informe.get('herramientas', [])),
               'correcto': bool(proceso.returncode == 0 and informe.get('correcto'))}
    (salida / 'entorno_verificado.json').write_text(json.dumps(resumen, indent=2), encoding='utf-8')
    if not resumen['correcto'] or resumen['herramientas'] != 25:
        raise RuntimeError(f'La distribución no superó la prueba. Consulte {resultado}: {informe.get("error", proceso.stderr.decode(errors="replace"))}')
    print(f'Verificación correcta: 25 herramientas, PDF y Excel, sin Python en PATH. Evidencia: {salida}')


if __name__ == '__main__':
    verificar(Path(sys.argv[1]), Path(sys.argv[2]))
