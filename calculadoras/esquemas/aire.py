"""Esquemas de manejo de aire: transportador neumático, ductos, colector, soplador y bomba de vacío.

Los diagramas de proceso son esquemas sin escala; las secciones de tubo y ducto sí son a escala.
"""
from __future__ import annotations

import math

from matplotlib.patches import Circle, Ellipse

from ..calculos import colector as COL
from ..calculos import soplador as SOP
from .base import C, caja_equipo, cota, cuadro, flecha, limites, num, poligono, preparar, rectangulo


def _seccion_tubo(ax, diametro_m: float, titulo: str, color_borde: str = C["estructura"],
                  particulas: bool = False, texto_flujo: str | None = None) -> None:
    """Sección circular a escala (cotas en mm)."""
    preparar(ax, titulo, True, "mm")
    D = diametro_m * 1000.0
    R = D / 2
    ax.add_patch(Circle((0, 0), R * 1.04, fc=C["relleno"], ec=color_borde, lw=1.0))
    ax.add_patch(Circle((0, 0), R, fc="#E3F2FD", ec=color_borde, lw=1.8))
    if particulas:  # patrón fijo de partículas suspendidas (ilustrativo)
        for i in range(-3, 4):
            for j in range(-3, 4):
                x, y = (i + 0.35 * (j % 2)) * R / 3.6, j * R / 3.6
                if x * x + y * y < (0.85 * R) ** 2:
                    ax.add_patch(Circle((x, y), 0.035 * R, fc=C["material_borde"], ec="none"))
    ax.add_patch(Circle((0, 0), 0.07 * R, fc="none", ec=C["aire"], lw=1.4))
    ax.add_patch(Circle((0, 0), 0.02 * R, fc=C["aire"], ec="none"))
    cota(ax, (-R, -R * 1.04), (R, -R * 1.04), f"Ø {num(D, 0)} mm", desplazamiento=-0.22 * R)
    if texto_flujo:
        ax.text(0, R * 1.22, texto_flujo, ha="center", va="bottom", fontsize=7, color=C["aire"])
    limites(ax, -1.3 * R, 1.3 * R, -1.65 * R, 1.6 * R)


def _ventilador(ax, x: float, y: float, r: float, texto: str = "Ventilador") -> None:
    ax.add_patch(Circle((x, y), r, fc=C["relleno"], ec=C["estructura"], lw=1.4, zorder=3))
    for k in range(6):
        t = k * math.pi / 3
        ax.plot([x, x + 0.85 * r * math.cos(t)], [y, y + 0.85 * r * math.sin(t)], color=C["estructura"],
                lw=0.8, zorder=4)
    ax.text(x, y - r - 0.15, texto, ha="center", va="top", fontsize=7)


