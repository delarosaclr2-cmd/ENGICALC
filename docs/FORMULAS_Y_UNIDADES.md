# Fórmulas, unidades y convenciones

Este documento describe las bases comunes de cálculo. Las ecuaciones de cada calculadora, con sus datos, rangos y resultados de ejemplo, están en `CATALOGO_DE_CALCULADORAS.md` (generado del código) y en la memoria de cálculo PDF/Excel de cada corrida.

## 1. Convenciones

| Tema | Convención |
|---|---|
| Sistema de unidades | SI en todas las calculadoras, salvo **bomba centrífuga** (unidades de EE. UU.: gpm, ft, psi, HP, como el original y sus imágenes de NPSH) y la parte interna del **helicoidal** (el método original trabaja en lb/h, ft³/h y ft; las entradas son SI y la conversión es interna y visible en las ecuaciones). |
| Unidades en pantalla | Cada dato y cada resultado muestran su unidad. Las salidas en otra unidad se presentan como resultado adicional (nivel D). |
| Separador decimal | Se acepta punto o coma al capturar. |
| Presiones | «manométrica» = relativa a la atmósfera del sitio; «absoluta» = relativa al vacío. Cada campo lo indica. En la bomba de vacío la succión es **absoluta**. |
| Presión atmosférica | Atmósfera estándar por altitud (sección 3.1), no 101.3 kPa fijo. La altitud del sitio por defecto se configura en `config/configuracion.json` y se puede cambiar en cada cálculo. |
| Caudal de gas | A condiciones de succión (reales), salvo indicación contraria en el campo. |
| Densidad de sólidos | **Aparente a granel** (la que define el volumen de equipos), no la densidad de partícula. |
| Humedad de sólidos | Base húmeda (% del peso total) o base seca (kg agua/kg sólido seco × 100), según se elija. |
| Eficiencias | El campo indica si es fracción (0–1) o porcentaje (0–100). |
| Factor de fricción | Siempre **Darcy** (4 veces el de Fanning). |
| Ángulos | En grados. Inclinaciones positivas cuando el transporte sube. |
| Datos capturados vs. tablas | Un valor capturado (> 0) siempre tiene prioridad sobre la lista o tabla del original; 0 = usar la tabla (nivel O). Cuando el dato sustituye a la opción elegida, se indica en las notas. |
| Resultados | Cada resultado lleva nivel de confianza: **V** verificada, **E** empírica con referencia, **O** criterio original sin fuente (no validado), **D** dato o conversión. |

## 2. Constantes y factores de conversión (`calculadoras/nucleo/constantes.py`)

| Magnitud | Valor | Origen |
|---|---|---|
| Gravedad estándar g | 9.80665 m/s² | Definición |
| Constante del aire seco R | 287.042 J/(kg·K) | ASHRAE Fundamentals |
| Relación de calores específicos del aire k | 1.4 | Gas ideal diatómico |
| cp aire seco / vapor / agua líquida | 1.006 / 1.86 / 4.186 kJ/(kg·K) | ASHRAE (aire, vapor); valor usual (agua) |
| Entalpía de vaporización a 0 °C | 2 501 kJ/kg | ASHRAE |
| Relación de masas molares agua/aire | 0.621945 | ASHRAE |
| Atmósfera normal | 101 325 Pa | Definición |
| 1 in / 1 ft | 0.0254 / 0.3048 m | Definición |
| 1 lb | 0.45359237 kg | Definición |
| 1 gal (EE. UU.) | 3.785411784 L | Definición |
| 1 ft³/min (CFM) | 4.71947×10⁻⁴ m³/s | Derivada |
| 1 gpm | 0.002228 ft³/s | Derivada |
| 1 lb/ft³ | 16.0185 kg/m³ | Derivada |
| 1 mm H₂O | 9.80665 Pa | Convencional |
| 1 psi | 6 894.757 Pa | Derivada |
| 1 HP (mecánico) | 745.6999 W | 550 ft·lbf/s |
| ft por psi (agua) | 2.309 ft/psi (agua a ~15 °C; se divide entre GE) | Derivada |
| HP hidráulico | gpm·ft·GE/3960 | Derivada |

Los factores se comprueban en `tests/test_nucleo.py::test_conversiones_conocidas`.

## 3. Bases físicas compartidas (`calculadoras/nucleo/`)

### 3.1 Atmósfera (`atmosfera.py`)

p = 101 325·(1 − 2.25577×10⁻⁵·Z)^5.2559 [Pa], Z en m, válida de −500 a 11 000 m (ASHRAE Fundamentals, cap. 1, ec. 3). Comprobada contra la fórmula ISA independiente (error < 0.02 %). A 2 240 m: ≈ 77.2 kPa.

### 3.2 Psicrometría (`psicrometria.py`) — ASHRAE Fundamentals, cap. 1

| Propiedad | Ecuación |
|---|---|
| Presión de saturación | Hyland-Wexler (1983), ec. 5 (hielo) y 6 (agua), −100 a 200 °C |
| Humedad absoluta | W = 0.621945·p_w/(p − p_w) |
| Entalpía | h = 1.006·t + W·(2501 + 1.86·t) [kJ/kg a.s.] |
| Volumen específico | v = 287.042·(t + 273.15)·(1 + 1.607858·W)/p |
| Bulbo húmedo | Ecuación de balance de ASHRAE resuelta por bisección |
| Punto de rocío | Inversión de la presión de saturación |
| Calor latente (secador) | λ ≈ 2501 − 2.326·t [kJ/kg] (aproximación lineal) |

