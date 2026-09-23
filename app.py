"""Beam-Stack Search - Beam Search mit Rückweg: optimal bei jeder Breite, aber zu welchem Preis? - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Sechstes Stück der Heuristische-Baumsuche-Linie der "Konzepte"-Reihe, der Konvergenzpunkt von Beam Search und A*: Beam Search
begrenzt den Speicher durch die Breite, verliert dabei aber Pfade für immer (und scheitert bei schmaler Breite). Beam-Stack
Search (Zhou & Hansen, ICAPS 2005) springt zurück und macht daraus einen vollständigen, optimalen Anytime-Algorithmus. Was
kostet der Beweis, und was bleibt vom Speichervorteil? Muss gemessen werden, nicht angenommen.

Lauffähig mit: streamlit run app.py
"""

from dataclasses import replace

import streamlit as st

import bss_algorithm as A
import bss_constants as C
import bss_scenario as S
from bss_evaluation import SWEEP_LABELS, Settings, analyse, anytime_curves, sweep, tail
from bss_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from bss_visualization import (
    ASTAR_COLOR,
    BEAM_COLOR,
    BSS_COLOR,
    IDA_COLOR,
    build_anytime,
    build_instance,
    build_paths,
    build_revisits_bar,
    build_share_bars,
    build_solution_map,
    build_sweep,
    build_tradeoff,
)

st.set_page_config(page_title="Beam-Stack Search – Sebastian Hanisch", layout="wide")

TRAP_NAMES = list(S.TRAP_NODES.keys())


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=False)
def _curves(settings, widths):
    return anytime_curves(settings, widths)


@st.cache_data(show_spinner=False)
def _sweep(param, base):
    return sweep(param, base)


@st.cache_data(show_spinner=False)
def _tail(base):
    return tail(base)


@st.cache_data(show_spinner=False)
def _trap_trace(width, bound_width):
    inst = S.trap_instance()
    return A.beam_stack_search(inst.graph, inst.start, inst.goal, width, bound_width, keep_trace=True).trace


def _fmt_int(x):
    return f"{int(round(x)):,}".replace(",", ".")


st.title("🧭 Beam-Stack Search – Beam Search mit Rückweg: optimal bei jeder Breite, aber zu welchem Preis?")
st.markdown(
    """
**Sechstes Stück der Heuristische-Baumsuche-Linie** - der **Konvergenzpunkt** von Beam Search und A\\*. Beam Search begrenzt
den Speicher durch die Breite w, verliert dabei aber Pfade **für immer** - bei Breite 1 scheitert es in 40 % der Läufe (Größe 12) und
liefert bei schmaler Breite eine Lücke; die Geschwister-Demos haben das gemessen. A\\* ist optimal, hält aber die ganze Grenzmenge im Speicher.

**Beam-Stack Search** (Zhou & Hansen, ICAPS 2005) **springt zurück**: ein **Beam-Stack** merkt sich je Schicht, welchen f-Bereich
der Nachfolger schon zugelassen wurde, und kehrt zu Schichten zurück, in denen beschnitten wurde. Ergebnis: ein Anytime-Algorithmus,
der früh eine erste Lösung liefert (wie Beam Search), sie verbessert und am Ende das **Optimum beweist** - bei jeder Breite.
Was kostet der Beweis, und was bleibt vom Speichervorteil?
"""
)
st.caption(
    "Setzt auf [beam-search-demo](https://github.com/sebastian-hanisch/beam-search-demo) und [monobeam-demo](https://github.com/sebastian-hanisch/monobeam-demo) auf "
    "(derselbe Graph, dieselben Instanzen; Beam Search als Vergleich) und stellt die andere Speicher-Antwort der Linie, "
    "[IDA\\*](https://github.com/sebastian-hanisch/ida-star-demo), daneben. Noch nicht gebaute Geschwister: Diverse Beam Search, Monte Carlo Tree Search (MCTS)."
)

