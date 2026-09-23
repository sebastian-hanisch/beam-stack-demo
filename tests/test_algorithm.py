"""Die zentrale Korrektheits-Kette für Beam-Stack Search: gültiger Pfad, Satz 1 des Papers DIREKT (die beste Lösung ist bei jeder
Breite optimal, sobald der Stack leer ist) auf Raster, Falle, kleinen Graphen gegen Brute-Force und 1500 zufälligen Graphen mit nicht
konsistenter Heuristik, Anytime-Folge, die Sonderfälle des Papers (Breite >= größte Schicht = kein Rücksprung, Breite 1 = eine Schicht
je Knoten), Speicher-Schranken, Beam-Stack-Invarianten, Startschranke, Kappung, die handgebaute Falle und die kopierten Suchkerne."""

import numpy as np
import pytest

import bss_algorithm as A
import bss_graph as G
import bss_scenario as S

EPS = 1e-9
INF = float("inf")
HUGE = 10 ** 6


def _brute_force_shortest_cost(graph, start, goal):
    best = None
    stack = [(start, [start], 0.0)]
    while stack:
        node, path, cost = stack.pop()
        if node == goal:
            if best is None or cost < best:
                best = cost
            continue
        for v, w in zip(graph.neighbors[node], graph.weights[node]):
            if v not in path:
                stack.append((v, path + [v], cost + w))
    return best


def _random_layered_instance(seed):
    """Kleiner zufälliger Schichtgraph (<= 11 Knoten) mit ganzzahligen Gewichten und einer zulässigen, meist NICHT konsistenten
    Heuristik h = floor(Restweg * Faktor)."""
    rng = np.random.default_rng(seed)
    sizes = [1] + [int(rng.integers(1, 4)) for _ in range(int(rng.integers(2, 4)))] + [1]
    ids, k = [], 0
    for s in sizes:
        ids.append(list(range(k, k + s)))
        k += s
    edges = []
    for a, b in zip(ids[:-1], ids[1:]):
        has_out = set()
        for v in b:
            for u in rng.choice(a, size=int(rng.integers(1, min(2, len(a)) + 1)), replace=False):
                edges.append((int(u), int(v), float(rng.integers(1, 6))))
                has_out.add(int(u))
        for u in a:
            if u not in has_out:
                edges.append((int(u), int(rng.choice(b)), float(rng.integers(1, 6))))
    graph = G.from_edges(k, [(i, 0.0) for i in range(k)], edges)
    goal = k - 1
    d = np.array([A.uniform_cost_search(graph, v, goal).cost for v in range(k)])
    h = np.floor(d * rng.uniform(0.2, 1.0, k))
    h[goal] = 0
    return graph, 0, goal, h, d[0]


# --- Gültigkeit ------------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bound", [0, 4])
@pytest.mark.parametrize("width", [1, 2, 3, 5, 8])
@pytest.mark.parametrize("seed", range(8))
def test_bss_returns_a_valid_simple_path_with_recomputed_cost(seed, width, bound):
    inst = S.grid_instance(side=6, obstacle_pct=20, seed=seed)
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, width, bound)
    assert result.proved and result.path[0] == inst.start and result.path[-1] == inst.goal
    assert len(set(result.path)) == len(result.path)
    for u, v in zip(result.path[:-1], result.path[1:]):
        assert v in inst.graph.neighbors[u]
    assert G.path_cost(inst.graph, result.path) == pytest.approx(result.cost, abs=1e-6)


def test_bss_is_deterministic():
    inst = S.grid_instance(side=8, obstacle_pct=20, seed=3)
    r1 = A.beam_stack_search(inst.graph, inst.start, inst.goal, 2)
    r2 = A.beam_stack_search(inst.graph, inst.start, inst.goal, 2)
    assert r1.path == r2.path and r1.expansions == r2.expansions and r1.solutions == r2.solutions and r1.revisits == r2.revisits


