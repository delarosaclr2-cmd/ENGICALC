"""Permite ejecutar ``python -m calculadoras``."""
import sys

from menu_principal import main  # noqa: E402  (la raíz del proyecto está en sys.path al usar -m)

sys.exit(main())
