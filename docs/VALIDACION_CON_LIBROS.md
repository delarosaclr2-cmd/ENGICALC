# Validación con ejercicios de libros de texto — versión 2.1.1 (13/11/2026)

## 1. Objetivo y método

Solicitud del usuario: probar las calculadoras con ejercicios de libros de editoriales usadas en la enseñanza de la
ingeniería y la mecánica, para verificar que dan los resultados correctos.

Método aplicado a cada ejercicio:

1. Se toma un ejemplo o problema **resuelto y publicado** (la respuesta aparece en el libro, en su manual de
   soluciones o en la solución publicada del capítulo). No se usan respuestas de foros ni de terceros.
2. Los datos del enunciado se capturan en los campos de la calculadora tal como lo haría un usuario. Cuando el
   libro da un dato en otra forma (p. ej. viscosidad dinámica y densidad, humedad absoluta en lugar de
   humedad relativa), la conversión se indica en el caso.
3. Se compara cada resultado con el publicado y se calcula la diferencia relativa. Se acepta como
   **«Coincide»** una diferencia dentro de la precisión con la que el libro imprime el resultado (tres
   cifras significativas, ±0.5 %) o, cuando el libro lee propiedades en la carta psicrométrica, dentro de ±1–2 %.
4. La comprobación queda automatizada:
   - `tests/casos_libros.py` — datos de cada ejercicio (fuente única).
   - `tests/test_libros.py` — verifica el motor de cálculo contra la respuesta publicada.
   - `tests/test_interfaz.py::test_casos_de_libros_se_abren_y_dan_el_resultado_publicado` — abre cada caso
     **en la ventana del programa** (como lo haría el usuario) y verifica la misma respuesta.
   - `herramientas/generar_casos_libros.py` — genera los casos `docs/ejemplos/libros/*.json` y la tabla de la
     sección 3.
5. Los enunciados se resumen con sus datos; no se reproducen textualmente.

**Para repetirlo en el programa:** menú principal → Archivo → «Abrir caso guardado…» → carpeta
`docs/ejemplos/libros` → elija el caso. La calculadora se abre con los datos del ejercicio, calcula y muestra
el resultado; cada archivo incluye la fuente y el planteamiento.

## 2. Resumen

| Calculadora | Libro (editorial) | Ejercicio | Resultado |
|---|---|---|---|
| Torre de enfriamiento | Çengel y Boles, *Termodinámica* (McGraw-Hill) | Problema 14-112 (respuestas impresas en el enunciado) | Coincide: 44.93 vs 44.9 m³/s; 1.165 vs 1.16 kg/s |
| Torre de enfriamiento | Çengel y Boles, *Termodinámica*, 7.ª ed. — manual de soluciones (McGraw-Hill) | Problema 14-115 | Coincide: 4.218 vs 4.2 kg/s de aire; 0.0502 vs 0.050 kg/s |
| Bomba centrífuga (pérdidas) | Çengel y Cimbala, *Mecánica de fluidos* (McGraw-Hill) | Ejemplo 8-3 | Coincide: f 0.0174; hL 27.26 vs 27.3 ft; 460.9 vs 461 W |
| Ductos | Çengel y Cimbala, *Mecánica de fluidos* (McGraw-Hill) | Ejemplo 8-4 | Coincide: D 0.2672 vs 0.267 m; hL 19.99 vs 20 m |
| Bomba de vacío (compresión) | Çengel y Boles, *Termodinámica* (McGraw-Hill), cap. 7 | Trabajo de compresión de aire 100 kPa/300 K → 900 kPa | Coincide: 263.25 vs 263.2 y 189.21 vs 189.2 kJ/kg |
| Aerodeslizador (fluidización) | Rhodes, *Introduction to Particle Technology*, 2.ª ed. (Wiley) | Ejercicio 7.9 (a) | Coincide: Umf 3.81 vs 3.8 mm/s |
| Viga | *Strength of Materials* (libro abierto, Engineering Mechanics OER) | Ejemplo 11.1 | Coincide: 37.20 vs 37.2 mm |
| Secador rotatorio | Geankoplis, *Transport Processes and Unit Operations*, 3.ª ed. (Prentice Hall) | Ejemplo 9.10-2 | Coincide: G 1 170 vs 1 171 kg/h; H 0.02473 vs 0.0247 |

