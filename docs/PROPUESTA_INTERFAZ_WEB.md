# Propuesta: interfaz web o arquitectura híbrida (evaluación para una etapa futura)

Esta versión 2.0.0 conserva Python y Tkinter, como se pidió. Este documento evalúa el siguiente paso; no implica ninguna migración.

## 1. Punto de partida

La reestructuración de esta versión ya hizo la parte difícil de cualquier migración: **el cálculo está separado de la interfaz**.

- `calculadoras/nucleo` y `calculadoras/calculos` no importan Tkinter. Reciben un diccionario y devuelven un `Resultado` con valores, unidades, niveles, advertencias y ecuaciones.
- Cada calculadora se describe de forma declarativa (`Campo`: unidad, rango, opciones, ayuda, grupo). La ventana Tkinter se genera de esa descripción; una página web se puede generar igual, sin escribir 15 formularios a mano.
- Los reportes PDF/Excel ya se generan en Python a partir del resultado, no de la pantalla.
- Las pruebas del núcleo y de las calculadoras no dependen de la ventana: cualquier interfaz nueva hereda esa validación.

## 2. Alternativas

| Criterio | A. Mantener Tkinter (actual) | B. Web pura (reescribir en JavaScript) | C1. Híbrida local: motor Python + página web servida desde Python | C2. Híbrida sin servidor: motor Python en el navegador (Pyodide) |
|---|---|---|---|---|
| Confiabilidad de cálculos | Alta (motor probado) | **Baja al inicio**: hay que reescribir y revalidar las 15 calculadoras | Alta (mismo motor) | Alta (mismo motor), sujeta a verificar que las pruebas pasen en Pyodide |
| Esfuerzo | Nulo | Alto (reescritura + doble validación) | Medio: API + generador de formularios | Medio-alto: empaquetado y compatibilidad de bibliotecas |
| Instalación en cada PC | Python + bibliotecas | Ninguna | Ninguna para usuarios si se sirve en red interna; Python en una PC/servidor | Ninguna |
| Actualizaciones | Copiar la carpeta a cada PC | Publicar | Un solo lugar (el servidor) | Publicar |
| Sin conexión | Sí | Sí | Sí en la PC local; en red interna, depende de la red | Sí, tras la primera carga |
| PDF/Excel | Python (actual) | Bibliotecas JS o impresión del navegador | Python (actual) | Excel posible; PDF con reportlab **no verificado** en Pyodide (alternativa: impresión del navegador) |
| Seguridad | Local | Local si es archivo | En red interna requiere autenticación real (la contraseña actual no basta) | Local |
| Diseño visual y responsive | Limitado | Completo | Completo | Completo |

## 3. Recomendación

**C1 — motor Python con interfaz web local**, en una etapa posterior y solo si se confirma alguna de estas necesidades: varios usuarios, uso sin instalar Python en cada PC, actualización centralizada o mejor presentación. Si el uso es de una o dos personas en sus propias PC, **A (la versión actual) es suficiente** y no conviene invertir en migrar.

No recomiendo B: obligaría a validar las fórmulas dos veces y separaría el cálculo de las herramientas científicas de Python, sin ganancia de precisión. C2 es atractiva para compartir sin servidor, pero tiene dos incertidumbres que habría que probar antes (soporte de reportlab en el navegador y tiempo de carga).

## 4. Plan sugerido para C1 (por etapas verificables)

1. **Prototipo con una calculadora (ductos)**: API `POST /api/calcular/{id}` que reutiliza `Calculadora.calcular`, y `GET /api/calculadoras` que entrega la descripción de campos; formulario HTML generado de esa descripción. Puerta: resultados idénticos a la versión Tkinter en los casos de `tests/casos.py`.
2. **Las 15 calculadoras** con el mismo generador, más descarga del PDF/Excel generado en Python. Puerta: prueba automática que compara API y motor para todos los casos.
3. **Autenticación real** (si se publica en red), historial de cálculos por usuario y respaldo.
4. **Retiro o convivencia** de la versión Tkinter, a decisión de la empresa.

Tecnologías candidatas: FastAPI o la biblioteca estándar de Python para el servidor; HTML, CSS y JavaScript sin dependencias pesadas para la página. Se elegirían en el prototipo.

## 5. Información necesaria para decidir

- Cuántas personas lo usarán y en qué equipos (versión de Windows, si pueden instalar Python).
- Si hay red interna o un servidor disponible.
- Si se requiere acceso desde fuera de la oficina.
- Formato de memoria de cálculo de la empresa, si existe.
