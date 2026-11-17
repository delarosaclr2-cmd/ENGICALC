# Registro de errores y correcciones — versión 2.0.0

Fecha: 12/11/2026. Versión anterior: los 47 archivos `.py` originales del proyecto (menú «manejador de archivos» rev0–rev4 y 15 familias de calculadoras).

Ningún archivo original fue modificado. Esta versión es una carpeta nueva; cada calculadora nueva indica en su ventana («Información técnica»), en su memoria de cálculo y en `docs/CATALOGO_DE_CALCULADORAS.md` qué archivos originales sustituye.

Clave de la columna «Decisión»:

- **Corregido**: error comprobado numéricamente (ver `docs/EVIDENCIA_ORIGINAL_VS_CORREGIDO.txt`) y sustituido por el método físico o la referencia indicada.
- **Conservado (O)**: criterio o tabla del original sin fuente identificada. Se mantiene para no perder funcionalidad, pero el resultado se marca con nivel **O** (no validado), se puede sustituir por un dato capturado y se emite una advertencia.
- **Eliminado**: fórmula o salida sin sustento físico que no se puede conservar ni como criterio; se justifica en cada caso.
- **Agregado**: verificación o resultado nuevo necesario para que el cálculo tenga sentido.

---

## 1. Mapa de archivos originales → módulos nuevos

| Familia original (archivos) | Revisión de referencia | Módulo nuevo | Id. en el menú |
|---|---|---|---|
| `manejador de archivos.py`, `rev1`–`rev4` | rev4 | `calculadoras/interfaz/menu.py`, `acceso.py`, `menu_principal.py` | — |
| `calculo de banda.py`, `calculo de banda_vs2.py`, `Calculo de banda vs3/vs4/vs5.py` | vs5 (vs1 para la velocidad capturable) | `calculos/banda.py` | `banda` |
| `Calculo de Elevador vs1/vs2/vs3.py` | vs3 | `calculos/elevador.py` | `elevador` |
| `Calculo del transportador helicoidal.py` | única | `calculos/helicoidal.py` | `helicoidal` |
| `Calculo de Deslizador vs1/vs2.py` | vs2 | `calculos/aerodeslizador.py` | `aerodeslizador` |
| `Calculo transportador neumatico rev 0/rev 1.py` | rev 1 | `calculos/neumatico.py` | `neumatico` |
| `calculo de tolva de dosificación.py` | única | `calculos/tolva.py` | `tolva` |
| `Calculo de un silo metalico.py` | única | `calculos/silo.py` | `silo` |
| `Calculo de dimensionamientos de ductos con polvo.py` | única | `calculos/ductos.py` | `ductos` |
| `calculo de colector de polvo.py` | única | `calculos/colector.py` | `colector` |
| `Calculo de soplador Rev 0/Rev 1/Rev 2.py` | Rev 0 (velocidad capturable) + clasificación Rev 0 | `calculos/soplador.py` | `soplador` |
| `Calculo de bomba cemtrifuga.py`, `rev1`–`rev6` | rev6 (gráfica de rev2) | `calculos/bomba.py` | `bomba` |
| `calculo de bomba de vacio.py`, `rev1` | rev1 | `calculos/vacio.py` | `vacio` |
| `Calculo de torre de enfriamiento rev0/rev1.py` | rev1 | `calculos/torre.py` | `torre` |
| `calculo del secador.py`, `rev 1`, `rev 2`, `DS rev 3`–`DS rev 7` | rev0–rev2 (método corregido); DS rev3–7 descartado | `calculos/secador.py` | `secador` |
| `Calculo de Cantiliver.py`, `rev1`, `rev2` | rev2 | `calculos/viga.py` | `viga` |

Tres calculadoras que existían pero no estaban en el menú (bomba centrífuga, secador y viga) ahora sí están. Las 15 se abren desde el menú.

---

## 2. Infraestructura y menú

