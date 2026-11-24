"""Sistema visual ENGICALC v1 para Tkinter: colores, tipografía, estilos ttk y piezas comunes.

Traduce a Tkinter el «Sistema de componentes» del rediseño de interfaz (RMR Ingeniería):

- Marino y azul salen del logotipo; el cian del logotipo queda solo para la marca.
- IBM Plex Sans / IBM Plex Mono si están instaladas; si no, Segoe UI / Consolas (Windows) o
  DejaVu Sans / DejaVu Sans Mono (Linux), como indica el diseño.
- Una sola acción primaria por pantalla (azul), unidades siempre visibles en una pastilla,
  avisos con icono y título de tipo, insignias de nivel V / E / O / D con color propio.

Este módulo solo cambia la apariencia. Ningún cálculo, unidad, texto técnico, validación ni
exportación depende de él.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# ---------------------------------------------------------------------------
# Color (sección 01 del sistema de componentes)
# ---------------------------------------------------------------------------
MARINO = "#0E2A5C"          # navegación y títulos
MARINO_LOGO = "#1C3F94"     # encabezados de grupo de resultados
AZUL = "#1F5FBF"            # acción primaria, enlaces, foco
AZUL_HOVER = "#1A52A6"
AZUL_50 = "#E6EEFB"         # selección
CIAN = "#2EA8E6"            # solo marca: nunca para texto

TEXTO = "#142033"
TEXTO_2 = "#536175"         # contraste 6.1:1 sobre blanco
TEXTO_3 = "#8792A2"         # deshabilitado
ICONO_VACIO = "#9AA6B6"
BORDE_CONTROL = "#C3CCD8"
BORDE = "#D5DCE5"           # tarjetas
BORDE_UNIDAD = "#E1E6ED"
DIVISOR = "#E8ECF1"
DIVISOR_FILA = "#EEF1F5"
FONDO = "#F3F5F8"           # fondo de la aplicación
SUPERFICIE = "#FFFFFF"
SUPERFICIE_2 = "#F8FAFC"    # encabezados de tabla y pies de tarjeta
RESALTE = "#F2F6FD"         # filas clave y paso del cursor
AUTOMATICO = "#EEF2F7"      # valores derivados (solo lectura)
DESHABILITADO = "#EEF1F5"

ERROR = "#A61B1B"
ERROR_FONDO = "#FFF8F8"
PENDIENTE_BORDE = "#E7B566"
PENDIENTE_FONDO = "#FFFBF2"
CORRECTO = "#1B6B3F"
ADVERTENCIA = "#8A4B00"

# Series de gráfica y trazo de esquemas (sección 09)
SERIE_1 = "#1F5FBF"
SERIE_2 = "#C8641A"
SERIE_REFERENCIA = "#7A869A"
REJILLA = "#E8ECF1"
GEOMETRIA = "#2B3A4E"

# Tonos de aviso (sección 08): color de icono/texto fuerte, fondo, borde y texto del cuerpo
TONOS = {
    "critico": dict(color="#A61B1B", fondo="#FDECEC", borde="#EBB1B1", texto="#6E1010", titulo="Crítico",
                    icono="error"),
    "alto": dict(color="#C2410C", fondo="#FDEBDD", borde="#F3B58A", texto="#7C2D12", titulo="Alto",
                 icono="advertencia"),
    "advertencia": dict(color="#8A4B00", fondo="#FFF3DD", borde="#F0C27A", texto="#5E3300", titulo="Advertencia",
                        icono="advertencia"),
    "info": dict(color="#1F5FBF", fondo="#E8F0FC", borde="#B7CDF1", texto="#0E2A5C", titulo="Información",
                 icono="info"),
    "correcto": dict(color="#1B6B3F", fondo="#E3F2E9", borde="#A9D3B9", texto="#14532D", titulo="Correcto",
                     icono="correcto"),
    "nota": dict(color="#536175", fondo="#F3F5F8", borde="#D5DCE5", texto="#142033", titulo="Nota técnica",
                 icono="nota"),
}

# Insignias de nivel de confianza (sección 06): fondo, letra y contorno
NIVEL_ESTILO = {
    "V": ("#E3F2E9", "#1B6B3F", None),
    "E": ("#E6EEFB", "#1F5FBF", None),
    "O": ("#FFF1D6", "#8A4B00", "#E7B566"),   # contorno ámbar: verificar con fabricante o norma
    "D": ("#EEF1F5", "#536175", None),
}

# ---------------------------------------------------------------------------
# Tipografía (sección 02)
# ---------------------------------------------------------------------------
FAMILIAS_SANS = ("IBM Plex Sans", "Segoe UI", "DejaVu Sans", "Helvetica")
FAMILIAS_MONO = ("IBM Plex Mono", "Consolas", "DejaVu Sans Mono", "Courier New")

# nombre: (familia, tamaño en puntos, peso). 14 px de la maqueta ≈ 10 pt.
FUENTES = {
    "titulo": ("sans", 19, "bold"),
    "titulo_app": ("sans", 16, "bold"),
    "titulo_panel": ("sans", 14, "bold"),
    "subtitulo": ("sans", 11, "bold"),
    "grupo": ("sans", 10, "bold"),
    "cuerpo": ("sans", 10, "normal"),
    "cuerpo_negrita": ("sans", 10, "bold"),
    "pequeno": ("sans", 9, "normal"),
    "pequeno_negrita": ("sans", 9, "bold"),
    "etiqueta": ("sans", 8, "bold"),
    "mono": ("mono", 10, "normal"),
    "mono_negrita": ("mono", 10, "bold"),
    "mono_pequeno": ("mono", 9, "normal"),
    "mono_pequeno_negrita": ("mono", 9, "bold"),
    "kpi": ("mono", 18, "bold"),
    "kpi_unidad": ("mono", 11, "normal"),
}


def familias(widget: tk.Misc) -> tuple[str, str]:
    """(familia sans, familia mono) disponibles en este equipo, en el orden de preferencia del diseño."""
    disponibles = set(tkfont.families(widget))
    sans = next((f for f in FAMILIAS_SANS if f in disponibles), "TkDefaultFont")
    mono = next((f for f in FAMILIAS_MONO if f in disponibles), "TkFixedFont")
    return sans, mono


def fuente(nombre: str) -> str:
    """Nombre Tk de la fuente con nombre del tema (utilizable en ``font=``)."""
    return "Engi_" + nombre


def _raiz(widget: tk.Misc) -> tk.Misc:
    return widget._root()


def _crear_fuentes(raiz: tk.Misc) -> None:
    existentes = set(tkfont.names(raiz))
    sans, mono = familias(raiz)
    referencias = getattr(raiz, "_engicalc_fuentes", {})
    for nombre, (familia, tamano, peso) in FUENTES.items():
        nombre_tk = fuente(nombre)
        if nombre_tk in existentes:
            continue
        referencias[nombre_tk] = tkfont.Font(root=raiz, name=nombre_tk, family=sans if familia == "sans" else mono,
                                             size=tamano, weight=peso)
    # las fuentes con nombre se borran al recolectarse el objeto de Python: se conservan en la raíz
    raiz._engicalc_fuentes = referencias


# ---------------------------------------------------------------------------
# Estilos ttk
# ---------------------------------------------------------------------------
def aplicar(widget: tk.Misc) -> ttk.Style:
    """Activa el tema ENGICALC en el intérprete Tk de ``widget``. Se puede llamar varias veces."""
    raiz = _raiz(widget)
    estilo = ttk.Style(raiz)
    if getattr(raiz, "_engicalc_tema", False):
        return estilo
    _crear_fuentes(raiz)
    if "clam" in estilo.theme_names():  # «vista» no permite colorear botones ni bordes
        estilo.theme_use("clam")
    cuerpo, pequeno = fuente("cuerpo"), fuente("pequeno")

    estilo.configure(".", background=FONDO, foreground=TEXTO, font=cuerpo, bordercolor=BORDE_CONTROL,
                     lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, troughcolor=FONDO, fieldbackground=SUPERFICIE,
                     selectbackground=AZUL_50, selectforeground=TEXTO, insertcolor=TEXTO, focuscolor=AZUL)
    estilo.map(".", foreground=[("disabled", TEXTO_3)])
    for nombre, fondo in (("TFrame", FONDO), ("Superficie.TFrame", SUPERFICIE), ("Pie.TFrame", SUPERFICIE_2)):
        estilo.configure(nombre, background=fondo)
    estilo.configure("TLabel", background=FONDO, foreground=TEXTO)
    estilo.configure("Superficie.TLabel", background=SUPERFICIE)

    # Botones: secundario (por defecto), primario, fantasma, peligro y compacto
    estilo.configure("TButton", background=SUPERFICIE, foreground=TEXTO, bordercolor=BORDE_CONTROL,
                     lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, padding=(12, 5), focusthickness=1,
                     focuscolor=AZUL_50, font=cuerpo, anchor="center", width=0)  # ancho natural del texto
    estilo.map("TButton",
               background=[("disabled", DESHABILITADO), ("pressed", AZUL_50), ("active", RESALTE)],
               lightcolor=[("disabled", DESHABILITADO), ("pressed", AZUL_50), ("active", RESALTE)],
               darkcolor=[("disabled", DESHABILITADO), ("pressed", AZUL_50), ("active", RESALTE)],
               bordercolor=[("disabled", BORDE_UNIDAD), ("focus", AZUL)],
               foreground=[("disabled", TEXTO_3)])
    estilo.configure("Primario.TButton", background=AZUL, foreground=SUPERFICIE, bordercolor=AZUL,
                     lightcolor=AZUL, darkcolor=AZUL, focuscolor=AZUL, font=fuente("cuerpo_negrita"))
    estilo.map("Primario.TButton",
               background=[("disabled", DESHABILITADO), ("pressed", MARINO), ("active", AZUL_HOVER)],
               lightcolor=[("disabled", DESHABILITADO), ("pressed", MARINO), ("active", AZUL_HOVER)],
               darkcolor=[("disabled", DESHABILITADO), ("pressed", MARINO), ("active", AZUL_HOVER)],
               bordercolor=[("disabled", BORDE_UNIDAD), ("focus", MARINO)],
               foreground=[("disabled", TEXTO_3)])
    for nombre, fondo in (("Fantasma.TButton", SUPERFICIE), ("FantasmaFondo.TButton", FONDO),
                          ("FantasmaPie.TButton", SUPERFICIE_2)):
        estilo.configure(nombre, background=fondo, foreground=AZUL, bordercolor=fondo, lightcolor=fondo,
                         darkcolor=fondo, focuscolor=fondo)
        estilo.map(nombre, background=[("active", RESALTE)], lightcolor=[("active", RESALTE)],
                   darkcolor=[("active", RESALTE)], foreground=[("active", MARINO), ("disabled", TEXTO_3)],
                   bordercolor=[("focus", AZUL_50)])
    estilo.configure("Peligro.TButton", foreground=ERROR, bordercolor="#E5B4B4")
    estilo.configure("Compacto.TButton", padding=(9, 2), font=pequeno)
    estilo.configure("CompactoActivo.TButton", padding=(9, 2), font=pequeno, background=AZUL_50, bordercolor=AZUL,
                     lightcolor=AZUL_50, darkcolor=AZUL_50, foreground=MARINO)

    # Menús desplegables con aspecto de botón (Caso ▾, Exportar ▾); la flecha va en el texto
    estilo.layout("TMenubutton", [("Menubutton.border", {"sticky": "nswe", "children": [
        ("Menubutton.focus", {"sticky": "nswe", "children": [
            ("Menubutton.padding", {"sticky": "nswe", "children": [
                ("Menubutton.label", {"sticky": ""})]})]})]})])
    estilo.configure("TMenubutton", background=SUPERFICIE, foreground=TEXTO, bordercolor=BORDE_CONTROL,
                     lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, padding=(12, 5), font=cuerpo, focuscolor=AZUL_50,
                     width=0)
    estilo.map("TMenubutton", background=[("disabled", DESHABILITADO), ("pressed", AZUL_50), ("active", RESALTE)],
               lightcolor=[("pressed", AZUL_50), ("active", RESALTE)], darkcolor=[("pressed", AZUL_50),
                                                                                   ("active", RESALTE)],
               bordercolor=[("focus", AZUL)])
    estilo.layout("Primario.TMenubutton", estilo.layout("TMenubutton"))
    estilo.configure("Primario.TMenubutton", background=AZUL, foreground=SUPERFICIE, bordercolor=AZUL,
                     lightcolor=AZUL, darkcolor=AZUL, font=fuente("cuerpo_negrita"))
    estilo.map("Primario.TMenubutton", background=[("pressed", MARINO), ("active", AZUL_HOVER)],
               lightcolor=[("pressed", MARINO), ("active", AZUL_HOVER)],
               darkcolor=[("pressed", MARINO), ("active", AZUL_HOVER)], bordercolor=[("focus", MARINO)],
               foreground=[("disabled", TEXTO_3)])

    # Campos: normal, foco, error (estado «invalid»), pendiente, automático (solo lectura) y deshabilitado
    estilo.configure("TEntry", fieldbackground=SUPERFICIE, foreground=TEXTO, bordercolor=BORDE_CONTROL,
                     lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, padding=(8, 4), insertcolor=TEXTO)
    estilo.map("TEntry",
               bordercolor=[("invalid", ERROR), ("focus", AZUL)],
               lightcolor=[("invalid", ERROR_FONDO), ("focus", "#BCD0EF")],
               darkcolor=[("invalid", ERROR_FONDO), ("focus", "#BCD0EF")],
               fieldbackground=[("invalid", ERROR_FONDO), ("disabled", DESHABILITADO), ("readonly", AUTOMATICO)],
               foreground=[("disabled", TEXTO_3), ("readonly", TEXTO_2)])
    estilo.configure("Pendiente.TEntry", fieldbackground=PENDIENTE_FONDO, bordercolor=PENDIENTE_BORDE,
                     lightcolor=PENDIENTE_FONDO, darkcolor=PENDIENTE_FONDO)
    estilo.map("Pendiente.TEntry", bordercolor=[("invalid", ERROR), ("focus", AZUL)],
               fieldbackground=[("invalid", ERROR_FONDO)], lightcolor=[("focus", "#BCD0EF")],
               darkcolor=[("focus", "#BCD0EF")])
    estilo.configure("TCombobox", fieldbackground=SUPERFICIE, foreground=TEXTO, background=SUPERFICIE,
                     bordercolor=BORDE_CONTROL, lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, arrowcolor=TEXTO_2,
                     padding=(8, 4), arrowsize=13)
    estilo.map("TCombobox",
               fieldbackground=[("disabled", DESHABILITADO), ("readonly", SUPERFICIE)],
               background=[("active", RESALTE), ("readonly", SUPERFICIE)],
               bordercolor=[("invalid", ERROR), ("focus", AZUL)],
               lightcolor=[("focus", "#BCD0EF")], darkcolor=[("focus", "#BCD0EF")],
               foreground=[("disabled", TEXTO_3), ("readonly", TEXTO)],
               selectbackground=[("readonly", SUPERFICIE)], selectforeground=[("readonly", TEXTO)],
               arrowcolor=[("disabled", TEXTO_3)])
    for nombre, fondo in (("TCheckbutton", FONDO), ("Superficie.TCheckbutton", SUPERFICIE),
                          ("Pie.TCheckbutton", SUPERFICIE_2)):
        estilo.configure(nombre, background=fondo, foreground=TEXTO, indicatorbackground=SUPERFICIE,
                         indicatorforeground=SUPERFICIE, upperbordercolor=BORDE_CONTROL,
                         lowerbordercolor=BORDE_CONTROL, indicatormargin=(0, 0, 8, 0), focuscolor=fondo)
        estilo.map(nombre, indicatorbackground=[("selected", AZUL), ("disabled", DESHABILITADO)],
                   upperbordercolor=[("selected", AZUL)], lowerbordercolor=[("selected", AZUL)],
                   background=[("active", fondo)])
    for nombre, fondo in (("TRadiobutton", FONDO), ("Superficie.TRadiobutton", SUPERFICIE)):
        estilo.configure(nombre, background=fondo, indicatorbackground=SUPERFICIE, indicatorforeground=AZUL,
                         upperbordercolor=BORDE_CONTROL, lowerbordercolor=BORDE_CONTROL, focuscolor=fondo)
        estilo.map(nombre, background=[("active", fondo)], indicatorbackground=[("selected", SUPERFICIE)])

    # Barras de desplazamiento discretas
    for orientacion in ("Vertical", "Horizontal"):
        estilo.configure(f"{orientacion}.TScrollbar", background="#D3DAE3", troughcolor=FONDO, bordercolor=FONDO,
                         lightcolor="#D3DAE3", darkcolor="#D3DAE3", arrowcolor=TEXTO_2, gripcount=0, arrowsize=12)
        estilo.map(f"{orientacion}.TScrollbar", background=[("active", BORDE_CONTROL)],
                   lightcolor=[("active", BORDE_CONTROL)], darkcolor=[("active", BORDE_CONTROL)])

    # Tablas
    estilo.configure("Treeview", background=SUPERFICIE, fieldbackground=SUPERFICIE, foreground=TEXTO,
                     bordercolor=BORDE, lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, rowheight=_px(raiz, 28),
                     font=cuerpo)
    estilo.map("Treeview", background=[("selected", AZUL_50)], foreground=[("selected", MARINO)])
    estilo.configure("Treeview.Heading", background=SUPERFICIE_2, foreground=TEXTO_2, font=fuente("etiqueta"),
                     bordercolor=BORDE_CONTROL, lightcolor=SUPERFICIE_2, darkcolor=SUPERFICIE_2, relief="flat",
                     padding=(8, 6))
    estilo.map("Treeview.Heading", background=[("active", DIVISOR_FILA)])
    estilo.configure("Catalogo.Treeview", rowheight=_px(raiz, 32), bordercolor=SUPERFICIE)

    # Pestañas: las de ttk (memorias y aplicaciones) y un cuaderno sin pestañas para la barra propia
    estilo.configure("TNotebook", background=SUPERFICIE, bordercolor=BORDE, lightcolor=SUPERFICIE,
                     darkcolor=SUPERFICIE, tabmargins=(0, 0, 0, 0))
    estilo.configure("TNotebook.Tab", background=FONDO, foreground=TEXTO_2, bordercolor=BORDE,
                     lightcolor=FONDO, darkcolor=FONDO, padding=(14, 6), font=cuerpo)
    estilo.map("TNotebook.Tab", background=[("selected", SUPERFICIE), ("active", RESALTE)],
               lightcolor=[("selected", SUPERFICIE)], foreground=[("selected", MARINO)],
               font=[("selected", fuente("cuerpo_negrita"))], expand=[("selected", (0, 0, 0, 0))])
    estilo.layout("Oculto.TNotebook.Tab", [])
    estilo.configure("Oculto.TNotebook", background=SUPERFICIE, borderwidth=0, bordercolor=SUPERFICIE,
                     lightcolor=SUPERFICIE, darkcolor=SUPERFICIE, tabmargins=0)
    # Subpestañas segmentadas (nivel 2)
    estilo.configure("Segmentado.TNotebook", background=SUPERFICIE, bordercolor=SUPERFICIE, lightcolor=SUPERFICIE,
                     darkcolor=SUPERFICIE, tabmargins=(0, 0, 0, 6))
    estilo.configure("Segmentado.TNotebook.Tab", background=DESHABILITADO, foreground=TEXTO_2,
                     bordercolor=DESHABILITADO, lightcolor=DESHABILITADO, darkcolor=DESHABILITADO,
                     padding=(12, 5), font=pequeno)
    estilo.map("Segmentado.TNotebook.Tab", background=[("selected", SUPERFICIE), ("active", "#E4E9F0")],
               bordercolor=[("selected", BORDE)], lightcolor=[("selected", SUPERFICIE)],
               foreground=[("selected", TEXTO)], font=[("selected", fuente("pequeno_negrita"))],
               expand=[("selected", (0, 0, 0, 0))])

    # Separadores de paneles y recuadros
    estilo.configure("TPanedwindow", background=FONDO)
    estilo.configure("Sash", sashthickness=_px(raiz, 10), gripcount=0, background=FONDO)
    estilo.configure("TLabelframe", background=SUPERFICIE, bordercolor=BORDE, lightcolor=SUPERFICIE,
                     darkcolor=SUPERFICIE, relief="solid", borderwidth=1)
    estilo.configure("TLabelframe.Label", background=SUPERFICIE, foreground=MARINO, font=fuente("grupo"))
    estilo.configure("TSeparator", background=DIVISOR)

    # Menús emergentes y listas de las listas desplegables
    for patron, valor in (("*Menu.font", cuerpo), ("*Menu.background", SUPERFICIE), ("*Menu.foreground", TEXTO),
                          ("*Menu.activeBackground", RESALTE), ("*Menu.activeForeground", MARINO),
                          ("*Menu.relief", "flat"), ("*Menu.activeBorderWidth", 0), ("*Menu.borderWidth", 1),
                          ("*TCombobox*Listbox.font", cuerpo), ("*TCombobox*Listbox.background", SUPERFICIE),
                          ("*TCombobox*Listbox.selectBackground", AZUL_50),
                          ("*TCombobox*Listbox.selectForeground", MARINO)):
        raiz.option_add(patron, valor)
    raiz._engicalc_tema = True
    return estilo


def _px(widget: tk.Misc, pixeles_96dpi: int) -> int:
    """Convierte una medida de la maqueta (px a 96 ppp) a la escala de la pantalla actual."""
    try:
        escala = float(widget.tk.call("tk", "scaling")) / (96 / 72)
    except (tk.TclError, ValueError):
        escala = 1.0
    return max(1, round(pixeles_96dpi * max(escala, 1.0)))


# ---------------------------------------------------------------------------
# Piezas comunes (Tk clásico: control total de color y borde)
# ---------------------------------------------------------------------------
def fondo_de(widget: tk.Misc) -> str:
    """Color de fondo efectivo de un contenedor (tk o ttk)."""
    try:
        return widget.cget("background")
    except tk.TclError:
        pass
    try:
        estilo = widget.cget("style") or widget.winfo_class()
        return ttk.Style(widget).lookup(estilo, "background") or FONDO
    except tk.TclError:
        return FONDO


def tarjeta(padre: tk.Misc, fondo: str = SUPERFICIE, borde: str = BORDE, **opciones) -> tk.Frame:
    """Tarjeta: superficie con borde de 1 px, sin sombra (sección 03)."""
    return tk.Frame(padre, background=fondo, highlightthickness=1, highlightbackground=borde,
                    highlightcolor=borde, **opciones)


def etiqueta(padre: tk.Misc, texto: str = "", estilo: str = "cuerpo", color: str = TEXTO,
             fondo: str | None = None, **opciones) -> tk.Label:
    opciones.setdefault("anchor", "w")
    opciones.setdefault("justify", "left")
    return tk.Label(padre, text=texto, font=fuente(estilo), foreground=color,
                    background=fondo or fondo_de(padre), borderwidth=0, padx=0, pady=0, **opciones)


def titulo_seccion(padre: tk.Misc, texto: str, fondo: str | None = None, color: str = TEXTO_2) -> tk.Label:
    """Etiqueta en mayúsculas (12 / 600) para encabezados de bloque."""
    return etiqueta(padre, texto.upper(), "etiqueta", color, fondo)


def separador(padre: tk.Misc, orientacion: str = "vertical", color: str = BORDE, largo: int = 22) -> tk.Frame:
    if orientacion == "vertical":
        return tk.Frame(padre, width=1, height=largo, background=color)
    return tk.Frame(padre, height=1, background=color)


def unidad(padre: tk.Misc, texto: str) -> tk.Label:
    """Pastilla fija de unidad que se lee como parte del dato."""
    return tk.Label(padre, text=texto or "—", font=fuente("mono_pequeno"), foreground=TEXTO_2,
                    background=FONDO, highlightthickness=1, highlightbackground=BORDE_UNIDAD,
                    highlightcolor=BORDE_UNIDAD, padx=4, pady=1, borderwidth=0)


def insignia_nivel(padre: tk.Misc, nivel: str, pequena: bool = False, fondo: str | None = None) -> tk.Label:
    claro, oscuro, contorno = NIVEL_ESTILO.get(nivel, NIVEL_ESTILO["D"])
    return tk.Label(padre, text=nivel, width=2, font=fuente("mono_pequeno_negrita"), foreground=oscuro,
                    background=claro, highlightthickness=1, highlightbackground=contorno or claro,
                    highlightcolor=contorno or claro, padx=1 if pequena else 3, pady=0 if pequena else 1,
                    borderwidth=0)


def chip(padre: tk.Misc, texto: str, tono: str = "nota", solido: bool = False) -> tk.Label:
    t = TONOS[tono]
    return tk.Label(padre, text=texto, font=fuente("pequeno"),
                    foreground=SUPERFICIE if solido else t["color"], background=t["color"] if solido else t["fondo"],
                    padx=8, pady=1, borderwidth=0, highlightthickness=1,
                    highlightbackground=t["color"] if solido else t["borde"])


# ---------------------------------------------------------------------------
# Iconografía: trazo de 1.8 px y 20 px, siempre acompañada de texto (sección 03)
# ---------------------------------------------------------------------------
def icono(padre: tk.Misc, nombre: str, color: str = TEXTO, fondo: str | None = None, tam: int = 20) -> tk.Canvas:
    tam = _px(padre, tam)
    c = tk.Canvas(padre, width=tam, height=tam, background=fondo or fondo_de(padre), highlightthickness=0,
                  borderwidth=0, takefocus=0)
    dibujar_icono(c, nombre, color, 0, 0, tam)
    return c


def dibujar_icono(c: tk.Canvas, nombre: str, color: str, x: float, y: float, tam: float) -> None:
    """Dibuja un icono de 24 unidades escalado a ``tam`` en (x, y)."""
    k = tam / 24.0
    g = max(1.4, 1.9 * k)

    def p(*pts):
        return [x + v * k if i % 2 == 0 else y + v * k for i, v in enumerate(pts)]

    if nombre == "advertencia":
        c.create_polygon(*p(12, 3, 22, 21, 2, 21), outline=color, fill="", width=g, joinstyle="round")
        c.create_line(*p(12, 10, 12, 15), fill=color, width=g, capstyle="round")
        c.create_line(*p(12, 18, 12, 18.6), fill=color, width=g + .6, capstyle="round")
    elif nombre == "info":
        c.create_oval(*p(3, 3, 21, 21), outline=color, width=g)
        c.create_line(*p(12, 11, 12, 17), fill=color, width=g, capstyle="round")
        c.create_line(*p(12, 7.5, 12, 8.1), fill=color, width=g + .6, capstyle="round")
    elif nombre == "error":
        c.create_oval(*p(3, 3, 21, 21), outline=color, width=g)
        c.create_line(*p(8.5, 8.5, 15.5, 15.5), fill=color, width=g, capstyle="round")
        c.create_line(*p(15.5, 8.5, 8.5, 15.5), fill=color, width=g, capstyle="round")
    elif nombre == "correcto":
        c.create_line(*p(5, 12, 9, 16, 19, 6), fill=color, width=g, capstyle="round", joinstyle="round")
    elif nombre == "nota":
        c.create_polygon(*p(6, 3, 15, 3, 19, 7, 19, 21, 6, 21), outline=color, fill="", width=g, joinstyle="round")
        c.create_line(*p(9, 12, 16, 12), fill=color, width=g, capstyle="round")
        c.create_line(*p(9, 16, 14, 16), fill=color, width=g, capstyle="round")
    elif nombre == "calcular":
        c.create_rectangle(*p(5, 3, 19, 21), outline=color, width=g)
        for linea in ((8, 7, 16, 7), (8, 12, 10, 12), (14, 12, 16, 12), (8, 16, 10, 16), (14, 16, 16, 16)):
            c.create_line(*p(*linea), fill=color, width=g, capstyle="round")
    elif nombre == "buscar":
        c.create_oval(*p(4, 4, 18, 18), outline=color, width=g)
        c.create_line(*p(16, 16, 20.5, 20.5), fill=color, width=g, capstyle="round")
    elif nombre in ("estrella", "estrella_llena"):
        puntos = (12, 3.5, 14.6, 8.8, 20.5, 9.7, 16.2, 13.8, 17.2, 19.6, 12, 16.9, 6.8, 19.6, 7.8, 13.8, 3.5, 9.7,
                  9.4, 8.8)
        llena = nombre == "estrella_llena"
        c.create_polygon(*p(*puntos), outline="#B7821A" if llena else color, fill="#E0A526" if llena else "",
                         width=g, joinstyle="round")
    elif nombre == "pdf":
        c.create_polygon(*p(14, 3, 6, 3, 6, 21, 18, 21, 18, 7), outline=color, fill="", width=g, joinstyle="round")
        c.create_line(*p(14, 3, 14, 7, 18, 7), fill=color, width=g)
    elif nombre == "excel":
        c.create_rectangle(*p(4, 4, 20, 20), outline=color, width=g)
        for linea in ((4, 10, 20, 10), (4, 15, 20, 15), (10, 4, 10, 20)):
            c.create_line(*p(*linea), fill=color, width=g)
    elif nombre == "copiar":
        c.create_rectangle(*p(8, 8, 20, 20), outline=color, width=g)
        c.create_line(*p(16, 8, 16, 4, 4, 4, 4, 16, 8, 16), fill=color, width=g, joinstyle="round")


_ESTRELLA = (12, 3.5, 14.6, 8.8, 20.5, 9.7, 16.2, 13.8, 17.2, 19.6, 12, 16.9, 6.8, 19.6, 7.8, 13.8, 3.5, 9.7, 9.4, 8.8)


def imagen_estrella(widget: tk.Misc, llena: bool, tam: int = 18):
    """Imagen de estrella para las filas del catálogo (favorito: rellena ámbar; si no, contorno gris)."""
    raiz = _raiz(widget)
    cache = getattr(raiz, "_engicalc_estrellas", {})
    tam = _px(widget, tam)
    clave = (llena, tam)
    if clave in cache:
        return cache[clave]
    relleno, borde = ("#E0A526", "#B7821A") if llena else (None, "#9AA6B6")
    try:  # con Pillow: suavizada y con transparencia parcial
        from PIL import Image, ImageDraw, ImageTk

        k = 4 * tam / 24
        grande = Image.new("RGBA", (4 * tam, 4 * tam), (0, 0, 0, 0))
        puntos = [(_ESTRELLA[i] * k, _ESTRELLA[i + 1] * k) for i in range(0, len(_ESTRELLA), 2)]
        ImageDraw.Draw(grande).polygon(puntos, fill=relleno, outline=borde, width=max(2, round(1.8 * k)))
        imagen = ImageTk.PhotoImage(grande.resize((tam, tam), Image.LANCZOS), master=raiz)
    except Exception:  # noqa: BLE001 - sin Pillow: estrella sin suavizado con tk.PhotoImage
        imagen = tk.PhotoImage(master=raiz, width=tam, height=tam)
        k = tam / 24
        pts = [(_ESTRELLA[i] * k, _ESTRELLA[i + 1] * k) for i in range(0, len(_ESTRELLA), 2)]

        def dentro(x, y):
            c = False
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                    c = not c
            return c

        for y in range(tam):
            for x in range(tam):
                borde_pixel = sum(dentro(x + .5 + dx, y + .5 + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) < 4
                if dentro(x + .5, y + .5) and (borde_pixel or relleno):
                    imagen.put(borde if borde_pixel else relleno, (x, y))
                else:
                    imagen.transparency_set(x, y, True)
    cache[clave] = imagen
    raiz._engicalc_estrellas = cache
    return imagen


# ---------------------------------------------------------------------------
# Logotipo
# ---------------------------------------------------------------------------
def logotipo(padre: tk.Misc, ruta, alto: int, fondo: str | None = None) -> tk.Label | None:
    """Logotipo RMR a ``alto`` px. Sin Pillow o sin archivo devuelve None y la ventana sigue igual."""
    try:
        from pathlib import Path

        ruta = Path(ruta)
        if not ruta.is_file():
            return None
        from PIL import Image, ImageTk

        raiz = _raiz(padre)
        cache = getattr(raiz, "_engicalc_logos", {})
        clave = (str(ruta), alto)
        foto = cache.get(clave)
        if foto is None:
            imagen = Image.open(ruta)
            alto_px = _px(padre, alto)
            ancho = round(imagen.width * alto_px / imagen.height)
            foto = ImageTk.PhotoImage(imagen.resize((ancho, alto_px), Image.LANCZOS), master=raiz)
            cache[clave] = foto
            raiz._engicalc_logos = cache
        return tk.Label(padre, image=foto, background=fondo or fondo_de(padre), borderwidth=0)
    except Exception:  # noqa: BLE001 - el logotipo nunca debe impedir abrir una ventana
        return None


# ---------------------------------------------------------------------------
# Componentes compuestos
# ---------------------------------------------------------------------------
class Aviso(tk.Frame):
    """Aviso con icono, título de tipo, texto técnico original sin cambios y, si existe, su fuente."""

    def __init__(self, padre: tk.Misc, tono: str, textos, titulo: str | None = None, fuente_texto: str = "",
                 contador: str = "", max_lineas: int | None = None):
        t = TONOS[tono]
        self.max_lineas = max_lineas
        super().__init__(padre, background=t["fondo"], highlightthickness=1, highlightbackground=t["borde"],
                         highlightcolor=t["borde"], padx=12, pady=10)
        self.columnconfigure(1, weight=1)
        icono(self, t["icono"], t["color"], t["fondo"]).grid(row=0, column=0, sticky="nw", padx=(0, 10))
        textos = [textos] if isinstance(textos, str) else list(textos)
        titulo = titulo or t["titulo"]
        # Text (y no Label) para poner el título en negrita en el mismo renglón que el texto original
        self.texto = tk.Text(self, background=t["fondo"], foreground=t["texto"], font=fuente("cuerpo"),
                             wrap="word", relief="flat", borderwidth=0, highlightthickness=0, height=1,
                             width=50, cursor="arrow", padx=0, pady=0, spacing3=2, takefocus=0)
        self.texto.tag_configure("titulo", font=fuente("cuerpo_negrita"))
        self.texto.tag_configure("fuente", font=fuente("mono_pequeno"))
        if len(textos) == 1:
            self.texto.insert("end", titulo, "titulo")
            self.texto.insert("end", " · " + textos[0])
        else:
            self.texto.insert("end", f"{titulo} · {len(textos)}", "titulo")
            for texto in textos:
                self.texto.insert("end", "\n• " + texto)
        if fuente_texto:
            self.texto.insert("end", "\n" + fuente_texto, "fuente")
        self.texto.configure(state="disabled")
        self.texto.grid(row=0, column=1, sticky="ew")
        # con muchos avisos el panel no empuja los resultados fuera de la ventana: se desplaza por dentro
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=self.barra.set)
        if contador:
            tk.Label(self, text=contador, font=fuente("mono_pequeno"), foreground=t["color"],
                     background=t["fondo"]).grid(row=0, column=2, sticky="ne", padx=(10, 0))
        self.texto.bind("<Configure>", lambda e: self._ajustar_alto())

    def contenido(self) -> str:
        return self.texto.get("1.0", "end-1c")

    def _ajustar_alto(self) -> None:
        try:
            lineas = int(self.texto.tk.call(self.texto._w, "count", "-displaylines", "1.0", "end-1c")) + 1
        except (tk.TclError, ValueError):
            return
        visibles = min(lineas, self.max_lineas) if self.max_lineas else lineas
        if int(self.texto.cget("height")) != visibles:
            self.texto.configure(height=max(1, visibles))
        if visibles < lineas:
            self.barra.grid(row=0, column=3, sticky="ns", padx=(6, 0))
        else:
            self.barra.grid_remove()


class Flujo(tk.Frame):
    """Coloca a sus hijos en renglones y pasa al siguiente cuando no caben (barras de acciones, leyendas).

    Así, al estrechar la ventana, la barra de acciones pasa a una segunda línea en lugar de recortarse.
    """

    def __init__(self, padre: tk.Misc, separacion: int = 8, separacion_v: int = 6, alinear: str = "left",
                 **opciones):
        opciones.setdefault("background", fondo_de(padre))
        super().__init__(padre, **opciones)
        self.separacion, self.separacion_v, self.alinear = separacion, separacion_v, alinear
        self.elementos: list[tuple[tk.Misc, int]] = []
        self._ancho = 0
        self.bind("<Configure>", self._al_cambiar)

    def agregar(self, widget: tk.Misc, espacio_antes: int = 0) -> tk.Misc:
        self.elementos.append((widget, espacio_antes))
        self.after_idle(self.acomodar)
        return widget

    def _al_cambiar(self, evento) -> None:
        if evento.width != self._ancho:
            self._ancho = evento.width
            self.acomodar()

    def ancho_natural(self) -> int:
        return sum(w.winfo_reqwidth() + self.separacion + extra for w, extra in self.elementos)

    def acomodar(self) -> None:
        if not self.winfo_exists():
            return
        disponible = max(self.winfo_width(), 1)
        if disponible <= 1:  # aún sin geometría: pide el ancho natural en un renglón
            disponible = self.ancho_natural()
        renglones, actual, x = [], [], 0
        for widget, extra in self.elementos:
            ancho = widget.winfo_reqwidth()
            inicio = x + (extra if actual else 0)
            if actual and inicio + ancho > disponible:
                renglones.append(actual)
                actual, inicio = [], 0
            actual.append((widget, inicio, ancho))
            x = inicio + ancho + self.separacion
        if actual:
            renglones.append(actual)
        y = 0
        for renglon in renglones:
            alto = max(w.winfo_reqheight() for w, _, _ in renglon)
            ocupado = renglon[-1][1] + renglon[-1][2]
            desplazamiento = max(0, disponible - ocupado) if self.alinear == "right" else 0
            for widget, x0, _ in renglon:
                widget.place(in_=self, x=x0 + desplazamiento, y=y + (alto - widget.winfo_reqheight()) // 2)
            y += alto + self.separacion_v
        alto_total = max(1, y - self.separacion_v)
        ancho_req = max((r[-1][1] + r[-1][2] for r in renglones), default=1)
        if int(self.cget("height")) != alto_total or int(self.cget("width")) != ancho_req:
            self.configure(height=alto_total, width=ancho_req)


class Tooltip:
    """Texto emergente al pasar el cursor (fuente del nivel de confianza, ayudas)."""

    def __init__(self, widget: tk.Misc, texto):
        self.widget, self.texto, self.ventana = widget, texto, None
        widget.bind("<Enter>", self.mostrar, add="+")
        widget.bind("<Leave>", self.ocultar, add="+")
        widget.bind("<ButtonPress>", self.ocultar, add="+")

    def mostrar(self, _evento=None) -> None:
        texto = self.texto() if callable(self.texto) else self.texto
        if not texto or self.ventana is not None:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.ventana = tk.Toplevel(self.widget)
        self.ventana.wm_overrideredirect(True)
        self.ventana.wm_geometry(f"+{x}+{y}")
        tk.Label(self.ventana, text=texto, font=fuente("pequeno"), foreground=SUPERFICIE, background=TEXTO,
                 padx=10, pady=6, justify="left", wraplength=_px(self.widget, 300)).pack()

    def ocultar(self, _evento=None) -> None:
        if self.ventana is not None:
            self.ventana.destroy()
            self.ventana = None


class BarraPestanas(tk.Frame):
    """Pestañas de vista (nivel 1): texto, contador opcional y subrayado azul en la activa.

    Controla un ``ttk.Notebook`` con estilo «Oculto.TNotebook» (sin pestañas propias), de modo que
    ``notebook.select()``, ``tabs()`` y ``tab()`` siguen funcionando como siempre.
    """

    def __init__(self, padre: tk.Misc, cuaderno: ttk.Notebook, fondo: str = SUPERFICIE):
        super().__init__(padre, background=fondo)
        self.cuaderno, self.fondo = cuaderno, fondo
        self.pestanas: dict[str, dict] = {}
        self.extra = tk.Frame(self, background=fondo)
        self.extra.pack(side="right", padx=(0, 12))
        cuaderno.bind("<<NotebookTabChanged>>", lambda e: self.refrescar(), add="+")

    def agregar(self, hoja: tk.Misc, texto: str) -> None:
        caja = tk.Frame(self, background=self.fondo, cursor="hand2", takefocus=1)
        caja.pack(side="left", padx=(10 if not self.pestanas else 0, 0))
        fila = tk.Frame(caja, background=self.fondo)
        fila.pack(padx=12, pady=(10, 8))
        rotulo = tk.Label(fila, text=texto, font=fuente("cuerpo"), foreground=TEXTO_2, background=self.fondo)
        rotulo.pack(side="left")
        contador = tk.Label(fila, text="", font=fuente("mono_pequeno"), padx=6, pady=0, background=self.fondo)
        linea = tk.Frame(caja, height=2, background=self.fondo)
        linea.pack(fill="x", side="bottom")
        registro = dict(caja=caja, fila=fila, rotulo=rotulo, contador=contador, linea=linea, hoja=hoja)
        self.pestanas[str(hoja)] = registro
        for w in (caja, fila, rotulo, contador):
            w.bind("<Button-1>", lambda e, h=hoja: self.seleccionar(h))
        caja.bind("<Return>", lambda e, h=hoja: self.seleccionar(h))
        caja.bind("<space>", lambda e, h=hoja: self.seleccionar(h))
        caja.bind("<FocusIn>", lambda e, r=registro: r["rotulo"].configure(foreground=AZUL))
        caja.bind("<FocusOut>", lambda e: self.refrescar())
        self.refrescar()

    def seleccionar(self, hoja) -> None:
        self.cuaderno.select(hoja)
        self.refrescar()

    def contador(self, hoja, valor, tono: str = "info") -> None:
        registro = self.pestanas.get(str(hoja))
        if registro is None:
            return
        if valor in (None, "", 0):
            registro["contador"].pack_forget()
            return
        if tono == "info":
            fondo_c, color = AZUL_50, AZUL
        else:
            fondo_c, color = TONOS[tono]["fondo"], TONOS[tono]["color"]
        registro["contador"].configure(text=str(valor), background=fondo_c, foreground=color)
        registro["contador"].pack(side="left", padx=(8, 0))

    def refrescar(self) -> None:
        try:
            actual = self.cuaderno.select()
        except tk.TclError:
            return
        for clave, r in self.pestanas.items():
            activa = clave == actual
            r["rotulo"].configure(font=fuente("cuerpo_negrita" if activa else "cuerpo"),
                                  foreground=MARINO if activa else TEXTO_2)
            r["linea"].configure(background=AZUL if activa else self.fondo)


class BarraEstado(tk.Frame):
    """Barra de estado: estado del cálculo a la izquierda y proyecto a la derecha."""

    def __init__(self, padre: tk.Misc, texto: str = "", derecha: str = ""):
        super().__init__(padre, background=SUPERFICIE)
        separador(self, "horizontal").pack(fill="x", side="top")
        cuerpo = tk.Frame(self, background=SUPERFICIE)
        cuerpo.pack(fill="x", padx=_px(self, 24), pady=6)
        self.izquierda = tk.Label(cuerpo, text=texto, font=fuente("pequeno"), foreground=TEXTO_2,
                                  background=SUPERFICIE, anchor="w", justify="left")
        self.izquierda.pack(side="left", fill="x", expand=True)
        self.derecha = tk.Label(cuerpo, text=derecha, font=fuente("pequeno"), foreground=TEXTO_2,
                                background=SUPERFICIE, anchor="e")
        self.derecha.pack(side="right")

    def mostrar(self, texto: str, tono: str | None = None) -> None:
        color = TONOS[tono]["color"] if tono else TEXTO_2
        self.izquierda.configure(text=texto, foreground=color,
                                 font=fuente("pequeno_negrita" if tono in ("correcto", "advertencia", "critico")
                                             else "pequeno"))

    # compatibilidad con ttk.Label: ventana.estado.cget("text") / configure(text=...)
    def cget(self, opcion):  # type: ignore[override]
        if opcion == "text":
            return self.izquierda.cget("text")
        return super().cget(opcion)

    def configure(self, cnf=None, **opciones):  # type: ignore[override]
        color = opciones.pop("foreground", None)
        if "text" in opciones:
            self.mostrar(opciones.pop("text"), opciones.pop("tono", None))
        if color is not None:  # ttk.Label aceptaba foreground: se aplica al texto de estado
            self.izquierda.configure(foreground=color)
        if cnf or opciones:
            return super().configure(cnf, **opciones)
        return None

    config = configure


def encabezado_ventana(padre: tk.Misc, ruta_logo, migas: list[str], al_volver=None) -> tk.Frame:
    """Banda blanca con logotipo y ruta «Calculadoras › Categoría › Herramienta»."""
    banda = tk.Frame(padre, background=SUPERFICIE)
    cuerpo = tk.Frame(banda, background=SUPERFICIE)
    cuerpo.pack(fill="x", padx=_px(banda, 24), pady=8)
    logo = logotipo(cuerpo, ruta_logo, 30, SUPERFICIE)
    if logo is not None:
        logo.pack(side="left", padx=(0, 18))
    for i, texto in enumerate(migas):
        ultimo = i == len(migas) - 1
        if i:
            tk.Label(cuerpo, text="›", font=fuente("pequeno"), foreground=TEXTO_2,
                     background=SUPERFICIE).pack(side="left", padx=6)
        enlace = i == 0 and al_volver is not None
        rotulo = tk.Label(cuerpo, text=texto, background=SUPERFICIE,
                          font=fuente("pequeno_negrita" if ultimo else "pequeno"),
                          foreground=AZUL if enlace else (TEXTO if ultimo else TEXTO_2),
                          cursor="hand2" if enlace else "")
        rotulo.pack(side="left")
        if enlace:
            rotulo.bind("<Button-1>", lambda e: al_volver())
    separador(banda, "horizontal").pack(fill="x", side="bottom")
    banda.migas = cuerpo
    return banda


class DialogoBase(tk.Toplevel):
    """Diálogo compartido (sección 10): encabezado con título y descripción, cuerpo y pie con la
    acción principal a la derecha. Se usa en Acceso, Datos del proyecto, Información técnica,
    Niveles de confianza e Historial."""

    def __init__(self, padre: tk.Misc, titulo: str, descripcion: str = "", ancho_texto: int = 420):
        super().__init__(padre)
        aplicar(self)
        self.title(titulo)
        self.configure(background=SUPERFICIE)
        encabezado = tk.Frame(self, background=SUPERFICIE)
        encabezado.pack(fill="x")
        cuerpo_enc = tk.Frame(encabezado, background=SUPERFICIE)
        cuerpo_enc.pack(fill="x", padx=20, pady=(16, 12))
        self.rotulo_titulo = etiqueta(cuerpo_enc, titulo, "subtitulo", TEXTO, SUPERFICIE)
        self.rotulo_titulo.pack(anchor="w")
        if descripcion:
            etiqueta(cuerpo_enc, descripcion, "pequeno", TEXTO_2, SUPERFICIE,
                     wraplength=_px(self, ancho_texto)).pack(anchor="w", pady=(4, 0))
        separador(encabezado, "horizontal", DIVISOR).pack(fill="x")
        self.pie = tk.Frame(self, background=SUPERFICIE_2)
        self.pie.pack(fill="x", side="bottom")
        separador(self.pie, "horizontal", DIVISOR).pack(fill="x", side="top")
        self.botones = tk.Frame(self.pie, background=SUPERFICIE_2)
        self.botones.pack(fill="x", padx=20, pady=10)
        self.cuerpo = tk.Frame(self, background=SUPERFICIE)
        self.cuerpo.pack(fill="both", expand=True, padx=20, pady=16)

    def boton(self, texto: str, comando, primario: bool = False, izquierda: bool = False,
              estilo: str | None = None) -> ttk.Button:
        b = ttk.Button(self.botones, text=texto, command=comando,
                       style=estilo or ("Primario.TButton" if primario else "TButton"))
        b.pack(side="left" if izquierda else "right", padx=(0, 8) if izquierda else (8, 0))
        return b


def boton_menu(padre: tk.Misc, texto: str, opciones, primario: bool = False) -> ttk.Menubutton:
    """Botón con menú (Caso ▾, Exportar ▾). ``opciones``: lista de (texto, comando) o None (separador)."""
    boton = ttk.Menubutton(padre, text=f"{texto} ▾", style="Primario.TMenubutton" if primario else "TMenubutton")
    menu = tk.Menu(boton, tearoff=False)
    for opcion in opciones:
        if opcion is None:
            menu.add_separator()
        else:
            menu.add_command(label=opcion[0], command=opcion[1])
    boton["menu"] = menu
    boton.menu = menu
    return boton