Sin factor de mejora f (≈ 1.004): error del orden de 0.4 % en W. Comprobado contra tablas de vapor y el ejemplo de ASHRAE a 25 °C y 50 % HR, y contra la correlación de Stull (2011) dentro de su error declarado.

### 3.3 Fluidos (`fluidos.py`)

| Concepto | Ecuación | Notas |
|---|---|---|
| Diámetro por caudal | D = √(4Q/(π·v)) | |
| Reynolds | Re = ρ·v·D/μ | |
| Viscosidad del aire | Sutherland: μ = 1.716×10⁻⁵·(T/273.15)^1.5·(273.15 + 110.4)/(T + 110.4) | |
| Densidad del aire seco | ρ = p/(R·T) | |
| Fricción laminar | f = 64/Re (Re < 2 300) | |
| Fricción turbulenta | Colebrook-White, resuelta iterativamente desde Swamee-Jain | Entre 2 300 y 4 000 (transición) se usa Colebrook y se informa el régimen |
| Pérdida en tubería | ΔP = f·(L/D)·ρ·v²/2 (Darcy-Weisbach) | |
| Pérdidas menores | ΔP = ΣK·ρ·v²/2 | K del usuario o del original (O) |
| Potencia incompresible | P = ΔP·Q/η | Ventiladores, ΔP pequeña |
| Potencia adiabática | P = k/(k−1)·p₁·Q₁·[(p₂/p₁)^((k−1)/k) − 1]/η | Sopladores, bombas de vacío |
| Potencia isotérmica | P = p₁·Q₁·ln(p₂/p₁) | Referencia inferior; anillo líquido |
| Media logarítmica | ΔT_ml = (ΔT₁ − ΔT₂)/ln(ΔT₁/ΔT₂) | Secador |

### 3.4 Sólidos a granel (`solidos.py`)

| Concepto | Ecuación | Validez |
|---|---|---|
| Descarga por orificio | Beverloo (1961): W = 0.58·ρ_b·√g·(D₀ − 1.4·d)^2.5 [kg/s] | Sólidos gruesos no cohesivos. Con partículas < ~0.4 mm sobreestima el flujo: el programa lo advierte. |
| Presiones en silo | Janssen (1895): p_h = ρ·g·R/μ·(1 − e^(−z/z₀)), z₀ = R/(K·μ), R = D/4; p_v = p_h/K; p_w = μ·p_h | Presiones estáticas de llenado; la descarga se aproxima con un factor capturado. |
| Volumen de tolva | Tronco de cono o de secciones semejantes: V = h/3·(A₁ + A₂ + √(A₁A₂)) | |
| Pérdida en lecho | Ergun: ΔP/H = 150·μ·(1−ε)²·u/(ε³·d²) + 1.75·ρ·(1−ε)·u²/(ε³·d) | Lecho fijo hasta mínima fluidización |
| Lecho fluidizado | ΔP = ρ_b·g·H | |

### 3.5 Materiales (`materiales.py`)

Una sola tabla con las densidades y ángulos de reposo de **cada** módulo original (no coinciden entre sí; ver la Fase 1). Se usan solo si el usuario deja la densidad en 0, con nivel O y una advertencia que muestra los valores de todos los módulos.

## 4. Unidades por calculadora

| Calculadora | Entradas principales | Resultados principales |
|---|---|---|
| Banda | B mm, v m/s, ρ kg/m³, L m, δ °, q kg/m | t/h, m³/h, kN, kW |
| Elevador | paso mm, cangilón L, v m/s, H m | t/h, m³/h, kW |
| Helicoidal | t/h, m, kg/m³ | lb/h, ft³/h, rpm, HP, kW |
| Aerodeslizador | mm, °, µm, Pa·s, kg/m³, m³/(min·m²) | t/h, Pa, mm H₂O, m³/min |
| Neumático | m³/h, m/s, m, mm, °C, m | mm, kg/h, t/h, Pa, cm H₂O, kW |
| Tolva | kg, m², mm | m³, m, °, kg/s, kg/min, t/h |
| Silo | kg, m, °, MPa, mm | m³, m, kPa, kN/m, mm, t/h |
| Ductos | m³/h, m/s, °C, m, mm | mm, Pa, mm H₂O, kW, HP |
| Colector | m³/h, mm H₂O, g/m³, % | m², kW, kg/h, m³ |
| Soplador | m³/h, Pa, m/s, m | kPa, kW, HP, mm |
| Bomba centrífuga | gpm, in, ft, psig, psia, cSt | ft/s, ft, HP, kW, m |
| Bomba de vacío | CFM o m³/h, kPa abs, °C, m | m³/h, kg/h, kW, HP, mm |
| Torre | kg/s, °C, kJ/(kg·K), m | kW, BTU/h, TR, kJ/kg, kg/s, kg/h |
| Secador | kg/h, %, °C, m, m/s, kJ/kg, W/(m³·K) | kg/h, kW, m, m³, kg/h y gal/h de combustible |
| Viga | m, kg, kg/m, GPa, mm, cm⁴, MPa | kN, kN·m, mm, MPa |

## 5. Límites generales de validez

- Gases como ideales; aire seco o húmedo sin corrección por polvo en la densidad.
- Flujo permanente; líquidos newtonianos en la bomba.
- Vigas: elástico lineal, pequeñas deflexiones, sección constante, sin pandeo.
- Silo: sin pandeo, viento, sismo ni presiones de descarga normativas (EN 1991-4).
- Correlaciones empíricas (Beverloo, Ua de Perry's, estructura ISO 5048, Barth) solo con los coeficientes que el usuario confirme.
- Ninguna salida sustituye la revisión y firma de un ingeniero responsable.
