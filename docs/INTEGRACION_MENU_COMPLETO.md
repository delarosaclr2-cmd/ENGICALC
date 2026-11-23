# Integración de todas las calculadoras al menú

Rama de trabajo: `feature/robert/integrar-calculadoras-menu`.

## Uso

Ejecute `INICIAR.bat`, busque por nombre o seleccione una herramienta y pulse
**Abrir calculadora**. El doble clic también abre la selección. Una herramienta
Tk ya abierta se trae al frente; al cerrarla el menú sigue disponible. HVAC
industrial usa su propio proceso Qt y el menú evita abrir otra copia mientras
la primera siga ejecutándose.

En PowerShell, `py menu_principal.py --lista` muestra el catálogo. Use
`py menu_principal.py --calculadora ID` con uno de los identificadores siguientes.

## Inventario: 25 herramientas

| Identificador | Herramienta | Integración |
|---|---|---|
| `banda` | Banda transportadora | Ya disponible |
| `elevador` | Elevador de cangilones | Ya disponible |
| `helicoidal` | Transportador helicoidal | Ya disponible |
| `aerodeslizador` | Aerodeslizador (deslizador de polvo) | Ya disponible |
| `neumatico` | Transportador neumático | Ya disponible |
| `tolva` | Tolva de dosificación | Ya disponible |
| `silo` | Silo metálico (predimensionamiento) | Ya disponible |
| `ductos` | Ductos de aire con polvo | Ya disponible |
| `colector` | Colector de polvo | Ya disponible |
| `soplador` | Soplador | Ya disponible |
| `bomba` | Bomba centrífuga | Ya disponible |
| `vacio` | Bomba de vacío | Ya disponible |
| `torre` | Torre de enfriamiento | Ya disponible |
| `secador` | Secador rotatorio directo | Ya disponible |
| `viga` | Viga en voladizo o simplemente apoyada | Ya disponible |
| `memoria_agitadores` | Agitadores · memoria completa | Agregada: memoria completa |
| `memoria_bombas` | Bombas centrífugas · memoria completa | Agregada: memoria completa |
| `memoria_hvac` | Ductos HVAC · memoria completa | Agregada: memoria completa |
| `linea_agua` | Líneas de agua | Agregada: aplicación |
| `linea_vapor` | Líneas de vapor | Agregada: aplicación |
| `linea_aceite` | Líneas de aceite | Agregada: aplicación |
| `linea_gas` | Líneas de gas y aire comprimido | Agregada: aplicación |
| `gas_combustible` | Gas combustible | Agregada: aplicación |
| `tanque_pulmon` | Tanque pulmón de aire comprimido | Agregada: aplicación |
| `hvac_industrial` | HVAC industrial · aplicación completa | Agregada: aplicación |

## Origen y alcance

- Base del trabajo: `8386bd2b90c3bd9fa25886bf674d48ae7327c18d` de ENGICALC.
- Las tres memorias ya estaban en `calculadoras/memorias/`; se conecta su acceso
  al menú, buscador, lista por comando y apertura de casos `RMR-memoria`.
- HVAC industrial ya estaba en `HVAC_INDUSTRIAL_CALCULATOR/`. Se lanza su
  `main.py` con rutas absolutas, desde su propia carpeta y con su entorno local
  `.venv` cuando está instalado. Se inicia directamente en un único proceso;
  los errores del propio arranque se recogen sin bloquear el menú, sin instalar
  paquetes ni cerrar la sesión principal.
- Por instrucción del usuario se incorporan seis directorios del PR #4:
  `linea_agua`, `linea_vapor`, `linea_aceite`, `linea_gas`, `gas_combustible` y
  `tanque_pulmon`, tomados del commit
  `546d3bb9b1e5b4e552f7534dc972e9005d2443e1` de
  `feature/presion-velocidades-v1.1.0`. Son 229 archivos, incluidos casos,
  recursos, instrucciones de ejecución independiente y pruebas de origen.
  No se fusionó la rama ni se modificaron sus ecuaciones o pruebas.
- El registro de las 15 calculadoras básicas conserva su API y sus motores.
  El catálogo del menú reúne los tres tipos de herramienta sin mezclarlos.
- El rediseño gráfico queda fuera de este cambio. Las aplicaciones conservan
  sus interfaces y formatos propios. Los casos de las seis aplicaciones se
  abren desde su ventana; los proyectos HVAC, desde HVAC industrial.