# -------------------------------------------------------------------------------------- ductos
def ductos(fig, d: dict, r) -> None:
    ax1 = fig.add_subplot(1, 3, 1)
    ax2 = fig.add_subplot(1, 3, (2, 3))
    cumple = r["cumple_velocidad"] if "cumple_velocidad" in r else None
    color = C["estructura"] if cumple is None else (C["ok"] if cumple else C["mal"])
    _seccion_tubo(ax1, r["diametro_m"], "Sección del ducto", color, texto_flujo=f"v = {num(d['velocidad'], 1)} m/s")

    preparar(ax2, "Sistema de extracción", False)
    caja_equipo(ax2, 0.0, 1.6, 1.4, 0.9, "Campana /\ncaptación")
    ax2.plot([1.4, 6.2], [2.05, 2.05], color=C["estructura"], lw=6, solid_capstyle="butt", alpha=0.35)
    flecha(ax2, (1.6, 2.05), (5.9, 2.05), color=C["aire"], lw=1.8)
    ax2.text(3.75, 2.35, f"L = {num(d['longitud'], 1)} m · Q = {num(d['caudal'], 0)} m³/h", ha="center",
             fontsize=7.5)
    ax2.text(3.75, 1.7, f"ΔP fricción {num(r['dp_friccion_pa'], 0)} Pa + accesorios {num(r['dp_accesorios_pa'], 0)} Pa",
             ha="center", fontsize=7.5)
    _ventilador(ax2, 6.7, 2.05, 0.5)
    rectangulo(ax2, 7.05, 2.3, 0.35, 1.6, C["relleno"], C["estructura"], lw=1.2)
    flecha(ax2, (7.22, 3.9), (7.22, 4.5), color=C["aire"])
    ax2.text(7.6, 3.2, "Descarga /\nchimenea", fontsize=7, va="center")
    lineas = [f"Diámetro: {num(r['diametro_mm'], 0)} mm", f"Reynolds: {num(r['reynolds'], 0)}",
              f"f de Darcy: {num(r['friccion'], 4)}",
              f"ΔP total: {num(r['dp_total_pa'], 0)} Pa ({num(r['dp_total_mmh2o'], 1)} mm H₂O)",
              f"Potencia: {num(r['potencia_kw'], 2)} kW ({num(r['potencia_hp'], 2)} HP)"]
    if cumple is not None:
        lineas.append(f"v mínima de transporte: {num(r['velocidad_minima'], 1)} m/s → "
                      + ("cumple" if cumple else "NO cumple (sedimenta)"))
    cuadro(ax2, lineas, x=0.0, y=0.0, ha="left", va="bottom")
    limites(ax2, -0.2, 8.6, -1.6, 4.7, margen=0.02)


# ------------------------------------------------------------------------------------ neumático
def neumatico(fig, d: dict, r) -> None:
    ax1 = fig.add_subplot(1, 3, 1)
    ax2 = fig.add_subplot(1, 3, (2, 3))
    _seccion_tubo(ax1, r["diametro_mm"] / 1000.0, "Sección de la tubería", particulas=True,
                  texto_flujo=f"v aire = {num(d['velocidad'], 1)} m/s")

    preparar(ax2, f"Transporte neumático — {d['fase'].lower()}", False)
    _ventilador(ax2, 0.6, 1.0, 0.45, "Soplador")
    ax2.plot([1.05, 2.0], [1.0, 1.0], color=C["estructura"], lw=5, alpha=0.35)
    poligono(ax2, [(1.75, 1.15), (2.45, 1.15), (2.85, 2.0), (1.35, 2.0)], C["material"], C["material_borde"], lw=1)
    ax2.text(1.25, 1.6, "Tolva +\nválvula\nrotativa", ha="right", va="center", fontsize=7)
    flecha(ax2, (2.1, 2.9), (2.1, 2.25), color=C["material_borde"])
    caja_equipo(ax2, 1.9, 0.75, 0.4, 0.5, "")
    ax2.plot([2.3, 6.4, 6.4], [1.0, 1.0, 3.0], color=C["estructura"], lw=5, alpha=0.35, solid_joinstyle="round")
    flecha(ax2, (2.6, 1.0), (5.8, 1.0), color=C["aire"], lw=1.6)
    ax2.text(4.3, 0.7, f"L equivalente = {num(d['longitud'], 1)} m · ΣK = {num(d['k_accesorios'], 2)}", ha="center",
             va="top", fontsize=7.5)
    poligono(ax2, [(5.9, 3.0), (6.9, 3.0), (6.9, 3.9), (6.4, 4.5), (5.9, 3.9)], C["relleno"], C["estructura"], lw=1.2)
    ax2.text(7.0, 3.6, "Receptor /\nfiltro", fontsize=7, va="center")
    lineas = [f"Aire: {num(d['caudal'], 0)} m³/h ({num(r['masa_aire_kg_h'], 0)} kg/h)",
              f"Relación de carga μ = {num(d['relacion'], 2)} kg/kg",
              f"Capacidad de sólidos: {num(r['capacidad_t_h'], 2)} t/h",
              f"ΔP aire {num(r['dp_aire_pa'], 0)} Pa + sólidos {num(r['dp_solidos_pa'], 0)} Pa",
              f"ΔP total: {num(r['dp_total_pa'], 0)} Pa ({num(r['dp_total_cmh2o'], 1)} cm H₂O)",
              f"Potencia del soplador: {num(r['potencia_kw'], 2)} kW"]
    cuadro(ax2, lineas, x=1.0, y=0.0, ha="right", va="bottom")
    limites(ax2, -0.1, 8.2, -1.8, 4.7, margen=0.02)


