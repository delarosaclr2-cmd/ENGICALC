"""Accesos a aplicaciones completas; sus motores conservan sus propios paquetes."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import os
import subprocess
import sys
import tempfile

from .nucleo.configuracion import RAIZ


@dataclass(frozen=True)
class Aplicacion:
    id: str
    nombre: str
    disciplina: str
    descripcion: str
    modulo: str = ""
    carpeta: str = ""
    estado_auditoria: str = "PR #4: correcciones en revisión"
    estado_validacion: str = "Revisión pendiente"
    limitaciones: tuple[str, ...] = (
        "La revisión del PR #4 sigue pendiente; comprobar los resultados para cada proyecto.",
        "Las unidades, criterios y datos de material deben corresponder al servicio real.",
    )
    archivos_originales: tuple[str, ...] = ()


def _linea(id, nombre, disciplina, descripcion):
    return Aplicacion(id, nombre, disciplina, descripcion,
                      modulo=f"calculadoras.{id}.{id}.gui_tk",
                      archivos_originales=(f"calculadoras/{id}/",))


APLICACIONES = (
    _linea("linea_agua", "Líneas de agua", "Máquinas de fluido y bombeo",
           "Velocidad, pérdidas de presión, NPSH, espesor y selección de diámetros de agua."),
    _linea("linea_vapor", "Líneas de vapor", "Térmica y transferencia de calor",
           "Propiedades del vapor, velocidad, pérdidas, venteo y espesor. Revisar cada diámetro "
           "con el cálculo completo: el barrido conserva los K del diámetro original."),
    _linea("linea_aceite", "Líneas de aceite", "Máquinas de fluido y bombeo",
           "Viscosidad, velocidad, pérdidas de presión y espesor de líneas de aceite."),
    _linea("linea_gas", "Líneas de gas y aire comprimido", "Máquinas de fluido y bombeo",
           "Flujo compresible, velocidad, presión de llegada y capacidad. Comprobar el caudal "
           "máximo mostrado: el redondeo puede cambiar el dictamen al volver a capturarlo."),
    _linea("gas_combustible", "Gas combustible", "Térmica y transferencia de calor",
           "Composición del gas, propiedades, consumo de combustible y caudales de turbinas."),
    _linea("tanque_pulmon", "Tanque pulmón de aire comprimido", "Máquinas de fluido y bombeo",
           "Retención, volumen requerido, ciclo de compresor y presión admisible de tuberías."),
    Aplicacion(
        "hvac_industrial", "HVAC industrial · aplicación completa", "Ventilación y control de polvo",
        "Propiedades del aire, caudales, campanas, ductos, redes, ventiladores, potencia y reportes.",
        carpeta="HVAC_INDUSTRIAL_CALCULATOR",
        estado_auditoria="Revisión técnica documentada",
        estado_validacion="Verificación numérica documentada",
        limitaciones=("Los criterios y coeficientes deben verificarse para cada proyecto.",
                      "Se abre en una ventana independiente; requiere las dependencias de HVAC industrial."),
        archivos_originales=("HVAC_INDUSTRIAL_CALCULATOR/main.py",),
    ),
)
POR_ID = {a.id: a for a in APLICACIONES}


def abrir_nativa(raiz, aplicacion: Aplicacion):
    """Las aplicaciones Tk comparten la raíz y el acceso del menú, sin otro mainloop."""
    ventana, marco = import_module(aplicacion.modulo).abrir(raiz)

    def cerrar():
        # En ejecución independiente se cierra toda la sesión. Dentro del menú hay que cancelar
        # el recálculo pendiente del formulario antes de destruir solo esta ventana.
        pendiente = getattr(marco, "_pendiente", None)
        if pendiente:
            marco.after_cancel(pendiente)
            marco._pendiente = None
        ventana.destroy()

    ventana.protocol("WM_DELETE_WINDOW", cerrar)
    return ventana


def interprete(carpeta: Path) -> Path:
    """Prefiere el entorno instalado por instalar_windows.bat; después el Python del menú."""
    candidatos = (carpeta / ".venv" / "Scripts" / "python.exe",
                  carpeta / ".venv" / "bin" / "python", Path(sys.executable))
    elegido = next(p for p in candidatos if p.is_file())
    if elegido.name.lower() == "pythonw.exe":
        consola = elegido.with_name("python.exe")
        if consola.is_file():
            elegido = consola
    return elegido


class ProcesoAplicacion:
    """Proceso independiente y registro de errores para el aviso asíncrono del menú."""

    def __init__(self, proceso, registro, carpeta):
        self.proceso = proceso
        self.registro = registro
        self.carpeta = carpeta
        self.salida = Path(registro.name) / "salida.log"

    def __getattr__(self, nombre):
        return getattr(self.proceso, nombre)

    def mensaje_error(self):
        try:
            texto = self.salida.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            texto = ""
        causa = texto.splitlines()[-1] if texto else "El proceso terminó de forma inesperada."
        mensaje = f"HVAC industrial terminó con un error:\n{causa}"
        if "ModuleNotFoundError" in texto or "ImportError" in texto:
            mensaje += f"\n\nEjecute {self.carpeta / 'instalar_windows.bat'} y vuelva a abrirla."
        return mensaje

    def cerrar_registro(self):
        self.registro.cleanup()


def abrir_externa(aplicacion: Aplicacion):
    """Arranca HVAC una sola vez, sin cargar previamente sus bibliotecas en otro proceso.

    Los errores del propio arranque se recogen en un registro temporal y el menú los consulta
    sin bloquear su interfaz. No se instala ni modifica ningún paquete al abrir la aplicación.
    """
    carpeta = RAIZ / aplicacion.carpeta
    entrada = carpeta / "main.py"
    if not entrada.is_file():
        raise ValueError(f"No se encontró la aplicación: {entrada}")
    python = interprete(carpeta)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    if os.name == "nt" and python.with_name("pythonw.exe").is_file():
        python = python.with_name("pythonw.exe")
    # En Windows, al cerrar el menú HVAC puede seguir usando el archivo: no se fuerza su cierre.
    registro = tempfile.TemporaryDirectory(prefix="engicalc_hvac_", ignore_cleanup_errors=True)
    try:
        with (Path(registro.name) / "salida.log").open("w", encoding="utf-8") as salida:
            proceso = subprocess.Popen([str(python), str(entrada)], cwd=carpeta,
                                       stdin=subprocess.DEVNULL, stdout=salida,
                                       stderr=subprocess.STDOUT, creationflags=flags,
                                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except OSError:
        registro.cleanup()
        raise
    return ProcesoAplicacion(proceso, registro, carpeta)
