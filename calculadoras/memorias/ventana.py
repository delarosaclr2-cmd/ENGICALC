"""Ventanas nativas de las tres memorias; Tkinter + Matplotlib, sin navegador.

Sistema visual ENGICALC v1 (``calculadoras.interfaz.tema``): ruta y título de la memoria, actualización
automática, subpestañas segmentadas, KPI en mono, Exportar como acción principal y serie de gráfica
equipo (azul) / sistema (naranja) / afinidad (gris discontinuo). Solo apariencia: cálculos, textos,
casos y reportes no cambian.
"""
from __future__ import annotations
import datetime
import math
import tkinter as tk
from functools import wraps
from pathlib import Path
from tkinter import ttk,filedialog,messagebox

from .comun import copia,numero,exigir,catalogo
from .editores import EditorTabla
from . import reportes
from ..interfaz import tema


def obtener(obj,path):
    for key in path.split("."):obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj


def asignar(obj,path,value):
    keys=path.split(".")
    for key in keys[:-1]:obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    if isinstance(obj,list):obj[int(keys[-1])]=value
    else:obj[keys[-1]]=value


def sin_actualizacion_automatica(metodo):
    """Las escrituras del programa no se interpretan como cambios del usuario."""
    @wraps(metodo)
    def ejecutar(self,*args,**kwargs):
        self._auto_suspension+=1
        try:return metodo(self,*args,**kwargs)
        finally:self._auto_suspension-=1
    return ejecutar


