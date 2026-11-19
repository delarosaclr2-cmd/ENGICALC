# Revisión independiente de agitadores, bombas y ductos HVAC

Fecha: 18 de noviembre de 2026.
Rama de destino: `calculadoras/bombas-agitadores-ductos`.
Base de la integración: `64c65f6459a3fa158319e7baf85aeb901b0dfc01`.

Se incorpora el paquete Python `calculadoras/memorias/` procedente de
`C:\CALC AGITADORES\PRINCIPAL`. Los tres motores y sus catálogos JSON se
copian sin cambiar ecuaciones, constantes ni valores iniciales.

## Acceso y archivos

Abra y ejecute en su IDE el archivo correspondiente, ubicado en la raíz:

| Archivo | Ventana |
|---|---|
| `revisar_agitadores.py` | Agitadores · memoria completa |
| `revisar_bombas.py` | Bombas centrífugas · memoria completa |
| `revisar_ductos_hvac.py` | Ductos HVAC · memoria completa |

También puede ejecutar `py revisar_agitadores.py`, `py revisar_bombas.py` o
`py revisar_ductos_hvac.py`. Cada archivo abre solo su memoria. El acceso consulta
la configuración de contraseña existente. Cerrar la ventana termina la sesión.

El menú principal, `menu_principal.py`, el registro de las 15 calculadoras y sus
pruebas permanecen intactos. Las memorias no aparecen en el menú ni en
`menu_principal.py --lista`. Su incorporación al menú queda fuera de esta revisión,
por indicación del usuario.

Las memorias usan sus propios datos de documento y su formato `RMR-memoria`;
no se añaden al historial de las calculadoras anteriores ni reciben los datos
del proyecto global. Capture sus metadatos con **Datos del documento** y abra
sus archivos desde **Caso → Abrir caso**, en la propia ventana de la memoria.

El paquete incluye actualización automática, captura SI/US, tablas de curvas y
accesorios, gráficas/esquemas, JSON y exportación PDF/Excel. NumPy se declara
como dependencia directa. El logo incorporado está en `recursos/RMR_transparente.png`.

## Verificación y alcance

- `tests/test_memorias.py`: 44 referencias numéricas congeladas de los HTML,
  verificaciones independientes, archivos JSON y exportaciones PDF/Excel.
- `tests/test_lanzadores_memorias.py`: despacho de los tres archivos, acceso,
  cierre y liberación de la raíz ante errores al iniciar.
- `tests/test_memorias_interfaz.py` y `tests/test_memorias_auto.py`: ventanas,
  unidades, curvas, tramos, dimensionamiento y actualización automática.
- La suite anterior se conserva para comprobar regresiones.

Las comprobaciones gráficas requieren una instalación funcional de Tcl/Tk y
pantalla. Se omiten expresamente cuando ese entorno no está disponible.
Los resultados de la ejecución están en `RESULTADOS_INTEGRACION_MEMORIAS.md`.

Las referencias de equivalencia verifican la traducción del código. No
constituyen validación de ingeniería para un proyecto específico: se mantienen
los dominios y advertencias de las memorias originales. El documento de origen
`MIGRACION_MEMORIAS_NATIVAS.md` se conserva como antecedente de la migración;
sus referencias a la carpeta `PRINCIPAL` y a accesos desde el menú describen
aquella distribución, no esta rama. Use los tres archivos indicados arriba.

No se modifican los cálculos anteriores, la configuración de acceso ni los
archivos históricos de auditoría o resultados.