| # | Problema en el original | Consecuencia | Decisión |
|---|---|---|---|
| M1 | El menú abría scripts por rutas fijas `D:\Python\…` con `subprocess.Popen(["python", ruta], shell=True)`. | En cualquier otra PC: «archivo no encontrado». Dependía de `python` en el PATH. | **Corregido**: las calculadoras se registran en `calculadoras/calculos/__init__.py` y se abren como ventanas del mismo programa. Sin rutas absolutas. |
| M2 | El menú abría revisiones viejas: Soplador Rev 0 y Torre rev0 (con el error ×1/1000). | Resultados erróneos desde el menú. | **Corregido**: una sola versión por calculadora. |
| M3 | Contraseña en texto plano en el código; el usuario se ignoraba. | Cualquiera que abra el `.py` la ve. | **Corregido**: misma contraseña, guardada como SHA-256 con sal en `config/configuracion.json`; se cambia con `--cambiar-contrasena` o se desactiva. Sigue sin validar el usuario (igual que el original) salvo que se active `verificar_usuario`. Es una barrera de acceso, no seguridad. |
| M4 | «Guardar» escribía el texto fijo «Contenido de ejemplo»; «Exportar PDF» solo listaba nombres de programas; «Imprimir» y «Abrir» usaban `os.startfile` sobre cualquier archivo. | Funciones sin utilidad real. | **Eliminado** del menú principal y **sustituido** por funciones reales por calculadora: guardar/abrir caso (JSON), memoria de cálculo PDF y Excel, copiar resultados. |
| M5 | Cada calculadora construía la ventana al importarse y calculaba leyendo los campos de la ventana. | El cálculo no se podía probar ni reutilizar. | **Corregido**: arquitectura en capas — `nucleo` (física compartida), `calculos` (sin interfaz), `interfaz` (Tk). |
| M6 | Tablas de materiales copiadas en cada archivo, con valores distintos para el mismo material. | Resultados inconsistentes entre herramientas. | **Conservado (O)** en una sola tabla `nucleo/materiales.py` que guarda los valores de cada módulo original; la calculadora pide densidad aparente y, si se deja en 0, usa la del original con advertencia que muestra la discrepancia entre módulos. |
| M7 | Validación de entradas mínima: texto, negativos o cero producían excepciones o resultados sin sentido (potencias negativas, números complejos). | Resultados falsos sin aviso. | **Corregido**: cada dato tiene unidad, rango y obligatoriedad; se reportan todos los errores a la vez; los cálculos verifican condiciones físicas (p. ej. succión < descarga, aire de salida no sobresaturado). |
| M8 | Reportes con entradas de un cálculo y resultados de otro (bomba) o valores editables a mano. | Memorias de cálculo incoherentes. | **Corregido**: el PDF/Excel se genera solo del último cálculo; si los datos cambiaron después de calcular, la exportación se bloquea. |
| M9 | Sin pruebas automáticas. | Errores no detectados. | **Agregado**: 148 pruebas (`tests/`). |

---

## 3. Calculadoras

### 3.1 Torre de enfriamiento (`torre`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| T1 | rev0: Q = ṁ·cp·ΔT/1000 (kW mil veces menor). | **Corregido**: Q = ṁ·cp·ΔT [kW] (rev1 ya lo hacía). |
| T2 | Flujo de aire = 1.2·Q (rev0) o Q/187.5 (rev1): no salen de un balance; dan 0.30 y 1.34 kg/s para el mismo caso. | **Eliminado**; **Agregado** balance de entalpía: ṁ_aire = Q/(h_salida − h_entrada), con psicrometría ASHRAE y altitud. |
| T3 | La gráfica de rev1 conservaba el /1000. | **Corregido**: la gráfica usa el mismo motor que el resultado. |
| T4 | No pedía bulbo húmedo ni altitud. | **Agregado**: bulbo húmedo, bulbo seco, temperatura de aire de salida y altitud; verificación de aproximación (agua fría por encima del bulbo húmedo) y evaporación. |
| T5 | Clasificación de tipo de torre por caudal sin fuente. | **Conservado (O)** (criterio de rev1). |

### 3.2 Soplador (`soplador`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| S1 | P = ΔP[Pa]·Q/(102·η): sobreestima 9.81 veces (el 102 es para mm H₂O). | **Corregido**: P = ΔP·Q/η. |
| S2 | Modelo incompresible hasta relaciones de presión altas. | **Agregado**: potencia adiabática con la presión atmosférica del sitio; se reportan ambas y se advierte cuando la diferencia es significativa. |
| S3 | Rev 0 y Rev 2 clasificaban distinto el mismo punto. | **Conservado (O)**: clasificación de Rev 0 (la que abría el menú). |
| S4 | Gráfica marcada «ejemplo» en el propio código. | **Eliminado**. |
| S5 | Rev 1/Rev 2 fijaban v = 20 m/s. | **Corregido**: velocidad capturable (como Rev 0). |

