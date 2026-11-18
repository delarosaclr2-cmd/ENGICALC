# Manual de usuario — HVAC Industrial Engineering Calculator v1.0

## 1. Flujo de trabajo recomendado

1. **Propiedades del aire**: temperatura, altitud o presión barométrica, humedad relativa.
2. **Caudales**: propósito del sistema y métodos de ventilación general (ACH, dilución, térmico, ocupación).
3. **Campanas de extracción**: una campana por cada fuente, con su geometría, velocidad de captura y entrada.
4. **Redes ramificadas**: nodos (campanas, uniones, ventilador y descarga) y tramos con su geometría, material,
   accesorios y equipos.
5. **Pérdidas de presión**: revisión del camino crítico, componentes dominantes y estado de diseño del filtro.
6. **Selección de ventiladores**: curvas del fabricante, ventilador seleccionado y velocidad.
7. **Potencia y motores**: eficiencias, margen, horas, tarifa y perfil de carga.
8. **Memoria de cálculo**: datos del proyecto, dictamen, comparador de alternativas y exportación PDF/Excel.

El cálculo es automático: cada cambio recalcula en segundo plano en menos de un segundo. También puede pulsar
**Calcular** o la tecla **F5**. El resultado global aparece en la barra inferior.

## 2. Unidades

Elija **SI** o **Imperial (IP)** en la barra superior o en Configuración. Internamente todo se calcula en SI. Al
cambiar de sistema, los campos y las tablas se convierten automáticamente. En SI, el caudal puede mostrarse en m³/h,
m³/s o L/s (Configuración).

Los campos numéricos aceptan punto o coma decimal. Un campo en rojo indica un valor inválido o fuera de rango; el valor
anterior se conserva.

## 3. Páginas

### 3.1 Dashboard
Indicadores (caudal, presión, potencia, motor, velocidades, densidad, energía), conteo de alertas por nivel,
esquema del sistema (Gráfico 1) y evaluación por módulo.

### 3.2 Propiedades del aire
- **Condición**: personalizada, aire estándar ASHRAE o AMCA, o atmósfera estándar a la altitud.
- Si marca *Usar presión barométrica medida*, esa presión prevalece. Si además indica la altitud, el programa
  verifica la coherencia entre ambas.
- **Densidad declarada**: solo verifica; el cálculo usa siempre la densidad calculada.
- **Temperatura superficial mínima de ductos**: activa la verificación de riesgo de condensación.

### 3.3 Caudales
El **propósito** cambia los criterios. Por ejemplo, con *Control de contaminantes* el programa advierte si solo se
usan renovaciones por hora y recomienda captura localizada cuando la fuente es identificable. Los valores Rp, Ra y Ez
de ASHRAE 62.1 y el VLE del contaminante deben tomarse de las publicaciones oficiales.

### 3.4 Campanas de extracción
Agregue una campana y elija su tipo. Solo se muestran los parámetros que usa la ecuación de ese tipo. La entrada
puede ser simple (Fh·VPd, con valores de biblioteca) o compuesta (ranura + pleno). La guía de velocidades de captura
ACGIH aparece a la derecha. Las campanas se vinculan a los nodos de la red mediante la columna *Campana vinculada*.

### 3.5 Diseño de ductos
Herramienta independiente de dimensionamiento con tres métodos: velocidad constante, fricción constante y
recuperación estática. La regla de redondeo *Inferior* toma el diámetro comercial menor; es la práctica para
transporte de partículas porque mantiene la velocidad de transporte.

### 3.6 Pérdidas de presión
Tablas por tramo (fricción, locales, entrada, equipos, descarga, presiones total y estática al inicio y al final),
accesorios con su K, sección de referencia y fuente, y equipos en estado de diseño y con filtro limpio. Incluye los
Gráficos 4 y 6.

### 3.7 Redes ramificadas
- **Nodos**: tipo (campana, unión, ventilador, descarga). Para campanas: vínculo a la campana y, si quiere, Q forzado y
  temperatura del aire captado. Para la descarga: K de salida y altura sobre la cubierta. Para el ventilador: área de
  descarga, usada para obtener FSP.
- **Tramos**: desde/hacia, sección, dimensiones, longitud, material (o ε propia), K de compuerta y clase de
  contaminante (opcional; por defecto se hereda la más exigente aguas arriba).
- **Accesorios y equipos del tramo seleccionado**: cada accesorio indica su K de biblioteca o del usuario y su área de
  referencia. Las uniones se modelan como accesorios del tramo que llega (entrada de ramal a 30°/45°).
- La línea **Topología** valida la red en tiempo real: un ventilador, una descarga y un árbol convergente.
- Resultados: balance en uniones (relación r, acción, caudal corregido exacto y aproximado) y caudales por campana
  (requerido, diseño balanceado y operación real). Incluye los Gráficos 7 y 3.

