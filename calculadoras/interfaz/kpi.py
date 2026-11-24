"""Indicadores clave (KPI) que la ventana de cada calculadora muestra arriba de los resultados.

Solo selección de interfaz: cada entrada es la ``clave`` de una salida que la calculadora YA
calcula. No se crea ningún valor nuevo, no cambia la precisión ni el orden de la tabla y no
interviene en PDF, Excel, historial ni casos guardados.

PROPUESTA PENDIENTE DE CONFIRMACIÓN DEL RESPONSABLE TÉCNICO (paso 3 de la guía del rediseño).
Para cambiar un KPI basta editar esta lista; la prueba ``tests/test_rediseno.py`` comprueba que
cada clave exista en los resultados de la calculadora y que haya de 2 a 4 por herramienta.
"""

KPI: dict[str, tuple[str, ...]] = {
    "aerodeslizador": ("capacidad_th", "caudal_aire", "dp_lecho", "fluidiza"),
    "banda": ("capacidad_th", "capacidad_m3h", "potencia_motor", "fuerza_tangencial"),
    "bomba": ("altura_total", "potencia_freno", "npsha"),
    "colector": ("area_filtracion", "dp_total_pa", "potencia_kw", "polvo_kg_h"),
    "ductos": ("diametro_mm", "dp_total_pa", "potencia_kw", "cumple_velocidad"),
    "elevador": ("capacidad_th", "capacidad_m3h", "potencia_motor", "relacion_centrifuga"),
    "helicoidal": ("diametro", "rpm", "tshp_kw", "motor_kw"),
    "neumatico": ("diametro_mm", "capacidad_t_h", "dp_total_pa", "potencia_kw"),
    "secador": ("agua_evaporada", "diametro", "longitud", "combustible_kg_h"),
    "silo": ("volumen", "altura_total", "ph_diseno", "espesor_adoptado"),
    "soplador": ("potencia_eje_kw", "masa_kg_h", "diametro_mm", "t_descarga"),
    "tolva": ("volumen", "altura", "flujo_t_h", "tiempo_vaciado"),
    "torre": ("carga_kw", "flujo_aire", "evaporacion", "kav_l"),
    "vacio": ("potencia_eje_kw", "relacion_compresion", "masa_kg_h", "diametro_ducto_mm"),
    "viga": ("momento_max", "esfuerzo_flexion", "deflexion_max", "relacion_flexion"),
}
