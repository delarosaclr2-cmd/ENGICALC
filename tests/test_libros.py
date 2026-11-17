"""Validación con ejercicios resueltos de libros de texto de ingeniería (v2.1.1).

Cada caso de ``casos_libros.CASOS_LIBROS`` reproduce un ejemplo o problema publicado en un libro de
texto de uso docente: captura los datos del enunciado en los campos de la calculadora y compara cada
resultado con la respuesta publicada. Las tolerancias reflejan la precisión con que el libro imprime su
resultado (tres cifras significativas) o la diferencia esperada por leer propiedades en tablas o en la
carta psicrométrica. Detalle (datos, respuesta, resultado, diferencia): docs/VALIDACION_CON_LIBROS.md.

Libros: Çengel y Cimbala, Mecánica de fluidos (cap. 8); Çengel y Boles, Termodinámica (caps. 7 y 14);
Geankoplis, Transport Processes and Unit Operations (cap. 9); Rhodes, Introduction to Particle Technology
(cap. 7); Strength of Materials, Engineering Mechanics OER (cap. 11).
"""
import math

import pytest

from casos_libros import CASOS_LIBROS, valor
from calculadoras.calculos import POR_ID
from calculadoras.calculos import secador as S
from calculadoras.nucleo.modelo import ErrorEntrada


def calcular(id_calc: str, **datos):
    """Ejecuta una calculadora con sus valores por defecto más los datos del ejercicio."""
    calc = POR_ID[id_calc]
    entradas = calc.valores_por_defecto()
    entradas.update(datos)
    return calc.calcular(entradas)


@pytest.mark.parametrize("nombre", sorted(CASOS_LIBROS))
def test_ejercicio_de_libro(nombre):
    caso = CASOS_LIBROS[nombre]
    r = calcular(caso["calculadora"], **caso["entradas"])
    for etiqueta, salida, publicado, tolerancia in caso["comprobaciones"]:
        obtenido = valor(r, salida)
        assert obtenido == pytest.approx(publicado, rel=tolerancia), (
            f"{nombre} — {etiqueta}: publicado {publicado}, calculadora {obtenido:.6g}")


def test_cobertura_de_libros():
    """Al menos un ejercicio de libro en cada calculadora que tiene un ejemplo docente publicado."""
    cubiertas = {c["calculadora"] for c in CASOS_LIBROS.values()}
    assert {"torre", "bomba", "ductos", "vacio", "aerodeslizador", "viga", "secador"} <= cubiertas


def test_secador_contracorriente_solo_cambia_dtml():
    """Los balances no dependen de la disposición de los flujos; ΔT_ml sí."""
    base = dict(alimentacion=1000, base=S.HUMEDA, humedad_inicial=12, humedad_final=3, cp_solido=0.84,
                t_solido_entrada=20, t_solido_salida=80, t_aire_entrada=400, t_aire_salida=110,
                t_ambiente=20, hr_ambiente=50, altitud=0, perdidas=0, velocidad_aire=3, pci=0)
    par = calcular("secador", flujo=S.PARALELO, **base)
    contra = calcular("secador", flujo=S.CONTRACORRIENTE, **base)
    assert contra["aire_seco"] == pytest.approx(par["aire_seco"])
    assert contra["w_salida"] == pytest.approx(par["w_salida"])
    dt_par = ((400 - 20) - (110 - 80)) / math.log((400 - 20) / (110 - 80))
    dt_contra = ((400 - 80) - (110 - 20)) / math.log((400 - 80) / (110 - 20))
    assert par["dtml"] == pytest.approx(dt_par)
    assert contra["dtml"] == pytest.approx(dt_contra)
    assert contra["longitud"] < par["longitud"]  # mayor ΔT_ml → menor volumen


def test_secador_paralelo_rechaza_el_caso_de_geankoplis():
    """En flujo paralelo el sólido no puede salir más caliente que el aire de salida (62.8 > 37.8 °C)."""
    entradas = dict(CASOS_LIBROS["secador_geankoplis_ej_9_10_2"]["entradas"], flujo=S.PARALELO)
    with pytest.raises(ErrorEntrada):
        calcular("secador", **entradas)
