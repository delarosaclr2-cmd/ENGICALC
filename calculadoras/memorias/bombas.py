"""Motor nativo de bombas centrífugas: curvas, red, NPSH, BEP y afinidad."""
from __future__ import annotations
import math
import numpy as np
from .comun import G, catalogo, copia, exigir, validar_campos, raiz, fila


def por_defecto():
    c=catalogo("bombas")
    return {"inputs":copia(c["inputs"]),"curves":copia(c["curves"])}


def fit_poly(points):
    exigir(all(isinstance(p,dict) and math.isfinite(float(p["x"])) and math.isfinite(float(p["y"])) and float(p["x"])>=0 for p in points),"Los puntos de curva deben tener caudal no negativo y valores finitos.")
    if not points:return None
    deg=min(2,len(points)-1);xref=max(abs(p["x"]) for p in points) or 1
    x=np.array([p["x"]/xref for p in points]);y=np.array([p["y"] for p in points])
    A=np.vander(x,deg+1,increasing=True)
    c,_,rank,_=np.linalg.lstsq(A,y,rcond=None)
    exigir(rank==deg+1,"La curva contiene caudales repetidos o no permite ajustar el polinomio.")
    pred=A@c;sst=float(np.sum((y-y.mean())**2));r2=1-float(np.sum((y-pred)**2))/sst if sst>1e-12 else 1
    return dict(c=list(c)+[0.0]*(3-len(c)),xref=xref,r2=r2,n=len(points),deg=deg,xmin=min(p["x"] for p in points),xmax=max(p["x"] for p in points))


def poly_at(fit,x):
    if fit is None:return math.nan
    u=x/fit["xref"];a,b,c=fit["c"];return a+b*u+c*u*u


