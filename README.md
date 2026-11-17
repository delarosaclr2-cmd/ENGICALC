# Calculadoras de Ingeniería RMR — versión 2.2.0

Plataforma de escritorio (Python + Tkinter) con 15 calculadoras de ingeniería auditadas, corregidas y (12 de 15) validadas contra ejemplos publicados de normas, manuales y libros de texto (ver `docs/INFORME_AUDITORIA.md`, secciones 7 y 8, y `docs/VALIDACION_CON_LIBROS.md`), un menú principal por disciplinas, esquemas ajustables de cada equipo, memoria de cálculo en PDF y Excel, y pruebas automáticas.

> **Aviso.** Herramienta de apoyo para cálculos de ingeniería. Sus resultados no constituyen una memoria certificada ni sustituyen la revisión y firma de un ingeniero responsable. Cada resultado indica su nivel de confianza; los de nivel **O** provienen de criterios del programa original sin fuente y **no están validados**.

## 1. Instalación (Windows)

1. Instale Python 3.10 o superior desde python.org (marque «Add python.exe to PATH»). Tkinter ya viene incluido.
2. Descomprima esta carpeta donde quiera (no necesita una ruta fija).
3. Doble clic en **`INSTALAR.bat`** (o, en una terminal dentro de la carpeta: `py -m pip install -r requirements.txt`).
4. Si Windows muestra «No se pudo comprobar el editor» al abrir los `.bat`, es porque el ZIP vino de internet: presione **Ejecutar**, o antes de descomprimir haga clic derecho en el ZIP → Propiedades → marque **Desbloquear**.
5. Si falta alguna biblioteca, el menú lo indica en rojo y dice qué función se afecta. El cálculo no depende de ellas: sin matplotlib la memoria PDF se genera sin gráfica; sin openpyxl no se exporta a Excel.

## 2. Uso

- Doble clic en **`INICIAR.bat`** (o `py menu_principal.py`).
- Contraseña de acceso: la misma del menú original. Para cambiarla o desactivarla: `py menu_principal.py --cambiar-contrasena` (dejarla vacía la desactiva).
- En el menú: busque por nombre o palabra clave, seleccione la calculadora y presione **Abrir calculadora** (o doble clic).
- En cada calculadora:
  - Capture los datos (los marcados con * son obligatorios). Al seleccionar un campo aparece su ayuda y su rango válido. Se acepta coma o punto decimal.
  - **Calcular** (o Enter). Si un dato no es válido, se listan todos los errores juntos.
  - La tabla muestra cada resultado con su unidad y su nivel (V, E, O, D). Abajo aparecen advertencias, ecuaciones y notas.
  - **Exportar PDF / Excel**: memoria de cálculo del último cálculo. Si cambia un dato después de calcular, el programa pide recalcular antes de exportar.
  - **Guardar caso / Abrir caso**: archivo `.json` con los datos, para repetir o revisar un cálculo. También se abre desde el menú principal (Archivo → Abrir caso guardado).
  - **Información técnica**: estados de auditoría y validación, referencias, limitaciones y archivos originales que sustituye.
  - **Pestaña «Esquema»** (todas las calculadoras excepto la bomba centrífuga): dibujo del equipo con sus datos y resultados. Se redibuja solo, medio segundo después de cambiar un dato (si los datos son válidos), y al presionar Calcular. Silo, tolva, banda, helicoidal, elevador, aerodeslizador, secador, viga y las secciones de ductos y tuberías se dibujan **a escala**; torre, colector, soplador, vacío y neumático son **esquemas sin escala** con los valores del cálculo (cada figura lo indica). La barra inferior permite acercar (lupa), desplazar, volver a la vista inicial y guardar la imagen. El esquema no calcula nada nuevo: usa los resultados del cálculo y las mismas funciones del motor, así que no puede contradecir la tabla.
- **Datos del proyecto…** (botón de cada calculadora o menú Archivo): proyecto, cliente, documento, revisión, elaboró, revisó y aprobó. Encabezan el PDF, el Excel, los casos guardados y el historial; se recuerdan entre sesiones (`registro/proyecto.json`).
- **Historial de cálculos** (menú Archivo): cada cálculo válido queda registrado en `registro/historial.jsonl`; doble clic reabre la calculadora con esos datos y recalcula.
- Otras opciones de línea de comandos:
  - `py menu_principal.py --lista` — lista las calculadoras y su estado.
  - `py menu_principal.py --calculadora bomba` — abre directamente una calculadora (ids en `docs/CATALOGO_DE_CALCULADORAS.md`).

