"""Suchkerne - `_search`, `greedy_best_first`, `uniform_cost_search`, `a_star`, `beam_search` (beam-search-demo) und `ida_star`
(ida-star-demo) wortgleich kopiert (dort korrektheitsgeprüft; Vergleichsgrößen dieses Stücks; `beam_search` mit optionalem
expliziten Heuristik-Vektor `h`) und NEU `beam_stack_search`.

Beam-Stack Search (Zhou & Hansen, ICAPS 2005): Beam Search, das zurückspringt. Schichtweise Suche (Schicht = Kantenzahl), je
Schicht höchstens `width` Knoten. Der **Beam-Stack** hat je Schicht ein Element [fmin, fmax) über dem Schlüssel (f, Zustand):
für die nächste Schicht werden nur Nachfolger mit Schlüssel in [fmin, fmax) und f < U zugelassen (U = Kosten der besten bisher
gefundenen Lösung, anfangs unendlich). Wird eine Schicht auf `width` beschnitten (inadmissibles Pruning), wird fmax des Elements
der Vorgängerschicht der kleinste Schlüssel der verworfenen Knoten. Ein Zielfund setzt U und die Suche läuft weiter (anytime).
Ist die nächste Schicht leer, wird zurückgesprungen: vom Stack oben alle Elemente mit fmax >= U entfernen (Schicht
"backtracking-complete"); am obersten verbleibenden Element fmin := fmax, fmax := unbegrenzt, diese Schicht wird neu expandiert,
die tieferen werden neu erzeugt. Leerer Stack = die beste Lösung ist optimal (Satz 1 des Papers). Breite >= größte Schicht =
Breitensuche-Branch-and-Bound (kein Rücksprung), Breite 1 = Tiefensuche-Branch-and-Bound.

Startschranke: mit `bound_width > 0` läuft vorab ein Beam Search (f-Rang) dieser Breite; seine Lösung wird zum Inkumbent
(U) und seine Expansionen zählen mit. Ohne (0) ist U anfangs unendlich - die erste Lösung stammt dann aus dem Beam-artigen ersten Abstieg.

Duplikate: je Zustand innerhalb einer Schicht das kleinste g; zusätzlich Dominanz gegen alle gespeicherten früheren Schichten
(derselbe Zustand mit g' <= g dort) - das sichert die Terminierung auch mit U = unendlich. Speichermodell: alle Schichten der
aktuellen Tiefe (Beam-Stack-"dw"-Modell, hier "gespeicherte Knoten" = Summe der Schichtgrößen); Divide-and-Conquer-
Lösungsrekonstruktion und Externspeicher des Papers sind NICHT gebaut. `max_expansions` ist ein Sicherheitsnetz (`capped`):
dann bleibt die beste bis dahin gefundene Lösung gültig, aber ohne Optimalitätsbeweis. Deterministisch."""

import heapq
from dataclasses import dataclass, field

import numpy as np


def heuristic(xy, goal):
    """Euklidischer Abstand jedes Knotens zum Ziel - vektorisiert. Bei echten Kantengewichten (siehe
    `beam_scenario.py`) automatisch zulässig (Dreiecksungleichung)."""
    return np.hypot(*(xy - xy[goal]).T)


@dataclass
class SearchResult:
    path: list                  # Knotenfolge Start..Ziel, oder [] falls kein Pfad existiert
    cost: float                 # Summe der Kantengewichte entlang des Pfades
    expansions: int             # Zahl der expandierten Knoten (Effizienz-Kennzahl dieses Stücks)
    order: list = field(default_factory=list)     # Reihenfolge der expandierten Knoten (für die Schritt-Visualisierung)
    stored: int = 0             # Speicher-Kennzahl: gespeicherte Knoten am Ende (A*/UCS/GBFS: entdeckte Knoten; IDA*: max. Pfadtiefe)