### 3.3 Colector de polvo (`colector`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| C1 | P = (mm H₂O·9.80665)·Q/(102·η): ×9.8. | **Corregido**: P = ΔP[Pa]·Q/η. |
| C2 | Almacenamiento = caudal de aire/10 × 12 h (10 000 m³/h de aire → 12 000 m³ de polvo). | **Corregido**: masa de polvo = Q·concentración·eficiencia de captación; volumen con densidad aparente y horas capturadas. |
| C3 | Relación aire/tela fija 1.0 y 2.5 m/min. | **Conservado (O)** como opción («fino»/«grueso»), con opción para capturar el valor del fabricante. |

### 3.4 Ductos con polvo (`ductos`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| D1 | Cálculo correcto; usaba 9.795 Pa/mm H₂O. | **Corregido**: 9.80665 (diferencia 0.12 %). |
| D2 | f fijo sin aclarar Darcy/Fanning. | **Agregado**: f de Darcy capturado o calculado con Colebrook-White (rugosidad, Reynolds, viscosidad de Sutherland). |
| D3 | Solo tramo recto. | **Agregado**: ΣK de accesorios, densidad por altitud y temperatura, verificación de velocidad mínima de transporte capturada. |

### 3.5 Banda transportadora (`banda`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| B1 | «Área» = ancho × ocupación (en m, no m²): 3 456 t/h de arena a 1 m/s en banda de 1 000 mm. | **Corregido**: sección geométrica de artesa (trapecio) + sobrecarga parabólica con ángulos de artesa y de sobrecarga. Verificado contra área de polígono e integración numérica. |
| B2 | P = (t/h)·g·L·cos θ/(3600·η): trata L·cos θ como altura, fricción = 1; da más potencia en horizontal que en vertical. | **Corregido**: estructura de resistencias ISO 5048 / DIN 22101 con f y C del usuario + elevación q_G·g·H. |
| B3 | La velocidad la imponía el material. | **Corregido**: velocidad capturable; 0 = tabla original (**O**). |
| B4 | Tambor y rodillo por tabla de ancho. | **Conservado (O)**. |

### 3.6 Elevador de cangilones (`elevador`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| E1 | Cangilones por metro truncados a entero (paso 350 mm → 2 en vez de 2.857, −30 %). | **Corregido**: n = 1000/paso. |
| E2 | Volumen ya con 80 % de llenado y además × eficiencia mecánica. | **Corregido**: llenado φ separado de η; η solo en la potencia. |
| E3 | η se cancelaba en la potencia. | **Corregido**: P = ṁ·g·(H + H_carga)/η. |
| E4 | Volumen = prisma largo × ancho × fondo. | **Conservado (O)** con opción de capturar el volumen de catálogo. |
| E5 | No verificaba la descarga centrífuga. | **Agregado**: relación v²/(g·R) con el diámetro del tambor y advertencia. |
| E6 | Pasos L1–L30, cangilones C1–C30, velocidades, tambor por ancho. | **Conservado (O)**. |

### 3.7 Transportador helicoidal (`helicoidal`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| H1 | Método empírico (estructura similar a CEMA 350) sin fuente disponible («Tabla de HP.png» no está en el proyecto). | **Conservado (O)** completo, con los factores ahora explícitos y editables (capacidad ×1.25, Fm 0.4, Fo 1.25). No se puede corregir sin la fuente. |
| H2 | F elegido por capacidad (implica un diámetro) y D elegido aparte. | **Conservado (O)** con advertencia; **Agregado** F capturable del catálogo. |
| H3 | Ángulo pedido y no usado. | Se mantiene sin efecto y se **advierte** (no hay fuente para corregir por inclinación). |
| H4 | Entradas en ft y lb/ft³. | **Corregido**: entradas en SI, conversión interna documentada. |

### 3.8 Aerodeslizador (`aerodeslizador`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| A1 | ΔP no era la ecuación de Ergun ((1−ε) sin cuadrado, ε³ multiplicando, sin altura de lecho, /10 000 sin origen). | **Corregido**: Ergun por metro de lecho y ΔP de lecho fluidizado = ρb·g·H; velocidad mínima de fluidización. |
| A2 | Caudal de aire = sección del colchón × velocidad del material. | **Corregido**: caudal específico × área de tela (ancho × longitud). |
| A3 | Tamaño de partícula en «mm» con valores de 8–10 nm. | **Corregido**: dato en µm. |
| A4 | Inclinación pedida y no usada. | Se mantiene sin efecto y se **advierte**. |
| A5 | Velocidad del material por tabla. | **Conservado (O)**. |