**24 de 24 comprobaciones coinciden** con la respuesta publicada; la mayor diferencia es 0.53 % (número de
Reynolds del Ejemplo 8-4, porque la calculadora calcula la viscosidad del aire a 35 °C con su correlación en
lugar de tomar el valor del libro).

## 3. Resultados detallados (generados por `herramientas/generar_casos_libros.py`)

| Caso | Magnitud | Publicado | Calculadora | Diferencia | Veredicto |
|---|---|---|---|---|---|
| `torre_cengel_boles_P14_112` | Caudal de aire a la entrada [m³/s] | 44.9 | 44.93 | +0.06 % | Coincide |
| `torre_cengel_boles_P14_112` | Agua de reposición [kg/s] | 1.16 | 1.165 | +0.45 % | Coincide |
| `torre_cengel_boles_P14_115` | Humedad absoluta del aire de entrada ω₁ [kg/kg] | 0.00211 | 0.002101 | −0.44 % | Coincide |
| `torre_cengel_boles_P14_115` | Flujo de aire seco [kg/s] (dato del enunciado) | 4.2 | 4.218 | +0.43 % | Coincide |
| `torre_cengel_boles_P14_115` | Agua de reposición [kg/s] | 0.05 | 0.05019 | +0.39 % | Coincide |
| `bomba_cengel_cimbala_ej_8_3` | Velocidad [ft/s] | 9.17 | 9.167 | −0.03 % | Coincide |
| `bomba_cengel_cimbala_ej_8_3` | Número de Reynolds | 126 400 | 126 432 | +0.03 % | Coincide |
| `bomba_cengel_cimbala_ej_8_3` | Factor de fricción de Darcy | 0.0174 | 0.0174 | −0.02 % | Coincide |
| `bomba_cengel_cimbala_ej_8_3` | Pérdida de carga hL [ft] | 27.3 | 27.26 | −0.13 % | Coincide |
| `bomba_cengel_cimbala_ej_8_3` | Potencia de bombeo [W] | 461 | 460.9 | −0.03 % | Coincide |
| `ductos_cengel_cimbala_ej_8_4` | Diámetro [m] | 0.267 | 0.2672 | +0.09 % | Coincide |
| `ductos_cengel_cimbala_ej_8_4` | Número de Reynolds | 100 800 | 101 334 | +0.53 % | Coincide |
| `ductos_cengel_cimbala_ej_8_4` | Factor de fricción de Darcy | 0.018 | 0.01794 | −0.33 % | Coincide |
| `ductos_cengel_cimbala_ej_8_4` | Pérdida de carga hL [m] | 20 | 19.99 | −0.04 % | Coincide |
| `vacio_cengel_boles_compresion` | Trabajo isentrópico, k = 1.4 [kJ/kg] | 263.2 | 263.3 | +0.02 % | Coincide |
| `vacio_cengel_boles_compresion` | Trabajo isotérmico [kJ/kg] | 189.2 | 189.2 | +0.00 % | Coincide |
| `aerodeslizador_rhodes_ej_7_9` | Velocidad mínima de fluidización Umf [mm/s] | 3.8 | 3.811 | +0.29 % | Coincide |
| `aerodeslizador_rhodes_ej_7_9` | ΔP de 60 mm de lecho por equilibrio de fuerzas [Pa] (Rhodes: 9 705.4 Pa/m) | 582.3 | 582.1 | −0.03 % | Coincide |
| `viga_strength_of_materials_ej_11_1` | Deflexión al centro [mm] | 37.2 | 37.2 | +0.01 % | Coincide |
| `viga_strength_of_materials_ej_11_1` | Momento máximo wL²/8 [kN·m] (estática) | 250 | 250 | +0.00 % | Coincide |
| `viga_strength_of_materials_ej_11_1` | Reacción en cada apoyo [kN] (estática) | 100 | 100 | +0.00 % | Coincide |
| `secador_geankoplis_ej_9_10_2` | Agua evaporada [kg/h] (balance de masa) | 17.24 | 17.24 | +0.00 % | Coincide |
| `secador_geankoplis_ej_9_10_2` | Flujo de aire seco G [kg/h] | 1 171 | 1 170 | −0.10 % | Coincide |
| `secador_geankoplis_ej_9_10_2` | Humedad del aire de salida H [kg/kg] | 0.0247 | 0.02473 | +0.14 % | Coincide |

## 4. Detalle por ejercicio

### 4.1 Torre de enfriamiento — Çengel y Boles, problema 14-112