def calcular(estado):
    d=validar_campos("bombas",estado["inputs"]);curves=estado["curves"];warnings=[]
    for k in ["qd","ds","dd","cs","cd","rpm","dimp","eta","etaMot"]:exigir(d[k]>0,f"{k}: debe ser positivo.")
    for k in ["ls","ld","leqs","leqd","ks","kd","smargin","npshMin","npshRatio"]:exigir(d[k]>=0,f"{k}: no puede ser negativo.")
    exigir(0<d["eta"]<=100 and 0<d["etaMot"]<=100,"Las eficiencias deben estar entre 0 y 100 %.")
    T=d["temp"]
    exigir(-100<T<200,"Temperatura fuera del alcance de esta memoria.")
    if d["autoRho"]:d["rho"]=round(1000*(1-(T+288.9414)/(508929.2*(T+68.12963))*(T-3.9863)**2),1)
    if d["autoPv"]:d["pvap"]=round(.61121*math.exp((18.678-T/234.5)*(T/(257.14+T))),3)*1000
    if d["autoPatm"]:d["patm"]=round(101325*(1-2.25577e-5*max(-500,min(11000,d["alt"])))**5.25588/1000,3)*1000
    rho,pv,patm=d["rho"],d["pvap"],d["patm"];exigir(rho>0 and patm>0 and pv>=0,"Las propiedades del líquido y la presión absoluta no son válidas.")
    gamma=rho*G;Hs=d["zs"]-d["zb"];Hgeo=d["zd"]-d["zs"];Hpres=(d["pd"]-d["ps"])/gamma;Hst=Hgeo+Hpres
    def losses(Q):
        def line(s):
            diam,L,C,K,Leq=(d[k+s] for k in ["d","l","c","k","leq"])
            v=Q/(math.pi*diam*diam/4)
            hf=10.67*(L+Leq)*Q**1.852/(C**1.852*diam**4.87) if Q>0 else 0
            return hf,K*v*v/(2*G),v
        hfs,hms,Vs=line("s");hfd,hmd,Vd=line("d");hv=(Vd*Vd-Vs*Vs)/(2*G)
        return dict(hfs=hfs,hfd=hfd,hms=hms,hmd=hmd,Vs=Vs,Vd=Vd,hv=hv,suc=hfs+hms,dis=hfd+hmd,fric=hfs+hfd+hms+hmd,din=hfs+hfd+hms+hmd+hv)
    fitH,fitE,fitN=(fit_poly(curves.get(k,[])) for k in ["hq","eq","nq"])
    exigir(fitH is not None and fitH["n"]>=3,"Captura al menos tres puntos de altura Q–H del fabricante.")
    A=fitH["c"][0];B=-fitH["c"][1]/fitH["xref"];C=-fitH["c"][2]/fitH["xref"]**2
    exigir(A>0,"La curva ajustada tiene altura de cierre no positiva.")
    def hPump(Q):return A-B*Q-C*Q*Q
    def etaAt(Q):
        value=poly_at(fitE,Q) if d["useEtaCurve"] and fitE and fitE["n"]>=3 else math.nan
        return value if 1<value<=100 else d["eta"]
    def npshrAt(Q):
        value=poly_at(fitN,Q) if d["useNpshrCurve"] and fitN and fitN["n"]>=3 else math.nan
        return value if value>0 and math.isfinite(value) else d["npshr"]
    Qd=d["qd"];Ld=losses(Qd);TDH=Hst+Ld["din"];Kauto=Ld["din"]/Qd**2
    K=d["kval"] if d["manualK"] else Kauto;exigir(K>=0,"K de sistema no puede ser negativo.")
    def hSys(Q):return Hst+(losses(Q)["din"] if d["sysModel"]=="hw" else K*Q*Q)
    Qdata=max((p["x"] for p in curves["hq"]),default=Qd*1.6);Qmax=max(Qdata*1.25,Qd*1.3,1e-9)
    def solve(scale):
        if d["sysModel"]=="k":
            a,b,c=C+K,scale*B,Hst-scale*scale*A
            if abs(a)>1e-12 and b*b-4*a*c>=0:
                sq=math.sqrt(b*b-4*a*c);rs=[x for x in [(-b+sq)/(2*a),(-b-sq)/(2*a)] if x>1e-9]
                if rs:return min(rs)
            elif abs(a)<=1e-12 and abs(b)>1e-12 and -c/b>0:return -c/b
        return raiz(lambda Q:scale*scale*A-scale*B*Q-C*Q*Q-hSys(Q),1e-9,Qmax*(2.2 if d["sysModel"]=="hw" else 2.5),1200)
    Qop=solve(1);Hop=hPump(Qop) if Qop else None
    def npshAt(Q):
        hPress=(patm+d["ps"]-pv)/gamma;l=losses(Q);a=hPress+Hs-l["suc"];r=npshrAt(Q)
        return dict(hPress=hPress,hs=Hs,hfs=l["suc"],a=a,r=r,m=a-r,ratio=a/r if r>0 else None)
    def grade(p):
        if not p or p["r"]<=0:return "na"
        if p["m"]<=0:return "bad"
        return "ok" if p["m"]>=d["npshMin"] and p["ratio"]>=d["npshRatio"] else "warn"
    npD=npshAt(Qd);npOp=npshAt(Qop) if Qop else None
    Qb_eff=-fitE["c"][1]/(2*fitE["c"][2])*fitE["xref"] if fitE and fitE["n"]>=3 and fitE["c"][2]<0 else None
    if Qb_eff is not None and Qb_eff<=0:Qb_eff=None
    mode=d["bepMode"]
    if mode=="manual":Qb,Hb=d["bepQ"],d["bepH"]
    elif mode=="design":Qb,Hb=Qd,hPump(Qd)
    elif mode=="op":Qb,Hb=Qop,Hop
    else:Qb=Qb_eff or Qop or Qd;Hb=hPump(Qb)
    stages=max(1,round(d["stages"]));Hstage=Hb/stages if Hb else None
    nq=nsUS=wsAd=None
    if Qb and Hstage and Qb>0 and Hstage>0:
        nq=d["rpm"]*math.sqrt(Qb)/Hstage**.75;nsUS=d["rpm"]*math.sqrt(Qb/6.30901964e-5)/(Hstage/.3048)**.75
        wsAd=d["rpm"]*2*math.pi/60*math.sqrt(Qb)/(G*Hstage)**.75
    typ="—" if nsUS is None else "Radial de baja N" if nsUS<500 else "Radial" if nsUS<4000 else "Flujo mixto" if nsUS<9000 else "Axial"
    Phyd=gamma*Qd*TDH;etaD=etaAt(Qd);Pshaft=Phyd/(etaD/100)
    etaOp=etaAt(Qop) if Qop else None;PhydOp=gamma*Qop*Hop if Qop else None;PshaftOp=PhydOp/(etaOp/100) if Qop else None
    relBep=Qop/Qb_eff if Qop and Qb_eff else None
    r=None;Qop2=Hop2=etaOp2=PshaftOp2=None
    if d["affOn"]:
        r=d["rpm2"]/d["rpm"] if d["affVar"]=="N" else d["dimp2"]/d["dimp"]
        exigir(r>0,"La relación de afinidad debe ser positiva.")
        Qop2=solve(r)
        if Qop2:
            Hop2=r*r*A-r*B*Qop2-C*Qop2**2;etaOp2=etaAt(Qop2/r);PshaftOp2=gamma*Qop2*Hop2/(etaOp2/100)
        if d["affVar"]=="D" and r<.85:warnings.append("Recorte menor que 0.85 del diámetro original: verifica curvas específicas del fabricante.")
        if r>1.15:warnings.append("El escalado supera 1.15: verifica límites mecánicos, potencia y NPSH.")
    if pv>=patm:warnings.append("La presión de vapor supera la atmosférica; la aspiración abierta no es viable.")
    if not 0<=T<=100:warnings.append("Las correlaciones automáticas corresponden a agua entre 0 y 100 °C.")
    if fitH["r2"]<.985:warnings.append("El ajuste Q–H tiene R² menor que 0.985; revisa los puntos.")
    if fitH["n"]<4:warnings.append("Tres puntos no permiten verificar la calidad del ajuste; se recomiendan de 4 a 6.")
    if -B-2*C*fitH["xmax"]>0:warnings.append("La curva de bomba es creciente cerca del caudal máximo.")
    if Qop is None:warnings.append("No hay intersección positiva de las curvas de bomba y sistema.")
    elif Qop>fitH["xmax"]*1.02 or Qop<fitH["xmin"]*.98:warnings.append("El punto de operación extrapola el intervalo de datos del fabricante.")
    if Hop is not None and Hop<0:warnings.append("La intersección tiene altura negativa y no es una selección válida.")
    if grade(npD)=="bad" or grade(npOp)=="bad":warnings.append("Riesgo de cavitación: NPSHa ≤ NPSHr en diseño u operación.")
    elif grade(npD)=="warn" or grade(npOp)=="warn":warnings.append("No se cumplen ambos márgenes de NPSH: diferencia y relación mínima.")
    if relBep is not None and not .7<=relBep<=1.2:warnings.append("El punto de operación está fuera de 70–120 % del caudal BEP.")
    if Ld["Vs"]>2.1 or Ld["Vd"]>3.5:warnings.append("Velocidad elevada en succión o descarga; revisa diámetros y pérdidas.")
    if 0<Ld["Vs"]<.6:warnings.append("Velocidad baja en succión: revisa sedimentación si hay sólidos.")
    if d["ds"]<.05 or d["dd"]<.05:warnings.append("Hazen-Williams fuera del intervalo orientativo de diámetro ≥ 50 mm.")
    R=dict(T=T,rho=rho,pv=pv,patm=patm,gamma=gamma,Hs=Hs,Hgeo=Hgeo,Hpres=Hpres,Hst=Hst,fitH=fitH,fitE=fitE,fitN=fitN,can=dict(A=A,B=B,C=C),Qd=Qd,Ld_=Ld,TDH=TDH,
           etaD=etaD,Phyd=Phyd,Pshaft=Pshaft,Pmotor=Pshaft*(1+d["smargin"]/100),Pelec=Pshaft/(d["etaMot"]/100),Hbomba=hPump(Qd),Kauto=Kauto,K=K,Qmax=Qmax,
           Qop=Qop,Hop=Hop,etaOp=etaOp,PhydOp=PhydOp,PshaftOp=PshaftOp,Qbep_eff=Qb_eff,np=npD,npOp=npOp,gradeD=grade(npD),gradeOp=grade(npOp),
           Qbep=Qb,Hbep=Hb,Hstage=Hstage,nq=nq,nsUS=nsUS,wsAd=wsAd,tipo=typ,relBep=relBep,r=r,Qop2=Qop2,Hop2=Hop2,etaOp2=etaOp2,PshaftOp2=PshaftOp2,
           losses=losses,hPump=hPump,hSys=hSys,etaAt=etaAt,npshrAt=npshrAt,npshAt=npshAt,inputs=d,warnings=warnings)
    R["rows"]=[fila(k,l,R[k]*f,u) for k,l,f,u in [
        ("Hst","Altura estática",1,"m"),("TDH","Altura total a caudal de diseño",1,"m"),("Hbomba","Altura de bomba a caudal de diseño",1,"m"),
        ("Phyd","Potencia hidráulica de diseño",.001,"kW"),("Pshaft","Potencia al eje de diseño",.001,"kW"),("Pmotor","Potencia de motor con margen",.001,"kW"),
        ("Pelec","Potencia eléctrica estimada",.001,"kW"),("Qop","Caudal de operación",3600,"m³/h"),("Hop","Altura de operación",1,"m"),
        ("etaOp","Eficiencia de operación",1,"%"),("PshaftOp","Potencia al eje en operación",.001,"kW"),("Qbep","Caudal BEP adoptado",3600,"m³/h"),
        ("Hbep","Altura BEP adoptada",1,"m"),("nq","Velocidad específica métrica",1,""),("nsUS","Velocidad específica US",1,""),
        ("wsAd","Velocidad específica adimensional",1,""),("relBep","Q operación / Q BEP",100,"%"),("Qop2","Caudal con afinidad",3600,"m³/h"),
        ("Hop2","Altura con afinidad",1,"m"),("PshaftOp2","Potencia al eje con afinidad",.001,"kW")]
        if R.get(k) is not None]
    for name,values in [("Diseño",npD),("Operación",npOp)]:
        if values:
            R["rows"] += [fila(name+k,label+" · "+name,values[k],"m") for k,label in [("a","NPSH disponible"),("r","NPSH requerido"),("m","Margen NPSH")]]
    R["equations"]=["hf = 10.67·L·Q^1.852/(C^1.852·D^4.87); hm = ΣK·V²/(2g).",
        "Hest = zd−zs+(pd−ps)/(ρg); TDH = Hest + hf,s + hf,d + hm,s + hm,d + (Vd²−Vs²)/(2g).",
        "H(Q) = A−BQ−CQ², ajuste cuadrático por mínimos cuadrados sobre caudal normalizado.",
        "Sistema exacto Hazen-Williams o Hsistema=Hest+KQ², K anclado en Qd o capturado.",
        "NPSHa=(patm+ps−pv)/(ρg)+(zs−zb)−pérdidas de succión; margen=NPSHa−NPSHr.",
        "Peje=ρgQH/ηbomba; Pmotor=Peje(1+margen); Peléctrica=Peje/ηmotor.",
        "Afinidad: H2(Q)=r²A−rBQ−CQ², η2(Q)=η1(Q/r); nq=N√Q/H_etapa^0.75."]
    R["references"]=["Correlaciones de Kell (densidad del agua), Buck (1981, presión de vapor) y atmósfera estándar, según la memoria HTML Rev_A.",
        "Hazen-Williams para agua; coeficientes C y ΣK capturados por el usuario. No sustituye la verificación por Darcy para fluidos viscosos.",
        "Curvas Q–H, eficiencia y NPSHr: datos del fabricante. Los puntos iniciales constituyen un ejemplo.",
        "Criterios editables de margen NPSH y ventana 70–120 % del BEP conservados del ejemplo; confirmar con el proveedor y los criterios del proyecto."]
    return R