def test_invalid_arguments_are_rejected():
    inst = S.trap_instance()
    with pytest.raises(ValueError):
        A.beam_stack_search(inst.graph, inst.start, inst.goal, 0)
    with pytest.raises(ValueError):
        A.beam_stack_search(inst.graph, inst.start, inst.goal, 2, bound_width=-1)


def test_start_equals_goal_and_unreachable_goal():
    inst = S.trap_instance()
    trivial = A.beam_stack_search(inst.graph, inst.start, inst.start, 2)
    assert trivial.path == [inst.start] and trivial.cost == 0.0 and trivial.expansions == 0 and trivial.proved
    graph = G.from_edges(4, [(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 1, 1.0), (2, 3, 1.0)])
    for width in (1, 3, HUGE):
        result = A.beam_stack_search(graph, 0, 3, width)
        assert result.path == [] and result.cost == INF and result.proved and not result.capped and result.solutions == []


# --- Satz 1: optimal bei jeder Breite -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("obstacle", [0, 15, 40])
@pytest.mark.parametrize("seed", range(20))
def test_bss_finds_and_proves_the_optimum_on_grids_for_every_width(seed, obstacle):
    inst = S.grid_instance(side=8, obstacle_pct=obstacle, seed=200000 + seed)
    optimum = A.uniform_cost_search(inst.graph, inst.start, inst.goal).cost
    for width in (2, 3, 4, 8, 24, HUGE):
        result = A.beam_stack_search(inst.graph, inst.start, inst.goal, width)
        assert result.proved and result.cost == pytest.approx(optimum, abs=EPS), (width, result.cost, optimum)


@pytest.mark.parametrize("obstacle", [0, 15, 40])
@pytest.mark.parametrize("seed", range(20))
def test_bss_finds_and_proves_the_optimum_with_width_one_on_small_grids(seed, obstacle):
    inst = S.grid_instance(side=6, obstacle_pct=obstacle, seed=200000 + seed)
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, 1)
    assert result.proved and result.cost == pytest.approx(A.uniform_cost_search(inst.graph, inst.start, inst.goal).cost, abs=EPS)


@pytest.mark.parametrize("width", [1, 2, 3, 5])
@pytest.mark.parametrize("seed", range(12))
def test_bss_matches_the_brute_force_optimum_on_small_instances(seed, width):
    inst = S.grid_instance(side=5, obstacle_pct=15, seed=seed)
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, width)
    assert result.proved and result.cost == pytest.approx(_brute_force_shortest_cost(inst.graph, inst.start, inst.goal), abs=1e-6)


@pytest.mark.parametrize("width", [1, 2, 3, 4, 5, HUGE])
def test_bss_solves_the_trap_optimally_for_every_width(width):
    inst = S.trap_instance()
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, width)
    assert result.proved and result.cost == pytest.approx(_brute_force_shortest_cost(inst.graph, inst.start, inst.goal), abs=1e-6)


def test_bss_is_optimal_on_1500_random_small_graphs_with_an_inconsistent_heuristic():
    for seed in range(1500):
        graph, start, goal, h, optimum = _random_layered_instance(seed)
        for width in (1, 2, 3):
            result = A.beam_stack_search(graph, start, goal, width, h=h)
            assert result.proved and result.cost == pytest.approx(optimum, abs=EPS), (seed, width, result.cost, optimum)


def test_bss_finds_a_path_where_beam_search_fails():
    inst = S.grid_instance(side=12, obstacle_pct=15, seed=100000)
    assert A.beam_search(inst.graph, inst.start, inst.goal, 1, "f").failed
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, 1)
    assert result.proved and result.cost == pytest.approx(A.uniform_cost_search(inst.graph, inst.start, inst.goal).cost, abs=EPS)
    assert len(result.solutions) > 1


