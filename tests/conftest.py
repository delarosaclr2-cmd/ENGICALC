import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Las pruebas no deben escribir el historial ni los datos de proyecto en la carpeta del programa
os.environ.setdefault("CALCULADORAS_REGISTRO", tempfile.mkdtemp(prefix="calc_registro_"))
