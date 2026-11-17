# Catálogo de calculadoras (versión 2.2.0)

Documento generado automáticamente por `herramientas/generar_catalogo.py` a partir del código. No lo edite a mano.

Niveles de confianza de los resultados: **V** = Verificada; **E** = Empírica (con referencia); **O** = Criterio original sin fuente — no validado; **D** = Dato / conversión.

Un campo sin valor por defecto es obligatorio. «0 = …» en la ayuda indica un valor que activa un criterio alternativo (tabla original, cálculo por altitud, etc.).

## Índice
- **Manejo de sólidos a granel**: [Banda transportadora](#banda), [Elevador de cangilones](#elevador), [Transportador helicoidal](#helicoidal), [Aerodeslizador (deslizador de polvo)](#aerodeslizador), [Transportador neumático](#neumatico), [Tolva de dosificación](#tolva), [Silo metálico (predimensionamiento)](#silo)
- **Ventilación y control de polvo**: [Ductos de aire con polvo](#ductos), [Colector de polvo](#colector), [Soplador](#soplador)
- **Máquinas de fluido y bombeo**: [Bomba centrífuga](#bomba), [Bomba de vacío](#vacio)
- **Térmica y transferencia de calor**: [Torre de enfriamiento](#torre), [Secador rotatorio directo](#secador)
- **Estructural**: [Viga en voladizo o simplemente apoyada](#viga)

## Manejo de sólidos a granel

<a id="banda"></a>
### Banda transportadora  (`banda`)

Capacidad por geometría de la sección (artesa + sobrecarga) y potencia por resistencias (ISO 5048).

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: calculo de banda.py, calculo de banda_vs2.py, Calculo de banda vs3.py, Calculo de banda vs4.py, Calculo de banda vs5.py
- Abrir directamente: `python menu_principal.py --calculadora banda`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/banda.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Banda y material | Ancho de banda B | mm | obligatorio | ≥ 200 y ≤ 3000 |  |
| Banda y material | Material |  | Arena | Opciones: Arena / Grava / Carbón / Mineral de Hierro / Cemento / Otro (capturar velocidad) |  |
| Banda y material | Velocidad de la banda | m/s | 0 | ≥ 0 y ≤ 10 | 0 = usar la velocidad por material del original (sin fuente). |
| Banda y material | Densidad aparente del material | kg/m³ | obligatorio | > 0 |  |
| Sección | Ancho útil de carga b | mm | 0 | ≥ 0 | 0 = ISO 5048: b = 0.9·B − 50 mm (B ≤ 2 000 mm) o B − 250 mm. |
| Sección | Ángulo de artesa λ | ° | 0 | ≥ 0 y ≤ 60 | 0 = banda plana. |
| Sección | Longitud útil del rodillo central l₃ | mm | 0 | ≥ 0 | 0 = longitud normalizada ISO 1537 para el ancho B (o b/3 si B no es normalizado). |
| Sección | Ángulo de sobrecarga β del material | ° | obligatorio | ≥ 0 y ≤ 40 | Propiedad del material (dato de la referencia de la empresa). |
| Sección | Grado de llenado φ (0–1) |  | 1.0 | > 0 y ≤ 1 | Reemplaza la «ocupación» del original, ahora aplicada al área, no al ancho. |
| Potencia | Longitud entre centros L | m | obligatorio | > 0 |  |
| Potencia | Inclinación δ | ° | 0 | ≥ -30 y ≤ 30 | Positiva si sube en el sentido del transporte. |
| Potencia | Coeficiente de fricción ficticio f |  | 0.02 | > 0 y ≤ 0.1 | ISO 5048: 0.020 básico; 0.016 bien alineado; hasta 0.030 desfavorable; 0.012 descendente frenado. |
| Potencia | Coeficiente C de resistencias secundarias |  | 0 | ≥ 0 y ≤ 10 | 0 = ISO 5048: C = (L + L₀)/L. Capture C si calcula las resistencias secundarias. |
| Potencia | Longitud adicional L₀ para C | m | 100 | ≥ 70 y ≤ 100 | ISO 5048: 70–100 m. 100 m es el valor conservador. |
| Potencia | Masa giratoria de rodillos q_R (ida + retorno) | kg/m | 0 | ≥ 0 | Del catálogo de rodillos. |
| Potencia | Masa de la banda q_B | kg/m | 0 | ≥ 0 | Del catálogo de la banda. |
| Potencia | Eficiencia de la transmisión (0–1) |  | obligatorio | > 0 y ≤ 1 | El original indicaba 0.85–0.95. |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Velocidad usada | 1.50 | m/s | D |
| Ancho útil b | 850 | mm | E |
| Área de sobrecarga | 0.03550 | m² | V |
| Área de artesa | 0.07717 | m² | V |
| Longitud del rodillo central l₃ | 380 | mm | E |
| Área efectiva del material (φ·A) | 0.11267 | m² | V |
| Factor de pendiente k (IS 11592, tabla 9) | 0.970 |  | E |
| Capacidad volumétrica | 590.2 | m³/h | V |
| Capacidad másica | 944.3 | t/h | V |
| Carga de material por metro q_G | 174.86 | kg/m | V |
| Altura de elevación H | 13.92 | m | D |
| Coeficiente C de resistencias secundarias | 1.500 |  | D |
| Fuerza tangencial en el tambor motriz F_U | 30.716 | kN | E |
| Potencia en el tambor motriz | 46.07 | kW | E |
| Potencia requerida del motor | 51.19 | kW | E |
| Potencia solo de elevación (verificación) | 35.80 | kW | V |
| Diámetro de tambor sugerido | 400 | mm | O |
| Diámetro de rodillo sugerido | 133 | mm | O |

**Ecuaciones**

```
w = l₃ + (b − l₃)·cos λ;   A_sobrecarga = w²·tan β/6;   A_artesa = (l₃ + w)/2·((b − l₃)/2)·sen λ
Q = φ·A·k·v·3600 [m³/h];   Q_m = Q·ρ/1000 [t/h];   q_G = ρ·φ·A·k [kg/m]
C = (L + L₀)/L ≥ 1.02   (ISO 5048)
F_U = C·f·L·g·[q_R + (2·q_B + q_G)·cos δ] + q_G·g·H   (ISO 5048 / DIN 22101)
P_tambor = F_U·v;   P_motor = P_tambor/η
```

**Advertencias que emite con el caso de prueba**

- Tambor y rodillo sugeridos: tablas originales por ancho, sin fuente. Seleccione según tensión de la banda y catálogo.

**Referencias**

- ISO 5048:1989 e IS 11592:2000 (alineada con ISO 5048): sección S1 + S2, ancho útil b, f, C, factor de pendiente k y fuerza tangencial F_U.
- ISO 1537:1975: longitud de rodillos de artesas de tres rodillos.
- Validación: MEKA Crushing, Screening and Mining Equipment Handbook (capacidad volumétrica de referencia) — tests/test_banda.py.

**Limitaciones**

- Validada la capacidad y la potencia por el método ISO 5048 con C global.
- Masas de rodillos y de banda: datos de catálogo del usuario.
- Sin cálculo de tensiones, selección de banda ni de tambores (tambor y rodillo sugeridos: O).
- Para L < 80 m el C de ISO 5048 es incierto: capture C.

<a id="elevador"></a>
### Elevador de cangilones  (`elevador`)

Capacidad, potencia de elevación y verificación de descarga centrífuga.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo de Elevador vs1.py, Calculo de Elevador vs2.py, Calculo de Elevador vs3.py
- Abrir directamente: `python menu_principal.py --calculadora elevador`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/elevador.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Material | Material |  | Arena | Opciones: Arena / Asfalto / Carbon / Fluorita / Cemento / Caliza / Marmol / Arcilla / Caolin / Yeso / Otro (capturar densidad) |  |
| Material | Densidad aparente | kg/m³ | 0 | ≥ 0 | 0 = usar la tabla original del elevador (sin fuente). |
| Cangilones | Tipo de descarga |  | Descarga centrífuga, materiales livianos | Opciones: Descarga centrífuga, materiales livianos / Descarga centrífuga, materiales secos / Descarga por gravedad, materiales pesados / Descarga por gravedad, materiales abrasivos / Descarga combinada |  |
| Cangilones | Velocidad de la banda/cadena | m/s | 0 | ≥ 0 y ≤ 5 | 0 = velocidad de la tabla original según el tipo de descarga. |
| Cangilones | Paso de cangilones |  | L1 — paso 200 mm | Opciones: L1 — paso 200 mm / L3 — paso 250 mm / L5 — paso 300 mm / L6 — paso 300 mm / L8 — paso 350 mm / L12 — paso 400 mm / L14 — paso 330 mm / L20 — paso 400 mm / L30 — paso 500 mm / Capturar paso |  |
| Cangilones | Paso capturado | mm | 0 | ≥ 0 |  |
| Cangilones | Cangilón |  | C1 — 80 × 150 × 110 | Opciones: C1 — 80 × 150 × 110 / C3 — 80 × 180 × 130 / C5 — 80 × 200 × 150 / C6 — 80 × 250 × 150 / C8 — 80 × 300 × 200 / C12 — 80 × 400 × 250 / C14 — 90 × 400 × 250 / C20 — 90 × 500 × 320 / C30 — 90 × 600 × 400 / Capturar volumen de catálogo |  |
| Cangilones | Volumen de catálogo del cangilón | L | 0 | ≥ 0 | Capacidad de agua o volumen útil del fabricante. |
| Cangilones | Grado de llenado φ (0–1) |  | 0.8 | > 0 y ≤ 1 | 0.8 era el llenado implícito en la tabla original. |
| Potencia | Altura de elevación H | m | obligatorio | > 0 |  |
| Potencia | Altura equivalente de dragado y fricción capturada | m | 0 | ≥ 0 | Si > 0 sustituye al método KWS (dato del fabricante). |
| Potencia | Factor de longitud equivalente Leq (KWS) |  | 10 | ≥ 5 y ≤ 15 | KWS: 5 a 15 según la aplicación; el ejemplo KWS de arena usa 7. |
| Potencia | Diámetro del tambor de cola | mm | 0 | ≥ 0 | 0 = igual al tambor de cabeza. |
| Potencia | Eficiencia mecánica de la transmisión (0–1) |  | obligatorio | > 0 y ≤ 1 | El original indicaba 0.70–0.90. |
| Tambor | Ancho de banda | mm | obligatorio | > 0 |  |
| Tambor | Diámetro del tambor de cabeza | mm | 0 | ≥ 0 | 0 = tabla original por ancho de banda (sin fuente). |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Velocidad usada | 2.50 | m/s | O |
| Paso de cangilones | 350 | mm | O |
| Cangilones por metro | 2.857 | 1/m | V |
| Volumen del cangilón (sin llenado) | 4.800 | L | O |
| Capacidad volumétrica | 98.74 | m³/h | V |
| Capacidad másica | 118.49 | t/h | V |
| Altura equivalente de dragado y fricción | 4.50 | m | E |
| Potencia en el eje de cabeza (elevación + dragado) | 9.522 | kW | E |
| Potencia requerida del motor | 11.202 | kW | E |
| Diámetro del tambor de cabeza | 450 | mm | O |
| v²/(g·R) en el tambor de cabeza | 2.833 |  | V |

**Ecuaciones**

```
n = 1000/paso [cangilones/m]
Q = n·v·V·φ·3600 [m³/h];   Q_m = Q·ρ/1000 [t/h]
P = ṁ·g·(H + Leq·d_cola)/η   (KWS: P[HP] = G·(DH + Leq·d)/(33 000·60))
v²/(g·R): relación entre fuerza centrífuga y peso en el tambor de cabeza
```

**Advertencias que emite con el caso de prueba**

- Velocidad tomada de la tabla original por tipo de descarga (sin fuente).
- Volumen del cangilón = proyección × ancho × fondo (prisma) de la tabla original: no es la capacidad de catálogo. Capture el volumen del fabricante.
- Diámetro de tambor de la tabla original (sin fuente) usado también para el dragado KWS: capture los diámetros reales.

**Referencias**

- Balance de energía: P = ṁ·g·H/η (física básica).
- Dragado y fricción: KWS Bucket Elevator Engineering Guide, «Horsepower Calculation» (método de longitud equivalente, Leq 5–15).
- Pasos, cangilones y velocidades: tablas originales sin fuente (usar catálogo).

**Limitaciones**

- Capacidad con volumen de catálogo capturado; la tabla original usa un prisma (nivel O).
- Leq depende de la aplicación (5–15): confirmar con el fabricante.
- Velocidad y diámetros de tambor de tablas originales sin fuente si no se capturan.

<a id="helicoidal"></a>
### Transportador helicoidal  (`helicoidal`)

Selección de diámetro y velocidad, potencia y par por el método CEMA (tablas KWS).

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo del transportador helicoidal.py
- Abrir directamente: `python menu_principal.py --calculadora helicoidal`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/helicoidal.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Material | Material (tabla KWS) |  | Cemento Portland (cement, Portland) | Opciones: Alúmina (alumina) / Almidón (starch) / Arcilla calcinada (clay, calcined) / Arcilla de ladrillo, finos secos (clay, brick, dry fines) / Arcilla seca en terrones (clay, dry lumpy) / Arena seca de banco (sand, dry bank) / Arena sílica seca (sand, silica, dry) / Aserrín seco (sawdust, dry) / Astillas de madera (wood chips) / Azúcar granulada seca (sugar, granulated dry) / Bentonita (bentonite) / Cal hidratada (lime, hydrated) / Cal hidratada pulverizada (lime, hydrated, pulverized) / Cal viva en guijarros (lime, pebble, unslaked) / Caliza agrícola (limestone, agricultural) / Caliza triturada (limestone, crushed) / Caliza en polvo (limestone, dust) / Caolín (kaolin clay) / Carbón bituminoso extraído (coal, bituminous, mined) / Carbonato de sodio denso (soda ash, heavy) / Carbonato de sodio ligero (soda ash, light) / Cemento Portland (cement, Portland) / Ceniza volante (fly ash) / Clínker de cemento (cement clinker) / Fluorita (fluorspar) / Harina de maíz (corn meal) / Harina de sílice (silica flour) / Mineral de hierro (iron ore) / Potasa seca (potash, dry) / Roca fosfórica pulverizada (phosphate rock, pulverized) / Sal seca gruesa (salt, dry, coarse) / Sal seca fina (salt, dry, fine) / Talco en polvo (talc, powdered) / Trigo (wheat) / Yeso calcinado (gypsum, calcined) / Yeso crudo (gypsum, raw) / Otro (capturar densidad, carga y MF) |  |
| Material | Densidad aparente | kg/m³ | 0 | ≥ 0 | 0 = valor mínimo del intervalo de la tabla KWS (el más conservador para capacidad y velocidad). |
| Material | Carga de la artesa |  | Según tabla del material | Opciones: Según tabla del material / 15 % / 30 % (clase 30A) / 30 % (clase 30B) / 45 % | 30A y 30B difieren en la velocidad máxima recomendada (30B: materiales abrasivos). |
| Material | Factor de material MF |  | 0 | ≥ 0 y ≤ 10 | 0 = tabla KWS (si la tabla da un intervalo se usa el valor mayor). |
| Capacidad | Capacidad requerida | t/h | obligatorio | > 0 |  |
| Capacidad | Factor de diseño sobre la capacidad |  | 1.0 | ≥ 1 y ≤ 3 | 1.0 = capacidad requerida (KWS/CEMA). La versión original usaba 1.25 fijo. |
| Tornillo | Diámetro del tornillo |  | Automático (menor diámetro que cumpla) | Opciones: Automático (menor diámetro que cumpla) / 4 plg / 6 plg / 9 plg / 12 plg / 14 plg / 16 plg / 18 plg / 20 plg / 24 plg / 30 plg / 36 plg |  |
| Tornillo | Paso del tornillo (CF1) |  | Estándar (paso = D) | Opciones: Estándar (paso = D) / Corto (paso = 2/3 D) / Medio (paso = 1/2 D) / Largo (paso = 1.5 D) |  |
| Tornillo | Tipo de hélice (CF2, SF) |  | Estándar (hélice continua) | Opciones: Estándar (hélice continua) / Cortada (cut flight) / Cortada y doblada (cut & folded) / Listón (ribbon) |  |
| Tornillo | Paletas de mezcla por paso (CF3, PF) |  | 0 | ≥ 0 y ≤ 4 |  |
| Tornillo | Capacidad a 1 rpm (catálogo del fabricante) | ft³/(h·rpm) | 0 | ≥ 0 | 0 = tabla KWS. Requiere elegir un diámetro. |
| Tornillo | Velocidad máxima recomendada (catálogo) | rpm | 0 | ≥ 0 | 0 = tabla KWS. Requiere elegir un diámetro. |
| Potencia | Longitud del transportador | m | obligatorio | > 0 |  |
| Potencia | Cojinetes colgantes (HBF) |  | Bronce o madera | Opciones: Bolas, rodillos o sin colgantes / Bronce o madera / Plástico, nylon, UHMW o teflón / Hierro endurecido o stellite | Materiales abrasivos suelen requerir hierro endurecido (HBF 4.4). |
| Potencia | Eficiencia del accionamiento | % | 88 | > 0 y ≤ 100 | KWS: típico 88 % (reductor montado en flecha); entre 85 y 95 %. |
| Potencia | Factor de sobrecarga Fo (CEMA) |  | 0 | ≥ 0 y ≤ 5 | 0 = aproximación de la gráfica CEMA (Fo = 1 si HPf + HPm > 5.2 HP). |
| Potencia | MHP corregido de la gráfica KWS | HP | 0 | ≥ 0 | Si > 0 se usa el procedimiento KWS: TSHP = (FHP + MHP corregido)/e, sin Fo. |
| Inclinación | Ángulo de inclinación | ° | 0 | ≥ 0 y ≤ 45 | Hasta 10° sin corrección (KWS). Más de 10°: capture los dos factores siguientes. |
| Inclinación | Eficiencia de transporte por inclinación |  | 0 | ≥ 0 y ≤ 1 | Fracción de la capacidad horizontal (gráfica del fabricante). 0 = no capturado. |
| Inclinación | Factor de potencia por inclinación Fi |  | 0 | ≥ 0 y ≤ 5 | Gráfica del fabricante. Se aplica a FHP + MHP (criterio conservador). 0 = 1. |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Densidad aparente usada | 1 506 | kg/m³ | E |
| Densidad aparente usada | 94.0 | lb/ft³ | E |
| Carga de artesa (clase KWS) | 30 % (30B) |  | E |
| Factor de material MF | 1.40 |  | E |
| Capacidad de diseño CP | 22 046 | lb/h | D |
| Capacidad volumétrica CFH | 234.5 | ft³/h | V |
| Capacidad volumétrica CFH | 6.64 | m³/h | D |
| Factor de paso CF1 | 1.00 |  | E |
| Factor de hélice especial CF2 | 1.00 |  | E |
| Factor de paletas CF3 | 1.00 |  | E |
| Capacidad de selección SC | 234.5 | ft³/h | E |
| Diámetro del tornillo | 9 | plg | E |
| Diámetro del tornillo | 229 | mm | D |
| Capacidad a 1 rpm | 5.50 | ft³/(h·rpm) | E |
| Velocidad máxima recomendada | 55 | rpm | E |
| Capacidad a velocidad máxima | 305 | ft³/h | E |
| Velocidad de giro requerida | 42.6 | rpm | E |
| Cumple capacidad a velocidad máxima | Sí |  | E |
| Factor de diámetro DF | 31 |  | E |
| Factor de cojinete colgante HBF | 1.7 |  | E |
| Factor de hélice especial SF (potencia) | 1.00 |  | E |
| Factor de paletas PF (potencia) | 1.00 |  | E |
| Longitud | 19.69 | ft | D |
| Potencia de fricción FHP | 0.0442 | HP | E |
| Potencia de material MHP | 0.6076 | HP | E |
| Corrección por sobrecarga | CEMA (Fo sobre HPf + HPm) |  | D |
| Factor de sobrecarga Fo | 2.27 |  | E |
| Potencia total en la flecha TSHP | 1.685 | HP | E |
| Potencia total en la flecha | 1.256 | kW | E |
| Motor comercial mínimo (NEMA MG 1) | 2 | HP | D |
| Par a plena carga del motor en el tornillo | 2 956 | lbf·plg | V |
| Par a plena carga del motor en el tornillo | 334.0 | N·m | D |
| Motor comercial mínimo (IEC 60072-1) | 1.50 | kW | D |

**Ecuaciones**

```
CP = Q·f·1000/0.45359237 [lb/h];   CFH = CP/ρ [ft³/h]
SC = CFH·CF1·CF2·CF3 / η_incl;   N = SC / (capacidad a 1 rpm)
FHP = L·N·DF·HBF/10⁶;   MHP = CP·L·MF·SF·PF/10⁶   (L en ft)
TSHP = (FHP + MHP)·Fo·Fi / e   (CEMA)
T = 63 025·HP_motor / N [lbf·plg]
```

**Advertencias que emite con el caso de prueba**

- Fo obtenido por interpolación log-lineal de la gráfica CEMA (aproximación, no transcripción de la gráfica). Para un valor exacto capture Fo leído de la gráfica o el MHP corregido KWS.

**Referencias**

- KWS Screw Conveyor Engineering Guide (método CEMA): Screw Conveyor Capacity, Screw Conveyor Horsepower, Bulk Material Table, Screw Conveyor Torque (kwsmfg.com, consultado nov. 2026).
- CEMA 350 — Screw Conveyors for Bulk Materials (método de potencia con Fo), según catálogo Martin, sección H (aprobado por la sección de transportadores helicoidales de CEMA).
- NEMA MG 1 (potencias nominales de motores, HP); IEC 60072-1 (potencias nominales, kW).

**Limitaciones**

- Validado con el ejemplo publicado por KWS (harina de maíz, 12 plg, 30A): ver tests/test_helicoidal.py.
- Fo por interpolación de la gráfica CEMA cuando no se captura: aproximación (nivel E).
- Inclinación > 10° solo con factores capturados por el usuario; > 45° fuera de alcance.
- No cubre alimentadores de tornillo, transportadores verticales ni sin flecha (shaftless).
- No verifica tamaño de terrón ni resistencia de componentes (solo calcula el par a plena carga).

<a id="aerodeslizador"></a>
### Aerodeslizador (deslizador de polvo)  (`aerodeslizador`)

Capacidad, aire de fluidización y pérdidas de presión (Ergun y lecho fluidizado).

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDACIÓN PENDIENTE**
- Sustituye a: Calculo de Deslizador vs1.py, Calculo de Deslizador vs2.py
- Abrir directamente: `python menu_principal.py --calculadora aerodeslizador`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/aerodeslizador.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Material | Material |  | Cemento | Opciones: Arena / Asfalto / Carbon / Fluorita / Cemento / Caliza / Marmol / Arcilla / Caolin / Yeso / Otro (capturar densidad) |  |
| Material | Densidad aparente del material fluidizado | kg/m³ | 0 | ≥ 0 | 0 = tabla original del deslizador (sin fuente). |
| Transporte | Tipo de descarga |  | Descarga materiales secos | Opciones: Descarga materiales livianos / Descarga materiales secos / Descarga combinada |  |
| Transporte | Velocidad del material | m/s | 0 | ≥ 0 y ≤ 10 | 0 = tabla original por tipo de descarga (sin fuente). |
| Transporte | Ancho del canal | mm | obligatorio | > 0 | El original indicaba 300–1000 mm. |
| Transporte | Altura del lecho de material en movimiento | mm | obligatorio | > 0 | El original lo llamaba «altura del colchón (2–5 mm)»; confirme su significado. |
| Transporte | Inclinación | ° | 0 | ≥ 0 y ≤ 30 | No interviene en el cálculo. |
| Aire de fluidización | Longitud del aerodeslizador | m | 0 | ≥ 0 | 0 = no calcular el aire. |
| Aire de fluidización | Caudal específico de aire | m³/(min·m²) | 0 | ≥ 0 | Dato del fabricante de la tela porosa. 0 = no calcular. |
| Lecho | Porosidad del lecho ε |  | obligatorio | > 0 y < 1 | El original indicaba 0.45–0.55. |
| Lecho | Tamaño medio de partícula | µm | obligatorio | > 0 |  |
| Lecho | Viscosidad del aire | Pa·s | 1.8e-05 | > 0 |  |
| Lecho | Densidad del aire | kg/m³ | 1.2 | > 0 |  |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Velocidad del material usada | 3.00 | m/s | O |
| Capacidad de transporte | 285.12 | t/h | O |
| ΔP del lecho fluidizado (peso por área) | 647.2 | Pa | V |
| ΔP del lecho fluidizado | 66.00 | mm H₂O | D |
| Velocidad mínima de fluidización (Ergun) | 1.798 | mm/s | V |
| Área de tela porosa | 8.00 | m² | V |
| Caudal de aire de fluidización | 12.000 | m³/min | V |
| Caudal de aire de fluidización | 720.0 | m³/h | D |
| Velocidad superficial del aire | 25.000 | mm/s | V |
| ΔP de Ergun a esa velocidad (lecho fijo) | 9 010.5 | Pa | V |
| ¿El lecho se fluidiza? (u ≥ u_mf) | Sí |  | V |
| ΔP a través del lecho | 647.2 | Pa | V |

**Ecuaciones**

```
Q_m = v·b·h·ρb·3.6 [t/h]
ΔP/H = 150·μ·(1−ε)²·u/(ε³·d²) + 1.75·ρg·(1−ε)·u²/(ε³·d)   (Ergun)
ΔP_fluidizado = ρb·g·H;   u_mf: Ergun(u_mf)·H = ρb·g·H
Q_aire = q_específico·b·L
```

**Advertencias que emite con el caso de prueba**

- Velocidad del material tomada de la tabla original (sin fuente).
- La inclinación no interviene en este cálculo: la relación capacidad–pendiente es empírica y no estaba documentada en el original.

**Referencias**

- Ecuación de Ergun y criterio de mínima fluidización (Kunii y Levenspiel, Fluidization Engineering).

**Limitaciones**

- Capacidad depende de la velocidad del material (tabla original sin fuente).
- Sin pérdida de la tela porosa ni efecto de la pendiente.

<a id="neumatico"></a>
### Transportador neumático  (`neumatico`)

Diámetro, capacidad de sólidos, pérdidas de aire y de sólidos (Barth) y potencia del soplador.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDACIÓN PENDIENTE**
- Sustituye a: Calculo transportador neumatico rev 0.py, Calculo transportador neumatico rev 1.py
- Abrir directamente: `python menu_principal.py --calculadora neumatico`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/neumatico.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Sistema | Tipo de transporte |  | Fase diluida | Opciones: Fase diluida / Fase densa |  |
| Sistema | Caudal de aire de transporte | m³/h | obligatorio | > 0 |  |
| Sistema | Velocidad del aire | m/s | obligatorio | > 0 | El original indicaba 15–25 m/s (rango de fase diluida). |
| Sistema | Relación de carga μ (kg material / kg aire) |  | obligatorio | ≥ 0 | El original pedía «relación aire/material, ej. 4 para 1:4»: 1 kg de aire por 4 kg de material → μ = 4. |
| Tubería | Longitud equivalente de la tubería | m | obligatorio | > 0 |  |
| Tubería | Rugosidad absoluta de la tubería | mm | 0 | ≥ 0 y ≤ 10 | 0 = tubo liso (subestima la fricción). Tomar de su referencia. |
| Tubería | Suma de coeficientes K de accesorios (aire) |  | 0 | ≥ 0 |  |
| Sólidos | Coeficiente de pérdida adicional por sólidos Ks = λZ/λL |  | 0 | ≥ 0 | Dato del método de la empresa (Barth). 0 = no se calcula la pérdida de los sólidos. |
| Aire | Temperatura del aire | °C | 20 | ≥ -40 y ≤ 300 |  |
| Aire | Altitud del sitio | m | 0.0 | ≥ -500 y ≤ 5000 |  |
| Aire | Eficiencia del soplador (0–1) |  | 0.75 | > 0 y ≤ 1 | 0.75 era la constante del original. |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Diámetro interior de la tubería | 162.9 | mm | V |
| Densidad del aire | 1.2042 | kg/m³ | D |
| Flujo másico de aire | 1 806.2 | kg/h | V |
| Capacidad de sólidos | 7.225 | t/h | V |
| Número de Reynolds | 216 307 |  | V |
| Factor de fricción de Darcy (turbulento) | 0.01760 |  | V |
| Pérdida de presión del aire | 2 043.5 | Pa | V |
| Pérdida adicional por sólidos | 4 087.0 | Pa | E |
| Pérdida de presión total | 6 130.6 | Pa | E |
| Pérdida de presión total | 62.51 | cm H₂O | D |
| Potencia al eje del soplador | 3.406 | kW | V |

**Ecuaciones**

```
D = √(4·Q/(π·v));  ṁ_aire = ρ·Q;  ṁ_s = μ·ṁ_aire
ΔP_aire = f·(L/D)·ρ·v²/2 + ΣK·ρ·v²/2   (f por Colebrook-White)
ΔP_sólidos = μ·Ks·ΔP_aire   (forma de Barth, Ks del usuario)
P = (ΔP_aire + ΔP_sólidos)·Q/η
```

**Referencias**

- Darcy-Weisbach y Colebrook-White.
- Separación de pérdidas aire + sólidos (Barth); Ks debe venir de la referencia de la empresa (p. ej. Mills, Pneumatic Conveying Design Guide).

**Limitaciones**

- Sin aceleración de sólidos ni elevación de sólidos.
- Solo fase diluida.

<a id="tolva"></a>
### Tolva de dosificación  (`tolva`)

Volumen, altura, ángulos de pared y flujo de descarga (Beverloo) de una tolva de transición.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDACIÓN PENDIENTE**
- Sustituye a: calculo de tolva de dosificación.py
- Abrir directamente: `python menu_principal.py --calculadora tolva`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/tolva.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Material | Masa de material a almacenar | kg | obligatorio | > 0 |  |
| Material | Material |  | Cemento | Opciones: Yeso / Fluorita / Cemento / Cal / Carbonato de calcio / Arcilla / Mineral de hierro / Caolin / Otro (capturar densidad) |  |
| Material | Densidad aparente | kg/m³ | 0 | ≥ 0 | 0 = tabla original de la tolva (sin fuente; varios valores son densidad real, no aparente). |
| Material | Ángulo de reposo | ° | 0 | ≥ 0 y ≤ 90 | 0 = tabla original. Solo se usa como comparación indicativa. |
| Material | Tamaño medio de partícula | mm | 0 | ≥ 0 | Para Beverloo. 0 = se desprecia el término k·d (polvo muy fino: la correlación sobreestima). |
| Geometría | Área de la boca superior cuadrada | m² | obligatorio | > 0 |  |
| Geometría | Área de la descarga circular | m² | obligatorio | > 0 |  |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Volumen de material | 2.500 | m³ | V |
| Lado de la boca superior | 2.000 | m | D |
| Diámetro de la descarga | 0.357 | m | D |
| Altura de la tolva (tronco de secciones semejantes) | 1.585 | m | V |
| Longitud de pared en la cara plana | 1.785 | m | V |
| Ángulo de la cara plana con la horizontal | 62.6 | ° | V |
| Ángulo de la arista (valle) con la horizontal | 52.1 | ° | V |
| Flujo de descarga (Beverloo) | 165.689 | kg/s | E |
| Flujo de descarga (Beverloo) | 9 941.4 | kg/min | E |
| Flujo de descarga (Beverloo) | 596.48 | t/h | E |
| Tiempo de vaciado a ese flujo | 0.3 | min | E |
| Ángulo de reposo de referencia | 35 | ° | O |

**Ecuaciones**

```
V = m/ρ;   h = 3V/(A₁ + A₂ + √(A₁·A₂))
W = C·ρ·√g·(D₀ − k·d)^2.5,  C = 0.58,  k = 1.4   (Beverloo, 1961)
```

**Advertencias que emite con el caso de prueba**

- Partícula de 0.05 mm: Beverloo NO es aplicable a polvos finos (< ~0.4 mm). El aire intersticial reduce la descarga; el flujo real puede ser varias veces menor. Use el dato del dosificador o de la válvula, o pruebas.
- El ángulo de pared para flujo másico depende de la fricción con la pared (método de Jenike); no se verifica aquí.

**Referencias**

- Beverloo, Leniger y Van de Velde (1961), Chem. Eng. Sci. 15, 260: C ≈ 0.58, k ≈ 1.4.
- Aplicabilidad: sólidos gruesos no cohesivos; los polvos finos descargan más lento (Nedderman, Statics and Kinematics of Granular Materials, 1992).

**Limitaciones**

- Transición cuadrado–círculo aproximada como tronco de secciones semejantes.
- Sin análisis de flujo másico (Jenike).
- Flujo de Beverloo no aplicable a polvos finos (< ~0.4 mm).

<a id="silo"></a>
### Silo metálico (predimensionamiento)  (`silo`)

PREDIMENSIONAMIENTO: geometría, presiones de llenado de Janssen, espesor por presión circunferencial y descarga por gravedad. No apto para diseño estructural.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo de un silo metalico.py
- Abrir directamente: `python menu_principal.py --calculadora silo`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/silo.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Material | Masa de material almacenado | kg | obligatorio | > 0 |  |
| Material | Material |  | Cemento | Opciones: Yeso / Fluorita / Cemento / Cal / Carbonato de calcio / Arcilla / Mineral de hierro / Caolin / Otro (capturar densidad) |  |
| Material | Densidad aparente | kg/m³ | 0 | ≥ 0 | 0 = tabla original del silo (sin fuente). Para presiones use el valor superior de diseño. |
| Material | Relación de presión lateral K |  | obligatorio | > 0 y ≤ 1.5 | Propiedad del material (p. ej. EN 1991-4, anexo E). Jaky: K₀ = 1 − sen φ. |
| Material | Coeficiente de fricción con la pared μ |  | obligatorio | > 0 y ≤ 1.5 | Propiedad material–pared (ensayo o tabla de la norma). |
| Material | Tamaño medio de partícula | mm | 0 | ≥ 0 | Para el caudal de descarga (Beverloo). |
| Geometría | Diámetro del cilindro | m | obligatorio | > 0 |  |
| Geometría | Semiángulo de la tolva respecto a la vertical | ° | obligatorio | > 0 y ≤ 80 |  |
| Geometría | Diámetro de la descarga | m | obligatorio | > 0 |  |
| Envolvente | Esfuerzo admisible de la lámina | MPa | obligatorio | > 0 | Según el código y material de diseño de la empresa. |
| Envolvente | Eficiencia de junta soldada (0–1) |  | 1.0 | > 0 y ≤ 1 |  |
| Envolvente | Sobreespesor por corrosión/desgaste | mm | 0 | ≥ 0 |  |
| Envolvente | Espesor mínimo constructivo | mm | 2 | ≥ 0 | 2 mm era el mínimo del original. |
| Envolvente | Factor de sobrepresión de descarga |  | 1.0 | ≥ 1 y ≤ 3 | Multiplica la presión estática de Janssen. Tomar de la norma (EN 1991-4). |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Volumen de material | 76.923 | m³ | V |
| Altura de la tolva cónica | 3.204 | m | V |
| Volumen de la tolva | 14.504 | m³ | V |
| Altura de material en el cilindro | 4.967 | m | V |
| Altura total (tolva + cilindro, sin cono de sobrecarga) | 8.171 | m | V |
| Presión horizontal en la base del cilindro (Janssen) | 20.07 | kPa | V |
| Presión vertical en la base del cilindro | 40.14 | kPa | V |
| Fricción en pared en la base del cilindro | 8.03 | kPa | V |
| Presión horizontal asintótica (cilindro infinito) | 31.87 | kPa | V |
| Compresión axial en la pared por fricción (base) | 23.19 | kN/m | V |
| Presión horizontal de diseño (× factor de descarga) | 24.08 | kPa | V |
| Espesor de predimensionamiento por presión circunferencial | 1.88 | mm | V |
| Espesor mínimo de predimensionamiento (sin pandeo) | 4.00 | mm | V |
| Caudal de descarga por gravedad (Beverloo) | 418.78 | t/h | E |
| Caudal de descarga por gravedad (Beverloo) | 6 979.6 | kg/min | E |

**Ecuaciones**

```
h_tolva = (D − d₀)/(2·tan α);   V_tolva = π·h/12·(D² + D·d₀ + d₀²)
z₀ = R/(K·μ), R = D/4;   p_h = ρ·g·R/μ·(1 − e^(−z/z₀));   p_v = p_h/K;   p_w = μ·p_h   (Janssen)
n = R·(ρ·g·z − p_v)   (peso soportado por fricción por metro de perímetro)
t = p_h,diseño·(D/2)/(σ_adm·E) + c
W = 0.58·ρ·√g·(d₀ − 1.4·d)^2.5   (Beverloo)
```

**Advertencias que emite con el caso de prueba**

- PREDIMENSIONAMIENTO — NO APTO PARA DISEÑO ESTRUCTURAL. No se verificó el pandeo por compresión axial (EN 1993-4-1), las presiones de descarga normativas (EN 1991-4), la tolva, el viento, el sismo ni los apoyos. El espesor reportado cubre solo la tensión circunferencial por presión de llenado.
- Partícula de 0.05 mm: Beverloo NO es aplicable a polvos finos (< ~0.4 mm). El aire intersticial reduce la descarga; el flujo real puede ser varias veces menor. Use el dato del dosificador o de la válvula, o pruebas.

**Referencias**

- Teoría de Janssen (1895) para presiones en silos; misma forma que las presiones de llenado de EN 1991-4 para silos esbeltos: p_hf = γ·K·z₀·(1 − e^(−z/z₀)), z₀ = A/(K·μ·U).
- EN 1991-4 (acciones en silos) y EN 1993-4-1 (silos de acero): referencias para factores y pandeo.
- Beverloo et al. (1961) para la descarga; no aplicable a polvos finos (Nedderman, 1992).

**Limitaciones**

- Solo predimensionamiento (decisión del usuario): NO apto para diseño estructural.
- Sin pandeo, sin presiones de descarga normativas, sin tolva, viento ni sismo.
- K y μ: datos del material (EN 1991-4, anexo E, o ensayos).

## Ventilación y control de polvo

<a id="ductos"></a>
### Ductos de aire con polvo  (`ductos`)

Diámetro, pérdida de presión (Darcy-Weisbach) y potencia de ventilador para un ducto circular.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo de dimensionamientos de ductos con polvo.py
- Abrir directamente: `python menu_principal.py --calculadora ductos`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/ductos.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Flujo | Caudal de aire | m³/h | obligatorio | > 0 |  |
| Flujo | Velocidad de diseño en el ducto | m/s | obligatorio | > 0 | Debe ser mayor o igual a la velocidad mínima de transporte del polvo. |
| Flujo | Tipo de contaminante (velocidad mínima ACGIH) |  | No verificar / capturar velocidad mínima | Opciones: No verificar / capturar velocidad mínima / Vapores, gases y humo (cualquier velocidad; óptimo 1000–2000 fpm) / Humos metálicos — soldadura (2000–2500 fpm) / Polvo muy fino y ligero — pelusa de algodón, harina de madera (2500–3000 fpm) / Polvos secos — polvo de hule, baquelita, jabón, virutas ligeras (3000–4000 fpm) / Polvo industrial promedio — caliza, arcilla, harina de sílice, manejo de materiales (3500–4000 fpm) / Polvos pesados — aserrín húmedo, rebaba metálica, arena de chorro, plomo (4000–4500 fpm) / Polvos pesados o húmedos — cemento húmedo, cal viva (4500 fpm o más) |  |
| Flujo | Velocidad mínima de transporte capturada | m/s | 0 | ≥ 0 | Si > 0 sustituye a la tabla ACGIH (dato de la empresa o del fabricante). |
| Aire | Temperatura del aire | °C | 20 | ≥ -40 y ≤ 400 |  |
| Aire | Altitud del sitio | m | 0.0 | ≥ -500 y ≤ 5000 |  |
| Aire | Densidad del aire | kg/m³ | 0 | ≥ 0 | 0 = calcular como aire seco con la altitud y la temperatura. |
| Ducto | Longitud del ducto | m | obligatorio | > 0 |  |
| Ducto | Factor de fricción de Darcy |  | 0 | ≥ 0 y ≤ 0.2 | 0 = calcular con Colebrook-White a partir de la rugosidad. Es el factor de DARCY (4 × Fanning). |
| Ducto | Material del ducto (rugosidad ASHRAE) |  | Medianamente liso — acero galvanizado, costura longitudinal o espiral (0.09 mm) | Opciones: Liso — acero al carbono limpio, PVC, aluminio (0.03 mm) / Medianamente liso — acero galvanizado, costura longitudinal o espiral (0.09 mm) / Promedio — galvanizado por inmersión, juntas a 760 mm (0.15 mm) / Medianamente rugoso — fibra de vidrio rígido, espiral corrugado (0.9 mm) / Rugoso — ducto flexible extendido (3.0 mm) |  |
| Ducto | Rugosidad absoluta capturada | mm | 0 | ≥ 0 y ≤ 10 | 0 = según el material elegido. Se usa solo si el factor de fricción es 0. |
| Ducto | Suma de coeficientes K de accesorios |  | 0 | ≥ 0 | Campanas, codos, transiciones (ΣK). 0 = solo tramo recto. |
| Ventilador | Eficiencia del ventilador (0–1) |  | obligatorio | > 0 y ≤ 1 |  |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Diámetro interior del ducto | 0.4205 | m | V |
| Diámetro interior del ducto | 420.5 | mm | V |
| Densidad del aire usada | 1.2000 | kg/m³ | D |
| Número de Reynolds | 556 577 |  | V |
| Factor de fricción de Darcy (capturado) | 0.02000 |  | V |
| Pérdida por fricción | 570.7 | Pa | V |
| Pérdida por accesorios | 0.0 | Pa | V |
| Pérdida de presión total | 570.7 | Pa | V |
| Pérdida de presión total | 58.20 | mm H₂O | V |
| Potencia al eje del ventilador | 2.265 | kW | V |
| Potencia al eje del ventilador | 3.037 | HP | D |
| Velocidad mínima de transporte | 18.0 | m/s | D |
| Cumple velocidad mínima de transporte | Sí |  | D |

**Ecuaciones**

```
D = √(4·Q / (π·v))
Re = ρ·v·D/μ   (μ del aire por la ley de Sutherland)
1/√f = −2·log₁₀(ε/(3.7·D) + 2.51/(Re·√f))   (Colebrook-White, si f no se captura)
ΔP = f·(L/D)·ρ·v²/2 + ΣK·ρ·v²/2
P = ΔP·Q/η
v_min = v_min,ACGIH/√df;   df = ρ/(0.075 lb/ft³)   (ACGIH, 31.ª ed., ec. 5.1)
```

**Referencias**

- Darcy-Weisbach y Colebrook-White (mecánica de fluidos clásica).
- Viscosidad del aire: ley de Sutherland.
- Rugosidad: ASHRAE Handbook — Fundamentals, Duct Design, tabla 1 (categorías de rugosidad).
- Velocidades mínimas de diseño: ACGIH, Industrial Ventilation — A Manual of Recommended Practice for Design; corrección por densidad: 31.ª ed., ec. 5.1.
- Validación: ejemplo de ducto redondo de 24 plg con la base ASHRAE DFDB (tests/test_ductos.py).

**Limitaciones**

- No incluye campanas ni accesorios salvo por ΣK capturado.
- No corrige por la carga de polvo en la densidad del aire.

<a id="colector"></a>
### Colector de polvo  (`colector`)

Área de filtración, pérdida total, potencia de ventilador y volumen de polvo captado.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: calculo de colector de polvo.py
- Abrir directamente: `python menu_principal.py --calculadora colector`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/colector.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Aire | Caudal de aire | m³/h | obligatorio | > 0 |  |
| Aire | Velocidad en el ducto de entrada | m/s | obligatorio | > 0 | El original indicaba 20–25 m/s. |
| Filtro | Polvo (relación aire/tela EPA, tabla 1.1) |  | Cemento | Opciones: Almidón / Alúmina / Arcilla / Arena / Asbesto / Aserrín (madera) / Azúcar / Bauxita / Cacao, chocolate / Cal / Caliza / Carbón / Cemento / Ceniza volante / Cosméticos / Cuarzo / Especias / Feldespato / Fertilizante / Frita de esmalte / Grafito / Granos y alimento balanceado / Harina / Jabón y detergentes / Mica / Mineral de hierro / Negro de humo / Papel / Pigmentos de pintura / Pizarra / Plásticos / Polvo de cuero / Polvo de roca / Sulfato de hierro / Sílice / Tabaco / Talco / Yeso / Óxido de hierro / Óxido de plomo / Óxido de zinc / Fino — 1.0 m/min (criterio original) / Grueso — 2.5 m/min (criterio original) / Capturar relación aire/tela |  |
| Filtro | Tipo de limpieza y medio filtrante |  | Pulse jet, fieltro | Opciones: Pulse jet, fieltro / Sacudido o aire inverso, tela tejida |  |
| Filtro | Relación aire/tela capturada | m/min | 0 | ≥ 0 | Si se captura (> 0) tiene prioridad sobre la lista. Depende del polvo, de la limpieza y de la temperatura. |
| Pérdidas | Pérdida de presión en filtro de mangas | mm H₂O | obligatorio | ≥ 0 | El original indicaba 100–150 mm H₂O. |
| Pérdidas | Pérdida de presión en ductos | mm H₂O | obligatorio | ≥ 0 | El original indicaba 25–50 mm H₂O. Puede calcularse con la calculadora de ductos. |
| Pérdidas | Pérdida de presión en ciclón | mm H₂O | 0 | ≥ 0 | El original indicaba 30–100 mm H₂O. 0 si no hay ciclón. |
| Ventilador | Eficiencia del ventilador | % | 80 | > 0 y ≤ 100 |  |
| Almacenamiento | Concentración de polvo en el aire | g/m³ | 0 | ≥ 0 | 0 = no calcular el almacenamiento. |
| Almacenamiento | Eficiencia de captación | % | 100 | > 0 y ≤ 100 |  |
| Almacenamiento | Densidad aparente del polvo captado | kg/m³ | 0 | ≥ 0 |  |
| Almacenamiento | Tiempo de almacenamiento en tolva | h | 12 | > 0 |  |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Diámetro del ducto de entrada | 420.5 | mm | V |
| Relación aire/tela usada | 1.20 | m/min | D |
| Relación aire/tela usada | 3.94 | ft/min | D |
| Área de filtración | 138.89 | m² | D |
| Pérdida de presión total | 200.0 | mm H₂O | D |
| Pérdida de presión total | 1 961.3 | Pa | D |
| Potencia al eje del ventilador | 6.810 | kW | V |
| Potencia al eje del ventilador | 9.133 | HP | D |
| Polvo captado | 99.00 | kg/h | V |
| Volumen de polvo en 12 h | 1.080 | m³ | V |

**Ecuaciones**

```
ṁ_polvo = Q·c·η_captación;   V = ṁ_polvo·t/ρ_aparente
D = √(4·Q/(π·v))
A_filtración = Q[m³/min] / relación aire-tela[m/min]
ΔP[Pa] = ΔP[mm H₂O]·9.80665;   P = ΔP·Q/η
```

**Referencias**

- Potencia de ventilador: P = ΔP·Q/η (mecánica de fluidos).
- Relación aire/tela: EPA Air Pollution Control Cost Manual (EPA/452/B-02-001), sección 6, cap. 1, tabla 1.1 (Turner et al.).
- Validación: tests/test_colector.py (tabla 1.1 y ejemplo de la tabla 1.3 de la EPA).

**Limitaciones**

- Valores EPA: generalmente seguros; afinar con el fabricante según tamaño de partícula, carga de polvo y temperatura.
- Pérdidas de presión del filtro, ductos y ciclón: datos del usuario.
- Sacudido y aire inverso: no se calculan los compartimentos fuera de línea (área bruta).

<a id="soplador"></a>
### Soplador  (`soplador`)

Potencia al eje (adiabática e incompresible), diámetro de tubería y tipo orientativo.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo de soplador Rev 0.py, Calculo de soplador Rev 1.py, Calculo de soplador Rev 2.py
- Abrir directamente: `python menu_principal.py --calculadora soplador`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/soplador.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Datos de entrada | Tipo de máquina |  | Dinámico (centrífugo, canal lateral) o con compresión interna (tornillo) | Opciones: Dinámico (centrífugo, canal lateral) o con compresión interna (tornillo) / Desplazamiento positivo de lóbulos (Roots): compresión externa |  |
| Datos de entrada | Caudal de aire a condiciones de succión | m³/h | obligatorio | > 0 |  |
| Datos de entrada | Presión diferencial | Pa | obligatorio | > 0 |  |
| Datos de entrada | Velocidad del aire en la tubería | m/s | 20 | > 0 | Valor por defecto del original (Rev 0). |
| Datos de entrada | Eficiencia del soplador (0–1) |  | 0.8 | > 0 y ≤ 1 | 0.8 era la constante del original. |
| Datos de entrada | Altitud del sitio | m | 0.0 | ≥ -500 y ≤ 5000 | Define la presión absoluta de succión (succión atmosférica). |
| Datos de entrada | Temperatura del aire en la succión | °C | 20 | ≥ -40 y ≤ 200 |  |
| Datos de entrada | Relación de calores específicos k |  | 1.4 | > 1 y ≤ 1.7 |  |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Presión absoluta de succión | 101.33 | kPa | D |
| Relación de presiones p₂/p₁ | 1.0493 |  | V |
| Flujo másico de aire | 1 204.2 | kg/h | V |
| Potencia al eje recomendada para el tipo de máquina | 1.706 | kW | V |
| Potencia al eje recomendada | 2.288 | HP | D |
| Potencia al eje (compresión adiabática) | 1.706 | kW | V |
| Potencia al eje (adiabática) | 2.288 | HP | D |
| Potencia al eje (Q·Δp/η: isocórica, lóbulos) | 1.736 | kW | V |
| Temperatura de descarga (balance de energía, carcasa adiabática) | 25.1 | °C | V |
| Diámetro de la tubería | 133.0 | mm | V |
| Tipo de soplador sugerido | Soplador centrífugo |  | O |

**Ecuaciones**

```
P_incompresible = ΔP·Q/η
P_adiabática = k/(k−1)·p₁·Q₁·[(p₂/p₁)^((k−1)/k) − 1]/η
ṁ = p₁·Q₁/(R·T₁);   T₂ = T₁ + P_eje/(ṁ·cp),   cp = k·R/(k−1)
D = √(4·Q/(π·v))
```

**Advertencias que emite con el caso de prueba**

- La clasificación del tipo de soplador es orientativa (criterio original sin fuente). Seleccione el equipo con curvas del fabricante.

**Referencias**

- Compresión adiabática de gas ideal (termodinámica clásica).
- Sopladores de lóbulos: compresión externa isocórica, P = Q₁·Δp (Leybold, Vacuum Fundamentals; Atlas Copco, «Screw versus Roots technology in low pressure blowers»).
- Validación: tests/test_soplador.py (ruta independiente por entalpía y ejemplo Atlas Copco).

**Limitaciones**

- Tipo de soplador sugerido: criterio original sin fuente (nivel O).
- La temperatura de descarga supone carcasa adiabática (sin pérdidas de calor): es conservadora.
- La eficiencia debe tomarse de la curva del fabricante.

## Máquinas de fluido y bombeo

<a id="bomba"></a>
### Bomba centrífuga  (`bomba`)

Altura dinámica total, potencia hidráulica y al freno, NPSH disponible y curva del sistema.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo de bomba cemtrifuga.py, Calculo de bomba cemtrifuga rev1.py, Calculo de bomba cemtrifuga rev2.py, Calculo de bomba cemtrifuga rev3.py, Calculo de bomba cemtrifuga rev4.py, Calculo de bomba cemtrifuga rev5.py, Calculo de bomba cemtrifuga rev6.py
- Abrir directamente: `python menu_principal.py --calculadora bomba`
- Esquema ajustable (pestaña «Esquema»): no (decisión del usuario)

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Sistema | Caudal | gpm | obligatorio | > 0 |  |
| Sistema | Diámetro interior real de la tubería | in | obligatorio | > 0 | Diámetro interior según cédula, no el nominal. |
| Sistema | Longitud de tubería | ft | obligatorio | ≥ 0 |  |
| Sistema | Diferencia de elevación estática (descarga − succión) | ft | 0 |  | Positiva si el punto de descarga está más alto que la superficie del líquido en la succión. |
| Sistema | Presión manométrica requerida en la descarga | psig | 0 |  | Antes «presión disponible»: el original la sumaba a la altura. |
| Sistema | Presión manométrica en la superficie de succión | psig | 0 |  |  |
| Líquido | Gravedad específica del líquido |  | 1.0 | > 0 y ≤ 3 |  |
| Líquido | Viscosidad cinemática | cSt | 1.0 | > 0 | Agua a 20 °C ≈ 1.0 cSt. |
| Líquido | Temperatura del líquido | °C | 20 | ≥ 0 y ≤ 150 | Para la presión de vapor del agua en el NPSH. |
| Líquido | Presión de vapor del líquido | psia | 0 | ≥ 0 | 0 = presión de vapor del agua a la temperatura dada. |
| Fricción | Rugosidad absoluta | in | 0.0018 | ≥ 0 | 0.0018 in (0.045 mm): acero comercial, diagrama de Moody. |
| Fricción | Factor de fricción de Darcy fijo |  | 0 | ≥ 0 y ≤ 0.2 | 0 = Colebrook. El original usaba 0.02 fijo. |
| Accesorios | Codos de 90° estándar (L/D 30) |  | 0 | ≥ 0 |  |
| Accesorios | Codos de 90° de radio largo (L/D 20) |  | 0 | ≥ 0 |  |
| Accesorios | Codos de 45° (L/D 16) |  | 0 | ≥ 0 |  |
| Accesorios | Tees con flujo por la derivación (L/D 60) |  | 0 | ≥ 0 |  |
| Accesorios | Tees con flujo directo (L/D 20) |  | 0 | ≥ 0 |  |
| Accesorios | Válvulas de bloqueo |  | 0 | ≥ 0 |  |
| Accesorios | Tipo de válvula de bloqueo |  | Compuerta, abierta (L/D 8) | Opciones: Compuerta, abierta (L/D 8) / Bola, paso completo (L/D 3) / Mariposa ≤ 8 plg (L/D 45) / Globo, abierta (L/D 340) / Ángulo, abierta (L/D 150) / De pie con criba, disco con bisagra (L/D 75) |  |
| Accesorios | Válvulas de retención de columpio (L/D 100) |  | 0 | ≥ 0 |  |
| Accesorios | Entradas desde depósito (K 0.5) |  | 0 | ≥ 0 |  |
| Accesorios | Descargas a depósito (K 1.0) |  | 0 | ≥ 0 |  |
| Accesorios | Número de reducciones |  | 0 | ≥ 0 |  |
| Accesorios | K por codo de 90° estándar (capturado) |  | 0 | ≥ 0 | 0 = Crane (30·f_T). El original usaba 0.5 sin fuente. |
| Accesorios | K por válvula de bloqueo (capturado) |  | 0 | ≥ 0 | 0 = Crane según el tipo. El original usaba 1.0 sin fuente; con Cv: K = 891·d⁴/Cv² (d en plg). |
| Accesorios | K por tee de derivación (capturado) |  | 0 | ≥ 0 | 0 = Crane (60·f_T). El original usaba 1.8 sin fuente. |
| Accesorios | K por reducción |  | 0.8 | ≥ 0 | Valor original 0.8, sin fuente. Capture el K de Crane para la relación de diámetros y el ángulo. |
| Equipos | Número de cribas |  | 0 | ≥ 0 |  |
| Equipos | Número de limpiadores |  | 0 | ≥ 0 |  |
| Equipos | Número de limpiadores de alta densidad |  | 0 | ≥ 0 |  |
| Equipos | Número de limpiadores reversos |  | 0 | ≥ 0 |  |
| Equipos | Pérdida por criba | ft | 30 | ≥ 0 | Valor original. |
| Equipos | Pérdida por limpiador | ft | 35 | ≥ 0 | Valor original. |
| Equipos | Pérdida por limpiador de alta densidad | ft | 35 | ≥ 0 | Valor original. |
| Equipos | Pérdida por limpiador reverso | ft | 25 | ≥ 0 | Valor original. |
| Bomba | Eficiencia de la bomba | % | 0 | ≥ 0 y ≤ 100 | De la curva del fabricante. 0 = solo potencia hidráulica. |
| NPSH | Altitud del sitio | m | 0.0 | ≥ -500 y ≤ 5000 |  |
| NPSH | Elevación del líquido sobre el eje de la bomba | ft | 0 |  | Positiva con succión ahogada (tanque arriba); negativa con succión negativa. |
| NPSH | Pérdidas en la línea de succión | ft | 0 | ≥ 0 |  |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Velocidad en la tubería | 7.88 | ft/s | V |
| Número de Reynolds | 487 824 |  | V |
| Factor de fricción de Darcy (turbulento) | 0.01569 |  | V |
| Pérdida por fricción en tubería | 3.40 | ft | V |
| Factor de fricción en turbulencia completa f_T (Crane) | 0.0141 |  | V |
| Suma de coeficientes K de accesorios | 3.51 |  | O |
| Pérdida en accesorios | 3.39 | ft | O |
| Pérdida en equipos (cribas, limpiadores) | 30.00 | ft | O |
| Altura estática por elevación | 20.00 | ft | D |
| Altura por diferencia de presión | 32.33 | ft | V |
| Altura dinámica total (TDH) | 89.12 | ft | V |
| Altura dinámica total (TDH) | 27.16 | m | D |
| Potencia hidráulica | 27.77 | HP | V |
| Potencia al freno (eje de la bomba) | 37.03 | HP | V |
| Potencia al freno | 27.61 | kW | D |
| Presión atmosférica del sitio | 11.190 | psia | D |
| Presión de vapor usada | 0.3392 | psia | D |
| NPSH disponible | 28.05 | ft | V |
| NPSH disponible | 8.55 | m | D |

**Ecuaciones**

```
v = Q·0.002228/A;   h_f = f·(L/D)·v²/(2g);   h_k = ΣK·v²/(2g)
Crane TP-410: K = (L/D)·f_T;   f_T = 0.25/[log10(ε/(3.7·D))]²
TDH = Δz + (p_d − p_s)·2.309/GE + h_f + h_k + h_equipos
WHP = Q[gpm]·TDH[ft]·GE/3960;   BHP = WHP/η
NPSHa = (p_atm + p_s − p_vap)·2.309/GE + z_s − h_f,s
```

**Advertencias que emite con el caso de prueba**

- K de reducciones: valor del original sin fuente (0.8 por defecto). Calcúlelo con Crane TP-410 para la relación de diámetros y el ángulo reales.
- Pérdidas en cribas y limpiadores: valores del original sin fuente. Confírmelas con el fabricante.

**Referencias**

- Darcy-Weisbach, Colebrook-White y ecuación de energía.
- Crane Co., Flow of Fluids Through Valves, Fittings and Pipe, TP-410: K = (L/D)·f_T, tabla de f_T y L/D de codos, tees y válvulas (reproducidos en Machinery's Handbook, tabla de L/D).
- NPSH disponible: definición del Hydraulic Institute; ejemplos de J. Elsey, «NPSHa Basics», Pumps & Systems (2022).

**Limitaciones**

- Fluido newtoniano, flujo incompresible, tubería de diámetro único.
- Validado: f_T contra la tabla Crane, K de válvula de globo contra Pumps & Systems, NPSHa contra los ejemplos 1–3 de Pumps & Systems (tests/test_bomba.py).
- Reducciones y pérdidas por equipo: valores del original sin fuente (nivel O).
- Curva del sistema: pérdidas en equipos supuestas proporcionales a Q² (confirmar con el fabricante).

<a id="vacio"></a>
### Bomba de vacío  (`vacio`)

Potencia de compresión de la presión de vacío a la atmosférica y ducto de succión.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: calculo de bomba de vacio.py, calculo de bomba de vacio rev1.py
- Abrir directamente: `python menu_principal.py --calculadora vacio`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/vacio.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Bomba | Caudal a condiciones de succión |  | obligatorio | > 0 |  |
| Bomba | Unidad del caudal |  | CFM (ft³/min) | Opciones: CFM (ft³/min) / m³/h |  |
| Bomba | Presión absoluta de succión | kPa | obligatorio | > 0 |  |
| Bomba | Presión absoluta de descarga | kPa | 0 | ≥ 0 | 0 = presión atmosférica del sitio (por altitud). |
| Bomba | Altitud del sitio | m | 0.0 | ≥ -500 y ≤ 5000 |  |
| Bomba | Temperatura del gas en la succión | °C | 20 | ≥ -40 y ≤ 200 |  |
| Bomba | Eficiencia global (0–1) |  | 0.85 | > 0 y ≤ 1 | 0.85 era la constante del original. Use el dato del fabricante. |
| Bomba | Relación de calores específicos k |  | 1.4 | > 1 y ≤ 1.7 |  |
| Ducto | Velocidad en el ducto de succión | m/s | 0 | ≥ 0 | 0 = usar la tabla de velocidades por presión del original (sin fuente). |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Caudal a succión | 169.90 | m³/h | D |
| Presión absoluta de descarga | 101.33 | kPa | D |
| Relación de compresión pd/ps | 10.13 |  | V |
| Flujo másico de aire seco | 20.191 | kg/h | V |
| Potencia teórica adiabática | 1.549 | kW | V |
| Potencia teórica isotérmica (mínima ideal) | 1.093 | kW | V |
| Potencia al eje (adiabática/η) | 1.823 | kW | V |
| Potencia al eje | 2.444 | HP | D |
| Tipo de bomba sugerido | Bomba de tornillo |  | O |
| Velocidad en ducto de succión | 6.50 | m/s | O |
| Diámetro del ducto de succión | 96.1 | mm | V |

**Ecuaciones**

```
P = k/(k−1)·ps·Qs·[(pd/ps)^((k−1)/k) − 1]/η
P_iso = ps·Qs·ln(pd/ps)
ṁ = ps·Qs/(R·T)
D = √(4·Qs/(π·v))
```

**Advertencias que emite con el caso de prueba**

- Velocidad del ducto tomada de la tabla original por rangos de presión (sin fuente).
- Tipo de bomba: criterio original sin fuente. Verifique con curvas del fabricante.

**Referencias**

- Compresión adiabática e isotérmica de gas ideal.
- Presión atmosférica: ASHRAE Fundamentals, cap. 1, ec. 3.
- Validación de la potencia: tests/test_vacio.py (ruta independiente por entalpía e integral p·dV).

**Limitaciones**

- Validada solo la potencia de compresión de gas ideal (adiabática e isotérmica).
- Tipo de bomba y velocidades de ducto: criterios originales sin fuente (nivel O).
- La tabla «Tabla aplicación Bomba de vacio.png» (F:\) no está en el proyecto.

## Térmica y transferencia de calor

<a id="torre"></a>
### Torre de enfriamiento  (`torre`)

Carga térmica, aproximación al bulbo húmedo, flujo de aire por balance de entalpía y evaporación.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo de torre de enfriamiento rev0.py, Calculo de torre de enfriamiento rev1.py
- Abrir directamente: `python menu_principal.py --calculadora torre`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/torre.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Agua | Flujo de agua | kg/s | obligatorio | > 0 |  |
| Agua | Temperatura del agua caliente (entrada) | °C | obligatorio | ≥ 0 y ≤ 100 |  |
| Agua | Temperatura del agua fría (salida) | °C | obligatorio | ≥ 0 y ≤ 100 |  |
| Agua | Calor específico del agua | kJ/(kg·K) | 4.186 | ≥ 3.5 y ≤ 4.5 |  |
| Aire | Bulbo húmedo de diseño del aire de entrada | °C | 0 | ≥ 0 y ≤ 40 | 0 = no calcular la aproximación ni el aire. |
| Aire | Bulbo seco del aire de entrada | °C | 0 | ≥ 0 y ≤ 55 | Con bulbo seco y húmedo se usa el estado real del aire. 0 = aire saturado al bulbo húmedo. |
| Aire | Temperatura del aire de salida | °C | 0 | ≥ 0 y ≤ 100 | Supuesto de diseño. 0 = no calcular el flujo de aire. |
| Aire | Humedad relativa del aire de salida | % | 100 | ≥ 50 y ≤ 100 | 100 = saturado (supuesto usual). |
| Aire | Relación L/G de diseño (capturada) |  | 0 | ≥ 0 y ≤ 5 | 0 = calcular L/G con la temperatura del aire de salida. Si > 0 tiene prioridad. |
| Aire | Altitud del sitio | m | 0.0 | ≥ -500 y ≤ 5000 |  |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Rango de enfriamiento | 6.00 | °C | D |
| Carga térmica | 251.16 | kW | V |
| Carga térmica | 856 993 | BTU/h | D |
| Carga térmica | 71.42 | TR | D |
| Aproximación (T salida − bulbo húmedo) | 5.00 | °C | V |
| Entalpía del aire de entrada (bulbo seco y húmedo) | 71.86 | kJ/kg a.s. | V |
| Humedad absoluta del aire de entrada | 0.01549 | kg/kg a.s. | V |
| Entalpía del aire de salida (100 % HR) | 105.07 | kJ/kg a.s. | V |
| Humedad absoluta del aire de salida | 0.02888 | kg/kg a.s. | V |
| Flujo de aire seco | 7.952 | kg/s | V |
| Relación L/G (agua/aire seco) | 1.258 |  | V |
| Caudal de aire a la entrada | 7.045 | m³/s | V |
| Caudal de aire a la salida | 7.169 | m³/s | V |
| Agua evaporada (= agua de reposición sin purga ni arrastre) | 383.1 | kg/h | V |
| Agua evaporada | 0.1064 | kg/s | D |
| Evaporación respecto al flujo de agua | 1.06 | % | V |
| Característica requerida KaV/L (Merkel, Chebyshev 4 puntos) | 1.074 |  | E |
| KaV/L por integración numérica (verificación) | 1.075 |  | V |
| Diferencia de entalpía mínima en los puntos de Chebyshev | 22.64 | kJ/kg a.s. | V |
| Tipo de torre sugerido | Torre mediana (flujo cruzado) |  | O |

**Ecuaciones**

```
Q = ṁ_agua·cp·(T_entrada − T_salida)
ṁ_aire = ṁ_agua·cp·ΔT / [(h₂ − h₁) − (ω₂ − ω₁)·h_f(T_fría)]
ṁ_evap = ṁ_aire·(ω₂ − ω₁);   V̇₁ = ṁ_aire·v₁
KaV/L = ∫ cp·dT/(h_w − h_a) ≈ cp·R/4·Σ 1/(h_w − h_a) en T_fría + (0.1, 0.4, 0.6, 0.9)·R
h_a = h_entrada + (L/G)·cp·(T − T_fría)
```

**Referencias**

- Psicrometría: ASHRAE Handbook — Fundamentals, cap. 1.
- Merkel (1925); método de Chebyshev de 4 puntos (CTI; Perry's Chemical Engineers' Handbook, sec. 12).
- Balance de masa y energía con agua de reposición: Çengel y Boles, Termodinámica, cap. 14 (torre de enfriamiento húmeda).

**Limitaciones**

- No dimensiona el relleno ni la torre: requiere curvas del fabricante o del CTI.
- Aire de salida a la temperatura y humedad relativa capturadas (100 % = saturado).

<a id="secador"></a>
### Secador rotatorio directo  (`secador`)

Balances de masa y energía, psicrometría del aire, diámetro, longitud por Ua y combustible.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: calculo del secador.py, calculo del secador rev 1.py, calculo del secador rev 2.py, calculo del secador DS rev 3.py, calculo del secador DS rev 4.py, calculo del secador DS rev 5.py, calculo del secador DS rev 6.py, calculo del secador DS rev 7.py
- Abrir directamente: `python menu_principal.py --calculadora secador`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/secador.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Producto | Alimentación húmeda | kg/h | obligatorio | > 0 |  |
| Producto | Base de la humedad |  | Base húmeda (% del peso total) | Opciones: Base húmeda (% del peso total) / Base seca (kg agua / kg sólido seco × 100) | Rev0–rev2 usaban base húmeda; la serie DS no lo definía. |
| Producto | Humedad inicial | % | obligatorio | ≥ 0 |  |
| Producto | Humedad final | % | obligatorio | ≥ 0 |  |
| Producto | Calor específico del sólido seco | kJ/(kg·K) | obligatorio | > 0 y ≤ 5 |  |
| Producto | Temperatura del sólido a la entrada | °C | obligatorio | ≥ -20 y ≤ 300 |  |
| Producto | Temperatura del sólido a la salida | °C | obligatorio | ≥ -20 y ≤ 300 |  |
| Aire | Temperatura del aire a la entrada del secador | °C | obligatorio | ≥ 0 y ≤ 900 |  |
| Aire | Temperatura del aire a la salida | °C | obligatorio | ≥ 0 y ≤ 900 |  |
| Aire | Disposición de los flujos |  | Flujo paralelo (aire y sólido en el mismo sentido) | Opciones: Flujo paralelo (aire y sólido en el mismo sentido) / Contracorriente (aire en sentido opuesto al sólido) | Solo cambia ΔT_ml (longitud). Los balances de masa y energía son los mismos en ambos casos. |
| Aire | Temperatura del aire ambiente | °C | obligatorio | ≥ -20 y ≤ 50 |  |
| Aire | Humedad relativa ambiente | % | obligatorio | ≥ 0 y ≤ 100 |  |
| Aire | Altitud del sitio | m | 0.0 | ≥ -500 y ≤ 5000 |  |
| Aire | Calor latente de vaporización | kJ/kg | 0 | ≥ 0 | 0 = 2501 − 2.326·t evaluado al bulbo húmedo del aire de entrada. |
| Aire | Pérdidas de calor por la envolvente | % del calor útil | 20 | ≥ 0 y ≤ 100 | 20 % era el criterio del original (Q_total = 1.2·Q). |
| Dimensiones | Velocidad permisible del gas en el tambor | m/s | obligatorio | > 0 y ≤ 10 | Perry's: típica 3 m/s en flujo paralelo, 2 m/s a contracorriente. |
| Dimensiones | Fracción de la sección libre para el gas |  | 1.0 | > 0 y ≤ 1 | 1 = toda la sección. (El «9» de la serie DS equivalía a 0.444 sin documentar.) |
| Dimensiones | Coeficiente volumétrico Ua |  | Correlación de Perry's: Ua = 0.5·G^0.67/D (unidades inglesas) | Opciones: Correlación de Perry's: Ua = 0.5·G^0.67/D (unidades inglesas) / Capturar Ua |  |
| Dimensiones | Ua capturado | W/(m³·K) | 0 | ≥ 0 |  |
| Combustible | Poder calorífico inferior del combustible | kJ/kg | 0 | ≥ 0 | 0 = no calcular el combustible. |
| Combustible | Eficiencia del calentador | % | 0 | ≥ 0 y ≤ 100 |  |
| Combustible | Masa de combustible por galón | kg/gal | 0 | ≥ 0 | Para reportar gal/h y L/h. 0 = solo kg/h. |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Sólido seco | 3 311.97 | kg/h | V |
| Agua en la alimentación | 451.63 | kg/h | V |
| Agua en el producto | 102.43 | kg/h | V |
| Producto a la salida | 3 414.40 | kg/h | V |
| Agua evaporada | 349.20 | kg/h | V |
| Humedad absoluta del aire de entrada | 0.00912 | kg/kg a.s. | V |
| Bulbo húmedo del aire de entrada (T de evaporación) | 55.78 | °C | V |
| Calor latente usado | 2 371.3 | kJ/kg | D |
| Calor para calentar el sólido | 46.37 | kW | V |
| Calor para calentar el agua residual | 7.15 | kW | V |
| Calor para evaporar y sobrecalentar el vapor | 254.32 | kW | V |
| Calor útil | 307.84 | kW | V |
| Pérdidas de calor | 61.57 | kW | O |
| Calor total que cede el aire | 369.40 | kW | V |
| Flujo de aire seco | 4 482.7 | kg/h | V |
| Humedad absoluta del aire de salida | 0.08702 | kg/kg a.s. | V |
| Humedad relativa del aire de salida | 6.9 | % | V |
| Punto de rocío del aire de salida | 45.7 | °C | V |
| Caudal de gas de diseño (mayor entre entrada y salida) | 3.018 | m³/s | V |
| Diámetro interior del tambor | 1.132 | m | V |
| Flujo másico de gas por área | 4 456 | kg/(h·m²) | V |
| Coeficiente volumétrico Ua | 241.4 | W/(m³·K) | E |
| Diferencia media logarítmica (flujo paralelo) | 137.85 | °C | V |
| Volumen del tambor | 9.25 | m³ | E |
| Longitud del tambor | 9.19 | m | E |
| Relación L/D | 8.12 |  | E |
| Calor del calentador (aire ambiente → entrada) | 484.05 | kW | V |
| Eficiencia térmica (calor útil / calentador) | 63.6 | % | V |
| Consumo de combustible | 48.81 | kg/h | V |
| Consumo de combustible | 15.25 | gal/h | D |
| Consumo de combustible | 57.74 | L/h | D |
| Potencia estimada (fórmula rev0, con D real en ft) | 1.48 | HP | O |
| Número de aletas (criterio rev0: 2.63·D) | 3.0 |  | O |
| Altura de aletas (criterio rev0: 4.6·D) | 5.2 | cm | O |

**Ecuaciones**

```
Base húmeda: ms = F·(1 − xi);  agua_f = ms·xf/(1 − xf);  W = F·xi − agua_f
Q_útil = ms·cps·ΔTs + agua_f·cpw·ΔTs + W·[cpw·(t_ev − Ts1) + λ + cpv·(Tg2 − t_ev)]
G = Q_total/((1.006 + 1.86·W_in)·(Tg1 − Tg2));   W_out = W_in + W/G
D = √(4·Q_gas/(π·v·φ_libre));   V = Q_útil/(Ua·ΔT_ml);   L = V/A
ΔT_ml: paralelo (Tg1 − Ts1, Tg2 − Ts2);  contracorriente (Tg1 − Ts2, Tg2 − Ts1)
Ua = 0.5·G^0.67/D [Btu/(h·ft³·°F), G en lb/(h·ft²), D en ft] (Perry's)
Q_calentador = G·cp_h·(Tg1 − T_amb);   ṁ_comb = Q_calentador/(PCI·η)
```

**Advertencias que emite con el caso de prueba**

- Ua por la correlación de Perry's (McCormick): estimación preliminar; depende de aletas, rpm y carga del tambor. Confírmelo con el fabricante o con pruebas.
- Potencia de accionamiento y aletas: fórmulas originales sin fuente; NO validadas. El tiempo de residencia y la pendiente no se calculan (correlación de Friedman-Marshall pendiente de verificar contra Perry's).

**Referencias**

- Perry's Chemical Engineers' Handbook, secadores rotatorios: Ua = 0.5·G^0.67/D (estimación), L/D entre 5 y 10, velocidad típica del gas.
- Pacheco y Stella, Braz. J. Chem. Eng.: Ua = 244.7·G^0.67/D en SI (contraste de la conversión).
- Psicrometría: ASHRAE Handbook — Fundamentals, cap. 1.
- Geankoplis, Transport Processes and Unit Operations, 3.ª ed., Ej. 9.10-2 «Heat Balance on a Dryer» (validación de los balances: G = 1 171 kg a.s./h, H = 0.0247).

**Limitaciones**

- Validada para balances de masa y energía, flujo de aire seco y humedad de salida.
- Diámetro, longitud y Ua: estimación preliminar (Ua empírico); sin tiempo de residencia; potencia y aletas sin validar.

## Estructural

<a id="viga"></a>
### Viga en voladizo o simplemente apoyada  (`viga`)

Reacciones, cortante, momento, deflexión y esfuerzos para carga puntual y uniforme.

- Estado de auditoría: **CORREGIDA**
- Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS**
- Sustituye a: Calculo de Cantiliver.py, Calculo de Cantiliver rev1.py, Calculo de Cantiliver rev2.py
- Abrir directamente: `python menu_principal.py --calculadora viga`
- Esquema ajustable (pestaña «Esquema»): sí — captura en `docs/capturas/esquemas/viga.png`

**Datos de entrada**

| Grupo | Dato | Unidad | Por defecto | Rango | Ayuda |
|---|---|---|---|---|---|
| Viga | Tipo de viga |  | Voladizo (empotrada en x = 0) | Opciones: Voladizo (empotrada en x = 0) / Simplemente apoyada (apoyos en x = 0 y x = L) |  |
| Viga | Longitud L | m | obligatorio | > 0 |  |
| Cargas | Carga puntual P | kg | 0 | ≥ 0 | Masa; se convierte a N con g = 9.80665 m/s². |
| Cargas | Posición de la carga puntual (desde x = 0) | m | 0 | ≥ 0 | Voladizo: distancia desde el empotramiento. Simple: desde el apoyo izquierdo. |
| Cargas | Carga distribuida uniforme w (en toda la longitud) | kg/m | 0 | ≥ 0 | Incluya aquí el peso propio si desea considerarlo. |
| Material | Material (módulo E) |  | Acero | Opciones: Acero / Aluminio / Madera / Bronce / Hierro / Personalizado (capturar E) |  |
| Material | Módulo de elasticidad E | GPa | 0 | ≥ 0 | Un valor capturado tiene prioridad sobre la lista. 0 = valor de la lista del original (nivel O). |
| Sección | Sección transversal |  | Rectangular maciza | Opciones: Rectangular maciza / Circular maciza / Tubo circular / I simétrica / Personalizada (I, c, A) |  |
| Sección | Ancho b (rectangular o patín de la I) | mm | 0 | ≥ 0 |  |
| Sección | Peralte h (rectangular o I) | mm | 0 | ≥ 0 |  |
| Sección | Diámetro exterior d (circular o tubo) | mm | 0 | ≥ 0 |  |
| Sección | Espesor de pared t (tubo) | mm | 0 | ≥ 0 |  |
| Sección | Espesor del patín tf (I) | mm | 0 | ≥ 0 |  |
| Sección | Espesor del alma tw (I) | mm | 0 | ≥ 0 |  |
| Sección | Momento de inercia I (personalizada) | cm⁴ | 0 | ≥ 0 |  |
| Sección | Distancia a la fibra extrema c (personalizada) | mm | 0 | ≥ 0 |  |
| Sección | Área A (personalizada) | cm² | 0 | ≥ 0 |  |
| Sección | Fabricación del perfil I |  | Laminado (rolado) | Opciones: Laminado (rolado) / Soldado (placas) |  |
| Propiedades del manual (I) | Ix del manual (perfil I) | cm⁴ | 0 | ≥ 0 | 0 = calcular con las placas (sin filetes). Para perfiles laminados capture las del manual IMCA/AISC. |
| Propiedades del manual (I) | Área A del manual | cm² | 0 | ≥ 0 |  |
| Propiedades del manual (I) | Zx del manual | cm³ | 0 | ≥ 0 |  |
| Propiedades del manual (I) | Sx del manual | cm³ | 0 | ≥ 0 |  |
| Propiedades del manual (I) | Iy del manual | cm⁴ | 0 | ≥ 0 |  |
| Propiedades del manual (I) | J (constante de torsión) del manual | cm⁴ | 0 | ≥ 0 |  |
| Propiedades del manual (I) | Cw (constante de alabeo) del manual | cm⁶ | 0 | ≥ 0 |  |
| Revisión por norma (acero) | Revisión de resistencia |  | AISC 360-22 y NTC-DCEA | Opciones: AISC 360-22 y NTC-DCEA / AISC 360-22 (LRFD) / NTC-DCEA (CDMX) / Ninguna (solo análisis elástico) |  |
| Revisión por norma (acero) | Esfuerzo de fluencia Fy | MPa | 0 | ≥ 0 | Ej.: ASTM A36 = 250 MPa; ASTM A992 / A572 Gr. 50 = 345 MPa. Obligatorio si se revisa por norma. |
| Revisión por norma (acero) | Factor de carga para resistencia (LRFD) |  | 0 | ≥ 0 | Multiplica las cargas capturadas (de servicio) para obtener Mu y Vu. Use el de la combinación aplicable de su norma de cargas; la deflexión se calcula con las cargas sin factorizar. |
| Revisión por norma (acero) | Soporte lateral del patín comprimido |  | Solo en apoyos (sin soportes intermedios) | Opciones: Solo en apoyos (sin soportes intermedios) / Continuo (losa o cubierta conectada) / En puntos equidistantes (capturar número de tramos) |  |
| Revisión por norma (acero) | Número de tramos entre soportes laterales |  | 2 | ≥ 2 y ≤ 20 | Solo con soportes en puntos equidistantes. |
| Revisión | Esfuerzo admisible a flexión | MPa | 0 | ≥ 0 | 0 = no comparar. |
| Revisión | Límite de deflexión L/n (capturar n) |  | 0 | ≥ 0 | Ej. 360 para L/360. 0 = no comparar. |

**Resultados (caso de prueba ordinario de `tests/casos.py`)**

| Resultado | Valor | Unidad | Nivel |
|---|---|---|---|
| Reacción vertical en el empotramiento | 9.807 | kN | V |
| Momento en el empotramiento | 19.613 | kN·m | V |
| Módulo de elasticidad E | 210.0 | GPa | O |
| Momento de inercia I | 6 666.67 | cm⁴ | V |
| Módulo de sección S = I/c | 666.67 | cm³ | V |
| Cortante máximo | 9.807 | kN | V |
| Momento flector máximo | 19.613 | kN·m | V |
| Ubicación del momento máximo | 0.000 | m | V |
| Deflexión máxima | 1.868 | mm | V |
| Ubicación de la deflexión máxima | 2.000 | m | V |
| Esfuerzo máximo de flexión σ = M·c/I | 29.42 | MPa | V |
| Esfuerzo cortante máximo (aprox. según sección) | 0.74 | MPa | V |
| Relación σ/σ_adm | 0.178 |  | V |
| Deflexión permitida L/360 | 5.556 | mm | D |

**Ecuaciones**

```
Voladizo, P en a: y(x) = P·x²(3a − x)/(6EI) para x ≤ a;  P·a²(3x − a)/(6EI) para x ≥ a
Voladizo, w: y(x) = w·x²(6L² − 4Lx + x²)/(24EI)
Simple, P en a (b = L − a): y(x) = P·b·x(L² − b² − x²)/(6·L·EI) para x ≤ a (simétrica para x > a)
Simple, w: y(x) = w·x(L³ − 2Lx² + x³)/(24EI)
σ = M·c/I;   τ_max = k·V/A (k = 1.5 rectangular, 4/3 circular, ≈2 tubo delgado; I: V/(h·tw))
```

**Advertencias que emite con el caso de prueba**

- Sin revisión por norma: no se verifican pandeo lateral-torsional, pandeo local ni cortante del alma. Elija AISC 360-22 o NTC-DCEA para acero estructural.

**Referencias**

- Fórmulas clásicas de vigas de Euler-Bernoulli (resistencia de materiales).
- AISC 360-22, capítulos F y G (LRFD); validado con AISC Design Examples v16.0 (F.1-1B, F.1-2B, F.1-3B, F.3B, G.1B).
- NTC-DCEA, CDMX: secciones 6.2, 6.3 y 7.2 (texto publicado en 2020); verificar contra la edición 2023.

**Limitaciones**

- Elástico lineal, pequeñas deflexiones, sección constante, cargas estáticas.
- Revisión por norma: perfiles I de doble simetría con alma compacta, barras rectangulares y redondas, tubos redondos (AISC); NTC solo perfiles I compactos.
- No revisa conexiones, aplastamiento del alma, atiesadores ni flexocompresión.

