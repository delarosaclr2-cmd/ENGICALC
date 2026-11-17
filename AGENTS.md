# ENGICALC — Instrucciones compartidas para agentes de programación

> Versión 1.0 · Política del repositorio para Codex y Claude Code.
> Este documento es una guía operativa: no sustituye los controles de acceso de GitHub.

## 1. Objetivo y prioridades

ENGICALC es una aplicación de calculadoras de ingeniería desarrollada en Python por dos colaboradores humanos con asistencia de agentes de IA. Ambos pueden trabajar al mismo tiempo en ramas diferentes.

Prioridades, en este orden: **exactitud técnica**, **conservación del trabajo ajeno**, **cambios verificables** y **mantenibilidad**. No sacrificar exactitud de ingeniería para hacer pasar una prueba o simplificar una interfaz.

## 2. Estructura conocida del repositorio

Según la estructura documentada por el equipo:

- `calculadoras/calculos/`: cálculos (confirmar responsabilidad real en el código).
- `calculadoras/esquemas/`: esquemas (confirmar responsabilidad).
- `calculadoras/interfaz/`: interfaz (confirmar responsabilidad).
- `calculadoras/nucleo/`: componentes comunes (confirmar responsabilidad).
- `config/`: configuración; `herramientas/`: utilidades; `recursos/`: recursos.
- `docs/`: documentación, fórmulas, unidades y evidencias de validación.
- `registro/`: registros; determinar qué datos son históricos y cuáles temporales.
- `tests/`: pruebas; `pytest.ini`: configuración de pytest.
- Puntos de entrada o ejecución por verificar: `menu_principal.py`, `calculadoras/__main__.py`, `INICIAR.bat`, `INSTALAR.bat`, `PROBAR.bat`.
- Dependencias: `requirements.txt`.

**No inferir el comportamiento de un módulo por su nombre.** Leer el código antes de modificarlo. No reestructurar carpetas ni renombrar importaciones sin encargo expreso.

## 3. Protección de `main` (regla crítica)

- `main` es la rama principal de integración, no una rama de trabajo.
- **No editar, hacer commits ni hacer push directamente en `main`.** Sí se permite al humano actualizar su copia de `main` mediante un pull *fast-forward* con el árbol limpio.
- No hacer `merge`, `rebase` ni cerrar/aprobar pull requests por iniciativa propia.
- No ejecutar `git push --force`, `git reset --hard`, `git clean -fd`, borrados de ramas remotas ni comandos destructivos sin autorización humana específica y evaluación de consecuencias.
- No ejecutar `git commit`, `git push`, crear un PR o fusionarlo sin autorización humana **específica para esa acción**; una petición de programar no autoriza publicar cambios.
- Si el usuario solicita modificar código estando en `main`, **no editar aún**: explicar la situación y pedir o preparar, con autorización, una rama de tarea.
- Las instrucciones escritas aquí no bloquean técnicamente las operaciones; respetar también permisos, revisiones y protecciones configuradas en GitHub.

## 4. Ramas y coordinación de dos desarrolladores

- Una tarea = una rama nueva basada en `main` actualizado.
- Convención: `feature/<persona>/<tarea>`, `fix/<persona>/<tarea>`, `refactor/<persona>/<tarea>`, `docs/<persona>/<tarea>`.
- Ejemplos: `feature/luis/calculo-bombas`, `fix/colaborador/unidades-presion`.
- Identificar a cada persona con un nombre estable y distinto. **No compartir ramas de trabajo** por defecto.
- Cada colaborador mantiene su clon local. Si hay varios agentes sobre la misma PC, utilizar clones o `git worktree` separados; **no permitir escrituras concurrentes sobre un mismo directorio**.
- Las ramas aíslan cambios, **no evitan conflictos** en archivos o interfaces compartidos.
- Antes de intervenir módulos compartidos (`calculadoras/nucleo/`, `config/`, `requirements.txt`, `menu_principal.py`, archivos de instrucciones), verificar alcance y coordinarse con el otro colaborador.
- Comunicar en GitHub Issues/PR o por el canal acordado qué archivo o funcionalidad tiene cada persona; no asumir que está libre por ausencia de cambios locales.

## 5. Comprobaciones antes de modificar cualquier archivo

Ejecutar únicamente comandos de lectura y explicar hallazgos:

```bash
git rev-parse --show-toplevel
git branch --show-current
git status --short
git remote -v
```

- Confirmar que se trabaja en el repositorio y rama correctos.
- Revisar diffs y cambios sin registrar. Si existen cambios desconocidos o una rama de otra persona, **detenerse** y consultar antes de cambiar de rama o editar.
- Identificar los archivos implicados, sus dependencias y las pruebas existentes.
- Presentar un plan breve antes de cambios con impacto en cálculos, interfaces públicas o estructura.
- Pedir aprobación antes de ampliar el alcance a archivos no previstos.

## 6. Límites de edición y uso de herramientas

- Cambiar solo lo necesario para la tarea solicitada.
- No reescribir módulos completos, formatear todo el repositorio, actualizar paquetes ni reorganizar directorios como efecto secundario.
- Conservar cambios locales ajenos, incluso archivos sin seguimiento; no sobrescribirlos ni revertirlos.
- No modificar documentación histórica ni resultados de auditoría para que coincidan con el nuevo código; agregar evidencia nueva si corresponde.
- No incluir secretos, credenciales, `.env`, cachés, entornos virtuales ni archivos temporales en commits.
- Antes de proponer un commit, revisar `git diff`, `git status` y los archivos concretos; preferir `git add ruta/archivo` a `git add .` cuando existan cambios ajenos.
- No lanzar procesos externos, instalar dependencias ni ejecutar scripts desconocidos sin revisar su contenido y contar con autorización cuando proceda.

## 7. Integridad de cálculos de ingeniería

Ante cualquier cambio de cálculo:

1. Identificar ecuaciones, hipótesis, unidades y dominio de validez.
2. Comprobar dimensiones, conversiones, signos, condiciones límite y precisión numérica.
3. Consultar las referencias técnicas existentes en `docs/` y casos de referencia.
4. Separar **prueba de software** (el código ejecuta), **verificación numérica** (coincide con casos conocidos) y **validación de ingeniería** (el método resulta adecuado).
5. No inventar factores, propiedades, normas ni tolerancias. Si falta una referencia o dato, indicarlo expresamente.
6. No modificar el resultado esperado de una prueba solo para conseguir que pase.
7. Para resultados de alto impacto, solicitar revisión humana antes de integrar el cambio.

## 8. Pruebas y documentación

- Inspeccionar `pytest.ini`, `tests/`, `requirements.txt` y `PROBAR.bat` antes de decidir cómo probar.
- Si el entorno está preparado y pytest es la herramienta aplicable, ejecutar las pruebas relacionadas y, cuando corresponda, `python -m pytest -q`.
- Añadir o actualizar pruebas de regresión para errores corregidos; incluir casos nominales, límites, entradas inválidas y conversiones si son pertinentes.
- Informar qué comandos se ejecutaron, resultados reales, pruebas omitidas y limitaciones. **No afirmar que algo pasó sin ejecutarlo.**
- Mantener documentación de fórmulas, entradas/salidas o cambios de comportamiento cuando corresponda, sin alterar evidencias históricas.

## 9. Commits, publicación e integración

- Convención sugerida de mensajes: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- Solo después de autorización humana: crear commit en la rama de tarea y hacer push a **esa misma rama**, no a `main`.
- Abrir PR con: objetivo, archivos afectados, consideraciones técnicas, pruebas y resultados, riesgos y limitaciones.
- Revisar los PR del otro colaborador, especialmente cualquier modificación de ecuaciones o interfaces compartidas.
- Si la rama quedó desactualizada, informar antes de mezclar cambios; **no resolver automáticamente conflictos semánticos** ni reescribir historial remoto.
- La integración final de un PR en `main` requiere decisión explícita de los responsables humanos.

## 10. Formato obligatorio de respuesta del agente

Al iniciar: indicar **rama actual**, **estado Git**, **objetivo**, **archivos previstos** y **riesgos**.

Al concluir: entregar un resumen con:

1. Rama y archivos modificados.
2. Qué cambió y por qué.
3. Pruebas ejecutadas y resultados observados.
4. Riesgos, pendientes y aspectos no verificados.
5. Estado Git final y si hubo commit/push/PR (solo si se autorizaron).

Si aparece una contradicción, conflicto, riesgo de pérdida de datos o duda técnica relevante: **detener la operación afectada y solicitar decisión humana**.