### 3.9 Transportador neumático (`neumatico`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| N1 | Relación de carga pedida y no usada; flujo de sólidos no calculado. | **Corregido**: ṁ_s = μ·ṁ_aire; capacidad en t/h. |
| N2 | ΔP solo del aire con f fijo (0.03/0.06). | **Corregido**: Colebrook-White + ΣK; **Agregado** pérdida por sólidos de forma Barth ΔP_s = μ·Ks·ΔP_aire con Ks capturado (sin valor por defecto inventado). |
| N3 | Fase densa con el mismo modelo. | Se calcula, pero se **advierte** que el modelo es de fase diluida. |
| N4 | rev 0: ΔP = coef·L/10 y potencia con /3600 extra. | **Eliminado** (sustituido por N2). |

### 3.10 Tolva de dosificación (`tolva`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| TV1 | Altura por área media de extremos (−23 % en el caso de prueba). | **Corregido**: tronco de secciones semejantes h = 3V/(A₁ + A₂ + √(A₁A₂)). |
| TV2 | Flujo = 0.5·A₂·√(g·h)·ρ/3.66 (como líquido; /3.66 en vez de ×60). | **Corregido**: Beverloo (1961) con C = 0.58, k = 1.4. **Agregado** advertencia: no aplicable a polvos finos (< ~0.4 mm). |
| TV3 | Ángulo de reposo mostrado y no usado. | **Agregado**: ángulos de cara plana y de arista; advertencia si la arista no supera el ángulo de reposo. |
| TV4 | Densidades de partícula en vez de aparentes. | Densidad aparente capturable; tabla original **O** con advertencia. |

### 3.11 Silo metálico (`silo`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| SI1 | Espesor = factor·D·10 mm (sin presión ni esfuerzo admisible). | **Eliminado**; **Agregado** espesor por tensión circunferencial con presión de Janssen × factor de descarga, esfuerzo admisible, eficiencia de junta, corrosión y espesor mínimo. Pandeo **no** verificado (advertencia permanente). |
| SI2 | «Presión lateral» = ρ·g·h (hidrostática). | **Corregido**: Janssen (presión horizontal, vertical, fricción en pared y compresión axial). |
| SI3 | Volumen repartido 60/40 cilindro/cono. | **Corregido**: geometría real con semiángulo de tolva. |
| SI4 | Caudal = masa/10 (siempre 10 min). | **Corregido**: Beverloo, con la misma advertencia para polvos finos. |

### 3.12 Bomba de vacío (`vacio`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| V1 | P = k/(k−1)·Patm·Q·[1 − (ps/Patm)^m]: no es la compresión de ps a la atmósfera (×5.2 a 10 kPa; ×27 a 1 kPa). | **Corregido**: P = k/(k−1)·ps·Qs·[(pd/ps)^m − 1]/η y, además, la isotérmica. |
| V2 | Potencia negativa con ps > Patm; número complejo con ps < 0. | **Corregido**: validación 0 < ps < pd. |
| V3 | Patm = 101.3 kPa fija. | **Corregido**: presión de descarga = atmósfera del sitio por altitud, o capturada. |
| V4 | CFM sin definir condiciones. | **Corregido**: caudal a condiciones de succión, en CFM o m³/h. |
| V5 | Tipo de bomba y velocidad de ducto por rangos. | **Conservado (O)**. |

### 3.13 Bomba centrífuga (`bomba`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| BC1 | gpm·H/3960 (hidráulica, agua) presentado como potencia requerida. | **Corregido**: WHP = gpm·H·GE/3960 y BHP = WHP/η. Con η = 0 solo se reporta la potencia hidráulica, con advertencia. En `prueba.pdf`: 175.4 HP hidráulicos → 233.9 HP al freno con η = 75 %. |
| BC2 | Sin diferencia de elevación. | **Agregado**: Δz, presión de descarga y de succión. |
| BC3 | «Presión disponible» sumada a la altura. | **Corregido**: TDH = Δz + (p_d − p_s)·2.309/GE + pérdidas. |
| BC4 | Sin NPSH disponible. | **Agregado**: NPSHa con presión atmosférica por altitud, presión de vapor, nivel y pérdidas de succión. |
| BC5 | Gráfica rev3–rev6 solo con fricción (36.7 ft contra 562.9 ft). | **Corregido**: curva del sistema con todas las pérdidas (como rev2). |
| BC6 | f = 0.02 fijo, 2.31 ft/psi solo para agua. | **Corregido**: Colebrook-White con rugosidad y viscosidad, o f capturado; 2.309/GE. |
| BC7 | K de accesorios y pérdidas por equipo (30/35/35/25 ft). | **Conservado (O)** como valores editables. |