### Niveles de confianza

| Nivel | Significado |
|---|---|
| **V** | Verificada: ecuación física o normativa comprobada con un cálculo independiente. |
| **E** | Empírica con referencia identificada (p. ej. Beverloo, Ua de Perry's): válida dentro de su campo y con los coeficientes que usted confirme. |
| **O** | Criterio o tabla del programa original sin fuente: **no validado**. Sustitúyalo por el dato del fabricante o de la norma cuando sea posible. |
| **D** | Dato capturado, conversión de unidades o valor informativo. |

### Estados de las calculadoras

Se muestran en el menú: **VALIDADA BAJO CONDICIONES DOCUMENTADAS** (ductos, viga) o **VALIDACIÓN PENDIENTE** (las demás, por depender de algún criterio sin fuente o de un coeficiente que debe confirmar la empresa). El detalle está en `docs/INFORME_AUDITORIA.md`.

## 3. Configuración — `config/configuracion.json`

| Clave | Uso |
|---|---|
| `sitio.altitud_m` | Valor inicial del campo «Altitud del sitio» (presión atmosférica). Ajústelo al sitio habitual de sus proyectos (p. ej. CDMX ≈ 2240 m). |
| `acceso.requerir_contrasena` | `true` / `false`. |
| `acceso.verificar_usuario` | `false` = como el original (solo contraseña); `true` = exige también el usuario de `acceso.usuario`. |
| `reportes.empresa`, `reportes.logo`, `reportes.elaboro` | Encabezado de la memoria de cálculo. El logo se busca en `recursos/`. |

La contraseña se guarda como hash SHA-256 con sal, no en texto plano. Es una barrera de acceso, no un mecanismo de seguridad: quien pueda editar la carpeta puede desactivarla.

## 4. Estructura

```
CALCULADORAS_INGENIERIA_VERSION_FINAL/
├── menu_principal.py          punto de entrada
├── INICIAR.bat / INSTALAR.bat / PROBAR.bat
├── requirements.txt
├── calculadoras/
│   ├── nucleo/                física y utilidades compartidas, sin interfaz
│   │   ├── constantes.py      constantes y conversiones de unidades
│   │   ├── atmosfera.py       presión por altitud
│   │   ├── psicrometria.py    aire húmedo (ASHRAE)
│   │   ├── fluidos.py         Darcy, Colebrook, compresión, etc.
│   │   ├── solidos.py         Beverloo, Janssen, volúmenes
│   │   ├── materiales.py      tabla única de materiales del original (nivel O)
│   │   ├── modelo.py          Campo, Resultado, Calculadora, validación
│   │   └── configuracion.py   lectura de config/configuracion.json
│   ├── calculos/              una calculadora por módulo (sin interfaz)
│   ├── esquemas/              esquemas ajustables (matplotlib), uno por calculadora excepto la bomba
│   └── interfaz/              menú, ventana genérica, pestaña de esquema, acceso y reportes
├── config/configuracion.json
├── recursos/                  logotipo, ícono e imágenes de referencia
├── tests/                     pruebas automáticas y evidencia numérica
├── herramientas/              generador del catálogo
└── docs/                      informe de auditoría, registro de cambios, fórmulas, catálogo, resultados
```

El cálculo está separado de la interfaz: cada módulo de `calculos/` recibe un diccionario de datos validados y devuelve un `Resultado`. Se puede usar sin ventanas:

```python
from calculadoras.calculos import POR_ID
r = POR_ID["ductos"].calcular({"caudal": 10000, "velocidad": 20, "longitud": 50, "eficiencia": 0.7})
print(r["dp_total_mmh2o"], r["potencia_kw"])
```

## 5. Cómo agregar una calculadora

1. Cree `calculadoras/calculos/mi_calculo.py`:

```python
from ..nucleo.modelo import Calculadora, Campo, Resultado, requerir, VERIFICADA

CAMPOS = [
    Campo("caudal", "Caudal", "m³/h", minimo=0, min_incluido=False, grupo="Datos"),
    Campo("eficiencia", "Eficiencia (0–1)", "", defecto=0.7, minimo=0, maximo=1, min_incluido=False, grupo="Datos"),
]

def calcular(d: dict) -> Resultado:
    r = Resultado()
    requerir(d["caudal"] < 1e6, "Caudal fuera del alcance del método.")
    r.agregar("q_m3s", "Caudal", d["caudal"] / 3600, "m³/s", 4, VERIFICADA)
    r.ecuacion("Q[m³/s] = Q[m³/h]/3600")
    return r

CALCULADORA = Calculadora(
    id="mi_calculo", nombre="Mi cálculo", disciplina="Ventilación y control de polvo",
    descripcion="Qué calcula, en una línea.", campos=CAMPOS, funcion=calcular,
    referencias=("Fuente del método.",), limitaciones=("Condiciones de validez.",),
)
```

2. Agregue `"mi_calculo"` a `_MODULOS` en `calculadoras/calculos/__init__.py` (la disciplina debe estar en `DISCIPLINAS` o se agrega al final).
3. Agregue un caso ordinario en `tests/casos.py` y sus pruebas de validación en `tests/test_calculadoras.py`.
4. (Opcional) Dibuje su esquema en `calculadoras/esquemas/` (función `(figura, datos, resultado)`) y regístrelo en `ESQUEMAS` de `calculadoras/esquemas/__init__.py`; la pestaña «Esquema» aparece sola.
5. Ejecute `PROBAR.bat` y `py herramientas/generar_catalogo.py`.

El menú, el buscador, la memoria PDF/Excel y la prueba de humo de interfaz la incluyen automáticamente.

## 6. Pruebas

`PROBAR.bat` o `py -m pytest`. Incluye:

- `test_nucleo.py`: constantes, atmósfera, psicrometría (tablas de vapor, ASHRAE, Stull), fricción, Beverloo, Janssen (contra integración numérica), validación de campos.
- `test_calculadoras.py`: cada calculadora contra cálculos independientes, casos límite y extremos, entradas inválidas y reproducción de los errores del original.
- `test_reportes.py`: PDF, Excel y casos JSON de las 15 calculadoras; configuración y contraseña.
- `test_interfaz.py`: abre el menú, entra a cada calculadora, calcula, compara la tabla con el motor, exporta, abre gráficas e imágenes y prueba entradas inválidas. Abre también cada ejercicio de libro en su ventana. Requiere pantalla.
- `test_esquemas.py`: cada esquema se dibuja con el caso ordinario, con 16 variantes y con los ejercicios de libros; la geometría dibujada coincide con el cálculo (áreas de la banda, alturas y presión de Janssen del silo, deflexión de la viga).
- `test_libros.py` y `casos_libros.py`: 8 ejercicios resueltos de libros de texto (Çengel y Cimbala, Çengel y Boles, Geankoplis, Rhodes, *Strength of Materials*) contra la respuesta publicada.
- `evidencia_original_vs_corregido.py`: tabla original / corregido / independiente (`py tests/evidencia_original_vs_corregido.py`).

## 7. Documentación

| Archivo | Contenido |
|---|---|
| `docs/INFORME_AUDITORIA.md` | Auditoría A–F por calculadora, estados, pendientes y limitaciones |
| `docs/REGISTRO_DE_CAMBIOS.md` | Cada error encontrado, su corrección y el mapa de archivos originales |
| `docs/EVIDENCIA_ORIGINAL_VS_CORREGIDO.txt` | Comparación numérica |
| `docs/FORMULAS_Y_UNIDADES.md` | Convenciones, constantes y bases físicas |
| `docs/CATALOGO_DE_CALCULADORAS.md` | Datos, rangos, ecuaciones y resultados de cada calculadora (generado) |
| `docs/RESULTADOS_PRUEBAS.txt` | Última ejecución de las pruebas |
| `docs/PROPUESTA_INTERFAZ_WEB.md` | Evaluación de una interfaz web o híbrida |
| `docs/capturas/` | Capturas del programa en ejecución |
| `docs/capturas/esquemas/` | Esquema de cada calculadora con su caso de prueba |
| `docs/VALIDACION_CON_LIBROS.md` | Ejercicios de libros de texto: datos capturados, respuesta publicada, resultado y diferencia |
| `docs/ejemplos/` | Memorias de cálculo PDF/Excel y casos JSON de ejemplo (bomba, viga, helicoidal, torre, ductos) |
| `docs/ejemplos/libros/` | Un caso JSON por ejercicio de libro: Archivo → «Abrir caso guardado…» lo abre con los datos del ejercicio y calcula |

## 8. Errores inesperados

Si algo falla en la interfaz, el programa muestra un mensaje y guarda el detalle en `registro/errores.log`. Si falta una biblioteca, indica ejecutar `INSTALAR.bat`.
