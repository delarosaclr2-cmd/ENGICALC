# Calculadora de tanque pulmón de aire comprimido (v1.2.0)

Módulo para ENGICALC derivado de la auditoría de la memoria **PCGV-DM-014** (Cogeneración V).
Calcula, para un recipiente de aire comprimido y la tubería conectada a él:

- tiempo de retención sin aporte del compresor y volumen requerido para un tiempo dado;
- tiempos de carga y vacío, fracción de carga y ciclos por hora (si se captura el FAD del compresor);
- tiempo de arranque desde presión atmosférica;
- verificaciones contra los criterios del proyecto y clasificación NOM-020-STPS-2011.

## Estado

| Aspecto | Estado |
|---|---|
| Auditoría del método | CORREGIDA |
| Validación del motor | VALIDADA BAJO CONDICIONES DOCUMENTADAS: aire como gas ideal (Z verificado ≈ 0.998), presiones < 25 bar, recipiente rígido, consumo constante |
| Resultados del proyecto PCGV-DM-014 | VALIDACIÓN PENDIENTE: faltan la temperatura del aire, el FAD del compresor, las condiciones de referencia de los caudales, la cédula de la tubería y el criterio de retención |

## Uso

```
python -m tanque_pulmon                                   # interfaz gráfica (Tkinter)
python -m tanque_pulmon casos/PCGV-DM-014_caso1_retencion_105Sm3h.json
python -m tanque_pulmon caso.json --pdf reporte.pdf --xlsx reporte.xlsx
```

Desde el menú de ENGICALC:

```python
from tanque_pulmon.gui_tk import abrir
abrir(ventana_principal)      # abre la calculadora como Toplevel
```

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `constantes.py` | R del aire, condiciones de referencia (normal, estándar 60 °F, 20 °C/100 kPa), diámetros interiores ASME B36.10M (céd. 40/80) |
| `unidades.py` | Conversión de presión (absoluta/manométrica con la atmósfera del sitio), caudal, volumen y temperatura |
| `motor.py` | Ecuaciones (balance de masa). Sin interfaz ni E/S |
| `validacion.py` | Errores de entrada (bloquean) y advertencias (no bloquean) |
| `criterios.py` | Verificaciones de aceptación, NOM-020-STPS-2011 num. 7.1.1 y 14.2, B31.3 Categoría D |
| `caso.py` | Caso en unidades de usuario, archivo JSON y huella SHA-256 de las entradas |
| `reporte.py` | Ejecución, texto, Excel (openpyxl) y PDF (reportlab) |
| `gui_tk.py` | Formulario de la ventana común (`ui/ventana.py`) |
| `esquema.py` | Esquema interactivo (solo dibuja resultados) |
| `memoria.py` | Arma la memoria de cálculo (PDF, Excel, impresión) |
| `casos/` | Casos de la memoria PCGV-DM-014 (el caso 3 es un ESCENARIO con FAD supuesto) |
| `tests/` | 33 pruebas |

## Modelo

```
ṁ      = Q_ref · P_ref / (R · T_ref)                  caudal de aire libre → masa
t_ret  = V · (Ps − Pi) · T_ref / (Q_ref · P_ref · T_r)
V_req  = t · Q_ref · P_ref · T_r / ((Ps − Pi) · T_ref)
t_carga = Δm / (ṁc − ṁd);   t_vacío = Δm / ṁd;   fracción de carga = ṁd / ṁc
f_max  = ṁc / (4 · Δm)                                  ciclado máximo (ṁd = ṁc/2)
```

`V` es el volumen del tanque más el de la tubería conectada sin regulador ni válvula de retención
intermedios. Opción `n` (1 a 1.4): descarga politrópica, `Δm = ρs·V·[1 − (Pi/Ps)^(1/n)]`.

## Pruebas

```
pip install pytest openpyxl reportlab scipy CoolProp     # scipy y CoolProp son opcionales
python -m pytest -q
```

Incluyen una segunda implementación independiente: integración numérica de la descarga isotérmica
y de la adiabática (balance de masa y energía), simulación paso a paso de un compresor carga/vacío,
factor Z con CoolProp, reproducción de la memoria original y prueba de la interfaz (requiere pantalla
o `xvfb-run`). Resultado: 33/33 (motor con Python 3.13; interfaz con Python 3.12 y Tk 8.6 bajo xvfb).

## Limitaciones

- Consumo constante durante el intervalo; para consumos pulsantes (casa de filtros) usar el consumo
  de diseño o pico que defina el proyecto.
- No dimensiona el recipiente a presión (espesores, válvula de seguridad): eso corresponde a ASME BPVC
  Sección VIII y a la NOM-020-STPS-2011.
- La tabla de diámetros cubre NPS ½ a 12 en céd. 40 y 80; para otras cédulas capture Di.

Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación de un
ingeniero responsable ni constituyen una validación del proyecto.

## Velocidad por diámetro, capacidad y presión máxima (v1.1.0)

La pestaña **Tablas** y la memoria incluyen, para cada tramo de tubería conectado: la velocidad que daría cada NPS al caudal capturado,
la capacidad de la línea (caudal que agota el criterio de velocidad) y, si se capturan los datos del material
(esfuerzo admisible S y, opcionalmente, la cedencia SMYS), la presión máxima admisible por el código a presión
(ASME B31.3/B31.1) y por la ecuación de Barlow con los factores de la NOM-007-SECRE-2010.

El criterio de Barlow con factor de clase de localización es el de transporte de gas natural por ducto: fuera de ese
servicio se marca INFORMATIVO y gobierna el código a presión.

## Interfaz (v1.1.0)

La ventana tiene el formulario a la izquierda y cuatro pestañas a la derecha:

- **Resultados**: resultados principales, tabla de resultados, verificaciones (CUMPLE en verde, NO CUMPLE en rojo) y advertencias.
- **Esquema**: tanque con manómetro (Ps/Pi), válvula de seguridad con su categoría NOM-020, suministro y consumo, y la gráfica presión–tiempo (descarga o ciclo carga/vacío) con el tiempo requerido. Es interactivo: rueda para acercar, arrastre para mover y cursor sobre un elemento para ver sus valores. Se puede guardar en SVG.
- **Memoria (texto)**: la memoria completa en texto plano.

Los resultados se recalculan solos medio segundo después de cambiar un dato. Si un dato es inválido, se avisa en la barra de estado y se conserva el último resultado válido.

Botones: CALCULAR, Abrir caso, Guardar caso (JSON), **Memoria PDF** (memoria de cálculo con logo, datos, supuestos, esquema, ecuaciones, sustitución de valores, resultados, verificaciones, referencias y cuadro de firmas Elaboró / Revisó / Aprobó), **Imprimir** (envía esa memoria a la impresora predeterminada de Windows), Excel y Copiar resultados. Toda exportación recalcula antes de escribir, así que el archivo nunca queda desfasado de los datos.

El esquema solo dibuja valores que ya calculó el motor; no hace cálculos propios (lo comprueba `tests/test_esquema.py`).

Dependencias: openpyxl y reportlab (las instala el lanzador la primera vez).
