# linea_vapor v1.1.0: líneas de vapor saturado y sobrecalentado

Velocidad (Menon ec. 4.24), caída de presión por segmentos con flujo adiabático y **IAPWS-IF97** (la densidad sigue a la presión),
velocidad sónica de referencia (Menon ec. 4.25), caudal real de venteo a silenciador (expansión isentálpica) y espesor de pared.

```
python -m linea_vapor                   # interfaz
python -m linea_vapor casos/*.json      # las 4 líneas de PCGV-DM-011 Rev D
```

Criterio por defecto: Menon (2005) tabla 4.4, vapor saturado ≥ 345 kPa g, 30.5–50.9 m/s.

**Estado:** VALIDADA BAJO CONDICIONES DOCUMENTADAS (regiones 2 y 4 de IF97, sin región 3; ΔP < 70 % de p₁; tubería aislada). 30 pruebas: verificación IF97, velocidades de la memoria, ΔP contra integración independiente con CoolProp (IAPWS-95), venteo, espesor, entradas inválidas, esquema, memoria e interfaz.

## Presión máxima admisible y selección de diámetro (v1.1.0)

Cada cálculo entrega además, en la pestaña **Tablas** y en la memoria:

1. **Velocidad por diámetro** al caudal capturado: NPS, Di real, v en m/s y ft/s, Reynolds, ΔP por fricción y el
   estado contra el criterio de velocidad. Marca con `*` el diámetro en uso.
2. **Capacidad de la línea**: el caudal que corresponde a la velocidad mínima, a la capturada y a la máxima. El de la
   velocidad máxima es la capacidad de la línea con ese criterio.
3. **Presión máxima admisible** por tres espesores (nominal, nominal − tolerancia y − corrosión) y por dos criterios:
   - **Código a presión** (ASME B31.3 §304.1.2 / B31.1 §104.1.2): P = 2·S·E·W·t/(D − 2·Y·t). Es el que gobierna.
   - **Barlow con factores de la NOM-007-SECRE-2010** (el de las memorias originales): P = 2·S·t·F·E·T/D, con S la
     cedencia mínima especificada (SMYS), F por clase de localización (cuadro 2), E por tipo de junta (cuadro 3) y T
     por temperatura (cuadro 4, interpolación directa).

La que gobierna es la calculada con el espesor **nominal − tolerancia de fabricación − sobreespesor por corrosión**:
es la que la tubería soporta al final de su vida útil con el tubo en el límite inferior de fabricación.

**La NOM-007-SECRE-2010 rige el transporte de gas natural por ducto.** En cualquier otro servicio, el resultado de
Barlow se marca INFORMATIVO y solo sirve para comparar con la memoria original; el dictamen lo da el código a presión.
Si la línea sí es de transporte de gas natural, ponga `aplica_nom` en `true` y entonces Barlow dictamina.

No se evalúan: presión de prueba hidrostática, expansión térmica, cargas externas, refuerzo de ramales ni clase de
bridas, válvulas y juntas. La presión máxima de un sistema la limita el componente más débil, que no se calcula aquí.

## Interfaz

Formulario a la izquierda y cuatro pestañas a la derecha: **Resultados** (valores principales, tabla, verificaciones en color y advertencias), **Tablas** (los tres cuadros de arriba), **Esquema** interactivo (rueda para acercar, arrastre para mover, cursor para ver valores; se guarda en SVG) y **Memoria (texto)**. Se recalcula sola medio segundo después de cada cambio. Botones: CALCULAR, Abrir/Guardar caso, **Memoria PDF**, **Imprimir**, Excel y Copiar resultados. Toda exportación recalcula antes de escribir.

Verificaciones: CUMPLE (verde), NO CUMPLE (rojo) e INFORMATIVO (amarillo; p. ej. velocidad por debajo del intervalo recomendado, que solo indica tubería holgada).

Dependencias: openpyxl y reportlab (las instala el lanzador). No requiere CoolProp: las propiedades se calculan con código propio verificado.

Herramienta de apoyo; no sustituye la revisión de un ingeniero responsable.
