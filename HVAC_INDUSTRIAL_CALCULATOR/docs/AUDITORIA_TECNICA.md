# Auditoría técnica del documento base y de la especificación

Documento auditado: *Arquitectura_Calculadora_Ventilacion_Industrial.pdf* (11 páginas) y especificación del proyecto
(incluido el módulo de criterio de ingeniería).

Clasificación de cada hallazgo: **EM** error matemático · **EP** error de programación/pseudocódigo · **EF** error de
interpretación física · **EU** error de unidades · **EN** normativo · **LM** limitación del método · **HN** hipótesis no
documentada.

## 1. Hallazgos y correcciones

| # | Hallazgo en el documento | Tipo | Consecuencia | Corrección implementada |
|---|---|---|---|---|
| 1 | El PDF salta de "Alcance" a la sección 4: faltan las secciones 1–3 (ecuaciones de caudal, campanas, balance de contaminantes) | HN | Sin base para los módulos de captura y dilución | Ecuaciones tomadas de la especificación y de ACGIH/ASHRAE con fuente y estado de verificación (`core/airflow.py`, `core/hood_design.py`) |
| 2 | `potencia_aire = Q·presion.total` usa el Q del método de caudal, mientras cada tramo usa `ducto.caudal` | EP/EF | En redes, el ventilador mueve la suma corregida por balance, no el Q de diseño | Potencia con el caudal resuelto en la entrada del ventilador (ṁ/ρ) en el punto de operación |
| 3 | `calcular_accesorios(ducto.accesorios, rho)` no usa velocidad ni sección de referencia | EF | K sin velocidad de referencia carece de significado | Cada accesorio con área de referencia: ΔP = K·ρ·(Q/A_ref)²/2 (`core/fittings.py`) |
| 4 | Colebrook sin verificar régimen | LM | Valores inválidos en laminar/transición | Laminar 64/Re; transición 2300–4000 con valor conservador y alerta (`core/friction.py`) |
| 5 | Sin pérdida de entrada de campana, aceleración (1 VP) ni pérdida de descarga | EF | Subestimación de 20–40 % de la presión en extracción localizada | he = Fh·VPd (Ce de ACGIH), SPh = he + VPd, ranura + pleno, descarga K = 1 |
| 6 | `potencia_eje = P_aire/η_vent` llamada "potencia al eje" | EF | Confusión entre eje del ventilador y eje del motor | Cadena explícita: aire → ventilador → eje del motor (η_transmisión) → eléctrica (η_motor·η_variador) |
| 7 | No se indica si η es total o estática | EF | Error de 10–30 % al mezclar bases | Presión y eficiencia siempre en la misma base; FSP con η_s o FTP con η_t |
| 8 | Altitud y presión, y densidad "opcional", sin verificación de consistencia | HN | Densidad incoherente con T, p, HR | Densidad siempre calculada; verificación presión–altitud y densidad declarada con alertas |
| 9 | No distingue caudal real y estándar ni la densidad de referencia de las curvas | EF/EU | A 2 240 m la densidad es 25 % menor: presión y potencia de catálogo sobrestimadas | Caudal real; curvas corregidas P ∝ ρ, W ∝ ρ; velocidad mínima de transporte corregida V/√df (ACGIH 31.ª ed., ec. 5.1) |
| 10 | Implícitamente VP = (V/4005)² en IP | EU | Solo válida a 0.075 lb/ft³ | VP = ρV²/2 en SI y conversión; la forma 4005 solo en pruebas |
| 11 | "Ramales paralelos entre los mismos nodos" | EF | Las campanas no comparten nodo interno: comparten la atmósfera | Modelo de árbol con atmósfera como referencia común; balance de presión total; dos modos (diseño y operación) |
| 12 | Leyes de ventiladores solo con N | LM | No permite cambio de tamaño ni de densidad | Q ∝ N·D³, P ∝ ρ·N²·D², W ∝ ρ·N³·D⁵ con advertencias de semejanza |
| 13 | `Q = Vc·A` presentada como ecuación de captura | EF | Solo vale para cabinas/envolventes (velocidad de cara) | Ecuaciones de DallaValle por geometría con validez X ≤ 1.5·D y W/L ≥ 0.2 |
| 14 | Niveles de alerta inconsistentes entre PDF (4), especificación (4) y módulo de criterio (5) | HN | Ambigüedad en la clasificación | 5 niveles + CORRECTO con tabla de equivalencia (`validation/alerts.py`) |
| 15 | Constante imperial 6356 sin indicar la temperatura del agua de la pulgada | EU | 0.1 % de diferencia con 248.84 Pa (60 °F) | Cálculo en SI; diferencia documentada y probada |
| 16 | Archivo `validation/unit_tests.py` duplicaría `tests/` | EP | Duplicidad | Pruebas solo en `tests/` |
| 17 | Filtro con pérdida fija | LM | No refleja ensuciamiento ni sobrecarga con filtro limpio | Modelo de filtro limpio/saturado; curva del sistema en ambos estados; verificación de sobrecarga del motor |

