"""Equivalencia contra los HTML de revisión A y verificaciones independientes.

Las referencias congeladas se obtuvieron ejecutando los motores originales;
las pruebas y la aplicación no necesitan Node, navegador ni los HTML.
"""
import importlib
import json
import math
from pathlib import Path

import pytest
from calculadoras.memorias import MEMORIAS,POR_ID,buscar
from calculadoras.memorias import agitadores,bombas,ductos,reportes
from calculadoras.memorias.comun import copia,catalogo
from calculadoras.nucleo.modelo import ErrorEntrada

CASOS=json.loads((Path(__file__).parent/'datos'/'equivalencia_html.json').read_text(encoding='utf-8'))


def assert_valor(actual,expected):
    if isinstance(expected,list):assert actual==pytest.approx(expected,rel=1e-7,abs=1e-9)
    elif expected is None:assert actual is None
    elif isinstance(expected,dict):
        for k,v in expected.items():assert_valor(actual[k],v)
    else:assert actual==pytest.approx(expected,rel=1e-7,abs=1e-9)


@pytest.mark.parametrize('case',CASOS,ids=lambda c:c['name'])
def test_equivalencia_html(case):
    motor=importlib.import_module('calculadoras.memorias.'+case['module']);r=motor.calcular(case['state']);expected=case['expected']
    if case['module']=='ductos':
        values=dict(Qdesign=r['design']['Qtot'],Pdesign=r['duty']['dP'],designPath=r['design']['path'],designBalance=r['KbalDesign'],flows=r['flows'],
                    Qop=r['op'].get('Q'),Pop=r['op'].get('dP'),power=r['op'].get('power'),pressures=r['duty']['pressures'])
    else:
        values=r.copy()
        if case['module']=='bombas':values.update(npsha=r['np']['a'],npshr=r['np']['r'])
    for k,v in expected.items():assert_valor(values[k],v)


@pytest.mark.parametrize('memoria',MEMORIAS,ids=lambda m:m.id)
def test_casos_y_exportaciones_nativas(memoria,tmp_path):
    from matplotlib.figure import Figure
    st=memoria.motor.por_defecto();r=memoria.motor.calcular(st);assert r['rows'] and r['equations']
    original=copia(st);memoria.motor.calcular(st);assert st==original,'El motor no debe modificar los datos de entrada.'
    ruta=tmp_path/'caso.json';documento={'Proyecto':'=SUM(1,2)','Fecha':'13/11/2026','Elaboró':'RMR'}
    reportes.guardar_caso(ruta,memoria,st,documento);loaded=reportes.abrir_caso(ruta);assert loaded['datos']==st
    reportes.exportar_excel(tmp_path/'memoria.xlsx',memoria,st,r,documento)
    from openpyxl import load_workbook
    wb=load_workbook(tmp_path/'memoria.xlsx');assert wb['Documento']['B1'].value=='=SUM(1,2)';assert wb['Documento']['B1'].data_type=='s'
    fig=Figure();fig.add_subplot().plot([0,1],[0,1]);reportes.exportar_pdf(tmp_path/'memoria.pdf',memoria,st,r,documento,fig)
    assert (tmp_path/'memoria.pdf').stat().st_size>5000


def test_registro_memorias():
    assert len(MEMORIAS)==3
    assert [m.id for m in buscar('NPSH')]==['memoria_bombas']
    assert [m.id for m in buscar('balanceo')]==['memoria_hvac']


def test_agitador_independiente_y_material():
    st=agitadores.por_defecto();d=st['inputs'];r=agitadores.calcular(st)
    assert r['P']==pytest.approx(5.5*1000*(60/60)**3*1.05**5)
    assert r['Q']==pytest.approx(.72*1.05**3)
    assert r['E1']['teq']==pytest.approx(16/(math.pi*r['dad']**3)*math.hypot(d['Km']*r['E1']['M'],d['Kt']*r['Tq']))
    d.update(orient='horizontal',Lsh=1.5,mat='m316');rh=agitadores.calcular(st);assert rh['inputs']['Sy']==170e6;assert rh['E1']['w']>0
    d['N']=0
    with pytest.raises(ErrorEntrada):agitadores.calcular(st)


def test_bomba_independiente_y_curva_invalida():
    st=bombas.por_defecto();r=bombas.calcular(st);q=r['Qop'];assert r['hPump'](q)==pytest.approx(r['hSys'](q),rel=1e-10)
    assert r['np']['a']==pytest.approx((r['patm']-r['pv'])/(r['rho']*9.80665)-2.5-r['Ld_']['suc'])
    st['curves']['hq']=[{'x':0,'y':10}]*3
    with pytest.raises(ErrorEntrada):bombas.calcular(st)


def test_arbol_independiente_continuidad_balanceo():
    st=ductos.por_defecto();st['branches'][1]['parent']='A';st['branches'][2]['parent']='A'
    r=ductos.calcular(st);assert r['design']['Qd'][0]==pytest.approx(r['design']['Qd'][1]+r['design']['Qd'][2])
    sp=r['net'].split(r['design']['Qtot'])
    assert sp['Q']==pytest.approx(r['design']['Qd'],rel=1e-8)
    op=r['op'];assert op['found'];assert op['dP']==pytest.approx(op['dPsys'],rel=1e-8)
    p=op['pressures'];assert p['static']+p['velocity']==pytest.approx(p['total'])
    st['branches'][0]['parent']='B'
    with pytest.raises(ErrorEntrada):ductos.calcular(st)


def test_dimensionamiento_independiente():
    st=ductos.por_defecto();cfg=st['sizing'];cfg.update(velocity=5,roundSeries='100,200,300,400,500,630,800');seg=st['branches'][0];air=ductos.build_air(st)
    p=ductos.size_segment(seg,1,air,st['method'],cfg);assert p['ideal']['D']==pytest.approx(math.sqrt(4/(5*math.pi)),rel=1e-10);assert p['proposed']['D']==.63;assert p['result']['V']<=5
    cfg['criterion']='friction';p=ductos.size_segment(seg,1,air,st['method'],cfg);assert p['result']['dPf']<=cfg['friction']
    cfg['roundSeries']='80,100'
    with pytest.raises(ErrorEntrada):ductos.size_segment(seg,1,air,st['method'],cfg)


def test_eficiencia_estatica_y_afinidad():
    st=ductos.por_defecto();st['air']['rhoCat']=1.2;f=st['fan'];f.update(outletArea=.2,pressureType='static',efficiencyType='static',points=[dict(Q=0,dP=600,eta=0),dict(Q=1,dP=500,eta=.5),dict(Q=2,dP=300,eta=.4)])
    fan=ductos.Ventilador(st);assert fan.at(1,1,1)==pytest.approx(515);assert fan.power(1,1,1)==pytest.approx(1000);assert fan.at(.5,.5,.8)==pytest.approx(103)
    f['outletArea']=.001
    with pytest.raises(ErrorEntrada):ductos.Ventilador(st)


def test_tabla_damper_inversion():
    assert ductos.damper_extra_k(30)==pytest.approx(3.4)
    for angle in [0,5,10,20,30,45,60,75]:assert ductos.damper_angle(ductos.damper_extra_k(angle))==pytest.approx(angle,abs=1e-10)
    with pytest.raises(ErrorEntrada):ductos.damper_extra_k(90)
