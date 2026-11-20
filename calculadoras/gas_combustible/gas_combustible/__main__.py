"""python -m gas_combustible [caso.json] [--xlsx salida.xlsx]"""
import argparse
import json
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gas_combustible")
    ap.add_argument("caso", nargs="?")
    ap.add_argument("--xlsx")
    a = ap.parse_args(argv)
    if not a.caso:
        from .gui_tk import main as gui
        return gui()
    from .caso import a_texto, ejecutar, exportar_excel
    from .motor import ErrorEntrada
    c = json.load(open(a.caso, encoding="utf-8"))
    try:
        print(a_texto(c, ejecutar(c)))
    except (ErrorEntrada, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if a.xlsx:
        exportar_excel(c, a.xlsx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