## 2. Decisiones de diseño con criterio

- **Balance en nodos**: se usa la presión total con las pérdidas de unión asignadas a los tramos que llegan (convención
  ACGIH de pérdida de entrada de ramal o convención ASHRAE con Cb/Cs). Así la corrección por "presión de velocidad
  resultante" de ACGIH queda incluida: SP = TP − VP en cada sección.
- **Equilibrado por diseño**: el caudal corregido se resuelve de forma exacta (bisección sobre el subárbol) y se
  compara con la aproximación Q·√r. Ambas coinciden sin fricción (comprobado en las pruebas).
- **Umbrales sin norma explícita**: el desbalance aceptable, la zona alrededor del BEP, el margen a la zona inestable y
  la velocidad máxima son **criterios configurables** marcados como hipótesis. Nunca generan alertas CRÍTICAS.
- **Datos protegidos**: tablas de ACGIH, ASHRAE y SMACNA solo cuando son de amplia difusión (velocidades de transporte
  y captura, Ce de entradas, K de entrada de ramal), siempre con la marca "verificar en edición vigente". Todo lo
  demás (tees, codos segmentados, rejillas, compuertas, equipos) es dato del usuario.

## 3. Hallazgos durante la validación (corregidos)

| Hallazgo | Corrección |
|---|---|
| El bulbo húmedo usaba solo la ecuación sobre agua (ASHRAE ec. 35); bajo 0 °C error de 0.4 K | Se añadió la ecuación sobre hielo (ASHRAE ec. 37) |
| La precisión de Sutherland estaba sobrestimada en la documentación | Medida contra CoolProp: ≤ 0.8 % hasta 100 °C; 1.3 % a 200 °C; 2.4 % a 400 °C; efecto < 0.5 % en f |
| SP en la boca de la chimenea calculada como −VP | La pérdida de descarga ocurre fuera del ducto: en la salida SP = 0 y TP = VP |
| Supuesto erróneo: "ductos más grandes ⇒ menor consumo" | Con rpm fijas el ventilador mueve más aire y consume más; con rpm ajustadas, el balanceo exige más caudal en el principal. El comparador lo refleja |

## 3 bis. Hallazgos de la revisión del PR (v1.0.1, corregidos)

Revisión del commit 9769054: las 113 pruebas pasaban, pero cuatro comprobaciones adicionales reprodujeron errores.
Los cuatro se reprodujeron de forma independiente antes de corregirlos.

| # | Tipo | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|
| 1 | Error de interpretación física / validación | La curva aceptaba potencias absorbidas menores que la potencia al aire. Con las potencias del ejemplo a la mitad se obtenía η = 159 %, motor de 4 kW y "aceptable con observaciones" | Motor subdimensionado sin ninguna alerta | `FanCurve.validate()` exige η_t = Q·FTP/W < 1 en cada punto y η declarada en [0, 1). `power_chain` vuelve a comprobar η < 1 en el punto de operación (bases total y estática) y bloquea la selección. Si la curva seleccionada es inválida no se sustituye por una eficiencia supuesta. Resultado: CRÍTICO, sin motor, dictamen "no recomendable". La eficiencia del usuario debe estar en (0, 1). Nueva alerta MEDIO si la η declarada difiere más de 5 % de Q·P/W |
| 2 | Omisión de método | El transporte mínimo solo se verificaba con los caudales de diseño. A 2110 rpm, R1 y R4 operan a 20.54 y 20.50 m/s, por debajo del mínimo de 20.59 m/s, sin alerta, y la alternativa era elegible | Riesgo de sedimentación no detectado | `check_transport_operation` verifica la red de operación real del ventilador seleccionado con el mismo criterio (clase del tramo, V_min corregida por densidad), sin duplicar los tramos ya señalados en diseño. El dictamen y el comparador lo incorporan; el comparador reporta V mín/máx de operación con su base |
| 3 | Error de programación | El intervalo de muestreo de la curva del sistema se calculaba con el dominio de catálogo, antes de aplicar las rpm o el diámetro. A 2400 rpm se reportaba "sin intersección" aunque el solucionador converge a 0.350 m³/s | Falso CRÍTICO; selección de ventilador rechazada sin motivo | Las curvas se ajustan (Q ∝ N·D³) antes de muestrear, y el intervalo cubre el dominio ajustado de cada ventilador |
| 4 | Error de programación (trazabilidad) | La exportación combinaba el proyecto actual con el último resultado. Con el recálculo automático desactivado, una exportación a 35 °C usaba resultados de 25 °C | Memoria de cálculo incoherente | Cada resultado guarda una huella SHA-256 de sus entradas (proyecto, configuración y base de datos; se excluye la marca de guardado). `generate_pdf` y `export_excel` rechazan resultados de otras entradas (`StaleResultsError`). La interfaz recalcula de forma síncrona antes de exportar PDF, Excel o PNG, y vuelve a ejecutar el comparador si cambiaron las alternativas. Un cálculo en segundo plano más antiguo ya no sobrescribe uno más reciente |