### 3.14 Secador rotatorio (`secador`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| SE1 | DS rev3–7: V = Qt/(100·ΔT) se reduce a 10.05·G (no depende del calor ni de D, L). | **Eliminado** (serie DS rev3–7 descartada como método). |
| SE2 | DS rev3–7: D con factor 9 en lugar de 4 (+50 %). | **Eliminado**; D = √(4·Q_gas/(π·v·φ_libre)). |
| SE3 | DS rev3–7: L = 4·(1/v)/sen α (dimensionalmente inconsistente). | **Eliminado**; L = V/A con V = Q_útil/(Ua·ΔT_ml). |
| SE4 | DS rev3–7: potencia sin unidades de potencia; gráficas con P ∝ rpm³. | **Eliminado** (fórmula y gráficas). |
| SE5 | rev0–2: bulbo húmedo con Stull truncada (hasta −2.6 °C). | **Corregido**: psicrometría ASHRAE con altitud. |
| SE6 | rev0–2: (G + e^0.67) donde corresponde G^0.67; mezcla SI/inglés ×2. | **Corregido**: Ua = 0.5·G^0.67/D de Perry's en unidades inglesas, convertido a SI (contrastado con la forma SI publicada). |
| SE7 | rev0–2: potencia con D fijo 9.97. | **Conservado (O)** con el D real; aletas también **O**. No validados. |
| SE8 | Balance de energía incompleto, Cp sin usar, Y = 5 kg/kg aceptado. | **Corregido**: balance completo (sólido, agua residual, evaporación, sobrecalentamiento del vapor, pérdidas), base húmeda o seca, verificación de saturación del aire de salida, combustible. |
| SE9 | Tiempo de residencia (variante de Friedman–Marshall). | **No calculado**: pendiente de verificar contra Perry's. |

### 3.15 Viga (`viga`)

| # | Error / hallazgo original | Decisión |
|---|---|---|
| VG1 | I siempre con 0.1 × 0.2 m. | **Corregido**: secciones rectangular, circular, tubo, I y personalizada con sus dimensiones. |
| VG2 | Voladizo: carga medida desde el empotre en la deflexión y desde el extremo en el momento (M ×3). | **Corregido**: fórmulas cerradas de Euler-Bernoulli con x desde el empotre; verificadas por doble integración numérica. |
| VG3 | Simplemente apoyada: δ = 1.5 × PL³/48EI con carga al centro. | **Corregido**. |
| VG4 | σ = M·0.1/I con c fijo (×2 en circular de 0.1 m). | **Corregido**: σ = M·c/I con c de la sección. |
| VG5 | rev0: momento de reacción 0 con la carga en la punta. | **Corregido**. |
| VG6 | Sin cortante ni comparación con admisibles. | **Agregado**: cortante máximo, relación σ/σ_adm y deflexión contra L/n capturados. Pandeo lateral-torsional y revisión por código **no** incluidos (advertencia). |
| VG7 | Lista de E (210 GPa acero, etc.). | **Conservado (O)** con opción de capturar E. |

---

## 4. Cambios posteriores a la primera ejecución completa (control de calidad)

| Fecha | Cambio | Motivo |
|---|---|---|
| 12/11/2026 | Advertencia de aplicabilidad de Beverloo en tolva y silo para partículas < 0.4 mm o sin dato. | En la revisión de evidencia, el caso de cemento (d = 0.05 mm) daba ~12 t/min; Beverloo sobreestima la descarga de polvos finos (Nedderman, 1992). Prueba `test_beverloo_advierte_polvos_finos`. |
| 12/11/2026 | Ajustes de interfaz: el formulario se adapta al ancho visible, columnas de resultados sin recorte, imágenes en un menú, estados abreviados en el menú. | Capturas de pantalla de la ejecución real mostraban campos y columnas recortados. Cambio de interfaz, sin efecto en los cálculos. |
| 12/11/2026 | El encabezado «Gráfica» del PDF se mantiene junto a la imagen. | Quedaba solo al pie de página. |
| 12/11/2026 | Errores no previstos de la interfaz: mensaje al usuario y traza en `registro/errores.log`; si falta una biblioteca, indica ejecutar `INSTALAR.bat`. | Con `pythonw` (INICIAR.bat) los errores no se verían. Prueba `test_errores_inesperados_se_registran_y_se_muestran`. |
| 12/11/2026 | La rueda del ratón desplaza el formulario solo con el puntero encima y no cambia la opción de las listas. | Usabilidad en Windows. Sin efecto en los cálculos. |

