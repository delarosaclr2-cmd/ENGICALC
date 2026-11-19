# Resultados de la revisión independiente

Fecha: 18 de noviembre de 2026.
Rama: `calculadoras/bombas-agitadores-ductos`.
Base: `64c65f6459a3fa158319e7baf85aeb901b0dfc01`.

## Pruebas ejecutadas

Python 3.12.10, Windows. Desde la raíz de la copia de integración:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest -q -p no:cacheprovider --basetemp "$env:TEMP\engicalc-revision-independiente" --tb=short
```

Resultado observado: **312 passed, 70 skipped in 16.07s**.

Incluye las pruebas de la suite anterior, 44 casos de equivalencia numérica
de los motores HTML, comprobaciones independientes, exportación PDF/Excel,
casos JSON y siete pruebas de los lanzadores independientes.

Las 70 pruebas omitidas corresponden a interfaces gráficas. La creación de
`tkinter.Tk()` falló con `Can't find a usable init.tcl`; por tanto, la revisión
visual y la ejecución real de las ventanas quedan pendientes en un equipo con
Tcl/Tk funcional. Las pruebas de los lanzadores usan dobles de Tk para verificar
despacho, acceso y cierre; no sustituyen esa comprobación gráfica.

## Otras comprobaciones

- `python -B menu_principal.py --lista`: conserva las 15 calculadoras originales.
- `git diff --exit-code -- menu_principal.py calculadoras/interfaz/menu.py tests/test_interfaz.py`:
  salida 0; sin diferencias de código.
- Comparación binaria con el origen: `agitadores.py`, `bombas.py`, `ductos.py`,
  `comun.py` y los tres catálogos JSON coinciden, 7 de 7.

La equivalencia comprueba la migración de software. No certifica la adecuación
de las correlaciones, curvas o coeficientes para un proyecto concreto.

## Aplicación pendiente

La sesión permite leer `C:\ENGICALC` y escribir en `C:\CALC AGITADORES`,
pero no escribir en `C:\ENGICALC`. Los cambios se prepararon en una copia
de la rama dentro de `C:\CALC AGITADORES\ENGICALC_integracion`.
Se entrega un parche para aplicar al repositorio de destino, sin commit,
push, pull request ni fusión.
