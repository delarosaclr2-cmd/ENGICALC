"""Validación de entradas. Lanza ErrorEntrada si el cálculo no tiene sentido físico;
devuelve advertencias si el dato es admisible pero merece revisión."""
from __future__ import annotations

import math

from .constantes import REFERENCIAS


class ErrorEntrada(ValueError):
    pass


def _finito_positivo(nombre, valor):
    if valor is None or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ErrorEntrada(f"{nombre}: valor no numérico o no finito")
    if valor <= 0:
        raise ErrorEntrada(f"{nombre}: debe ser mayor que cero")


def validar(e) -> list:
    adv = []
    _finito_positivo("Volumen del tanque", e.v_tanque_m3)
    _finito_positivo("Presión superior", e.p_superior_pa)
    _finito_positivo("Presión inferior", e.p_inferior_pa)
    _finito_positivo("Temperatura del aire", e.t_aire_k)
    _finito_positivo("Caudal de consumo", e.q_consumo_m3s)
    _finito_positivo("Presión atmosférica del sitio", e.p_atm_sitio_pa)
    for ref in (e.ref_consumo, e.ref_compresor):
        if ref not in REFERENCIAS:
            raise ErrorEntrada(f"Condición de referencia desconocida: {ref}")
    if e.p_superior_pa <= e.p_inferior_pa:
        raise ErrorEntrada("La presión superior debe ser mayor que la inferior")
    if e.p_inferior_pa <= e.p_atm_sitio_pa:
        raise ErrorEntrada("La presión inferior debe ser mayor que la atmosférica del sitio "
                           "(¿se capturó presión manométrica como absoluta?)")
    if not (1.0 <= e.n_politropico <= 1.4):
        raise ErrorEntrada("El exponente politrópico debe estar entre 1.0 (isotérmico) y 1.4 (adiabático)")
    for nombre, z in (("Z superior", e.z_superior), ("Z inferior", e.z_inferior)):
        _finito_positivo(nombre, z)
        if not 0.8 <= z <= 1.2:
            raise ErrorEntrada(f"{nombre} fuera del intervalo físico esperado para aire (0.8–1.2)")
    if not 0.0 <= e.margen_consumo <= 1.0:
        raise ErrorEntrada("El margen de consumo debe estar entre 0 y 100 %")
    for t in e.tramos:
        _finito_positivo(f"Longitud del tramo '{t.descripcion}'", t.longitud_m)
        _finito_positivo(f"Diámetro interior del tramo '{t.descripcion}'", t.d_interior_m)
        if t.d_interior_m > 2.0:
            raise ErrorEntrada(f"Diámetro interior de '{t.descripcion}' > 2 m: ¿se capturó en mm?")
    if e.t_retencion_req_min is not None:
        _finito_positivo("Tiempo de retención requerido", e.t_retencion_req_min)
    if e.q_compresor_m3s is not None:
        _finito_positivo("FAD del compresor", e.q_compresor_m3s)

    # Advertencias
    t_c = e.t_aire_k - 273.15
    if not -20.0 <= t_c <= 80.0:
        adv.append(f"Temperatura del aire {t_c:.1f} °C fuera del intervalo usual (−20 a 80 °C)")
    if e.p_superior_pa > 2.5e6:
        adv.append("Presión superior > 25 bar: verificar Z (gas real) con un método de estado")
    if e.n_politropico == 1.0:
        adv.append("Descarga isotérmica supuesta. Si la descarga es rápida (segundos), "
                   "evaluar n = 1.4 como cota inferior del tiempo")
    if e.margen_consumo == 0.0:
        adv.append("Sin margen de consumo por fugas o crecimiento futuro; definirlo en las bases de diseño")
    if e.ref_consumo != e.ref_compresor and e.q_compresor_m3s is not None:
        adv.append("Consumo y FAD están en referencias distintas; el motor los convierte a masa")
    if e.q_compresor_m3s is not None:
        from .motor import flujo_masico
        if flujo_masico(e.q_compresor_m3s, e.ref_compresor) <= flujo_masico(e.q_consumo_m3s, e.ref_consumo) * (1 + e.margen_consumo):
            adv.append("El FAD del compresor no supera el consumo: el sistema no recupera presión "
                       "(tiempo de carga infinito)")
    if not e.incluir_tuberia or not e.tramos:
        adv.append("Volumen de tubería no incluido (conservador para retención, no para tiempos de carga)")
    return adv
