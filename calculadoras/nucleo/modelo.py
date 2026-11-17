"""Modelo de datos común a todas las calculadoras.

Cada calculadora se describe con un objeto :class:`Calculadora`:

- ``campos``: lista de :class:`Campo` (etiqueta, unidad, rango válido, valor por
  defecto). La interfaz construye el formulario a partir de esta lista, de modo
  que agregar una calculadora nueva no requiere programar ventanas.
- ``funcion``: recibe un ``dict`` con las entradas ya validadas y devuelve un
  :class:`Resultado`.

El :class:`Resultado` guarda cada salida con su unidad y su **nivel de
confianza**, de forma que la memoria de cálculo distingue lo verificado de lo
que es un criterio heredado sin fuente.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Estados de auditoría (instrucciones del proyecto, sección 9)
# ---------------------------------------------------------------------------
NO_REVISADA = "NO REVISADA"
EN_AUDITORIA = "EN AUDITORÍA"
ERROR_DETECTADO = "ERROR DETECTADO"
CORREGIDA = "CORREGIDA"
VALIDACION_PENDIENTE = "VALIDACIÓN PENDIENTE"
VALIDADA_CONDICIONES = "VALIDADA BAJO CONDICIONES DOCUMENTADAS"

# ---------------------------------------------------------------------------
# Nivel de confianza de cada salida
# ---------------------------------------------------------------------------
VERIFICADA = "V"   # ecuación física o normativa verificada con cálculo independiente
EMPIRICA = "E"     # correlación empírica con referencia bibliográfica identificada
ORIGINAL = "O"     # criterio heredado de la versión original, sin fuente: NO validado
DATO = "D"         # dato de entrada, conversión de unidades o valor informativo

NIVELES = {
    VERIFICADA: "Verificada",
    EMPIRICA: "Empírica (con referencia)",
    ORIGINAL: "Criterio original sin fuente — no validado",
    DATO: "Dato / conversión",
}


class ErrorEntrada(ValueError):
    """Error de validación de datos de entrada. ``errores`` lista los mensajes."""

    def __init__(self, errores: list[str] | str):
        if isinstance(errores, str):
            errores = [errores]
        self.errores = list(errores)
        super().__init__("\n".join(self.errores))


@dataclass
class Campo:
    """Definición de un dato de entrada.

    ``defecto=None`` hace el campo obligatorio. Para campos opcionales cuyo valor
    0 significa «no aplica» se documenta en ``ayuda``.
    """

    clave: str
    etiqueta: str
    unidad: str = ""
    tipo: str = "real"            # "real" | "entero" | "opcion"
    defecto: Any = None
    minimo: Optional[float] = None
    maximo: Optional[float] = None
    min_incluido: bool = True
    max_incluido: bool = True
    opciones: tuple = ()
    ayuda: str = ""
    grupo: str = "Datos de entrada"

    @property
    def obligatorio(self) -> bool:
        return self.defecto is None

    def describir_rango(self) -> str:
        partes = []
        if self.minimo is not None:
            partes.append(("≥ " if self.min_incluido else "> ") + _fmt(self.minimo))
        if self.maximo is not None:
            partes.append(("≤ " if self.max_incluido else "< ") + _fmt(self.maximo))
        return " y ".join(partes)

    def convertir(self, valor: Any) -> Any:
        """Convierte y valida un valor (texto o número). Lanza ErrorEntrada."""
        nombre = f"«{self.etiqueta}»"
        if self.tipo == "opcion":
            texto = "" if valor is None else str(valor).strip()
            if texto == "" and self.defecto is not None:
                texto = str(self.defecto)
            if texto not in self.opciones:
                raise ErrorEntrada(f"{nombre}: seleccione una opción válida ({', '.join(self.opciones)}).")
            return texto

        if valor is None or (isinstance(valor, str) and valor.strip() == ""):
            if self.defecto is None:
                raise ErrorEntrada(f"{nombre}: dato obligatorio.")
            valor = self.defecto

        if isinstance(valor, str):
            texto = valor.strip().replace(",", ".")
            try:
                numero = float(texto)
            except ValueError:
                raise ErrorEntrada(f"{nombre}: «{valor}» no es un número válido.") from None
        else:
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                raise ErrorEntrada(f"{nombre}: valor no numérico.") from None

        if not math.isfinite(numero):
            raise ErrorEntrada(f"{nombre}: el valor debe ser finito.")

        if self.tipo == "entero":
            if abs(numero - round(numero)) > 1e-9:
                raise ErrorEntrada(f"{nombre}: debe ser un número entero.")
            numero = int(round(numero))

        if self.minimo is not None:
            if numero < self.minimo or (not self.min_incluido and numero == self.minimo):
                raise ErrorEntrada(f"{nombre}: debe ser {self.describir_rango()} {self.unidad}".rstrip() + ".")
        if self.maximo is not None:
            if numero > self.maximo or (not self.max_incluido and numero == self.maximo):
                raise ErrorEntrada(f"{nombre}: debe ser {self.describir_rango()} {self.unidad}".rstrip() + ".")
        return numero


@dataclass
class Salida:
    clave: str
    etiqueta: str
    valor: Any
    unidad: str = ""
    decimales: int = 3
    nivel: str = VERIFICADA
    nota: str = ""

    def texto_valor(self) -> str:
        if isinstance(self.valor, str):
            return self.valor
        if self.valor is None:
            return "—"
        if isinstance(self.valor, bool):
            return "Sí" if self.valor else "No"
        if isinstance(self.valor, int):
            return f"{self.valor:,d}".replace(",", " ")
        v = float(self.valor)
        if v != 0 and (abs(v) >= 1e7 or abs(v) < 10 ** (-self.decimales)):
            return f"{v:.{max(self.decimales, 3)}e}"
        return f"{v:,.{self.decimales}f}".replace(",", " ")


@dataclass
class Resultado:
    salidas: list[Salida] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    ecuaciones: list[str] = field(default_factory=list)

    def agregar(self, clave: str, etiqueta: str, valor: Any, unidad: str = "",
                decimales: int = 3, nivel: str = VERIFICADA, nota: str = "") -> None:
        if isinstance(valor, float) and not math.isfinite(valor):
            raise ArithmeticError(f"Resultado no finito en «{etiqueta}».")
        self.salidas.append(Salida(clave, etiqueta, valor, unidad, decimales, nivel, nota))

    def advertir(self, mensaje: str) -> None:
        if mensaje not in self.advertencias:
            self.advertencias.append(mensaje)

    def nota(self, mensaje: str) -> None:
        if mensaje not in self.notas:
            self.notas.append(mensaje)

    def ecuacion(self, texto: str) -> None:
        if texto not in self.ecuaciones:
            self.ecuaciones.append(texto)

    def __getitem__(self, clave: str) -> Any:
        for s in self.salidas:
            if s.clave == clave:
                return s.valor
        raise KeyError(clave)

    def __contains__(self, clave: str) -> bool:
        return any(s.clave == clave for s in self.salidas)

    def salida(self, clave: str) -> Salida:
        for s in self.salidas:
            if s.clave == clave:
                return s
        raise KeyError(clave)

    def como_dict(self) -> dict:
        return {
            "salidas": [
                {"clave": s.clave, "etiqueta": s.etiqueta, "valor": s.valor, "unidad": s.unidad,
                 "nivel": s.nivel, "nota": s.nota}
                for s in self.salidas
            ],
            "advertencias": list(self.advertencias),
            "notas": list(self.notas),
            "ecuaciones": list(self.ecuaciones),
        }


@dataclass
class Calculadora:
    """Descripción completa de una calculadora."""

    id: str
    nombre: str
    disciplina: str
    descripcion: str
    campos: list[Campo]
    funcion: Callable[[dict], Resultado]
    estado_auditoria: str = CORREGIDA
    estado_validacion: str = VALIDACION_PENDIENTE
    archivos_originales: tuple = ()
    referencias: tuple = ()
    limitaciones: tuple = ()
    graficar: Optional[Callable[[dict, Resultado], Any]] = None
    imagenes: tuple = ()
    palabras_clave: tuple = ()
    claves_heredadas: dict = field(default_factory=dict)

    def campo(self, clave: str) -> Campo:
        for c in self.campos:
            if c.clave == clave:
                return c
        raise KeyError(clave)

    def valores_por_defecto(self) -> dict:
        return {c.clave: c.defecto for c in self.campos}

    def validar(self, entradas: dict) -> dict:
        """Convierte y valida todas las entradas; reúne todos los errores a la vez."""
        datos, errores = {}, []
        for c in self.campos:
            try:
                datos[c.clave] = c.convertir(entradas.get(c.clave))
            except ErrorEntrada as e:
                errores.extend(e.errores)
        if errores:
            raise ErrorEntrada(errores)
        return datos

    def calcular(self, entradas: dict) -> Resultado:
        """Valida las entradas y ejecuta el cálculo.

        Lanza :class:`ErrorEntrada` si un dato no es válido o si la combinación
        de datos no tiene sentido físico (la función de cálculo puede lanzarla).
        """
        datos = self.validar(entradas)
        try:
            resultado = self.funcion(datos)
        except ZeroDivisionError as e:  # protección adicional; los cálculos validan antes
            raise ErrorEntrada(f"División entre cero con los datos dados ({e}).") from e
        except (OverflowError, ArithmeticError) as e:
            raise ErrorEntrada(f"Los datos producen un resultado no válido: {e}") from e
        return resultado


def requerir(condicion: bool, mensaje: str) -> None:
    """Lanza ErrorEntrada si la condición física no se cumple."""
    if not condicion:
        raise ErrorEntrada(mensaje)


def _fmt(x: float) -> str:
    return f"{x:g}"
