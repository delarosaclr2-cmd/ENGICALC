"""Menú de las calculadoras RMR. Doble clic para abrirlo."""
import datetime
import importlib
import os
import sys
import tkinter as tk
import traceback
from tkinter import messagebox, ttk

AQUI = os.path.dirname(os.path.abspath(__file__))
CALCS = [('linea_gas', 'Líneas de gas y aire comprimido'), ('tanque_pulmon', 'Tanque pulmón de aire comprimido'), ('gas_combustible', 'Gas combustible'), ('linea_agua', 'Líneas de agua'), ('linea_vapor', 'Líneas de vapor'), ('linea_aceite', 'Líneas de aceite')]
for paquete, _ in CALCS:
    sys.path.insert(0, os.path.join(AQUI, paquete))


def abrir(paquete, raiz):
    try:
        importlib.import_module(paquete + ".gui_tk").abrir(raiz)
    except Exception:
        with open(os.path.join(AQUI, "errores_menu.log"), "a", encoding="utf-8") as fh:
            fh.write(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {paquete}\n{traceback.format_exc()}")
        messagebox.showerror("Error", f"No se pudo abrir {paquete}.\n"
                             "Si faltan componentes, ejecute una vez el archivo .bat de esa calculadora.\n\n"
                             + traceback.format_exc().strip().splitlines()[-1], parent=raiz)


def main():
    raiz = tk.Tk()
    raiz.title("Calculadoras de ingeniería RMR")
    marco = ttk.Frame(raiz, padding=16)
    marco.grid()
    ttk.Label(marco, text="Calculadoras de ingeniería RMR", font=("Arial", 13, "bold")).grid(pady=(0, 10))
    for i, (paquete, nombre) in enumerate(CALCS):
        ttk.Button(marco, text=nombre, width=40, command=lambda p=paquete: abrir(p, raiz)).grid(row=i + 1, pady=3)
    ttk.Label(marco, text="Herramientas de apoyo; no sustituyen la revisión de un ingeniero responsable.",
              foreground="#555", wraplength=320).grid(row=len(CALCS) + 1, pady=(10, 0))
    if os.environ.get("ENGICALC_PRUEBA_LANZADOR"):
        def prueba():
            for paquete, _ in CALCS:
                abrir(paquete, raiz)
            raiz.after(1500, raiz.destroy)
        raiz.after(200, prueba)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
