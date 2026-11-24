"""Reúne documentación y evidencia de procedencia, sin datos de uso personales."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def finalizar(app: Path, destino: Path) -> Path:
    repo = Path(__file__).resolve().parents[1]
    if not (app / 'ENGICALC.exe').is_file() or not (app / 'HVAC_INDUSTRIAL_CALCULATOR/HVAC_Calculator.exe').is_file():
        raise ValueError('Falta uno de los dos ejecutables.')
    if (app / 'datos_usuario').exists():
        raise ValueError('La distribución debe estar limpia, sin datos_usuario.')
    (app / 'portable.flag').write_text('ENGICALC portable: conservar junto al EXE.\n', encoding='utf-8')
    shutil.copyfile(repo / 'empaquetado/LEEME_PORTABLE.txt', app / 'LEEME_PRIMERO.txt')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    diff = subprocess.check_output(['git', 'diff', 'HEAD'], cwd=repo)
    versiones = {n: importlib.metadata.version(n) for n in (
        'PyInstaller', 'PySide6', 'scipy', 'numpy', 'CoolProp', 'matplotlib', 'reportlab', 'openpyxl', 'Pillow')}
    for paquete in [*versiones, 'PySide6_Essentials', 'shiboken6', 'pyinstaller-hooks-contrib']:
        distribucion = importlib.metadata.distribution(paquete)
        for archivo in distribucion.files or []:
            partes = archivo.parts
            if '..' in partes or not any(p.endswith('.dist-info') for p in partes):
                continue
            if not any('license' in p.lower() or p.lower().startswith('copying') for p in partes):
                continue
            origen = Path(distribucion.locate_file(archivo))
            if origen.is_file():
                indice = next(i for i, p in enumerate(partes) if p.endswith('.dist-info'))
                licencia = app / 'LICENCIAS' / paquete / Path(*partes[indice + 1:])
                licencia.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(origen, licencia)
    licencia_python = Path(sys.base_prefix) / 'LICENSE.txt'
    if licencia_python.is_file():
        (app / 'LICENCIAS').mkdir(exist_ok=True)
        shutil.copyfile(licencia_python, app / 'LICENCIAS/Python-LICENSE.txt')
    (destino / 'versiones_compilacion.json').write_text(json.dumps(versiones, indent=2), encoding='utf-8')
    manifest = {'commit_base': commit, 'cambios_sin_commit': bool(diff),
                'sha256_diff_base': hashlib.sha256(diff).hexdigest(),
                'python': sys.version, 'dependencias': versiones, 'fuentes_sha256': {}, 'archivos': {}}
    fuentes = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=repo)
    for nombre in fuentes.decode('utf-8').split('\0'):
        if nombre and (repo / nombre).is_file():
            manifest['fuentes_sha256'][nombre] = hashlib.sha256((repo / nombre).read_bytes()).hexdigest()
    for p in sorted(app.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(app).as_posix()
        if rel == 'MANIFIESTO.json':
            # El manifiesto anterior no puede formar parte de su propio hash.
            continue
        if any(part in {'__pycache__', '.git', '.venv', 'datos_usuario'} for part in p.relative_to(app).parts):
            raise ValueError(f'Archivo ajeno a la distribución: {rel}')
        manifest['archivos'][rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    (app / 'MANIFIESTO.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    salida = destino / 'ENGICALC_2.2.0_portable_windows_x64_r1.zip'
    if salida.exists():
        raise FileExistsError(salida)
    with zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(app.rglob('*')):
            if p.is_file():
                z.write(p, 'ENGICALC/' + p.relative_to(app).as_posix())
    with zipfile.ZipFile(salida) as z:
        if z.testzip() is not None:
            raise ValueError('El ZIP no superó la comprobación de integridad.')
    (destino / (salida.name + '.sha256')).write_text(
        hashlib.sha256(salida.read_bytes()).hexdigest() + '  ' + salida.name + '\n', encoding='ascii')
    print(f'ZIP portable: {salida}\nTamaño: {salida.stat().st_size / 1024**2:.1f} MB')
    return salida


if __name__ == '__main__':
    finalizar(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
