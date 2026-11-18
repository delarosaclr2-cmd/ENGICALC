# HVAC INDUSTRIAL ENGINEERING CALCULATOR

Aplicación de escritorio en Python (PySide6) para calcular, diseñar, analizar y verificar sistemas de **ventilación
general e industrial, extracción localizada, redes de ductos ramificadas y selección de ventiladores**, con memoria de
cálculo PDF, exportación Excel y un motor de dictamen técnico.

> Herramienta de apoyo al diseño. Sus resultados **no** constituyen certificación de cumplimiento normativo ni
> sustituyen la revisión y la responsabilidad del ingeniero a cargo.

## Instalación rápida (Windows)

1. Instale Python 3.11, 3.12 o 3.13 desde python.org (marque *Add Python to PATH*).
2. Descomprima esta carpeta, por ejemplo en `C:\HVAC_INDUSTRIAL_CALCULATOR`.
3. Doble clic en **`instalar_windows.bat`**. Crea un entorno virtual `.venv` e instala las dependencias.
4. Doble clic en **`ejecutar_app.bat`**. Se abre la aplicación con el banco de pruebas industrial cargado.

Instrucciones detalladas: [`docs/INSTALACION_WINDOWS.md`](docs/INSTALACION_WINDOWS.md).

Desde consola, en cualquier sistema operativo:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python main.py                     # abre el banco de pruebas industrial
python main.py --nuevo             # proyecto nuevo con una red mínima
python main.py mi_proyecto.hvac.json
python main.py --verificar         # sin interfaz: calcula el banco de pruebas y genera una memoria PDF
python -m pytest                   # pruebas: deja el registro en tests/results/
```

## Qué incluye

| Módulo | Contenido |
|---|---|
| Propiedades del aire | Psicrometría ASHRAE (Hyland-Wexler), aire seco y húmedo, densidad, viscosidad (Sutherland), rocío, bulbo húmedo, entalpía, volumen específico; atmósfera estándar y verificación presión–altitud |
| Caudales | ACH, dilución con factor de mezcla K y análisis transitorio, balance térmico sensible (base aire seco), ocupación ASHRAE 62.1 |
| Campanas | 10 geometrías (DallaValle/ACGIH), validez geométrica, pérdidas de entrada (Ce/Fh), campanas compuestas de ranura y pleno, presión estática de campana |
| Ductos | Circular/rectangular, Dh = 4A/Pm, De de Huebscher, velocidad constante, fricción constante, recuperación estática, series comerciales |
| Pérdidas | Darcy-Weisbach con Colebrook-White (también Swamee-Jain, Churchill y Altshul-Tsal), régimen transicional, accesorios con sección de referencia, equipos (fijo, ley de potencia, curva, filtro limpio/saturado) |
| Redes ramificadas | Árbol de extracción con continuidad de masa, mezcla adiabática, balance de presión total, camino crítico, equilibrado por diseño (exacto y aproximación √r), compuertas, solución de operación con la curva del ventilador |
| Ventiladores | Curvas CSV/Excel/manuales (PCHIP), leyes de semejanza (N, D, ρ), corrección por densidad, punto de operación, BEP, zona inestable, rpm requeridas, comparación de modelos |
| Potencia | P aerodinámica → ventilador → eje del motor → eléctrica; motor IEC/NEMA con margen único; energía, costo y comparación compuerta vs. variador |
| Criterio de ingeniería | Alertas de 5 niveles con criterio, consecuencia, recomendación y fuente; dictamen por módulo (diagnóstico, decisión, justificación, acción); comparador de 3 o más alternativas; recomendaciones constructivas |
| Reportes | Memoria PDF (portada, secciones 1–21, DICTAMEN, comparador, anexos de trazabilidad y validación) y libro Excel |

## Estructura

```
HVAC_INDUSTRIAL_CALCULATOR/
├── main.py                  punto de entrada
├── config/                  settings.json (criterios con base y fuente), cargador
├── core/                    motores de cálculo (sin interfaz): unidades, aire, caudales, campanas,
│                            ductos, fricción, accesorios, equipos, presión, red, ventiladores, potencia,
│                            modelo de proyecto y orquestador
├── database/                biblioteca técnica JSON editable (+ defaults de fábrica)
├── validation/              alertas, verificaciones, motor de decisión, comparador, recomendaciones
├── graphics/                7 gráficos técnicos (Matplotlib)
├── reports/                 tablas compartidas, memoria PDF (ReportLab), Excel (openpyxl)
├── interface/               PySide6: ventana principal, 12 páginas, componentes
├── tests/                   pytest (validación matemática, red, caso industrial, reportes, interfaz)
├── examples/                banco de pruebas industrial, curva CSV de ejemplo, memoria y Excel generados
├── assets/                  icono y fuentes DejaVu (licencia incluida)
└── docs/                    manual, instalación, auditoría técnica, validación, capturas
```

## Validación

`python -m pytest` ejecuta 113 pruebas con más de 180 comprobaciones numéricas contra referencias independientes:
CoolProp/IAPWS, soluciones analíticas, ecuaciones elementales y una segunda formulación del solucionador de red.
Cada comprobación queda registrada con entrada, valor esperado, valor obtenido, error absoluto, error relativo,
tolerancia y referencia en `tests/results/registro_pruebas.csv` y `.md`. Resumen y hallazgos en
[`docs/VALIDACION.md`](docs/VALIDACION.md).

## Ejecutable de Windows

`construir_exe_windows.bat` genera `dist\HVAC_Calculator\HVAC_Calculator.exe` con PyInstaller y
`hvac_calculator.spec`. Debe ejecutarse **en Windows**, porque PyInstaller no compila de forma cruzada. El archivo de
especificación se probó con una compilación en Linux: el ejecutable congelado abre la interfaz y `--verificar`
calcula y genera la memoria PDF. `HVAC_Calculator.exe --verificar` sirve para comprobar el ejecutable en Windows.

## Dependencias

PySide6, NumPy, SciPy, Matplotlib, ReportLab, openpyxl. Para las pruebas: pytest, pypdf y CoolProp. CoolProp
solo se usa como referencia independiente en las pruebas, no como motor de cálculo. No se usa Pandas: las tablas se
generan con un módulo propio (`reports/tables.py`) compartido por la interfaz, el PDF y el Excel, lo que reduce
dependencias y el tamaño del ejecutable.

## Licencias de terceros

Fuentes DejaVu: `assets/fonts/DEJAVU_LICENSE.txt`. Las normas citadas (ACGIH, ASHRAE, SMACNA, AMCA, etc.) no se
reproducen. Los valores tomados de ellas están marcados para verificación en la edición vigente.