---

## 5. Versión 2.0.1 — correcciones de la prueba en vivo en Windows (13/11/2026)

Prueba realizada en la PC del usuario (Windows, Python 3.14, sin openpyxl ni matplotlib instalados), con el programa tal como se descomprimió del ZIP. W6 corrige la curva del sistema de la bomba (no sus resultados numéricos) y W7 la prioridad de los datos capturados; las demás son de interfaz y reportes.

| # | Hallazgo en la prueba en vivo | Consecuencia | Corrección |
|---|---|---|---|
| W1 | La memoria PDF usaba Helvetica cuando matplotlib no está instalado (la fuente DejaVu se tomaba de matplotlib). | En el PDF desaparecían Δ, subíndices y superíndices: «mm H■O», «ΔP» sin Δ, «v²» sin ². | La fuente DejaVu Sans (licencia libre, `recursos/fuentes/LICENSE_DEJAVU`) va incluida en `recursos/fuentes`; respaldo: Segoe UI de Windows. Prueba `test_pdf_usa_fuente_unicode_incluida_sin_matplotlib`. |
| W2 | En bomba, torre y viga, «Exportar PDF» fallaba completo si falta matplotlib (la gráfica es parte del PDF). | No se podía obtener la memoria de cálculo. | El PDF se genera sin la gráfica y la barra de estado lo indica. Prueba `test_pdf_sin_matplotlib_se_genera_sin_grafica`. |
| W3 | El aviso de error aparecía sobre el menú principal, no sobre la calculadora en uso. | Confuso: la calculadora quedaba detrás. | El aviso se muestra sobre la ventana activa. |
| W4 | No había forma de saber al abrir el programa que faltaban bibliotecas. | El usuario se enteraba al exportar. | El menú muestra en rojo qué bibliotecas faltan, qué funciones afectan y que se ejecute `INSTALAR.bat`. Prueba `test_menu_avisa_bibliotecas_faltantes`. |
| W5 | Con una búsqueda sin coincidencias, el panel de detalle seguía mostrando la última calculadora seleccionada. | Información desfasada en pantalla. | El panel se limpia al filtrar. Prueba `test_buscador`. |
| W6 | **Cálculo (bomba centrífuga, solo la gráfica):** la curva del sistema sumaba las pérdidas por equipo (cribas, limpiadores) como constantes a todo caudal. | La curva arrancaba 30 ft arriba de la altura estática real a caudal cero (82.3 ft en vez de 52.3 ft en el caso de ejemplo); afecta la lectura fuera del punto de diseño. Los resultados numéricos y el punto de diseño no cambian. | Las pérdidas por equipo se escalan con (Q/Q_diseño)², igual que fricción y accesorios; supuesto documentado en las limitaciones. Prueba `test_bomba_curva_del_sistema`. |
| W7 | **Datos de entrada (viga, colector, elevador, secador):** un valor capturado se ignoraba sin aviso si en la lista no se elegía la opción «Capturar/Personalizado». En vivo: viga con «Acero» y E = 200 GPa capturado → se usó 210 GPa (deflexión 1.868 mm en vez de 1.961 mm). | Resultado distinto del que el usuario cree haber calculado. | Regla común: un valor capturado (> 0) siempre tiene prioridad; 0 = valor de la tabla original (nivel O). Cuando sustituye a la opción elegida, se indica en las notas. Pruebas `test_viga_modulo_capturado_tiene_prioridad`, `test_dato_capturado_tiene_prioridad_sobre_la_lista`, `test_secador_ua_capturado_tiene_prioridad`. |


---

## 6. Versión 2.1.0 — validación profesional (13/11/2026)

