# linea_vapor v1.1.1: líneas de vapor saturado y sobrecalentado

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

## Correcciones de la revisión del PR (v1.1.1)

Seis hallazgos de la revisión. Los tres primeros podían producir un CUMPLE indebido.

| # | Qué pasaba | Qué se hizo |
|---|---|---|
| P1-1 | Se aceptaba una corrosión anual, una vida útil o un sobreespesor **negativos**, que engrosaban la pared y elevaban la presión admisible (en DM-012, de ~991 a ~1,890 psig: el dictamen pasaba de NO CUMPLE a CUMPLE). | `presion.sobreespesor`, `presion.espesores` y `espesor.verificar` rechazan esos valores antes de calcular, con el mensaje de qué dato está mal. |
| P1-2 | Con `t ≥ D/6` o `P/(S·E) > 0.385` se avisaba del dominio, pero se conservaba la presión y se dictaminaba **CUMPLE** con la ec. (3a), que ASME B31.3 §304.1.2(b) no autoriza ahí. | Las verificaciones de presión y de espesor salen **NO EVALUABLE**, sin margen; la presión se conserva marcada «fuera de dominio» como referencia. El motivo y los números van en la referencia de la fila. |
| P2-5 | El cuadro 4 de la NOM-007 (que llega a 500 K) se leía aunque **no se pidiera Barlow**, e interrumpía el cálculo ASME a 300 °C, temperatura que sí está en la tabla A-1 implementada. | El factor T solo se evalúa cuando hay cedencia capturada, es decir cuando sí se va a calcular Barlow. El cálculo ASME es independiente. |
| P2-4 | La **capacidad máxima** salía de `v_máx·A` con el volumen específico de **entrada**, pero la verificación usa la mayor velocidad del tramo, que es la de salida. El escenario de 150 m anunciaba 130,411 kg/h, caudal con el que la salida llega a 55.04 m/s frente al límite de 50.9. | El caudal se resuelve marchando el tramo con el mismo modelo del dictamen: 121,887.7 kg/h, que da 50.90 m/s a la salida. La marcha por segmentos se extrajo a `motor.marcha()` para no duplicar la física; las marchas auxiliares usan `N_SEG_BARRIDO` segmentos, con la convergencia comprobada en `test_segmentacion_converge`. Sin longitud ni accesorios el comportamiento no cambia. |

Estado de las verificaciones: **CUMPLE**, **NO CUMPLE**, **INFORMATIVO** (criterio que no aplica a este servicio) y **NO EVALUABLE** (el método no cubre ese caso). El último es nuevo y aparece con fondo gris en la interfaz y en el PDF.

Pruebas de regresión en `tests/test_revision_pr.py`, con los mismos números de los escenarios reportados.
