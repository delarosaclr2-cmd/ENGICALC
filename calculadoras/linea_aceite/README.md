# linea_aceite v1.1.1: líneas de aceite (lubricación de turbinas)

Viscosidad a la temperatura de operación con **ASTM D341** (Menon ecs. 6.13–6.16) a partir de dos puntos de la hoja técnica,
Reynolds (Menon ec. 6.38), Darcy con altura en metros **del aceite** (ec. 6.49), flujo laminar (f = 64/Re, accesorios por
longitud equivalente) y espesor con ASME B31.3-2014 (Tabla A-1, A106 Gr. B).

```
python -m linea_aceite                  # interfaz
python -m linea_aceite casos/*.json     # las 3 líneas de líquido de PCGV-DM-017 Rev D
```

La línea de venteo del eliminador de neblina (aire) está en `linea_gas/casos/DM017_venteo_eliminador_neblina_8in.json`.

**Estado:** VALIDADA BAJO CONDICIONES DOCUMENTADAS (aceites minerales, tubería llena). 19 pruebas: ejemplo 6.6 de Menon, Hagen-Poiseuille en laminar, fórmula de Reynolds de Menon, espesor B31.3, entradas inválidas, esquema, memoria e interfaz.
Los dos puntos de viscosidad de la memoria dan 38 cSt a 40 °C, que no es ningún grado ISO VG: confirmar con la hoja técnica del aceite.

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

Estado de las verificaciones: **CUMPLE**, **NO CUMPLE**, **INFORMATIVO** (criterio que no aplica a este servicio) y **NO EVALUABLE** (el método no cubre ese caso). El último es nuevo y aparece con fondo gris en la interfaz y en el PDF.

Pruebas de regresión en `tests/test_revision_pr.py`, con los mismos números de los escenarios reportados.
