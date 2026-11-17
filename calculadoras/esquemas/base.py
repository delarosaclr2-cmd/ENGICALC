"""Utilidades de dibujo para los esquemas: cotas, flechas, etiquetas y cuadros de datos."""
from __future__ import annotations

import math

from matplotlib.patches import Arc, FancyArrowPatch, Polygon, Rectangle

C = {
    "estructura": "#455A64",
    "relleno": "#ECEFF1",
    "material": "#D7B98E",
    "material_borde": "#8D6E63",
    "aire": "#1E88E5",
    "agua": "#0277BD",
    "caliente": "#D32F2F",
    "frio": "#1565C0",
    "cota": "#263238",
    "carga": "#C62828",
    "ok": "#2E7D32",
    "mal": "#C62828",
    "tenue": "#90A4AE",
    "texto": "#212121",
}

FUENTE = 8


def num(valor: float, decimales: int = 2) -> str:
    """Número con espacio como separador de miles (como en la tabla de resultados)."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", " ")


def preparar(ax, titulo: str, a_escala: bool, unidades: str = "m") -> None:
    """Ejes sin marcos, proporción 1:1 y leyenda de escala."""
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(titulo, fontsize=10, fontweight="bold", color=C["texto"], loc="left")
    nota = (f"Dibujo a escala · cotas en {unidades}" if a_escala
            else "Esquema sin escala · valores del cálculo")
    ax.text(0.0, -0.02, nota, transform=ax.transAxes, fontsize=7, color=C["tenue"], va="top", ha="left",
            style="italic")


def limites(ax, xmin: float, xmax: float, ymin: float, ymax: float, margen: float = 0.06) -> None:
    dx, dy = xmax - xmin, ymax - ymin
    m = margen * max(dx, dy)
    ax.set_xlim(xmin - m, xmax + m)
    ax.set_ylim(ymin - m, ymax + m)


def cota(ax, p1, p2, texto: str, desplazamiento: float = 0.0, color: str = C["cota"], fs: int = FUENTE,
         extension: bool = True) -> None:
    """Línea de cota entre p1 y p2, desplazada perpendicularmente (a la izquierda de p1→p2)."""
    (x1, y1), (x2, y2) = p1, p2
    largo = math.hypot(x2 - x1, y2 - y1)
    if largo == 0:
        return
    nx, ny = -(y2 - y1) / largo, (x2 - x1) / largo
    q1 = (x1 + nx * desplazamiento, y1 + ny * desplazamiento)
    q2 = (x2 + nx * desplazamiento, y2 + ny * desplazamiento)
    if extension and desplazamiento:
        extra = 0.12 * abs(desplazamiento) * (1 if desplazamiento > 0 else -1)
        for p, q in ((p1, q1), (p2, q2)):
            ax.plot([p[0], q[0] + nx * extra], [p[1], q[1] + ny * extra], color=color, lw=0.5, alpha=0.7)
    ax.add_patch(FancyArrowPatch(q1, q2, arrowstyle="<|-|>", mutation_scale=7, color=color, lw=0.8,
                                 shrinkA=0, shrinkB=0))
    angulo = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if angulo > 90.01 or angulo < -89.99:
        angulo -= 180 if angulo > 0 else -180
    ax.text((q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2, texto, rotation=angulo, rotation_mode="anchor",
            ha="center", va="center", fontsize=fs, color=color,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))


def flecha(ax, desde, hasta, texto: str | None = None, color: str = C["aire"], lw: float = 1.6,
           fs: int = FUENTE, alinear: str = "center", lado_texto: str = "inicio", estilo: str = "-|>") -> None:
    ax.add_patch(FancyArrowPatch(desde, hasta, arrowstyle=estilo, mutation_scale=12, color=color, lw=lw,
                                 shrinkA=0, shrinkB=0))
    if texto:
        x, y = desde if lado_texto == "inicio" else hasta
        ax.text(x, y, texto, ha=alinear, va="center", fontsize=fs, color=color,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=0.5, alpha=0.95))


def angulo(ax, centro, radio: float, desde_grados: float, hasta_grados: float, texto: str,
           color: str = C["cota"], fs: int = FUENTE, radio_texto: float = 1.35,
           angulo_texto: float | None = None) -> None:
    """Arco de ángulo con su valor (el texto puede colocarse en otro ángulo para no tapar líneas)."""
    a1, a2 = sorted((desde_grados, hasta_grados))
    ax.add_patch(Arc(centro, 2 * radio, 2 * radio, theta1=a1, theta2=a2, color=color, lw=0.8))
    if not texto:
        return
    medio = math.radians((a1 + a2) / 2 if angulo_texto is None else angulo_texto)
    ax.text(centro[0] + radio_texto * radio * math.cos(medio), centro[1] + radio_texto * radio * math.sin(medio),
            texto, ha="center", va="center", fontsize=fs, color=color,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))


def cuadro(ax, lineas: list[str], x: float = 1.0, y: float = 1.0, ha: str = "right", va: str = "top",
           titulo: str | None = None) -> None:
    """Cuadro de datos en coordenadas de los ejes (0–1)."""
    texto = "\n".join(([titulo] if titulo else []) + lineas)
    ax.text(x, y, texto, transform=ax.transAxes, ha=ha, va=va, fontsize=FUENTE, color=C["texto"],
            family="DejaVu Sans", linespacing=1.35,
            bbox=dict(boxstyle="round,pad=0.4", fc="#FFFFFF", ec=C["tenue"], lw=0.6, alpha=0.95))


def poligono(ax, puntos, color: str, borde: str | None = None, lw: float = 1.0, alpha: float = 1.0,
             hatch: str | None = None, zorder: int = 1):
    parche = Polygon(puntos, closed=True, fc=color, ec=borde or color, lw=lw, alpha=alpha, hatch=hatch,
                     zorder=zorder)
    ax.add_patch(parche)
    return parche


def rectangulo(ax, x: float, y: float, ancho: float, alto: float, color: str, borde: str | None = None,
               lw: float = 1.0, angulo_grados: float = 0.0, zorder: int = 1, hatch: str | None = None):
    parche = Rectangle((x, y), ancho, alto, angle=angulo_grados, fc=color, ec=borde or color, lw=lw,
                       zorder=zorder, hatch=hatch)
    ax.add_patch(parche)
    return parche


def rotar(puntos, angulo_grados: float, origen=(0.0, 0.0)):
    """Gira una lista de puntos alrededor de 'origen'."""
    a = math.radians(angulo_grados)
    ca, sa = math.cos(a), math.sin(a)
    ox, oy = origen
    return [(ox + (x - ox) * ca - (y - oy) * sa, oy + (x - ox) * sa + (y - oy) * ca) for x, y in puntos]


def area_poligono(puntos) -> float:
    """Área por la fórmula del agrimensor (para verificar que el dibujo coincide con el cálculo)."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(puntos, puntos[1:] + puntos[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def caja_equipo(ax, x: float, y: float, ancho: float, alto: float, texto: str, color: str = C["relleno"],
                borde: str = C["estructura"], fs: int = FUENTE) -> None:
    """Bloque de equipo para los esquemas de proceso."""
    rectangulo(ax, x, y, ancho, alto, color, borde, lw=1.2, zorder=2)
    ax.text(x + ancho / 2, y + alto / 2, texto, ha="center", va="center", fontsize=fs, color=C["texto"], zorder=3)


def interrupcion(ax, x1: float, x2: float, y: float, alto: float, color: str = C["estructura"]) -> None:
    """Línea de interrupción en zigzag (tramo omitido del dibujo)."""
    xs = [x1, x1 + (x2 - x1) * 0.4, x1 + (x2 - x1) * 0.47, x1 + (x2 - x1) * 0.53, x1 + (x2 - x1) * 0.6, x2]
    ys = [y, y, y + alto, y - alto, y, y]
    ax.plot(xs, ys, color=color, lw=0.9, zorder=5)
