# Registro de cambios

## 1.0.1 — 2026-11-18 — Correcciones de la revisión del PR (commit 9769054)

Antes de corregir se reprodujeron los cuatro hallazgos con los casos del revisor. Se añadieron 19 pruebas de
regresión en `tests/test_regresion_revision.py`. Resultado: 132/132 pruebas y 199/199 comprobaciones numéricas.
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

### Efecto en el banco de pruebas

Sin cambios en diseño, operación, potencia, motor (11 kW) ni dictamen. En el comparador, la alternativa D (BI-450)
queda excluida también por transporte insuficiente en operación real, además del déficit de caudal.

## 1.0.0

Versión inicial: 8 módulos de cálculo, red ramificada, ventiladores, potencia, dictamen, comparador, memoria PDF y
Excel, y 113 pruebas.
