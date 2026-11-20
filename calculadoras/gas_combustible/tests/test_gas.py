import json
import os

import pytest

from gas_combustible.caso import ejecutar, exportar_excel
from gas_combustible.motor import (ErrorEntrada, estadistica, flujo_turbina_kg_s, lhv_masico, propiedades)

CASOS = os.path.join(os.path.dirname(__file__), "..", "casos")
COMP = json.load(open(os.path.join(CASOS, "PCGV_cogeneracion5_turbina_LT16.json"), encoding="utf-8"))["composicion"]


def test_masa_molar_coincide_con_laboratorio():
    p = propiedades(COMP, usar_coolprop=False, z_ref=1.0)
    assert p.m_kg_kmol == pytest.approx(17.102, abs=0.001)       # reporte de laboratorio: 17.102 ± 0.35
    assert p.sg_ideal == pytest.approx(0.5905, abs=1e-4)


def test_densidad_contra_coolprop_y_dm006():
    CP = pytest.importorskip("CoolProp.CoolProp")
    p = propiedades(COMP)
    assert p.z_ref == pytest.approx(0.9978, abs=2e-4)
    assert p.rho_ref == pytest.approx(0.723409, rel=1e-3)        # valor usado en PCGV-DM-006 Rev F
    assert lhv_masico(34.06, p.rho_ref) == pytest.approx(47082.63, rel=1e-3)   # LAC-0738 citado en DM-006


def test_flujo_turbina_hoja_original():
    assert flujo_turbina_kg_s(10055, 16590, 47134.1) * 3600 == pytest.approx(3539.1033, rel=1e-7)


def test_estadistica_suma_todas_las_unidades():
    e = estadistica(["d1", "d2"], {"A": [1.0, 5.0], "B": [10.0, 2.0], "C": [0.0, 4.0]})
    assert e.total_por_dia == [11.0, 11.0] and e.suma_max_no_coincidentes == 19.0 and e.promedio == 11.0
    c = json.load(open(os.path.join(CASOS, "PCGV_consumos_febrero_2024.json"), encoding="utf-8"))
    e = estadistica(c["consumos"]["fechas"], c["consumos"]["series"])
    assert e.total_max == 194418 and e.dia_max == "2024-02-24"
    assert e.total_por_dia[12] == 87192          # 13-feb: la hoja original daba 68 307
    assert e.promedio == pytest.approx(149509.96, abs=0.01)


@pytest.mark.parametrize("fn, msj", [
    (lambda: propiedades({"metano": 90.0}), "suma"),
    (lambda: propiedades({"kriptonita": 100.0}), "desconocido"),
    (lambda: flujo_turbina_kg_s(10055, 16590, 34.06), "kJ/m³"),
    (lambda: flujo_turbina_kg_s(10.055, 16590, 47134.1), "Tasa de calor"),
    (lambda: estadistica(["a"], {"X": [1.0, 2.0]}), "datos"),
])
def test_entradas_invalidas(fn, msj):
    with pytest.raises(ErrorEntrada, match=msj):
        fn()


def test_caso_y_excel(tmp_path):
    c = json.load(open(os.path.join(CASOS, "PCGV_cogeneracion5_turbina_LT16.json"), encoding="utf-8"))
    out = ejecutar(c)
    assert any("4,892" in f[1] for f in out["filas"])
    from openpyxl import load_workbook
    assert "Composición" in load_workbook(exportar_excel(c, str(tmp_path / "g.xlsx"))).sheetnames
