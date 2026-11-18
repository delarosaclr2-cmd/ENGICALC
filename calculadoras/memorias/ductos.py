"""Red HVAC nativa: árbol, balanceo, ventilador PCHIP, presión AMCA y secciones.

Portado del motor v4. No ejecuta JavaScript. Magnitudes internas SI.
"""
from __future__ import annotations
import math
from .comun import catalogo,copia,exigir,numero,pchip,fila


def por_defecto():return copia(catalogo("ductos")["state"])


def tree_meta(branches):
    exigir(isinstance(branches,list) and 1<=len(branches)<=40,"La red admite de 1 a 40 tramos además del principal.")
    byId={};children=[[] for b in branches];roots=[];order=[];active=set();seen=set()
    for i,b in enumerate(branches):
        exigir(b.get("id") and b["id"]!="main" and b["id"] not in byId,"Identificadores duplicados o no válidos.");byId[b["id"]]=i
    for i,b in enumerate(branches):
        parent=b.get("parent","main")
        if parent=="main":roots.append(i)
        else:exigir(parent in byId,"Conexión sin tramo padre.");children[byId[parent]].append(i)
    def visit(i):
        exigir(i not in active,"La red contiene una conexión circular.")
        if i in seen:return
        active.add(i)
        for j in children[i]:visit(j)
        active.remove(i);seen.add(i);order.append(i)
    for i in range(len(branches)):visit(i)
    paths=[]
    for i,b in enumerate(branches):
        path=[i];p=b.get("parent","main")
        while p!="main":i=byId[p];path.insert(0,i);p=branches[i].get("parent","main")
        paths.append(path)
    return dict(byId=byId,children=children,roots=roots,order=order,paths=paths,leaves=[i for i in order if not children[i]],flat=len(roots)==len(branches))


def design_flows(branches,t=None):
    t=t or tree_meta(branches);q=[b["Qd"] for b in branches]
    for i in t["order"]:
        if t["children"][i]:q[i]=sum(q[j] for j in t["children"][i])
        exigir(q[i]>0,"El caudal terminal debe ser mayor que cero.")
    return q


def geometria(seg):
    if seg["shape"]=="rect":
        W,H=seg["W"],seg["H"];A=W*H;P=2*(W+H)
        return dict(A=A,P=P,Dh=4*A/P,De=1.30*(W*H)**.625/(W+H)**.25)
    D=seg["D"];return dict(A=math.pi*D*D/4,P=math.pi*D,Dh=D,De=D)


def factor_friccion(Re,rr,method="colebrook"):
    def turbulent(re):
        f=.25/math.log10(rr/3.7+5.74/re**.9)**2
        if method=="swamee":return f
        x=1/math.sqrt(f)
        for _ in range(60):
            a=rr/3.7+2.51*x/re;g=x+2*math.log10(a);dg=1+2*(2.51/re)/(math.log(10)*a);dx=g/dg;x-=dx
            if abs(dx)<=1e-14*abs(x):break
        return 1/(x*x)
    if Re<=0:return 0,"none"
    if Re<2300:return 64/Re,"laminar"
    if Re>4000:return turbulent(Re),"turbulent"
    fl,ft=64/2300,turbulent(4000)
    return fl+(Re-2300)/1700*(ft-fl),"transition"


def segment_loss(seg,Q,air,method="colebrook",Kextra=0):
    g=geometria(seg);V=Q/g["A"];Re=air["rho"]*abs(V)*g["Dh"]/air["mu"];rr=seg["eps"]/g["Dh"]
    f,regime=factor_friccion(Re,rr,method);Pv=.5*air["rho"]*V*V;dPf=f*seg["L"]/g["Dh"]*Pv
    Kfit=sum(f["qty"]*f["K"] for f in seg.get("fittings",[]));dPm=Kfit*Pv;dPx=Kextra*Pv
    return dict(Q=Q,A=g["A"],Dh=g["Dh"],De=g["De"],V=V,Re=Re,rr=rr,f=f,regime=regime,Pv=Pv,dPf=dPf,Kfit=Kfit,dPm=dPm,Kextra=Kextra,dPx=dPx,dP=dPf+dPm+dPx)


def build_air(st):
    a=st["air"];T=a["T"]+273.15;p=101325*max(1-2.25577e-5*a["alt"],.01)**5.25588
    rho=a["rhoManual"] if a["source"]=="manual" else p/(287.055*T)
    return dict(rho=rho,mu=1.716e-5*(T/273.15)**1.5*(273.15+110.4)/(T+110.4),rhoRatio=rho/a["rhoCat"],patm=p)


