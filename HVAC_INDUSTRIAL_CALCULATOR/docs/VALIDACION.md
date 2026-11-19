# Validación matemática y prueba de integración

Ejecución: `python -m pytest` (140 pruebas, 204 comprobaciones numéricas registradas). El registro detallado de cada
comprobación (entrada, esperado, obtenido, error absoluto, error relativo, tolerancia, referencia y estado) está en
`tests/results/registro_pruebas.csv` y `tests/results/registro_pruebas.md`. Resultado de la última ejecución:
**140/140 pruebas aprobadas; 204/204 comprobaciones dentro de tolerancia** (v1.0.1).

Regla aplicada: los valores esperados provienen de referencias independientes del código y **nunca se ajustaron para
aprobar**. Las discrepancias se investigaron; la sección 3 documenta las causas.

## 1. Referencias independientes usadas

| Área | Referencia independiente | Tolerancia y justificación |
|---|---|---|
| Unidades | Factores exactos de definición (NIST SP 811) | 10⁻¹² (aritmética) |
| Presión de saturación | CoolProp IAPWS-95 (líquido) e IAPWS 2011 (sublimación del hielo) | 0.15 % (precisión de Hyland-Wexler) |
| Atmósfera estándar | Deducción desde hidrostática + gas ideal + gradiente lineal; tabla ASHRAE | 2·10⁻⁵ |
| Aire húmedo (W, ρ, h, rocío, bulbo húmedo) | CoolProp HAPropsSI (ASHRAE RP-1485) | 0.6 % en W y h (el programa omite el factor de realce, ≈0.4 %); 0.1 % en ρ |
| Viscosidad | CoolProp (Lemmon y Jacobsen) | Precisión documentada de Sutherland por rango; efecto sobre f < 0.5 % |
| Colebrook | Solución por bisección (algoritmo distinto) | 10⁻¹⁰ |
| Swamee-Jain, Haaland, Churchill | Contraste con Colebrook | 1.5–3 % (precisión declarada de cada correlación) |
| Tubo liso | Prandtl–Kármán | 1 % |
| Campanas, ACH, dilución, térmico, 62.1 | Aritmética explícita en la prueba; ejemplo IP de 1100 cfm | 10⁻¹² |
| Accesorios | Fórmulas de Borda-Carnot, Crane e Idelchik escritas en la prueba | 10⁻¹² |
| Punto de operación | Curvas analíticas: ventilador 2000 − 50Q², sistema 30Q² ⇒ Q = 5 | 0.2 % (interpolación PCHIP de puntos) |
| rpm requeridas | Solución cerrada P_k(Q) = 2000k² − 50Q² | 0.2 % |
| Red: reparto | Solución cerrada con resistencias puras: Q ∝ A/√K | 10⁻⁶ |
| Red: operación | **Segunda implementación**: formulación de nudos (presiones de nodo + bisección por tramo, fsolve) frente a la formulación por trayectorias del programa | 10⁻⁶ (ṁ ventilador), 10⁻⁵ (campanas) |
| Red: diseño ↔ operación | Ventilador que pasa por el punto de diseño con compuertas exactas ⇒ caudales de diseño | 10⁻⁵ |
| Caso industrial | Recalculo independiente de cada tramo del camino crítico con ecuaciones elementales | 10⁻⁹ |

## 2. Banco de pruebas industrial

`examples/nave_industrial_4_campanas.hvac.json` (generado por `examples/build_example.py`).

**Hipótesis**:
- Valle de México: 2 240 m, 25 °C, HR 50 %; presión de la atmósfera estándar.
- Ductos de acero galvanizado (ε = 0.09 mm), codos lisos R/D = 2 (Idelchik), entradas de ramal a 30° y 45° (ACGIH).
- Colector de mangas modelado como filtro lineal (n = 1): 600 Pa limpio y 1 500 Pa saturado a 2.3 m³/s (hipótesis
  del ejemplo).
- Curvas de ventilador **sintéticas**.

| Resultado | Valor |
|---|---|
| Densidad del aire | 0.8945 kg/m³ (74.5 % del estándar); CoolProp 0.8948 |
| Caudales requeridos C1–C4 | 0.671 / 0.390 / 0.750 / 0.380 m³/s |
| Balance | J1 r = 1.01 (aceptado); J2 r = 1.064 → caudal de R3 aumentado a 0.775 m³/s; J3 r = 1.009 (aceptado) |
| Camino crítico | R4 → M3 → M4 → D1 (campana gobernante H4) |
| Diseño | Q = 2.216 m³/s; FTP = 2 328 Pa; FSP = 2 242 Pa (fricción 486, locales 397, equipos 1 445 Pa) |
| Operación BI-560 a 2 200 rpm | Q = 2.248 m³/s; FTP = 2 369 Pa; η_t = 79.5 %; rpm requeridas para el diseño: 2 179 |
| Caudales en operación | H1 0.684, H2 0.395, H3 0.785, H4 0.384 m³/s (todas ≥ requerido) |
| Potencias | aire 5.33 kW; ventilador 6.70 kW; eje del motor 7.05 kW; eléctrica 7.69 kW; motor IEC 11 kW (carga 64 %) |
| Energía | 36 912 kWh/año; variador frente a compuerta: ahorro de 2 984 kWh/año con el perfil indicado |
| Dictamen | Diseño aceptable con observaciones (3 MEDIO, 1 BAJO) |

**Comparador** (4 alternativas):

