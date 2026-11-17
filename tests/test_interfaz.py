"""Prueba de humo de la interfaz gráfica.

Abre el menú principal, recorre TODAS las calculadoras desde el menú, captura el
caso ordinario, calcula, verifica que la tabla muestre los mismos valores que el
motor de cálculo, exporta PDF/Excel/JSON, abre gráficas e imágenes y comprueba
el rechazo de entradas no válidas. Requiere pantalla (en Linux: xvfb-run).
"""
import os
import tkinter as tk

import pytest

from calculadoras.calculos import CALCULADORAS, POR_ID
from tests.casos import CASOS
from tests.casos_libros import CASOS_LIBROS, valor

def crear_raiz() -> tk.Tk:
    """tk.Tk() con reintentos: en Windows (Python 3.14) crear y destruir intérpretes Tk seguidos falla de forma
    intermitente con «Can't find a usable tk.tcl» aunque Tk esté bien instalado (la aplicación crea uno solo)."""
    import time

    for intento in range(5):
        try:
            return tk.Tk()
        except tk.TclError:
            if intento == 4:
                raise
            time.sleep(0.3)


try:
    _raiz_prueba = crear_raiz()
    _raiz_prueba.destroy()
    HAY_PANTALLA = True
except tk.TclError:
    HAY_PANTALLA = False

pytestmark = pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")


@pytest.fixture
def menu(monkeypatch):
    import matplotlib

    matplotlib.use("Agg", force=True)
    from calculadoras.interfaz import menu as modulo_menu
    from calculadoras.interfaz.ventana import VentanaCalculadora

    errores = []
    monkeypatch.setattr(VentanaCalculadora, "mostrar_error", lambda self, t, m: errores.append((t, m)))
    raiz = crear_raiz()
    raiz.withdraw()
    m = modulo_menu.MenuPrincipal(raiz)
    m.errores = errores
    yield m
    raiz.destroy()


def test_menu_lista_todas_las_calculadoras(menu):
    hijos = [h for d in menu.arbol.get_children() for h in menu.arbol.get_children(d)]
    assert sorted(hijos) == sorted(POR_ID)


def test_buscador(menu):
    menu.texto_busqueda.set("npsh")
    hijos = [h for d in menu.arbol.get_children() for h in menu.arbol.get_children(d)]
    assert hijos == ["bomba"]
    menu.texto_busqueda.set("transportador")
    hijos = {h for d in menu.arbol.get_children() for h in menu.arbol.get_children(d)}
    assert {"helicoidal", "neumatico", "banda"} <= hijos
    menu.texto_busqueda.set("")
    assert len([h for d in menu.arbol.get_children() for h in menu.arbol.get_children(d)]) == len(CALCULADORAS)
    # una búsqueda sin coincidencias limpia el panel de detalle (hallazgo de la prueba en vivo)
    menu.arbol.selection_set("soplador")
    menu.describir()
    menu.texto_busqueda.set("texto inexistente")
    assert menu.titulo.cget("text") == "Seleccione una calculadora"
    assert str(menu.boton_abrir.cget("state")) == "disabled"


@pytest.mark.parametrize("cid", sorted(POR_ID))
def test_cada_calculadora_desde_el_menu(menu, cid, tmp_path):
    menu.arbol.selection_set(cid)
    menu.describir()
    ventana = menu.abrir_seleccion()
    menu.raiz.update()
    assert ventana.calc.id == cid
    # todos los campos tienen widget y los de opción solo aceptan valores de la lista
    assert set(ventana.variables) == {c.clave for c in ventana.calc.campos}

    ventana.asignar(CASOS[cid])
    resultado = ventana.calcular()
    assert resultado is not None, menu.errores
    esperado = POR_ID[cid].calcular(CASOS[cid])
    filas = [ventana.tabla.item(i) for i in ventana.tabla.get_children()]
    assert [f["text"] for f in filas] == [s.etiqueta for s in esperado.salidas]
    assert [str(f["values"][0]) for f in filas] == [s.texto_valor() for s in esperado.salidas]

    ventana.exportar_pdf_a(tmp_path / "m.pdf")
    ventana.exportar_excel_a(tmp_path / "m.xlsx")
    assert (tmp_path / "m.pdf").stat().st_size > 2000 and (tmp_path / "m.xlsx").stat().st_size > 2000
    if ventana.calc.graficar:
        ventana.mostrar_grafica().destroy()
    for imagen in ventana.calc.imagenes:
        ventana.ver_imagen(imagen).destroy()

    # guardar y volver a abrir el caso
    from calculadoras.interfaz import reportes

    reportes.guardar_caso(tmp_path / "c.json", ventana.calc, ventana.capturado(), resultado)
    ventana.restaurar_defectos()
    ventana.cargar_caso(tmp_path / "c.json")
    assert ventana.ultimo is not None

    # entrada no válida: texto en el primer campo numérico
    numerico = next(c for c in ventana.calc.campos if c.tipo != "opcion")
    ventana.variables[numerico.clave].set("abc")
    assert ventana.calcular() is None
    assert menu.errores and menu.errores[-1][0] == "Datos no válidos"
    assert ventana.ultimo is None and not ventana.tabla.get_children()

    # exportar sin cálculo vigente está bloqueado
    n = len(menu.errores)
    ventana.copiar_resultados()
    assert len(menu.errores) == n + 1
    ventana.destroy()