def ahu_loss(st,Q,air):
    items=[];total=0
    for c in st["ahu"]["comps"]:
        dp=0
        if c["enabled"] and Q>0:
            base=c["states"][c["state"]] if "states" in c else c["dp"]
            dp=base*(Q/st["ahu"]["Qnom"])**c["n"]*(air["rhoRatio"]**(c["n"]-1) if st["air"]["correctComponents"] else 1)
        items.append(dict(id=c["id"],dP=dp));total+=dp
    return dict(total=total,items=items)


def parallel_k(values):return 1/sum(1/math.sqrt(max(v,1e-30)) for v in values)**2


def damper_extra_k(angulo):
    theta=numero(angulo,"Ángulo de cierre",minimo=0,maximo=75);tabla=catalogo("ductos")["damperTable"]
    for (a,k0),(b,k1) in zip(tabla,tabla[1:]):
        if theta<=b:return math.exp(math.log(k0)+(theta-a)/(b-a)*(math.log(k1)-math.log(k0)))-tabla[0][1]
    return tabla[-1][1]-tabla[0][1]


def damper_angle(Kextra):
    tabla=catalogo("ductos")["damperTable"];K=numero(Kextra,"K adicional",minimo=0)+tabla[0][1]
    if K<=tabla[0][1]:return 0
    for (a,k0),(b,k1) in zip(tabla,tabla[1:]):
        if K<=k1:return a+(math.log(K)-math.log(k0))/(math.log(k1)-math.log(k0))*(b-a)
    return tabla[-1][0]


class Red:
    def __init__(self,st,air,Kbal):
        self.st=st;self.air=air;self.Kbal=Kbal;self.tree=tree_meta(st["branches"])
        self.qd=design_flows(st["branches"],self.tree)
    def branch(self,i,Q):return segment_loss(self.st["branches"][i],Q,self.air,self.st["method"],self.Kbal[i])
    def split(self,Qtot,guess=None):
        t=self.tree;n=len(self.qd);q=(guess or self.qd).copy();total=sum(q[i] for i in t["roots"])
        q=[v/total*Qtot if Qtot>0 else 0 for v in q]
        def evaluate():
            br=[self.branch(i,v) for i,v in enumerate(q)];paths=[sum(br[j]["dP"] for j in t["paths"][i]) for i in t["leaves"]]
            Pn=sum(paths)/len(paths);residual=(max(paths)-min(paths))/Pn if Pn>0 else 0
            return br,paths,Pn,residual
        it=0
        if Qtot>0:
            for it in range(180):
                br,paths,Pn,residual=evaluate()
                if residual<2e-11:break
                C=[0]*n
                for i in t["order"]:
                    C[i]=br[i]["dP"]/(q[i]*q[i])
                    if t["children"][i]:C[i]+=parallel_k([C[j] for j in t["children"][i]])
                    C[i]=max(C[i],1e-18)
                nxt=[0]*n
                def distribute(nodes,Q):
                    weights=[1/math.sqrt(C[i]) for i in nodes];sw=sum(weights)
                    for k,i in enumerate(nodes):
                        nxt[i]=Q*weights[k]/sw
                        if t["children"][i]:distribute(t["children"][i],nxt[i])
                distribute(t["roots"],Qtot);q=[.25*v+.75*nxt[i] for i,v in enumerate(q)]
        br,paths,Pn,residual=evaluate();exigir(residual<=1e-8,"El reparto de caudales no converge; revisa las resistencias de la red.")
        return dict(Q=q,Pn=Pn,br=br,paths=paths,residual=residual,iters=it)
    def at(self,Q,guess=None):
        a=ahu_loss(self.st,Q,self.air);m=segment_loss(self.st["main"],Q,self.air,self.st["method"]);sp=self.split(Q,guess)
        return dict(Q=Q,dP=a["total"]+m["dP"]+sp["Pn"],ahu=a,main=m,split=sp,Pn=sp["Pn"])


