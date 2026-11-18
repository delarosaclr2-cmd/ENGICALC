"""Prueba de las ventanas nativas independientes y de sus editores."""
import tkinter as tk
from pathlib import Path
import pytest
from calculadoras.memorias import MEMORIAS,POR_ID,reportes
from calculadoras.memorias.comun import copia
from tests.test_interfaz import crear_raiz, HAY_PANTALLA

pytestmark = pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")


@pytest.fixture
def menu_nativo(monkeypatch):
    from types import SimpleNamespace
    from calculadoras.memorias.lanzador import abrir_memoria
    from calculadoras.memorias.ventana import VentanaMemoria
    errors=[];monkeypatch.setattr(VentanaMemoria,'mostrar_error',lambda self,e:errors.append(str(e)))
    root=crear_raiz();root.withdraw();ventanas={}
    def abrir(cid):
        ventana=ventanas.get(cid)
        if ventana is None or not ventana.winfo_exists():
            ventana=abrir_memoria(root,cid);ventanas[cid]=ventana
        return ventana
    menu=SimpleNamespace(raiz=root,abrir=abrir,errors=errors)
    yield menu
    root.destroy()


@pytest.mark.parametrize('memoria',MEMORIAS,ids=lambda m:m.id)
def test_ventanas_nativas_y_archivos(menu_nativo,memoria,tmp_path):
    menu=menu_nativo;w=menu.abrir(memoria.id);menu.raiz.update()
    assert w.resultado is not None,menu.errors
    assert menu.abrir(memoria.id) is w
    assert len(w.tabla.get_children())==len(w.resultado['rows'])
    original=copia(w.estado)
    w.unidades.set('US');w.cambiar_unidades();r=w.calcular();assert r is not None,menu.errors
    w.unidades.set('SI');w.cambiar_unidades();assert w.calcular() is not None,menu.errors
    reportes.guardar_caso(tmp_path/'c.json',memoria,w.estado,w.documento)
    assert w.cargar_caso(tmp_path/'c.json') is not None
    assert w.exportar_pdf_a(tmp_path/'m.pdf');assert w.exportar_excel_a(tmp_path/'m.xlsx')
    assert (tmp_path/'m.pdf').stat().st_size>5000
    path='inputs.N' if memoria.modulo=='agitadores' else 'inputs.qd' if memoria.modulo=='bombas' else 'main.L'
    w.variables[path].set('abc');assert w.calcular() is None
    assert not w.tabla.get_children() and w.resultado is None
    assert not w.exportar_pdf_a(tmp_path/'invalido.pdf');assert not (tmp_path/'invalido.pdf').exists()
    w.destroy()


def test_red_tramos_secciones_balanceo(menu_nativo):
    w=menu_nativo.abrir('memoria_hvac');root=menu_nativo.raiz;root.update()
    w.segmento='A';w._render_segmento();w._add_child();root.update()
    assert len(w.estado['branches'])==4 and w.estado['branches'][-1]['parent']=='A'
    w._add_parallel();root.update();assert len(w.estado['branches'])==5
    path='branches.4.name';w.variables[path].set('HVAC-05');w.variables['branches.4.parent'].set('Ramal B');assert w.calcular() is not None,menu_nativo.errors
    assert w.estado['branches'][4]['name']=='HVAC-05' and w.estado['branches'][4]['parent']=='B'
    assert w._proponer() is not None;w._aplicar_propuesta();w._dimensionar_red();root.update();assert w.resultado is not None,menu_nativo.errors
    w.variables['mode'].set('Operación · dampers fijos');assert w.calcular() is not None
    w._rebalancear();assert w.resultado['op']['found']
    w._delete_segment();assert len(w.estado['branches'])==4
    assert not menu_nativo.errors
    w.destroy()


def test_campos_manual_frecuencia_material_y_curvas(menu_nativo):
    w=menu_nativo.abrir('memoria_agitadores');menu_nativo.raiz.update()
    w.variables['inputs.freq'].set('50 Hz');w._frecuencia();assert w.calcular() is not None
    assert w.estado['inputs']['nmot']=='1450'
    w.variables['inputs.mat'].set('Acero inoxidable AISI 316 / 316L — recocido');w._aplicar_material();assert w.calcular() is not None
    assert w.resultado['inputs']['Sy']==170e6
    w.variables['inputs.manNp'].set(True);w._activar_manuales();assert str(w.widgets['inputs.Np'].cget('state'))=='normal'
    w.variables['inputs.Np'].set('2');assert w.calcular()['Np']==2
    w.destroy()


def test_proporciones_y_preset_tuberia(menu_nativo):
    w=menu_nativo.abrir('memoria_agitadores');w.variables['inputs.T'].set('4');w._proporciones();assert w.estado['inputs']['D']==pytest.approx(1.4);assert w.estado['inputs']['C']==pytest.approx(1.32);w.destroy()
    w=menu_nativo.abrir('memoria_bombas');assert 'Caudal de diseño'==w.campos['inputs.qd']['label'];w.variables['inputs.mat'].set('PVC / PE / plástico liso (C = 150)');w._aplicar_tuberia();assert w.estado['inputs']['cs']==150 and w.estado['inputs']['cd']==150;w.destroy()
    w=menu_nativo.abrir('memoria_bombas');ed=w.editores[0];ed.arbol.selection_set('1');ed.elegir();ed.vars['y'].set('57');ed.flush()
    assert w.estado['curves']['hq'][1]['y']==57
    assert w.calcular() is not None,menu_nativo.errors
    w.destroy()


def test_cabecera_y_metricas_en_ventana_reducida(menu_nativo):
    w=menu_nativo.abrir('memoria_bombas');w.geometry('1050x700');menu_nativo.raiz.update()
    header=w.winfo_children()[0]
    for child in header.winfo_children():assert child.winfo_x()+child.winfo_width()<=header.winfo_width()+1
    assert len({int(c.grid_info()['row']) for c in w.metric_cells})==2
    assert all(c.winfo_x()+c.winfo_width()<=w.metricas.winfo_width()+1 for c in w.metric_cells)
    w.destroy()


@pytest.mark.parametrize('indice',[0,1,2])
@pytest.mark.parametrize('pendiente',['99',''])
def test_eliminar_fila_con_edicion_pendiente(menu_nativo,indice,pendiente):
    from calculadoras.memorias.editores import EditorTabla

    filas=[{'x':1.,'y':2.},{'x':3.,'y':4.},{'x':5.,'y':6.}]
    guardados=[]
    editor=EditorTabla(menu_nativo.raiz,[('x','X'),('y','Y')],filas,guardados.append)
    editor.arbol.selection_set(str(indice));editor.elegir()
    editor.vars['y'].set(pendiente)
    editor.eliminar()
    esperado=filas[:indice]+filas[indice+1:]
    assert editor.filas==esperado and guardados==[esperado]
    assert editor.seleccion is None and not editor.arbol.selection()
    assert all(var.get()=='' for var in editor.vars.values())
    menu_nativo.raiz.update()
    assert editor.filas==esperado


def test_caso_de_otra_memoria_indica_archivo_independiente(menu_nativo,tmp_path):
    w=menu_nativo.abrir('memoria_bombas')
    original=copia(w.estado)
    memoria=POR_ID['memoria_agitadores']
    ruta=tmp_path/'agitadores.json'
    reportes.guardar_caso(ruta,memoria,memoria.motor.por_defecto(),{})
    assert w.cargar_caso(ruta) is None
    assert w.estado==original
    assert 'revisar_agitadores.py' in menu_nativo.errors[-1]