with st.expander("So funktioniert Beam-Stack Search", expanded=True):
    st.markdown(
        """
1. **Schichten und Breite:** wie Beam Search Schicht für Schicht (Schicht = Kantenzahl), je Schicht höchstens **w** Knoten - der beste
   nach f = g + h zuerst. Der erste Abstieg ist ein normales Beam Search.
2. **Beam-Stack:** je Schicht ein Element **[fmin, fmax)**: nur Nachfolger mit f in diesem Bereich (und f < **U**) kommen in die nächste Schicht.
   Wird beschnitten, wird fmax der kleinste Wert der verworfenen Knoten - der Rest bleibt "für später".
3. **Ziel gefunden:** die Kosten werden zur oberen Schranke **U**, die Suche läuft weiter (anytime). Knoten mit f ≥ U werden nie mehr betrachtet.
4. **Rücksprung:** ist die nächste Schicht leer, wird zur tiefsten Schicht zurückgesprungen, in der beschnitten wurde: ihr Bereich rutscht weiter
   (fmin := fmax), die Schicht wird neu expandiert. **Stack leer = das Optimum ist bewiesen.**
5. **Sonderfälle:** Breite ≥ größte Schicht = Breitensuche-Branch-and-Bound (kein Rücksprung); Breite 1 = Tiefensuche-Branch-and-Bound.
        """
    )

if C.PRESETS:
    st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
    preset_names = list(C.PRESETS.keys())
    for row in (preset_names[:4], preset_names[4:]):
        if not row:
            continue
        cols = st.columns(len(row))
        for col, name in zip(cols, row):
            with col:
                st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    network = st.radio("Instanz", options=["grid", "trap"], format_func=lambda n: "Raster" if n == "grid" else "Handgebaute Heuristik-Falle",
                        key="network_select", help="Die Falle ist ein fester, von Hand gebauter Graph - Rastergröße/Hindernisdichte/Seed wirken dort nicht.")
    if network == "grid":
        side = st.slider("Rastergröße (Seitenlänge)", *bounds("side_slider"), key="side_slider",
                          help="Bei Breite 1 wächst der Aufwand mit der Größe stark (Größe 16: im Median 352x A*, 20 % der Läufe bei 300 000 Expansionen gekappt).")
        obstacle_pct = st.slider("Hindernisdichte [%]", *bounds("obstacle_slider"), key="obstacle_slider", step=C.OBSTACLE_STEP,
                                  help="Bei dichten Hindernissen scheitert Beam Search häufig (Breite 2, 30 %: 60 % der Läufe), BSS beweist in 100 %.")
        seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
        st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    else:
        side, obstacle_pct, seed = C.DEFAULT_SIDE, C.DEFAULT_OBSTACLE, C.DEFAULT_SEED
    width = st.select_slider("Breite w", options=list(C.WIDTHS), key="width_select",
                             help="Höchstens so viele Knoten je Schicht. Breite 1 = Tiefensuche-Branch-and-Bound, Breite ≥ größte Schicht = kein Rücksprung.")
    bound_width = st.select_slider("Startschranke: Beam Search der Breite", options=list(C.BOUND_WIDTHS), key="bound_select", format_func=lambda b: "keine" if b == 0 else str(b),
                                   help="Ein vorab laufendes Beam Search liefert die obere Schranke U (seine Expansionen zählen mit). Bei Breite 1 spart das im Median 37 %, bei Breite 4 kostet es mehr.")
    cap = st.select_slider("Expansions-Obergrenze", options=list(C.CAPS), key="cap_select", format_func=_fmt_int,
                           help="Sicherheitsnetz: bei Erreichen bricht BSS ab, die beste Lösung bis dahin bleibt gültig, ist aber nicht bewiesen.")

sync_query_params({"network_select": network, "side_slider": int(side), "obstacle_slider": int(obstacle_pct), "seed_input": int(seed),
                   "width_select": int(width), "bound_select": int(bound_width), "cap_select": int(cap)})

settings = Settings(network, int(side), int(obstacle_pct), int(seed), int(width), int(bound_width), int(cap))
with st.spinner("Rechne..."):
    a = _analysis(settings)
bss, beam = a.bss, a.beam
names = TRAP_NAMES if network == "trap" else None