# --- Anytime-Folge -----------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("width", [1, 2, 4])
@pytest.mark.parametrize("seed", range(10))
def test_solution_sequence_is_strictly_improving_and_ends_at_the_proven_optimum(seed, width):
    inst = S.grid_instance(side=10, obstacle_pct=15, seed=100000 + seed)
    optimum = A.uniform_cost_search(inst.graph, inst.start, inst.goal).cost
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, width)
    costs = [c for _e, c, _p in result.solutions]
    exps = [e for e, _c, _p in result.solutions]
    assert all(b < a - 1e-12 for a, b in zip(costs[:-1], costs[1:]))
    assert all(b >= a for a, b in zip(exps[:-1], exps[1:])) and exps[-1] <= result.expansions
    assert costs[0] >= optimum - EPS and costs[-1] == pytest.approx(optimum, abs=EPS) and result.cost == costs[-1]
    for _e, cost, path in result.solutions:
        assert G.path_cost(inst.graph, path) == pytest.approx(cost, abs=1e-6)


# --- Sonderfälle des Papers -----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("obstacle", [0, 15, 40])
@pytest.mark.parametrize("seed", range(10))
def test_width_at_least_the_largest_layer_means_no_backtracking(seed, obstacle):
    inst = S.grid_instance(side=10, obstacle_pct=obstacle, seed=100000 + seed)
    unlimited = A.beam_stack_search(inst.graph, inst.start, inst.goal, HUGE)
    assert unlimited.backtracks == 0
    at_limit = A.beam_stack_search(inst.graph, inst.start, inst.goal, unlimited.max_layer_size)
    assert at_limit.backtracks == 0 and at_limit.expansions == unlimited.expansions and at_limit.cost == unlimited.cost
    if unlimited.max_layer_size > 1:
        assert A.beam_stack_search(inst.graph, inst.start, inst.goal, 1).backtracks > 0


@pytest.mark.parametrize("seed", range(10))
def test_width_one_stores_a_single_node_per_layer_like_depth_first_search(seed):
    inst = S.grid_instance(side=8, obstacle_pct=15, seed=100000 + seed)
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, 1)
    assert result.max_layer_size == 1 and result.peak_stored <= len(result.revisits)
    assert result.backtracks == sum(result.revisits) and result.backtracks > 0


# --- Schranken und Beam-Stack-Invarianten ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("width", [1, 2, 4, 8])
@pytest.mark.parametrize("seed", range(8))
def test_storage_is_bounded_by_width_times_depth(seed, width):
    inst = S.grid_instance(side=10, obstacle_pct=15, seed=100000 + seed)
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, width)
    assert result.max_layer_size <= width
    assert result.peak_stored <= width * len(result.revisits)
    assert result.peak_stored <= A.a_star(inst.graph, inst.start, inst.goal).stored or width >= 4      # bei schmaler Breite weniger Speicher als A*


@pytest.mark.parametrize("width", [1, 2, 3])
def test_beam_stack_invariants_on_the_trap_trace(width):
    inst = S.trap_instance()
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, width, keep_trace=True)
    events = [t[0] for t in result.trace]
    assert events[0] == "start" and events[-1] == "done"
    for event, ell, items, U, layers in result.trace:
        assert len(items) == len(layers) or event == "done"
        for fmin, fmax in items:
            assert fmin <= fmax
        assert ell < max(len(layers), 1)
    assert result.trace[-1][2] == []                                   # Stack am Ende leer
    us = [t[3] for t in result.trace]
    assert all(b <= a for a, b in zip(us[:-1], us[1:]))                # U sinkt nur


# --- Startschranke ---------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("width", [1, 2, 4])
@pytest.mark.parametrize("seed", range(8))
def test_start_bound_keeps_the_optimum_and_counts_the_beam_expansions(seed, width):
    inst = S.grid_instance(side=10, obstacle_pct=15, seed=100000 + seed)
    plain = A.beam_stack_search(inst.graph, inst.start, inst.goal, width)
    bounded = A.beam_stack_search(inst.graph, inst.start, inst.goal, width, bound_width=8)
    beam = A.beam_search(inst.graph, inst.start, inst.goal, 8, "f")
    assert bounded.proved and bounded.cost == pytest.approx(plain.cost, abs=EPS)
    assert bounded.solutions[0][0] == beam.expansions and bounded.solutions[0][1] == pytest.approx(beam.cost, abs=EPS)
    assert bounded.expansions >= beam.expansions


