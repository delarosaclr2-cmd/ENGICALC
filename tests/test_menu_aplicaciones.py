"""Inventario, apertura y aislamiento de las aplicaciones integradas al menú."""
from types import SimpleNamespace
from pathlib import Path
import json
import subprocess
import time

import pytest

from calculadoras import aplicaciones
from calculadoras.catalogo import HERRAMIENTAS, POR_ID, buscar
from tests.test_interfaz import HAY_PANTALLA, menu

NATIVAS = [a for a in aplicaciones.APLICACIONES if a.modulo]
HVAC = aplicaciones.POR_ID["hvac_industrial"]


def test_inventario_completo_y_archivos_existentes():
    assert len(HERRAMIENTAS) == len(POR_ID) == 25
    assert {a.id for a in aplicaciones.APLICACIONES} == {
        "linea_agua", "linea_vapor", "linea_aceite", "linea_gas", "gas_combustible",
        "tanque_pulmon", "hvac_industrial",
    }
    assert [a.id for a in buscar("HVAC industrial")] == ["hvac_industrial"]
    assert [a.id for a in buscar("aceite")] == ["linea_aceite"]
    for app in aplicaciones.APLICACIONES:
        for archivo in app.archivos_originales:
            assert (aplicaciones.RAIZ / archivo).exists()


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
@pytest.mark.parametrize("app", NATIVAS, ids=lambda a: a.id)
def test_abrir_calcular_cerrar_y_reabrir_desde_menu(menu, app):
    menu.texto_busqueda.set(app.id)
    menu.arbol.selection_set(app.id)
    menu.describir()
    ventana = menu.abrir_seleccion()
    menu.raiz.update()
    marco = next(w for w in ventana.winfo_children() if hasattr(w, "memoria"))
    assert marco.memoria is not None
    assert marco.memoria.resultados
    assert menu.abrir(app.id) is ventana
    # Simula una edición antes del cierre: su callback no debe ejecutarse sobre widgets destruidos.
    pendientes = []
    marco._pendiente = marco.after(10000, lambda: pendientes.append("ejecutado"))
    token = marco._pendiente
    menu.raiz.tk.call(ventana.protocol("WM_DELETE_WINDOW"))
    assert token not in menu.raiz.tk.call("after", "info")
    assert menu.winfo_exists() and not pendientes
    nueva = menu.abrir(app.id)
    menu.raiz.update()
    assert nueva is not ventana
    assert not menu.errores


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
def test_correccion_redondeo_gas_desde_menu(menu):
    ventana = menu.abrir("linea_gas")
    marco = next(w for w in ventana.winfo_children() if hasattr(w, "memoria"))
    ruta = Path(__file__).resolve().parents[1] / "calculadoras/linea_gas/casos/DM014E_L1_rack_4in.json"
    caso = json.loads(ruta.read_text(encoding="utf-8"))
    caso["criterios"] = {"v_max_m_s": 15.0}
    marco.poner(caso)
    tabla = next(t for t in marco.memoria.tablas if t[0].startswith("Capacidad de la línea"))
    fila = next(f for f in tabla[2] if "máxima" in f[0])
    assert fila[2] == "3,026.14"
    caso["caudal"]["valor"] = float(fila[2].replace(",", ""))
    marco.poner(caso)
    verificacion = next(v for v in marco.memoria.verificaciones if v[0] == "Velocidad máxima")
    assert verificacion[3] == "CUMPLE"
    assert not menu.errores


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
def test_correccion_accesorios_vapor_desde_menu(menu):
    ventana = menu.abrir("linea_vapor")
    marco = next(w for w in ventana.winfo_children() if hasattr(w, "memoria"))
    ruta = Path(__file__).resolve().parents[1] / "calculadoras/linea_vapor/casos/ESCENARIO_principal_12in_150m.json"
    caso = json.loads(ruta.read_text(encoding="utf-8"))
    caso["flujo"]["valor"] = 53265.24
    marco.poner(caso)
    tabla = next(t for t in marco.memoria.tablas if t[0].startswith("Velocidad por diámetro"))
    fila = next(f for f in tabla[2] if f[0] == "8")
    assert fila[7] == "NO CUMPLE"
    assert float(fila[3]) == pytest.approx(51.020, abs=0.001)
    caso["tuberia"]["nps"] = "8"
    marco.poner(caso)
    verificacion = next(v for v in marco.memoria.verificaciones if v[0].startswith("Velocidad máxima"))
    assert verificacion[3] == "NO CUMPLE"
    assert not menu.errores


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
def test_hvac_se_abre_aparte_y_no_duplica_proceso(menu, monkeypatch):
    from calculadoras.interfaz import menu as modulo_menu

    estado = {"codigo": None}
    proceso = SimpleNamespace(poll=lambda: estado["codigo"])
    aperturas, avisos = [], []
    monkeypatch.setattr(modulo_menu, "abrir_externa", lambda app: aperturas.append(app.id) or proceso)
    monkeypatch.setattr(modulo_menu.messagebox, "showinfo", lambda *a, **kw: avisos.append(a))
    assert menu.abrir(HVAC.id) is proceso
    assert menu.abrir(HVAC.id) is proceso
    assert aperturas == [HVAC.id] and avisos
    assert HVAC.id not in menu.ventanas
    estado["codigo"] = 0
    assert menu.abrir(HVAC.id) is proceso
    assert aperturas == [HVAC.id, HVAC.id]


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
def test_error_hvac_se_informa_sin_cerrar_menu(menu, monkeypatch):
    from calculadoras.interfaz import menu as modulo_menu

    def fallar(app):
        raise ValueError("Falta PySide6")

    avisos = []
    monkeypatch.setattr(modulo_menu, "abrir_externa", fallar)
    monkeypatch.setattr(modulo_menu.messagebox, "showerror", lambda *a, **kw: avisos.append(a))
    assert menu.abrir(HVAC.id) is None
    assert avisos and menu.winfo_exists()
    assert HVAC.id not in menu.procesos


