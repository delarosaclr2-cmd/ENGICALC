# Informe técnico de auditoría — Calculadoras de Ingeniería RMR, versión 2.1.0

Fecha: 12/11/2026. Alcance: las 15 calculadoras y el menú del proyecto (47 archivos `.py` originales). Ningún archivo original fue modificado; la versión corregida es una carpeta independiente.

Documentos relacionados:

- `REGISTRO_DE_CAMBIOS.md`: cada error, su corrección y el mapa archivo original → módulo nuevo.
- `EVIDENCIA_ORIGINAL_VS_CORREGIDO.txt`: tabla numérica original / corregido / cálculo independiente.
- `CATALOGO_DE_CALCULADORAS.md`: datos, unidades, rangos, ecuaciones y resultados de cada calculadora (generado del código).
- `FORMULAS_Y_UNIDADES.md`: convenciones, constantes y bases físicas compartidas.
- `RESULTADOS_PRUEBAS.txt`: salida de las pruebas automáticas.
- `PROPUESTA_INTERFAZ_WEB.md`: evaluación para una interfaz web o híbrida futura.

---

## 1. Resumen

| # | Calculadora | Prioridad (Fase 1) | Errores comprobados en el original | Estado de auditoría | Estado de validación |
|---|---|---|---|---|---|
| 1 | Torre de enfriamiento | Crítica | Carga ×1/1000 (rev0), aire sin balance | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0; balance completo y libros en la 2.1.1) |
| 2 | Soplador | Crítica | Potencia ×9.8 | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0) |
| 3 | Colector de polvo | Crítica | Potencia ×9.8, almacenamiento ×10⁴ | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0) |
| 4 | Banda transportadora | Crítica | Área en m, potencia sin física | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0) |
| 5 | Silo metálico | Crítica (seguridad) | Espesor sin presión, presión hidrostática | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0, solo predimensionamiento) |
| 6 | Tolva de dosificación | Crítica | Altura −23 %, flujo /3.66 y modelo de líquido | CORREGIDA | VALIDACIÓN PENDIENTE |
| 7 | Aerodeslizador | Crítica | No era Ergun; aire mal calculado | CORREGIDA | VALIDACIÓN PENDIENTE |
| 8 | Bomba de vacío | Alta | Ecuación de compresión mal planteada (×5 a ×27) | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0, potencia) |
| 9 | Transportador neumático | Alta | Relación de carga sin usar, sin pérdida de sólidos | CORREGIDA | VALIDACIÓN PENDIENTE |
| 10 | Elevador de cangilones | Alta | Truncado −30 %, eficiencia doble/cancelada | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0) |
| 11 | Transportador helicoidal | Alta | Método sin fuente, F y D inconsistentes | CORREGIDA (2.1.0: método KWS/CEMA; el original se conserva para trazabilidad) | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0) |
| 12 | Ductos con polvo | Media | Ninguno de cálculo (9.795 vs 9.80665) | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** |
| 13 | Secador rotatorio | Crítica | DS rev3–7 sin sustento; rev0–2 con errores | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.1, balances; dimensiones preliminares) |
| 14 | Viga | Crítica (seguridad) | Momento ×3, δ ×1.5, σ ×2, I fija | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** |
| 15 | Bomba centrífuga | Alta | Potencia sin η, sin Δz ni NPSH, gráfica incompleta | CORREGIDA | **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (2.1.0) |
| — | Menú | — | Rutas absolutas, revisiones viejas, contraseña en claro | CORREGIDO | Probado (prueba de humo de interfaz) |

**Criterio de estados.** «VALIDADA BAJO CONDICIONES DOCUMENTADAS» se asignó solo cuando (a) todas las salidas principales son de nivel V o D, o de nivel E cuando la correlación publicada se reprodujo con un ejemplo resuelto de su propia fuente (criterio agregado en la 2.1.0, sección 7), (b) cada una se comprobó con un cálculo independiente (fórmula cerrada, integración numérica o tabla publicada) en casos ordinario, límite y extremo, y (c) las condiciones de validez están escritas en la calculadora. Las demás quedan en «VALIDACIÓN PENDIENTE» porque al menos una salida de diseño depende de un criterio original sin fuente (nivel O), de un coeficiente empírico que debe confirmar la empresa, o de un alcance incompleto (p. ej. pandeo en el silo). La parte física que sí se corrigió está verificada y sus pruebas pasan; lo pendiente se lista en la sección 4.

**Ninguna calculadora quedó en «ERROR DETECTADO»**: todos los errores comprobados se corrigieron o se retiraron con justificación.

