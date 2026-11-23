"""python -m linea_gas                 -> interfaz gráfica
python -m linea_gas caso.json [...]  -> reporte en texto (uno o varios casos)
python -m linea_gas casos/*.json --xlsx resumen.xlsx
"""
import argparse
import json
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="linea_gas")
    ap.add_argument("casos", nargs="*")
    ap.add_argument("--xlsx")
    a = ap.parse_args(argv)
    if not a.casos:
        from .gui_tk import main as gui
        return gui()
    from .caso import a_texto, ejecutar, exportar_excel
    from .motor import ErrorEntrada
    casos = [json.load(open(r, encoding="utf-8")) for r in a.casos]
    for c in casos:
        try:
            e, r = ejecutar(c)
        except (ErrorEntrada, KeyError, ValueError) as exc:
            print(f"ERROR en {c.get('nombre')}: {exc}", file=sys.stderr)
            return 2
        print(a_texto(c, e, r), "\n")
    if a.xlsx:
        exportar_excel(casos, a.xlsx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