# --- Beam-Stack Search in Aktion ---------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Beam-Stack Search in Aktion")
STEP_LABELS = {1: "1 · Instanz", 2: "2 · Lösungsfolge", 3: "3 · Ergebnis"}
step = st.select_slider("Schritt", options=list(STEP_LABELS), key="bss_step", format_func=lambda s: STEP_LABELS[s])

if step == 1:
    if network == "trap":
        st.markdown(f"**{a.inst.graph.n} Knoten** (Start, Ziel, ein Köder mit Sackgasse und ein Umweg)")
    else:
        st.markdown(f"**{a.inst.graph.n} Zellen** ({len(a.inst.blocked_xy)} Hindernisse), Start (grün) und Ziel (rot)")
    st.plotly_chart(build_instance(a.inst, names), width="stretch", key="s1_map")
elif step == 2:
    n_sol = len(bss.solutions)
    if n_sol == 0:
        st.warning("BSS hat innerhalb der Obergrenze keine Lösung gefunden.")
    else:
        if n_sol > 1:
            if "bss_solution" in st.session_state:
                st.session_state["bss_solution"] = min(max(1, int(st.session_state["bss_solution"])), n_sol)
            k = st.slider("Lösung", 1, n_sol, key="bss_solution", help="Jede neue Lösung ist kürzer als die vorige (die obere Schranke U sinkt).")
        else:
            k = 1
        exp_k, cost_k, _path = bss.solutions[k - 1]
        gap_k = 100.0 * (cost_k - a.ucs.cost) / a.ucs.cost
        st.markdown(
            f"**Lösung {k} von {n_sol}:** {cost_k:.2f} km (Lücke **{gap_k:.2f} %**), gefunden nach **{_fmt_int(exp_k)} Expansionen**"
            + f" ({exp_k / a.astar.expansions:.2f}x A\\*)"
            + (" - die letzte Lösung ist das " + ("**bewiesene Optimum** (nach insgesamt " + _fmt_int(bss.expansions) + " Expansionen)." if bss.proved else "beste bis zur Obergrenze, **nicht bewiesen**.") if k == n_sol else "")
        )
        st.plotly_chart(build_solution_map(a.inst, bss.solutions, k, names), width="stretch", key=f"s2_map_{k}")
else:
    if bss.path:
        beam_txt = "gescheitert (kein Pfad)" if beam.failed else f"{beam.cost:.2f} km"
        st.markdown(f"**BSS:** {bss.cost:.2f} km" + (" (bewiesen optimal)" if bss.proved else " (**nicht bewiesen**)") + f" – **Beam Search** (Breite {settings.width}): {beam_txt} – **Optimum:** {a.ucs.cost:.2f} km")
    else:
        st.warning("BSS hat innerhalb der Obergrenze keine Lösung gefunden.")
    st.plotly_chart(build_paths(a.inst, bss.path, [] if beam.failed else beam.path, a.astar.path, names), width="stretch", key="s3_map")

st.markdown("---")

# --- Ergebnis ----------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Was der Beweis kostet")
st.caption(
    "**Exp. bis Beweis / A\\*:** Expansionen bis der Beam-Stack leer ist (bei Abbruch nur eine Untergrenze, \"≥\"). **Speicher A\\* / BSS:** von A\\* gespeicherte Knoten "
    "durch die Spitze der von BSS gespeicherten (alle Schichten der aktuellen Tiefe); über 1 heißt, BSS braucht weniger Speicher. Rücksprünge in diesem Lauf: " + _fmt_int(bss.backtracks) + "."
)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Status", "gekappt" if bss.capped else "bewiesen", delta=f"{len(bss.solutions)} Lösungen", delta_color="off")
m2.metric("Exp. bis Beweis / A*", ("≥ " if bss.capped else "") + f"{a.total_ratio:.1f}x", delta=f"{_fmt_int(bss.expansions)} gegen {a.astar.expansions}", delta_color="off")
m3.metric("Speicher A* / BSS", f"{a.memory_ratio:.1f}x", delta=f"{a.astar.stored} gegen {bss.peak_stored}", delta_color="off")
best_gap = 100.0 * (bss.cost - a.ucs.cost) / a.ucs.cost if bss.path else float("nan")
m4.metric(f"Beam (Breite {settings.width})", "kein Pfad" if beam.failed else f"{a.beam_gap:.2f} %", delta="BSS: " + ("keine" if not bss.path else f"{best_gap:.2f} %"), delta_color="off")