**Pruebas.** 148 pruebas automáticas pasan (`RESULTADOS_PRUEBAS.txt`): núcleo físico contra tablas y fórmulas independientes, cada calculadora (casos ordinario, límite y extremo, entradas inválidas), reportes PDF/Excel/JSON y la interfaz completa (menú → cada calculadora → calcular → exportar → entradas inválidas) ejecutada en pantalla virtual.

---

## 2. Auditoría por calculadora (formato A–F)

En cada ficha: **A** identificación, **B** funcionamiento actual (nuevo), **C** auditoría (hallazgos del original), **D** validación, **E** mejoras aplicadas, **F** estado. Los datos de entrada completos están en el catálogo.

### 2.1 Torre de enfriamiento

- **A.** Térmica. Original: `Calculo de torre de enfriamiento rev0.py`, `rev1.py` (el menú abría rev0). Nuevo: `calculos/torre.py`.
- **B.** Q = ṁ·cp·ΔT; aire por balance de entalpía con h de entrada ≈ h de saturación al bulbo húmedo (aproximación de Merkel) y aire de salida saturado a la temperatura capturada; relación L/G; evaporación ṁ_aire·ΔW; psicrometría ASHRAE con altitud.
- **C.** Carga ×1/1000 en rev0 (error de unidades); flujo de aire con factores sin balance (1.2·Q o Q/187.5); gráfica de rev1 con /1000; faltaban bulbo húmedo y altitud; clasificación por caudal sin fuente.
- **D.** 10 kg/s, ΔT 6 °C: original 0.25 kW → corregido 251.2 kW = cálculo a mano. Entalpías de saturación contra tabla ASHRAE (25 y 30 °C). Balance ṁ_aire·Δh = Q. Límites: agua fría bajo el bulbo húmedo, rango nulo y aire más caliente que el agua se rechazan.
- **E.** Balance de energía real; datos de aire; advertencias de aproximación; gráfica coherente.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: el tipo de torre es criterio original (O); no dimensiona relleno (requiere curvas del fabricante o CTI); la temperatura del aire de salida es un dato supuesto.

### 2.2 Soplador

- **A.** Máquinas de fluido. Original: `Calculo de soplador Rev 0/1/2.py`. Nuevo: `calculos/soplador.py`.
- **B.** Potencia incompresible ΔP·Q/η y adiabática con p₁ del sitio; diámetro de descarga por velocidad; tipo sugerido.
- **C.** ΔP en Pa dividido entre 102 (×9.8); modelo incompresible a relaciones de presión altas; Rev 0 y Rev 2 clasifican distinto; gráfica «ejemplo».
- **D.** 1 000 m³/h, 5 000 Pa, η 0.8: original 17.02 kW → corregido 1.736 kW (incompresible) y 1.706 kW (adiabática), iguales al cálculo independiente. Caso extremo 80 kPa: advierte compresibilidad.
- **E.** Se corrigió la potencia, se agregó el modelo adiabático y la altitud, se retiró la gráfica sin fuente.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: clasificación de tipo (O). La potencia está verificada.

### 2.3 Colector de polvo

- **A.** Ventilación. Original: `calculo de colector de polvo.py`. Nuevo: `calculos/colector.py`.
- **B.** Diámetro de entrada; área de filtración con relación aire/tela; ΔP total; potencia ΔP·Q/η; polvo capturado y volumen de tolva.
- **C.** Potencia ×9.8; almacenamiento = aire/10 (12 000 m³ de «polvo»); relaciones aire/tela fijas sin fuente.
- **D.** 10 000 m³/h, 200 mm H₂O, η 80 %: 66.8 → 6.81 kW (= independiente). Polvo: 12 000 → 1.08 m³ (10 g/m³, 99 %, 1 100 kg/m³, 12 h). Entradas inválidas rechazadas.
- **E.** Unidades corregidas; balance de polvo; relación aire/tela capturable.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: si se usan los valores 1.0/2.5 m/min del original, el área es nivel O. Con el dato del fabricante el área deja de ser nivel O.

### 2.4 Ductos de aire con polvo