def design_analysis(st,air):
    t=tree_meta(st["branches"]);q=design_flows(st["branches"],t);Qt=sum(q[i] for i in t["roots"])
    ahu=ahu_loss(st,Qt,air);main=segment_loss(st["main"],Qt,air,st["method"])
    br=[segment_loss(b,q[i],air,st["method"]) for i,b in enumerate(st["branches"])]
    path=[ahu["total"]+main["dP"]+sum(br[j]["dP"] for j in t["paths"][i]) for i in range(len(q))]
    crit=max(t["leaves"],key=lambda i:path[i]);bal=[]
    for i,b in enumerate(br):
        dp=0 if t["children"][i] else max(0,path[crit]-path[i]);bal.append(dict(dP=dp,K=dp/b["Pv"] if b["Pv"]>0 else 0))
    return dict(Qd=q,Qtot=Qt,ahu=ahu,main=main,br=br,path=path,crit=crit,bal=bal,dPreq=path[crit],Pn=path[crit]-ahu["total"]-main["dP"],tree=t)


class Ventilador:
    def __init__(self,st):
        self.st=st;fan=st["fan"];self.points=sorted(fan["points"],key=lambda p:p["Q"])
        exigir(len(self.points)>=3,"La curva de ventilador necesita al menos tres puntos.")
        for p in self.points:
            for k in ["Q","dP","eta"]:numero(p[k],"Curva "+k,minimo=0)
            exigir(p["eta"]<=1,"La eficiencia de ventilador debe estar entre 0 y 100 %.")
        xs=[p["Q"] for p in self.points];self.qMin,self.qMax=xs[0],xs[-1]
        self.rawdp=pchip(xs,[p["dP"] for p in self.points]);self.raweta=pchip(xs,[p["eta"] for p in self.points])
        peak={"Q":self.qMin,"dP":self.dp0(self.qMin)};bep={"Q":self.qMin,"eta":self.eta0(self.qMin)}
        for i in range(801):
            Q=self.qMin+(self.qMax-self.qMin)*i/800;p=self.dp0(Q);e=self.eta0(Q)
            if fan["efficiencyType"]=="static" and self.raweta(Q)>0 and Q>0:
                exigir(p-self.pv(Q)>0 and e<=1+1e-9,"La eficiencia estática y el área de descarga implican una eficiencia total mayor que 100 %.")
            if p>peak["dP"]:peak=dict(Q=Q,dP=p)
            if e>bep["eta"]:bep=dict(Q=Q,eta=e)
        self.peak,self.bep=peak,bep
    def pv(self,Q):return .5*self.st["air"]["rhoCat"]*(Q/self.st["fan"]["outletArea"])**2
    def dp0(self,Q):return self.rawdp(Q)+(self.pv(Q) if self.st["fan"]["pressureType"]=="static" else 0)
    def eta0(self,Q):
        pt=self.dp0(Q);basis=pt-self.pv(Q) if self.st["fan"]["efficiencyType"]=="static" else pt
        return self.raweta(Q)*pt/basis if pt>0 and basis>0 else 0
    def at(self,Q,s,rr):return s*s*rr*self.dp0(Q/s)
    def efficiency(self,Q,s):return self.eta0(Q/s)
    def power(self,Q,s,rr):
        e=self.efficiency(Q,s);return Q*self.at(Q,s,rr)/e if e>1e-6 else None


def operating_point(net,fan,s,rr):
    qlo=max(s*fan.qMin,s*fan.qMax*1e-7);qhi=s*fan.qMax;cross=[];guess=None;prevQ=prevF=0;first=last=0
    for k in range(121):
        Q=qlo+(qhi-qlo)*k/120;sys=net.at(Q,guess);guess=sys["split"]["Q"];F=fan.at(Q,s,rr)-sys["dP"]
        if k==0:first=F
        if k>0 and ((prevF>0 and F<=0) or (prevF<0 and F>=0)):cross.append((prevQ,Q,prevF,guess))
        prevQ,prevF,last=Q,F,F
    if not cross:return dict(found=False,crossings=0,reason="beyond-max" if last>0 else "below-min" if first<0 else "none")
    stable=[c for c in cross if c[2]>0];a,b,fa,guess=(stable or cross)[-1]
    for _ in range(200):
        mid=(a+b)/2;fm=fan.at(mid,s,rr)-net.at(mid,guess)["dP"]
        if (fm>0)==(fa>0):a,fa=mid,fm
        else:b=mid
        if b-a<=1e-14*b:break
    Q=(a+b)/2;sys=net.at(Q,guess);dp=fan.at(Q,s,rr)
    return dict(found=True,crossings=len(cross),Q=Q,dP=dp,dPsys=sys["dP"],mismatch=abs(dp-sys["dP"]),eta=fan.efficiency(Q,s),
                power=fan.power(Q,s,rr),airPower=Q*dp,sys=sys,u=Q/s)