st.markdown("---")

# --- Anytime -----------------------------------------------------------------------------------------------------------------------------------

st.markdown("## ⏱️ Anytime: früh eine Lösung, später der Beweis")
st.caption(
    "Kosten der besten bisher gefundenen Lösung über die kumulierten Expansionen (logarithmisch), je Breite eine Kurve. **x** = Optimum bewiesen, offener Kreis = "
    "gekappt. Gestrichelt: Optimum; senkrecht gepunktet: Expansionen von A\\*; Raute: Beam Search der gewählten Breite (kein Zurück - ein Punkt, oder gar keiner, wenn es scheitert)."
)
curve_widths = tuple(sorted(set(C.CURVE_WIDTHS) | {settings.width}))
with st.spinner("Rechne die Anytime-Kurven..."):
    curves = _curves(settings, curve_widths)
beam_point = None if beam.failed else (beam.expansions, beam.cost)
st.plotly_chart(build_anytime(curves, beam_point, highlight=settings.width), width="stretch", key="anytime")
if bss.revisits and bss.backtracks:
    st.markdown("**Wohin wurde zurückgesprungen?** (Breite " + str(settings.width) + ")")
    st.plotly_chart(build_revisits_bar(bss.revisits), width="stretch", key="revisits")
    st.caption("Wie bei Tiefensuche wird vor allem in die tieferen Schichten zurückgesprungen - dort ist am meisten beschnitten worden.")

st.markdown("---")

# --- Beam-Stack Schritt für Schritt (Falle) -------------------------------------------------------------------------------------------------------

if network == "trap":
    st.subheader("🔍 Der Beam-Stack Schritt für Schritt")
    trace = _trap_trace(settings.width, settings.bound_width)
    EVENT_LABELS = {"start": "Start: Schicht 0 = {Start}", "descend": "neue Schicht erzeugt", "solution": "Ziel gefunden - U sinkt", "backtrack": "Rücksprung: Bereich der obersten Schicht verschoben",
                    "done": "Stack leer: Optimum bewiesen"}

    def fmt_key(key):
        if key[0] == float("-inf"):
            return "0"
        if key[0] == float("inf"):
            return "U"
        return f"{key[0]:.2f} ({TRAP_NAMES[key[1]]})"

    if len(trace) > 1:
        if "trace_step" in st.session_state:
            st.session_state["trace_step"] = min(max(1, int(st.session_state["trace_step"])), len(trace))
        t = st.slider("Schritt im Verlauf", 1, len(trace), key="trace_step")
    else:
        t = 1
    event, ell, items, U, layer_states = trace[t - 1]
    st.markdown(f"**Schritt {t} von {len(trace)}: {EVENT_LABELS[event]}** - obere Schranke U = " + ("∞" if U == float("inf") else f"{U:.2f}"))
    rows = ["| Schicht | Knoten (Beam, sortiert nach f) | Beam-Stack-Element [fmin, fmax) |", "|---|---|---|"]
    for i, states in enumerate(layer_states):
        item = items[i] if i < len(items) else None
        rows.append(f"| {i}{' ◀' if i == ell else ''} | {', '.join(TRAP_NAMES[s] for s in states)} | " + (f"[{fmt_key(item[0])}, {fmt_key(item[1])})" if item else "-") + " |")
    st.markdown("\n".join(rows))
    st.caption("◀ = Schicht, die als Nächstes expandiert wird. Ein fmax < U bedeutet: in dieser Schicht wurde beschnitten, dorthin wird beim Rücksprung zurückgekehrt.")
    st.markdown("---")

