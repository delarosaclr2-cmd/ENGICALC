# linea_agua v1.1.0: líneas de agua (alimentación, condensado, servicios)

Velocidad, caída de presión (Darcy-Weisbach con Colebrook-White), NPSH disponible en succiones y espesor de pared.
Propiedades del agua con **IAPWS-IF97** (región 1 y saturación) y viscosidad IAPWS 2008, implementadas en `nucleo/if97.py`
y comprobadas contra los valores de verificación de la norma y contra CoolProp (diferencia < 10⁻⁶).

```
python -m linea_agua                    # interfaz
python -m linea_agua casos/*.json       # memoria en texto de las 4 líneas de PCGV-DM-012 Rev C
```

| Archivo | Contenido |
|---|---|
| `motor.py` | Cálculo (propiedades, pérdidas, NPSH, espesor) |
| `esquema.py` | Esquema interactivo (solo dibuja resultados) |
| `memoria.py` | Memoria de cálculo (PDF, Excel, impresión) |
| `gui_tk.py` | Formulario de la ventana común (`ui/ventana.py`) |
| `nucleo/` | Tablas ASME B36.10M y Menon 5.11, Colebrook, espesor B31, IF97 |

**Estado:** VALIDADA BAJO CONDICIONES DOCUMENTADAS (agua líquida 0–350 °C, flujo lleno, Re fuera de 2100–4000). 32 pruebas: verificación IF97, Darcy independiente, espesor, NPSH, entradas inválidas, esquema, memoria e interfaz.
El espesor por B31.1 usa el S que captura el usuario (B31.1 no se proporcionó). El NPSH requiere nivel y NPSHr, que la memoria no da.

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
