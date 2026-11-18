"""Memoria de agitadores: proceso y mecánica. Portado de la revisión A HTML.

No depende de Tkinter. Entradas y resultados en SI. Mantiene las correlaciones
de referencia y sus límites; la migración no les asigna una certificación nueva.
"""
from __future__ import annotations
import math
from .comun import G, catalogo, copia, exigir, validar_campos, siguiente, fila


def por_defecto():
    return {"inputs": copia(catalogo("agitadores")["inputs"])}


def shaft_eval(d, c):
    A=math.pi*d*d/4;I=math.pi*d**4/64
    w=0 if c["isV"] else A*(c["rhom"]-(c["rho"] if c["buo"] else 0))*G
    M=c["Fh"]*c["L"]+(0 if c["isV"] else c["mimp"]*G*c["L"]+w*c["L"]**2/2)
    teq=16/(math.pi*d**3)*math.hypot(c["Km"]*M,c["Kt"]*c["Tq"])
    ms=A*c["L"]*c["rhom"];k=3*c["E"]*I/c["L"]**3;meff=c["mimp"]+0.2357*ms
    Nc=60/(2*math.pi)*math.sqrt(k/meff)*c["kadd"]
    dh=c["Fh"]*c["L"]**3/(3*c["E"]*I)
    dw=0 if c["isV"] else w*c["L"]**4/(8*c["E"]*I)+c["mimp"]*G*c["L"]**3/(3*c["E"]*I)
    dt=dh+dw
    return dict(A=A,I=I,w=w,M=M,teq=teq,ms=ms,k=k,meff=meff,Nc=Nc,dh=dh,dw=dw,dt=dt,
                okS=teq<=c["tperm"],okD=dt<=c["dadm"],okN=c["Nrpm"]/Nc<=0.7)