# --- Sweeps ------------------------------------------------------------------------------------------------------------------------------------

if network == "grid":
    st.subheader("📐 Speicher-Zeit-Tausch und Sweeps")
    base_sweep = replace(settings, seed=0)
    if st.button("Speicher-Zeit-Diagramm berechnen (Breiten 1-24, 5 feste Instanzen)", key="tradeoff_start"):
        st.session_state["tradeoff_done"] = st.session_state.get("tradeoff_done", set()) | {base_sweep}
    if base_sweep in st.session_state.get("tradeoff_done", set()):
        with st.spinner("Rechne die Breiten-Sweeps..."):
            rows_w = _sweep("width", base_sweep)
        ida_point = (rows_w[0]["ida_memory_ratio"], rows_w[0]["ida_factor"])
        st.plotly_chart(build_tradeoff(rows_w, ida_point), width="stretch", key="tradeoff")
        st.caption(
            "Wie Tab. 1 des Papers: je Breite ein Punkt (Median über 5 feste Instanzen, Seeds 100000–100004). Rechts = weniger Speicher als A\\*, oben = mehr Expansionen. "
            + ("IDA\\* ist bei dieser Rastergröße gekappt - sein Punkt zeigt nur eine Untergrenze der Expansionen (und ohne Speicher-Verhältnis, wenn alle Läufe gekappt sind). " if rows_w[0]["ida_capped_share"] > 0 else "")
            + "Ab Breite ≈ 6 braucht BSS nicht mehr weniger Speicher als A\\*."
        )

    sweep_param = st.selectbox("Welcher Regler soll durchgefahren werden?", list(SWEEP_LABELS), format_func=lambda k: SWEEP_LABELS[k], key="sweep_select")
    metric = st.radio("Kennzahl", options=["ratio", "memory", "gap", "anytime", "shares"],
                       format_func=lambda k: {"ratio": "Expansionen bis Beweis / A*", "memory": "Speicher A* / BSS", "gap": "Lücke der ersten Lösung", "anytime": "Anytime (erste / ≤ 1 % / optimal / Beweis)",
                                              "shares": "bewiesen / gekappt / Beam scheitert (%)"}[k], key="sweep_metric", horizontal=True)
    if st.button("Sweep über 5 feste Instanzen berechnen (kann einige Sekunden dauern)", key="sweep_start"):
        st.session_state["sweep_done"] = st.session_state.get("sweep_done", set()) | {(sweep_param, base_sweep)}
    if (sweep_param, base_sweep) in st.session_state.get("sweep_done", set()):
        with st.spinner("Rechne den Sweep über 5 feste Instanzen..."):
            rows_sweep = _sweep(sweep_param, base_sweep)
        label = SWEEP_LABELS[sweep_param]
        if metric == "shares":
            st.plotly_chart(build_share_bars(rows_sweep, label), width="stretch", key="sweep_shares")
        elif metric == "ratio":
            st.plotly_chart(build_sweep(rows_sweep, label, [("total_ratio", "Beam-Stack Search", BSS_COLOR), ("ida_factor", "IDA* (gekappt: Untergrenze)", IDA_COLOR)], "Expansionen / A* (log)", log_y=True, ref_line=1.0, ref_label="so viel wie A*"),
                            width="stretch", key="sweep_ratio")
        elif metric == "memory":
            st.plotly_chart(build_sweep(rows_sweep, label, [("memory_ratio", "Beam-Stack Search", BSS_COLOR)], "Speicher A* / BSS", ref_line=1.0, ref_label="so viel wie A*"), width="stretch", key="sweep_memory")
        elif metric == "gap":
            st.plotly_chart(build_sweep(rows_sweep, label, [("first_gap", "BSS: erste Lösung", BSS_COLOR), ("beam_gap", "Beam Search (nur gelöste Läufe)", BEAM_COLOR)], "Lücke zum Optimum (%)"), width="stretch", key="sweep_gap")
        else:
            st.plotly_chart(build_sweep(rows_sweep, label, [("first_ratio", "erste Lösung", "#7b3fbf"), ("onepct_ratio", "Lücke ≤ 1 %", "#f58518"), ("optimal_ratio", "optimale Lösung", "#54a24b"), ("total_ratio", "Beweis", BSS_COLOR)],
                                        "Expansionen / A* (log)", log_y=True, ref_line=1.0, ref_label="so viel wie A*"), width="stretch", key="sweep_anytime")
        st.caption(
            "Median über 5 feste Instanzen (Seeds 100000–100004), Band = Minimum bis Maximum. Bei gekappten Läufen ist der Faktor nur eine Untergrenze; der Balken-Modus zeigt, "
            "in wie vielen Läufen der Beweis gelang und wie oft Beam Search scheiterte."
        )

    st.markdown("---")

    st.subheader("🔬 Der Median täuscht: wie schwer ist der Schwanz?")
    st.caption(
        "Expansionen bis zum Beweis relativ zu A\\* über 40 feste Instanzen (Seeds 200000–200039) mit den Rastergrößen/Hindernissen der Seitenleiste, je Breite 1–4. "
        "Breite 1 ist Tiefensuche: meist schnell, aber mit einem schweren Schwanz - gekappte Läufe zählen mit ihrer Untergrenze. Bei Breite 1 und großen Rastern kann die Rechnung "
        "mehrere Minuten dauern (Obergrenze in der Seitenleiste senken)."
    )
    key_tail = replace(settings, seed=0, width=C.DEFAULT_WIDTH)
    if st.button("Ausreißer über 40 feste Instanzen messen", key="tail_start"):
        st.session_state["tail_done"] = st.session_state.get("tail_done", set()) | {key_tail}
    if key_tail in st.session_state.get("tail_done", set()):
        with st.spinner("Rechne 40 Instanzen x 4 Breiten..."):
            tail_res = _tail(key_tail)
        rows_md = ["| Breite | Median | 75. Perzentil | 90. Perzentil | Maximum | gekappt | ganz ohne Lösung |", "|---|---|---|---|---|---|---|"]
        for w, r in tail_res.items():
            rows_md.append(f"| {w} | {r['median']:.1f}x | {r['p75']:.1f}x | {r['p90']:.1f}x | {r['max']:.0f}x | {r['capped_share']:.0f} % | {r['no_solution_share']:.0f} % |")
        st.markdown("\n".join(rows_md))
        st.caption(f"Rastergröße {settings.side}, Hindernisdichte {settings.obstacle_pct} %, Obergrenze {_fmt_int(settings.cap)} Expansionen, Startschranke {'keine' if settings.bound_width == 0 else settings.bound_width}.")

    st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Beam Search scheitert bei schmaler Breite** | BSS nicht: bei jeder Breite wird das Optimum gefunden und bewiesen (Raster, Falle und 1500 zufällige Graphen im Test). Beam Search scheitert bei Breite 1 in 40 % der Läufe (Größe 12), BSS beweist in 100 %. | **Beam Stack Search** (diese Demo) |