- **Planteamiento:** 60 kg/s de agua de 40 a 26 °C; aire a 1 atm con 22 °C de bulbo seco y 16 °C de bulbo
  húmedo; sale a 34 °C y 90 % de humedad relativa. Se pide el caudal de aire de entrada y el agua de reposición.
- **Captura:** flujo 60 kg/s; 40 y 26 °C; cp 4.18; bulbo seco 22, bulbo húmedo 16; aire de salida 34 °C y
  HR 90 %; L/G 0; altitud 0.
- **Resultado:** 44.93 m³/s y 1.165 kg/s (publicado 44.9 m³/s y 1.16 kg/s, leídos en la carta psicrométrica).
- **Observación:** con la versión 2.1.0 este problema no podía capturarse tal cual, porque la torre suponía
  aire de salida saturado y aire de entrada saturado al bulbo húmedo. Con ese supuesto el resultado habría sido
  ≈ 38.3 m³/s y ≈ 1.04 kg/s (−15 % y −10 %). Por eso, en esta versión, la torre usa el balance exacto del libro
  (sección 5).

### 4.2 Torre de enfriamiento — Çengel y Boles, problema 14-115 (manual de soluciones)

- **Planteamiento:** 4 kg/s de agua a 32 °C; aire a 1 atm, 15 °C y 20 % HR, con 4.2 kg/s de aire seco; sale a
  20 °C con ω = 0.014 kg/kg. Se piden el agua de reposición y la temperatura del agua fría. Publicado: 0.050 kg/s
  y 23.4 °C.
- **Captura (problema inverso):** la calculadora calcula el flujo de aire a partir de las temperaturas del agua.
  Se captura el agua fría publicada (23.4 °C), el bulbo húmedo que corresponde a 15 °C y 20 % HR (5.95 °C) y la
  HR de salida que corresponde a ω = 0.014 a 20 °C (95.4 %). La calculadora debe devolver el flujo de aire del
  enunciado.
- **Resultado:** 4.218 kg/s de aire (dato del enunciado 4.2) y 0.0502 kg/s de reposición (publicado 0.050).

### 4.3 Bomba centrífuga — Çengel y Cimbala, Ejemplo 8-3

- **Planteamiento:** agua a 60 °F (ρ = 62.36 lbm/ft³, μ = 7.536 × 10⁻⁴ lbm/(ft·s)) con 0.2 ft³/s en un tubo
  horizontal de acero inoxidable de 2 in y 200 ft (ε = 0.000007 ft). Se piden la pérdida y la potencia.
- **Captura:** caudal 0.2 ft³/s = 89.77 gpm; diámetro 2 in; longitud 200 ft; rugosidad 0.000084 in;
  viscosidad cinemática μ/ρ = 1.1227 cSt; GE 1; sin accesorios, equipos ni elevación.
- **Resultado:** V = 9.167 ft/s, Re = 126 432, f = 0.0174 (Colebrook), hL = 27.26 ft y potencia hidráulica
  0.618 HP = 460.9 W (publicado 9.17 ft/s, 126 400, 0.0174, 27.3 ft, 461 W).

### 4.4 Ductos — Çengel y Cimbala, Ejemplo 8-4

- **Planteamiento:** aire a 1 atm y 35 °C (ρ = 1.145 kg/m³) con 0.35 m³/s en un ducto liso de 150 m; la pérdida
  no debe exceder 20 m. Se pide el diámetro.
- **Captura (problema inverso):** la calculadora dimensiona por velocidad; se captura la velocidad de la solución
  del libro (6.24 m/s), caudal 1 260 m³/h, densidad 1.145, 35 °C, rugosidad prácticamente nula (1 × 10⁻⁶ mm).
- **Resultado:** D = 0.2672 m, f = 0.01794 y hL = ΔP/(ρg) = 19.99 m (publicado 0.267 m y 20 m).

### 4.5 Bomba de vacío (compresión de gas) — Çengel y Boles, capítulo 7

- **Planteamiento:** aire comprimido de forma reversible de 100 kPa y 300 K a 900 kPa; trabajo por unidad de
  masa para compresión isentrópica (k = 1.4) e isotérmica.
- **Captura:** caudal de succión de 1 kg/s (v₁·3 600 = 3 100 m³/h) para que la potencia en kW sea el trabajo en
  kJ/kg; succión 100 kPa; descarga 900 kPa; 26.85 °C; eficiencia 1; k 1.4.
