"""Doble clic para abrir la calculadora: Tanque pulmon de aire comprimido.
En Windows los archivos .pyw se abren sin ventana de consola."""
import datetime
import importlib.util
import os
import sys
import traceback

AQUI = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
if not getattr(sys, "frozen", False):
    sys.path.insert(0, AQUI)
REQUERIDOS = ['openpyxl', 'reportlab']
REGISTRO = os.path.join(AQUI, "errores_tanque_pulmon.log")


def _aviso(titulo, texto):
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(titulo, texto, parent=r)
        r.destroy()
    except Exception:
        print(titulo, texto, file=sys.stderr)


def main():
    faltan = [m for m in REQUERIDOS if importlib.util.find_spec(m) is None]
    if faltan:
        _aviso("Faltan componentes",
               "Falta instalar: " + ", ".join(faltan) + ".\n\n"
               "Abra la calculadora con el archivo 'ABRIR TANQUE PULMON.bat' (los instala la primera vez) "
               "o ejecute en una terminal:\n  py -m pip install -r requirements.txt")
        return 1
    try:
        from tanque_pulmon.gui_tk import abrir
        ventana, _ = abrir()
        if os.environ.get("ENGICALC_PRUEBA_LANZADOR"):
            ventana.after(1500, ventana.destroy)
        ventana.mainloop()
        return 0
    except Exception:
        detalle = traceback.format_exc()
        try:
            with open(REGISTRO, "a", encoding="utf-8") as fh:
                fh.write(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n{detalle}")
        except OSError:
            pass
        _aviso("Error al abrir la calculadora",
               "No se pudo abrir la calculadora.\nEl detalle se guardó en:\n" + REGISTRO + "\n\n"
               + detalle.strip().splitlines()[-1])
        return 1


if __name__ == "__main__":
    sys.exit(main())
