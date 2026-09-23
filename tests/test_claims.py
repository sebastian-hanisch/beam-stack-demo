"""Jede Zahl in den Hilfetexten, Presets, Tabellen und Grenzen der App ist hier über die fünf festen Sweep-Instanzen belegt (der Ausreißer-
Test über 40 feste Instanzen), mit denselben Auswertungsfunktionen wie die App selbst (`ev.run_config`/`ev.sweep`/`ev.tail`) - NIE über ein
Ad-hoc-Skript. Positive UND negative Aussagen: BSS beweist bei jeder Breite das Optimum (positiv) - aber der Beweis ist teuer, der
Speichergewinn verschwindet ab Breite ~6, Breite 1 hat einen schweren Schwanz, und eine Startschranke hilft nicht immer (negativ). Werte sind
MEDIANE (Faktoren sind stark schief); gekappte Läufe werden getrennt ausgewiesen."""

from dataclasses import replace
from functools import lru_cache

import pytest

import bss_constants as C
import bss_evaluation as ev


@lru_cache(maxsize=None)
def _cfg(items):
    return ev.run_config(ev.Settings(), **dict(items))


def cfg(**kw):
    return _cfg(tuple(sorted(kw.items())))


@lru_cache(maxsize=None)
def _tail(items):
    return ev.tail(ev.Settings(), **dict(items))


def near(value, expected, tol):
    assert abs(value - expected) <= tol, f"{value:.3f} statt {expected}"


def rel(value, expected, frac=0.08, floor=0.05):
    near(value, expected, frac * abs(expected) + floor)


# --- Frage 1: optimal bei jeder Breite ---------------------------------------------------------------------------------------------------------


def test_every_width_proves_the_optimum_on_every_sweep_instance_and_beam_fails_at_width_one():
    for w in C.WIDTHS:
        row = cfg(width=w)
        assert row["proved_share"] == 100.0 and row["capped_share"] == 0.0 and row["optimal_found_share"] == 100.0
    assert cfg(width=1)["beam_failed_share"] == 40.0 and all(cfg(width=w)["beam_failed_share"] == 0.0 for w in C.WIDTHS[1:])


# --- Frage 2: was kostet der Beweis? -----------------------------------------------------------------------------------------------------------


def test_expansions_until_the_proof_relative_to_a_star_by_width():
    for w, ratio in zip(C.WIDTHS, (87.5, 17.04, 4.92, 2.68, 1.52, 1.23, 1.25, 1.25, 1.25)):
        rel(cfg(width=w)["total_ratio"], ratio)


def test_backtracks_by_width_and_none_from_width_eight():
    for w, back in zip(C.WIDTHS, (1924, 193, 30, 8, 3, 0, 0, 0, 0)):
        near(cfg(width=w)["backtracks"], back, 0.06 * back + 1)
    assert all(cfg(width=w)["backtracks"] == 0 for w in (8, 12, 16, 24))


def test_memory_saving_by_width_disappears_from_about_width_six():
    for w, ratio in zip(C.WIDTHS, (4.40, 2.44, 1.69, 1.41, 1.05, 0.97, 0.90, 0.90, 0.90)):
        near(cfg(width=w)["memory_ratio"], ratio, 0.07)
    assert cfg(width=4)["memory_ratio"] > 1.2 and cfg(width=8)["memory_ratio"] < 1.0 and cfg(width=24)["memory_ratio"] < 1.0


def test_the_default_width_numbers_from_the_preset_help_and_intro():
    row = cfg()
    rel(row["total_ratio"], 17.04)
    near(row["memory_ratio"], 2.44, 0.2)


# --- Anytime -----------------------------------------------------------------------------------------------------------------------------------


def test_first_solution_gap_and_timing_at_widths_one_and_two():
    near(cfg(width=1)["first_gap"], 7.05, 0.35)
    near(cfg(width=1)["beam_gap"], 5.97, 0.35)
    near(cfg(width=2)["first_gap"], 4.50, 0.3)
    near(cfg(width=2)["beam_gap"], 4.50, 0.3)
    near(cfg(width=1)["first_ratio"], 0.26, 0.03)
    near(cfg(width=2)["first_ratio"], 0.47, 0.04)


def test_expansions_to_one_percent_and_to_the_optimum_versus_the_proof():
    rel(cfg(width=1)["onepct_ratio"], 39.8, 0.1)
    rel(cfg(width=1)["optimal_ratio"], 40.3, 0.1)
    rel(cfg(width=2)["onepct_ratio"], 4.87, 0.1)
    rel(cfg(width=2)["optimal_ratio"], 4.87, 0.1)
    assert cfg(width=1)["optimal_ratio"] < 0.6 * cfg(width=1)["total_ratio"]         # bei Breite 1 verbraucht der Beweis noch einmal etwa so viel


