"""Calculadoras de Ingeniería RMR — versión corregida.

Paquete organizado en tres capas independientes:

- ``calculadoras.nucleo``    Constantes, unidades, validación, propiedades y
                             fórmulas compartidas (fluidos, psicrometría, sólidos).
- ``calculadoras.calculos``  Un módulo por calculadora. Solo contiene cálculo:
                             no importa Tkinter y se puede probar sin ventanas.
- ``calculadoras.interfaz``  Menú principal, ventanas de captura y reportes.
"""

__version__ = "2.2.0"