def _search(graph, start, goal, priority_fn, relax=True):
    """`priority_fn(node, g_cost) -> float` bestimmt die Warteschlangen-Priorität. `g_cost` ist der bislang
    aufgelaufene Pfadwert zu `node` (für Uniform-Cost-Search gebraucht, von Greedy Best-First ignoriert).

    `relax`: ob ein noch nicht expandierter, aber schon entdeckter Knoten einen GÜNSTIGEREN Elternknoten
    bekommt, sobald ein billigerer Weg zu ihm gefunden wird (klassische Dijkstra-Relaxation - für
    Uniform-Cost-Search nötig, damit es tatsächlich optimal bleibt). Bei `relax=False` behält ein Knoten für
    immer den ERSTEN gefundenen Elternknoten (echtes "kein Backtracking" - der Kern der GBFS-Schwäche: eine
    Relaxation hier würde den gemessenen Qualitätsverlust künstlich kleinrechnen, da GBFS dann doch beiläufig
    von g(n) profitieren würde, obwohl es g(n) laut Definition komplett ignoriert)."""
    counter = 0
    frontier = [(priority_fn(start, 0.0), counter, start, 0.0)]
    came_from = {start: None}
    g_cost = {start: 0.0}
    visited = set()
    order = []

    while frontier:
        _priority, _c, node, g = heapq.heappop(frontier)
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        if node == goal:
            path = []
            cur = node
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return SearchResult(path, g, len(order), order, len(g_cost))
        for v, w in zip(graph.neighbors[node], graph.weights[node]):
            if v in visited:
                continue
            g_v = g + w
            is_new = v not in g_cost
            if is_new or (relax and g_v < g_cost[v]):
                g_cost[v] = g_v
                came_from[v] = node
                counter += 1
                heapq.heappush(frontier, (priority_fn(v, g_v), counter, v, g_v))

    return SearchResult([], float("inf"), len(order), order, len(g_cost))


def greedy_best_first(graph, start, goal):
    h = heuristic(graph.xy, goal)
    return _search(graph, start, goal, lambda node, g: h[node], relax=False)


def uniform_cost_search(graph, start, goal):
    return _search(graph, start, goal, lambda node, g: g, relax=True)


def a_star(graph, start, goal):
    h = heuristic(graph.xy, goal)
    return _search(graph, start, goal, lambda node, g: g + h[node], relax=True)


@dataclass
class BeamResult(SearchResult):
    failed: bool = False
    layers: int = 0
    per_layer: list = field(default_factory=list)    # [(Strahl, verworfene Kandidaten), ...] je Schicht
    peak_width: int = 0                              # größte Kandidatenzahl einer Schicht vor dem Beschneiden


def beam_search(graph, start, goal, width, rank="h", h=None):
    if width < 1:
        raise ValueError("width muss mindestens 1 sein")
    if rank not in ("h", "f"):
        raise ValueError("rank muss 'h' oder 'f' sein")
    if h is None:
        h = heuristic(graph.xy, goal)
    neighbors, weights = graph.neighbors, graph.weights
    beam = [start]
    g = {start: 0.0}
    parent = {start: None}
    expanded = set()
    discovered = {start}
    order = []
    per_layer = []
    peak = 1

    def build_path(node):
        path = []
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    if start == goal:
        return BeamResult([start], 0.0, 0, [], 1, False, 0, [], 1)

    while True:
        cand_g, cand_parent = {}, {}
        current = list(beam)
        for node in beam:
            expanded.add(node)
            order.append(node)
        for node in beam:
            for v, w in zip(neighbors[node], weights[node]):
                if v in expanded:
                    continue
                g_v = g[node] + w
                if v not in cand_g or g_v < cand_g[v]:
                    cand_g[v] = g_v
                    cand_parent[v] = node
        discovered.update(cand_g)
        peak = max(peak, len(cand_g))
        if goal in cand_g:
            parent[goal] = cand_parent[goal]
            per_layer.append((current, []))
            return BeamResult(build_path(goal), cand_g[goal], len(order), order, len(discovered), False, len(per_layer), per_layer, peak)
        if not cand_g:
            per_layer.append((current, []))
            return BeamResult([], float("inf"), len(order), order, len(discovered), True, len(per_layer), per_layer, peak)
        if rank == "h":
            ranked = sorted(cand_g, key=lambda v: (h[v], v))
        else:
            ranked = sorted(cand_g, key=lambda v: (cand_g[v] + h[v], v))
        beam, dropped = ranked[:width], ranked[width:]
        per_layer.append((current, dropped))
        for v in beam:
            g[v] = cand_g[v]
            parent[v] = cand_parent[v]


