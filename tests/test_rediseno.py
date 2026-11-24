"""Pruebas del rediseño de interfaz v1 (sistema visual ENGICALC).

El rediseño solo cambia disposición y estilo. Estas pruebas cubren lo nuevo de la interfaz
(KPI, estados vacío y de validación, favoritos y recientes, copias del tema) y comprueban que
no se haya creado ningún valor de cálculo nuevo. La equivalencia de resultados y exportaciones
con la versión anterior la cubren test_interfaz.py y la instantánea de no regresión documentada
en docs/REDISENO_INTERFAZ_V1.md.
"""
import hashlib
import json
from pathlib import Path

import pytest

from calculadoras.calculos import POR_ID
from calculadoras.interfaz.kpi import KPI
from tests.casos import CASOS
from tests.test_interfaz import HAY_PANTALLA, menu  # noqa: F401 (fixture)

RAIZ = Path(__file__).resolve().parents[1]
APLICACIONES_TK = ("linea_agua", "linea_vapor", "linea_aceite", "linea_gas", "gas_combustible", "tanque_pulmon")


# ---------------------------------------------------------------------------
# Sin pantalla
# ---------------------------------------------------------------------------
def test_kpi_son_salidas_existentes_de_cada_calculadora():
    """Paso 3 de la guía: de 2 a 4 KPI elegidos de la lista de resultados actual; ningún valor nuevo."""
    assert set(KPI) == set(POR_ID)
    for cid, claves in KPI.items():
        assert 2 <= len(claves) <= 4, cid
        assert len(set(claves)) == len(claves), cid
        resultado = POR_ID[cid].calcular(CASOS[cid])
        for clave in claves:
            assert clave in resultado, f"{cid}: «{clave}» no es una salida de la calculadora"


def test_copias_del_tema_en_las_aplicaciones_son_identicas():
    """Las 6 aplicaciones también se ejecutan solas desde su carpeta: su copia del tema no debe divergir."""
    original = hashlib.sha256((RAIZ / "calculadoras/interfaz/tema.py").read_bytes()).hexdigest()
    for app in APLICACIONES_TK:
        copia = RAIZ / f"calculadoras/{app}/{app}/ui/tema.py"
        assert hashlib.sha256(copia.read_bytes()).hexdigest() == original, copia


def test_preferencias_del_menu_toleran_archivo_danado(tmp_path, monkeypatch):
    from calculadoras.interfaz import preferencias

    monkeypatch.setenv("CALCULADORAS_REGISTRO", str(tmp_path))
    (tmp_path / preferencias.ARCHIVO).write_text("{roto", encoding="utf-8")
    datos = preferencias.cargar()
    assert datos == {"favoritos": [], "recientes": []}
    assert preferencias.alternar_favorito(datos, "banda") is True
    for cid in ("a", "b", "c", "d", "e", "f"):
        preferencias.registrar_reciente(datos, cid)
    guardado = json.loads((tmp_path / preferencias.ARCHIVO).read_text(encoding="utf-8"))
    assert guardado["favoritos"] == ["banda"]
    assert guardado["recientes"] == ["f", "e", "d", "c", "b"]
    assert preferencias.alternar_favorito(datos, "banda") is False


def test_unidades_de_las_aplicaciones_solo_se_separan_si_son_unidades():
    import sys

    sys.path.insert(0, str(RAIZ / "calculadoras/linea_agua"))
    try:
        from linea_agua.ui.ventana import _separar_unidad
    finally:
        sys.path.remove(str(RAIZ / "calculadoras/linea_agua"))
    assert _separar_unidad("Longitud (m)") == ("Longitud", "m")
    assert _separar_unidad("Temperatura de diseño (°C)") == ("Temperatura de diseño", "°C")
    assert _separar_unidad("Clase de localización (F)") == ("Clase de localización (F)", "")
    assert _separar_unidad("Longitud (m; 0 = solo velocidad)") == ("Longitud (m; 0 = solo velocidad)", "")
    assert _separar_unidad("Presión de operación (opcional)") == ("Presión de operación (opcional)", "")


# ---------------------------------------------------------------------------
# Con pantalla
# ---------------------------------------------------------------------------
pantalla = pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")


def _textos(widget) -> list[str]:
    """Textos de todas las etiquetas dentro de un contenedor."""
    textos = []
    for hijo in widget.winfo_children():
        try:
            textos.append(str(hijo.cget("text")))
        except Exception:  # noqa: BLE001 - marcos sin texto
            pass
        textos += _textos(hijo)
    return textos


@pantalla
def test_estado_vacio_lista_los_obligatorios_pendientes(menu):
    ventana = menu.abrir("banda")
    menu.raiz.update()
    obligatorios = [c for c in ventana.calc.campos if c.obligatorio and c.tipo != "opcion"]
    assert ventana.vacio.winfo_ismapped() and not ventana.marco_tabla.winfo_ismapped()
    assert ventana.titulo_pendientes.cget("text") == f"Datos obligatorios pendientes · {len(obligatorios)}"
    assert all(str(ventana.entradas_widget[c.clave].cget("style")) == "Pendiente.TEntry" for c in obligatorios)
    ventana.asignar(CASOS["banda"])
    menu.raiz.update()
    assert not ventana.caja_pendientes.winfo_ismapped()
    assert all(str(ventana.entradas_widget[c.clave].cget("style")) == "TEntry" for c in obligatorios)


