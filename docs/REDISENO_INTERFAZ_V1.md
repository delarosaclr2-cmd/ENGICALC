# Rediseño de interfaz v1 — fase 1 (Tkinter)

Rama: `feature/jmanuel/rediseno-interfaz` · Base: `main` en `be6e273` (PR #7) · Fecha: 24/11/2026

Implementa la propuesta «Rediseño ENGICALC» (sistema de componentes, menú principal, arquetipo A
de calculadora y memoria completa) en las ventanas Tkinter. **HVAC industrial (PySide6) queda fuera
de esta fase.**

Regla del diseño que se respetó en todo el cambio: *el cálculo no cambia*. Solo se tocaron
disposición, estilo y agrupación. Etiquetas técnicas, unidades, valores, validaciones, ecuaciones,
avisos, casos guardados, historial y exportaciones PDF / Excel / «Copiar resultados» se generan
exactamente igual que antes.

## 1. Qué cambió

| Área | Archivos | Cambio |
|---|---|---|
| Sistema visual | `calculadoras/interfaz/tema.py` (nuevo) | Paleta RMR (marino, azul de acción, estados), tipografía IBM Plex → Segoe UI / Consolas → DejaVu, estilos ttk sobre el tema `clam` (el tema `vista` no permite colorear botones ni bordes), piezas comunes: tarjeta, pastilla de unidad, insignia de nivel, aviso, pestañas, barra de estado, diálogo base, iconos. |
| Calculadoras (15) | `interfaz/ventana.py`, `tabla_resultados.py` (nuevo), `panel_esquema.py`, `kpi.py` (nuevo) | Encabezado con logotipo y ruta; título con etiqueta «sin guardar / guardado»; barra de acciones con una sola acción primaria (Calcular), Caso ▾ y Exportar ▾ (de 9 botones a 5 controles). Datos en tarjetas por grupo con unidad en pastilla; obligatorios pendientes en ámbar con conteo por grupo; errores de validación marcados en el campo con el mensaje existente debajo. Resultados: KPI, panel ámbar de advertencias, pestañas Resultados · Esquema · Ecuaciones y notas, tabla con valor en mono e insignia V/E/O/D por fila, estado vacío con la lista de obligatorios pendientes. Esquema con barra compacta (Restablecer vista, Acercar, Desplazar, Guardar imagen…). |
| Menú principal | `interfaz/menu.py`, `preferencias.py` (nuevo), `acceso.py` | Encabezado con logotipo, conteo y buscador; categorías con conteo; favoritos (estrella en el catálogo o tecla F) y recientes; catálogo con descripción; ficha con estado de validación y limitaciones principales en recuadro ámbar. Diálogos con formato común: Acceso, Datos del proyecto, Información técnica, Niveles de confianza, Historial. |
| Memorias (3) | `memorias/ventana.py` | Ruta y título, Exportar ▾ como acción principal (actualización automática), subpestañas segmentadas, KPI en mono, colores de serie de gráfica del diseño (equipo azul, sistema naranja, afinidad gris discontinuo, operación marino). |
| Aplicaciones Tk (6) | `<app>/<app>/ui/ventana.py`, `<app>/<app>/ui/tema.py` (copia) | Mismo encabezado, tarjetas de datos con pastilla de unidad cuando la etiqueta termina en una unidad simple, panel ámbar de advertencias, KPI, Exportar ▾ primario, barra de estado. `ui/tema.py` es copia idéntica de `interfaz/tema.py` para que cada aplicación siga funcionando sola desde su carpeta; una prueba impide que las copias diverjan. |
| Esquemas | `calculadoras/esquemas/base.py` | Solo la paleta de trazo (geometría, material, cotas, título, ficha de resumen). Dibujo a escala, cotas y valores sin cambio. Los esquemas no forman parte de PDF ni Excel. |
| Preferencias | `.gitignore` | `registro/preferencias_menu.json` (favoritos y recientes de cada equipo) no se versiona. |

## 2. Decisiones tomadas por confiabilidad

1. **Niveles V / E / O / D.** La maqueta de la calculadora muestra solo R y E. Se conservan los
   cuatro niveles del programa (como en el sistema de componentes): ocultar la O escondería
   resultados no validados. La insignia O lleva contorno ámbar.
2. **«Valores por defecto»** conserva su nombre en las calculadoras: restablece valores por defecto, no
   carga un caso de ejemplo («Restablecer ejemplo» solo existe en las memorias, donde sí es un ejemplo).
3. **Aplicaciones de líneas, gas y tanque:** se actualizan solas, por eso Exportar ▾ es la acción
   principal; se conserva un botón «Calcular» secundario porque es el único que muestra el error en un
   diálogo.
4. **Nota de cada resultado** (`Salida.nota`): antes no se veía en la tabla. Ahora aparece al pasar
   el cursor sobre la insignia de nivel o sobre «ⓘ». Se rotula «Nota», no «Fuente», porque no todas las
   notas son referencias.
5. **Advertencias:** van en el panel ámbar con su texto literal y además al final de la pestaña
   «Ecuaciones y notas». Con muchas advertencias el panel se desplaza por dentro (4 renglones en
   ventanas bajas) para no empujar los resultados fuera de la ventana.

## 3. KPI propuestos — pendientes de confirmación del responsable técnico

Paso 3 de la guía del diseño. Cada KPI es una salida que la calculadora ya calcula; se muestra con el
mismo texto, unidad y nivel que la tabla. Se cambian en `calculadoras/interfaz/kpi.py`.

| Calculadora | KPI (unidad, nivel) |
|---|---|
| Aerodeslizador | Capacidad de transporte (t/h, **O**) · Caudal de aire de fluidización (m³/min, V) · ΔP a través del lecho (Pa, V) · ¿El lecho se fluidiza? (—, V) |
| Banda transportadora | Capacidad másica (t/h, V) · Capacidad volumétrica (m³/h, V) · Potencia requerida del motor (kW, E) · Fuerza tangencial F_U (kN, E) |
| Bomba centrífuga | TDH (ft, V) · Potencia al freno (HP, V) · NPSH disponible (ft, V) |
| Colector de polvo | Área de filtración (m², D) · Pérdida de presión total (Pa, D) · Potencia al eje del ventilador (kW, V) · Polvo captado (kg/h, V) |
| Ductos de aire con polvo | Diámetro interior (mm, V) · Pérdida de presión total (Pa, V) · Potencia al eje (kW, V) · Cumple velocidad mínima (—, D) |
| Elevador de cangilones | Capacidad másica (t/h, V) · Capacidad volumétrica (m³/h, V) · Potencia requerida del motor (kW, E) · v²/(g·R) (—, V) |
| Transportador helicoidal | Diámetro del tornillo (plg, E) · Velocidad de giro (rpm, E) · Potencia total en la flecha (kW, E) · Motor comercial mínimo IEC (kW, D) |
| Transportador neumático | Diámetro interior (mm, V) · Capacidad de sólidos (t/h, V) · Pérdida de presión total (Pa, E) · Potencia al eje del soplador (kW, V) |
| Secador rotatorio directo | Agua evaporada (kg/h, V) · Diámetro del tambor (m, V) · Longitud del tambor (m, E) · Consumo de combustible (kg/h, V) |
| Silo metálico | Volumen de material (m³, V) · Altura total (m, V) · Presión horizontal de diseño (kPa, V) · Espesor mínimo de predimensionamiento (mm, V) |
| Soplador | Potencia al eje recomendada (kW, V) · Flujo másico de aire (kg/h, V) · Diámetro de la tubería (mm, V) · Temperatura de descarga (°C, V) |
| Tolva de dosificación | Volumen de material (m³, V) · Altura de la tolva (m, V) · Flujo de descarga (t/h, E) · Tiempo de vaciado (min, E) |
| Torre de enfriamiento | Carga térmica (kW, V) · Flujo de aire seco (kg/s, V) · Agua evaporada (kg/h, V) · KaV/L requerida (—, E) |
| Bomba de vacío | Potencia al eje (kW, V) · Relación de compresión (—, V) · Flujo másico de aire seco (kg/h, V) · Diámetro del ducto de succión (mm, V) |
| Viga | Momento flector máximo (kN·m, V) · Esfuerzo máximo de flexión (MPa, V) · Deflexión máxima (mm, V) · Relación σ/σ_adm (—, V) |

Puntos a decidir: la capacidad del aerodeslizador es nivel **O** (se muestra con su insignia y la
leyenda «no validado»); la bomba centrífuga calcula en unidades US y también ofrece TDH, potencia y
NPSHa en SI como conversiones (nivel D: `altura_total_m`, `potencia_freno_kw`, `npsha_m`).

## 4. Verificación

- **Pruebas:** `python -m pytest -q` → 449 aprobadas (424 anteriores + 25 nuevas en
  `tests/test_rediseno.py`). Aplicaciones: los mismos resultados que en `main` (línea de agua 83,
  vapor 87, aceite 68, gas 78, tanque 60 aprobadas). `gas_combustible` tiene 1 falla que **ya existía en
  `main`** (`test_caso_y_excel`, busca «4,892» en la tabla del caso de cogeneración); no la toca este cambio.
- **Prueba modificada:** `tests/test_interfaz.py::test_pestana_esquema` ahora espera la pestaña
  «Ecuaciones y notas» (y que la bomba, sin esquema, tenga «Resultados» y «Ecuaciones y notas»).
  Es una prueba de interfaz; ningún valor esperado de ingeniería cambió.
- **No regresión (paso 6 de la guía):** con los casos de `tests/casos.py` se abrió cada herramienta
  desde el menú, se calculó y se registraron filas de la tabla, texto de «Copiar resultados», celdas del
  Excel exportado, resultados de las 3 memorias y de las 6 aplicaciones. Las instantáneas antes y
  después del cambio son idénticas (SHA-256 `7349a359…e1bfc`, fechas enmascaradas).

## 5. Pendiente (fases siguientes)

- HVAC industrial (PySide6): barra lateral agrupada, encabezado del caso, tablas anchas con columna fija.
- Encabezados de grupo dentro de la tabla de resultados: requieren declarar el grupo de cada salida en
  cada calculadora (dato que hoy no existe en `Salida`).
- Tamaños ≥ 1600 px (esquema siempre visible) y ventana acoplada estrecha con ancla «Ir a resultados».
- Listas JSON de las aplicaciones como tabla editable con «Ver JSON».
- Fuentes IBM Plex: se usan si están instaladas en Windows; no se incluyen en el repositorio.