| Alternativa | Resultado |
|---|---|
| A — Diseño base | Elegible, 90/100, **recomendada** |
| B — Principal un diámetro mayor | No elegible: velocidad de transporte insuficiente |
| C — Punta radial RT-500 | Elegible, 66/100: mayor consumo |
| D — Ventilador pequeño BI-450 | No elegible: déficit de caudal 15 % y transporte insuficiente en operación real, aunque es la de menor consumo |

El comparador no elige la alternativa más económica.

## 3. Discrepancias encontradas y su causa

1. **pws a −20 °C (0.44 %)**: la referencia inicial (HAPropsSI con HR = 1) incluye el factor de realce y no es pws
   pura. Se sustituyó por la ecuación IAPWS de sublimación. Concordancia: 0.01 %.
2. **Bulbo húmedo bajo 0 °C (0.4 K)**: error real del programa. Faltaba la ecuación sobre hielo; se corrigió con
   ASHRAE ec. 37.
3. **Viscosidad a 200–400 °C (1.3–2.4 %)**: límite del modelo de Sutherland. Se documentó la precisión por rango y se
   verificó que el efecto sobre el factor de fricción es menor a 0.5 %.
4. **Compuertas con tolerancia del 5 %**: la operación difiere 0.5 % del diseño porque los desbalances menores al
   5 % se aceptan por criterio. Con tolerancia 0 la concordancia es de 10⁻⁵.
5. **Alternativa B**: el supuesto "menos pérdida ⇒ menos energía" resultó falso en este caso por el reequilibrado de la
   red. El programa estaba en lo correcto; se corrigió la prueba y se añadió una prueba del comportamiento físico.

6. **Revisión del PR (v1.0.1)**: cuatro errores reproducidos con casos del revisor y corregidos (ver
   `docs/AUDITORIA_TECNICA.md`, sección 3 bis). Las pruebas de regresión están en
   `tests/test_regresion_revision.py` (19 casos):
   - η ≥ 100 %: curva con potencias a la mitad rechazada (η = 1.60 = Q·P/W calculado aparte). Sin motor y dictamen
     "no recomendable". Bloqueo también para η_s que implica η_t > 1, para η = 1 indicada y para η > 1 en el
     punto de operación.
   - Transporte: a 2110 rpm el diseño cumple y la operación no. V de R1 y R4 contrastadas con V = ṁ/(ρ·A) y
     V_min = 17.78/√(ρ/1.2) m/s. Alternativa excluida; a 2200 rpm no hay alerta.
   - Intervalo de búsqueda: red de una campana a 1600, 2000, 2300 y 2400 rpm y con D = 0.42/0.44 m. El punto de
     operación coincide (10⁻⁶) con el solucionador de red en modo operación. q_max ajustado = 0.30·2400/2000 = 0.36.
   - Exportación: la GUI con recálculo automático desactivado y t = 35 °C exporta Excel y PDF con ρ(35 °C). El
     valor se contrasta con un `run_project` independiente. Los generadores rechazan resultados desactualizados y
     la huella no depende de la marca de guardado.
   - Efecto en el banco: sin cambios en diseño, operación, potencia, motor (11 kW) ni dictamen. En el comparador,
     D (BI-450) también se excluye por transporte en operación real, además del déficit de caudal.

7. **Segunda revisión del PR**: se corrigió una regresión introducida por el punto 1 de la revisión
   anterior. La validación rechazaba toda curva con un punto de eficiencia nula y caudal positivo, pero
   en una curva en presión estática el extremo de descarga libre tiene FSP = 0 y, por definición,
   η_s = Q·FSP/W = 0, con η_t > 0 por la presión dinámica de salida. Pruebas añadidas (8 casos, al final
   de `tests/test_regresion_revision.py`):
   - Curva estática sintética de 0.05 a 0.30 m³/s que termina en FSP = 0, W = 48 W y η_s = 0: se acepta.
     Contraste independiente en ese punto: VP = ½·1.2·(0.30/0.03)² = 60 Pa, FTP = 60 Pa y
     η_t = 0.30·60/48 = 0.375, calculados a mano.
   - Caso completo con esa curva: hay punto de operación, se selecciona motor y no aparece alerta
     CRÍTICA. η_t y η_s del punto de operación contrastadas contra sus definiciones.
   - Se conserva el rechazo de η = 0 con caudal y presión positivos (exigiría potencia infinita), de
     η < 0 y de η ≥ 100 %, en base total y en base estática.
   - η = 0 a caudal nulo (cierre) se acepta, como antes.

## 4. Pruebas de interfaz y reportes

- La aplicación se abre sin pantalla (QT_QPA_PLATFORM=offscreen), calcula, recorre las 12 páginas y guarda capturas
  (`docs/capturas/`).
- Se edita un campo y se verifica el recálculo; se cambia SI↔IP (95 °F = 35 °C) y se guarda el proyecto.
- La memoria PDF se genera en SI e IP; el texto extraído contiene el dictamen, el camino crítico, la selección del
  ventilador, las hipótesis, el comparador, el anexo de trazabilidad y la numeración "Página X de Y".
- El libro Excel contiene las hojas de resultados, alertas, dictamen, comparador, trazabilidad y gráficos.

## 5. Limitaciones de la validación

- No se dispone de casos publicados del manual ACGIH ni de datos de campo para contraste: deben añadirse cuando el
  usuario los proporcione (pruebas de campo de la sección 5.2 del PDF).
- Los coeficientes tabulados (ACGIH) se validaron solo en su uso, no en su valor; requieren la edición vigente.
