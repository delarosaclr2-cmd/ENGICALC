"""IAPWS-IF97 implementado: valores de verificación de la propia norma (IAPWS R7-97, tablas 5, 15, 35)
y contraste con la implementación IF97 de CoolProp en todo el intervalo usado."""
import pytest

from linea_vapor.nucleo import if97


@pytest.mark.parametrize("p,t,v,h", [(3e6, 300, 0.100215168e-2, 0.115331273e6), (80e6, 300, 0.971180894e-3, 0.184142828e6),
                                     (3e6, 500, 0.120241800e-2, 0.975542239e6)])
def test_region1_verificacion(p, t, v, h):
    e = if97.estado_pt(p, t)
    assert e.v == pytest.approx(v, rel=1e-8) and e.h == pytest.approx(h, rel=1e-8)


@pytest.mark.parametrize("p,t,v,h", [(3500, 300, 0.394913866e2, 0.254991145e7), (3500, 700, 0.923015898e2, 0.333568375e7),
                                     (30e6, 700, 0.542946619e-2, 0.263149474e7)])
def test_region2_verificacion(p, t, v, h):
    v_, h_, _ = if97._region2(p, t)
    assert v_ == pytest.approx(v, rel=1e-8) and h_ == pytest.approx(h, rel=1e-8)


def test_saturacion_verificacion():
    assert if97.p_sat(300) == pytest.approx(0.353658941e4, rel=1e-8)
    assert if97.p_sat(500) == pytest.approx(0.263889776e7, rel=1e-8)
    assert if97.t_sat(0.1e6) == pytest.approx(0.372755919e3, rel=1e-8)
    assert if97.t_sat(10e6) == pytest.approx(0.584149488e3, rel=1e-8)


def test_contra_coolprop():
    cp = pytest.importorskip("CoolProp.CoolProp")
    peor = 0.0
    for p in (1e4, 1e5, 5e5, 2e6, 5e6, 1e7, 3e7):
        for t in range(280, 1070, 13):
            try:
                e = if97.estado_pt(p, t)
            except ValueError:
                continue
            peor = max(peor, abs(e.rho / cp.PropsSI("D", "P", p, "T", t, "IF97::Water") - 1),
                       abs(e.h - cp.PropsSI("H", "P", p, "T", t, "IF97::Water")) / 3e6,
                       abs(e.mu / cp.PropsSI("V", "P", p, "T", t, "Water") - 1) / 100)
    assert peor < 1e-6


def test_region3_rechazada():
    with pytest.raises(ValueError):
        if97.estado_pt(25e6, 650)