| Calculadora | Cambio | Justificación / referencia |
|---|---|---|
| Helicoidal | **Método sustituido** por CEMA/KWS (capacidad de selección, velocidad, FHP, MHP, TSHP, par, motor NEMA/IEC; tabla de 36 materiales KWS; hélices especiales y paletas). El método heredado se conserva en `calculos/helicoidal_original.py` (no aparece en el menú) y su prueba sigue pasando. | El método original no tenía fuente (H1–H4). El nuevo reproduce los ejemplos publicados de KWS. Los casos guardados del helicoidal 2.0.x usan otros campos: se deben volver a capturar. |
| Bomba centrífuga | K de codos, tees y válvulas por Crane TP-410 (K = (L/D)·f_T) con tipos de válvula; nuevos accesorios (codos de radio largo y 45°, tees de paso, retenciones, entradas y salidas). Los K originales (0.5, 1.0, 1.8) se pueden capturar. | Sustituye valores sin fuente. Casos 2.0.x: los K capturados siguen funcionando. |
| Ductos | Material del ducto (rugosidad ASHRAE); tipo de contaminante con velocidad mínima ACGIH corregida por densidad; verificación «cumple». | Antes, rugosidad 0 = ducto liso y la velocidad mínima era un dato sin guía. |
| Colector | Relación aire/tela de la tabla 1.1 de la EPA por polvo (41 polvos) y tipo de limpieza. Los criterios originales 1.0/2.5 m/min siguen como opción (nivel O). | Sustituye el criterio original sin fuente como valor por defecto. |
| Soplador | Tipo de máquina (dinámica o de lóbulos), potencia recomendada según el tipo, temperatura de succión, flujo másico y temperatura de descarga. | En sopladores de lóbulos la potencia adiabática subestimaba la real. |
| Banda | Valores por defecto de ISO 5048 (f = 0.020; C = (L + L₀)/L; rodillo ISO 1537; b para B > 2 000 mm) y factor de pendiente de IS 11592. | Antes f y C eran datos sin guía y no se reducía la sección por inclinación. |
| Elevador | Dragado y fricción por el método de longitud equivalente de KWS (Leq, tambor de cola); la altura equivalente capturada tiene prioridad. | Antes, sin dato capturado, la potencia excluía el dragado. |
| Torre | KaV/L requerido (Merkel, Chebyshev y Simpson), L/G capturable y verificación de cruce con la curva de saturación. | La torre no tenía cálculo de característica. |
| Silo | Nombre, descripción, advertencia y salidas marcadas como **predimensionamiento, no apto para diseño estructural**. | Decisión del usuario. |
| Viga | Revisión AISC 360-22 y NTC-DCEA (flexión con pandeo lateral-torsional y pandeo local de patín, cortante) para secciones I, tubos y barras. | Decisión del usuario («Ambas»). |
| Viga (casos 2.0.x) | Un caso de viga guardado en la 2.0.x abre con la norma por defecto («AISC 360-22 y NTC-DCEA») y pide Fy y el factor de carga; para repetir el análisis elástico anterior elija «Ninguna». El ejemplo `docs/ejemplos/caso_viga.json` se actualizó así. | Compatibilidad de casos guardados. |
| Plataforma | Datos del proyecto en reportes y casos; historial automático con reapertura; los decimales se conservan al reabrir (12 cifras significativas). | Uso profesional (trazabilidad del documento). |

## 7. Versión 2.1.1 — validación con ejercicios de libros de texto (13/11/2026)

Solicitud del usuario: probar las calculadoras con ejercicios de libros de texto de editoriales usadas en la
enseñanza (detalle completo en `docs/VALIDACION_CON_LIBROS.md`). Se reprodujeron 8 ejercicios publicados
(Çengel y Cimbala; Çengel y Boles; Geankoplis; Rhodes; *Strength of Materials* OER): 24 de 24 comprobaciones
coinciden con la respuesta publicada (diferencia máxima 0.53 %).

| Calculadora | Cambio | Justificación / referencia |
|---|---|---|
| Torre | **Balance completo** de Çengel y Boles: estado del aire de entrada por bulbo seco y bulbo húmedo (si el bulbo seco es 0 se mantiene la aproximación de Merkel, aire saturado al bulbo húmedo); aire de salida con temperatura y **humedad relativa** capturadas (campo nuevo `hr_aire_salida`, 50–100 %, por defecto 100 % = comportamiento anterior); el agua de reposición entra en el balance de energía: ṁ_a = Q/[(h₂ − h₁) − (ω₂ − ω₁)·h_f,fría]. Salidas nuevas: ω de entrada y salida, caudal de aire a la entrada, reposición en kg/s. | Los problemas 14-112 y 14-115 especifican la HR de salida (90 %, 95 %). Con el supuesto de saturación de la 2.1.0 el P14-112 daba ≈ 38.3 m³/s en lugar de 44.9 (−15 %). Los casos guardados de la 2.1.0 abren con HR = 100 % (mismo supuesto anterior), pero el flujo de aire resulta ≈ 3–4 % mayor (caso de prueba: 7.64 → 7.95 kg/s) porque ahora el balance incluye el agua de reposición y el estado real del aire de entrada, como en Çengel y Boles; la 2.1.0 lo omitía. Con L/G capturado el flujo de aire no cambia; si además se captura el bulbo seco, la entalpía de entrada y KaV/L usan el estado real del aire en lugar de la aproximación de Merkel (aire saturado al bulbo húmedo). |
| Secador | Opción **«Disposición de los flujos»** (paralelo o contracorriente; por defecto paralelo = comportamiento anterior). Solo cambian las diferencias de temperatura de ΔT_ml; los balances no dependen de la disposición. Estado de validación: **VALIDADA BAJO CONDICIONES DOCUMENTADAS** para balances de masa y energía, flujo de aire seco y humedad de salida (Geankoplis, Ej. 9.10-2: 1 170 vs 1 171 kg/h, 0.02473 vs 0.0247). Diámetro, longitud y Ua siguen como estimación preliminar (E); potencia y aletas del original siguen sin validar (O). | El ejemplo de Geankoplis es a contracorriente y no podía capturarse (el programa rechazaba con razón ese caso en flujo paralelo). |
| Pruebas | `tests/casos_libros.py` (datos de los ejercicios), `tests/test_libros.py` (motor) y prueba de interfaz que abre cada caso en la ventana y verifica la respuesta publicada. | Evidencia automática y repetible. |
| Ejemplos | `docs/ejemplos/libros/*.json` (8 casos con fuente y planteamiento) generados por `herramientas/generar_casos_libros.py`. | El usuario puede abrir cada ejercicio en el programa y ver el resultado. |
| Versión | 2.1.0 → 2.1.1. | — |

