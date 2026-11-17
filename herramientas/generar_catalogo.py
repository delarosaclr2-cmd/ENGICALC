"""Genera docs/CATALOGO_DE_CALCULADORAS.md a partir del registro de calculadoras.

El catálogo se obtiene del propio código (campos, unidades, rangos, ecuaciones,
niveles de confianza, referencias y limitaciones), así la documentación no puede
desfasarse del programa. Ejecutar después de modificar una calculadora:

    python herramientas/generar_catalogo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from calculadoras import __version__  # noqa: E402
from calculadoras import esquemas  # noqa: E402
from calculadoras.calculos import DISCIPLINAS, por_disciplina  # noqa: E402
from calculadoras.nucleo.modelo import NIVELES  # noqa: E402
from tests.casos import CASOS  # noqa: E402


def _celda(texto) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ")


def generar() -> str:
    lineas = [f"# Catálogo de calculadoras (versión {__version__})", "",
              "Documento generado automáticamente por `herramientas/generar_catalogo.py` a partir del código. "
              "No lo edite a mano.", "",
              "Niveles de confianza de los resultados: " + "; ".join(f"**{k}** = {v}" for k, v in NIVELES.items()) + ".",
              "", "Un campo sin valor por defecto es obligatorio. «0 = …» en la ayuda indica un valor que activa "
              "un criterio alternativo (tabla original, cálculo por altitud, etc.).", ""]
    lineas.append("## Índice")
    for disciplina, lista in por_disciplina().items():
        lineas.append(f"- **{disciplina}**: " + ", ".join(f"[{c.nombre}](#{c.id})" for c in lista))
    lineas.append("")
    for disciplina in DISCIPLINAS:
        lineas += [f"## {disciplina}", ""]
        for c in por_disciplina()[disciplina]:
            lineas += [f'<a id="{c.id}"></a>', f"### {c.nombre}  (`{c.id}`)", "", c.descripcion, "",
                       f"- Estado de auditoría: **{c.estado_auditoria}**",
                       f"- Estado de validación: **{c.estado_validacion}**",
                       f"- Sustituye a: {', '.join(c.archivos_originales)}",
                       f"- Abrir directamente: `python menu_principal.py --calculadora {c.id}`",
                       "- Esquema ajustable (pestaña «Esquema»): "
                       + (f"sí — captura en `docs/capturas/esquemas/{c.id}.png`" if esquemas.disponible(c.id)
                          else "no (decisión del usuario)"), "",
                       "**Datos de entrada**", "",
                       "| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |", "|---|---|---|---|---|---|"]
            for campo in c.campos:
                if campo.tipo == "opcion":
                    rango = "Opciones: " + " / ".join(campo.opciones)
                else:
                    rango = campo.describir_rango()
                defecto = "obligatorio" if campo.obligatorio else campo.defecto
                lineas.append(f"| {_celda(campo.grupo)} | {_celda(campo.etiqueta)} | {_celda(campo.unidad)} | "
                              f"{_celda(defecto)} | {_celda(rango)} | {_celda(campo.ayuda)} |")
            resultado = c.calcular(CASOS[c.id])
            lineas += ["", "**Resultados (caso de prueba ordinario de `tests/casos.py`)**", "",
                       "| Resultado | Valor | Unidad | Nivel |", "|---|---|---|---|"]
            for s in resultado.salidas:
                lineas.append(f"| {_celda(s.etiqueta)} | {_celda(s.texto_valor())} | {_celda(s.unidad)} | {s.nivel} |")
            if resultado.ecuaciones:
                lineas += ["", "**Ecuaciones**", "", "```"] + resultado.ecuaciones + ["```"]
            if resultado.advertencias:
                lineas += ["", "**Advertencias que emite con el caso de prueba**", ""]
                lineas += [f"- {a}" for a in resultado.advertencias]
            lineas += ["", "**Referencias**", ""] + [f"- {r}" for r in c.referencias]
            lineas += ["", "**Limitaciones**", ""] + [f"- {li}" for li in c.limitaciones] + [""]
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    destino = RAIZ / "docs" / "CATALOGO_DE_CALCULADORAS.md"
    destino.write_text(generar(), encoding="utf-8")
    print(f"Catálogo escrito en {destino}")
