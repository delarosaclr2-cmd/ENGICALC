# Migración de memorias de cálculo a Python nativo

Fecha: 13 de noviembre de 2026. Versión de aplicación: 2.1.0.

Actualización 2.1.1: las tres ventanas recalculan automáticamente al editar, tras 400 ms sin nuevas teclas. La sincronización de campos calculados no dispara nuevos cálculos. Se preservan el foco y los decimales incompletos, se notifican errores de captura en la propia ventana y se cancelan actualizaciones pendientes al restablecer o cerrar. Las tablas de curvas/accesorios, los ángulos de dampers y la propuesta de dimensionamiento también se actualizan al editar. El encabezado conserva un único botón **Restablecer ejemplo**; **F5** sigue disponible para recalcular manualmente.

Se reescribieron los tres motores y las interfaces de revisión A. No se incrustan páginas ni se ejecuta JavaScript: el funcionamiento diario depende de Python, Tkinter, NumPy, Matplotlib, Pillow, ReportLab y openpyxl. Todos los recursos y datos necesarios están dentro de PRINCIPAL; puede mover esta carpeta sin conservar las carpetas HTML originales.

## Funciones incorporadas

| Memoria | Funciones |
|---|---|
| Agitadores | Montaje vertical/lateral, geometría, seis impulsores, Reynolds, Np automático/manual, potencia, bombeo, tiempo de mezclado, Zwietering, caverna esférica/cilíndrica para fibra, motor IEC/NEMA, materiales, torque, flecha por esfuerzo/deflexión/velocidad crítica, sello y acoplamiento. |
| Bombas centrífugas | Propiedades automáticas/manuales del agua, succión/descarga, Hazen-Williams, pérdidas K y longitudes equivalentes, sistema cuadrático/exacto, tablas Q–H/eficiencia/NPSHr, ajuste cuadrático, operación, NPSH y márgenes, BEP automático/manual/diseño/operación, etapas, velocidad específica y afinidad por rpm/diámetro. |
| Ductos HVAC | Principal más hasta 40 tramos, conexión en árbol, TAG, caudales terminales, accesorios editables, Darcy-Colebrook/Swamee-Jain, aire por sitio/manual, AHU y filtros, ventilador PCHIP, bases de presión y eficiencia, balanceo, operación, variador, trayecto crítico y dimensionamiento por velocidad/Pa por metro con series editables. |

Las tres incluyen esquema/curvas Matplotlib, captura SI/US, metadatos del documento, casos JSON y PDF/Excel. Las salidas se muestran en SI. Los K adicionales de operación pueden capturarse en tramos comunes además de terminales; el balanceo automático de diseño se asigna solo a terminales.

## Archivos principales

- `calculadoras/memorias/agitadores.py`, `bombas.py`, `ductos.py`: motores independientes del GUI.
- `calculadoras/memorias/comun.py`: validación, interpolación y utilidades.
- `calculadoras/memorias/ventana.py`, `editores.py`: interfaz nativa y tablas.
- `calculadoras/memorias/reportes.py`: JSON, PDF y Excel.
- `calculadoras/memorias/datos/`: parámetros, opciones, series y casos iniciales convertidos desde los HTML.
- `recursos/RMR_transparente.png`: logo original transparente, utilizado por las memorias y sus PDF.
- `tests/test_memorias.py`, `test_memorias_interfaz.py`: comprobaciones del motor, archivos, integración y edición.
- `tests/datos/equivalencia_html.json`: 44 escenarios congelados de los motores HTML originales. No requiere navegador para probar la aplicación.

## Verificación numérica

Se comparan 14 escenarios de agitadores, 14 de bombas y 16 de HVAC con tolerancia relativa 1e-7 y absoluta 1e-9. Incluyen cambios de orientación, régimen, impulsor, material, frecuencia, sólidos, fibra, diámetro manual, sistema exacto, temperatura, altitud, BEP, afinidad, coeficientes manuales y topologías anidadas. También se comprueban fórmulas independientes, continuidad por nodo, cierre de presiones y balanceo, conversión de presión estática/total, potencia con eficiencia estática y dimensionamiento. Los ajustes de bomba utilizan mínimos cuadrados con QR/SVD de NumPy, mejor condicionado que las ecuaciones normales originales.

Las propiedades automáticas de bomba conservan el redondeo métrico del ejemplo HTML para reproducir sus resultados. La captura US convierte a SI antes de calcular y no cambia esa base numérica. El motor no modifica el diccionario de entrada. Los datos inválidos bloquean resultados y exportación. Las selecciones de motor que exceden las series se rechazan; una flecha sin diámetro suficiente en la serie conserva una advertencia explícita.

La equivalencia verifica la traducción del código; no extiende el rango físico de las correlaciones ni certifica los K o curvas de ejemplo. Se mantienen las hipótesis del original: agua para Hazen-Williams, agitador en voladizo con correlaciones de referencia, red HVAC sin mallas ni fugas, K constantes y sin cálculo automático de los coeficientes de tees según reparto. Las pérdidas de entrada/salida deben estar incluidas una sola vez en los accesorios.

## Uso desde Python sin ventanas

```python
from calculadoras.memorias import agitadores, bombas, ductos

estado = ductos.por_defecto()
resultado = ductos.calcular(estado)
print(resultado["design"]["dPreq"], resultado["op"]["Q"])

estado = bombas.por_defecto()
estado["inputs"]["qd"] = 100 / 3600  # m³/s internos
resultado = bombas.calcular(estado)
print(resultado["TDH"], resultado["np"]["a"])
```

No se sustituyen los identificadores `bomba` y `ductos` de la biblioteca anterior: son cálculos distintos. Los nuevos identificadores son `memoria_agitadores`, `memoria_bombas`, `memoria_hvac`. La contraseña, la configuración del sitio y los casos de las calculadoras anteriores se conservan.