def test_exportar_bloqueado_si_cambian_los_datos(menu):
    ventana = menu.abrir("ductos")
    ventana.asignar(CASOS["ductos"])
    ventana.calcular()
    ventana.variables["caudal"].set("12000")
    assert not ventana._requerir_calculo_vigente()
    assert menu.errores[-1][0] == "Datos modificados"


def test_abrir_dos_veces_reutiliza_la_ventana(menu):
    a = menu.abrir("viga")
    b = menu.abrir("viga")
    assert a is b


def test_dialogo_de_acceso():
    from calculadoras.interfaz.acceso import DialogoAcceso
    from calculadoras.nucleo.configuracion import cargar

    raiz = crear_raiz()
    raiz.withdraw()
    try:
        d = DialogoAcceso(raiz, cargar())
        d.contrasena.set("incorrecta")
        assert not d.ingresar() and not d.aceptado
        d.contrasena.set("rmr123")
        assert d.ingresar() and d.aceptado
    finally:
        raiz.destroy()


def test_errores_inesperados_se_registran_y_se_muestran(monkeypatch, tmp_path):
    from calculadoras.interfaz import menu as modulo_menu

    monkeypatch.setattr(modulo_menu, "RAIZ", tmp_path)
    mostrados = []
    monkeypatch.setattr(modulo_menu.messagebox, "showerror", lambda t, m, parent=None: mostrados.append(m))
    raiz = crear_raiz()
    raiz.withdraw()
    try:
        manejar = modulo_menu._manejar_excepcion(raiz)
        try:
            raise ModuleNotFoundError("No module named 'reportlab'", name="reportlab")
        except ModuleNotFoundError as e:
            manejar(type(e), e, e.__traceback__)
        assert "INSTALAR.bat" in mostrados[-1]
        try:
            1 / 0
        except ZeroDivisionError as e:
            manejar(type(e), e, e.__traceback__)
        assert "errores.log" in mostrados[-1]
        assert "ZeroDivisionError" in (tmp_path / "registro" / "errores.log").read_text(encoding="utf-8")
    finally:
        raiz.destroy()


def test_rueda_del_raton_desplaza_el_formulario(menu):
    from types import SimpleNamespace

    ventana = menu.abrir("secador")
    ventana.geometry("1000x500")
    menu.raiz.update()
    inicio = ventana._lienzo.yview()[0]
    assert ventana._desplazar_formulario(SimpleNamespace(num=5, delta=0)) == "break"
    menu.raiz.update()
    assert ventana._lienzo.yview()[0] > inicio
    ventana._desplazar_formulario(SimpleNamespace(num=None, delta=120))
    ventana._rueda(True)
    ventana._rueda(False)


def test_pdf_sin_matplotlib_se_genera_sin_grafica(menu, tmp_path, monkeypatch):
    """Hallazgo de la prueba en vivo: sin matplotlib, la memoria PDF de bomba/torre/viga fallaba completa."""
    import sys

    ventana = menu.abrir("bomba")
    ventana.asignar(CASOS["bomba"])
    assert ventana.calcular() is not None
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    monkeypatch.setitem(sys.modules, "matplotlib.figure", None)
    ventana.exportar_pdf_a(tmp_path / "bomba.pdf")
    assert (tmp_path / "bomba.pdf").stat().st_size > 2000
    assert "sin gráfica" in ventana.estado.cget("text")


def test_menu_avisa_bibliotecas_faltantes(monkeypatch):
    import importlib.util

    from calculadoras.interfaz import menu as modulo_menu

    original = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda nombre, *a: None if nombre in ("openpyxl", "matplotlib") else original(nombre, *a))
    assert modulo_menu.bibliotecas_faltantes() == ["openpyxl", "matplotlib"]
    raiz = crear_raiz()
    raiz.withdraw()
    try:
        m = modulo_menu.MenuPrincipal(raiz)
        texto = m.aviso_bibliotecas.cget("text")
        assert "openpyxl" in texto and "Excel" in texto and "INSTALAR.bat" in texto
    finally:
        raiz.destroy()