@pantalla
@pytest.mark.parametrize("cid", sorted(POR_ID))
def test_kpi_avisos_y_tabla_reflejan_el_resultado(menu, cid):
    ventana = menu.abrir(cid)
    ventana.asignar(CASOS[cid])
    resultado = ventana.calcular()
    menu.raiz.update()
    assert ventana.marco_tabla.winfo_ismapped()
    # los KPI muestran exactamente el texto de la tabla (mismo valor, misma precisión, misma unidad)
    assert len(ventana._celdas_kpi) == len(KPI[cid])
    for (celda, _), clave in zip(ventana._celdas_kpi, KPI[cid]):
        s = resultado.salida(clave)
        textos = _textos(celda)
        assert s.etiqueta in textos and s.texto_valor() in textos, (cid, clave, textos)
        assert not s.unidad or f" {s.unidad}" in textos
    assert ventana.tabla._claves == {resultado.salida(k).etiqueta for k in KPI[cid]}
    # el panel de avisos lleva el texto literal de cada advertencia
    avisos = [w for w in ventana.zona_avisos.winfo_children()]
    if resultado.advertencias:
        contenido = avisos[0].contenido()
        assert all(a in contenido for a in resultado.advertencias)
    else:
        assert not avisos
    # la pestaña Ecuaciones y notas conserva ecuaciones y notas sin cambios
    texto = ventana.texto.get("1.0", "end")
    assert all(e in texto for e in resultado.ecuaciones) and all(n in texto for n in resultado.notas)


@pantalla
def test_validacion_marca_el_campo_y_conserva_el_mensaje(menu):
    ventana = menu.abrir("banda")
    ventana.asignar(CASOS["banda"])
    campo = ventana.calc.campos[0]
    ventana.variables[campo.clave].set("abc")
    assert ventana.calcular() is None
    menu.raiz.update()
    assert menu.errores[-1][0] == "Datos no válidos"
    assert ventana.entradas_widget[campo.clave].instate(["invalid"])
    pista = ventana._pistas[campo.clave]
    assert pista.winfo_ismapped() and "no es un número válido" in pista.cget("text")
    ventana.variables[campo.clave].set("1000")          # al corregir, la marca desaparece
    menu.raiz.update()
    assert not ventana.entradas_widget[campo.clave].instate(["invalid"]) and not pista.winfo_ismapped()


@pantalla
def test_nivel_muestra_la_nota_del_resultado_al_pasar_el_cursor(menu):
    """La nota de cada salida (Salida.nota) no se veía en la tabla anterior; ahora se lee junto al nivel."""
    ventana = menu.abrir("helicoidal")
    ventana.asignar(CASOS["helicoidal"])
    resultado = ventana.calcular()
    con_nota = next(s for s in resultado.salidas if s.nota)
    iid = next(i for i in ventana.tabla.get_children() if ventana.tabla.item(i)["text"] == con_nota.etiqueta)
    assert con_nota.nota in ventana.tabla.texto_nivel(iid)


@pantalla
def test_etiqueta_de_guardado(menu, tmp_path, monkeypatch):
    ventana = menu.abrir("viga")
    assert ventana.chip_guardado.cget("text") == "sin guardar"
    monkeypatch.setattr("calculadoras.interfaz.ventana.filedialog.asksaveasfilename", lambda **k: str(tmp_path / "v.json"))
    ventana.asignar(CASOS["viga"])
    ventana.calcular()
    ventana.guardar_caso()
    assert ventana.chip_guardado.cget("text") == "guardado"
    ventana.variables[ventana.calc.campos[0].clave].set("7")
    menu.raiz.update()
    assert ventana.chip_guardado.cget("text") == "sin guardar"


@pantalla
def test_categorias_favoritos_y_recientes_del_menu(menu):
    hijos = lambda: [h for d in menu.arbol.get_children() for h in menu.arbol.get_children(d)]  # noqa: E731
    menu.elegir_categoria("Estructural")
    assert hijos() == ["viga"]
    menu.texto_busqueda.set("bomba")             # la categoría y el buscador se combinan
    assert hijos() == []
    menu.elegir_categoria("Todas")
    assert {"bomba", "memoria_bombas"} <= set(hijos())
    menu.texto_busqueda.set("")
    assert menu.alternar_favorito("tolva") is True
    assert "tolva" in menu.preferencias["favoritos"]
    assert any(w.cget("text") == "Tolva de dosificación" for w in menu.caja_favoritos.lista.winfo_children())
    menu.abrir("silo")
    assert menu.preferencias["recientes"][0] == "silo"
    assert menu.alternar_favorito("tolva") is False


@pantalla
def test_acciones_pasan_a_segunda_linea_en_ventana_estrecha(menu):
    ventana = menu.abrir("secador")
    ventana.geometry("1440x900")
    menu.raiz.update()
    ancha = int(ventana.acciones.grid_info()["row"])
    ventana.geometry("1024x700")
    menu.raiz.update()
    menu.raiz.update()
    assert (ancha, int(ventana.acciones.grid_info()["row"])) == (0, 1)
    for w, _ in ventana.acciones.elementos:          # nada se recorta a la derecha
        assert w.winfo_x() + w.winfo_width() <= ventana.acciones.winfo_width() + 1