- **A.** Ventilación. Original: `Calculo de dimensionamientos de ductos con polvo.py`. Nuevo: `calculos/ductos.py`.
- **B.** D = √(4Q/πv); densidad por altitud y temperatura; Re con Sutherland; f capturado o Colebrook-White; ΔP de fricción y accesorios; potencia.
- **C.** Sin error de cálculo (método conservado). 9.795 Pa/mm H₂O en lugar de 9.80665; sin accesorios ni velocidad mínima.
- **D.** Cálculo a mano idéntico; coincide con el original dentro de 0.3 %; caso laminar f = 64/Re; Colebrook en el intervalo esperado; densidad a 2 240 m contra p/(RT); entradas inválidas rechazadas.
- **E.** Colebrook, ΣK, altitud, verificación de velocidad mínima de transporte.
- **F.** CORREGIDA / **VALIDADA BAJO CONDICIONES DOCUMENTADAS**: tramo circular, flujo incompresible, carga de polvo baja (sin corrección de densidad de mezcla), K y velocidad mínima suministrados por el usuario (ACGIH).

### 2.5 Banda transportadora

- **A.** Sólidos a granel. Original: `calculo de banda.py` … `Calculo de banda vs5.py`. Nuevo: `calculos/banda.py`.
- **B.** Sección de artesa (trapecio) + sobrecarga parabólica; capacidad; fuerza tangencial por la estructura ISO 5048/DIN 22101 con f y C del usuario; potencia en tambor y motor; potencia de elevación pura como control.
- **C.** «Área» en m (3 456 t/h de arena a 1 m/s); potencia sin fricción ni elevación correctas; velocidad impuesta por el material; tambor y rodillos por tabla.
- **D.** Área contra polígono (artesa) e integración numérica (sobrecarga); capacidad y F_U contra cálculo a mano; caso del original: 3 456 → 678 t/h. Límites: ancho útil > B y banda descendente regenerativa se rechazan.
- **E.** Geometría y resistencias físicas; velocidad capturable.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: f, C, β y holgura de borde deben venir de la norma o el método de la empresa (CEMA, ISO 5048 o DIN 22101); tambor, rodillo y velocidad por tabla son O; sin factor de reducción de sección por inclinación ni tensiones.

### 2.6 Elevador de cangilones

- **A.** Sólidos a granel. Original: `Calculo de Elevador vs1/vs2/vs3.py`. Nuevo: `calculos/elevador.py`.
- **B.** n = 1000/paso; Q = n·v·V·φ·3600; P = ṁ·g·(H + H_carga)/η; relación v²/(g·R).
- **C.** Truncado de cangilones por metro (−30 %); llenado y eficiencia mezclados; η se cancelaba en la potencia; volumen como prisma.
- **D.** Capacidad y potencia contra cálculo a mano; η ya no cambia la capacidad y sí la potencia; relación centrífuga contra fórmula.
- **E.** Separación φ/η; volumen y paso capturables; verificación de descarga centrífuga.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: tablas de pasos, cangilones, velocidades y tambor (O); sin potencia de dragado salvo altura equivalente capturada.

### 2.7 Transportador helicoidal

- **A.** Sólidos a granel. Original: `Calculo del transportador helicoidal.py`. Nuevo: `calculos/helicoidal.py`.
- **B.** Método original: C [lb/h] = Q·f·1000/0.4536, C_v = C/ρ, N = C_v/F, HP = L·(Fd·N + C·Fm)/10⁶·Fo/η.
- **C.** Estructura similar a CEMA 350 pero sin Fb, Ff, Fp y con Fm y Fo constantes; F por capacidad y D por separado; ángulo no usado; tabla de 15 % con posible escalón omitido; fuente «Tabla de HP.png» no disponible.
- **D.** El nuevo código reproduce el algoritmo original transcrito (rpm y HP dentro de 0.2 %). No hay cálculo independiente posible sin la fuente.
- **E.** Factores visibles y editables; F capturable; entradas SI; advertencias.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. **Método no validado**: todas sus salidas son nivel O. Se necesita la fuente original o el manual CEMA 350 para validarlo o sustituirlo.

### 2.8 Aerodeslizador

- **A.** Sólidos a granel / fluidización. Original: `Calculo de Deslizador vs1/vs2.py`. Nuevo: `calculos/aerodeslizador.py`.
- **B.** Capacidad v·b·h·ρ; Ergun por metro de lecho; ΔP de lecho fluidizado ρ_b·g·H; velocidad de mínima fluidización; aire = caudal específico × área de tela.
- **C.** La expresión de ΔP no era Ergun (exponentes y posición de ε erróneos, /10 000 sin origen); aire = sección × velocidad del material; partícula en nm; inclinación sin uso.
- **D.** Ergun contra cálculo a mano; u_mf satisface ΔP_Ergun = ρ_b·g·H; caso sin fluidización advierte; porosidad 1 rechazada.
- **E.** Física de fluidización correcta y unidades de partícula en µm.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: velocidad del material por tabla (O); pérdida de la tela porosa y efecto de la pendiente no incluidos (datos del fabricante).

