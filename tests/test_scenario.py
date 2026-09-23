import numpy as np
import pytest

import bss_graph as G
import bss_scenario as S


@pytest.mark.parametrize("seed", range(30))
def test_start_and_goal_are_always_connected(seed):
    inst = S.grid_instance(side=10, obstacle_pct=35, seed=seed)
    assert _bfs_connected(inst.graph, inst.start, inst.goal)


def _bfs_connected(graph, start, goal):
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        if u == goal:
            return True
        for v in graph.neighbors[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return goal in seen


@pytest.mark.parametrize("seed", range(10))
def test_edge_weights_match_euclidean_distance_between_endpoints(seed):
    inst = S.grid_instance(side=10, obstacle_pct=20, seed=seed)
    xy = inst.graph.xy
    for u in range(inst.graph.n):
        for v, w in zip(inst.graph.neighbors[u], inst.graph.weights[u]):
            expected = float(np.hypot(*(xy[u] - xy[v])))
            assert w == pytest.approx(expected, abs=1e-9)


def test_higher_obstacle_percent_blocks_more_cells_on_average():
    low = [len(S.grid_instance(side=14, obstacle_pct=5, seed=s).blocked_xy) for s in range(10)]
    high = [len(S.grid_instance(side=14, obstacle_pct=35, seed=s).blocked_xy) for s in range(10)]
    assert np.mean(high) > np.mean(low)


def test_zero_obstacle_percent_leaves_every_cell_open():
    inst = S.grid_instance(side=10, obstacle_pct=0, seed=1)
    assert len(inst.blocked_xy) == 0
    assert inst.graph.n == 100


def test_no_isolated_edges_shorter_than_zero():
    inst = S.grid_instance(side=12, obstacle_pct=30, seed=7)
    for u in range(inst.graph.n):
        for w in inst.graph.weights[u]:
            assert w > 0


def test_trap_instance_has_the_expected_shape():
    inst = S.trap_instance()
    assert inst.graph.n == 8
    assert _bfs_connected(inst.graph, inst.start, inst.goal)


def test_path_cost_matches_a_hand_walked_path_on_the_trap_instance():
    inst = S.trap_instance()
    names = list(S.TRAP_NODES.keys())
    idx = {n: i for i, n in enumerate(names)}
    detour_path = [idx[n] for n in ("Start", "Umweg1", "Umweg2", "Ziel")]
    cost = G.path_cost(inst.graph, detour_path)
    expected = sum(np.hypot(*(np.array(S.TRAP_NODES[a]) - np.array(S.TRAP_NODES[b])))
                   for a, b in zip(("Start", "Umweg1", "Umweg2"), ("Umweg1", "Umweg2", "Ziel")))
    assert cost == pytest.approx(expected, abs=1e-9)
