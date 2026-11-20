"""Uso:
    python -m tanque_pulmon                    -> abre la interfaz gráfica
    python -m tanque_pulmon caso.json          -> imprime el reporte en texto
    python -m tanque_pulmon caso.json --pdf salida.pdf --xlsx salida.xlsx
"""
import argparse
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tanque_pulmon", description="Cálculo de tanque pulmón de aire comprimido")
    ap.add_argument("caso", nargs="?", help="archivo .json del caso")
    ap.add_argument("--pdf", help="exportar reporte PDF")
    ap.add_argument("--xlsx", help="exportar reporte Excel")
    a = ap.parse_args(argv)
    if not a.caso:
        from .gui_tk import main as gui
        return gui()
    from .caso import CasoUsuario
    from .reporte import ejecutar, a_texto, exportar_excel, exportar_pdf
    from .validacion import ErrorEntrada
    try:
        inf = ejecutar(CasoUsuario.cargar(a.caso))
    except (ErrorEntrada, ValueError, KeyError) as exc:
        print(f"ERROR DE ENTRADA: {exc}", file=sys.stderr)
        return 2
    print(a_texto(inf))
    if a.pdf:
        exportar_pdf(inf, a.pdf)
    if a.xlsx:
        exportar_excel(inf, a.xlsx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
