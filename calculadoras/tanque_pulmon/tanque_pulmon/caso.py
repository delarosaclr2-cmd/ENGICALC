"""Caso de cálculo en unidades de usuario (lo que captura la interfaz o el archivo JSON).

Convierte a Entradas/Criterios en SI y guarda/carga archivos .json con trazabilidad.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from . import unidades as u
from .constantes import diametro_interior_m
from .criterios import Criterios
from .motor import Entradas, Tramo

_DIF_PRESION = {"kPa": 1_000.0, "psi": u.PSI, "bar": u.BAR}


@dataclass
class Magnitud:
    valor: float
    unidad: str
    referencia: Optional[str] = None   # solo caudales


@dataclass
class TramoUsuario:
    descripcion: str
    longitud_m: float
    nps: Optional[str] = None
    cedula: Optional[str] = None
    d_interior_mm: Optional[float] = None
    espesor: Optional[dict] = None          # datos de material de ESTE tramo (anula el del caso)

    def d_interior_m(self) -> float:
        if self.d_interior_mm is not None:
            return self.d_interior_mm / 1000.0
        if self.nps and self.cedula:
            return diametro_interior_m(self.nps, self.cedula)
        raise ValueError(f"Tramo '{self.descripcion}': indique NPS y cédula, o el diámetro interior")


@dataclass
class CasoUsuario:
    nombre: str
    v_tanque: Magnitud
    p_superior: Magnitud
    p_inferior: Magnitud
    t_aire: Magnitud
    q_consumo: Magnitud
    p_atm_sitio: Magnitud = field(default_factory=lambda: Magnitud(14.696, "psia"))
    documento: str = ""
    margen_consumo_pct: float = 0.0
    q_compresor: Optional[Magnitud] = None
    tramos: List[TramoUsuario] = field(default_factory=list)
    incluir_tuberia: bool = True
    n_politropico: float = 1.0
    t_retencion_req_min: Optional[float] = None
    fraccion_carga_max_pct: Optional[float] = None
    ciclos_h_max: Optional[float] = None
    p_min_consumidor: Optional[Magnitud] = None
    dp_linea: Optional[Magnitud] = None
    p_calibracion_psv: Optional[Magnitud] = None
    p_diseno: Optional[Magnitud] = None
    t_diseno_c: Optional[float] = None
    espesor: Optional[dict] = None          # material de la tubería conectada: S, c, tolerancia, Barlow
    notas: str = ""

    # ------------------------------------------------------------------ conversión
    def _p(self, m: Magnitud, patm: float) -> float:
        return u.presion_a_pa_abs(m.valor, m.unidad, patm)

    def p_atm_pa(self) -> float:
        if self.p_atm_sitio.unidad not in ("Pa a", "kPa a", "bar a", "psia", "kgf/cm² a"):
            raise ValueError("La presión atmosférica del sitio debe darse en unidades absolutas")
        return u.presion_a_pa_abs(self.p_atm_sitio.valor, self.p_atm_sitio.unidad, 0.0)

    def a_entradas(self) -> Entradas:
        patm = self.p_atm_pa()
        qc = None
        refc = "normal"
        if self.q_compresor is not None:
            qc = u.caudal_a_m3s(self.q_compresor.valor, self.q_compresor.unidad)
            refc = self.q_compresor.referencia or "normal"
        return Entradas(
            nombre_caso=self.nombre,
            v_tanque_m3=u.volumen_a_m3(self.v_tanque.valor, self.v_tanque.unidad),
            p_superior_pa=self._p(self.p_superior, patm),
            p_inferior_pa=self._p(self.p_inferior, patm),
            t_aire_k=u.temperatura_a_k(self.t_aire.valor, self.t_aire.unidad),
            q_consumo_m3s=u.caudal_a_m3s(self.q_consumo.valor, self.q_consumo.unidad),
            ref_consumo=self.q_consumo.referencia or "normal",
            p_atm_sitio_pa=patm,
            tramos=[Tramo(t.descripcion, t.longitud_m, t.d_interior_m()) for t in self.tramos],
            incluir_tuberia=self.incluir_tuberia,
            margen_consumo=self.margen_consumo_pct / 100.0,
            q_compresor_m3s=qc,
            ref_compresor=refc,
            t_retencion_req_min=self.t_retencion_req_min,
            n_politropico=self.n_politropico,
        )

    def a_criterios(self) -> Criterios:
        patm = self.p_atm_pa()

        def gauge(m):
            return None if m is None else self._p(m, patm) - patm

        return Criterios(
            t_retencion_min=self.t_retencion_req_min,
            fraccion_carga_max=None if self.fraccion_carga_max_pct is None else self.fraccion_carga_max_pct / 100.0,
            ciclos_h_max=self.ciclos_h_max,
            p_min_consumidor_pa=None if self.p_min_consumidor is None else self._p(self.p_min_consumidor, patm),
            dp_linea_pa=0.0 if self.dp_linea is None else self.dp_linea.valor * _DIF_PRESION[self.dp_linea.unidad],
            p_calibracion_psv_pa_g=gauge(self.p_calibracion_psv),
            p_diseno_pa_g=gauge(self.p_diseno),
            t_diseno_c=self.t_diseno_c,
        )

    # ------------------------------------------------------------------ persistencia
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CasoUsuario":
        d = dict(d)
        for k in ("v_tanque", "p_superior", "p_inferior", "t_aire", "q_consumo", "p_atm_sitio",
                  "q_compresor", "p_min_consumidor", "dp_linea", "p_calibracion_psv", "p_diseno"):
            if d.get(k) is not None:
                d[k] = Magnitud(**d[k])
        d["tramos"] = [TramoUsuario(**t) for t in d.get("tramos", [])]
        return cls(**d)

    def guardar(self, ruta: str) -> None:
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)

    @classmethod
    def cargar(cls, ruta: str) -> "CasoUsuario":
        with open(ruta, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def huella(self) -> str:
        """SHA-256 de las entradas: liga cada reporte con los datos que lo produjeron."""
        texto = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]