def calcular(estado):
    d=validar_campos("agitadores",estado["inputs"]);cat=catalogo("agitadores");warnings=[]
    for key in ["T","H","Htk","D","rho","mu","N","Lsh","mimp","fs","eta","Km","Kt","ndef","kadd"]:
        exigir(d[key]>0,f"{key}: debe ser mayor que cero.")
    exigir(d["eta"]<=1,"La eficiencia del reductor debe ser ≤ 1.")
    exigir(d["imp"] in cat["impellers"] and d["mat"] in cat["materials"],"Impulsor o material desconocido.")
    isV=d["orient"]=="vertical";isF=d["fluido"]=="fibra";T,H,D,C=d["T"],d["H"],d["D"],d["C"]
    rho,mu,Nrpm=d["rho"],d["mu"],d["N"];Ns=Nrpm/60
    Vol=d["Vov"] if d["Vov"]>0 else math.pi/4*T*T*H
    Re=rho*Ns*D*D/mu;imp=cat["impellers"][d["imp"]]
    if d["manNp"]:
        Np,Nq=d["Np"],d["Nq"]
    else:
        Nq=imp["Nq"]
        x=(math.log10(Re)-1)/3
        Np=imp["Kp"]/Re if Re<10 else imp["NpT"] if Re>1e4 else 10**((1-x)*math.log10(imp["Kp"]/10)+x*math.log10(imp["NpT"]))
    exigir(Np>0 and Nq>0,"Np y Nq deben ser positivos.")
    P=Np*rho*Ns**3*D**5;PV=P/Vol;vtip=math.pi*D*Ns;Q=Nq*Ns*D**3
    Pd=P*d["fs"];Pmot=Pd/d["eta"]
    kwSel=siguiente(cat["IEC_KW"],Pmot/1000);hpSel=siguiente(cat["NEMA_HP"],Pmot/745.699872)
    exigir(kwSel is not None and hpSel is not None,"La potencia requerida excede la serie comercial del ejemplo. Amplía la selección de motor.")
    ired=float(d["nmot"])/Nrpm;mat=cat["materials"][d["mat"]]
    if d["mat"]!="mcust":
        d.update(Sy=mat["Sy"],Su=mat["Su"],Emod=mat["E"],rhom=mat["rho"])
    exigir(all(d[k]>0 for k in ["Sy","Su","Emod","rhom"]),"Las propiedades del material deben ser positivas.")
    Tq_d=9550*(Pd/1000)/Nrpm;Tq_m=9550*(kwSel*d["eta"])/Nrpm
    Tq=max(Tq_d,Tq_m) if d["chkMot"] else Tq_d;Fh=d["fh"]*2*Tq/D
    tperm=min(.3*d["Sy"],.18*d["Su"])*(.75 if d["chkKey"] else 1);dadm=d["Lsh"]/d["ndef"]
    ctx=dict(isV=isV,L=d["Lsh"],Fh=Fh,Tq=Tq,Km=d["Km"],Kt=d["Kt"],mimp=d["mimp"],rhom=d["rhom"],rho=rho,
             buo=not isV and d["chkBuo"],E=d["Emod"],kadd=d["kadd"],tperm=tperm,dadm=dadm,Nrpm=Nrpm)
    diameter=.05
    for _ in range(80):
        moment=shaft_eval(diameter,ctx)["M"]
        nxt=(16/(math.pi*tperm)*math.hypot(d["Km"]*moment,d["Kt"]*Tq))**(1/3)
        if abs(nxt-diameter)<1e-7: diameter=nxt;break
        diameter=(diameter+nxt)/2
    dreq=diameter;dcom=None
    for mm in cat["D_COM"]:
        dd=mm/1000
        if dd>=dreq:
            e=shaft_eval(dd,ctx)
            if e["okS"] and e["okD"] and e["okN"]: dcom=dd;break
    if dcom is None:
        dcom=cat["D_COM"][-1]/1000;warnings.append("Ningún diámetro de la serie satisface todos los criterios; se muestra el mayor disponible.")
    dad=dcom if d["autoD"] else d["dsel"];exigir(dad>0,"El diámetro adoptado debe ser positivo.")
    E1=shaft_eval(dad,ctx);FSs=tperm/E1["teq"] if E1["teq"] else math.inf
    sb=32*E1["M"]/(math.pi*dad**3);tt=16*Tq/(math.pi*dad**3)
    psel=rho*G*max(0,0 if isV else H-C)
    R=dict(Vol=Vol,Re=Re,Np=Np,Nq=Nq,P=P,PV=PV,vtip=vtip,Q=Q,turn=Q/Vol*60,ttur=Vol/Q,
           Pd=Pd,Pmot=Pmot,kwSel=kwSel,hpSel=hpSel,ired=ired,Tq=Tq,Fh=Fh,dreq=dreq,dcom=dcom,dad=dad,
           FSs=FSs,Ncf=E1["Nc"],Nc=E1["Nc"]/d["kadd"],ratN=Nrpm/E1["Nc"],dtot=E1["dt"],dadm=dadm,
           Tac=Tq*d["fac"],psel=psel,E1=E1,tperm=tperm,sb=sb,tt=tt,svm=math.sqrt(sb*sb+3*tt*tt),inputs=d)
    R["t95"]=None if isF else 5.2/(Ns*Np**(1/3))*(T/D)**2*math.sqrt(max(H/T,.001))
    if not isF and Re<=1e4: warnings.append("La correlación de tiempo de mezclado corresponde al régimen turbulento.")
    if H>d["Htk"]: warnings.append("El nivel de operación excede la altura del tanque.")
    if C>H: warnings.append("El impulsor no permanece sumergido al nivel capturado.")
    if isV and Re>50 and not isF and d["nb"]==0: warnings.append("Tanque vertical sin mamparas: posible formación de vórtice.")
    ranges=[("D/T",D/T,.30,.40),("C/T",C/T,.25,1),("H/T",H/T,.8,1.3),("Wb/T",d["Wb"]/T,.07,.10)] if isV else [("D/T",D/T,.15,.45),("C/T",C/T,.08,.4),("H/T",H/T,.3,2.5),("θh",d["thH"],5,15),("θv",d["thV"],0,15)]
    warnings.extend(f"Relación {k} fuera del rango de referencia ({lo:g}–{hi:g})." for k,v,lo,hi in ranges if not lo<=v<=hi)
    if d["chkSol"]:
        exigir(d["rhos"]>rho and d["dp"]>0 and d["Xs"]>=0 and d["Sz"]>0,"Zwietering requiere partículas más densas que el líquido y datos positivos.")
        Njs=d["Sz"]*(mu/rho)**.1*d["dp"]**.2*(G*(d["rhos"]-rho)/rho)**.45*d["Xs"]**.13/D**.85
        rhom=rho*(1+d["Xs"]/100)/(1+d["Xs"]/100*rho/d["rhos"])
        R.update(Njs=Njs,NjsR=Njs*60,Pjs=Np*rhom*Njs**3*D**5)
        if Ns<Njs: warnings.append("La velocidad de operación es menor que la de justo suspendido; se prevé sedimentación.")
    if isF:
        exigir(d["Cm"]>0 and d["ca"]>0 and d["alp"]>0,"El modelo de caverna requiere consistencia, coeficiente a y α positivos.")
        ty=d["ca"]*d["Cm"]**d["cb"];Rey=rho*Ns*Ns*D*D/ty
        DcWW=.3*math.sqrt(Np*Rey)*D;DcCI=D*(4*Np*Rey/(math.pi**2*d["alp"]))**(1/3)
        Dc=DcWW if d["cavMod"]=="ww" else DcCI;Hc=d["alp"]*Dc
        Nmin=math.sqrt((T/(.3*D))**2*ty/(Np*rho*D*D)) if d["cavMod"]=="ww" else math.sqrt((T/D)**3*math.pi**2*d["alp"]*ty/(4*Np*rho*D*D))
        R.update(ty=ty,Rey=Rey,DcWW=DcWW,DcCI=DcCI,Dc=Dc,Hc=Hc,NminR=Nmin*60,Pmin=Np*rho*Nmin**3*D**5)
        if Dc<T: warnings.append("La caverna activa no abarca el diámetro del tanque.")
        if Hc<H: warnings.append("La altura de la caverna no cubre todo el nivel de líquido.")
        warnings.append("La viscosidad de fase líquida no clasifica el mezclado global de la suspensión fibrosa.")
    for key,text in [("okS","esfuerzo combinado"),("okD","deflexión"),("okN","velocidad crítica")]:
        if not E1[key]: warnings.append("La flecha adoptada no cumple por "+text+".")
    if ired<1: warnings.append("Se requiere multiplicador de velocidad, no reductor.")
    if ired>60: warnings.append("La reducción supera 60:1; revisa la disposición de etapas.")
    R["warnings"]=warnings
    R["rows"]=[fila(k,l,R[k]*f,u,"E" if k in ["P","Q","t95","NjsR","Dc","Pmin"] else "V") for k,l,f,u in [
        ("Vol","Volumen de operación",1,"m³"),("Re","Reynolds del impulsor",1,""),("Np","Número de potencia",1,""),
        ("P","Potencia de proceso",.001,"kW"),("PV","Potencia específica",.001,"kW/m³"),("vtip","Velocidad periférica",1,"m/s"),
        ("Q","Caudal de bombeo",3600,"m³/h"),("turn","Recirculaciones",1,"1/min"),("t95","Tiempo de mezcla 95 %",1,"s"),
        ("Pd","Potencia de diseño",.001,"kW"),("Pmot","Potencia requerida al motor",.001,"kW"),("kwSel","Motor IEC seleccionado",1,"kW"),
        ("hpSel","Motor NEMA seleccionado",1,"HP"),("ired","Relación de reducción",1,":1"),("Tq","Torque de flecha",1,"N·m"),
        ("Fh","Carga radial",1,"N"),("dreq","Diámetro por esfuerzo",1000,"mm"),("dad","Diámetro adoptado",1000,"mm"),
        ("FSs","Factor de seguridad por esfuerzo",1,""),("Ncf","Velocidad crítica corregida",1,"rpm"),("ratN","Relación N/Nc",1,""),
        ("dtot","Deflexión total",1000,"mm"),("dadm","Deflexión admisible",1000,"mm"),("Tac","Torque del acoplamiento",1,"N·m"),
        ("psel","Presión hidrostática sobre sello",.001,"kPa"),("NjsR","Velocidad de justo suspendido",1,"rpm"),
        ("Pjs","Potencia a justo suspendido",.001,"kW"),("ty","Esfuerzo de cedencia",1,"Pa"),("Dc","Diámetro de caverna",1,"m"),
        ("Hc","Altura de caverna",1,"m"),("NminR","Velocidad mínima de cobertura",1,"rpm"),("Pmin","Potencia mínima de cobertura",.001,"kW")]
        if R.get(k) is not None]
    R["equations"]=["Re = ρND²/μ; P = NpρN³D⁵; Q = NqND³; N en rev/s.",
        "θ95 = 5.2/(N·Np^(1/3))·(T/D)²·(H/T)^0.5 (turbulento).",
        "Pd = fs·P; Pmotor = Pd/η; Tq = 9550·P[kW]/N[rpm].",
        "τeq = 16·√((KmM)²+(KtTq)²)/(πd³); τperm = min(0.30Sy,0.18Su), ×0.75 con cuñero.",
        "Nc = (60/2π)√((3EI/L³)/(mi+0.2357mflecha))·kfluido; N/Nc ≤ 0.7; δ ≤ L/ndef.",
        "Zwietering: Njs = Sν^0.1 dp^0.2 [g(ρs−ρ)/ρ]^0.45 X^0.13 / D^0.85.",
        "Fibra: τy=a·Cm^b; Rey=ρN²D²/τy; Dc/D=0.3√(NpRey) o [4NpRey/(π²α)]^(1/3)."]
    R["references"]=["Rushton et al. (1950); Perry, Chemical Engineers’ Handbook, sección 18: coeficientes de impulsores de referencia.",
        "Handbook of Industrial Mixing (Wiley, 2004): correlación de tiempo de mezclado turbulento.",
        "Zwietering (1958): velocidad de justo suspendido; S requiere confirmar geometría y partículas.",
        "Bennington, Kerekes y Grace (1990); Wichterle y Wein (1981); Solomon, Elson y Nienow (1981): esfuerzo de cedencia y caverna de suspensión fibrosa.",
        "ASME B106.1M-1985, referencia histórica de flechas, y Shigley: esfuerzos combinados. No se calcula fatiga ni análisis modal detallado.",
        "Series de motor IEC y NEMA y propiedades de material del ejemplo Rev_A; verificar selección comercial y certificados."]
    return R
