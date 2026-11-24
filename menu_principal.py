"""Punto de entrada de Calculadoras de Ingeniería RMR.

Uso:
    python menu_principal.py                        abre el menú principal
    python menu_principal.py --calculadora bomba    abre el menú y una calculadora
    python menu_principal.py --calculadora memoria_bombas    abre el menú y la memoria completa
    python menu_principal.py --calculadora hvac_industrial   abre HVAC industrial desde el menú
    python menu_principal.py --lista                lista las calculadoras disponibles
    python menu_principal.py --cambiar-contrasena   cambia (o desactiva) la contraseña de acceso
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv: list[str] | None = None) -> int:
    from calculadoras.catalogo import HERRAMIENTAS as herramientas

    parser = argparse.ArgumentParser(description="Calculadoras de Ingeniería RMR")
    parser.add_argument("--calculadora", choices=sorted(c.id for c in herramientas),
                        help="abre directamente una calculadora o memoria completa")
    parser.add_argument("--lista", action="store_true", help="lista las calculadoras y memorias y termina")
    parser.add_argument("--verificar-instalacion", metavar="CARPETA",
                        help="comprueba ventanas y reportes; guarda evidencia técnica en CARPETA")
    parser.add_argument("--cambiar-contrasena", action="store_true", help="cambia la contraseña de acceso y termina")
    args = parser.parse_args(argv)

    if args.verificar_instalacion:
        from calculadoras.nucleo.verificar_distribucion import comprobar

        return comprobar(Path(args.verificar_instalacion))

    if args.lista:
        for c in herramientas:
            print(f"{c.id:16s} {c.nombre}  [{c.estado_validacion}]")
        return 0
    if args.cambiar_contrasena:
        from calculadoras.nucleo.configuracion import establecer_contrasena

        nueva = getpass.getpass("Contraseña nueva (vacía = desactivar el acceso con contraseña): ")
        if nueva and nueva != getpass.getpass("Repita la contraseña: "):
            print("Las contraseñas no coinciden; no se hizo ningún cambio.")
            return 1
        establecer_contrasena(nueva, requerir=bool(nueva))
        print("Contraseña actualizada." if nueva else "Acceso con contraseña desactivado.")
        return 0

    from calculadoras.interfaz.menu import iniciar

    iniciar(args.calculadora)
    return 0


if __name__ == "__main__":
    sys.exit(main())