- Las memorias y las aplicaciones conservan sus metadatos propios; no se
  incorporan al historial ni reciben automáticamente el proyecto global.

## Observaciones pendientes del PR #4

Estas seis aplicaciones se muestran con estado **Revisión pendiente**. Esta
integración no equivale a aprobar el cálculo ni a resolver las observaciones:

1. En el barrido de diámetros de vapor se conservan los K de accesorios del NPS
   original. En `ESCENARIO_principal_12in_150m.json`, a 53,265.24 kg/h y NPS 12,
   la fila de 8 pulgadas indica CUMPLE; al seleccionar NPS 8 se obtienen
   51.02 m/s frente al máximo de 50.9 m/s y NO CUMPLE.
2. En gas, el caudal máximo mostrado se redondea a 3,026.15 Nm³/h para el caso
   L1 con límite de 15 m/s. Al volver a capturarlo, un pequeño exceso de
   redondeo produce NO CUMPLE. Debe verificarse el valor mostrado, además del
   resultado interno del solucionador.

Las correcciones futuras deben conservar la correspondencia con el PR de origen.
Los documentos históricos de auditoría y resultados no se modifican.

## Verificación

- `python -m pytest -q`: suite principal, incluido catálogo, las tres memorias,
  seis aperturas nativas, ciclo de cierre, casos guardados, comandos y lanzador.
- `tests/test_menu_aplicaciones.py`: inventario completo, rutas, intérprete,
  ausencia de dependencias, proceso externo y prevención de duplicados.
- HVAC industrial mantiene su suite independiente. Sus comprobaciones de GUI
  se ejecutan en una copia temporal para conservar las evidencias históricas.

### Resultados observados el 23 de noviembre de 2026

- Suite principal: **420 pruebas aprobadas**, sin omisiones, con
  `python -m pytest -q`.
- HVAC industrial: **4 pruebas aprobadas** de `tests/test_reports_gui.py` en una
  copia temporal. Se registraron 96 avisos de obsolescencia de Matplotlib/Qt,
  sin fallos de pruebas.
- Apertura real mediante el lanzador, con las dependencias del entorno temporal
  de revisión: ventana del banco de pruebas, **12 páginas**, resultado calculado
  y diccionario de errores vacío. La prueba cerró esa ventana al terminar.
- Se compararon mediante SHA-256 los **229 archivos** incorporados del PR #4
  contra la carpeta de origen: todos coinciden.
- `menu_principal.py --lista` muestra los **25 identificadores** del inventario.

La prueba de HVAC utilizó un entorno temporal ya preparado; en una instalación
nueva debe ejecutarse su instalador para disponer de PySide6 y SciPy. Esta
verificación de integración no constituye validación de ingeniería de un
proyecto ni resuelve las dos observaciones anteriores.

## Optimización del inicio de HVAC industrial

Se conserva su ventana independiente, por elección del usuario. El menú ejecuta
directamente `main.py` en un único proceso, usando el entorno local de HVAC.
Se eliminó el proceso previo que importaba PySide6, SciPy y las demás bibliotecas
para comprobarlas: HVAC volvía a importarlas al arrancar.

El menú recupera el control inmediatamente y consulta el proceso mediante sus
eventos normales. Si el arranque falla, recoge el error de un registro temporal
y muestra el aviso correspondiente, incluida la instrucción del instalador
cuando falta una dependencia. No se instalan paquetes al abrir. Al cerrar el
menú se cancela esa vigilancia y HVAC puede continuar abierto.

Medición automatizada en esta PC, con el mismo banco de pruebas y Qt en modo
de prueba; estos tiempos no son una garantía para otros equipos:

| Medida | Inicio anterior | Inicio directo |
|---|---:|---:|
| Espera del menú al hacer clic | 1.09 s | 0.009 s |
| Ventana construida y mostrada | 3.38 s | 2.28 s |
| Ejemplo calculado | 3.96 s | 2.90 s |

La comprobación real del inicio directo encontró las 12 páginas y ningún error
de cálculo. Pasaron las 20 pruebas específicas de integración, incluidos un
proceso con una dependencia ausente, su aviso asíncrono y la cancelación de
la vigilancia al cerrar el menú. Los motores de cálculo y la interfaz propia
de HVAC industrial conservan su código.

La suite principal completa terminó con **422 pruebas aprobadas**, sin
omisiones, mediante `python -m pytest -q`.
