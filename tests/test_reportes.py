"""Pruebas de reportes (PDF, Excel, texto), casos JSON y configuración de acceso."""
import json

import pytest

from calculadoras.calculos import CALCULADORAS, POR_ID
from calculadoras.interfaz import reportes
from calculadoras.nucleo import configuracion
from tests.casos import CASOS


@pytest.mark.parametrize("cid", sorted(POR_ID))
def test_pdf_excel_y_texto(cid, tmp_path):
    calc = POR_ID[cid]
    datos = calc.validar(CASOS[cid])
    resultado = calc.calcular(datos)
    figura = calc.graficar(datos, resultado) if calc.graficar else None
    pdf, xlsx = tmp_path / f"{cid}.pdf", tmp_path / f"{cid}.xlsx"
    reportes.generar_pdf(pdf, calc, datos, resultado, figura)
    reportes.generar_excel(xlsx, calc, datos, resultado)
    assert pdf.read_bytes()[:5] == b"%PDF-" and pdf.stat().st_size > 2000
    from openpyxl import load_workbook

    hoja = load_workbook(xlsx).active
    valores = [fila[1] for fila in hoja.iter_rows(values_only=True) if fila and len(fila) > 1]
    # el primer resultado numérico se guarda como número, no como texto
    numericos = [s.valor for s in resultado.salidas if isinstance(s.valor, float)]
    assert any(isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v - numericos[0]) < 1e-9
               for v in valores)
    texto = reportes.texto_reporte(calc, datos, resultado)
    assert calc.nombre in texto and reportes.AVISO in texto


def test_pdf_con_texto_y_simbolos(tmp_path):
    """El PDF debe aceptar griegas, subíndices y caracteres reservados de XML."""
    calc = POR_ID["secador"]
    datos = calc.validar(CASOS["secador"])
    resultado = calc.calcular(datos)
    resultado.nota("Prueba de símbolos: ΔT, ρ, η, m³/h, <menor> & mayor")
    ruta = tmp_path / "simbolos.pdf"
    reportes.generar_pdf(ruta, calc, datos, resultado)
    assert ruta.stat().st_size > 2000


def test_caso_json_ida_y_vuelta(tmp_path):
    calc = POR_ID["bomba"]
    resultado = calc.calcular(CASOS["bomba"])
    ruta = tmp_path / "caso.json"
    reportes.guardar_caso(ruta, calc, CASOS["bomba"], resultado)
    datos = reportes.abrir_caso(ruta)
    assert datos["calculadora"] == "bomba"
    nuevo = calc.calcular(datos["entradas"])
    assert [s.valor for s in nuevo.salidas] == [s.valor for s in resultado.salidas]


def test_caso_json_invalido(tmp_path):
    ruta = tmp_path / "otro.json"
    ruta.write_text(json.dumps({"hola": 1}), encoding="utf-8")
    with pytest.raises(ValueError):
        reportes.abrir_caso(ruta)


def test_configuracion_incluida_y_contrasena_original():
    config = configuracion.cargar()
    assert config["acceso"]["requerir_contrasena"] is True
    assert "rmr123" not in configuracion.RUTA_CONFIG.read_text(encoding="utf-8")  # no se guarda en texto plano
    assert configuracion.verificar_contrasena("cualquier nombre", "rmr123", config)  # igual que el original
    assert not configuracion.verificar_contrasena("usuario", "otra", config)


def test_configuracion_faltante_o_danada(tmp_path):
    danada = tmp_path / "c.json"
    danada.write_text("{no es json", encoding="utf-8")
    assert configuracion.cargar(danada) == configuracion.POR_DEFECTO
    assert configuracion.cargar(tmp_path / "no_existe.json") == configuracion.POR_DEFECTO


def test_cambiar_y_desactivar_contrasena(tmp_path):
    ruta = tmp_path / "c.json"
    configuracion.establecer_contrasena("nueva123", ruta)
    config = configuracion.cargar(ruta)
    assert configuracion.verificar_contrasena("x", "nueva123", config)
    assert not configuracion.verificar_contrasena("x", "rmr123", config)
    config["acceso"]["verificar_usuario"] = True
    assert not configuracion.verificar_contrasena("x", "nueva123", config)
    assert configuracion.verificar_contrasena("usuario", "nueva123", config)
    configuracion.establecer_contrasena("", ruta, requerir=False)
    assert configuracion.verificar_contrasena("x", "", configuracion.cargar(ruta))
    with pytest.raises(ValueError):
        configuracion.establecer_contrasena("abc", ruta)


def test_recursos_presentes():
    for calc in CALCULADORAS:
        for imagen in calc.imagenes:
            assert configuracion.recurso(imagen).is_file(), imagen
    assert configuracion.recurso(configuracion.cargar()["reportes"]["logo"]).is_file()


def test_pdf_usa_fuente_unicode_incluida_sin_matplotlib(tmp_path, monkeypatch):
    """En la prueba en vivo (Windows sin matplotlib) el PDF salió con Helvetica y perdió Δ, ₂ y ².
    La fuente DejaVu va incluida en recursos/fuentes y no depende de matplotlib."""
    import sys

    monkeypatch.setitem(sys.modules, "matplotlib", None)
    assert reportes._registrar_fuentes() == ("DejaVu", "DejaVu-Bold")
    calc = POR_ID["ductos"]
    resultado = calc.calcular(CASOS["ductos"])
    ruta = tmp_path / "ductos.pdf"
    reportes.generar_pdf(ruta, calc, calc.validar(CASOS["ductos"]), resultado)
    contenido = ruta.read_bytes()
    # ReportLab siempre declara Helvetica como fuente base; lo que importa es que el texto use DejaVu incrustada
    assert b"+DejaVuSans" in contenido and b"+DejaVuSans-Bold" in contenido