## 8. Versión 2.2.0 — esquemas ajustables (13/11/2026)

Solicitud del usuario: agregar diagramas o material de apoyo visual ajustable a las calculadoras, **sin agregar
material visual a la bomba centrífuga**. Decisiones del usuario: esquema a escala que se redibuja con los datos;
solo en la ventana (la memoria PDF no cambia).

**Este cambio es solo de interfaz: no modifica ninguna ecuación, dato por defecto ni resultado.** Los resultados de
las 15 calculadoras son idénticos a los de la 2.1.1 (las pruebas de cálculo y de libros no cambiaron).

| Elemento | Cambio |
|---|---|
| `calculadoras/esquemas/` (nuevo) | Un esquema por calculadora (14), dibujado con matplotlib a partir de los datos validados y del resultado. No calcula nada nuevo: toma las dimensiones del resultado o llama a las mismas funciones del motor (Janssen del silo, elástica de la viga, geometría ISO 5048 de la banda). |
| Ventana de calculadora | Pestañas «Resultados» y «Esquema». El esquema se redibuja 0.5 s después de cambiar un dato (si los datos son válidos) y al presionar Calcular; con datos incompletos conserva el último dibujo y lo indica. Barra de matplotlib para acercar, desplazar, volver y guardar la imagen. Sin matplotlib, la pestaña lo avisa y el cálculo sigue igual. |
| Bomba centrífuga | Sin esquema ni pestaña nueva (decisión del usuario); conserva su gráfica de la curva del sistema e imágenes NPSH de siempre. |
| Dibujos a escala | Silo (elevación + diagrama de presiones p_h de Janssen), tolva (frente y planta, ángulos de cara y arista), banda (sección con A₁ y A₂ de ISO 5048 + perfil con L, H, δ), helicoidal (elevación con hélice al paso real + sección con la carga CEMA), elevador (elevación con tramo intermedio interrumpido + detalle del tambor y cangilones al paso real), aerodeslizador (sección + perfil), secador (tambor D × L), viga (elevación, cargas, reacciones, deformada amplificada y sección), secciones de ductos y tuberías. |
| Esquemas sin escala | Torre (con escala de temperaturas a escala: rango y aproximación), colector, soplador, bomba de vacío (con escala de presión absoluta a escala) y transportador neumático. |
| Elementos indicativos (rotulados) | Cámara de aire del aerodeslizador, aros, corona y aletas del secador, número de mangas del colector, techo del silo y forma de la sección personalizada de la viga: no se calculan y la figura lo dice. |
| Pruebas | `tests/test_esquemas.py` (37): todos los esquemas con el caso ordinario, 16 variantes y los ejercicios de libros; coherencia geométrica (áreas de la banda = A₁ y A₂ calculadas; alturas del silo; p_h de Janssen en el fondo = resultado; deflexión dibujada = δ máx). `tests/test_interfaz.py`: pestaña presente en 14 calculadoras y ausente en la bomba; redibujo al cambiar datos y manejo de datos incompletos. |
| Documentación | `docs/capturas/esquemas/*.png` (14), README, catálogo (línea «Esquema ajustable»), versión 2.2.0. |

