"""Unabhängiges Orakel für Beam-Stack Search auf ALLGEMEINEN Graphen (gerichtet und ungerichtet, mit Zyklen, zulässige aber
inkonsistente Heuristik; die vorhandenen Zufallstests laufen nur auf Schichtgraphen): (1) Kosten == Brute-Force-Optimum und
`proved` bei jeder Breite und mit/ohne Startschranke; (2) eine eigene Neuimplementierung nach Zhou & Hansen (Dict-Schichten, Liste
[fmin, fmax) als Beam-Stack) liefert dieselben Expansionen, Rücksprünge und dieselbe Anytime-Folge; (3) auf Rastern expandiert
BSS mindestens jeden Knoten mit g* + h < C* (Untergrenze, unabhängig per networkx-Dijkstra)."""

import math
import random

import numpy as np
import pytest

import bss_algorithm as A
import bss_graph as G
import bss_scenario as S

INF = math.inf


def _brute_force(adj, s, t):
    best, stack = INF, [(s, frozenset([s]), 0.0)]
    while stack:
        u, seen, c = stack.pop()
        if u == t:
            best = min(best, c)
            continue
        stack.extend((v, seen | {v}, c + w) for v, w in adj[u] if v not in seen)
    return best


def _distances_to(adj, n, t):
    radj = [[] for _ in range(n)]
    for u in range(n):
        for v, w in adj[u]:
            radj[v].append((u, w))
    d, todo = [INF] * n, set(range(n))
    d[t] = 0.0
    while todo:
        u = min(todo, key=lambda x: d[x])
        if d[u] == INF:
            break
        todo.discard(u)
        for v, w in radj[u]:
            d[v] = min(d[v], d[u] + w)
    return d


def _reference_bss(adj, s, t, width, h):
    U, sols, exp, bt = INF, [], 0, 0
    layers, stack = [{s: (0.0, h[s])}], [[(-INF, -1), (INF, 0)]]
    while True:
        ell = len(layers) - 1
        lo, hi = stack[ell]
        cand = {}
        for v in sorted(layers[ell], key=lambda x: (layers[ell][x][1], x)):
            g, f = layers[ell][v]
            if v == t:
                if g < U:
                    U = g
                    sols.append((exp, g))
                continue
            if f >= U:
                continue
            exp += 1
            for w, c in adj[v]:
                g2, f2 = g + c, g + c + h[w]
                if f2 >= U or not (lo <= (f2, w) < hi):
                    continue
                if any(w in layers[j] and layers[j][w][0] <= g2 for j in range(ell + 1)):
                    continue
                if w not in cand or g2 < cand[w][0]:
                    cand[w] = (g2, f2)
        order = sorted(cand, key=lambda x: (cand[x][1], x))
        if len(order) > width:
            stack[ell][1] = (cand[order[width]][1], order[width])
            order = order[:width]
        if order:
            layers.append({x: cand[x] for x in order})
            stack.append([(-INF, -1), (INF, 0)])
            continue
        while stack and stack[-1][1][0] >= U:
            stack.pop()
            layers.pop()
        if not stack:
            return U, sols, exp, bt
        stack[-1][0], stack[-1][1] = stack[-1][1], (INF, 0)
        bt += 1


def _random_instance(seed):
    rnd = random.Random(seed)
    n, directed, p = rnd.randint(3, 8), seed % 2 == 0, rnd.choice([0.25, 0.4, 0.6])
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j or rnd.random() >= p or (not directed and i > j):
                continue
            w = float(rnd.randint(1, 6))
            adj[i].append((j, w))
            if not directed:
                adj[j].append((i, w))
    s, t = rnd.sample(range(n), 2)
    dt = _distances_to(adj, n, t)
    h = [0.0 if dt[v] == INF else math.floor(dt[v] * rnd.uniform(0.2, 1.0)) for v in range(n)]
    h[t] = 0.0
    graph = G.Graph(np.zeros((n, 2)), tuple(tuple(v for v, _ in sorted(a)) for a in adj), tuple(tuple(w for _, w in sorted(a)) for a in adj))
    return n, adj, graph, s, t, h


@pytest.mark.parametrize("seed", range(150))
def test_bss_on_general_graphs_matches_brute_force_and_reference_implementation(seed):
    n, adj, graph, s, t, h = _random_instance(seed)
    best = _brute_force(adj, s, t)
    for width in (1, 2, 3, 100):
        result = A.beam_stack_search(graph, s, t, width, h=np.array(h))
        assert result.proved and not result.capped
        assert result.cost == best or result.cost == pytest.approx(best, abs=1e-9)
        cost, sols, exp, bt = _reference_bss(adj, s, t, width, h)
        assert (cost, exp, bt) == (result.cost, result.expansions, result.backtracks)
        assert sols == [(e, c) for e, c, _p in result.solutions]
        bounded = A.beam_stack_search(graph, s, t, width, bound_width=2, h=np.array(h))
        assert bounded.proved and (bounded.cost == best or bounded.cost == pytest.approx(best, abs=1e-9))


@pytest.mark.parametrize("seed", range(12))
def test_bss_expands_at_least_every_node_with_f_star_below_the_optimum(seed):
    nx = pytest.importorskip("networkx")
    inst = S.grid_instance(7, (seed % 4) * 12, 7000 + seed)
    g = inst.graph
    H = nx.Graph()
    for u in range(g.n):
        for v, w in zip(g.neighbors[u], g.weights[u]):
            H.add_edge(u, v, weight=w)
    opt = nx.dijkstra_path_length(H, inst.start, inst.goal)
    ds = nx.single_source_dijkstra_path_length(H, inst.start)
    h = A.heuristic(g.xy, inst.goal)
    must = sum(1 for v in range(g.n) if ds.get(v, 1e18) + h[v] < opt - 1e-9)
    for width in (1, 2, 4, 10**6):
        result = A.beam_stack_search(g, inst.start, inst.goal, width)
        assert result.proved and result.cost == pytest.approx(opt, abs=1e-9)
        assert result.expansions >= must
