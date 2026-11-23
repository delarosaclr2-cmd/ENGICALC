# linea_gas v1.2.1: caída de presión en líneas de aire comprimido y gas natural

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

## Correcciones de la revisión del PR (v1.2.1)

Seis hallazgos de la revisión. Los tres primeros podían producir un CUMPLE indebido.

| # | Qué pasaba | Qué se hizo |
|---|---|---|
| P1-1 | Se aceptaba una corrosión anual, una vida útil o un sobreespesor **negativos**, que engrosaban la pared y elevaban la presión admisible (en DM-012, de ~991 a ~1,890 psig: el dictamen pasaba de NO CUMPLE a CUMPLE). | `presion.sobreespesor`, `presion.espesores` y `espesor.verificar` rechazan esos valores antes de calcular, con el mensaje de qué dato está mal. |
| P1-2 | Con `t ≥ D/6` o `P/(S·E) > 0.385` se avisaba del dominio, pero se conservaba la presión y se dictaminaba **CUMPLE** con la ec. (3a), que ASME B31.3 §304.1.2(b) no autoriza ahí. | Las verificaciones de presión y de espesor salen **NO EVALUABLE**, sin margen; la presión se conserva marcada «fuera de dominio» como referencia. El motivo y los números van en la referencia de la fila. |
| P2-5 | El cuadro 4 de la NOM-007 (que llega a 500 K) se leía aunque **no se pidiera Barlow**, e interrumpía el cálculo ASME a 300 °C, temperatura que sí está en la tabla A-1 implementada. | El factor T solo se evalúa cuando hay cedencia capturada, es decir cuando sí se va a calcular Barlow. El cálculo ASME es independiente. |
| P1-3 | La presión de operación se pasaba a manométrica restando **101325 Pa fijos**, aunque el caso permite capturar otra atmósfera. En el caso L1 con 10 psia de sitio y 114.2 psig de entrada se verificaba contra 109.5 psig, y con S de 1,700 psi eso convertía un NO CUMPLE en CUMPLE. | Se resta la atmósfera del sitio (`caso.p_atm_sitio_pa`), la misma con la que se convierten las entradas. |
| P2-4 | La **capacidad máxima** salía de `v_máx·A` con la densidad de **entrada**, pero la verificación usa la velocidad de **salida**, mayor al caer la presión. A 15 m/s anunciaba 3,577.63 Nm³/h, caudal con el que la salida llega a 19.30 m/s y la propia calculadora dice NO CUMPLE. | El caudal de capacidad se resuelve con el modelo del tramo, de modo que la velocidad gobernante iguale el límite: 3,026.15 Nm³/h. El barrido de diámetros y la curva v(Q) también informan la velocidad de salida y la ΔP del modelo completo. |

Estado de las verificaciones: **CUMPLE**, **NO CUMPLE**, **INFORMATIVO** (criterio que no aplica a este servicio) y **NO EVALUABLE** (el método no cubre ese caso). El último es nuevo y aparece con fondo gris en la interfaz y en el PDF.

Pruebas de regresión en `tests/test_revision_pr.py`, con los mismos números de los escenarios reportados.

## Segunda ronda de comentarios del PR (v1.2.2)

| # | Qué pasaba | Qué se hizo |
|---|---|---|
| C-2 | La **capacidad máxima** se mostraba con redondeo al más cercano. En gas (DM014E_L1, v máx 15 m/s) la tabla anunciaba 3,026.15 Nm³/h, que al reintroducirse daba 15.000010344 m/s y NO CUMPLE. El mismo defecto estaba en la fila «Capacidad máxima» de la memoria y en la etiqueta de la gráfica. | `seleccion.redondeo_seguro`: la capacidad máxima se redondea **hacia abajo**; el caudal mínimo y el diámetro requerido, **hacia arriba**. La tabla comprueba el valor mostrado reintroduciéndolo con el modelo del dictamen. El criterio físico no cambia: 3,026.15 sigue siendo NO CUMPLE. |
| C-3 | El **caudal mínimo** se resolvía con la velocidad de salida, pero el dictamen juzga el mínimo con la de **entrada** (la menor del tramo); el estado del barrido hacía lo mismo. En el escenario de vapor el mínimo mostrado dejaba la entrada en 29.73 m/s, por debajo de 30.5. | `limites_de_caudal`: Q_mín = v_mín·A con la velocidad de entrada. `estado_velocidad(v, …, v_baja)`: el máximo con la mayor velocidad del tramo y el mínimo con la menor, igual que el dictamen. En líquidos ambas son iguales y nada cambia. |

El comentario de K por diámetro no aplicaba a gas: su barrido ya corre `calcular()` con el NPS de cada diámetro, que retoma los K tabulados de ese NPS y conserva los capturados. Se agregó una prueba que lo comprueba fila por fila. Pruebas: `test_capacidad_mostrada_reintroducida_cumple_con_el_limite`, `test_caudal_minimo_mostrado_deja_la_entrada_en_el_intervalo`, `test_barrido_de_gas_coincide_con_el_calculo_completo_en_otro_diametro` y las comunes de `seleccion`.
