"""Reglas del sistema de alertas y del motor de decisión."""
import copy

from validation.alerts import Alert, BASIS_HYPOTHESIS, LEGACY
from validation.decision_engine import module_decision, global_decision, Decision
from core.calculation import run_project
from core.project import Project


def test_hypothesis_cannot_be_critical():
    a = Alert("CRÍTICO", "X", "p", "d", basis=BASIS_HYPOTHESIS)
    assert a.level == "ALTO"


def test_legacy_mapping():
    assert LEGACY["CRÍTICO"] == "CRÍTICA" and LEGACY["MEDIO"] == "ADVERTENCIA" and LEGACY["INFO"] == "INFORMATIVA"


def test_decision_levels():
    mk = lambda lv: [Alert(lv, "M", "p", "d", basis="física")]  # noqa: E731
    assert module_decision("M", mk("CRÍTICO"), [], []).code == "no"
    assert module_decision("M", mk("ALTO"), [], []).code == "mod"
    assert module_decision("M", mk("MEDIO"), [], []).code == "obs"
    assert module_decision("M", mk("CORRECTO"), [], []).code == "ok"
    assert module_decision("M", [], [], [], insufficient=True).code == "insuf"


def test_global_decision():
    d = {"A": Decision("A", "ok"), "B": Decision("B", "obs")}
    assert global_decision(d, ("A",)) == "obs"
    d["C"] = Decision("C", "mod")
    assert global_decision(d, ("A",)) == "mod"


def test_low_transport_velocity_triggers_alto(example_project, db, settings):
    p = Project.from_dict(copy.deepcopy(example_project.to_dict()))
    for s in p.network.segments:
        if s.id == "M2":
            s.D = 0.40
    r = run_project(p, db, settings, compute_fans=False)
    assert any(a.parameter == "Velocidad de transporte" and a.item == "M2" and a.level == "ALTO" for a in r.alerts)


def test_undersized_fan_flow_deficit(example_project, db, settings):
    p = Project.from_dict(copy.deepcopy(example_project.to_dict()))
    p.fan_selection.selected_id = "BI-450"
    r = run_project(p, db, settings)
    assert any(a.parameter == "Caudal insuficiente" for a in r.alerts)
    assert r.dictamen.decision_code in ("mod", "no")


def test_ach_only_for_contaminant_control(example_project, db, settings):
    p = Project.from_dict(copy.deepcopy(example_project.to_dict()))
    p.airflow.purpose = "contaminant_control"
    p.hoods = []
    p.network.nodes = {}
    p.network.segments = []
    r = run_project(p, db, settings)
    assert any(a.parameter == "Método de caudal" and a.level == "ALTO" for a in r.alerts)


def test_motor_undersized_critical(example_project, db, settings):
    p = Project.from_dict(copy.deepcopy(example_project.to_dict()))
    p.power.motor_selected_kw = 4.0
    r = run_project(p, db, settings)
    assert any(a.module == "Potencia y motores" and a.level == "CRÍTICO" for a in r.alerts)