@pytest.mark.parametrize("app", aplicaciones.APLICACIONES, ids=lambda a: a.id)
def test_acceso_directo_por_comando(app, monkeypatch):
    import menu_principal
    from calculadoras.interfaz import menu as modulo_menu

    aperturas = []
    monkeypatch.setattr(modulo_menu, "iniciar", aperturas.append)
    assert menu_principal.main(["--calculadora", app.id]) == 0
    assert aperturas == [app.id]


def test_lanzador_prefiere_entorno_instalado_y_usa_rutas_absolutas(tmp_path, monkeypatch):
    carpeta = tmp_path / "HVAC_INDUSTRIAL_CALCULATOR"
    carpeta.mkdir()
    (carpeta / "main.py").touch()
    scripts = carpeta / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    python = scripts / "python.exe"
    python.touch()
    llamadas = []
    monkeypatch.setattr(aplicaciones, "RAIZ", tmp_path)
    monkeypatch.setattr(aplicaciones.subprocess, "run", lambda *a, **kw:
                        pytest.fail("El inicio no debe cargar las bibliotecas en otro proceso"))
    proceso = SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(aplicaciones.subprocess, "Popen", lambda args, **kw:
                        llamadas.append((args, kw)) or proceso)
    abierto = aplicaciones.abrir_externa(HVAC)
    assert abierto.proceso is proceso and len(llamadas) == 1
    args, opciones = llamadas[0]
    assert args == [str(python), str(carpeta / "main.py")]
    assert opciones["cwd"] == carpeta
    assert opciones["stdin"] == subprocess.DEVNULL
    assert opciones["stderr"] == subprocess.STDOUT
    abierto.cerrar_registro()


def test_dependencias_ausentes_se_recogen_del_propio_arranque(tmp_path, monkeypatch):
    carpeta = tmp_path / HVAC.carpeta
    carpeta.mkdir()
    (carpeta / "main.py").write_text("raise ModuleNotFoundError(\"No module named 'PySide6'\")",
                                      encoding="utf-8")
    monkeypatch.setattr(aplicaciones, "RAIZ", tmp_path)
    monkeypatch.setattr(aplicaciones.subprocess, "run", lambda *a, **kw:
                        pytest.fail("No debe ejecutar otra comprobación ni instalar paquetes"))
    proceso = aplicaciones.abrir_externa(HVAC)
    try:
        assert proceso.wait(timeout=10) != 0
        assert "PySide6" in proceso.mensaje_error()
        assert "instalar_windows.bat" in proceso.mensaje_error()
    finally:
        proceso.cerrar_registro()
    assert not proceso.salida.exists()


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
def test_menu_muestra_error_asincrono_y_sigue_utilizable(menu, tmp_path, monkeypatch):
    from calculadoras.interfaz import menu as modulo_menu

    carpeta = tmp_path / HVAC.carpeta
    carpeta.mkdir()
    (carpeta / "main.py").write_text("raise ModuleNotFoundError(\"No module named 'PySide6'\")",
                                      encoding="utf-8")
    monkeypatch.setattr(aplicaciones, "RAIZ", tmp_path)
    avisos = []
    monkeypatch.setattr(modulo_menu.messagebox, "showerror", lambda *a, **kw: avisos.append(a))
    proceso = menu.abrir(HVAC.id)
    limite = time.monotonic() + 10
    while not avisos and time.monotonic() < limite:
        menu.raiz.update()
        time.sleep(0.02)
    assert avisos and "PySide6" in avisos[0][1]
    assert proceso.poll() != 0 and not proceso.salida.exists()
    assert menu.abrir("viga").winfo_exists()
    assert HVAC.id not in menu._vigias


@pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")
def test_cerrar_menu_cancela_vigilancia_y_conserva_hvac(menu, monkeypatch):
    from calculadoras.interfaz import menu as modulo_menu

    proceso = SimpleNamespace(poll=lambda: None,
                             terminate=lambda: pytest.fail("Cerrar el menú no debe terminar HVAC"))
    monkeypatch.setattr(modulo_menu, "abrir_externa", lambda app: proceso)
    menu.abrir(HVAC.id)
    token = menu._vigias[HVAC.id]
    menu.destroy()
    assert token not in menu.raiz.tk.call("after", "info")
    assert proceso.poll() is None