### 3.8 Selección de ventiladores
- Agregue curvas manualmente o importe CSV/Excel con encabezados `Q, P, eta, W` (eta en fracción o %). Al importar,
  el programa pregunta las unidades.
- Indique las rpm de la curva, la densidad de referencia, la base de presión (total o estática), el área de descarga,
  las rpm máximas y el rango recomendado si el fabricante lo publica. Marque *Certificada* solo si la curva tiene
  respaldo del fabricante.
- **Velocidad de operación** y **diámetro** aplican las leyes de semejanza a la curva seleccionada.
- El Gráfico 5 muestra la curva del ventilador corregida, las curvas del sistema (filtro saturado y limpio), el punto
  de operación, el BEP, el punto de diseño requerido y la zona inestable.

### 3.9 Potencia y motores
La eficiencia del ventilador solo se usa si la curva no trae potencia ni eficiencia, y debe estar en la misma base que
la presión. El margen se aplica una sola vez. El factor de servicio es informativo. El perfil de carga compara la
regulación por compuerta con el variador de frecuencia.

### 3.10 Memoria de cálculo
- Datos del proyecto que aparecen en la portada.
- **DICTAMEN Y RECOMENDACIONES DE INGENIERÍA** con sus 12 apartados.
- **Comparador**:
  1. Use *Guardar estado actual como alternativa*.
  2. Modifique el diseño (diámetros, ventilador, rpm…) y guarde otra alternativa. Repita hasta tener al menos tres.
  3. Califique la complejidad de instalación y la dificultad de mantenimiento (1–5).
  4. Pulse *Comparar*.

  Primero se excluyen las alternativas con riesgo crítico, déficit de caudal o velocidad de transporte insuficiente.
  Luego se puntúan las elegibles.
- **Generar memoria PDF** y **Exportar Excel**.

### 3.11 Base de datos
Materiales y rugosidad, accesorios (K y fuente), entradas de campana, velocidades de transporte y de captura,
referencias, motores y diámetros comerciales. *Guardar* escribe en `%APPDATA%\HVAC_Industrial_Calculator\database`.
*Restaurar* recupera los valores de fábrica.

### 3.12 Configuración
Unidades, autoguardado, método de fricción, puntos de la curva del sistema, criterios de evaluación (valor, base,
nivel y fuente) y pesos del comparador.

## 4. Alertas y dictamen

| Nivel | Significado |
|---|---|
| CRÍTICO | Resultado físicamente inválido o condición insegura respaldada por física o referencia |
| ALTO | Problema importante que debe corregirse antes de aprobar |
| MEDIO | Condición que requiere revisión u oportunidad de mejora |
| BAJO | Recomendación de optimización |
| INFO | Observación, hipótesis o dato pendiente |
| CORRECTO | Verificación satisfactoria |

Equivalencia con la clasificación general: CRÍTICO → CRÍTICA; ALTO/MEDIO → ADVERTENCIA; BAJO/INFO → INFORMATIVA.
Un criterio de tipo *hipótesis* nunca genera una alerta CRÍTICA.

Cada módulo emite una de estas decisiones:
- técnicamente aceptable bajo las hipótesis;
- aceptable con observaciones;
- requiere modificaciones;
- no recomendable;
- información insuficiente.

## 5. Archivos

- Proyectos: `*.hvac.json`, legibles y versionables. **Guardar como** pide un nombre. El ejemplo no se sobrescribe.
- Autoguardado cada N minutos en `%APPDATA%\HVAC_Industrial_Calculator\autosave.hvac.json`. Para restaurarlo use
  *Archivo → Recuperar autoguardado*.
- Al cerrar con cambios sin guardar, el programa pregunta si desea guardarlos.
- *Archivo → Exportar todas las gráficas (PNG)*. Cada gráfico también tiene su botón de guardado en la barra de
  herramientas.

## 6. Convenciones físicas

- Presiones manométricas referidas a la atmósfera; en la succión TP y SP son negativas.
- FTP = TP_salida − TP_entrada; FSP = FTP − VP_salida (AMCA 210).
- Caudal del ventilador = caudal real a la entrada del ventilador (ṁ/ρ con la temperatura de mezcla).
- La pérdida de descarga (K = 1 por defecto) ocurre fuera del ducto: en la boca de salida SP = 0 y TP = VP.

## 7. Banco de pruebas incluido

`examples/nave_industrial_4_campanas.hvac.json` modela una nave en el Valle de México (2 240 m) con:
- vaciado de sacos, soldadura, llenado de sacos y transferencia de banda;
- colector de mangas, ventilador y chimenea;
- tres curvas de ventilador **sintéticas** de demostración;
- cuatro alternativas guardadas.

Los datos de equipos son hipótesis del ejemplo y deben sustituirse por datos de fabricante en proyectos reales.
