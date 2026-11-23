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
- Por instrucción del usuario se incorporaron inicialmente seis directorios del PR #4:
  `linea_agua`, `linea_vapor`, `linea_aceite`, `linea_gas`, `gas_combustible` y
  `tanque_pulmon`, tomados del commit
  `546d3bb9b1e5b4e552f7534dc972e9005d2443e1` de
  `feature/presion-velocidades-v1.1.0`. Son 229 archivos, incluidos casos,
  recursos, instrucciones de ejecución independiente y pruebas de origen.
  La incorporación inicial se hizo por copia, sin modificar sus ecuaciones o pruebas.
  Después se actualizaron desde `main`, commit
  `477d6e4c43b527af6b246abd791c6d7cf4adeac7`, que fusionó el PR #4 con las
  correcciones revisadas del commit `7fb6228274b93aa1aacbb6bc5689662893566ab7`.
- El registro de las 15 calculadoras básicas conserva su API y sus motores.
  El catálogo del menú reúne los tres tipos de herramienta sin mezclarlos.
- El rediseño gráfico queda fuera de este cambio. Las aplicaciones conservan
  sus interfaces y formatos propios. Los casos de las seis aplicaciones se
  abren desde su ventana; los proyectos HVAC, desde HVAC industrial.
- Las memorias y las aplicaciones conservan sus metadatos propios; no se
  incorporan al historial ni reciben automáticamente el proyecto global.

## Correcciones del PR #4 integradas

El PR #4 fue revisado y fusionado en `main`. Las seis aplicaciones muestran
**Revisión de código aprobada**; ese estado no constituye aprobación de
ingeniería de un proyecto. Las dos observaciones anteriores quedaron atendidas:

1. El barrido de vapor recalcula los K tabulados para cada NPS y conserva los
   K capturados explícitamente. En `ESCENARIO_principal_12in_150m.json`, a
   53,265.24 kg/h y NPS 12, la fila de 8 pulgadas ahora indica 51.020 m/s y
   NO CUMPLE, igual que el cálculo completo al seleccionar NPS 8.
2. La capacidad de gas se redondea hacia abajo y el valor mostrado se comprueba
   con el modelo del dictamen. El caso L1 con límite de 15 m/s anuncia
   3,026.14 Nm³/h y cumple al reintroducirlo; 3,026.15 sigue siendo NO CUMPLE.

Las seis carpetas conservan la correspondencia con la versión fusionada del PR.
Los documentos históricos de auditoría y resultados no se modifican.

## Verificación

- `python -m pytest -q`: suite principal, incluido catálogo, las tres memorias,
  seis aperturas nativas, ciclo de cierre, casos guardados, comandos y lanzador.
- `tests/test_menu_aplicaciones.py`: inventario completo, rutas, intérprete,
  ausencia de dependencias, proceso externo y prevención de duplicados.
- HVAC industrial mantiene su suite independiente. Sus comprobaciones de GUI
  se ejecutan en una copia temporal para conservar las evidencias históricas.

### Resultados observados el 23 de noviembre de 2026

Los resultados de esta sección corresponden a la integración inicial, anterior
a la actualización con `main`; los de la comprobación combinada se añaden al final.

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

## Comprobación combinada después de fusionar el PR #4

El 23 de noviembre de 2026 se comprobó la actualización de la rama del menú
con `main` (`477d6e4`), que incorpora la versión revisada `7fb6228`.
Los 25 conflictos quedaron resueltos conservando las calculadoras de `main`.
Se verificó que los **229 archivos** de las seis carpetas coinciden con esa
versión, tanto en el área preparada para commit como en los archivos de trabajo.
Los cambios específicos del menú quedan en nueve archivos respecto de `main`.

Se actualizaron las descripciones y el estado de las seis aplicaciones a
**Revisión de código aprobada**, retirando los avisos de los dos defectos ya
corregidos. Las limitaciones de ingeniería de cada proyecto se conservan.

Se añadieron dos regresiones en `tests/test_menu_aplicaciones.py` que abren
las ventanas desde el menú y comprueban las correcciones en esa misma sesión:

- Gas: la capacidad mostrada es 3,026.14 Nm³/h y al reintroducirla cumple.
- Vapor: para 53,265.24 kg/h y NPS 12, la fila del NPS 8 muestra 51.020 m/s
  y NO CUMPLE; al seleccionar ese NPS el dictamen completo también es NO CUMPLE.

Las dos comprobaciones específicas pasaron antes de ejecutar la suite completa.
La ejecución combinada de `python -m pytest -q` terminó con **424 pruebas
aprobadas**, sin omisiones. No quedaron archivos con conflictos sin resolver.
La revisión dejó el commit de la fusión y su publicación a cargo del usuario.
