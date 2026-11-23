"""Catálogo del menú: calculadoras básicas, memorias y aplicaciones completas."""
import unicodedata

from .calculos import CALCULADORAS, DISCIPLINAS
from .memorias import MEMORIAS
from .aplicaciones import APLICACIONES

HERRAMIENTAS = [*CALCULADORAS, *MEMORIAS, *APLICACIONES]
POR_ID = {h.id: h for h in HERRAMIENTAS}


def por_disciplina():
    grupos = {d: [] for d in DISCIPLINAS}
    for herramienta in HERRAMIENTAS:
        grupos.setdefault(herramienta.disciplina, []).append(herramienta)
    return grupos


def buscar(texto):
    def normal(valor):
        return "".join(c for c in unicodedata.normalize("NFD", valor.lower())
                       if unicodedata.category(c) != "Mn")

    palabras = normal(texto).split()
    return [h for h in HERRAMIENTAS if all(
        p in normal(" ".join((h.id, h.nombre, h.disciplina, h.descripcion,
                             *getattr(h, "palabras_clave", ())))) for p in palabras)]