def required_speed(fan,rr,Q,dp):
    if Q<=0 or dp<=0:return dict(found=False)
    lo=Q/fan.qMax*(1+1e-12);hi=Q/fan.qMin*(1-1e-12) if fan.qMin>0 else max(4*lo,20)
    phi=lambda s:s*s*rr*fan.dp0(Q/s)-dp
    if not phi(lo)<0 or not phi(hi)>0:return dict(found=False)
    for _ in range(200):
        mid=(lo+hi)/2
        if phi(mid)<0:lo=mid
        else:hi=mid
        if hi-lo<=1e-14*hi:break
    s=(lo+hi)/2;u=Q/s;e=fan.eta0(u)
    return dict(found=True,s=s,u=u,eta=e,power=Q*dp/e if e>1e-6 else None)


def pressure_parts(Q,total,rho,area):
    velocity=.5*rho*(Q/area)**2
    return dict(total=total,static=total-velocity,velocity=velocity)


def validar(st):
    exigir(st.get("mode") in ["design","operation"],"Modo de cálculo no válido.")
    t=tree_meta(st["branches"]);names=[]
    for seg in [st["main"]]+st["branches"]:
        name=seg.get("name","").strip();exigir(name and name.lower() not in names,"Usa un TAG único para cada tramo.");names.append(name.lower())
        exigir(seg["shape"] in ["round","rect"],"Sección de tramo no válida.")
        for k in ["D","W","H"]:numero(seg[k],name+" "+k,minimo=.02,maximo=5)
        numero(seg["L"],name+" longitud",minimo=0,maximo=2000);numero(seg["eps"],name+" rugosidad",minimo=0,maximo=.01)
        for f in seg["fittings"]:numero(f["K"],"K de accesorio",minimo=0,maximo=100000);numero(f["qty"],"Cantidad",minimo=0,maximo=50)
    for i in t["leaves"]:
        b=st["branches"][i];numero(b["Qd"],"Caudal terminal",positivo=True,maximo=200)
        exigir(b["L"]>0 or sum(f["qty"]*f["K"] for f in b["fittings"])>0,"Cada terminal necesita longitud o algún accesorio.")
    a=st["air"];numero(a["T"],"Temperatura",minimo=-40,maximo=80);numero(a["alt"],"Altitud",minimo=-400,maximo=6000)
    for k in ["rhoManual","rhoCat"]:numero(a[k],"Densidad",minimo=.3,maximo=2)
    numero(st["fan"]["outletArea"],"Área de descarga",minimo=.001,maximo=25)
    numero(st["fan"]["speed"],"Relación de velocidad",minimo=.2,maximo=1.1)
    numero(st["fan"]["f0"],"Frecuencia nominal",positivo=True);numero(st["fan"]["n0"],"rpm nominal",positivo=True)
    numero(st["ahu"]["Qnom"],"Caudal nominal AHU",positivo=True)
    for c in st["ahu"]["comps"]:
        numero(c["n"],"Exponente AHU",minimo=.5,maximo=3)
        for v in (c["states"].values() if "states" in c else [c["dp"]]):numero(v,"Pérdida AHU",minimo=0,maximo=20000)
    exigir(st["method"] in ["colebrook","swamee"],"Método de fricción no válido.")
    exigir(st["fan"]["pressureType"] in ["total","static"] and st["fan"]["efficiencyType"] in ["total","static"],"Base de catálogo no válida.")
    exigir(len(st["op"]["Kbal"])==len(st["branches"]),"Lista de dampers no consistente con los tramos.")
    for k in st["op"]["Kbal"]:numero(k,"K adicional de balanceo",minimo=0,maximo=100000)
    for k in ["vMain","vBranch"]:numero(st["thresholds"][k],"Umbral de velocidad",positivo=True)
    for k in ["minFlow","pMargin"]:numero(st["thresholds"][k],"Criterio de diseño",minimo=0,maximo=1)
    return t