| **Der Beweis ist billig** | Nein. Bei Breite 1/2/4 braucht er im Median 87.5 / 17.0 / 2.7 Mal so viele Expansionen wie A\\* (Größe 12); bei Größe 16 und Breite 1 sind 20 % der Läufe bei 300 000 Expansionen gekappt. Die erste Lösung kommt früh (nach 0.26x bzw. 0.47x A\\*), die optimale nach 40x bzw. 4.9x - bei Breite 1 verbraucht der Beweis noch einmal etwa so viel wie das Finden. | Startschranke (siehe unten), größere Breite |
| **Der Median genügt** | Nein, bei Breite 1: über 40 Instanzen (Größe 12) Median 49x, 90. Perzentil 1109x, Maximum 4054x A\\*, und 4 von 40 Läufen (10 %) bleiben bei 300 000 Expansionen ohne jede Lösung (Tiefensuche in einer Sackgassen-Region; Extrembeispiel Größe 8, Seed 200001: A\\* 37 Expansionen, BSS Breite 1 573 409, Breite 2 643). Breite 2-4 ist gutartig (Maximum 35x / 30x / 8x, nichts gekappt). Die frühe erste Lösung gilt also im Median, nicht garantiert. | größere Breite (2-4) |
| **Beam-Stack spart Speicher** | Nur bei schmaler Breite: 4.4x / 2.4x / 1.4x weniger Speicher als A\\* bei Breite 1/2/4, ab Breite ≈ 6 nicht mehr (Breite 24: 0.9x). Gezählt werden alle Schichten der aktuellen Tiefe (Beam-Stack-Modell w·Tiefe). Die Divide-and-Conquer-Rekonstruktion des Papers (4w-Speicher, tiefenunabhängig) und der Externspeicher sind hier **nicht gebaut**. | Divide-and-Conquer-Beam-Stack (Paper, nicht gebaut) |
| **BSS schlägt IDA\\*** | Auf diesem Raster ja: bei Größe 8 braucht IDA\\* im Median 705x A\\*, BSS bei Breite 1 9.1x (gleiche Speicherersparnis 3.0x); ab Größe 12 bricht IDA\\* bei 300 000 Expansionen ab (80-100 % der Läufe), BSS beweist bei Breite 2 bis Größe 16 in 100 %. Warum genau, wird nicht isoliert: BSS hat eine obere Schranke und Dominanz-Duplikate, IDA\\* nur die Schwelle. | - |
| **Eine Startschranke hilft** | Nur bei schwachem ersten Abstieg: bei Breite 1 sinken die Expansionen von 87.5x auf 55x A\\*, bei Breite 4 steigen sie von 2.7x auf 3.3-3.8x. | - |
| **Synthetische Instanzen** | Ein Raster mit Jitter, Vierer-Nachbarschaft, keine Zeitfenster, keine gerichteten Kanten. Andere Graphstrukturen wurden nicht gemessen; Größen bis 20 im Regler. | Echte Straßennetze (hier nicht gebaut) |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Schichten.** $L_0 = \{s\}$; $L_{t+1}$ enthält die $w$ besten (Schlüssel $(f, \text{Zustand})$) Nachfolger von $L_t$, je Zustand mit kleinstem $g$,
mit $\text{fmin}_t \le \text{Schlüssel} < \text{fmax}_t$ und $f < U$; Dominanz: ein Zustand, der in einer gespeicherten früheren Schicht mit $g' \le g$ steht, wird verworfen.

