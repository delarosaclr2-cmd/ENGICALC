# linea_gas v1.2.0: caída de presión en líneas de aire comprimido y gas natural

Cálculo isotérmico compresible con Darcy y Colebrook-White (Menon 2005, cap. 5). Los accesorios se suman como ΣK, con valores de la tabla 5.11 de Menon por diámetro, dentro de la misma ecuación. La ΔP se obtiene con la densidad del gas. Para aire se incluye la fórmula de Fritzsche (Menon ec. 5.34) como comparación.

```
python -m linea_gas                                   # interfaz
python -m linea_gas casos/*.json --xlsx resumen.xlsx  # las 5 líneas de PCGV-DM-014 Rev E
```

**Estado:** VALIDADA BAJO CONDICIONES DOCUMENTADAS. Aplica a flujo turbulento con Mach < 0.3, ΔP < 40 % de P₁, Z constante en el tramo y acero comercial con ε = 0.0018 in. La validación incluye 15 pruebas:
- ejemplos 5.15 y 5.17 de Menon;
- integración numérica independiente;
- tabla 5.11;
- viscosidad contra CoolProp;
- densidad de gas natural contra CoolProp;
- entradas inválidas;
- interfaz.

El cálculo usa la presión de entrada; la presión de diseño de cada línea debe confirmarla el proyecto.

Herramienta de apoyo; no sustituye la revisión de un ingeniero responsable.

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

## Interfaz (v1.1.0)

La ventana tiene el formulario a la izquierda y cuatro pestañas a la derecha:

- **Resultados**: resultados principales, tabla de resultados, verificaciones (CUMPLE en verde, NO CUMPLE en rojo) y advertencias.
- **Esquema**: la tubería con sus accesorios (cada uno con su K), presiones de entrada y salida, longitud y el perfil de presión a lo largo de la línea, con la presión mínima si se capturó. Es interactivo: rueda para acercar, arrastre para mover y cursor sobre un elemento para ver sus valores. Se puede guardar en SVG.
- **Memoria (texto)**: la memoria completa en texto plano.

Los resultados se recalculan solos medio segundo después de cambiar un dato. Si un dato es inválido, se avisa en la barra de estado y se conserva el último resultado válido.

Botones: CALCULAR, Abrir caso, Guardar caso (JSON), **Memoria PDF** (memoria de cálculo con logo, datos, supuestos, esquema, ecuaciones, sustitución de valores, resultados, verificaciones, referencias y cuadro de firmas Elaboró / Revisó / Aprobó), **Imprimir** (envía esa memoria a la impresora predeterminada de Windows), Excel y Copiar resultados. Toda exportación recalcula antes de escribir, así que el archivo nunca queda desfasado de los datos.

El esquema solo dibuja valores que ya calculó el motor; no hace cálculos propios (lo comprueba `tests/test_esquema.py`).

Dependencias: openpyxl y reportlab (las instala el lanzador la primera vez).
