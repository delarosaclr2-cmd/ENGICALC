"""El esquema y la memoria del gas reflejan los resultados del motor."""
import json
import os

from gas_combustible.caso import ejecutar
from gas_combustible.memoria import evaluar
from gas_combustible.ui.memoria_pdf import exportar_excel, exportar_pdf

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")


def _c(n):
    return json.load(open(os.path.join(CASOS, n), encoding="utf-8"))


def test_maximo_coincidente_y_flujos_en_el_esquema():
    c = _c("PCGV_consumos_febrero_2024.json")
    e = ejecutar(c)["consumo"]
    textos = " ".join(evaluar(c).escena.textos())
    assert f"máx. {e.total_max:,.0f}" in textos and f"prom. {e.promedio:,.0f}" in textos
    c = _c("PCGV_cogeneracion5_turbina_LT16.json")
    out = ejecutar(c)
    textos = " ".join(evaluar(c).escena.textos())
    for _, kgh in out["flujos"]:
        assert f"{kgh:,.1f} kg/h" in textos
    assert "3,539.1 kg/h" in textos                           # turbina LT16 verificada en la auditoría


def test_la_ventana_acepta_composicion_como_lista():
    c = _c("PCGV_cogeneracion5_turbina_LT16.json")
    lista = dict(c, composicion=[{"componente": k, "pct_mol": v} for k, v in c["composicion"].items()])
    assert evaluar(lista).resultados == evaluar(c).resultados


def test_secciones_opcionales_vacias_se_ignoran():
    c = _c("PCGV_consumos_febrero_2024.json")
    c2 = dict(c, linea={"p": {}}, turbina={})
    assert evaluar(c2).resultados == evaluar(c).resultados


def test_memoria_pdf_y_excel(tmp_path):
    m = evaluar(_c("PCGV_cogeneracion5_turbina_LT16.json"))
    exportar_pdf(m, str(tmp_path / "m.pdf"))
    exportar_excel(m, str(tmp_path / "m.xlsx"))
    assert (tmp_path / "m.pdf").stat().st_size > 20000 and (tmp_path / "m.xlsx").stat().st_size > 4000
