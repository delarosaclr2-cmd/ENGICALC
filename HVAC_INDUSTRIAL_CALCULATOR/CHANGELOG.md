# Registro de cambios

## 1.0.1 — 2026-11-18 — Correcciones de la revisión del PR (commit 9769054)

Antes de corregir se reprodujeron los hallazgos con los casos del revisor. Se añadieron 27 pruebas de regresión en
`tests/test_regresion_revision.py`. Resultado: 140/140 pruebas y 204/204 comprobaciones numéricas.
Detalle técnico en `docs/AUDITORIA_TECNICA.md` (sección 3 bis) y `docs/VALIDACION.md`.

### Cambios de cálculo y validación

- **[P1] Eficiencia físicamente imposible.**
  - Cambios:
    - `FanCurve.validate()` rechaza los puntos con η_t = Q·FTP/W ≥ 1 y las eficiencias declaradas fuera de [0, 1).
    - `power_chain()` comprueba η < 1 en el punto de operación (bases total y estática) y lanza
      `PhysicalInconsistencyError`, con lo que no se selecciona motor.
    - Si la curva del ventilador seleccionado es inválida, ya no se sustituye por la eficiencia supuesta.
    - La eficiencia indicada por el usuario debe estar en (0, 1).
    - Nueva alerta MEDIO si la η declarada difiere más de 5 % de Q·P/W.
  - Archivos: `core/fan_curves.py`, `core/power.py`, `core/calculation.py`, `validation/engineering_checks.py`,
    `validation/input_validation.py`.
- **[P1] Transporte en operación real.**
  - Cambios:
    - Nueva verificación `check_transport_operation()`, que usa los caudales del punto de operación del ventilador
      seleccionado.
    - El dictamen y el comparador la incorporan.
    - El comparador reporta las velocidades de operación con su base.
  - Archivos: `validation/engineering_checks.py`, `core/calculation.py`, `validation/comparator.py`.
- **[P2] Intervalo de búsqueda del punto de operación.**
  - Cambio: las curvas se ajustan a rpm, diámetro y densidad antes de muestrear la curva del sistema, y el
    intervalo cubre el dominio ajustado.
  - Archivo: `core/calculation.py`.
- **[P2] Coherencia entre entradas y resultados.**
  - Cambios:
    - Cada `ProjectResults` guarda una huella SHA-256 de sus entradas (proyecto, configuración y base de datos).
    - `generate_pdf()` y `export_excel()` rechazan resultados desactualizados (`StaleResultsError`).
  - Archivos: `core/calculation.py`, `reports/consistency.py`, `reports/pdf_report.py`, `reports/excel_export.py`.

### Cambios de interfaz y reportes

- Antes de exportar PDF, Excel o PNG la aplicación recalcula de forma síncrona si las entradas cambiaron, y vuelve
  a ejecutar el comparador si cambiaron las alternativas.
- Los cálculos en segundo plano llevan número de secuencia: un resultado antiguo que termina tarde se descarta.
- La memoria y el Excel muestran el motivo del bloqueo de la selección de motor.
- El comparador tiene una columna "Base de V".
- El campo de eficiencia del ventilador se limita a 99 %.
- Se corrigió la doble viñeta en las conclusiones del comparador del PDF.
- Archivos: `interface/main_window.py`, `interface/pages/report.py`, `interface/pages/base.py`,
  `interface/pages/fans_power.py`, `reports/tables.py`, `reports/pdf_report.py`.

### Corrección posterior a la segunda revisión

La segunda revisión confirmó los cuatro puntos y detectó una regresión introducida por el primero. La versión 1.0.1
no se ha publicado todavía (es el contenido de este PR), por lo que la corrección se integra en esta misma entrada en
lugar de abrir una versión nueva.

- **[P2] Eficiencia estática nula en descarga libre** (`core/fan_curves.py`).
  - Defecto: `FanCurve.validate()` rechazaba todo punto con η = 0 y caudal positivo. En una curva en presión
    estática el extremo de descarga libre tiene FSP = 0 y η_s = Q·FSP/W = 0 por definición, con η_t > 0 por la
    presión dinámica de salida. La curva completa quedaba rechazada y no se seleccionaba motor.
  - Corrección: la eficiencia se interpreta en la base de presión de la curva. η = 0 se admite cuando Q = 0 o
    cuando la presión de la curva es nula; se mantiene el rechazo de η = 0 con caudal y presión positivos, de
    η < 0 y de η ≥ 100 %. La comprobación η_t = Q·FTP/W < 1 frente a la potencia absorbida no cambia.
  - Pruebas: 8 casos nuevos al final de `tests/test_regresion_revision.py`, con contraste a mano de
    VP = 60 Pa y η_t = 0.375 en el punto de descarga libre de la curva de prueba.

Total tras esta corrección: ENGICALC 389/389; HVAC 140/140 con 204/204 comprobaciones numéricas.

### Efecto en el banco de pruebas

Sin cambios en diseño, operación, potencia, motor (11 kW) ni dictamen. En el comparador, la alternativa D (BI-450)
queda excluida también por transporte insuficiente en operación real, además del déficit de caudal.

## 1.0.0

Versión inicial: 8 módulos de cálculo, red ramificada, ventiladores, potencia, dictamen, comparador, memoria PDF y
Excel, y 113 pruebas.