def calcular(estado):
    st=copia(estado);t=validar(st);air=build_air(st);d=design_analysis(st,air)
    Kdesign=[b["K"] for b in d["bal"]];Kbal=Kdesign if st["mode"]=="design" else st["op"]["Kbal"]
    net=Red(st,air,Kbal);fan=Ventilador(st);speed=st["fan"]["speed"]
    atDesign=net.at(d["Qtot"]);duty=dict(Q=d["Qtot"],dP=atDesign["dP"]);duty["pressures"]=pressure_parts(duty["Q"],duty["dP"],air["rho"],st["fan"]["outletArea"])
    op=operating_point(net,fan,speed,air["rhoRatio"]);req=required_speed(fan,air["rhoRatio"],duty["Q"],duty["dP"])
    if op["found"]:
        op["pressures"]=pressure_parts(op["Q"],op["dP"],air["rho"],st["fan"]["outletArea"])
        op["stall"]=op["u"]<fan.peak["Q"]*(1-1e-9);op["bepRatio"]=op["u"]/fan.bep["Q"] if fan.bep["Q"]>0 else None
    if st["mode"]=="design":
        flows=d["Qd"];Qt=d["Qtot"];main=d["main"];br=[net.branch(i,q) for i,q in enumerate(flows)];ahu=d["ahu"];Pn=d["Pn"];shown=True
    elif op["found"]:
        sys=op["sys"];flows=sys["split"]["Q"];Qt=op["Q"];main=sys["main"];br=sys["split"]["br"];ahu=sys["ahu"];Pn=sys["Pn"];shown=True
    else:
        flows=[0]*len(st["branches"]);Qt=0;main=segment_loss(st["main"],0,air,st["method"]);br=[net.branch(i,0) for i in range(len(flows))];ahu=ahu_loss(st,0,air);Pn=0;shown=False
    warnings=[];th=st["thresholds"]
    for b,r,limit in [(st["main"],main,th["vMain"])]+[(b,br[i],th["vBranch"]) for i,b in enumerate(st["branches"])]:
        if r["V"]>limit:warnings.append("Velocidad superior al umbral en "+b["name"]+".")
    if not op["found"]:warnings.append("No hay punto de operación dentro de la curva del ventilador.")
    else:
        if op["stall"]:warnings.append("La operación queda a la izquierda del máximo de presión de la curva.")
        if op["crossings"]>1:warnings.append("Hay múltiples cruces; se adopta el estable de mayor caudal.")
        if op["Q"]<th["minFlow"]*d["Qtot"]:warnings.append("El caudal total de operación es inferior al mínimo de diseño.")
        if st["mode"]=="operation":
            for i in t["leaves"]:
                if flows[i]<th["minFlow"]*d["Qd"][i]:warnings.append("Caudal insuficiente en "+st["branches"][i]["name"]+".")
    pqd=fan.at(duty["Q"],speed,air["rhoRatio"])
    if math.isfinite(pqd) and pqd<duty["dP"]*(1+th["pMargin"])*.998:warnings.append("Presión insuficiente a caudal de diseño.")
    if duty["pressures"]["static"]<0:warnings.append("Presión estática requerida negativa: revisa el área de descarga y la instalación.")
    R=dict(air=air,mode=st["mode"],design=d,KbalDesign=Kdesign,Kbal=Kbal,net=net,fan=fan,speed=speed,hz=speed*st["fan"]["f0"],rpm=speed*st["fan"]["n0"],
           sysAtDesign=atDesign,duty=duty,op=op,req=req,flows=flows,Qtot=Qt,segMain=main,segBr=br,ahu=ahu,Pn=Pn,shown=shown,warnings=warnings)
    rows=[fila("Qdesign","Caudal de diseño",d["Qtot"]*3600,"m³/h"),fila("Pdesign","Presión total requerida",duty["dP"],"Pa"),
          fila("critical","Terminal del trayecto crítico",st["branches"][d["crit"]]["name"]),fila("speed","Frecuencia requerida",req["s"]*st["fan"]["f0"] if req["found"] else None,"Hz")]
    for title,pres in [("Diseño",duty["pressures"]),("Operación",op.get("pressures"))]:
        if pres:
            rows.extend(fila(title+k,title+" · "+label,pres[k],"Pa") for k,label in [("total","Presión total ΔPt"),("static","Presión estática AMCA ΔPs"),("velocity","Presión dinámica de descarga Pv")])
    if op["found"]:rows.extend([fila("Qop","Caudal de operación",op["Q"]*3600,"m³/h"),fila("power","Potencia en el eje",op["power"]/1000 if op["power"] else None,"kW"),fila("efficiency","Eficiencia total en operación",op["eta"]*100,"%")])
    for i,(b,r) in enumerate(zip([st["main"]]+st["branches"],[main]+br)):
        for key,label,factor,unit in [("Q","Caudal",3600,"m³/h"),("V","Velocidad",1,"m/s"),("dP","Pérdida total",1,"Pa"),("dPf","Pérdida recta",1,"Pa"),("dPm","Pérdida de accesorios",1,"Pa"),("dPx","Pérdida de balanceo",1,"Pa"),("Re","Reynolds",1,""),("f","Factor Darcy",1,"")]:
            rows.append(fila(f"s{i}_{key}",b["name"]+" · "+label,r[key]*factor,unit))
    for i,b in enumerate(st["branches"]):
        rows.extend([fila(f"Kbal{i}",b["name"]+" · K adicional de balanceo",Kbal[i]),fila(f"angle{i}",b["name"]+" · Ángulo orientativo",damper_angle(Kbal[i]),"°")])
    R["rows"]=rows;R["equations"]=["Q de tramo común = ΣQ terminales de su subárbol; se conserva caudal en cada nodo.",
        "ΔPt,tramo = [f(L/Dh)+ΣK+Kbalanceo]·ρV²/2; Dh=4A/P; Re=ρVDh/μ.",
        "Colebrook o Swamee-Jain; f=64/Re en laminar; transición lineal entre Re=2300 y 4000.",
        "El mayor trayecto AHU+principal+tramos conectados fija la presión requerida. El balanceo se agrega solo en terminales.",
        "ΔPs,AMCA=ΔPt−ρ(Q/A_descarga)²/2; no es el salto de presión estática entre las bocas del ventilador.",
        "P=eje=QΔPt/ηt=QΔPs/ηs. Curvas PCHIP sin extrapolación y afinidad con corrección por densidad.",
        "Red en árbol; sin mallas, fugas ni múltiples ventiladores. Terminales a igual presión de referencia. K a revisar según geometría y sentido de flujo."]
    R["references"]=["AMCA, Straightening Out Fan Curves: https://www.amca.org/educate/articles-and-technical-papers/amca-inmotion-articles/straightening-out-fan-curves.html",
        "ASHRAE Handbook, Duct Design y Fans: bases de presión total, estática y dinámica; métodos de dimensionamiento.",
        "La serie circular inicial y los incrementos rectangulares son editables y deben ajustarse al proveedor."]
    used={f["type"] for b in [st["main"]]+st["branches"] for f in b["fittings"]}
    for key in sorted(used):
        ref=catalogo("ductos")["fittings"].get(key)
        if ref:R["references"].append(ref["name"]+" · K inicial "+str(ref["K"])+" · "+ref["src"]+" ("+ref["status"]+")")
    return R