### Segunda revisión (regresión corregida)

La revisión del 19 de noviembre confirmó los cuatro puntos anteriores y detectó una regresión introducida por la
corrección del punto 1.

| # | Tipo | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|
| 5 | Error de interpretación física (regresión) | La validación exigía η > 0 en todo punto con caudal positivo. En una curva en **presión estática** el extremo de descarga libre tiene FSP = 0 y, por definición, η_s = Q·FSP/W = 0, con η_t > 0 gracias a la presión dinámica de salida. Una curva así quedaba rechazada por completo y se bloqueaba la selección del motor | Curvas de catálogo válidas se declaraban incoherentes; falso CRÍTICO y pérdida de la selección de motor | La eficiencia se interpreta en la base de presión de la curva: η = 0 se admite cuando el numerador Q·P es nulo, es decir a caudal nulo o a presión nula de la curva. Se mantiene el rechazo de η = 0 con caudal y presión positivos (exigiría potencia absorbida infinita), de η < 0 y de η ≥ 100 % |

El criterio queda así, idéntico en base total y estática, con P la presión de la curva en su propia base:

- η debe estar en [0, 1).
- η = 0 es válida si y solo si Q = 0 o P = 0.
- La comprobación de coherencia η_t = Q·FTP/W < 1 frente a la potencia absorbida no cambia.

Cambios de interfaz, documentados por separado de los de cálculo:

- La memoria y el Excel muestran el motivo cuando la selección de motor está bloqueada.
- El comparador tiene una columna "Base de V" (operación real o diseño).
- El campo de eficiencia del ventilador se limita a 99 %.
- Se corrigió la doble viñeta en las conclusiones del comparador del PDF.

## 4. Estado de las herramientas (formato del proyecto)

| Módulo | Estado de auditoría | Estado de validación |
|---|---|---|
| Unidades | CORREGIDA | VALIDADA BAJO CONDICIONES DOCUMENTADAS |
| Propiedades del aire | CORREGIDA | VALIDADA BAJO CONDICIONES DOCUMENTADAS (−100…200 °C; gas ideal) |
| Caudales (ACH, dilución, térmico, 62.1) | CORREGIDA | VALIDADA BAJO CONDICIONES DOCUMENTADAS |
| Campanas | CORREGIDA | VALIDADA (ecuaciones) — coeficientes ACGIH: VALIDACIÓN PENDIENTE contra la edición vigente |
| Ductos y fricción | CORREGIDA | VALIDADA BAJO CONDICIONES DOCUMENTADAS |
| Accesorios | CORREGIDA | Fórmulas: VALIDADA; K tabulados: VALIDACIÓN PENDIENTE (fuente marcada) |
| Red ramificada | NUEVA | VALIDADA BAJO CONDICIONES DOCUMENTADAS (árbol de extracción, un ventilador) |
| Ventiladores | CORREGIDA (v1.0.1: intervalo con curva ajustada; coherencia Q·P·W según la base de presión) | VALIDADA BAJO CONDICIONES DOCUMENTADAS (curvas reales: requieren datos certificados) |
| Potencia | CORREGIDA (v1.0.1: bloqueo con η ≥ 100 %) | VALIDADA BAJO CONDICIONES DOCUMENTADAS |
| Transporte en operación real | NUEVA (v1.0.1) | VALIDADA BAJO CONDICIONES DOCUMENTADAS (ventilador seleccionado, filtro en estado de diseño) |
| Exportación (coherencia entradas–resultados) | CORREGIDA (v1.0.1) | VALIDADA (prueba de interfaz con recálculo automático desactivado) |

## 5. Pendientes que requieren documentos del usuario

- Edición vigente del ACGIH Industrial Ventilation Manual: confirmar velocidades de transporte y captura, Ce, K de
  entrada de ramal y umbrales de equilibrado.
- ASHRAE Duct Fitting Database o SMACNA: coeficientes de tees, codos segmentados y transiciones.
- Curvas certificadas de los ventiladores candidatos (con potencia y rango recomendado).
- Pérdidas del colector/filtro del fabricante (limpio y de mantenimiento).
- Fuera del alcance actual: redes de inyección divergentes y redes con varios ventiladores.
