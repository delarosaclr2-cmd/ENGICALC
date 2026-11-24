"""Comprobación explícita del paquete, sin mostrar ventanas ni alterar datos reales."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


def comprobar(destino: Path) -> int:
    destino = destino.resolve()
    destino.mkdir(parents=True, exist_ok=True)
    os.environ['CALCULADORAS_REGISTRO'] = str(destino / 'registro_prueba')
    os.environ['MPLCONFIGDIR'] = str(destino / 'cache_graficas')
    informe = {'ejecutable': sys.executable, 'herramientas': [], 'correcto': False}
    ruta = destino / 'resultado.json'
    raiz = None

    def guardar():
        ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')

    try:
        import tkinter as tk
        from unittest.mock import patch
        from importlib import import_module
        from ..catalogo import HERRAMIENTAS
        from ..calculos import POR_ID as BASICAS
        from ..memorias import POR_ID as MEMORIAS
        from ..aplicaciones import POR_ID as APLICACIONES
        from ..interfaz.menu import MenuPrincipal
        from .rutas import raiz_recursos, raiz_instalacion, empaquetado

        casos_path = raiz_recursos() / 'verificacion/casos_verificacion.json'
        if casos_path.is_file():
            casos = json.loads(casos_path.read_text(encoding='utf-8'))
        else:
            from tests.casos import CASOS
            casos = CASOS
        raiz = tk.Tk()
        raiz.withdraw()
        menu = MenuPrincipal(raiz)

        def error(*args, **kw):
            raise RuntimeError(' | '.join(map(str, args)))

        with patch('tkinter.messagebox.showerror', error):
            for herramienta in HERRAMIENTAS:
                cid = herramienta.id
                if cid == 'hvac_industrial':
                    continue
                ventana = menu.abrir(cid)
                ventana.withdraw()
                pdf, excel = destino / (cid + '.pdf'), destino / (cid + '.xlsx')
                if cid in BASICAS:
                    ventana.asignar(casos[cid])
                    if ventana.calcular() is None:
                        raise RuntimeError(f'No se pudo calcular {cid}')
                    ventana.exportar_pdf_a(pdf)
                    ventana.exportar_excel_a(excel)
                    if ventana.panel_esquema is not None:
                        if not ventana.panel_esquema.actualizar(ventana.ultimo[1], ventana.ultimo[2]):
                            raise RuntimeError(f'No se pudo dibujar {cid}')
                elif cid in MEMORIAS:
                    if ventana.resultado is None:
                        raise RuntimeError(f'No se pudo calcular {cid}')
                    ventana.exportar_pdf_a(pdf)
                    ventana.exportar_excel_a(excel)
                else:
                    marco = next(w for w in ventana.winfo_children() if hasattr(w, 'memoria'))
                    if marco.memoria is None or not marco.memoria.resultados:
                        raise RuntimeError(f'No se pudo calcular {cid}')
                    reportes = import_module(APLICACIONES[cid].modulo.rsplit('.', 1)[0] + '.ui.memoria_pdf')
                    reportes.exportar_pdf(marco.memoria, str(pdf))
                    reportes.exportar_excel(marco.memoria, str(excel))
                if not pdf.read_bytes().startswith(b'%PDF-') or not excel.read_bytes().startswith(b'PK'):
                    raise RuntimeError(f'Reportes inválidos: {cid}')
                raiz.tk.call(ventana.protocol('WM_DELETE_WINDOW')) if ventana.protocol('WM_DELETE_WINDOW') else ventana.destroy()
                informe['herramientas'].append(cid)
                guardar()
            carpeta = raiz_instalacion() / 'HVAC_INDUSTRIAL_CALCULATOR'
            comando = ([str(carpeta / 'HVAC_Calculator.exe')] if empaquetado()
                       else [sys.executable, str(carpeta / 'main.py')])
            entorno = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1', QT_QPA_PLATFORM='offscreen',
                           ENGICALC_HVAC_DATOS=str(destino / 'perfil_hvac'))
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            proceso = subprocess.run(comando + ['--verificar-instalacion', str(destino / 'hvac')],
                                     env=entorno, cwd=carpeta, capture_output=True, timeout=180,
                                     creationflags=flags)
            if proceso.returncode:
                raise RuntimeError(f'HVAC: código {proceso.returncode}; {proceso.stderr.decode(errors="replace")}')
            hvac = json.loads((destino / 'hvac/resultado.json').read_text(encoding='utf-8'))
            if not hvac.get('correcto'):
                raise RuntimeError(f'Verificación HVAC incompleta: {hvac}')
            informe['herramientas'].append('hvac_industrial')
            if len(informe['herramientas']) != len(HERRAMIENTAS):
                raise RuntimeError('El inventario de herramientas no coincide')
            informe['correcto'] = True
    except Exception:
        informe['error'] = traceback.format_exc()
    finally:
        if raiz is not None:
            raiz.destroy()
        guardar()
    return 0 if informe['correcto'] else 1