# ---------------------------------------------------------------------------
# Datos del proyecto e historial (v2.1.0)
# ---------------------------------------------------------------------------
def test_historial_y_datos_de_proyecto(tmp_path, monkeypatch):
    import json

    from calculadoras.interfaz import ventana as V
    from calculadoras.interfaz.menu import MenuPrincipal
    from calculadoras.nucleo import historial

    monkeypatch.setenv("CALCULADORAS_REGISTRO", str(tmp_path))
    monkeypatch.setattr(V, "_PROYECTO", None)
    raiz = crear_raiz()
    raiz.withdraw()
    try:
        menu = MenuPrincipal(raiz)
        datos_proyecto = dict(proyecto="Planta de cemento", cliente="Cliente X", documento="MC-001", revision="A",
                              elaboro="JMA", reviso="", aprobo="")
        dialogo = menu.editar_proyecto()
        for clave, valor in datos_proyecto.items():
            dialogo.variables[clave].set(valor)
        dialogo.guardar()
        assert json.loads((tmp_path / "proyecto.json").read_text(encoding="utf-8"))["documento"] == "MC-001"

        ventana = menu.abrir("helicoidal")
        ventana.asignar(CASOS["helicoidal"])
        resultado = ventana.calcular()
        assert resultado is not None and ventana.historial_ok
        registros = historial.leer(carpeta=tmp_path)
        assert registros[0]["calculadora"] == "helicoidal"
        assert registros[0]["proyecto"]["proyecto"] == "Planta de cemento"

        # PDF y Excel con encabezado del proyecto
        pdf, xlsx = tmp_path / "m.pdf", tmp_path / "m.xlsx"
        ventana.exportar_pdf_a(str(pdf))
        ventana.exportar_excel_a(str(xlsx))
        from openpyxl import load_workbook
        hoja = load_workbook(xlsx).active
        valores = [hoja.cell(i, 2).value for i in range(1, 15)]
        assert "MC-001" in valores and pdf.stat().st_size > 1000

        # Reabrir desde el historial con otro valor en pantalla
        ventana.variables["capacidad"].set("99")
        historial_ventana = menu.ver_historial()
        historial_ventana.tabla.selection_set("0")
        reabierta = historial_ventana.abrir()
        assert float(reabierta.variables["capacidad"].get()) == pytest.approx(10)
        historial_ventana.destroy()
    finally:
        raiz.destroy()


def test_historial_tolera_lineas_danadas(tmp_path):
    from calculadoras.nucleo import historial

    (tmp_path / "historial.jsonl").write_text('{"roto": \n{"calculadora": "bomba", "entradas": {}}\n',
                                              encoding="utf-8")
    assert [r["calculadora"] for r in historial.leer(carpeta=tmp_path)] == ["bomba"]
    assert historial.compactar(carpeta=tmp_path, conservar=1)
    assert len((tmp_path / "historial.jsonl").read_text(encoding="utf-8").splitlines()) == 1


@pytest.mark.parametrize("nombre", sorted(CASOS_LIBROS))
def test_casos_de_libros_se_abren_y_dan_el_resultado_publicado(menu, nombre):
    """Los casos de docs/ejemplos/libros se abren en la ventana (como lo haría el usuario) y la ventana
    obtiene la respuesta publicada en el libro."""
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[1] / "docs" / "ejemplos" / "libros" / f"{nombre}.json"
    caso = CASOS_LIBROS[nombre]
    ventana = menu.abrir(caso["calculadora"])
    ventana.cargar_caso(str(ruta))
    menu.raiz.update()
    assert not menu.errores
    resultado = ventana.ultimo[2]
    for etiqueta, salida, publicado, tolerancia in caso["comprobaciones"]:
        assert valor(resultado, salida) == pytest.approx(publicado, rel=tolerancia), etiqueta


@pytest.mark.parametrize("cid", sorted(POR_ID))
def test_pestana_esquema(menu, cid):
    """Todas las calculadoras menos la bomba tienen la pestaña «Esquema»; se dibuja con el cálculo."""
    ventana = menu.abrir(cid)
    menu.raiz.update()
    if cid == "bomba":
        assert ventana.pestanas is None and ventana.panel_esquema is None
        return
    assert [ventana.pestanas.tab(t, "text") for t in ventana.pestanas.tabs()] == ["Resultados", "Esquema"]
    ventana.asignar(CASOS[cid])
    assert ventana.calcular() is not None
    ventana.pestanas.select(ventana.panel_esquema)
    menu.raiz.update()
    ventana.panel_esquema.al_mostrar()
    panel = ventana.panel_esquema
    assert panel.dibujado and panel.figura.axes and not panel.sucio
    assert "coinciden con la tabla" in panel.estado.cget("text")


def test_esquema_se_ajusta_a_los_datos(menu):
    ventana = menu.abrir("tolva")
    ventana.asignar(CASOS["tolva"])
    ventana.calcular()
    ventana.pestanas.select(ventana.panel_esquema)
    menu.raiz.update()
    panel = ventana.panel_esquema
    panel.actualizar()

    def textos():
        return [t.get_text() for ax in panel.figura.axes for t in ax.texts]

    assert any("lado = 2.000 m" in t for t in textos())
    ventana.variables["area_superior"].set("9")      # el usuario cambia un dato: queda pendiente de redibujar
    assert panel.sucio and panel._pendiente is not None
    panel.actualizar()
    assert any("lado = 3.000 m" in t for t in textos())
    assert "Presione Calcular" in panel.estado.cget("text")
    ventana.variables["area_superior"].set("")       # dato incompleto: se conserva el último dibujo
    assert panel.actualizar() is False
    assert "últimos datos válidos" in panel.estado.cget("text")
    assert any("lado = 3.000 m" in t for t in textos())

