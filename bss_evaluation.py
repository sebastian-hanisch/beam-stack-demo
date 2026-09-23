"""Auswertung: was kostet Beam-Stack Search den Optimalitätsbeweis, und was spart es an Speicher? Vergleich mit Beam Search
(f-Rang, gleiche Breite, kein Zurück), A* (Speicher-hungrig, optimal) und IDA* (die andere Speicher-Antwort) auf demselben Graphen.

Kennzahlen (Median mit Minimum/Maximum über die 5 festen Sweep-Instanzen, Seeds 100000-100004, deterministisch):

- **Expansions-Faktor** = Expansionen bis zum BEWEIS der Optimalität (Stack leer) / Expansionen A*. Bei gekappten Läufen
  (Obergrenze erreicht) nur eine UNTERGRENZE - gekappte Läufe werden deshalb getrennt als Anteil ausgewiesen, der Faktor
  wird mit und ohne sie berichtet.
- **Speicher-Verhältnis** = von A* gespeicherte Knoten / Spitze der von BSS gespeicherten Knoten (alle Schichten der aktuellen
  Tiefe; über 1 heißt: BSS braucht weniger Speicher als A*).
- **Anytime**: Lücke der ersten Lösung (gegen Beam Search gleicher Breite) und Expansionen bis zur ersten Lösung / bis Lücke <= 1 % /
  bis zur ersten optimalen Lösung / bis zum Beweis, jeweils relativ zu A*.
- **IDA\\*** als Gegenstück: Expansions-Faktor und Speicher-Verhältnis (gekappt bei `IDA_CAP`).

Faktoren sind schief verteilt - deshalb Median mit Spannweite."""

from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np

import bss_algorithm as A
import bss_constants as C
import bss_scenario as S

INF = float("inf")


@dataclass(frozen=True)
class Settings:
    network: str = "grid"           # "grid" oder "trap"
    side: int = C.DEFAULT_SIDE
    obstacle_pct: int = C.DEFAULT_OBSTACLE
    seed: int = C.DEFAULT_SEED
    width: int = C.DEFAULT_WIDTH
    bound_width: int = 0            # 0 = keine Startschranke, sonst Breite des vorab laufenden Beam Search
    cap: int = C.DEFAULT_CAP


@lru_cache(maxsize=512)
def instance(side, obstacle_pct, seed):
    return S.grid_instance(side, obstacle_pct, seed)


def _instance(settings):
    return S.trap_instance() if settings.network == "trap" else instance(settings.side, settings.obstacle_pct, settings.seed)


@dataclass
class Analysis:
    settings: Settings
    inst: object
    bss: A.BSSResult
    beam: A.BeamResult
    astar: A.SearchResult
    ucs: A.SearchResult
    ida: A.IDAResult

    @property
    def proved(self):
        return self.bss.proved

    @property
    def found_optimal(self):
        return (not self.bss.capped) or self.bss.cost <= self.ucs.cost + 1e-9

    @property
    def total_ratio(self):
        """Expansionen BSS / A*; bei gekappten Läufen eine UNTERGRENZE."""
        return self.bss.expansions / self.astar.expansions

    @property
    def memory_ratio(self):
        return self.astar.stored / self.bss.peak_stored

    def _gap(self, cost):
        return 100.0 * (cost - self.ucs.cost) / self.ucs.cost

    @property
    def first_gap(self):
        """Lücke der ersten gefundenen Lösung in %; NaN, falls keine gefunden."""
        return self._gap(self.bss.solutions[0][1]) if self.bss.solutions else float("nan")

    @property
    def beam_gap(self):
        return float("nan") if self.beam.failed else self._gap(self.beam.cost)

    def expansions_until(self, gap_pct):
        """Expansionen bis zur ersten Lösung mit Lücke <= gap_pct; NaN, falls nie erreicht (z. B. gekappt)."""
        for exp, cost, _path in self.bss.solutions:
            if self._gap(cost) <= gap_pct + 1e-9:
                return float(exp)
        return float("nan")

    @property
    def ida_factor(self):
        return self.ida.expansions / self.astar.expansions

    @property
    def ida_memory_ratio(self):
        return self.astar.stored / self.ida.stored if not self.ida.capped else float("nan")


@lru_cache(maxsize=256)
def _references(network, side, obstacle_pct, seed):
    """A*, Uniform-Cost und IDA* hängen nicht von Breite/Startschranke ab - je Instanz nur einmal gerechnet."""
    inst = S.trap_instance() if network == "trap" else instance(side, obstacle_pct, seed)
    g, s, t = inst.graph, inst.start, inst.goal
    return A.a_star(g, s, t), A.uniform_cost_search(g, s, t), A.ida_star(g, s, t, C.IDA_CAP)


def analyse(settings):
    inst = _instance(settings)
    g, s, t = inst.graph, inst.start, inst.goal
    bss = A.beam_stack_search(g, s, t, settings.width, settings.bound_width, settings.cap)
    beam = A.beam_search(g, s, t, settings.width, "f")
    astar, ucs, ida = _references(settings.network, settings.side, settings.obstacle_pct, settings.seed)
    return Analysis(settings, inst, bss, beam, astar, ucs, ida)


# --- Sweeps --------------------------------------------------------------------------------------------------------------------------------------


def _median_range(values):
    values = [v for v in values if not np.isnan(v)]
    if not values:
        return float("nan"), float("nan"), float("nan")
    return float(np.median(values)), float(np.min(values)), float(np.max(values))


