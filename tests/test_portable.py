"""Regresiones de la distribución: datos persistentes, recursos y proceso HVAC."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import sys

import pytest

from calculadoras import aplicaciones
from calculadoras.nucleo import rutas, configuracion, historial


@pytest.fixture
def portable(tmp_path, monkeypatch):
    instalacion = tmp_path / 'Programa con espacios'
    recursos = instalacion / '_internal'
    recursos.mkdir(parents=True)
    (instalacion / 'portable.flag').touch()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(recursos), raising=False)
    monkeypatch.setattr(sys, 'executable', str(instalacion / 'ENGICALC.exe'))
    return instalacion, recursos


def test_datos_portable_separados_de_recursos_y_directorio_actual(portable, tmp_path, monkeypatch):
    instalacion, recursos = portable
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('CALCULADORAS_REGISTRO', raising=False)
    assert rutas.raiz_recursos() == recursos
    assert rutas.raiz_instalacion() == instalacion
    assert rutas.carpeta_datos() == instalacion / 'datos_usuario'
    assert historial.carpeta_registro() == instalacion / 'datos_usuario/registro'
    assert historial.guardar_proyecto({'proyecto': 'Prueba portable'})
    assert historial.cargar_proyecto()['proyecto'] == 'Prueba portable'
    assert not (recursos / 'registro').exists()


def test_distribucion_sin_marca_usa_perfil_del_usuario(portable, tmp_path, monkeypatch):
    instalacion, _ = portable
    (instalacion / 'portable.flag').unlink()
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'perfil'))
    assert rutas.carpeta_datos() == tmp_path / 'perfil/RMR/ENGICALC'


def test_fuente_conserva_rutas_y_override_de_pruebas(tmp_path, monkeypatch):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    assert rutas.carpeta_datos() == Path(__file__).resolve().parents[1]
    monkeypatch.setenv('CALCULADORAS_REGISTRO', str(tmp_path))
    assert historial.carpeta_registro() == tmp_path


def test_configuracion_inicial_conserva_clave_y_actualizacion_no_pisa_usuario(portable, monkeypatch):
    instalacion, recursos = portable
    distribuida = recursos / 'config/configuracion.json'
    distribuida.parent.mkdir()
    original = configuracion.cargar()
    original['sitio']['nombre'] = 'Sitio de fábrica'
    distribuida.write_text(json.dumps(original), encoding='utf-8')
    usuario = instalacion / 'datos_usuario/config/configuracion.json'
    monkeypatch.setattr(configuracion, 'RUTA_CONFIG_DISTRIBUIDA', distribuida)
    monkeypatch.setattr(configuracion, 'RUTA_CONFIG', usuario)
    assert configuracion.verificar_contrasena('usuario', 'rmr123')
    configuracion.establecer_contrasena('otra-clave')
    assert configuracion.cargar()['sitio']['nombre'] == 'Sitio de fábrica'
    assert configuracion.verificar_contrasena('usuario', 'otra-clave')
    assert not configuracion.verificar_contrasena('usuario', 'rmr123')
    distribuida.write_text('{}', encoding='utf-8')
    assert configuracion.verificar_contrasena('usuario', 'otra-clave')
    assert not configuracion.verificar_contrasena('usuario', 'otra-clave', original)


def test_hvac_portable_no_busca_python_y_no_hereda_bootloader(portable, monkeypatch):
    instalacion, _ = portable
    carpeta = instalacion / 'HVAC_INDUSTRIAL_CALCULATOR'
    carpeta.mkdir()
    ejecutable = carpeta / 'HVAC_Calculator.exe'
    ejecutable.touch()
    llamadas = []
    monkeypatch.setattr(aplicaciones, 'interprete', lambda *a: pytest.fail('No debe buscar Python'))
    monkeypatch.setattr(aplicaciones.subprocess, 'Popen', lambda args, **kw:
                        llamadas.append((args, kw)) or SimpleNamespace(poll=lambda: None))
    proceso = aplicaciones.abrir_externa(aplicaciones.POR_ID['hvac_industrial'])
    try:
        assert llamadas[0][0] == [str(ejecutable)]
        assert llamadas[0][1]['cwd'] == carpeta
        assert llamadas[0][1]['env']['PYINSTALLER_RESET_ENVIRONMENT'] == '1'
        proceso.salida.write_text('ImportError: prueba', encoding='utf-8')
        assert 'instalar_windows.bat' not in proceso.mensaje_error()
        assert 'ZIP completo' in proceso.mensaje_error()
    finally:
        proceso.cerrar_registro()


def test_hvac_ausente_da_error_sin_volver_a_abrir_el_menu(portable):
    with pytest.raises(ValueError, match='HVAC_Calculator.exe'):
        aplicaciones.abrir_externa(aplicaciones.POR_ID['hvac_industrial'])


def test_hvac_guarda_datos_en_la_misma_carpeta_portable(portable, monkeypatch):
    instalacion, _ = portable
    monkeypatch.delenv('ENGICALC_HVAC_DATOS', raising=False)
    monkeypatch.setattr(sys, 'executable', str(instalacion / 'HVAC_INDUSTRIAL_CALCULATOR/HVAC_Calculator.exe'))
    archivo = Path(__file__).resolve().parents[1] / 'HVAC_INDUSTRIAL_CALCULATOR/config/settings.py'
    spec = importlib.util.spec_from_file_location('settings_portable_prueba', archivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert Path(modulo.user_data_dir()) == instalacion / 'datos_usuario/HVAC'
    assert (instalacion / 'datos_usuario/HVAC').is_dir()


def test_hvac_guardar_configuracion_no_modifica_la_copia_distribuida(portable, monkeypatch):
    instalacion, recursos = portable
    monkeypatch.delenv('ENGICALC_HVAC_DATOS', raising=False)
    monkeypatch.setattr(sys, 'executable', str(instalacion / 'HVAC_INDUSTRIAL_CALCULATOR/HVAC_Calculator.exe'))
    archivo = Path(__file__).resolve().parents[1] / 'HVAC_INDUSTRIAL_CALCULATOR/config/settings.py'
    spec = importlib.util.spec_from_file_location('settings_portable_guardar', archivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    config = recursos / 'config'
    config.mkdir()
    defecto, distribuida = config / 'default.json', config / 'settings.json'
    defecto.write_text('{"app":{"prueba":1}}', encoding='utf-8')
    distribuida.write_text('{"app":{"prueba":2}}', encoding='utf-8')
    monkeypatch.setattr(modulo, 'DEFAULT_PATH', str(defecto))
    monkeypatch.setattr(modulo, 'SHIPPED_PATH', str(distribuida))
    settings = modulo.load_settings()
    assert settings.app('prueba') == 2 and settings.path is None
    settings.data['app']['prueba'] = 3
    guardada = Path(settings.save())
    assert guardada == instalacion / 'datos_usuario/HVAC/settings.json'
    assert json.loads(distribuida.read_text())['app']['prueba'] == 2
    assert modulo.load_settings().app('prueba') == 3