### 2.9 Transportador neumático

- **A.** Sólidos / neumática. Original: `Calculo transportador neumatico rev 0/rev 1.py`. Nuevo: `calculos/neumatico.py`.
- **B.** D por caudal y velocidad; ρ por altitud; ṁ_s = μ·ṁ_aire; ΔP aire por Colebrook + ΣK; ΔP sólidos = μ·Ks·ΔP_aire; potencia.
- **C.** Relación de carga sin usar; solo fricción del aire con f fijo; fase densa con el mismo modelo; rev 0 con errores de unidades.
- **D.** Balances de masa y presión contra cálculo a mano; sin Ks advierte que las pérdidas están subestimadas; fase densa advierte.
- **E.** Capacidad de sólidos y pérdida de sólidos agregadas.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: Ks debe venir de la referencia de la empresa (p. ej. Mills); sin aceleración ni elevación de sólidos; solo fase diluida.

### 2.10 Tolva de dosificación

- **A.** Sólidos a granel. Original: `calculo de tolva de dosificación.py`. Nuevo: `calculos/tolva.py`.
- **B.** V = m/ρ; altura de tronco de secciones semejantes; ángulos de cara y arista; Beverloo.
- **C.** Altura por área media (−23 %); flujo de líquido con /3.66; ángulo de reposo sin uso; densidades de partícula.
- **D.** Altura 0.98 → 1.27 m (= tronco); Beverloo contra cálculo a mano; descarga mayor que la boca y arqueo rechazados.
- **E.** Geometría, ángulos, Beverloo y su advertencia de aplicabilidad.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: Beverloo **no aplica a polvos finos** (< ~0.4 mm: cemento, cal, caolín); la calculadora lo advierte y el flujo real lo fija el dosificador. Sin análisis de Jenike para flujo másico.

### 2.11 Silo metálico

- **A.** Sólidos / estructural. Original: `Calculo de un silo metalico.py`. Nuevo: `calculos/silo.py`.
- **B.** Geometría con semiángulo de tolva; Janssen (p_h, p_v, p_w, compresión axial por fricción); espesor por tensión circunferencial con factor de descarga, σ_adm, junta, corrosión y mínimo; Beverloo.
- **C.** Espesor = factor·D·10 mm (sin presión); presión hidrostática en lugar de Janssen; reparto 60/40; caudal = masa/10.
- **D.** Geometría y Janssen contra cálculo a mano e integración numérica; espesor contra fórmula; Janssen menor que la hidrostática; casos sin cilindro y descarga mayor que el diámetro.
- **E.** Presiones y espesor con base física.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. **Uso con precaución**: no verifica pandeo, presiones de descarga normativas, tolva, viento ni sismo (EN 1991-4 / EN 1993-4-1 u otra norma). El espesor reportado es solo el de tensión circunferencial.

### 2.12 Bomba de vacío

- **A.** Máquinas de fluido. Original: `calculo de bomba de vacio.py`, `rev1.py`. Nuevo: `calculos/vacio.py`.
- **B.** Compresión adiabática de ps a pd (atmósfera del sitio o capturada) e isotérmica; masa de aire; potencia al eje; ducto de succión.
- **C.** Ecuación mal planteada (×5.2 a 10 kPa, ×27 a 1 kPa); potencia negativa o compleja con entradas fuera de rango; Patm fija; condiciones del caudal sin definir.
- **D.** Fórmula adiabática e isotérmica contra cálculo independiente; a 2 240 m la descarga es 77.16 kPa; ps > pd y ps < 0 rechazados; CFM y m³/h equivalentes.
- **E.** Ecuación correcta, altitud, validación.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: tipo de bomba y velocidad de ducto por rangos (O; la tabla fuente en F:\ no está en el proyecto).

### 2.13 Bomba centrífuga

- **A.** Hidráulica. Original: `Calculo de bomba cemtrifuga.py`, `rev1`–`rev6`. Nuevo: `calculos/bomba.py`.
- **B.** TDH = Δz + (p_d − p_s)·2.309/GE + h_f + h_k + h_equipos; f por Colebrook o capturado; WHP y BHP; NPSHa con altitud y presión de vapor; curva del sistema.
- **C.** Potencia hidráulica presentada como requerida; sin Δz ni NPSH; presión «disponible» sumada; gráfica sin accesorios ni equipos; f = 0.02 fijo; 2.31 ft/psi solo para agua.
- **D.** Reproduce `prueba.pdf` (H = 562.85 ft, 175.39 HP hidráulicos) con los supuestos originales; con η = 75 %: 233.9 HP al freno. TDH, BHP y NPSHa contra cálculo a mano; laminar y GE ≠ 1 verificados.
- **E.** Ecuación de energía completa, NPSHa, curva del sistema con todas las pérdidas.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: K de accesorios y pérdidas por equipo del original (O) — confirmar con Crane TP-410 y fabricantes. En la curva del sistema las pérdidas por equipo se suponen proporcionales a Q² (corregido en la 2.0.1).

