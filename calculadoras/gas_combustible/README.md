# gas_combustible v1.2.0: propiedades del gas natural, flujo de turbina y consumos

Calcula a partir de la cromatografía:
- M con las masas molares de GPA 2145-16;
- SG;
- Z a la condición de referencia (CoolProp HEOS, o el valor capturado);
- densidad a la referencia;
- LHV másico = LHV volumétrico / ρ.

También calcula el flujo de turbina ṁ = HR·P/(LHV·3600) y la estadística de consumos diarios sumando todas las unidades: máximo coincidente, promedio y suma de máximos no coincidentes.

```
python -m gas_combustible casos/PCGV_cogeneracion5_turbina_LT16.json --xlsx gas.xlsx
python -m gas_combustible casos/PCGV_consumos_febrero_2024.json
```

**Estado:** VALIDADA BAJO CONDICIONES DOCUMENTADAS, con 11 pruebas. Coincide con el laboratorio (M = 17.102) y con PCGV-DM-006 Rev F (ρ = 0.723409 kg/m³ y LHV = 47 082.6 kJ/kg). La tasa de calor, la potencia y el LHV del fabricante son datos de entrada, no verificados por la calculadora.

Herramienta de apoyo; no sustituye la revisión de un ingeniero responsable.

## Interfaz (v1.1.0)

La ventana tiene el formulario a la izquierda y tres pestañas a la derecha:

- **Resultados**: resultados principales, tabla de resultados, verificaciones (CUMPLE en verde, NO CUMPLE en rojo) y advertencias.
- **Esquema**: barras de composición, diagrama del gas hacia la turbina y los consumidores (kg/h y m³/h a la referencia) y consumos diarios apilados por unidad con el máximo coincidente y el promedio. Es interactivo: rueda para acercar, arrastre para mover y cursor sobre un elemento para ver sus valores. Se puede guardar en SVG.
- **Memoria (texto)**: la memoria completa en texto plano.

Los resultados se recalculan solos medio segundo después de cambiar un dato. Si un dato es inválido, se avisa en la barra de estado y se conserva el último resultado válido.

Botones: CALCULAR, Abrir caso, Guardar caso (JSON), **Memoria PDF** (memoria de cálculo con logo, datos, supuestos, esquema, ecuaciones, sustitución de valores, resultados, verificaciones, referencias y cuadro de firmas Elaboró / Revisó / Aprobó), **Imprimir** (envía esa memoria a la impresora predeterminada de Windows), Excel y Copiar resultados. Toda exportación recalcula antes de escribir, así que el archivo nunca queda desfasado de los datos.

El esquema solo dibuja valores que ya calculó el motor; no hace cálculos propios (lo comprueba `tests/test_esquema.py`).

Dependencias: openpyxl y reportlab (las instala el lanzador la primera vez).
