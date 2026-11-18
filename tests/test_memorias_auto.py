"""La edición actualiza el motor, las tablas y los dibujos sin pulsar Calcular."""
import tkinter as tk
from tkinter import ttk
import pytest
from tests.test_memorias_interfaz import menu_nativo
from calculadoras.memorias.ventana import VentanaMemoria
from tests.test_interfaz import HAY_PANTALLA

pytestmark = pytest.mark.skipif(not HAY_PANTALLA, reason="sin pantalla disponible para Tk")


def esperar(root,ms=220):
    done=tk.BooleanVar(master=root,value=False)
    root.after(ms,lambda:done.set(True))
    root.wait_variable(done)


@pytest.fixture(autouse=True)
def pausa_corta(monkeypatch):
    monkeypatch.setattr(VentanaMemoria,'AUTO_DELAY_MS',50)


@pytest.mark.parametrize('cid,path,value,output',[
    ('memoria_agitadores','inputs.N','80','P'),
    ('memoria_bombas','inputs.qd','90','TDH'),
    ('memoria_hvac','main.L','30','design'),
])
def test_editar_actualiza_y_recupera_dato_incompleto(menu_nativo,cid,path,value,output):
    m=menu_nativo;w=m.abrir(cid);m.raiz.update();before=w.resultado[output]
    drawings=[];original=w.dibujar
    def draw():drawings.append(True);return original()
    w.dibujar=draw
    w.variables[path].set('');esperar(m.raiz)
    assert w.resultado is None and not w.tabla.get_children()
    assert not m.errors,'La captura temporalmente incompleta no debe abrir un aviso modal.'
    w.variables[path].set(value);esperar(m.raiz)
    assert w.resultado is not None and w.resultado[output]!=before
    assert drawings and w.figura.axes and len(w.tabla.get_children())==len(w.resultado['rows'])
    assert w._auto_after is None and not m.errors


def test_agrupa_teclas_y_no_recalcula_en_bucle(menu_nativo):
    w=menu_nativo.abrir('memoria_agitadores');root=menu_nativo.raiz;root.update();calls=[];original=w.calcular
    def calc(*args,**kwargs):calls.append(kwargs.get('automatico',False));return original(*args,**kwargs)
    w.calcular=calc
    for value in ['7','75','90']:w.variables['inputs.N'].set(value)
    esperar(root)
    assert calls==[True] and w.resultado['inputs']['N']==90
    esperar(root)
    assert calls==[True] and w._auto_after is None


def test_conserva_decimal_y_foco_al_actualizar(menu_nativo):
    w=menu_nativo.abrir('memoria_agitadores');root=menu_nativo.raiz;root.update()
    field=w.widgets['inputs.N'];field.focus_force();root.update()
    w.variables['inputs.N'].set('60.');esperar(root)
    assert w.variables['inputs.N'].get()=='60.' and w.focus_get() is field
    w.variables['inputs.N'].set('60.5');esperar(root)
    assert w.resultado['inputs']['N']==60.5 and w.focus_get() is field


def test_casillas_y_listas_actualizan_dependencias(menu_nativo):
    w=menu_nativo.abrir('memoria_agitadores');root=menu_nativo.raiz;root.update()
    w.variables['inputs.chkSol'].set(True);esperar(root);assert 'NjsR' in w.resultado
    w.variables['inputs.manNp'].set(True);esperar(root);assert str(w.widgets['inputs.Np'].cget('state'))=='normal'
    w.variables['inputs.Np'].set('2');esperar(root);assert w.resultado['Np']==2
    w.variables['inputs.fluido'].set('Suspensión fibrosa');esperar(root);assert 'Dc' in w.resultado
    assert not menu_nativo.errors


@pytest.mark.parametrize('kind',['bomba','ventilador','accesorio'])
def test_fila_editada_actualiza_sin_aplicar_y_preserva_decimal(menu_nativo,kind):
    w=menu_nativo.abrir('memoria_bombas' if kind=='bomba' else 'memoria_hvac');root=menu_nativo.raiz;root.update()
    ed=w.editores[0] if kind=='bomba' else w.fan_table if kind=='ventilador' else next(e for e in w.editores if getattr(e,'segment_editor',False))
    index='1' if kind!='accesorio' else '0';key='y' if kind=='bomba' else 'dP' if kind=='ventilador' else 'K';value='57.' if kind=='bomba' else '945.' if kind=='ventilador' else '1.'
    ed.arbol.selection_set(index);ed.elegir();ed.vars[key].set(value);esperar(root)
    assert ed.vars[key].get()==value and w.resultado is not None
    if kind=='bomba':assert w.estado['curves']['hq'][1]['y']==57
    elif kind=='ventilador':assert w.estado['fan']['points'][1]['dP']==945
    else:assert w.resultado['segMain']['Kfit']==2
    assert not menu_nativo.errors


def test_nueva_fila_parcial_no_duplica_puntos(menu_nativo):
    w=menu_nativo.abrir('memoria_bombas');root=menu_nativo.raiz;root.update();ed=w.editores[0];n=len(ed.filas)
    ed.vars['x'].set('220');esperar(root);assert len(ed.filas)==n and w.resultado is None and not menu_nativo.errors
    ed.vars['y'].set('10');esperar(root);assert len(ed.filas)==n+1 and w.resultado is not None
    ed.vars['y'].set('12');esperar(root);assert len(ed.filas)==n+1
    ed.eliminar();esperar(root);assert len(ed.filas)==n and w.resultado is not None


def test_angulo_y_propuesta_hvac_se_actualizan(menu_nativo):
    w=menu_nativo.abrir('memoria_hvac');root=menu_nativo.raiz;root.update()
    w.segmento='A';w._render_segmento();w.variables['mode'].set('Operación · dampers fijos');esperar(root)
    w.angle_var.set('30');esperar(root);assert w.estado['op']['Kbal'][0]==pytest.approx(3.4)
    w.variables['sizing.velocity'].set('3');esperar(root)
    assert w._proposal is not None and w._proposal[1]['result']['V']<=3
    assert not menu_nativo.errors


def test_reset_recupera_ejemplo_y_cancela_edicion_pendiente(menu_nativo,monkeypatch):
    monkeypatch.setattr('calculadoras.memorias.ventana.messagebox.askyesno',lambda *a,**kw:True)
    w=menu_nativo.abrir('memoria_agitadores');root=menu_nativo.raiz;root.update();power=w.resultado['P']
    w.variables['inputs.N'].set('90');w.restablecer();esperar(root)
    assert w.resultado['P']==power and w.estado['inputs']['N']==60 and w._auto_after is None
    header=w.winfo_children()[0];labels=[child.cget('text') for frame in header.winfo_children() if isinstance(frame,ttk.Frame) for child in frame.winfo_children() if isinstance(child,ttk.Button)]
    assert labels.count('Restablecer ejemplo')==1 and 'Calcular' not in labels


def test_cierre_cancela_callback_pendiente(menu_nativo):
    w=menu_nativo.abrir('memoria_bombas');root=menu_nativo.raiz;root.update();w.variables['inputs.qd'].set('100');token=w._auto_after
    assert token is not None
    w.destroy();assert token not in root.tk.call('after','info');esperar(root)