# --- Kappung ----------------------------------------------------------------------------------------------------------------------------------


def test_cap_stops_the_search_keeps_a_valid_best_solution_and_claims_no_proof():
    inst = S.grid_instance(side=16, obstacle_pct=15, seed=35)
    optimum = A.uniform_cost_search(inst.graph, inst.start, inst.goal).cost
    result = A.beam_stack_search(inst.graph, inst.start, inst.goal, 1, max_expansions=10000)
    assert result.capped and not result.proved and result.expansions > 10000
    assert result.path and result.cost >= optimum - EPS and G.path_cost(inst.graph, result.path) == pytest.approx(result.cost, abs=1e-6)
    full = A.beam_stack_search(inst.graph, inst.start, inst.goal, 1)
    assert full.proved and full.cost == pytest.approx(optimum, abs=EPS)


# --- Handgebaute Falle ----------------------------------------------------------------------------------------------------------------------


def test_trap_numbers():
    inst = S.trap_instance()
    w1 = A.beam_stack_search(inst.graph, inst.start, inst.goal, 1)
    assert [round(c, 3) for _e, c, _p in w1.solutions] == [14.464, 13.459] and w1.backtracks == 1 and w1.expansions == 8
    w2 = A.beam_stack_search(inst.graph, inst.start, inst.goal, 2)
    assert [round(c, 3) for _e, c, _p in w2.solutions] == [13.459] and w2.backtracks == 0 and w2.expansions == 6


# --- Kopierte Suchkerne ---------------------------------------------------------------------------------------------------------------------


def test_copied_searches_reproduce_the_sibling_demo_numbers():
    inst = S.grid_instance(side=12, obstacle_pct=15, seed=35)
    f3 = A.beam_search(inst.graph, inst.start, inst.goal, 3, "f")
    assert f3.cost == pytest.approx(175.90, abs=0.01) and f3.expansions == 63
    trap = S.trap_instance()
    ida = A.ida_star(trap.graph, trap.start, trap.goal)
    assert (ida.expansions, ida.iterations, ida.stored) == (22, 6, 4)


def test_inherited_heuristic_is_admissible_and_a_star_is_optimal():
    for seed in range(10):
        inst = S.grid_instance(side=7, obstacle_pct=20, seed=seed)
        h = A.heuristic(inst.graph.xy, inst.goal)
        ucs = A.uniform_cost_search(inst.graph, inst.start, inst.goal)
        for node in range(inst.graph.n):
            assert h[node] <= A.uniform_cost_search(inst.graph, node, inst.goal).cost + EPS
        assert A.a_star(inst.graph, inst.start, inst.goal).cost == pytest.approx(ucs.cost, abs=EPS)


# --- Ausreißer: Breite 1 ist Tiefensuche mit schwerem Schwanz -------------------------------------------------------------------------------


def test_width_one_can_need_orders_of_magnitude_more_expansions_than_width_two():
    inst = S.grid_instance(side=8, obstacle_pct=15, seed=200001)
    astar = A.a_star(inst.graph, inst.start, inst.goal)
    capped = A.beam_stack_search(inst.graph, inst.start, inst.goal, 1, max_expansions=100000)
    assert capped.capped and capped.solutions == [] and capped.path == []
    w2 = A.beam_stack_search(inst.graph, inst.start, inst.goal, 2)
    w3 = A.beam_stack_search(inst.graph, inst.start, inst.goal, 3)
    assert w2.proved and w3.proved and w2.expansions == 643 and w3.expansions == 84 and astar.expansions == 37