@dataclass
class IDAResult(SearchResult):
    iterations: int = 0
    per_iteration: list = field(default_factory=list)      # [(Schwelle, Expansionen in dieser Iteration), ...]
    expansion_counts: dict = field(default_factory=dict)   # Knoten -> wie oft expandiert (Mehrfachheit)
    capped: bool = False


def ida_star(graph, start, goal, max_expansions=1_000_000):
    h = heuristic(graph.xy, goal)
    neighbors, weights = graph.neighbors, graph.weights
    threshold = float(h[start])
    total = 0
    counts = {}
    per_iteration = []
    max_depth = 1

    while True:
        next_threshold = float("inf")
        expansions_here = 0
        path_nodes, path_g, path_idx = [], [], []
        on_path = set()
        found = capped = False

        def push(node, g):
            nonlocal next_threshold, total, expansions_here, found, capped, max_depth
            f = g + h[node]
            if f > threshold:
                if f < next_threshold:
                    next_threshold = f
                return
            if total >= max_expansions:
                capped = True
                return
            total += 1
            expansions_here += 1
            counts[node] = counts.get(node, 0) + 1
            path_nodes.append(node)
            path_g.append(g)
            path_idx.append(0)
            on_path.add(node)
            max_depth = max(max_depth, len(path_nodes))
            if node == goal:
                found = True

        push(start, 0.0)
        while path_nodes and not found and not capped:
            node = path_nodes[-1]
            i = path_idx[-1]
            if i == len(neighbors[node]):
                on_path.discard(path_nodes.pop())
                path_g.pop()
                path_idx.pop()
                continue
            path_idx[-1] = i + 1
            v = neighbors[node][i]
            if v in on_path:
                continue
            push(v, path_g[-1] + weights[node][i])

        per_iteration.append((threshold, expansions_here))
        if found:
            return IDAResult(list(path_nodes), path_g[-1], total, [], max_depth, len(per_iteration), per_iteration, counts, False)
        if capped:
            return IDAResult([], float("inf"), total, [], max_depth, len(per_iteration), per_iteration, counts, True)
        if next_threshold == float("inf"):
            return IDAResult([], float("inf"), total, [], max_depth, len(per_iteration), per_iteration, counts, False)
        threshold = next_threshold


@dataclass
class BSSResult(SearchResult):
    solutions: list = field(default_factory=list)    # anytime-Folge [(Expansionen bis dahin, Kosten, Pfad)], Kosten streng fallend
    proved: bool = False                             # Stack leer und nicht gekappt: beste Lösung (oder "kein Pfad") bewiesen
    capped: bool = False
    backtracks: int = 0
    revisits: list = field(default_factory=list)     # je Schicht: wie oft dorthin zurückgesprungen wurde
    peak_stored: int = 0                             # Spitze der Summe aller gespeicherten Schichtgrößen
    max_layer_size: int = 0                          # größte gespeicherte Schicht
    trace: list = field(default_factory=list)        # optional (keep_trace=True): (Ereignis, Schicht, Stack-Elemente, U, Zustände je Schicht)