# --- IDA* als Gegenstück -----------------------------------------------------------------------------------------------------------------------


def test_ida_star_versus_beam_stack_search_at_size_eight():
    row = cfg(side=8, width=1)
    near(row["ida_factor"], 705, 60)
    near(row["ida_memory_ratio"], 3.0, 0.3)
    rel(row["total_ratio"], 9.10, 0.1)
    near(row["memory_ratio"], 3.0, 0.3)
    assert row["ida_factor"] > 50 * row["total_ratio"]


def test_ida_star_hits_its_cap_from_size_twelve_while_beam_stack_search_proves_at_width_two():
    assert [cfg(side=s, width=2)["ida_capped_share"] for s in (8, 10, 12, 14, 16)] == [0.0, 40.0, 80.0, 100.0, 100.0]
    for s in (8, 10, 12, 14, 16):
        assert cfg(side=s, width=2)["proved_share"] == 100.0


# --- Startschranke -----------------------------------------------------------------------------------------------------------------------------


def test_start_bound_helps_at_width_one_and_two_but_costs_more_at_width_four():
    none1 = cfg(width=1)["total_ratio"]
    for b in (4, 8, 16, 24):
        rel(cfg(width=1, bound_width=b)["total_ratio"], 55.3, 0.08)
        assert cfg(width=1, bound_width=b)["total_ratio"] < 0.7 * none1
    for b in (4, 8, 16, 24):
        assert 14.5 < cfg(width=2, bound_width=b)["total_ratio"] < 17.0
    for b in (4, 8, 16, 24):
        assert 3.2 < cfg(width=4, bound_width=b)["total_ratio"] < 4.0 and cfg(width=4, bound_width=b)["total_ratio"] > cfg(width=4)["total_ratio"]
    near(1 - cfg(width=1, bound_width=8)["total_ratio"] / none1, 0.37, 0.03)              # "im Median 37 %"


# --- Hindernisdichte und Rastergröße -----------------------------------------------------------------------------------------------------------


def test_obstacle_sweep_at_width_two():
    rows = ev.sweep("obstacle_pct", replace(ev.Settings(), width=2))
    for row, ratio in zip(rows, (32.0, 9.78, 11.70, 3.63, 3.19)):
        rel(row["total_ratio"], ratio, 0.1)
    for row, mem in zip(rows, (2.80, 2.44, 2.17, 1.49, 1.25)):
        near(row["memory_ratio"], mem, 0.2)
    assert [r["beam_failed_share"] for r in rows] == [0.0, 0.0, 20.0, 60.0, 20.0]
    assert all(r["proved_share"] == 100.0 for r in rows)


def test_size_sweep_at_width_two_and_width_one():
    rows2 = ev.sweep("side", replace(ev.Settings(), width=2))
    for row, ratio in zip(rows2, (2.79, 5.16, 17.04, 9.96, 49.64)):
        rel(row["total_ratio"], ratio, 0.1)
    for row, mem in zip(rows2, (1.61, 2.00, 2.44, 2.42, 2.62)):
        near(row["memory_ratio"], mem, 0.2)
    rows1 = ev.sweep("side", replace(ev.Settings(), width=1))
    for row, ratio in zip(rows1, (9.10, 14.03, 87.51, 67.68, 351.74)):
        rel(row["total_ratio"], ratio, 0.12)
    for row, mem in zip(rows1, (3.0, 3.58, 4.40, 4.74, 4.94)):
        near(row["memory_ratio"], mem, 0.3)
    assert [r["capped_share"] for r in rows1] == [0.0, 0.0, 0.0, 0.0, 20.0] and rows1[-1]["proved_share"] == 80.0


# --- Ausreißer ---------------------------------------------------------------------------------------------------------------------------------


def test_width_one_has_a_heavy_tail_over_40_instances():
    r = _tail(())[1]
    assert r["n"] == 40
    rel(r["median"], 49.1, 0.12)
    rel(r["p75"], 122.5, 0.15)
    rel(r["p90"], 1109, 0.2)
    rel(r["max"], 4054, 0.25)
    assert r["capped_share"] == 10.0 and r["no_solution_share"] == 10.0                    # 4 von 40, alle ganz ohne Lösung


def test_widths_two_to_four_are_well_behaved_over_the_same_instances():
    res = _tail(())
    for w, maxv in ((2, 35), (3, 30), (4, 8)):
        assert res[w]["capped_share"] == 0.0 and res[w]["no_solution_share"] == 0.0
        near(res[w]["max"], maxv, 0.2 * maxv + 1)
    assert res[1]["max"] > 50 * res[2]["max"]