class VentanaMemoria(tk.Toplevel):
    AUTO_DELAY_MS=400
    def __init__(self,padre,memoria):
        super().__init__(padre);self.memoria=memoria;self.calc=memoria;self.motor=memoria.motor
        self._auto_after=None;self._auto_suspension=1;self._angle_dirty=False;self._angle_trace=None
        self.estado=self.motor.por_defecto();self.resultado=None;self.variables={};self.campos={};self.widgets={};self.editores=[];self._scopes={};self._scope="general";self._busy=False
        self.unidades=tk.StringVar(value="SI");self._sistema="SI";self.segmento="main";self._mode="design"
        self.documento={k:"" for k in ["Proyecto","Cliente","Ubicación / planta","Fecha","Equipo / TAG","Elaboró","Revisó","Documento / revisión"]}
        self.documento["Fecha"]=datetime.date.today().strftime("%d/%m/%Y")
        self.title(memoria.nombre+" — RMR Ingeniería");tema.aplicar(self);self.configure(background=tema.FONDO)
        w=min(1600,self.winfo_screenwidth()-60);h=min(950,self.winfo_screenheight()-110);self.geometry(f"{w}x{h}+25+20");self.minsize(1050,650)
        self._estilos();self._construir();self.calcular();self._auto_suspension=0;self.protocol("WM_DELETE_WINDOW",self.destroy)
    def _estilos(self):
        s=ttk.Style(self)
        for name in ["RMR.TFrame","RMR.TLabel","RMR.Small.TLabel","RMR.TCheckbutton"]:s.configure(name,background=tema.SUPERFICIE)
        s.configure("RMR.TLabel",font=tema.fuente("cuerpo"),foreground=tema.TEXTO)
        s.configure("RMR.Small.TLabel",font=tema.fuente("pequeno"),foreground=tema.TEXTO_2)
        s.configure("RMR.Title.TLabel",font=tema.fuente("titulo"),background=tema.SUPERFICIE,foreground=tema.MARINO)
        s.configure("RMR.Ruta.TLabel",font=tema.fuente("pequeno"),background=tema.SUPERFICIE,foreground=tema.TEXTO_2)
        s.configure("RMR.Estado.TLabel",font=tema.fuente("pequeno"),background=tema.SUPERFICIE,foreground=tema.TEXTO_2)
        s.configure("RMR.TButton",padding=(12,5))
        s.configure("RMR.TEntry",padding=(8,4))
        s.configure("RMR.TCombobox",padding=(8,4))
        s.configure("RMR.TCheckbutton",font=tema.fuente("cuerpo"),padding=(0,4),background=tema.SUPERFICIE)
        s.map("RMR.TCheckbutton",indicatorbackground=[("selected",tema.AZUL),("disabled",tema.DESHABILITADO)],background=[("active",tema.SUPERFICIE)])
        s.configure("RMR.TNotebook.Tab",padding=(14,6))
        s.configure("RMR.TLabelframe",background=tema.SUPERFICIE,padding=12)
        s.configure("RMR.TLabelframe.Label",font=tema.fuente("grupo"),background=tema.SUPERFICIE,foreground=tema.MARINO)
        s.configure("RMR.Treeview",font=tema.fuente("cuerpo"),rowheight=tema._px(self,28))
        s.configure("RMR.Treeview.Heading",font=tema.fuente("etiqueta"))
    def _construir(self):
        header=ttk.Frame(self,style="RMR.TFrame",padding=(24,12));header.pack(fill="x");header.columnconfigure(1,weight=1)
        if reportes.LOGO.is_file():
            from PIL import Image,ImageTk
            image=Image.open(reportes.LOGO);image.thumbnail((180,46));self.logo=ImageTk.PhotoImage(image);ttk.Label(header,image=self.logo,style="RMR.TLabel").grid(row=0,column=0,sticky="w",padx=(0,24))
        titulos=ttk.Frame(header,style="RMR.TFrame");titulos.grid(row=0,column=1,sticky="w")
        ttk.Label(titulos,text=f"Calculadoras  ›  {self.memoria.disciplina}  ›  {self.memoria.nombre}",style="RMR.Ruta.TLabel").pack(anchor="w")
        fila_titulo=ttk.Frame(titulos,style="RMR.TFrame");fila_titulo.pack(anchor="w",pady=(2,0))
        ttk.Label(fila_titulo,text=self.memoria.nombre.split(" ·")[0],style="RMR.Title.TLabel").pack(side="left")
        tema.chip(fila_titulo,"Memoria de cálculo","nota").pack(side="left",padx=(12,0))
        controls=ttk.Frame(header,style="RMR.TFrame");controls.grid(row=0,column=2,sticky="e")
        def ajustar_cabecera(event):
            narrow=event.width<1320
            controls.grid_configure(row=1 if narrow else 0,column=0 if narrow else 2,columnspan=3 if narrow else 1,pady=(10,0) if narrow else 0,sticky="e")
        header.bind("<Configure>",ajustar_cabecera)
        for label,command in [("Restablecer ejemplo",self.restablecer),("Datos del documento",self.editar_documento)]:ttk.Button(controls,text=label,command=command,style="RMR.TButton").pack(side="left",padx=4)
        for label,options in [("Caso",[("Guardar caso…",self.guardar_caso),("Abrir caso…",self.abrir_caso)]),("Exportar",[("PDF…",self.exportar_pdf),("Excel…",self.exportar_excel)])]:
            # actualización automática: no hay botón Calcular y Exportar es la acción principal
            button=ttk.Menubutton(controls,text=label+" ▾",style="Primario.TMenubutton" if label=="Exportar" else "TMenubutton");menu=tk.Menu(button,tearoff=False)
            for text,command in options:menu.add_command(label=text,command=command)
            button["menu"]=menu;button.pack(side="left",padx=4)
        tk.Frame(self,height=1,background=tema.BORDE).pack(fill="x")
        self.paned=ttk.PanedWindow(self,orient="horizontal");self.paned.pack(fill="both",expand=True,padx=24,pady=16)
        self.left=ttk.Frame(self.paned,style="RMR.TFrame",width=560);right=ttk.Frame(self.paned,style="RMR.TFrame");self.paned.add(self.left,weight=0);self.paned.add(right,weight=1)
        unitbar=ttk.Frame(self.left,style="RMR.TFrame",padding=10);unitbar.pack(fill="x")
        tema.chip(unitbar,"● Actualización automática","correcto").pack(side="left");ttk.Label(unitbar,text="  Unidades de captura",style="RMR.Small.TLabel").pack(side="left")
        combo=ttk.Combobox(unitbar,textvariable=self.unidades,values=["SI","US"],state="readonly",width=7);combo.pack(side="right");combo.bind("<<ComboboxSelected>>",lambda e:self.cambiar_unidades())
        self.notebook=ttk.Notebook(self.left,style="RMR.TNotebook");self.notebook.pack(fill="both",expand=True)
        self.inputs_host=ttk.Frame(self.notebook);self.notebook.add(self.inputs_host,text="Datos")
        self._armar_inputs()
        resultframe=ttk.Frame(self.notebook);self.notebook.add(resultframe,text="Resultados")
        self.tabla=ttk.Treeview(resultframe,columns=("value","unit"),show="tree headings",style="RMR.Treeview")
        self.tabla.heading("#0",text="Resultado");self.tabla.heading("value",text="Valor");self.tabla.heading("unit",text="Unidad")
        self.tabla.column("#0",width=290,minwidth=170);self.tabla.column("value",width=110,stretch=False,anchor="e");self.tabla.column("unit",width=80,stretch=False)
        scroll=ttk.Scrollbar(resultframe,command=self.tabla.yview);self.tabla.configure(yscrollcommand=scroll.set);scroll.pack(side="right",fill="y");self.tabla.pack(fill="both",expand=True)
        self.ecuaciones=tk.Text(resultframe,height=8,wrap="word",font=tema.fuente("mono_pequeno"),relief="flat",background=tema.SUPERFICIE_2,foreground=tema.TEXTO,padx=12,pady=8,highlightthickness=0);self.ecuaciones.pack(fill="x")
        self.metricas=ttk.Frame(right,style="RMR.TFrame",padding=16);self.metricas.pack(fill="x");self.metric_cells=[];self.metricas.bind("<Configure>",lambda e:self._distribuir_metricas(e.width))
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
        self.figura=Figure(figsize=(8,7),dpi=100,facecolor="white",layout="constrained");self.canvas=FigureCanvasTkAgg(self.figura,master=right);self.canvas.get_tk_widget().pack(fill="both",expand=True)
        toolbar=NavigationToolbar2Tk(self.canvas,right,pack_toolbar=False);toolbar.update();toolbar.pack(fill="x")
        tk.Frame(self,height=1,background=tema.BORDE).pack(fill="x")
        self.aviso=ttk.Label(self,text="",style="RMR.Estado.TLabel",padding=(24,8),wraplength=1450);self.aviso.pack(fill="x")
        self.bind("<Control-s>",lambda e:self.guardar_caso());self.bind("<F5>",lambda e:self.calcular())
    def scroll_tab(self,notebook,title):
        frame=ttk.Frame(notebook);notebook.add(frame,text=title);canvas=tk.Canvas(frame,highlightthickness=0,bg="white",width=540);bar=ttk.Scrollbar(frame,command=canvas.yview);canvas.configure(yscrollcommand=bar.set);bar.pack(side="right",fill="y");canvas.pack(fill="both",expand=True)
        body=ttk.Frame(canvas,style="RMR.TFrame",padding=8);window=canvas.create_window((0,0),window=body,anchor="nw");body.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")));canvas.bind("<Configure>",lambda e:canvas.itemconfigure(window,width=e.width))
        def wheel(e):
            canvas.yview_scroll(-1 if e.delta>0 else 1,"units");return "break"
        def route(e):
            pointer=self.winfo_containing(e.x_root,e.y_root)
            if pointer and str(pointer).startswith(str(frame)):return wheel(e)
        self.bind("<MouseWheel>",route,add="+")
        return body
    def grupo(self,padre,title):
        frame=ttk.LabelFrame(padre,text=title,style="RMR.TLabelframe");frame.pack(fill="x",padx=3,pady=7);frame.columnconfigure(0,weight=1);return frame
    def unit(self,path,f):
        q=f.get("quantity","");system=self._sistema
        if "units" in f:return f["units"][system]
        if self.memoria.modulo!="ductos":
            c=catalogo(self.memoria.modulo)
            if path=="inputs.kval":return (12960000,"m/(m³/h)²") if system=="SI" else (.3048/6.30901964e-5**2,"ft/GPM²")
            if q:
                u=c["units"][q][system] if self.memoria.modulo=="agitadores" else c["units"][system][q]
                return u.get("f",1),u.get("u",u.get("lbl",""))
        return 1,f.get("unit","")
    def campo(self,padre,path,label,tipo="number",options=None,quantity="",unit="",units=None,callback=None):
        row=getattr(padre,"_rmr_row",0);padre._rmr_row=row+1
        f=dict(label=label,type=tipo,options=options or [],quantity=quantity,unit=unit,units=units) if units else dict(label=label,type=tipo,options=options or [],quantity=quantity,unit=unit)
        self.campos[path]=f;self._scopes[path]=self._scope
        value=obtener(self.estado,path)
        if tipo=="checkbox":
            var=tk.BooleanVar(value=value);widget=ttk.Checkbutton(padre,text=label,variable=var,style="RMR.TCheckbutton",command=callback);widget.grid(row=row,column=0,columnspan=2,sticky="w",pady=5)
        else:
            factor,un=self.unit(path,f);shown=value
            if tipo=="number":shown=(value*1.8+32 if self._sistema=="US" else value) if quantity=="temp" else value/factor
            var=tk.StringVar(value=f"{shown:.10g}" if isinstance(shown,(int,float)) else str(shown))
            labelwidget=ttk.Label(padre,text=label+(f" ({un})" if un else ""),style="RMR.TLabel",wraplength=255);labelwidget.grid(row=row,column=0,sticky="w",pady=5,padx=(0,12));f["label_widget"]=labelwidget
            if options:
                f["labels"]={str(v):str(text) for v,text in options};f["reverse"]={str(text):str(v) for v,text in options};var.set(f["labels"].get(str(value),str(value)))
                widget=ttk.Combobox(padre,textvariable=var,values=list(f["reverse"]),state="readonly",width=20,font=("Segoe UI",11),style="RMR.TCombobox")
                if callback:widget.bind("<<ComboboxSelected>>",lambda e:callback())
            else:widget=ttk.Entry(padre,textvariable=var,width=20 if tipo=="text" else 13,font=("Segoe UI",11),style="RMR.TEntry")
            widget.grid(row=row,column=1,sticky="ew",pady=5)
        self.variables[path]=var;self.widgets[path]=widget
        anterior=[var.get()]
        def editar(*args):
            value=var.get()
            if value==anterior[0]:return
            anterior[0]=value
            if path.startswith("op.Kbal.") and not self._auto_suspension and not self._busy:self._angle_dirty=False
            self._programar_actualizacion()
        f["auto_trace"]=var.trace_add("write",editar)
        return widget
    def _cancelar_actualizacion(self):
        if self._auto_after is not None:
            try:self.after_cancel(self._auto_after)
            except tk.TclError:pass
            self._auto_after=None
    def _programar_actualizacion(self):
        if self._auto_suspension or self._busy:return
        self._cancelar_actualizacion()
        self._auto_after=self.after(self.AUTO_DELAY_MS,self._actualizar_automaticamente)
        if hasattr(self,"aviso"):self.aviso.configure(text="Actualizando al terminar de escribir…",foreground=tema.TEXTO_2)
    def _actualizar_automaticamente(self):
        self._auto_after=None
        if self.winfo_exists():self.calcular(automatico=True)
    def _desvincular_campo(self,path):
        trace=self.campos[path].get("auto_trace")
        if trace:
            try:self.variables[path].trace_remove("write",trace)
            except tk.TclError:pass
    def _desvincular_angulo(self):
        if self._angle_trace:
            try:self.angle_var.trace_remove("write",self._angle_trace)
            except tk.TclError:pass
        self._angle_trace=None;self._angle_dirty=False
    def guardar_campos(self):
        updates=[]
        for path,var in self.variables.items():
            f=self.campos[path];value=var.get()
            if f.get("reverse"):value=f["reverse"].get(value,value)
            elif f["type"]=="number":
                value=numero(value,f["label"]);factor,unit=self.unit(path,f)
                value=(value-32)/1.8 if f["quantity"]=="temp" and self._sistema=="US" else value*factor
            updates.append((path,value))
        for path,value in updates:asignar(self.estado,path,value)
        for ed in list(self.editores):ed.flush()
        if self.memoria.modulo=="ductos" and self._angle_dirty:
            exigir(self.estado["mode"]=="operation","El ángulo manual se aplica en modo Operación.")
            p,b=self._seg_ref();exigir(p!="main","Selecciona un ramal.")
            self.estado["op"]["Kbal"][int(p.split(".")[1])]=self.motor.damper_extra_k(self.angle_var.get());self._angle_dirty=False
        if self.memoria.modulo=="ductos":self.estado["units"]={"flow":"m3h" if self._sistema=="SI" else "cfm","pressure":"Pa" if self._sistema=="SI" else "inH2O"}
    @sin_actualizacion_automatica
    def _armar_inputs(self):
        self._cancelar_actualizacion()
        self._desvincular_angulo()
        self._availability_signature=None;self._visibility_signature=None
        for path in self.variables:self._desvincular_campo(path)
        for child in self.inputs_host.winfo_children():child.destroy()
        self.variables={};self.campos={};self.widgets={};self._scopes={};self.editores=[];self._scope="general"
        self.tabs=ttk.Notebook(self.inputs_host,style="Segmentado.TNotebook");self.tabs.pack(fill="both",expand=True)
        if self.memoria.modulo=="ductos":self._armar_ductos();return
        groups={};pages={}
        for f in catalogo(self.memoria.modulo)["fields"]:
            if self.memoria.modulo=="agitadores":page="Mecánica" if f["group"] in ["Motor y reductor","Flecha de agitación","Sello y acoplamiento"] else "Proceso"
            else:page="Bomba y curvas" if f["group"] in ["Datos de la bomba","Curvas del fabricante","Criterios de selección","Configura la bomba"] else "Sistema"
            if page not in pages:pages[page]=self.scroll_tab(self.tabs,page)
            if f["group"] not in groups:groups[f["group"]]=self.grupo(pages[page],f["group"])
            label=f["label"]
            if f["options"]:label=label.split(f["options"][0][1])[0].strip() or f["id"]
            self.campo(groups[f["group"]],"inputs."+f["id"],label,tipo="choice" if f["options"] else f["type"],options=f["options"],quantity=f["quantity"],unit=f["unit"])
        if self.memoria.modulo=="bombas":
            page=self.scroll_tab(self.tabs,"Puntos de curva")
            for key,title,unit in [("hq","Altura del fabricante","m"),("eq","Eficiencia","%"),("nq","NPSH requerido","m")]:
                g=self.grupo(page,title);factorQ=1/3600 if self._sistema=="SI" else 6.30901964e-5;factorY=1 if key=="eq" else 1 if self._sistema=="SI" else .3048
                ed=EditorTabla(g,[("x","Caudal "+("m³/h" if self._sistema=="SI" else "GPM")),("y",unit if self._sistema=="SI" or key=="eq" else "ft")],self.estado["curves"][key],lambda rows,k=key:self.estado["curves"].__setitem__(k,rows),convertir={"x":factorQ,"y":factorY},al_cambiar=self._programar_actualizacion);ed.pack(fill="x");self.editores.append(ed)
        else:
            ttk.Button(groups["Geometría del tanque"],text="Aplicar proporciones estándar",command=self._proporciones,style="RMR.TButton").grid(row=100,column=0,columnspan=2,sticky="w",pady=8)
        self._group_order=list(groups.items());self._habilitar()
    def _habilitar(self):
        if self.memoria.modulo=="ductos":return
        d=self.estado["inputs"]
        disabled=[]
        if self.memoria.modulo=="agitadores":
            if not d["manNp"]:disabled += ["Np","Nq"]
            if d["autoD"]:disabled += ["dsel"]
            if d["mat"]!="mcust":disabled += ["Sy","Su","Emod","rhom"]
        else:
            for flag,key in [("autoRho","rho"),("autoPv","pvap"),("autoPatm","patm")]:
                if d[flag]:disabled.append(key)
            if not d["manualK"]:disabled.append("kval")
            if d["bepMode"]!="manual":disabled += ["bepQ","bepH"]
            if not d["affOn"]:disabled += ["rpm2","dimp2"]
            else:disabled.append("dimp2" if d["affVar"]=="N" else "rpm2")
        for key in disabled:
            if "inputs."+key in self.widgets:self.widgets["inputs."+key].configure(state="disabled")
        # Checkbox changes make manual fields available immediately.
        for path,w in self.widgets.items():
            if self.campos[path]["type"]=="checkbox":w.configure(command=self._activar_manuales)
        if self.memoria.modulo=="agitadores":
            self.widgets["inputs.mat"].bind("<<ComboboxSelected>>",lambda e:self._aplicar_material())
            self.widgets["inputs.imp"].bind("<<ComboboxSelected>>",lambda e:self._aplicar_impulsor())
            self.widgets["inputs.freq"].bind("<<ComboboxSelected>>",lambda e:self._frecuencia())
            self._frecuencia()
            for key in ["orient","fluido"]:self.widgets["inputs."+key].bind("<<ComboboxSelected>>",lambda e:self._activar_manuales())
            self._visibilidad_agitador()
        else:
            self.widgets["inputs.mat"].bind("<<ComboboxSelected>>",lambda e:self._aplicar_tuberia())
            for key in ["bepMode","affVar"]:self.widgets["inputs."+key].bind("<<ComboboxSelected>>",lambda e:self._activar_manuales())
        self._availability_signature=self._firma_disponibilidad()
    def _firma_disponibilidad(self):
        d=self.estado.get("inputs",{})
        return tuple(d.get(k) for k in ["orient","fluido","chkSol","manNp","autoD","mat","freq","autoRho","autoPv","autoPatm","manualK","bepMode","affOn","affVar"])
    @sin_actualizacion_automatica
    def _actualizar_disponibilidad(self):
        if self.memoria.modulo=="ductos" or self._availability_signature==self._firma_disponibilidad():return
        for path,w in self.widgets.items():
            if self.campos[path]["type"]=="number":w.configure(state="normal")
        self._habilitar()
    def _avisar_edicion(self,error):
        self.aviso.configure(text="Completa o corrige el dato: "+str(error),foreground=tema.ADVERTENCIA)
        self._programar_actualizacion()
    def _aplicar_tuberia(self):
        try:
            self.guardar_campos();value=self.estado["inputs"]["mat"]
            if value:self.estado["inputs"].update(cs=float(value),cd=float(value))
            self.sincronizar()
        except ValueError as e:self._avisar_edicion(e)
    def _proporciones(self):
        try:
            self.guardar_campos();d=self.estado["inputs"];T=numero(d["T"],"Diámetro del tanque",positivo=True);d.update(D=.35*T,C=.33*T,H=T,Htk=1.1*T,Wb=T/12);self.sincronizar();self.calcular()
        except ValueError as e:self.mostrar_error(e)
    def _visibilidad_agitador(self):
        d=self.estado["inputs"];vertical=d["orient"]=="vertical"
        signature=(d["orient"],d["fluido"],d["chkSol"])
        if self._visibility_signature==signature:return
        self._visibility_signature=signature
        for name,frame in self._group_order:
            frame.pack_forget()
            if name!="Suspensión fibrosa" or d["fluido"]=="fibra":frame.pack(fill="x",padx=3,pady=7)
        for key,visible in [("nb",vertical),("Wb",vertical),("thH",not vertical),("thV",not vertical)]+[(k,d["chkSol"]) for k in ["dp","rhos","Xs","Sz"]]:
            path="inputs."+key
            for widget in [self.widgets[path],self.campos[path].get("label_widget")]:
                if widget is not None:
                    if visible:widget.grid()
                    else:widget.grid_remove()
    def _activar_manuales(self):
        try:self.guardar_campos()
        except ValueError:return
        self._actualizar_disponibilidad()
    def _frecuencia(self):
        var=self.variables["inputs.freq"];f=self.campos["inputs.freq"];freq=f["reverse"].get(var.get(),var.get());rpms=catalogo("agitadores")["RPM"][str(freq)]
        f=self.campos["inputs.nmot"];current=f["reverse"].get(self.variables["inputs.nmot"].get(),self.variables["inputs.nmot"].get());chosen=current if current in [str(x) for x in rpms] else str(rpms[1]);f["labels"]={str(x):str(x) for x in rpms};f["reverse"]={str(x):str(x) for x in rpms};self.widgets["inputs.nmot"].configure(values=[str(x) for x in rpms]);self.variables["inputs.nmot"].set(chosen)
    def _aplicar_material(self):
        try:
            self.guardar_campos();m=catalogo("agitadores")["materials"][self.estado["inputs"]["mat"]]
            if m["Sy"] is not None:self.estado["inputs"].update(Sy=m["Sy"],Su=m["Su"],Emod=m["E"],rhom=m["rho"])
            self.sincronizar();self._activar_manuales()
        except ValueError as e:self._avisar_edicion(e)
    def _aplicar_impulsor(self):
        try:
            self.guardar_campos();d=self.estado["inputs"];imp=catalogo("agitadores")["impellers"][d["imp"]]
            if imp["S"] is not None:d["Sz"]=imp["S"]
            if not d["manNp"]:d["Nq"]=imp["Nq"]
            self.sincronizar()
        except ValueError as e:self._avisar_edicion(e)
    def cambiar_unidades(self):
        target=self.unidades.get()
        try:self.guardar_campos()
        except ValueError as e:self.unidades.set(self._sistema);self.mostrar_error(e);return
        self._sistema=target;self._armar_inputs();self.calcular()
    def restablecer(self):
        if not messagebox.askyesno("Restablecer ejemplo","¿Restablecer los datos de cálculo al ejemplo inicial?",parent=self):return
        self.estado=self.motor.por_defecto();self.segmento="main";self._mode="design";self._armar_inputs();self.calcular()
    def mostrar_error(self,error):
        self.aviso.configure(text=str(error),foreground=tema.ERROR);messagebox.showerror("Revisa los datos",str(error),parent=self)
    def destroy(self):
        self._auto_suspension+=1;self._cancelar_actualizacion()
        self._desvincular_angulo()
        for path in self.variables:self._desvincular_campo(path)
        if hasattr(self,"canvas"):
            widget=self.canvas.get_tk_widget()
            for name in ["_idle_draw_id","_event_loop_id"]:
                handle=getattr(self.canvas,name,None)
                if handle:
                    try:widget.after_cancel(handle)
                    except tk.TclError:pass
                    setattr(self.canvas,name,None)
        super().destroy()
    def calcular(self,automatico=False):
        if self._busy:return None
        self._cancelar_actualizacion()
        self._busy=True
        try:
            self.guardar_campos()
            if self.memoria.modulo=="ductos" and self.estado["mode"]=="operation" and self._mode!="operation":
                temp=copia(self.estado);temp["mode"]="design";self.estado["op"]["Kbal"]=self.motor.calcular(temp)["KbalDesign"]
            result=self.motor.calcular(self.estado);self.resultado=result
            if self.memoria.modulo=="ductos":self._mode=self.estado["mode"];self._refrescar_arbol()
            else:
                self.estado["inputs"].update(result["inputs"])
                if self.memoria.modulo=="agitadores":self.estado["inputs"].update(Np=result["Np"],Nq=result["Nq"],dsel=result["dad"])
            self.sincronizar(preservar_foco=automatico)
            self._actualizar_disponibilidad()
            if self.memoria.modulo=="ductos":self._balance_readout();self._actualizar_propuesta()
            self._resultados();self.dibujar()
            self.aviso.configure(text="✓ Actualizado automáticamente" if not result["warnings"] else "  •  ".join(result["warnings"]),foreground=tema.CORRECTO if not result["warnings"] else tema.ADVERTENCIA)
            return result
        except (ValueError,ArithmeticError,KeyError,TypeError) as error:
            self.resultado=None;self.tabla.delete(*self.tabla.get_children())
            self.metric_cells=[]
            for child in self.metricas.winfo_children():child.destroy()
            ttk.Label(self.metricas,text="Corrige los datos para actualizar los resultados.",style="RMR.TLabel").pack(anchor="w")
            self.figura.clear();self.canvas.draw_idle()
            if automatico:self.aviso.configure(text="Completa o corrige el dato: "+str(error),foreground=tema.ADVERTENCIA)
            else:self.mostrar_error(error)
            return None
        finally:self._busy=False
    @sin_actualizacion_automatica
    def sincronizar(self,preservar_foco=False):
        focused=self.focus_get() if preservar_foco else None
        for path,var in self.variables.items():
            f=self.campos[path];value=obtener(self.estado,path)
            if preservar_foco and self.widgets[path] is focused and f["type"] in ["number","text"]:continue
            if f.get("labels"):var.set(f["labels"].get(str(value),str(value)))
            elif f["type"]=="number":
                factor,_=self.unit(path,f);shown=value*1.8+32 if f["quantity"]=="temp" and self._sistema=="US" else value/factor;var.set(f"{shown:.10g}")
            else:var.set(value)
    def _resultados(self):
        self.tabla.delete(*self.tabla.get_children())
        for row in self.resultado["rows"]:self.tabla.insert("","end",text=row["etiqueta"],values=(reportes.texto(row["valor"]),row["unidad"]))
        self.ecuaciones.configure(state="normal");self.ecuaciones.delete("1.0","end");self.ecuaciones.insert("1.0","\n\n".join(self.resultado["equations"])+"\n\nFuentes y alcance\n\n"+"\n\n".join(self.resultado.get("references",[])));self.ecuaciones.configure(state="disabled")
        for c in self.metricas.winfo_children():c.destroy()
        self.metric_cells=[]
        r=self.resultado;kind=self.memoria.modulo
        if kind=="agitadores":metrics=[("Volumen",r["Vol"],"m³"),("Proceso",r["P"]/1000,"kW"),("Motor",r["kwSel"],"kW"),("Flecha",r["dad"]*1000,"mm")]
        elif kind=="bombas":metrics=[("Caudal real",r["Qop"]*3600 if r["Qop"] else None,"m³/h"),("Altura real",r["Hop"],"m"),("Potencia eje",r["PshaftOp"]/1000 if r["PshaftOp"] else None,"kW"),("NPSHa real",r["npOp"]["a"] if r["npOp"] else None,"m")]
        else:op=r["op"];metrics=[("Caudal real",op["Q"]*3600 if op["found"] else None,"m³/h"),("Presión total",op["dP"] if op["found"] else None,"Pa"),("Potencia eje",op["power"]/1000 if op["found"] and op["power"] else None,"kW"),("ΔPt diseño",r["duty"]["dP"],"Pa")]
        for i,(label,value,unit) in enumerate(metrics):
            cell=ttk.Frame(self.metricas,style="RMR.TFrame");cell.grid(row=0,column=i,sticky="ew",padx=(0,18));self.metricas.columnconfigure(i,weight=1)
            self.metric_cells.append(cell)
            shown="—" if value is None else f"{value:,.0f}" if value==int(value) or abs(value)>=1000 else f"{value:,.2f}"
            ttk.Label(cell,text=label,style="RMR.Small.TLabel").pack(anchor="w");ttk.Label(cell,text=f"{shown} {unit}",font=tema.fuente("kpi"),background=tema.SUPERFICIE,foreground=tema.MARINO).pack(anchor="w")
        self._distribuir_metricas(self.metricas.winfo_width())
    def _distribuir_metricas(self,width):
        columns=2 if width<720 else 4
        for i in range(4):self.metricas.columnconfigure(i,weight=1 if i<columns else 0)
        for i,cell in enumerate(self.metric_cells):
            if cell.winfo_exists():cell.grid_configure(row=i//columns,column=i%columns,pady=(0,8))
    def editar_documento(self):
        win=tk.Toplevel(self);win.title("Datos del documento");win.transient(self);frame=ttk.Frame(win,padding=20);frame.pack(fill="both",expand=True);variables={}
        for i,(k,v) in enumerate(self.documento.items()):
            ttk.Label(frame,text=k).grid(row=i,column=0,sticky="w",padx=(0,15),pady=7);var=tk.StringVar(value=v);variables[k]=var;ttk.Entry(frame,textvariable=var,width=55).grid(row=i,column=1,pady=7)
        def save():self.documento={k:v.get().strip() for k,v in variables.items()};win.destroy()
        ttk.Button(frame,text="Guardar",command=save,style="RMR.TButton").grid(row=8,column=1,sticky="e",pady=10)
    def guardar_caso(self):
        try:
            self.guardar_campos();self.motor.calcular(self.estado)
            ruta=filedialog.asksaveasfilename(parent=self,defaultextension=".json",filetypes=[("Caso RMR","*.json")],initialfile=self.memoria.id+".json")
            if ruta:reportes.guardar_caso(ruta,self.memoria,self.estado,self.documento,self._sistema);self.aviso.configure(text="Caso guardado: "+ruta)
        except (ValueError,OSError) as e:self.mostrar_error(e)
    def abrir_caso(self):
        ruta=filedialog.askopenfilename(parent=self,filetypes=[("Caso RMR","*.json")])
        if ruta:self.cargar_caso(ruta)
    def cargar_caso(self,ruta):
        try:
            c=reportes.abrir_caso(ruta)
            archivo={"memoria_agitadores":"revisar_agitadores.py","memoria_bombas":"revisar_bombas.py","memoria_hvac":"revisar_ductos_hvac.py"}[c["calculadora"]]
            exigir(c["calculadora"]==self.memoria.id,f"Este caso pertenece a otra memoria; ejecuta {archivo} y usa Caso → Abrir caso.")
            self.estado=c["datos"];self.documento.update(c.get("documento",{}));self._sistema=c.get("preferencias",{}).get("unidades","SI");self.unidades.set(self._sistema);self.segmento="main";self._mode=self.estado.get("mode","design");self._armar_inputs();return self.calcular()
        except (ValueError,OSError) as e:self.mostrar_error(e);return None
    def exportar_pdf_a(self,ruta):
        if self.calcular() is None:return False
        reportes.exportar_pdf(ruta,self.memoria,self.estado,self.resultado,self.documento,self.figura);return True
    def exportar_excel_a(self,ruta):
        if self.calcular() is None:return False
        reportes.exportar_excel(ruta,self.memoria,self.estado,self.resultado,self.documento);return True
    def exportar_pdf(self):
        ruta=filedialog.asksaveasfilename(parent=self,defaultextension=".pdf",filetypes=[("Memoria PDF","*.pdf")],initialfile=self.memoria.id+".pdf")
        if ruta:
            try:
                if self.exportar_pdf_a(ruta):self.aviso.configure(text="PDF exportado: "+ruta)
            except (ValueError,OSError) as e:self.mostrar_error(e)
    def exportar_excel(self):
        ruta=filedialog.asksaveasfilename(parent=self,defaultextension=".xlsx",filetypes=[("Excel","*.xlsx")],initialfile=self.memoria.id+".xlsx")
        if ruta:
            try:
                if self.exportar_excel_a(ruta):self.aviso.configure(text="Excel exportado: "+ruta)
            except (ValueError,OSError) as e:self.mostrar_error(e)

    # --------------------------------------------------------- Editor de la red HVAC
    def duct_field(self,padre,path,label,kind="number",options=None):
        units={
            "mm":{"SI":(.001,"mm"),"US":(.0254,"in")},"m":{"SI":(1,"m"),"US":(.3048,"ft")},
            "flow":{"SI":(1/3600,"m³/h"),"US":(1/2118.88,"CFM")},"pressure":{"SI":(1,"Pa"),"US":(249.0889,"in.wg")},
            "percent":{"SI":(.01,"%"),"US":(.01,"%")},"density":{"SI":(1,"kg/m³"),"US":(16.018463,"lb/ft³")},
        }
        types={"text":"text","choice":"choice","checkbox":"checkbox"}
        return self.campo(padre,path,label,tipo=types.get(kind,"number"),options=options,units=units.get(kind),quantity="temp" if kind=="temp" else "",unit={"vel":"m/s","area":"m²","temp":"°C","hz":"Hz","rpm":"rpm","rate":"Pa/m"}.get(kind,""))
    def _armar_ductos(self):
        red=self.scroll_tab(self.tabs,"Red");equipo=self.scroll_tab(self.tabs,"Equipos")
        g=self.grupo(red,"Servicio y modo de cálculo")
        self.duct_field(g,"systemKind","Servicio","choice",[("supply","Suministro"),("return","Retorno"),("exhaust","Extracción")])
        self.duct_field(g,"mode","Modo","choice",[("design","Diseño · balanceo automático"),("operation","Operación · dampers fijos")])
        self.duct_field(g,"method","Fricción","choice",[("colebrook","Colebrook-White"),("swamee","Swamee-Jain")])
        g=self.grupo(red,"Tramos conectados")
        self.arbol=ttk.Treeview(g,columns=("flow",),show="tree headings",height=7,style="RMR.Treeview");self.arbol.heading("#0",text="TAG / conexión");self.arbol.heading("flow",text="Diseño (m³/h)");self.arbol.column("#0",width=270);self.arbol.column("flow",width=140,stretch=False,anchor="e");self.arbol.pack(fill="x")
        self._refrescar_arbol();self.arbol.bind("<<TreeviewSelect>>",self._seleccionar_tramo)
        buttons=ttk.Frame(g,style="RMR.TFrame");buttons.pack(fill="x",pady=8)
        for label,command in [("Añadir hijo",self._add_child),("Añadir paralelo",self._add_parallel),("Eliminar",self._delete_segment)]:ttk.Button(buttons,text=label,command=command,style="RMR.TButton").pack(side="left",padx=(0,5))
        self.segment_host=ttk.Frame(red,style="RMR.TFrame");self.segment_host.pack(fill="x");self._render_segmento()
        g=self.grupo(equipo,"Aire y sitio")
        for path,label,kind,options in [("air.source","Densidad","choice",[("site","Por altitud y temperatura"),("manual","Captura manual")]),("air.alt","Altitud","m",None),("air.T","Temperatura","temp",None),("air.rhoManual","Densidad manual","density",None),("air.rhoCat","Densidad de catálogo","density",None),("air.correctComponents","Corregir pérdidas de AHU por densidad","checkbox",None)]:self.duct_field(g,path,label,kind,options)
        g=self.grupo(equipo,"Ventilador")
        presets=catalogo("ductos")["fanPresets"]
        widget=self.duct_field(g,"fan.preset","Curva","choice",[(k,v["name"]) for k,v in presets.items()]+[("custom","Curva personalizada")]);widget.bind("<<ComboboxSelected>>",lambda e:self._fan_preset())
        for path,label,kind,options in [("fan.pressureType","Presión del catálogo","choice",[("total","Total ΔPt"),("static","Estática AMCA ΔPs")]),("fan.efficiencyType","Eficiencia del catálogo","choice",[("total","Total ηt"),("static","Estática ηs")]),("fan.outletArea","Área de descarga","area",None),("fan.f0","Frecuencia nominal","hz",None),("fan.n0","Velocidad nominal","rpm",None),("fan.speed","Velocidad actual (% nominal)","percent",None)]:self.duct_field(g,path,label,kind,options)
        ttk.Button(g,text="Ajustar velocidad al diseño",command=self._ajustar_velocidad,style="RMR.TButton").grid(row=20,column=0,columnspan=2,sticky="w",pady=8)
        g=self.grupo(equipo,"Puntos del ventilador · datos de ejemplo")
        self.fan_table=EditorTabla(g,[("Q","Caudal (m³/h)"),("dP","Presión (Pa)"),("eta","Eficiencia (%)")],self.estado["fan"]["points"],lambda rows:self.estado["fan"].update(points=rows,preset="custom"),convertir={"Q":1/3600,"eta":.01},al_cambiar=self._programar_actualizacion);self.fan_table.pack(fill="x");self.editores.append(self.fan_table)
        g=self.grupo(equipo,"AHU · caudal nominal")
        self.duct_field(g,"ahu.Qnom","Caudal nominal","flow")
        for i,c in enumerate(self.estado["ahu"]["comps"]):
            g=self.grupo(equipo,c["name"]);p=f"ahu.comps.{i}"
            self.duct_field(g,p+".enabled","Instalado","checkbox");self.duct_field(g,p+".n","Exponente n")
            if "states" in c:
                self.duct_field(g,p+".state","Estado","choice",[("clean","Limpio"),("medium","Medio"),("dirty","Sucio")])
                for k,title in [("clean","Pérdida limpio"),("medium","Pérdida medio"),("dirty","Pérdida sucio")]:self.duct_field(g,p+".states."+k,title,"pressure")
            else:self.duct_field(g,p+".dp","Pérdida nominal","pressure")
        g=self.grupo(equipo,"Criterios de diseño")
        for p,label,kind in [("thresholds.vMain","Velocidad máxima principal","vel"),("thresholds.vBranch","Velocidad máxima ramales","vel"),("thresholds.minFlow","Caudal mínimo (% diseño)","percent"),("thresholds.pMargin","Margen de presión","percent")]:self.duct_field(g,p,label,kind)
    def _seg_ref(self):
        if self.segmento=="main":return "main",self.estado["main"]
        for i,b in enumerate(self.estado["branches"]):
            if b["id"]==self.segmento:return f"branches.{i}",b
        self.segmento="main";return "main",self.estado["main"]
    def _refrescar_arbol(self):
        if not hasattr(self,"arbol"):return
        t=self.motor.tree_meta(self.estado["branches"]);q=self.motor.design_flows(self.estado["branches"],t)
        self.arbol.delete(*self.arbol.get_children());self.arbol.insert("","end",iid="main",text=self.estado["main"]["name"],values=(f"{sum(q[i] for i in t['roots'])*3600:,.0f}",),open=True)
        def insert(i):
            b=self.estado["branches"][i];self.arbol.insert(b.get("parent","main"),"end",iid=b["id"],text=b["name"],values=(f"{q[i]*3600:,.0f}",),open=True)
            for j in t["children"][i]:insert(j)
        for i in t["roots"]:insert(i)
        if self.arbol.exists(self.segmento):self.arbol.selection_set(self.segmento)
    def _seleccionar_tramo(self,event=None):
        sel=self.arbol.selection()
        if not sel or sel[0]==self.segmento:return
        try:self.guardar_campos()
        except ValueError as e:self.mostrar_error(e);return
        self.segmento=sel[0];self._render_segmento()
    @sin_actualizacion_automatica
    def _render_segmento(self):
        self._desvincular_angulo()
        for ed in list(self.editores):
            if getattr(ed,"segment_editor",False):self.editores.remove(ed)
        for path in list(self.variables):
            if self._scopes[path]=="segment":self._desvincular_campo(path);self.variables.pop(path);self.campos.pop(path);self.widgets.pop(path);self._scopes.pop(path)
        for child in self.segment_host.winfo_children():child.destroy()
        self._scope="segment";p,b=self._seg_ref();t=self.motor.tree_meta(self.estado["branches"]);self.damper_info=None
        g=self.grupo(self.segment_host,"Datos del tramo")
        self.duct_field(g,p+".name","TAG","text")
        if p!="main":
            i=int(p.split(".")[1]);options=[("main",self.estado["main"]["name"])]+[(seg["id"],seg["name"]) for j,seg in enumerate(self.estado["branches"]) if j!=i and i not in t["paths"][j]]
            self.duct_field(g,p+".parent","Conectado a","choice",options)
            if not t["children"][i]:
                self.duct_field(g,p+".Qd","Caudal de diseño","flow")
            else:ttk.Label(g,text="Caudal derivado de los terminales de su subárbol.",style="RMR.Small.TLabel",wraplength=460).grid(row=20,column=0,columnspan=2,sticky="w",pady=7)
            self.duct_field(g,f"op.Kbal.{i}","K adicional (operación)")
            controls=ttk.Frame(g,style="RMR.TFrame");controls.grid(row=21,column=0,columnspan=2,sticky="ew",pady=8)
            self.angle_var=tk.StringVar(value=f"{self.motor.damper_angle(self.estado['op']['Kbal'][i]):.1f}")
            def editar_angulo(*args):
                if not self._auto_suspension and not self._busy:self._angle_dirty=True;self._programar_actualizacion()
            self._angle_trace=self.angle_var.trace_add("write",editar_angulo)
            ttk.Label(controls,text="Cierre orientativo (°)",style="RMR.Small.TLabel").pack(side="left");self.angle_entry=ttk.Entry(controls,textvariable=self.angle_var,width=7,font=("Segoe UI",11),style="RMR.TEntry");self.angle_entry.pack(side="left",padx=8)
            self.damper_apply=ttk.Button(controls,text="Aplicar ángulo",command=self._aplicar_angulo,style="RMR.TButton");self.damper_apply.pack(side="left")
            self.damper_info=ttk.Label(g,text="",style="RMR.Small.TLabel",wraplength=460);self.damper_info.grid(row=22,column=0,columnspan=2,sticky="ew")
        widget=self.duct_field(g,p+".shape","Sección","choice",[("round","Circular"),("rect","Rectangular")]);widget.bind("<<ComboboxSelected>>",lambda e:self._cambiar_seccion())
        for key,label,kind in ([("D","Diámetro","mm")] if b["shape"]=="round" else [("W","Ancho","mm"),("H","Alto","mm")])+[("L","Longitud","m"),("eps","Rugosidad ε","mm")]:self.duct_field(g,p+"."+key,label,kind)
        g=self.grupo(self.segment_host,"Accesorios · K referido a la sección del tramo")
        options=list(catalogo("ductos")["fittings"])
        ed=EditorTabla(g,[("type","Tipo"),("qty","Cantidad"),("K","K unitario")],b["fittings"],lambda rows,path=p:asignar(self.estado,path+".fittings",rows),opciones={"type":options},al_cambiar=self._programar_actualizacion);ed.segment_editor=True;ed.pack(fill="x");self.editores.append(ed)
        helptext="  ·  ".join(k+": "+v["name"] for k,v in catalogo("ductos")["fittings"].items());ttk.Label(g,text=helptext,wraplength=460,style="RMR.Small.TLabel").pack(fill="x",pady=6)
        g=self.grupo(self.segment_host,"Dimensionamiento de ductos")
        self.duct_field(g,"sizing.criterion","Dimensionar por","choice",[("velocity","Velocidad objetivo"),("friction","Fricción por metro")])
        for path,label,kind in [("sizing.velocity","Velocidad objetivo","vel"),("sizing.friction","Fricción objetivo","rate"),("sizing.aspect","Proporción rectangular W/H","number"),("sizing.rectStep","Incremento rectangular","mm"),("sizing.roundSeries","Diámetros disponibles (mm)","text")]:self.duct_field(g,path,label,kind)
        buttons=ttk.Frame(g,style="RMR.TFrame");buttons.grid(row=25,column=0,columnspan=2,sticky="ew",pady=8)
        for label,command in [("Proponer",self._proponer),("Aplicar",self._aplicar_propuesta),("Dimensionar red",self._dimensionar_red)]:ttk.Button(buttons,text=label,command=command,style="RMR.TButton").pack(side="left",padx=(0,5))
        self.propuesta_label=ttk.Label(g,text="La propuesta solo cambia las medidas al pulsar Aplicar.",wraplength=460,style="RMR.Small.TLabel");self.propuesta_label.grid(row=26,column=0,columnspan=2,sticky="ew")
        self._scope="general";self._proposal=None
        if p!="main" and self.estado["mode"]=="design":self.widgets[f"op.Kbal.{int(p.split('.')[1])}"].configure(state="disabled")
        ttk.Button(self.segment_host,text="Rebalancear dampers a los caudales de diseño",command=self._rebalancear,style="RMR.TButton").pack(fill="x",pady=8)
        self._balance_readout()
    @sin_actualizacion_automatica
    def _balance_readout(self):
        if not getattr(self,"damper_info",None):return
        p,b=self._seg_ref()
        if p=="main":return
        i=int(p.split(".")[1]);design=self.estado["mode"]=="design"
        value=self.resultado["Kbal"][i] if self.resultado and i<len(self.resultado["Kbal"]) else self.estado["op"]["Kbal"][i]
        self.damper_info.configure(text=f"Balanceo mostrado: K = {value:.3f} · cierre ≈ {self.motor.damper_angle(value):.1f}°. Tabla orientativa de mariposa; ajustar en campo.")
        self.widgets[f"op.Kbal.{i}"].configure(state="disabled" if design else "normal");self.damper_apply.configure(state="disabled" if design else "normal")
        self.angle_entry.configure(state="disabled" if design else "normal")
        if self.focus_get() is not self.angle_entry:self.angle_var.set(f"{self.motor.damper_angle(value):.1f}")
    def _aplicar_angulo(self):
        try:
            self.guardar_campos();exigir(self.estado["mode"]=="operation","El ángulo manual se aplica en modo Operación.");p,b=self._seg_ref();exigir(p!="main","Selecciona un ramal.");i=int(p.split(".")[1]);self.estado["op"]["Kbal"][i]=self.motor.damper_extra_k(self.angle_var.get());self.sincronizar();self.calcular()
        except ValueError as e:self.mostrar_error(e)
    def _cambiar_seccion(self):
        try:self.guardar_campos();self._render_segmento()
        except ValueError as e:self._avisar_edicion(e)
    def _add_child(self):self._add_segment(False)
    def _add_parallel(self):self._add_segment(True)
    def _add_segment(self,parallel):
        try:
            self.guardar_campos();exigir(len(self.estado["branches"])<40,"Se alcanzó el máximo de 40 tramos.");p,b=self._seg_ref();used={seg["id"] for seg in self.estado["branches"]};names={seg["name"] for seg in [self.estado["main"]]+self.estado["branches"]};k=1
            while f"n{k}" in used or f"T-{k}" in names:k+=1
            parent=b.get("parent","main") if parallel and p!="main" else b["id"]
            child=dict(id=f"n{k}",name=f"T-{k}",parent=parent,shape=b["shape"],D=.315,W=.4,H=.25,L=5,eps=b["eps"],Qd=500/3600,fittings=[])
            t=self.motor.tree_meta(self.estado["branches"])
            if not parallel and p!="main" and not t["children"][int(p.split('.')[1])]:
                child["Qd"]=b["Qd"];child["fittings"]=[f for f in b["fittings"] if f["type"] in ["diffuser","grille"]];b["fittings"]=[f for f in b["fittings"] if f["type"] not in ["diffuser","grille"]]
            self.estado["branches"].append(child);self.estado["op"]["Kbal"].append(0);self.segmento=child["id"];self._armar_inputs();self.calcular()
        except ValueError as e:self.mostrar_error(e)
    def _delete_segment(self):
        try:
            self.guardar_campos();p,b=self._seg_ref();exigir(p!="main","El principal se conserva como conexión común.");exigir(len(self.estado["branches"])>1,"Conserva al menos un terminal.")
            for seg in self.estado["branches"]:
                if seg["parent"]==b["id"]:seg["parent"]=b["parent"]
            i=int(p.split(".")[1]);self.estado["branches"].pop(i);self.estado["op"]["Kbal"].pop(i);self.segmento="main";self._armar_inputs();self.calcular()
        except ValueError as e:self.mostrar_error(e)
    def _proponer(self):
        try:
            self.guardar_campos();return self._actualizar_propuesta(avisar=True)
        except ValueError as e:self.mostrar_error(e);return None
    def _actualizar_propuesta(self,avisar=False):
        try:
            p,b=self._seg_ref();air=self.motor.build_air(self.estado);d=self.motor.design_analysis(self.estado,air);q=d["Qtot"] if p=="main" else d["Qd"][int(p.split('.')[1])]
            plan=self.motor.size_segment(b,q,air,self.estado["method"],self.estado["sizing"]);self._proposal=(p,plan)
            def section(s):return f"Ø {s['D']*1000:.1f} mm" if s["shape"]=="round" else f"{s['W']*1000:.1f} × {s['H']*1000:.1f} mm"
            self.propuesta_label.configure(text=f"Calculada: {section(plan['ideal'])}\nPropuesta: {section(plan['proposed'])}\nAdoptada: {section(b)}\nPropuesta: {plan['result']['V']:.2f} m/s · {plan['result']['dPf']:.2f} Pa/m\nAdoptada: {plan['current']['V']:.2f} m/s · {plan['current']['dPf']:.2f} Pa/m")
            return plan
        except ValueError as e:
            self._proposal=None;self.propuesta_label.configure(text="Revisa el objetivo de dimensionamiento: "+str(e))
            if avisar:self.mostrar_error(e)
            return None
    def _aplicar_propuesta(self):
        if self._proponer() is None:return
        p,plan=self._proposal;b=obtener(self.estado,p)
        for key in (["D"] if b["shape"]=="round" else ["W","H"]):b[key]=plan["proposed"][key]
        self._render_segmento();self.calcular()
    def _dimensionar_red(self):
        try:
            self.guardar_campos();air=self.motor.build_air(self.estado);d=self.motor.design_analysis(self.estado,air);segs=[self.estado["main"]]+self.estado["branches"];flows=[d["Qtot"]]+d["Qd"]
            plans=[self.motor.size_segment(b,q,air,self.estado["method"],self.estado["sizing"]) for b,q in zip(segs,flows)]
            for b,plan in zip(segs,plans):
                for key in (["D"] if b["shape"]=="round" else ["W","H"]):b[key]=plan["proposed"][key]
            self._render_segmento();self.calcular()
        except ValueError as e:self.mostrar_error(e)
    def _rebalancear(self):
        try:
            self.guardar_campos();temp=copia(self.estado);temp["mode"]="design";self.estado["op"]["Kbal"]=self.motor.calcular(temp)["KbalDesign"];self.sincronizar();self.calcular()
        except ValueError as e:self.mostrar_error(e)
    def _fan_preset(self):
        try:
            self.guardar_campos();key=self.estado["fan"]["preset"]
            if key=="custom":return
            pts=catalogo("ductos")["fanPresets"][key]["points"];self.estado["fan"].update(points=[dict(Q=p[0]/3600,dP=p[1],eta=p[2]/100) for p in pts],pressureType="total",efficiencyType="total")
            self._armar_inputs();self.calcular()
        except ValueError as e:self._avisar_edicion(e)
    def _ajustar_velocidad(self):
        r=self.calcular()
        if r is None:return
        try:
            exigir(r["req"]["found"],"La curva no alcanza el punto de diseño.");s=r["req"]["s"];exigir(.2<=s<=1.1,"La frecuencia requerida queda fuera del intervalo de 20–110 % del ejemplo.")
            self.estado["fan"]["speed"]=s;self.sincronizar();self.calcular()
        except ValueError as e:self.mostrar_error(e)

    # --------------------------------------------------------- Dibujos nativos
    def dibujar(self):
        self.figura.clear();kind=self.memoria.modulo;r=self.resultado;accent=tema.SERIE_1
        if kind=="agitadores":
            from matplotlib.patches import Rectangle,Ellipse
            ax=self.figura.add_subplot(111);d=self.estado["inputs"];T,H,D=d["T"],d["H"],d["D"];Ht=d["Htk"];ax.set_aspect("equal");ax.axis("off")
            ax.add_patch(Rectangle((-T/2,0),T,min(H,Ht),facecolor="#dcecf0",edgecolor="none"));ax.plot([-T/2,-T/2,T/2,T/2],[Ht,0,0,Ht],color=accent,lw=2);ax.hlines(H,-T/2,T/2,linestyle="dashed",color="#5ba9be")
            if d["orient"]=="vertical":
                ax.plot([0,0],[d["C"],Ht+.4],color="#53616e",lw=4);ax.plot([-D/2,D/2],[d["C"]+.09,d["C"]-.09],color=accent,lw=4);ax.add_patch(Rectangle((-.3,Ht+.3),.6,.35,facecolor="#e5ecef",edgecolor=accent));ax.text(0,Ht+.75,"Motor / reductor",ha="center",fontsize=11)
                if d["nb"]>0:
                    for x in [-T/2,T/2-d["Wb"]]:ax.add_patch(Rectangle((x,.1),d["Wb"],max(.1,min(H,Ht)-.2),facecolor="#afcbd3",edgecolor="#829da8"))
            else:
                end=-T/2+d["Lsh"];ax.plot([-T/2-.5,end],[d["C"],d["C"]],color="#53616e",lw=4);ax.vlines(end,d["C"]-D/2,d["C"]+D/2,color=accent,lw=4);ax.text(-T/2-.55,d["C"]+.3,"Motor",ha="right",fontsize=11)
            ax.annotate("",xy=(-T/2,-.3),xytext=(T/2,-.3),arrowprops=dict(arrowstyle="<->",color=tema.TEXTO_2));ax.text(0,-.55,f"T = {T:g} m",ha="center",fontsize=11)
            ax.annotate("",xy=(T/2+.3,0),xytext=(T/2+.3,H),arrowprops=dict(arrowstyle="<->",color=tema.TEXTO_2));ax.text(T/2+.4,H/2,f"H = {H:g} m",rotation=90,va="center",fontsize=11)
            if "Dc" in r:ax.add_patch(Ellipse((0,d["C"]),min(r["Dc"],T),min(r["Hc"],Ht),facecolor="#91d0c2",alpha=.4,edgecolor=accent));ax.text(0,-.85,f"Caverna: Dc = {r['Dc']:.2f} m",ha="center",fontsize=11)
            ax.set_xlim(-T/2-1,T/2+1.2);ax.set_ylim(-1.2,Ht+1.1);ax.set_title("Esquema del equipo · dimensiones de diseño",loc="left",pad=16,fontsize=13)
        elif kind=="bombas":
            ax,ax2=self.figura.subplots(2,1,gridspec_kw={"height_ratios":[2,1]});import numpy as np
            qs=np.linspace(0,r["Qmax"],150);ax.plot(qs*3600,[r["hPump"](q) for q in qs],label="Bomba",color=accent,lw=2);ax.plot(qs*3600,[r["hSys"](q) for q in qs],label="Sistema",color=tema.SERIE_2,lw=2)
            if r["r"]:ax.plot(qs*3600,[r["r"]**2*r["can"]["A"]-r["r"]*r["can"]["B"]*q-r["can"]["C"]*q*q for q in qs],label="Afinidad",color=tema.SERIE_REFERENCIA,ls="--")
            points=self.estado["curves"]["hq"];ax.scatter([p["x"]*3600 for p in points],[p["y"] for p in points],color=accent,s=20)
            if r["Qop"]:ax.scatter([r["Qop"]*3600],[r["Hop"]],color=tema.MARINO,s=45,zorder=5);ax.annotate(f"Operación\n{r['Qop']*3600:.1f} m³/h · {r['Hop']:.1f} m",(r["Qop"]*3600,r["Hop"]),xytext=(10,12),textcoords="offset points",fontsize=10)
            ax.scatter([r["Qd"]*3600],[r["TDH"]],facecolor="white",edgecolor=accent,s=45,zorder=5);ax.set_ylabel("Altura (m)");ax.set_xlabel("Caudal (m³/h)");ax.set_ylim(bottom=0);ax.set_title("Curvas de bomba y sistema",loc="left");ax.legend(frameon=False,fontsize=9)
            ax2.plot(qs*3600,[r["npshAt"](q)["a"] for q in qs],label="NPSHa",color=accent);ax2.plot(qs*3600,[r["npshrAt"](q) for q in qs],label="NPSHr",color=tema.SERIE_2);ax2.set_ylabel("NPSH (m)");ax2.set_xlabel("Caudal (m³/h)");ax2.legend(frameon=False,fontsize=9)
            for a in [ax,ax2]:a.grid(alpha=.18);a.spines[["top","right"]].set_visible(False)
        else:
            import numpy as np
            ax,netax=self.figura.subplots(2,1,gridspec_kw={"height_ratios":[1.4,1]});fan=r["fan"];qmax=max(r["speed"]*fan.qMax,r["duty"]["Q"]*1.2)
            qs=np.linspace(0,qmax,65);sys=[];guess=None
            for q in qs:
                point=r["net"].at(float(q),guess);sys.append(point["dP"]);guess=point["split"]["Q"] if q>0 else None
            ax.plot(qs*3600,sys,color=tema.SERIE_2,label="Sistema");qf=np.linspace(fan.qMin*r["speed"],fan.qMax*r["speed"],100);ax.plot(qf*3600,[fan.at(q,r["speed"],r["air"]["rhoRatio"]) for q in qf],color=accent,label="Ventilador");ax.scatter([r["duty"]["Q"]*3600],[r["duty"]["dP"]],facecolor="white",edgecolor=accent,s=40,zorder=5)
            if r["op"]["found"]:op=r["op"];ax.scatter([op["Q"]*3600],[op["dP"]],color=tema.MARINO,s=40,zorder=5);ax.annotate(f"Operación\n{op['Q']*3600:,.0f} m³/h · {op['dP']:.0f} Pa",(op["Q"]*3600,op["dP"]),xytext=(9,10),textcoords="offset points",fontsize=9)
            ax.set_xlabel("Caudal (m³/h)");ax.set_ylabel("Presión total ΔPt (Pa)");ax.set_title("Ventilador y red",loc="left");ax.grid(alpha=.18);ax.spines[["top","right"]].set_visible(False);ax.legend(frameon=False,fontsize=9);ax.set_ylim(0,max(r["duty"]["dP"]*1.7,max(fan.at(q,r["speed"],r["air"]["rhoRatio"]) for q in qf)*1.2))
            st=self.estado;t=r["design"]["tree"];positions={};cursor=[0]
            def place(i,depth):
                kids=t["children"][i]
                for j in kids:place(j,depth+1)
                y=sum(positions[j][1] for j in kids)/len(kids) if kids else cursor[0]
                if not kids:cursor[0]+=1
                positions[i]=(depth,y)
            for i in t["roots"]:place(i,1)
            positions[-1]=(0,sum(positions[i][1] for i in t["roots"])/len(t["roots"]));critical=t["paths"][r["design"]["crit"]]
            for i,b in enumerate(st["branches"]):
                parent=-1 if b["parent"]=="main" else t["byId"][b["parent"]];a,z=positions[parent],positions[i]
                if st["systemKind"]!="supply":a,z=z,a
                netax.annotate("",xy=z,xytext=a,arrowprops=dict(arrowstyle="->",color=accent if i in critical else "#b7c2c9",lw=2))
            for i,(x,y) in positions.items():
                b=st["main"] if i==-1 else st["branches"][i];flow=r["Qtot"] if i==-1 else r["flows"][i]
                netax.text(x,y,b["name"]+f"\n{flow*3600:,.0f} m³/h",ha="center",va="center",fontsize=10 if len(st["branches"])<12 else 8,bbox=dict(boxstyle="round,pad=.5",fc="white",ec=accent if i==-1 or i in critical else "#d8e0e6"))
            netax.set_xlim(-.5,max(x for x,y in positions.values())+.6);netax.set_ylim(-.7,max(1,cursor[0])-.3);netax.axis("off");netax.set_title("Conexiones · trayecto crítico en verde",loc="left",fontsize=11)
        self.canvas.draw_idle()