**Beam-Stack.** Element $t$ = $[\text{fmin}_t, \text{fmax}_t)$, anfangs $[0, \infty)$. Wird $L_{t+1}$ beschnitten: $\text{fmax}_t$ = kleinster Schlüssel der
verworfenen Knoten. Zielfund: $U = \min(U, g)$.

**Rücksprung.** Leere Schicht: Elemente mit $\text{fmax} \ge U$ vom Stack entfernen (Schichten "backtracking-complete"); am obersten Element $\text{fmin} := \text{fmax}$,
$\text{fmax} := \infty$, diese Schicht neu expandieren. Stack leer $\Rightarrow$ beste Lösung optimal (Satz 1, zulässiges $h$).

**Sonderfälle, im Test nachgewiesen.** $w \ge$ größte Schicht: kein Rücksprung, gleiche Expansionen wie unbegrenzt; $w = 1$: jede Schicht höchstens ein Knoten.

**Literatur.** Zhou, R., & Hansen, E. A. (2005). *Beam-Stack Search: Integrating Backtracking with Beam Search.* Proceedings of the 15th International Conference on Automated Planning and
Scheduling (ICAPS). Korf, R. E. (1985). *Depth-first iterative-deepening: An optimal admissible tree search.* Artificial Intelligence, 27(1), 97-109 (IDA\*-Vergleich).

Implementiert in `bss_algorithm.py` (Suchkerne, `beam_search`, `ida_star` aus den Geschwister-Demos, `beam_stack_search` neu), `bss_graph.py`/`bss_scenario.py`
(Graph, Raster- und Fallen-Instanz), `bss_evaluation.py` (Kennzahlen, Sweeps, Anytime-Kurven).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