def beam_stack_search(graph, start, goal, width, bound_width=0, max_expansions=300_000, h=None, keep_trace=False):
    if width < 1:
        raise ValueError("width muss mindestens 1 sein")
    if bound_width < 0:
        raise ValueError("bound_width muss >= 0 sein")
    if h is None:
        h = heuristic(graph.xy, goal)
    neighbors, weights = graph.neighbors, graph.weights
    INF = float("inf")
    MIN_KEY, INF_KEY = (-INF, -1), (INF, 0)

    if start == goal:
        return BSSResult([start], 0.0, 0, [], 1, [(0, 0.0, [start])], True, False, 0, [], 1, 1)

    U, best_path, best_cost = INF, [], INF
    solutions = []
    expansions = 0
    if bound_width > 0:
        beam = beam_search(graph, start, goal, bound_width, "f", h=h)
        expansions = beam.expansions
        if not beam.failed:
            U, best_path, best_cost = beam.cost, beam.path, beam.cost
            solutions.append((expansions, beam.cost, list(beam.path)))

    root = (start, 0.0, float(h[start]), None)
    layers = [[root]]
    layer_g = [{start: 0.0}]
    stack = [[MIN_KEY, INF_KEY]]                      # Beam-Stack: [fmin, fmax) je Schicht
    stored = 1
    peak, max_layer = 1, 1
    backtracks, revisits = 0, [0]
    trace = []
    capped = False

    def snapshot(event, ell):
        if keep_trace:
            trace.append((event, ell, [(tuple(item[0]), tuple(item[1])) for item in stack], U, [[nd[0] for nd in layer] for layer in layers]))

    def path_of(node):
        out = []
        while node is not None:
            out.append(node[0])
            node = node[3]
        out.reverse()
        return out

    snapshot("start", 0)
    while True:
        ell = len(layers) - 1
        fmin, fmax = stack[ell]
        cand = {}
        for node in layers[ell]:
            state, g, f, _p = node
            if state == goal:
                if g < U:
                    U, best_cost, best_path = g, g, path_of(node)
                    solutions.append((expansions, g, list(best_path)))
                    snapshot("solution", ell)
                continue
            if f >= U:
                continue
            expansions += 1
            if expansions > max_expansions:
                capped = True
                break
            for v, w in zip(neighbors[state], weights[state]):
                g_v = g + w
                f_v = g_v + float(h[v])
                if f_v >= U:
                    continue
                key = (f_v, v)
                if key < fmin or key >= fmax:
                    continue
                if any(v in layer_g[j] and layer_g[j][v] <= g_v for j in range(ell, -1, -1)):
                    continue
                prev = cand.get(v)
                if prev is None or g_v < prev[1]:
                    cand[v] = (v, g_v, f_v, node)
        if capped:
            break
        nodes = sorted(cand.values(), key=lambda n: (n[2], n[0]))
        if len(nodes) > width:
            stack[ell][1] = (nodes[width][2], nodes[width][0])          # kleinster verworfener Schlüssel
            nodes = nodes[:width]
        if nodes:
            layers.append(nodes)
            layer_g.append({n[0]: n[1] for n in nodes})
            stack.append([MIN_KEY, INF_KEY])
            if len(revisits) < len(layers):
                revisits.append(0)
            stored += len(nodes)
            peak = max(peak, stored)
            max_layer = max(max_layer, len(nodes))
            snapshot("descend", ell + 1)
            continue
        # nächste Schicht leer: zurückspringen
        while stack and stack[-1][1][0] >= U:
            stack.pop()
            stored -= len(layers.pop())
            layer_g.pop()
        if not stack:
            snapshot("done", 0)
            break
        ell = len(stack) - 1
        stack[ell][0] = stack[ell][1]
        stack[ell][1] = INF_KEY
        backtracks += 1
        revisits[ell] += 1
        snapshot("backtrack", ell)

    proved = not capped
    return BSSResult(best_path, best_cost, expansions, [], peak, solutions, proved, capped, backtracks, revisits, peak, max_layer, trace)