def run_config(base, seeds=C.SWEEP_SEEDS, **changes):
    s0 = replace(base, **changes)
    rows = [analyse(replace(s0, seed=seed)) for seed in seeds]
    n = len(rows)
    out = {
        "n_runs": n,
        "proved_share": 100.0 * sum(r.proved for r in rows) / n,
        "capped_share": 100.0 * sum(r.bss.capped for r in rows) / n,
        "optimal_found_share": 100.0 * sum(r.found_optimal and r.bss.cost <= r.ucs.cost + 1e-9 for r in rows) / n,
        "beam_failed_share": 100.0 * sum(r.beam.failed for r in rows) / n,
        "ida_capped_share": 100.0 * sum(r.ida.capped for r in rows) / n,
    }
    for key, values in (
        ("total_ratio", [r.total_ratio for r in rows]),                                               # Untergrenze bei gekappten Läufen
        ("total_ratio_proved", [r.total_ratio if r.proved else float("nan") for r in rows]),
        ("memory_ratio", [r.memory_ratio for r in rows]),
        ("first_gap", [r.first_gap for r in rows]),
        ("beam_gap", [r.beam_gap for r in rows]),
        ("first_ratio", [r.bss.solutions[0][0] / r.astar.expansions if r.bss.solutions else float("nan") for r in rows]),
        ("onepct_ratio", [r.expansions_until(1.0) / r.astar.expansions for r in rows]),
        ("optimal_ratio", [r.expansions_until(0.0) / r.astar.expansions for r in rows]),
        ("backtracks", [float(r.bss.backtracks) for r in rows]),
        ("ida_factor", [r.ida_factor for r in rows]),
        ("ida_memory_ratio", [r.ida_memory_ratio for r in rows]),
    ):
        out[key], out[f"{key}_lo"], out[f"{key}_hi"] = _median_range(values)
    out["astar_expansions"] = float(np.median([r.astar.expansions for r in rows]))
    out["astar_stored"] = float(np.mean([r.astar.stored for r in rows]))
    return out


SWEEP_VALUES = {"width": C.WIDTHS, "obstacle_pct": C.OBSTACLE_SWEEP, "side": C.SCALING_SIDES}
SWEEP_LABELS = {"width": "Breite w", "obstacle_pct": "Hindernisdichte (%)", "side": "Rastergröße (Seitenlänge)"}


def sweep(param, base=Settings(), values=None):
    values = SWEEP_VALUES[param] if values is None else values
    return [{"value": v, **run_config(base, **{param: v})} for v in values]


# --- Anytime-Kurven ------------------------------------------------------------------------------------------------------------------------------


def anytime_curves(settings, widths=C.CURVE_WIDTHS):
    """Je Breite die Anytime-Folge der EINEN Instanz von `settings`: Liste (kumulierte Expansionen, Kosten) der besten Lösung,
    dazu Gesamtexpansionen, bewiesen/gekappt. Referenzen: Beam (Breite gleich `settings.width`), A*, UCS-Optimum."""
    inst = _instance(settings)
    g, s, t = inst.graph, inst.start, inst.goal
    out = {}
    for w in widths:
        r = A.beam_stack_search(g, s, t, w, settings.bound_width, settings.cap)
        out[w] = {"points": [(e, c) for e, c, _p in r.solutions], "total": r.expansions, "proved": r.proved, "capped": r.capped,
                  "peak_stored": r.peak_stored, "backtracks": r.backtracks}
    astar = A.a_star(g, s, t)
    ucs = A.uniform_cost_search(g, s, t)
    return {"curves": out, "optimum": ucs.cost, "astar_expansions": astar.expansions, "astar_stored": astar.stored}


# --- Ausreißer (Schwanz der Aufwandsverteilung) --------------------------------------------------------------------------------------------------


@lru_cache(maxsize=512)
def _astar_only(network, side, obstacle_pct, seed):
    inst = S.trap_instance() if network == "trap" else instance(side, obstacle_pct, seed)
    return A.a_star(inst.graph, inst.start, inst.goal)


def tail(base, seeds=C.TAIL_SEEDS, widths=C.TAIL_WIDTHS, **changes):
    """Verteilung des Expansions-Faktors (BSS / A*) über viele feste Instanzen je Breite: Median, 75./90. Perzentil, Maximum (bei
    gekappten Läufen Untergrenze), Anteil gekappter Läufe und Anteil Läufe OHNE jede Lösung. Der Median allein verschweigt bei
    Breite 1 den schweren Schwanz (Tiefensuche)."""
    s0 = replace(base, **changes)
    out = {}
    for w in widths:
        ratios, capped, nosol = [], 0, 0
        for seed in seeds:
            inst = _instance(replace(s0, seed=seed))
            astar = _astar_only(s0.network, s0.side, s0.obstacle_pct, seed)
            r = A.beam_stack_search(inst.graph, inst.start, inst.goal, w, s0.bound_width, s0.cap)
            ratios.append(r.expansions / astar.expansions)
            capped += r.capped
            nosol += not r.solutions
        q = np.percentile(ratios, [50, 75, 90, 100])
        n = len(seeds)
        out[w] = {"n": n, "capped_share": 100.0 * capped / n, "no_solution_share": 100.0 * nosol / n,
                  "median": float(q[0]), "p75": float(q[1]), "p90": float(q[2]), "max": float(q[3])}
    return out
