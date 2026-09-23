import math
from dataclasses import replace

import bss_constants as C
import bss_evaluation as EV


def test_analyse_grid_and_trap_prove_the_optimum_and_agree_with_the_references():
    for network in ("grid", "trap"):
        a = EV.analyse(EV.Settings(network=network, side=8, obstacle_pct=20, seed=1, width=3))
        assert a.proved and not a.bss.capped and abs(a.bss.cost - a.ucs.cost) < 1e-9 and abs(a.astar.cost - a.ucs.cost) < 1e-9
        assert a.found_optimal and a.total_ratio > 0 and a.memory_ratio > 0


def test_a_capped_run_is_flagged_and_its_ratios_are_only_lower_bounds():
    a = EV.analyse(EV.Settings(side=8, seed=200001, width=1, cap=100000))
    assert a.bss.capped and not a.proved and not a.found_optimal
    assert math.isnan(a.first_gap) and math.isnan(a.expansions_until(1.0)) and math.isnan(a.expansions_until(0.0))
    full = EV.analyse(EV.Settings(side=8, seed=200001, width=1, cap=1000000))
    assert full.proved and a.total_ratio < full.total_ratio                      # Untergrenze < wahrer Faktor


def test_expansions_until_is_ordered_first_onepct_optimal_total():
    a = EV.analyse(EV.Settings(seed=100000, width=1))
    first = a.bss.solutions[0][0]
    onepct, optimal = a.expansions_until(1.0), a.expansions_until(0.0)
    assert first <= onepct <= optimal <= a.bss.expansions
    assert optimal == a.bss.solutions[-1][0]


def test_first_gap_and_beam_gap_agree_when_the_first_descent_is_the_beam_run():
    a = EV.analyse(EV.Settings(width=2))
    assert a.first_gap == a.beam_gap or abs(a.first_gap - a.beam_gap) < 1e-9
    failed = EV.analyse(EV.Settings(seed=100000, width=1))
    assert failed.beam.failed and math.isnan(failed.beam_gap) and not math.isnan(failed.first_gap)


def test_run_config_reports_shares_medians_and_ranges():
    out = EV.run_config(EV.Settings(), width=2)
    assert out["n_runs"] == 5 and out["proved_share"] == 100.0 and out["capped_share"] == 0.0 and out["optimal_found_share"] == 100.0
    assert out["total_ratio_lo"] <= out["total_ratio"] <= out["total_ratio_hi"]
    assert out["astar_expansions"] > 0 and out["astar_stored"] > 0


def test_run_config_separates_capped_runs():
    out = EV.run_config(EV.Settings(side=16), width=1, cap=10000)
    assert out["capped_share"] == 100.0 and out["proved_share"] == 0.0 and math.isnan(out["total_ratio_proved"])
    assert out["total_ratio"] > 1


def test_sweep_returns_one_row_per_value():
    assert [r["value"] for r in EV.sweep("width", EV.Settings(side=8))] == list(C.WIDTHS)
    assert [r["value"] for r in EV.sweep("obstacle_pct", EV.Settings(side=8))] == list(C.OBSTACLE_SWEEP)
    assert [r["value"] for r in EV.sweep("side", EV.Settings(), values=(6, 8))] == [6, 8]


def test_analyse_is_deterministic():
    a1 = EV.analyse(EV.Settings(side=9, obstacle_pct=25, seed=7))
    a2 = EV.analyse(EV.Settings(side=9, obstacle_pct=25, seed=7))
    assert a1.bss.solutions == a2.bss.solutions and a1.bss.expansions == a2.bss.expansions


def test_anytime_curves_structure_and_consistency():
    s = EV.Settings(side=10)
    data = EV.anytime_curves(s, widths=(1, 2, 4))
    assert set(data["curves"]) == {1, 2, 4} and data["optimum"] > 0 and data["astar_expansions"] > 0
    for w, cur in data["curves"].items():
        assert cur["proved"] and not cur["capped"] and abs(cur["points"][-1][1] - data["optimum"]) < 1e-9
        assert cur["total"] >= cur["points"][-1][0]
    direct = EV.analyse(replace(s, width=2))
    assert data["curves"][2]["total"] == direct.bss.expansions


def test_tail_structure_and_ordering():
    res = EV.tail(EV.Settings(side=8, cap=10000), seeds=(200000, 200001, 200002, 200003), widths=(1, 2))
    assert set(res) == {1, 2}
    for w, r in res.items():
        assert r["n"] == 4 and r["median"] <= r["p75"] <= r["p90"] <= r["max"]
        assert 0.0 <= r["capped_share"] <= 100.0 and r["no_solution_share"] <= r["capped_share"] + 1e-9
    assert res[1]["capped_share"] > 0 and res[2]["capped_share"] == 0.0
