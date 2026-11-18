"""Editores Tkinter para tablas pequeñas de curvas y accesorios."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from .comun import exigir,numero,copia


class EditorTabla(ttk.Frame):
    def __init__(self,padre,columnas,filas,guardar,opciones=None,convertir=None,al_cambiar=None):
        super().__init__(padre,style="RMR.TFrame")
        self.columnas=columnas;self.filas=copia(filas);self.guardar=guardar;self.opciones=opciones or {};self.convertir=convertir or {}
        self.vars={};self.seleccion=None;self.base={};self.al_cambiar=al_cambiar;self._cargando=False;self._traces=[]
        self.arbol=ttk.Treeview(self,columns=[c[0] for c in columnas],show="headings",height=min(6,max(3,len(filas))))
        for key,label in columnas:
            self.arbol.heading(key,text=label);self.arbol.column(key,width=110,minwidth=65,stretch=True)
        self.arbol.pack(fill="x",pady=(5,6));self.arbol.bind("<<TreeviewSelect>>",self.elegir)
        form=ttk.Frame(self,style="RMR.TFrame");form.pack(fill="x")
        for i,(key,label) in enumerate(columnas):
            cell=ttk.Frame(form,style="RMR.TFrame");cell.grid(row=0,column=i,sticky="ew",padx=(0,6));form.columnconfigure(i,weight=1)
            ttk.Label(cell,text=label,style="RMR.Small.TLabel").pack(anchor="w");var=tk.StringVar(value="");self.vars[key]=var
            if key in self.opciones:widget=ttk.Combobox(cell,textvariable=var,values=self.opciones[key],state="readonly",width=12)
            else:widget=ttk.Entry(cell,textvariable=var,width=12,font=("Segoe UI",11),style="RMR.TEntry")
            widget.pack(fill="x",pady=4)
        buttons=ttk.Frame(self,style="RMR.TFrame");buttons.pack(fill="x",pady=(2,8))
        for label,command in [("Nuevo",self.nuevo),("Aplicar fila",self.aplicar),("Eliminar",self.eliminar)]:
            ttk.Button(buttons,text=label,command=lambda c=command:self.seguro(c),style="RMR.TButton").pack(side="left",padx=(0,6))
        self.error=ttk.Label(self,text="",foreground="#b63f45",wraplength=480,style="RMR.Small.TLabel");self.error.pack(fill="x")
        self.refrescar();self.nuevo()
        for var in self.vars.values():self._traces.append((var,var.trace_add("write",self._editar)))
    def _editar(self,*args):
        if not self._cargando and self.al_cambiar:self.al_cambiar()
    def destroy(self):
        for var,token in self._traces:
            try:var.trace_remove("write",token)
            except tk.TclError:pass
        super().destroy()
    def seguro(self,fn):
        try:fn();self.error.config(text="")
        except (ValueError,KeyError) as e:self.error.config(text=str(e))
    def factor(self,k):return self.convertir.get(k,1)
    def refrescar(self):
        self.arbol.delete(*self.arbol.get_children())
        for i,row in enumerate(self.filas):self.arbol.insert("","end",iid=str(i),values=[f"{row[k]/self.factor(k):.6g}" if isinstance(row[k],(int,float)) else row[k] for k,l in self.columnas])
    def elegir(self,event=None):
        sel=self.arbol.selection()
        if not sel:return
        index=int(sel[0])
        if index==self.seleccion:return
        # Commit the previous row before moving; an incomplete row stays editable.
        try:self.flush()
        except ValueError as e:
            self.error.config(text=str(e))
            if self.seleccion is not None:self.arbol.selection_set(str(self.seleccion))
            else:self.arbol.selection_remove(sel)
            return
        self.seleccion=index;row=self.filas[index];self._cargando=True
        try:
            for k,l in self.columnas:
                value=row[k];self.vars[k].set(f"{value/self.factor(k):.10g}" if isinstance(value,(int,float)) else value)
            self.base={k:v.get() for k,v in self.vars.items()}
        finally:self._cargando=False
    def nuevo(self):
        cambios=bool(self._traces) and {k:v.get() for k,v in self.vars.items()}!=self.base
        if cambios:
            try:self.flush()
            except ValueError:pass  # Nuevo descarta una fila aún incompleta.
        self._cargando=True
        try:
            self.seleccion=None
            for k,l in self.columnas:self.vars[k].set(self.opciones[k][0] if k in self.opciones else "")
            self.base={k:v.get() for k,v in self.vars.items()}
            self.arbol.selection_remove(self.arbol.selection())
        finally:self._cargando=False
        if cambios:self._editar()
    def leer(self):
        row={}
        for k,l in self.columnas:
            if k in self.opciones:
                row[k]=self.vars[k].get();exigir(row[k] in self.opciones[k],"Selecciona un tipo de accesorio.")
            else:row[k]=numero(self.vars[k].get(),l,minimo=0)*self.factor(k)
        return row
    def aplicar(self,preservar_entrada=False):
        row=self.leer()
        nueva=self.seleccion is None
        if nueva:self.filas.append(row);self.seleccion=len(self.filas)-1
        else:self.filas[self.seleccion].update(row)
        self.guardar(copia(self.filas))
        if preservar_entrada:
            values=[f"{self.filas[self.seleccion][k]/self.factor(k):.6g}" if isinstance(self.filas[self.seleccion][k],(int,float)) else self.filas[self.seleccion][k] for k,l in self.columnas]
            if nueva:self.arbol.insert("","end",iid=str(self.seleccion),values=values)
            else:self.arbol.item(str(self.seleccion),values=values)
        else:self.refrescar();self.arbol.selection_set(str(self.seleccion))
        self.base={k:v.get() for k,v in self.vars.items()};self.error.config(text="");self._editar()
    def eliminar(self):
        exigir(self.seleccion is not None,"Selecciona una fila para eliminar.")
        self.filas.pop(self.seleccion);self.guardar(copia(self.filas));self.refrescar()
        # La edición pendiente pertenece a la fila eliminada: no aplicarla a
        # la siguiente fila cuando nuevo() restablezca el formulario.
        self.base={k:v.get() for k,v in self.vars.items()}
        self.nuevo();self._editar()
    def flush(self):
        if {k:v.get() for k,v in self.vars.items()}!=self.base:self.aplicar(preservar_entrada=True)