- **Resultado:** 263.25 kJ/kg isentrópico y 189.21 kJ/kg isotérmico (publicado 263.2 y 189.2 kJ/kg).

### 4.6 Aerodeslizador — Rhodes, Ejercicio 7.9 (a)

- **Planteamiento:** polvo de 60 µm y 1 800 kg/m³ fluidizado con aire (1.2 kg/m³; 1.84 × 10⁻⁵ Pa·s);
  porosidad a mínima fluidización 0.45; Umf por Ergun.
- **Captura:** la calculadora pide la densidad del lecho fluidizado, que en el equilibrio de fuerzas es
  (1 − ε)(ρp − ρf) = 989.3 kg/m³; partícula 60 µm; porosidad 0.45; aire 1.2 kg/m³ y 1.84 × 10⁻⁵ Pa·s.
- **Resultado:** Umf = 3.811 mm/s (publicado 3.8 × 10⁻³ m/s).
- **Alcance:** valida el cálculo de fluidización (Ergun y caída de presión del lecho). La capacidad de transporte
  sigue usando las velocidades de material del original (nivel O), que ningún libro docente permite validar.

### 4.7 Viga — *Strength of Materials* (OER), Ejemplo 11.1

- **Planteamiento:** viga simplemente apoyada de 10 m con carga uniforme de 20 kN/m; E = 200 GPa;
  I = 350 × 10⁶ mm⁴. Se pide la deflexión al centro.
- **Captura:** simplemente apoyada; L = 10 m; carga distribuida 20 000/9.80665 = 2 039.4 kg/m (el programa usa
  kg/m); material personalizado E = 200 GPa; sección personalizada con I = 35 000 cm⁴ (c y A solo afectan
  esfuerzos); norma «Ninguna».
- **Resultado:** 37.20 mm (publicado 37.2 mm); además M = 250 kN·m y reacciones de 100 kN (estática).

### 4.8 Secador rotatorio — Geankoplis, Ejemplo 9.10-2

- **Planteamiento:** secador continuo a contracorriente; 453.6 kg/h de sólido seco con humedad libre de 0.04 a
  0.002 kg/kg (base seca); cp del sólido 1.465 kJ/(kg·K); sólido de 26.7 a 62.8 °C; aire de 93.3 a 37.8 °C con
  H = 0.010 a la entrada; sin pérdidas. Se piden el flujo de aire y la humedad de salida.
- **Captura:** alimentación 453.6 × 1.04 = 471.7 kg/h en base seca (4 % → 0.2 %); temperaturas del enunciado;
  disposición **contracorriente** (nueva opción); pérdidas 0 %; aire ambiente 25 °C con la HR que da H = 0.010
  (50.6 %).
- **Resultado:** G = 1 170 kg aire seco/h y H = 0.02473 (publicado 1 171 kg/h y 0.0247).
- **Observación:** el libro hace el balance con entalpías referidas a 0 °C; la calculadora lo hace evaporando el
  agua al bulbo húmedo del aire (34.2 °C) con su calor latente y sobrecalentando el vapor hasta la salida. Ambos
  caminos son equivalentes y difieren 0.1 %. El caso no se puede capturar en flujo paralelo: el sólido saldría
  más caliente (62.8 °C) que el aire (37.8 °C), lo cual es físicamente imposible en esa disposición y el
  programa lo rechaza.

## 5. Ajustes hechos al programa por esta verificación (versión 2.1.1)

| Calculadora | Ajuste | Por qué |
|---|---|---|
| Torre | Balance de masa y energía completo (Çengel y Boles): estado del aire de entrada por bulbo seco y bulbo húmedo; aire de salida con temperatura **y humedad relativa** capturadas (100 % = saturado); el agua de reposición entra en el balance de energía. Nuevas salidas: ω de entrada y de salida, caudal de aire a la entrada y reposición en kg/s. | Los problemas del libro especifican la HR del aire de salida (90 %, 95 %); la versión 2.1.0 suponía saturación y daba 15 % menos aire en el P14-112. |
| Secador | Opción **contracorriente** además de flujo paralelo; los balances no cambian, solo ΔT_ml (y por lo tanto la longitud). Estado: **VALIDADA BAJO CONDICIONES DOCUMENTADAS** para balances de masa y energía, flujo de aire y humedad de salida. | El ejemplo de Geankoplis (y muchos secadores industriales) es a contracorriente. El diámetro, la longitud y Ua siguen siendo estimaciones preliminares (nivel E), y la potencia y las aletas del original siguen sin validar (nivel O). |

