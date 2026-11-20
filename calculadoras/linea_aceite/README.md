# linea_aceite v1.1.0: líneas de aceite (lubricación de turbinas)

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
