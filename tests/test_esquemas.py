"""Esquemas ajustables: se dibujan con cualquier dato válido y no contradicen el cálculo.

Además de comprobar que cada esquema se dibuja (caso ordinario y variantes), se verifica que la
geometría dibujada sea la del cálculo: áreas de la sección de la banda, alturas del silo, presión
de Janssen en el fondo del cilindro y deflexión máxima de la viga.
"""
import math

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402

from casos import CASOS  # noqa: E402
from casos_libros import CASOS_LIBROS  # noqa: E402
from calculadoras import esquemas  # noqa: E402
from calculadoras.calculos import POR_ID  # noqa: E402
from calculadoras.calculos import colector as COL  # noqa: E402
from calculadoras.calculos import elevador as EL  # noqa: E402
from calculadoras.calculos import helicoidal as HE  # noqa: E402
from calculadoras.calculos import soplador as SOP  # noqa: E402
from calculadoras.calculos import secador as SEC  # noqa: E402
from calculadoras.calculos import viga as VG  # noqa: E402
from calculadoras.esquemas import base, estructural, solidos  # noqa: E402


def preparar(cid, **cambios):
    calc = POR_ID[cid]
    entradas = dict(calc.valores_por_defecto())
    entradas.update(CASOS[cid])
    entradas.update(cambios)
    datos = calc.validar(entradas)
    return datos, calc.calcular(datos)


def dibujar(cid, datos, resultado):
    figura = esquemas.crear_figura(cid, datos, resultado)
    FigureCanvasAgg(figura).draw()  # fuerza el trazado completo (textos, cotas, flechas)
    return figura


def textos(figura):
    return [t.get_text() for ax in figura.axes for t in ax.texts]


def test_todas_menos_la_bomba_tienen_esquema():
    assert set(esquemas.ESQUEMAS) == set(POR_ID) - {"bomba"}
    assert not esquemas.disponible("bomba")


@pytest.mark.parametrize("cid", sorted(esquemas.ESQUEMAS))
def test_esquema_del_caso_ordinario(cid):
    figura = dibujar(cid, *preparar(cid))
    assert figura.axes
    nota = " ".join(textos(figura))
    assert "Dibujo a escala" in nota or "Esquema sin escala" in nota


VARIANTES = [
    ("viga", dict(tipo=VG.SIMPLE, longitud=6, carga_puntual=500, posicion=2, carga_distribuida=200,
                  seccion=VG.IVIGA, b=150, h=300, tf=10, tw=6)),
    ("viga", dict(seccion=VG.CIRC, d=120)),
    ("viga", dict(seccion=VG.TUBO, d=150, t=8)),
    ("viga", dict(seccion=VG.PERS, inercia=5000, c=100, area=40)),
    ("helicoidal", dict(angulo=20, eficiencia_inclinacion=0.7, factor_inclinacion=1.5, paso="Corto (paso = 2/3 D)")),
    ("banda", dict(inclinacion=0)),
    ("aerodeslizador", dict(longitud=0)),
    ("aerodeslizador", dict(inclinacion=0)),
    ("torre", dict(t_bulbo_humedo=0, t_bulbo_seco=0, t_aire_salida=0)),
    ("torre", dict(t_bulbo_seco=0, relacion_lg=1.2)),
    ("secador", dict(flujo=SEC.CONTRACORRIENTE, t_aire_salida=100, t_solido_salida=80, t_aire_entrada=300)),
    ("elevador", dict(cangilon_tabla=EL.CAPTURAR_VOLUMEN, volumen_cangilon=3, diametro_cola=400)),
    ("ductos", dict(contaminante="No verificar / capturar velocidad mínima", velocidad_minima=0)),
    ("vacio", dict(presion_descarga=200, velocidad_ducto=10)),
    ("colector", dict(limpieza=COL.TEJIDA)),
    ("soplador", dict(tipo_maquina=SOP.LOBULOS)),
]


@pytest.mark.parametrize("cid,cambios", VARIANTES, ids=[f"{c}-{i}" for i, (c, _) in enumerate(VARIANTES)])
def test_esquemas_con_otros_datos(cid, cambios):
    calc = POR_ID[cid]
    for clave, valor in cambios.items():  # las opciones de las variantes deben existir en la calculadora
        campo = calc.campo(clave)
        if campo.tipo == "opcion" and valor not in campo.opciones:
            pytest.skip(f"opción «{valor}» no existe en {cid}.{clave}")
    figura = dibujar(cid, *preparar(cid, **cambios))
    assert figura.axes


def test_libros_tambien_se_dibujan():
    for caso in CASOS_LIBROS.values():
        if not esquemas.disponible(caso["calculadora"]):  # la bomba no lleva esquema
            continue
        calc = POR_ID[caso["calculadora"]]
        datos = calc.validar(dict(calc.valores_por_defecto(), **caso["entradas"]))
        dibujar(caso["calculadora"], datos, calc.calcular(datos))


def test_banda_areas_dibujadas_iguales_a_las_calculadas():
    datos, r = preparar("banda")
    s = solidos.seccion_banda(datos, r)
    assert base.area_poligono(s["artesa"]) == pytest.approx(r["area_artesa"], rel=1e-9)
    sobre = s["sobrecarga"]  # cerrada por la cuerda: el polígono de puntos ya inicia y termina en ella
    assert base.area_poligono(sobre) == pytest.approx(r["area_sobrecarga"], rel=1e-3)


def test_silo_geometria_y_presion_en_el_fondo():
    datos, r = preparar("silo")
    g = solidos.geometria_silo(datos, r)
    assert g["contorno"][1][1] == pytest.approx(r["altura_tolva"])
    assert g["contorno"][2][1] == pytest.approx(r["altura_total"])
    perfil = solidos.perfil_janssen(datos, r)
    assert perfil[-1][0] == pytest.approx(r["altura_cilindro"])
    assert perfil[-1][1] == pytest.approx(r["ph"], rel=1e-6)
    figura = dibujar("silo", datos, r)
    assert any(t.startswith("D = 4.00 m") for t in textos(figura))


def test_viga_deformada_dibujada_es_la_del_calculo():
    for cambios in ({}, dict(tipo=VG.SIMPLE, longitud=5, carga_puntual=800, posicion=1.5, carga_distribuida=100)):
        datos, r = preparar("viga", **cambios)
        curva = estructural.elastica(datos, puntos=2000)
        assert max(abs(y) for _, y in curva) * 1000 == pytest.approx(r["deflexion_max"], rel=1e-3)


def test_helicoidal_paso_y_carga():
    assert set(solidos.PASO_RELATIVO) == set(HE.PASOS)
    _, r = preparar("helicoidal")
    assert solidos.carga_helicoidal(r) == pytest.approx(0.30)
    R = 1.0
    h = solidos.segmento_por_fraccion(R, 0.30)
    area = R ** 2 * math.acos((R - h) / R) - (R - h) * math.sqrt(2 * R * h - h * h)
    assert area / (math.pi * R ** 2) == pytest.approx(0.30, rel=1e-6)


def test_cotas_siguen_a_los_datos():
    """Al cambiar un dato el esquema cambia (es ajustable)."""
    a = textos(dibujar("tolva", *preparar("tolva")))
    b = textos(dibujar("tolva", *preparar("tolva", area_superior=9)))
    assert any("lado = 2.000 m" in t for t in a)
    assert any("lado = 3.000 m" in t for t in b)