Ninguno de los ejercicios mostró un error en las ecuaciones ya corregidas en la Fase 2: las diferencias son de
redondeo o de lectura de tablas y cartas.

## 6. Calculadoras sin ejercicio de libro docente

Para estas herramientas no existe un ejercicio resuelto equivalente en los libros de texto generales; se validaron
(versión 2.1.0) con los ejemplos de los manuales y normas del método que usan:

| Calculadora | Validación vigente | Comentario |
|---|---|---|
| Helicoidal | Ejemplos resueltos de KWS (método CEMA) | Los libros de texto no tratan el método CEMA. |
| Banda | MEKA Handbook; tablas de IS 11592 e ISO 5048 | Ídem (CEMA / DIN 22101 / ISO 5048). |
| Elevador | Ejemplo de KWS | Ídem. |
| Colector | Tablas de la EPA (Air Pollution Control Cost Manual) | Ídem. |
| Soplador | Ejemplo de Atlas Copco y ruta independiente por entalpía | La compresión de gas también queda cubierta por el caso 4.5. |
| Silo | Janssen y Beverloo verificados por cálculo independiente | Predimensionamiento (decisión del usuario). |
| Tolva | Beverloo verificado contra la ecuación publicada | No se encontró un ejercicio resuelto numérico de un libro docente; sigue en VALIDACIÓN PENDIENTE. |
| Neumático | Colebrook y forma de Barth con Ks del usuario | Los libros (Rhodes, Holdich) usan otras correlaciones de sólidos, no comparables con Ks; sigue en VALIDACIÓN PENDIENTE. |
| Viga (AISC/NTC) | Ejemplos de diseño de AISC (F.1-1B, F.1-2B, F.1-3B, F.3B, G.1B) | Complementa el caso 4.7. |

## 7. Estado de validación después de la 2.1.1

- **VALIDADA BAJO CONDICIONES DOCUMENTADAS (12):** banda, elevador, helicoidal, silo (predimensionamiento),
  ductos, colector, soplador, bomba centrífuga, bomba de vacío, torre, **secador (balances)**, viga.
- **VALIDACIÓN PENDIENTE (3):** aerodeslizador (la fluidización ya coincide con Rhodes; falta la capacidad de
  transporte, que usa velocidades del original), transportador neumático y tolva de dosificación.

## 8. Fuentes de las respuestas publicadas

- Çengel y Cimbala, *Fluid Mechanics*, Ejemplos 8-3 y 8-4 (páginas del capítulo 8 reproducidas en Scribd y en
  las notas de clase de BYU ChE 374):
  <https://www.scribd.com/document/645341561/Chapter-8-24-pdf>,
  <https://www.scribd.com/document/736555622/Internal-Flow-Examples-2>,
  <https://ignite.byu.edu/che374/lectures/Lecture_19_notes.pdf>.
- Çengel y Boles, problema 14-112 con respuestas: <https://transtutors.com/questions/a-wet-cooling-tower-is-to-cool-60-kg-s-of-water-from-40-to-26-c-atmospheric-air--10260645.htm>.
- Çengel y Boles, 7.ª ed., manual de soluciones del cap. 14 (problema 14-115):
  <https://www.mhtlab.uwaterloo.ca/courses/me354/assignments/pdffiles/cengel/all14.pdf>.
- Rhodes, solución del Ejercicio 7.9: <https://www.scribd.com/document/901320485/Fluidised-bed-Example>.
- *Strength of Materials*, cap. 11, Ejemplo 11.1: <https://engineeringmechanicsoer.github.io/StrengthBook/Chapter%2011.html>.
- Geankoplis, Ejemplo 9.10-2 (Textbook Companion de FOSSEE):
  <https://tbc-python.fossee.in/convert-notebook/TRANSPORT_PROCESSES_AND_UNIT_OPERATIONS/GeankoplisChapter09.ipynb>.
- Çengel y Boles, trabajo de compresión de aire 100 kPa/300 K → 900 kPa (sección «Reversible steady-flow work»
  del cap. 7): los valores 263.2 y 189.2 kJ/kg corresponden a las expresiones cerradas del libro
  (w = kRT₁/(k − 1)·[(P₂/P₁)^((k−1)/k) − 1] y w = RT₁·ln(P₂/P₁)); el número del ejemplo varía según la edición.
