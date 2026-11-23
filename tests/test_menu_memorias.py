"""Acceso real a las memorias desde el menú y desde la línea de comandos."""
import json

import pytest

from calculadoras.memorias import MEMORIAS, reportes
from tests.test_interfaz import HAY_PANTALLA, menu


@pytest.fixture
def menu_memorias(menu, monkeypatch):
    from calculadoras.memorias.ventana import VentanaMemoria

    monkeypatch.setattr(VentanaMemoria, "mostrar_error",
                        lambda self, error: menu.errores.append(("Memoria", str(error))))
    return menu


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
class TestMemoriasEnMenu:
    @pytest.mark.parametrize("memoria", MEMORIAS, ids=lambda m: m.id)
    def test_buscar_abrir_reutilizar_y_reabrir(self, menu_memorias, memoria):
        menu = menu_memorias
        menu.texto_busqueda.set(memoria.nombre.split(" ·")[0])
        assert menu.arbol.exists(memoria.id)
        assert menu.arbol.item(menu.arbol.parent(memoria.id), "text") == memoria.disciplina
        menu.arbol.selection_set(memoria.id)
        menu.describir()
        assert menu.titulo.cget("text") == memoria.nombre
        ventana = menu.abrir_seleccion()
        menu.raiz.update()
        assert ventana.memoria is memoria
        assert ventana.resultado is not None, menu.errores
        assert menu.abrir(memoria.id) is ventana
        ventana.destroy()
        assert menu.winfo_exists()
        nueva = menu.abrir(memoria.id)
        menu.raiz.update()
        assert nueva is not ventana and nueva.resultado is not None
        assert not menu.errores

    @pytest.mark.parametrize("memoria", MEMORIAS, ids=lambda m: m.id)
    def test_abrir_caso_desde_archivo_del_menu(self, menu_memorias, memoria, tmp_path, monkeypatch):
        from calculadoras.interfaz import menu as modulo_menu

        estado = memoria.motor.por_defecto()
        if memoria.modulo == "agitadores":
            bloque, campo, valor = "inputs", "N", 80
        elif memoria.modulo == "bombas":
            bloque, campo, valor = "inputs", "qd", 90
        else:
            bloque, campo, valor = "main", "L", 30
        estado[bloque][campo] = valor
        ruta = tmp_path / "caso.json"
        reportes.guardar_caso(ruta, memoria, estado, {"Proyecto": "Caso desde el menú"}, unidades="US")
        monkeypatch.setattr(modulo_menu.filedialog, "askopenfilename", lambda **kw: str(ruta))
        menu_memorias.abrir_caso()
        menu_memorias.raiz.update()
        ventana = menu_memorias.ventanas[memoria.id]
        # La captura US convierte y redondea a diez cifras al mostrar los campos.
        assert ventana.estado[bloque][campo] == pytest.approx(valor, rel=1e-8)
        assert ventana.documento["Proyecto"] == "Caso desde el menú"
        assert ventana.unidades.get() == "US"
        assert ventana.resultado is not None, menu_memorias.errores
        assert not menu_memorias.errores

    def test_abrir_caso_de_calculadora_basica(self, menu_memorias, tmp_path, monkeypatch):
        from calculadoras.calculos import POR_ID
        from calculadoras.interfaz import menu as modulo_menu, reportes as reportes_basicos
        from tests.casos import CASOS

        calc = POR_ID["bomba"]
        ruta = tmp_path / "bomba.json"
        reportes_basicos.guardar_caso(ruta, calc, CASOS["bomba"], calc.calcular(CASOS["bomba"]))
        monkeypatch.setattr(modulo_menu.filedialog, "askopenfilename", lambda **kw: str(ruta))
        menu_memorias.abrir_caso()
        assert menu_memorias.ventanas["bomba"].ultimo is not None
        assert not menu_memorias.errores

    @pytest.mark.parametrize("contenido", [
        [],
        {"formato": "RMR-memoria", "version": 999, "calculadora": "memoria_bombas", "datos": {}},
    ])
    def test_caso_invalido_no_reemplaza_resultados(self, menu_memorias, tmp_path, monkeypatch, contenido):
        from calculadoras.interfaz import menu as modulo_menu

        ventana = menu_memorias.abrir("memoria_bombas")
        resultado = ventana.resultado
        avisos = []
        monkeypatch.setattr(modulo_menu.messagebox, "showerror", lambda *a, **kw: avisos.append(a))
        ruta = tmp_path / "invalido.json"
        ruta.write_text(json.dumps(contenido), encoding="utf-8")
        monkeypatch.setattr(modulo_menu.filedialog, "askopenfilename", lambda **kw: str(ruta))
        menu_memorias.abrir_caso()
        assert avisos
        assert ventana.resultado is resultado
        assert list(menu_memorias.ventanas) == ["memoria_bombas"]


def test_lista_incluye_memorias_sin_iniciar_interfaz(capsys, monkeypatch):
    import menu_principal
    from calculadoras.interfaz import menu as modulo_menu
    from calculadoras.catalogo import HERRAMIENTAS

    aperturas = []
    monkeypatch.setattr(modulo_menu, "iniciar", aperturas.append)
    assert menu_principal.main(["--lista"]) == 0
    salida = capsys.readouterr().out
    for herramienta in HERRAMIENTAS:
        assert herramienta.id in salida
    assert len(salida.splitlines()) == len(HERRAMIENTAS)
    assert not aperturas


@pytest.mark.parametrize("memoria", MEMORIAS, ids=lambda m: m.id)
def test_acceso_directo_por_comando(memoria, monkeypatch):
    import menu_principal
    from calculadoras.interfaz import menu as modulo_menu

    aperturas = []
    monkeypatch.setattr(modulo_menu, "iniciar", aperturas.append)
    assert menu_principal.main(["--calculadora", memoria.id]) == 0
    assert aperturas == [memoria.id]
