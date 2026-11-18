"""Despacho de archivos independientes y ciclo de vida, sin requerir pantalla."""
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

from calculadoras.memorias import lanzador


@pytest.mark.parametrize("archivo,cid", [
    ("revisar_agitadores.py", "memoria_agitadores"),
    ("revisar_bombas.py", "memoria_bombas"),
    ("revisar_ductos_hvac.py", "memoria_hvac"),
])
def test_archivo_ejecutable_despacha_memoria(archivo, cid, monkeypatch, tmp_path):
    aperturas = []
    monkeypatch.setattr(lanzador, "iniciar", aperturas.append)
    monkeypatch.chdir(tmp_path)
    ruta = Path(__file__).resolve().parents[1] / archivo
    runpy.run_path(str(ruta), run_name="__main__")
    assert aperturas == [cid]


def preparar_entorno(monkeypatch, acceso=True):
    import tkinter as tk
    from tkinter import ttk
    from calculadoras.interfaz import acceso as modulo_acceso

    eventos = []
    ventana = SimpleNamespace(protocol=lambda nombre, callback: eventos.append((nombre, callback)))
    raiz = SimpleNamespace(
        withdraw=lambda: eventos.append("ocultar"),
        destroy=lambda: eventos.append("destruir"),
        mainloop=lambda: eventos.append("bucle"),
    )
    monkeypatch.setattr(tk, "Tk", lambda: raiz)
    monkeypatch.setattr(ttk, "Style", lambda padre: SimpleNamespace(
        theme_names=lambda: ("clam",), theme_use=lambda nombre: None))

    def solicitar(padre):
        eventos.append("acceso")
        return acceso

    def abrir(padre, cid):
        assert padre is raiz
        eventos.append(cid)
        return ventana

    monkeypatch.setattr(modulo_acceso, "solicitar_acceso", solicitar)
    monkeypatch.setattr(lanzador, "abrir_memoria", abrir)
    return raiz, eventos


def test_lanzador_comprueba_acceso_y_prepara_cierre(monkeypatch):
    raiz, eventos = preparar_entorno(monkeypatch)
    lanzador.iniciar("memoria_bombas")
    assert eventos[:3] == ["ocultar", "acceso", "memoria_bombas"]
    assert eventos[3] == ("WM_DELETE_WINDOW", raiz.destroy)
    assert eventos[4:] == ["bucle", "destruir"]


def test_acceso_cancelado_no_abre_memoria(monkeypatch):
    raiz, eventos = preparar_entorno(monkeypatch, acceso=False)
    lanzador.iniciar("memoria_agitadores")
    assert eventos == ["ocultar", "acceso", "destruir"]


def test_error_de_inicio_libera_raiz(monkeypatch):
    raiz, eventos = preparar_entorno(monkeypatch)

    def fallar(*args):
        raise ImportError("dependencia ausente")

    monkeypatch.setattr(lanzador, "abrir_memoria", fallar)
    with pytest.raises(ImportError, match="dependencia ausente"):
        lanzador.iniciar("memoria_hvac")
    assert eventos[-1] == "destruir"
    assert "bucle" not in eventos


def test_id_invalido_no_crea_raiz(monkeypatch):
    import tkinter as tk

    def no_crear():
        pytest.fail("No debe crear Tk con un identificador inválido")

    monkeypatch.setattr(tk, "Tk", no_crear)
    with pytest.raises(ValueError, match="Memoria desconocida"):
        lanzador.iniciar("ausente")
