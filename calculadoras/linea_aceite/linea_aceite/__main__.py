"""python -m linea_aceite                -> interfaz gráfica
python -m linea_aceite caso.json [...] -> memoria en texto"""
import json
import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        from .gui_tk import main as gui
        return gui()
    from .memoria import evaluar
    for ruta in argv:
        print(evaluar(json.load(open(ruta, encoding="utf-8"))).a_texto(), "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