# ------------------------------------------------------------------------------------- colector
def colector(fig, d: dict, r) -> None:
    ax = fig.add_subplot(111)
    tipo = "pulse jet" if d["limpieza"] == COL.PULSE_JET else "tela tejida"
    preparar(ax, f"Colector de polvo de mangas ({tipo})", False)
    # carcasa, placa porta-mangas, cámara limpia y tolva
    rectangulo(ax, 2.0, 1.5, 3.0, 3.6, "#FAFAFA", C["estructura"], lw=1.8)
    ax.plot([2.0, 5.0], [4.4, 4.4], color=C["estructura"], lw=1.6)
    ax.text(3.5, 4.75, "cámara de aire limpio", ha="center", fontsize=7, color=C["tenue"])
    poligono(ax, [(2.0, 1.5), (5.0, 1.5), (3.85, 0.25), (3.15, 0.25)], "#FAFAFA", C["estructura"], lw=1.8)
    poligono(ax, [(2.55, 0.9), (4.45, 0.9), (3.85, 0.25), (3.15, 0.25)], C["material"], C["material_borde"], lw=0.6)
    for i in range(7):
        x = 2.25 + i * 0.4
        rectangulo(ax, x, 1.9, 0.2, 2.5, "#ECEFF1", C["tenue"], lw=0.8)
        if d["limpieza"] == COL.PULSE_JET:
            flecha(ax, (x + 0.1, 4.75 - 0.05), (x + 0.1, 4.45), color=C["caliente"], lw=0.8)
    ax.text(3.5, 3.15, f"Área filtrante\n{num(r['area_filtracion'], 1)} m²", ha="center", va="center", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=C["tenue"], lw=0.5))
    ax.text(3.5, 0.0, f"Polvo captado {num(r['polvo_kg_h'], 1)} kg/h\nTolva para {num(d['horas'], 0)} h: "
            f"{num(r['volumen_tolva'], 2)} m³", ha="center", va="top", fontsize=7, color=C["material_borde"])
    # entrada sucia y salida limpia
    ax.plot([0.0, 2.0], [2.6, 2.6], color=C["estructura"], lw=7, alpha=0.3)
    flecha(ax, (0.1, 2.6), (1.9, 2.6), color=C["material_borde"], lw=1.6)
    ax.text(1.0, 2.95, f"Aire con polvo\n{num(d['caudal'], 0)} m³/h · Ø {num(r['diametro_mm'], 0)} mm",
            ha="center", va="bottom", fontsize=7)
    ax.plot([5.0, 6.6], [4.75, 4.75], color=C["estructura"], lw=7, alpha=0.3)
    flecha(ax, (5.1, 4.75), (6.3, 4.75), color=C["aire"], lw=1.6)
    _ventilador(ax, 7.0, 4.75, 0.42)
    flecha(ax, (7.0, 5.2), (7.0, 5.9), "aire limpio", color=C["aire"], lado_texto="fin")
    cuadro(ax, [f"Relación aire/tela: {num(r['relacion_aire_tela'], 2)} m/min ({num(r['relacion_aire_tela_ftmin'], 2)} ft/min)",
                f"ΔP total: {num(r['dp_total_mmh2o'], 0)} mm H₂O ({num(r['dp_total_pa'], 0)} Pa)",
                f"Potencia del ventilador: {num(r['potencia_kw'], 2)} kW ({num(r['potencia_hp'], 2)} HP)",
                "Mangas dibujadas: representativas (el número no se calcula)"],
          x=1.0, y=0.0, ha="right", va="bottom")
    limites(ax, -0.2, 9.8, -1.0, 6.2, margen=0.02)