### 2.14 Secador rotatorio directo

- **A.** Térmica. Original: 8 archivos (`calculo del secador.py` … `DS rev 7.py`). Nuevo: `calculos/secador.py`.
- **B.** Balance de masa (base húmeda o seca); balance de energía completo con pérdidas; psicrometría con altitud y verificación de saturación del aire de salida; D por velocidad del gas; Ua de Perry's (inglés → SI); L = V/A con ΔT_ml en paralelo; combustible.
- **C.** Serie DS rev3–7 sin sustento físico (V ≡ 10.05·G, D ×1.5, L sin dimensiones, potencia sin unidades); rev0–2 con bulbo húmedo truncado, G^0.67 mal escrito y D fijo en la potencia; el `.docx` de referencia tiene errores propios.
- **D.** Balances de masa y energía cerrados; W_salida = W_entrada + agua/aire; base seca = base húmeda; Ua convertido contra la forma SI publicada (dentro de 4 %); bulbo húmedo psicrométrico contra Stull; saturación y sólido más caliente que el aire rechazados.
- **E.** Método rev0–2 corregido; serie DS retirada.
- **F.** CORREGIDA / VALIDACIÓN PENDIENTE. Pendiente: Ua es correlación empírica preliminar (E); potencia de accionamiento y aletas del original (O, no validadas); tiempo de residencia y pendiente **no calculados** (Friedman–Marshall pendiente de verificar contra Perry's).
- **Actualización 2.1.1.** Disposición en contracorriente agregada (solo cambia ΔT_ml). Balances de masa y energía, flujo de aire y humedad de salida validados con Geankoplis, Ej. 9.10-2 (sección 8): estado **VALIDADA BAJO CONDICIONES DOCUMENTADAS** limitado a los balances; las dimensiones siguen siendo preliminares.

### 2.15 Viga en voladizo o simplemente apoyada

- **A.** Estructural. Original: `Calculo de Cantiliver.py`, `rev1`, `rev2`. Nuevo: `calculos/viga.py`.
- **B.** Fórmulas cerradas de Euler-Bernoulli para carga puntual en cualquier posición y carga uniforme, ambas condiciones de apoyo; secciones rectangular, circular, tubo, I y personalizada; V, M, δ, σ, τ; revisión contra σ_adm y L/n; diagramas.
- **C.** I fija 0.1 × 0.2 m; momento ×3 en voladizo con carga intermedia; δ ×1.5 simplemente apoyada; σ con c fijo (×2 en circular); rev0 con momento de reacción nulo.
- **D.** Fórmulas clásicas (PL³/3EI, PL³/48EI, 5wL⁴/384EI, wL⁴/8EI) y doble integración numérica independiente de M/EI; inercias de secciones contra fórmula; entradas imposibles rechazadas.
- **E.** Secciones y posiciones reales, cortante y revisión de admisibles.
- **F.** CORREGIDA / **VALIDADA BAJO CONDICIONES DOCUMENTADAS**: elástico lineal, pequeñas deflexiones, sección constante, cargas estáticas. Desde la 2.1.0 incluye la revisión por AISC 360-22 y NTC-DCEA (pandeo lateral-torsional, pandeo local de patín y cortante), validada con los ejemplos AISC (sección 7). E de la lista original es O si no se captura.

---

## 3. Menú e infraestructura

- Menú por disciplinas con buscador sin acentos, estado de validación visible, descripción y limitaciones; doble clic o botón para abrir; una ventana por calculadora.
- Acceso con la contraseña del menú original, ahora con hash; configurable.
- Cada calculadora: formulario con unidades y rangos, ayuda por campo, resultados con nivel de confianza, advertencias y ecuaciones, gráfica cuando aplica, imágenes de referencia, guardar/abrir caso, PDF, Excel y copiar.
- Agregar una calculadora: un módulo en `calculadoras/calculos/` y una línea en `_MODULOS` (ver README); el menú, el buscador, los reportes y las pruebas de humo la incluyen sin más cambios.

---

## 4. Pendientes y funciones no validadas

### 4.1 Funciones conservadas sin validar (nivel O)

| Calculadora | Elemento | Qué se necesita |
|---|---|---|
| Banda | Velocidad por material, tambor, rodillo | Catálogo o norma de la empresa (CEMA / DIN 22101) |
| Elevador | Pasos L1–L30, cangilones C1–C30, velocidades, tambor | Catálogo del fabricante de cangilones |
| Helicoidal | Método completo (F, Fd, Fm, Fo, factores de capacidad) | «Tabla de HP.png» o CEMA 350 |
| Aerodeslizador | Velocidad del material | Dato del fabricante o pruebas |
| Colector | Relación aire/tela 1.0 / 2.5 m/min | Dato del fabricante del filtro |
| Soplador | Tipo de soplador | Curvas de fabricantes |
| Bomba de vacío | Tipo de bomba, velocidad de ducto | «Tabla aplicación Bomba de vacio.png» |
| Bomba centrífuga | K de accesorios, pérdidas por equipo | Crane TP-410, datos de cribas y limpiadores |
| Torre | Tipo de torre | CTI o fabricante |
| Secador | Potencia de accionamiento, número y altura de aletas, pérdidas 20 % por defecto | Fuente de rev0, fabricante |
| Viga | Lista de E | Capturar E del material |
| Todas las de sólidos | Densidades y ángulos de reposo por defecto | Densidad aparente medida de los materiales |

### 4.2 Alcances no cubiertos

- Silo: pandeo, presiones de descarga normativas, tolva, viento, sismo.
- Viga: revisión por código (AISC 360 / NTC), pandeo.
- Secador: tiempo de residencia y pendiente.
- Tolva y silo: flujo de polvos finos (Beverloo no aplica) y diseño de flujo másico (Jenike).
- Neumático: aceleración y elevación de sólidos, fase densa.
- Torre: dimensionamiento del relleno.

### 4.3 Limitaciones de esta auditoría

- **Normas no consultadas.** No se tuvo acceso a CEMA, ISO 5048, DIN 22101, EN 1991-4, EN 1993-4-1, AISC 360, NTC, ACGIH, Crane TP-410, Hydraulic Institute ni CTI. Donde se citan, es como referencia a confirmar; no se tomaron de ellas valores tabulados. Las correlaciones usadas con valores numéricos (ASHRAE, Beverloo, Perry's/McCormick, Ergun, Janssen, Sutherland, Colebrook) son de dominio técnico general y se verificaron con cálculos independientes o fuentes publicadas.
- **Sin casos reales.** No se recibieron memorias de cálculo revisadas ni datos de equipos instalados; la validación es contra primeros principios y fórmulas independientes, no contra mediciones.
- **Pruebas de interfaz.** La suite completa se ejecuta en Linux (pantalla virtual, Python 3.12). Además se hizo una prueba en vivo en la PC del usuario (Windows, Python 3.14) el 13/11/2026: acceso, menú, ductos (resultado igual al cálculo independiente), bomba con caso guardado (17 resultados idénticos a la versión de referencia), validación de entradas, imágenes, PDF y registro de errores. Los cinco defectos de interfaz, la curva del sistema de la bomba y la prioridad de los datos capturados (viga, colector, elevador, secador) se corrigieron en la 2.0.1 (`REGISTRO_DE_CAMBIOS.md`, sección 5). La suite automática no se ha ejecutado en Windows.

### 4.4 Información solicitada para cerrar la validación

1. Fuentes de las tablas originales (sección 4.1), en especial las tres imágenes de `F:\1.5 proyecto San Luis Fluorita`.
2. Normas y manuales disponibles en la empresa, con su edición.
3. Densidad aparente, granulometría y fricción con pared de los materiales usuales.
4. Dos o tres memorias de cálculo revisadas o equipos instalados por calculadora, para casos de referencia.
5. Altitudes típicas de los sitios de proyecto (para el valor por defecto de `config/configuracion.json`).

---

## 7. Fase 3 — validación profesional con ejemplos publicados (versión 2.1.0, 13/11/2026)

Objetivo (solicitud del usuario): dejar las calculadoras usables de modo profesional, validando cada área contra
ejemplos resueltos de normas, manuales o libros de cálculo. Decisiones del usuario: viga con **AISC 360-22 y
NTC-DCEA** («Ambas»); silo **solo predimensionamiento**. Regla mantenida: no se inventan ecuaciones ni coeficientes;
lo que no tiene fuente sigue marcado como nivel O, y una aproximación de gráfica se marca como tal.

| Calculadora | Método / norma agregada | Referencia de validación | Resultado |
|---|---|---|---|
| Viga | AISC 360-22 (F2, F3, F8, F11, G2, G5) y NTC-DCEA (Me, MR, VR) | Ejemplos de diseño AISC F.1-1B, F.1-2B, F.1-3B, F.3B, G.1B | Reproducidos (Mn y φVn dentro de 1 %) — `tests/test_acero.py` |
| Helicoidal | Método CEMA en la forma KWS: SC = CFH·CF1·CF2·CF3, N = SC/cap. 1 rpm, FHP, MHP, TSHP, par | Ejemplo KWS harina de maíz (12 plg, 62 rpm, MHP 0.21 HP) y ejemplo KWS cal viva (SC 1 873 ft³/h, 16 plg, 60 rpm) | Reproducidos — `tests/test_helicoidal.py` |
| Bomba centrífuga | Crane TP-410: K = (L/D)·f_T, f_T por fórmula; entrada/salida | Tabla f_T de Crane (10 diámetros), K de válvula de globo (Pumps & Systems), NPSHa ejemplos 1–3 de Pumps & Systems | Dentro de 0.1 ft y del redondeo de la tabla — `tests/test_bomba.py` |
| Ductos | Rugosidad ASHRAE por material; velocidad mínima ACGIH con corrección por densidad | Ejemplo ASHRAE DFDB de ducto de 24 plg (0.71/1.09/0.05/0.07 plg c.a.); ACGIH 3 000 → 3 282 fpm a 5 000 ft | Dentro de 0.006 plg c.a. y 0.5 % — `tests/test_ductos.py` |
| Soplador | Tipo de máquina (lóbulos: compresión isocórica Q·Δp); temperatura de descarga por balance | Ruta independiente por entalpía; ejemplo Atlas Copco de soplador de lóbulos (125 °C) | Dentro de 5 °C (la carcasa real pierde calor) — `tests/test_soplador.py` |
| Bomba de vacío | Potencia adiabática e isotérmica | Rutas independientes (entalpía; integral de V·dp) | Coincidencia 1e-9 — `tests/test_vacio.py` |
| Colector | Relación aire/tela EPA (tabla 1.1) por polvo y tipo de limpieza | EPA/452/B-02-001 sec. 6 cap. 1, tablas 1.1 y 1.3 | Reproducidos — `tests/test_colector.py` |
| Banda | ISO 5048 / IS 11592: b, rodillo ISO 1537, f = 0.020, C = (L + L₀)/L, factor de pendiente k | MEKA Handbook (1 000 mm, 35°/20°, 2 m/s → 795 m³/h); tabla 9 de IS 11592 | Dentro de 3 % (MEKA usa el borde libre CEMA) — `tests/test_banda.py` |
| Elevador | Dragado y fricción por longitud equivalente KWS (Leq 5–15) | Ecuación KWS en unidades inglesas; ejemplo KWS de arena (6.01 HP) | Equivalencia SI ↔ KWS exacta — `tests/test_elevador.py` |
| Torre | Característica requerida KaV/L de Merkel (Chebyshev 4 puntos + Simpson) | Perry's (Δh en puntos de Chebyshev) y ejemplo de diseño 110/84/69 °F, L/G 1.30 → 1.49 | Dentro de 1 % y 2.5 % — `tests/test_torre.py` |
| Silo | Marcado como **predimensionamiento, no apto para diseño estructural**; Janssen = presiones de llenado EN 1991-4 | Verificaciones anteriores (Janssen, integral, Beverloo) | Sin cambio de método |

**Pruebas.** Suite completa: 229 pruebas aprobadas en Linux (Python 3.12) y en la PC del usuario (Windows, Python 3.14, `PROBAR.bat`, 13/11/2026). En la primera corrida en Windows una prueba de interfaz falló al crear el intérprete Tk («Can't find a usable tk.tcl»), falla intermitente de Tcl/Tk al crear y destruir intérpretes seguidos; las pruebas ahora reintentan la creación (la aplicación crea uno solo).

**Plataforma (2.1.0).** Datos del proyecto (proyecto, cliente, documento, revisión, elaboró, revisó, aprobó) en el
encabezado del PDF, del Excel, del texto copiado y de los casos guardados; historial automático de cálculos
(`registro/historial.jsonl`) con ventana para reabrir cualquier cálculo anterior. Motores comerciales (NEMA MG 1 e
IEC 60072-1) en el helicoidal.

**Quedan en VALIDACIÓN PENDIENTE (honestamente):** aerodeslizador, transportador neumático, tolva de dosificación y
secador rotatorio. Sus ecuaciones físicas están verificadas (Ergun, Colebrook, Beverloo, balances), pero no se
encontró un ejemplo resuelto público que permita validarlas de extremo a extremo, y conservan criterios originales
sin fuente (velocidades por tabla, coeficiente Ks, ángulos de reposo). Se pueden usar con los datos del fabricante
capturados; cada salida indica su nivel.

**Aproximaciones declaradas.** Fo de la gráfica CEMA en el helicoidal (interpolación log-lineal entre los extremos
publicados, nivel E, sustituible por un Fo o un MHP corregido capturados); factor C de ISO 5048 con L₀ = 100 m
(extremo conservador del intervalo 70–100 m) e incierto para L < 80 m (se advierte).

## 8. Validación con ejercicios de libros de texto (versión 2.1.1, 13/11/2026)

Solicitud del usuario: probar las calculadoras con ejercicios de libros de editoriales usadas en la enseñanza de
la ingeniería y la mecánica. Detalle completo, capturas y fuentes: `docs/VALIDACION_CON_LIBROS.md`.

| Calculadora | Libro y ejercicio | Resultado |
|---|---|---|
| Torre | Çengel y Boles, *Termodinámica*: P14-112 (respuestas en el enunciado) y P14-115 (manual de soluciones) | Coincide (≤ 0.45 %) |
| Bomba centrífuga | Çengel y Cimbala, *Mecánica de fluidos*: Ejemplo 8-3 | Coincide (≤ 0.13 %) |
| Ductos | Çengel y Cimbala, *Mecánica de fluidos*: Ejemplo 8-4 | Coincide (≤ 0.53 %) |
| Bomba de vacío | Çengel y Boles, *Termodinámica*, cap. 7: trabajo de compresión 100 kPa/300 K → 900 kPa | Coincide (≤ 0.02 %) |
| Aerodeslizador | Rhodes, *Introduction to Particle Technology*: Ejercicio 7.9 (Umf por Ergun) | Coincide (0.29 %) |
| Viga | *Strength of Materials* (OER): Ejemplo 11.1 | Coincide (0.01 %) |
| Secador | Geankoplis, *Transport Processes and Unit Operations*: Ejemplo 9.10-2 | Coincide (≤ 0.14 %) |

24 de 24 comprobaciones coinciden. Ningún ejercicio reveló un error en las ecuaciones corregidas; sí revelaron dos
limitaciones de captura que se resolvieron en la 2.1.1 (torre con HR de salida y balance completo; secador a
contracorriente). Las pruebas `tests/test_libros.py` y `tests/test_interfaz.py::test_casos_de_libros_…` las
repiten en cada ejecución, y los casos `docs/ejemplos/libros/*.json` permiten repetirlas en el programa.

**Pruebas 2.1.1.** Suite completa: 248 pruebas aprobadas en Linux (Python 3.12) y en la PC del usuario (Windows,
Python 3.14, `PROBAR.bat`, 13/11/2026 17:16, 89.6 s), incluidas las 19 nuevas de libros de texto.

**Estado después de la 2.1.1:** 12 de 15 VALIDADAS BAJO CONDICIONES DOCUMENTADAS (se suma el secador, limitado a
balances). Quedan en VALIDACIÓN PENDIENTE el aerodeslizador (la fluidización ya coincide con Rhodes; la capacidad
usa velocidades del original, nivel O), el transportador neumático (Ks del usuario; los libros usan otras
correlaciones) y la tolva (Beverloo verificado contra la ecuación, sin ejercicio resuelto publicado localizado).

## 9. Material visual: esquemas ajustables (versión 2.2.0, 13/11/2026)

Cada calculadora, excepto la bomba centrífuga (decisión del usuario), tiene una pestaña «Esquema» con el dibujo del
equipo que se redibuja con los datos. Detalle en `docs/REGISTRO_DE_CAMBIOS.md`, sección 8.

**Control de calidad del material visual.** Un esquema mal dibujado puede inducir a error aunque el cálculo sea
correcto. Por eso los esquemas no calculan: usan los resultados y las mismas funciones del motor, y las pruebas
verifican que lo dibujado coincide con lo calculado (áreas de la sección de la banda, alturas y presión de Janssen del
silo, deflexión máxima de la viga). Cada figura indica si es **a escala** o **esquema sin escala**, y los elementos que
no se calculan están rotulados como indicativos. El estado de auditoría y de validación de las calculadoras no
cambia: el material visual es apoyo, no evidencia de validación.

**Pruebas 2.2.0.** 301 pruebas aprobadas en Linux (Python 3.12).

