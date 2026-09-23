"""AppTest-Rauchtests: Voreinstellung, jedes Preset, jeder Schritt für beide Instanz-Typen, gekappte Läufe, Lösungs-Slider und Beam-Stack-Verlauf,
Randwerte, Würfel-Knopf, Permalink-Grenzen, Instanzwechsel, Sweeps/Speicher-Zeit-Diagramm/Ausreißer-Test auf Abruf, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import bss_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(step=1, **state):
    at = AppTest.from_file(APP, default_timeout=240)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    if step != 1:
        at.select_slider(key="bss_step").set_value(step).run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def _labels(at):
    return {m.label for m in at.metric}


def test_default_run_has_no_exception_and_shows_four_metrics():
    at = _run()
    _ok(at)
    assert {"Status", "Exp. bis Beweis / A*", "Speicher A* / BSS", "Beam (Breite 2)"} <= _labels(at)
    assert _metric(at, "Status") == "bewiesen" and _metric(at, "Exp. bis Beweis / A*") == "7.9x"


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_button_runs(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert at.session_state["network_select"] == p["network"] and at.session_state["width_select"] == p["width"]
    assert at.session_state["bound_select"] == p["bound_width"] and at.session_state["cap_select"] == p["cap"]
    assert at.metric


@pytest.mark.parametrize("step", [1, 2, 3])
def test_every_step_runs_for_both_networks(step):
    for network in ("grid", "trap"):
        at = _run(network_select=network, step=step)
        _ok(at)
        assert at.get("plotly_chart") and at.session_state["bss_step"] == step


@pytest.mark.parametrize("step", [1, 2, 3])
def test_capped_runs_without_any_solution_render_in_every_step_and_are_flagged(step):
    at = _run(side_slider=8, seed_input=200001, width_select=1, cap_select=100000, step=step)
    _ok(at)
    assert _metric(at, "Status") == "gekappt" and _metric(at, "Exp. bis Beweis / A*").startswith("≥ ") and _metric(at, "Beam (Breite 1)") == "kein Pfad"
    if step in (2, 3):
        assert any("keine Lösung" in w.value for w in at.warning)


def test_solution_slider_walks_through_all_solutions_and_survives_an_instance_change():
    at = _run(step=2, seed_input=100000, width_select=1)
    _ok(at)
    slider = at.slider(key="bss_solution")
    assert slider.max == 22
    slider.set_value(slider.max).run()
    _ok(at)
    assert at.session_state["bss_solution"] == 22
    at.session_state["network_select"] = "trap"                  # weniger Lösungen: gespeicherter Wert wird geklemmt
    at.run()
    _ok(at)
    assert at.session_state["bss_solution"] <= 2


def test_trap_shows_the_beam_stack_walkthrough_and_its_slider_is_clamped():
    at = _run(network_select="trap", width_select=1)
    _ok(at)
    assert any("Beam-Stack Schritt für Schritt" in s.value for s in at.subheader)
    slider = at.slider(key="trace_step")
    slider.set_value(slider.max).run()
    _ok(at)
    assert any("Stack leer: Optimum bewiesen" in m.value for m in at.markdown)
    at.session_state["width_select"] = 3                            # kürzerer Verlauf
    at.run()
    _ok(at)
    assert at.session_state["trace_step"] <= slider.max


@pytest.mark.parametrize("kw", [
    dict(side_slider=C.SIDE_MIN), dict(side_slider=C.SIDE_MAX, cap_select=10000), dict(obstacle_slider=C.OBSTACLE_MIN), dict(obstacle_slider=C.OBSTACLE_MAX),
    dict(width_select=C.WIDTHS[0], cap_select=10000), dict(width_select=C.WIDTHS[-1]), dict(bound_select=24), dict(cap_select=C.CAPS[0]),
])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))
    _ok(_run(step=2, **kw))


def test_dice_button_changes_the_seed():
    at = _run()
    old = at.session_state["seed_input"]
    next(b for b in at.button if b.label == "🎲 Neue Instanz generieren").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old


def test_permalink_values_are_clamped_and_invalid_choices_fall_back_to_the_default():
    at = AppTest.from_file(APP, default_timeout=240)
    at.query_params["side"] = "9999"
    at.query_params["obstacle"] = "9999"
    at.query_params["width"] = "7"
    at.query_params["bound"] = "5"
    at.query_params["cap"] = "12345"
    at.query_params["network"] = "zzz"
    at.run()
    _ok(at)
    assert at.session_state["side_slider"] == C.SIDE_MAX and at.session_state["obstacle_slider"] == C.OBSTACLE_MAX
    assert at.session_state["width_select"] == C.DEFAULT_WIDTH and at.session_state["bound_select"] == 0
    assert at.session_state["cap_select"] == C.DEFAULT_CAP and at.session_state["network_select"] == "grid"


def test_sidebar_hides_grid_only_controls_for_the_trap_but_keeps_width_bound_and_cap():
    at = _run(network_select="trap")
    _ok(at)
    assert not any(s.key == "side_slider" for s in at.slider)
    keys = {s.key for s in at.select_slider}
    assert {"width_select", "bound_select", "cap_select"} <= keys


def test_changing_the_instance_while_on_step_two_does_not_crash():
    at = _run(step=2, side_slider=12)
    _ok(at)
    at.session_state["side_slider"] = C.SIDE_MIN
    at.run()
    _ok(at)
    at.session_state["network_select"] = "trap"
    at.run()
    _ok(at)


def test_tradeoff_diagram_runs_on_demand():
    at = _run(side_slider=8)
    next(b for b in at.button if b.key == "tradeoff_start").click().run()
    _ok(at)
    assert at.get("plotly_chart") and any("Tab. 1 des Papers" in c.value for c in at.caption)


@pytest.mark.parametrize("param", ["width", "obstacle_pct", "side"])
@pytest.mark.parametrize("metric", ["ratio", "memory", "gap", "anytime", "shares"])
def test_sweeps_run_on_demand_for_every_metric(param, metric):
    at = _run(side_slider=8, sweep_metric=metric)
    at.selectbox(key="sweep_select").set_value(param).run()
    next(b for b in at.button if b.key == "sweep_start").click().run()
    _ok(at)
    assert at.get("plotly_chart")


def test_tail_experiment_runs_on_demand_and_shows_one_row_per_width():
    at = _run(side_slider=8, cap_select=10000)
    next(b for b in at.button if b.key == "tail_start").click().run()
    _ok(at)
    table = next(m.value for m in at.markdown if m.value.startswith("| Breite | Median"))
    assert all(f"| {w} |" in table for w in (1, 2, 3, 4))


def test_limits_footer_and_literature_are_present():
    at = _run()
    assert any("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in c.value for c in at.caption)
    assert any("Wo die Annahmen enden" in s.value for s in at.subheader)
    assert any("Der Median genügt" in m.value and "Der Beweis ist billig" in m.value and "BSS schlägt IDA" in m.value for m in at.markdown)