# ------------------------------------------------------------------------------------- soplador
def soplador(fig, d: dict, r) -> None:
    ax1 = fig.add_subplot(1, 3, (1, 2))
    ax2 = fig.add_subplot(1, 3, 3)
    lobulos = d["tipo_maquina"] == SOP.LOBULOS
    preparar(ax1, "Soplador — succión y descarga", False)
    p1 = r["presion_succion_kpa"]
    p2 = p1 + d["presion"] / 1000.0
    flecha(ax1, (0.0, 1.5), (1.9, 1.5), color=C["aire"], lw=2)
    ax1.text(0.0, 1.85, f"Succión\np₁ = {num(p1, 2)} kPa abs\nT₁ = {num(d['temperatura'], 1)} °C\n"
             f"Q = {num(d['caudal'], 0)} m³/h", fontsize=7.5, va="bottom")
    if lobulos:
        caja_equipo(ax1, 2.0, 0.7, 1.8, 1.6, "")
        for dx in (-0.35, 0.35):
            ax1.add_patch(Ellipse((2.9 + dx, 1.5), 0.55, 1.1, fc="#CFD8DC", ec=C["estructura"], lw=1.2, zorder=4))
    else:
        ax1.add_patch(Circle((2.9, 1.5), 0.85, fc=C["relleno"], ec=C["estructura"], lw=1.6))
        for k in range(8):
            t = k * math.pi / 4
            ax1.plot([2.9 + 0.2 * math.cos(t), 2.9 + 0.75 * math.cos(t + 0.4)],
                     [1.5 + 0.2 * math.sin(t), 1.5 + 0.75 * math.sin(t + 0.4)], color=C["estructura"], lw=0.9)
    ax1.text(2.9, 0.45, "Soplador de lóbulos (Roots)" if lobulos else r["tipo"], ha="center", va="top", fontsize=7.5)
    ax1.text(2.9, 2.55, f"Potencia al eje {num(r['potencia_eje_kw'], 2)} kW ({num(r['potencia_eje_hp'], 2)} HP)",
             ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax1.plot([3.8, 6.0], [1.5, 1.5], color=C["estructura"], lw=6, alpha=0.3)
    flecha(ax1, (3.9, 1.5), (6.2, 1.5), color=C["caliente"], lw=2)
    ax1.text(6.25, 1.5, f"Descarga\np₂ = {num(p2, 2)} kPa abs\nΔp = {num(d['presion'], 0)} Pa\n"
             f"T₂ ≈ {num(r['t_descarga'], 1)} °C", fontsize=7.5, va="center")
    cuadro(ax1, [f"Flujo másico: {num(r['masa_kg_h'], 0)} kg/h", f"Relación de presiones: {num(r['relacion_presiones'], 3)}",
                 f"Potencia adiabática: {num(r['potencia_adiabatica_kw'], 2)} kW",
                 f"Potencia incompresible ΔP·Q/η: {num(r['potencia_incompresible_kw'], 2)} kW"],
          x=0.0, y=0.0, ha="left", va="bottom")
    limites(ax1, -0.1, 7.6, -1.4, 3.3, margen=0.02)
    _seccion_tubo(ax2, r["diametro_mm"] / 1000.0, "Tubería de descarga", texto_flujo=f"v = {num(d['velocidad'], 1)} m/s")


# ----------------------------------------------------------------------------------------- vacío
def vacio(fig, d: dict, r) -> None:
    ax1 = fig.add_subplot(1, 3, (1, 2))
    ax2 = fig.add_subplot(1, 3, 3)
    ps = d["presion_succion"]
    pd = r["presion_descarga_kpa"]
    preparar(ax1, "Bomba de vacío — sistema", False)
    rectangulo(ax1, 0.0, 0.8, 1.5, 1.8, "#FAFAFA", C["estructura"], lw=1.6)
    ax1.text(0.75, 1.7, f"Proceso\n{num(ps, 2)} kPa abs\n{num(d['temperatura'], 1)} °C", ha="center", va="center",
             fontsize=7.5)
    ax1.plot([1.5, 3.2], [1.7, 1.7], color=C["estructura"], lw=6, alpha=0.3)
    flecha(ax1, (1.6, 1.7), (3.1, 1.7), color=C["aire"], lw=1.8)
    txt_ducto = f"Q = {num(r['caudal_m3h'], 1)} m³/h"
    if "diametro_ducto_mm" in r:
        txt_ducto += f"\nØ {num(r['diametro_ducto_mm'], 0)} mm a {num(r['velocidad_ducto'], 1)} m/s"
    ax1.text(2.35, 1.95, txt_ducto, ha="center", va="bottom", fontsize=7)
    ax1.add_patch(Circle((3.9, 1.7), 0.7, fc=C["relleno"], ec=C["estructura"], lw=1.6))
    ax1.add_patch(Circle((3.9, 1.7), 0.25, fc="#CFD8DC", ec=C["estructura"], lw=1.0))
    ax1.text(3.9, 0.85, r["tipo"], ha="center", va="top", fontsize=7.5)
    ax1.plot([4.6, 6.0], [1.7, 1.7], color=C["estructura"], lw=6, alpha=0.3)
    flecha(ax1, (4.7, 1.7), (6.1, 1.7), color=C["caliente"], lw=1.8)
    ax1.text(6.15, 1.7, f"Descarga\n{num(pd, 2)} kPa abs", fontsize=7.5, va="center")
    cuadro(ax1, [f"Relación de compresión: {num(r['relacion_compresion'], 2)}",
                 f"Flujo másico: {num(r['masa_kg_h'], 2)} kg/h",
                 f"Potencia teórica (adiabática): {num(r['potencia_teorica_kw'], 3)} kW",
                 f"Potencia isotérmica: {num(r['potencia_isotermica_kw'], 3)} kW",
                 f"Potencia al eje: {num(r['potencia_eje_kw'], 3)} kW ({num(r['potencia_eje_hp'], 2)} HP)"],
          x=0.0, y=0.0, ha="left", va="bottom")
    limites(ax1, -0.1, 7.4, -1.6, 3.0, margen=0.02)

    preparar(ax2, "Escala de presión absoluta", True, "kPa")
    tope = max(pd, ps) * 1.1
    rectangulo(ax2, 0, 0, 1.0, tope, "#FAFAFA", C["estructura"], lw=1.2)
    rectangulo(ax2, 0, 0, 1.0, ps, "#BBDEFB", C["aire"], lw=0.8)
    for valor, texto, color in ((ps, f"succión {num(ps, 2)}", C["aire"]), (pd, f"descarga {num(pd, 2)}", C["caliente"])):
        ax2.plot([-0.15, 1.15], [valor, valor], color=color, lw=1.4)
        ax2.text(1.25, valor, texto, va="center", fontsize=7, color=color)
    ax2.text(0.5, -0.03 * tope, "0 (vacío absoluto)", ha="center", va="top", fontsize=6.5, color=C["tenue"])
    cota(ax2, (-0.15, ps), (-0.15, pd), f"p₂ − p₁ = {num(pd - ps, 1)} kPa", desplazamiento=0.35,
         fs=7)
    ax2.set_aspect("auto")
    ax2.set_xlim(-1.0, 3.0)
    ax2.set_ylim(-0.12 * tope, 1.08 * tope)
