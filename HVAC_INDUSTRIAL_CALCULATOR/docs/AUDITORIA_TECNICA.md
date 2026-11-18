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
| Ventiladores | NUEVA | VALIDADA BAJO CONDICIONES DOCUMENTADAS (curvas reales: requieren datos certificados) |
| Potencia | CORREGIDA | VALIDADA BAJO CONDICIONES DOCUMENTADAS |

## 5. Pendientes que requieren documentos del usuario

- Edición vigente del ACGIH Industrial Ventilation Manual: confirmar velocidades de transporte y captura, Ce, K de
  entrada de ramal y umbrales de equilibrado.
- ASHRAE Duct Fitting Database o SMACNA: coeficientes de tees, codos segmentados y transiciones.
- Curvas certificadas de los ventiladores candidatos (con potencia y rango recomendado).
- Pérdidas del colector/filtro del fabricante (limpio y de mantenimiento).
- Fuera del alcance actual: redes de inyección divergentes y redes con varios ventiladores.
