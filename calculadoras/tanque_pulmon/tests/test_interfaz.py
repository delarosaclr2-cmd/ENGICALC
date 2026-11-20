"""Pruebas de la ventana, el esquema interactivo y la memoria (PDF, Excel, impresión). Requieren pantalla (xvfb)."""
import json
import os
import zipfile

import pytest

PKG = "tanque_pulmon"
CAMPO, VALOR = "q_consumo.valor", "150"
CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")


@pytest.fixture
def ventana():
    tk = pytest.importorskip("tkinter")
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sin pantalla")
    raiz.withdraw()
    gui = __import__(f"{PKG}.gui_tk", fromlist=["abrir"])
    v, f = gui.abrir(raiz)
    raiz.update()
    yield raiz, f
    raiz.destroy()


def test_carga_presenta_resultados_y_esquema(ventana):
    raiz, f = ventana
    m = f.memoria
    assert m is not None and m.resumen and m.resultados
    assert len(f.tv_res.get_children()) == len(m.resultados)
    assert len(f.tv_ver.get_children()) == len(m.verificaciones)
    assert m.titulo.upper() in f.txt_mem.get("1.0", "end").upper()
    assert len(f.lienzo.c.find_all()) > 20          # el esquema se dibujó


def test_recalculo_automatico_al_cambiar_un_dato(ventana):
    raiz, f = ventana
    h0 = f.memoria.huella
    f.vars[CAMPO].set(VALOR)
    for _ in range(20):                                  # espera el retardo de la ventana
        raiz.after(60)
        raiz.update()
    assert f.memoria.huella != h0


def test_dato_invalido_conserva_el_ultimo_resultado(ventana):
    raiz, f = ventana
    m0 = f.memoria
    txt = next(iter(f.textos.values()))
    txt.insert("1.0", "[")                               # tabla con JSON inválido
    assert f.recalcular(silencioso=True) is None
    assert f.memoria is m0
    assert "inválidos" in f.estado.cget("text")


def test_exporta_memoria_pdf_excel_y_svg(ventana, tmp_path):
    raiz, f = ventana
    pdf, xlsx, svg = tmp_path / "m.pdf", tmp_path / "m.xlsx", tmp_path / "e.svg"
    assert f.memoria_pdf(str(pdf)) and pdf.read_bytes()[:4] == b"%PDF"
    assert f.excel(str(xlsx)) and zipfile.is_zipfile(xlsx)
    f.lienzo.guardar_svg(str(svg))
    assert svg.read_text(encoding="utf-8").lstrip().startswith("<")


def test_imprimir_envia_la_memoria_actual(ventana, monkeypatch):
    raiz, f = ventana
    ui = __import__(f"{PKG}.ui.ventana", fromlist=["memoria_pdf"])
    enviadas = []
    monkeypatch.setattr(ui.memoria_pdf, "imprimir", lambda m: enviadas.append(m) or "x.pdf")
    assert f.imprimir() == "x.pdf" and enviadas[0].huella == f.memoria.huella


def test_guardar_y_abrir_caso(ventana, tmp_path):
    raiz, f = ventana
    ruta = str(tmp_path / "c.json")
    f.guardar(ruta)
    datos = json.load(open(ruta, encoding="utf-8"))
    f.abrir(ruta)
    assert f.leer() == datos
