"""Presets: Vollständigkeit, gültige Werte, der Median des Expansions-Faktors bleibt bei den Raster-Presets in der gemessenen Spannweite
über die 5 festen Sweep-Instanzen (vollständig deterministisch), und jedes Preset zeigt, was sein Name und sein Hilfetext sagen."""

from dataclasses import replace

import pytest

import bss_constants as C
import bss_evaluation as ev
import bss_presets as P


def _settings(p, seed=None):
    return ev.Settings(network=p["network"], side=p["side"], obstacle_pct=p["obstacle_pct"], seed=p["seed"] if seed is None else seed,
                       width=p["width"], bound_width=p["bound_width"], cap=p["cap"])


def _analyse(name):
    return ev.analyse(_settings(C.PRESETS[name]))


def test_every_preset_has_help_and_the_grid_presets_a_band():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    assert len(C.PRESETS) == 8
    for name, p in C.PRESETS.items():
        assert set(p) == set(P.PRESET_KEYS) and C.PRESET_HELP[name]
    assert set(C.PRESET_EXPECTED_BANDS) == {n for n, p in C.PRESETS.items() if p["network"] == "grid"}


def test_preset_values_are_valid():
    for p in C.PRESETS.values():
        assert p["network"] in P.NETWORKS and p["width"] in C.WIDTHS and p["bound_width"] in C.BOUND_WIDTHS and p["cap"] in C.CAPS
        assert C.SIDE_MIN <= p["side"] <= C.SIDE_MAX and C.OBSTACLE_MIN <= p["obstacle_pct"] <= C.OBSTACLE_MAX


def test_default_preset_equals_the_default_settings():
    assert _settings(C.PRESETS["Standardfall (Voreinstellung)"]) == ev.Settings()


@pytest.mark.parametrize("name", list(C.PRESET_EXPECTED_BANDS))
def test_grid_preset_median_expansion_factor_stays_in_its_measured_band(name):
    lo, hi = C.PRESET_EXPECTED_BANDS[name]
    row = ev.run_config(_settings(C.PRESETS[name]))
    assert lo <= row["total_ratio"] <= hi, row["total_ratio"]


def test_standard_preset_numbers_from_the_help_text():
    a = _analyse("Standardfall (Voreinstellung)")
    assert a.proved and a.bss.solutions[0][0] == 43 and a.beam.expansions == 43 and abs(a.beam.cost - a.ucs.cost) < 1e-9
    assert (a.bss.expansions, a.astar.expansions, a.bss.peak_stored, a.astar.stored) == (651, 82, 44, 100)


def test_beam_fails_preset_numbers_from_the_help_text():
    a = _analyse("Beam scheitert (Breite 1)")
    assert a.beam.failed and a.proved and len(a.bss.solutions) == 22
    assert a.bss.solutions[0][0] == 27 and a.bss.solutions[0][1] == pytest.approx(232.9, abs=0.05)
    assert a.bss.cost == pytest.approx(188.1, abs=0.05) and a.bss.expansions == 8488 and a.bss.peak_stored == 25 and a.astar.stored == 110


def test_trap_preset_numbers_from_the_help_text():
    a = _analyse("Handgebaute Falle (Breite 1)")
    assert [round(c, 2) for _e, c, _p in a.bss.solutions] == [14.46, 13.46] and a.bss.backtracks == 1
    assert (a.bss.expansions, a.astar.expansions) == (8, 7)


def test_depth_first_preset_numbers_from_the_help_text():
    a = _analyse("Breite 1 = Tiefensuche")
    assert a.bss.backtracks == 577 and a.bss.expansions == 2546 and a.bss.peak_stored == 23 and a.astar.stored == 100
    assert a.bss.solutions[0][0] == 22 and a.bss.solutions[0][1] == pytest.approx(177.7, abs=0.05)
    assert a.bss.solutions[1][0] == 25 and a.bss.solutions[1][1] == pytest.approx(175.9, abs=0.05)


def test_large_width_preset_has_no_backtracking_and_no_memory_saving():
    a = _analyse("Große Breite: kein Rücksprung")
    assert a.bss.backtracks == 0 and a.bss.expansions == 125 and a.bss.peak_stored == 126 and a.astar.stored == 100 and a.bss.peak_stored > a.astar.stored


def test_start_bound_preset_halves_the_effort_on_its_instance():
    p = C.PRESETS["Startschranke (Beam 8)"]
    with_bound = ev.analyse(_settings(p))
    without = ev.analyse(replace(_settings(p), bound_width=0))
    assert (without.bss.expansions, with_bound.bss.expansions) == (1190, 615)
    assert with_bound.bss.solutions[0][0] == 120                                    # die Expansionen des vorab laufenden Beam Search zählen mit


def test_outlier_preset_finds_nothing_within_the_cap_but_width_two_and_three_are_fast():
    a = _analyse("Ausreißer (Breite 1)")
    assert a.bss.capped and a.bss.solutions == [] and a.astar.expansions == 37
    base = _settings(C.PRESETS["Ausreißer (Breite 1)"])
    assert ev.analyse(replace(base, width=2)).bss.expansions == 643 and ev.analyse(replace(base, width=3)).bss.expansions == 84
    assert ev.analyse(replace(base, cap=1000000)).bss.expansions == 573409


def test_cap_preset_is_capped_with_an_unproven_best_solution_and_the_full_run_proves_it():
    a = _analyse("Kappung (Obergrenze 10 000)")
    assert a.bss.capped and not a.proved and len(a.bss.solutions) == 11
    assert a.bss.cost == pytest.approx(181.0, abs=0.05) and a.ucs.cost == pytest.approx(177.8, abs=0.05)
    full = ev.analyse(replace(_settings(C.PRESETS["Kappung (Obergrenze 10 000)"]), cap=300000))
    assert full.proved and full.bss.expansions == 53661


def test_bounds_and_permalink_constants():
    assert P.bounds("side_slider") == (C.SIDE_MIN, C.SIDE_MAX) and P.bounds("seed_input") == (0, C.SEED_MAX)
    assert len({spec.url_param for spec in P.SETTING_SPECS.values()}) == len(P.SETTING_SPECS)
    assert C.DEFAULT_WIDTH in C.WIDTHS and C.DEFAULT_CAP in C.CAPS and set(C.CURVE_WIDTHS) <= set(C.WIDTHS)


def test_network_width_bound_and_cap_permalink_casters():
    assert P._network_from_str("trap") == "trap"
    with pytest.raises(ValueError):
        P._network_from_str("nope")
    assert P.SETTING_SPECS["width_select"].caster("8") == 8 and P.SETTING_SPECS["bound_select"].caster("24") == 24 and P.SETTING_SPECS["cap_select"].caster("100000") == 100000
    for key, bad in (("width_select", "7"), ("bound_select", "5"), ("cap_select", "12345")):
        with pytest.raises(ValueError):
            P.SETTING_SPECS[key].caster(bad)