def size_segment(seg,Q,air,method,cfg):
    ratio=numero(cfg["aspect"],"W/H",minimo=1,maximo=4);target=numero(cfg["velocity"] if cfg["criterion"]=="velocity" else cfg["friction"],"Objetivo",positivo=True)
    exigir(Q>0,"Caudal de dimensionamiento no positivo.")
    def geom(x):return dict(seg,D=x) if seg["shape"]=="round" else dict(seg,H=x,W=ratio*x)
    def rate(b):return segment_loss(dict(b,L=1,fittings=[]),Q,air,method)
    def val(x):r=rate(geom(x));return r["V"] if cfg["criterion"]=="velocity" else r["dPf"]
    lo,hi=.005,5
    exigir(val(hi)<=target,"El objetivo requiere dimensiones mayores que 5 m.")
    for _ in range(75):
        mid=(lo+hi)/2
        if val(mid)>target:lo=mid
        else:hi=mid
    ideal=geom(hi);proposed=copia(ideal)
    if seg["shape"]=="round":
        import re
        series=[numero(x,"Diámetro disponible",minimo=20,maximo=5000) for x in re.split(r"[,;\s]+",cfg["roundSeries"].strip()) if x]
        choices=sorted(x for x in series if x/1000>=ideal["D"]*(1-1e-10));exigir(choices,"La serie no contiene un diámetro suficiente; amplíala.");proposed["D"]=choices[0]/1000
    else:
        step=numero(cfg["rectStep"],"Incremento rectangular",minimo=.005,maximo=.2)
        proposed.update(W=math.ceil(ideal["W"]/step-1e-10)*step,H=math.ceil(ideal["H"]/step-1e-10)*step)
        exigir(max(proposed["W"],proposed["H"])<=5,"La propuesta supera 5 m.")
    return dict(ideal=ideal,proposed=proposed,result=rate(proposed),current=rate(seg),Q=Q)
