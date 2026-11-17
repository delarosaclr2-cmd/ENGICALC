"""Validación del colector de polvo contra EPA/452/B-02-001, sección 6, capítulo 1 (Baghouses and Filters).

- Tabla 1.1: relación gas/tela [ft/min] por polvo; p. ej. cemento 2.0 (tejida) y 8 (fieltro, pulse jet),
  ceniza volante 2.5 y 5, yeso 2.0 y 10, caliza 2.7 y 8.
- Nota de la tabla 1.3: colector de 26 000 CFM con relación 2.9 ft/min → ≈ 9 000 ft² de tela.
"""
import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.calculos import colector as C
from calculadoras.nucleo.modelo import ErrorEntrada

CFM_A_M3H = 0.3048 ** 3 * 60


def calc(**cambios):
    datos = dict(CASOS["colector"])
    datos.update(cambios)
    return POR_ID["colector"].calcular(datos)


@pytest.mark.parametrize("polvo, limpieza, ftmin", [
    ("Cemento", C.PULSE_JET, 8), ("Cemento", C.TEJIDA, 2.0), ("Ceniza volante", C.PULSE_JET, 5),
    ("Yeso", C.PULSE_JET, 10), ("Caliza", C.TEJIDA, 2.7)])
def test_tabla_epa_1_1(polvo, limpieza, ftmin):
    r = calc(tipo_polvo=polvo, limpieza=limpieza, relacion_aire_tela=0)
    assert r["relacion_aire_tela_ftmin"] == pytest.approx(ftmin)
    assert r.salida("area_filtracion").nivel == "E"
    assert r["area_filtracion"] == pytest.approx(10000 / 60 / (ftmin * 0.3048))


def test_ejemplo_tabla_1_3_epa():
    r = calc(caudal=26000 * CFM_A_M3H, tipo_polvo=C.CAPTURAR, relacion_aire_tela=2.9 * 0.3048)
    assert r["area_filtracion"] / 0.3048 ** 2 == pytest.approx(9000, rel=0.01)


def test_prioridades_y_faltantes():
    capt = calc(tipo_polvo="Cemento", relacion_aire_tela=1.5)
    assert capt["relacion_aire_tela"] == 1.5 and capt.salida("relacion_aire_tela").nivel == "D"
    original = calc(tipo_polvo=C.FINO, relacion_aire_tela=0)
    assert original["relacion_aire_tela"] == 1.0 and original.salida("relacion_aire_tela").nivel == "O"
    with pytest.raises(ErrorEntrada):
        calc(tipo_polvo="Tabaco", limpieza=C.PULSE_JET, relacion_aire_tela=0)
    tejida = calc(tipo_polvo="Tabaco", limpieza=C.TEJIDA, relacion_aire_tela=0)
    assert any("NETA" in n for n in tejida.notas)
