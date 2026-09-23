"""Plotly-Abbildungen: Instanz (Raster oder Sackgassen-Falle mit Kanten und Namen), Lösungsfolge-Karte (die k-te verbesserte
Lösung), Pfad-Überlagerung, Anytime-Kurven (beste Kosten über kumulierte Expansionen, mehrere Breiten), Speicher-Zeit-Diagramm,
Sweeps, Bewiesen-/Gekappt-Anteile, Rücksprünge je Schicht. Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen
nicht zoomen."""

import numpy as np
import plotly.graph_objects as go

NODE_COLOR = "#4c78a8"
BLOCKED_COLOR = "#9d755d"
ASTAR_COLOR = "#4c78a8"
BSS_COLOR = "#e45756"
BEAM_COLOR = "#f58518"
IDA_COLOR = "#54a24b"
PALETTE = ["#7b3fbf", "#e45756", "#f58518", "#54a24b", "#4c78a8", "#b279a2", "#9d755d"]
INF = float("inf")


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height, legend_y=-0.1):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=legend_y), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _map_layout(fig, height=460):
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)
    return _base(fig, height)


def _is_trap(inst):
    return inst.side == 0


def _start_goal_trace(inst):
    xy = inst.graph.xy
    return [
        go.Scatter(x=[xy[inst.start, 0]], y=[xy[inst.start, 1]], mode="markers", marker=dict(size=16, symbol="star", color="#2ca02c", line=dict(width=1, color="white")), name="Start"),
        go.Scatter(x=[xy[inst.goal, 0]], y=[xy[inst.goal, 1]], mode="markers", marker=dict(size=16, symbol="star", color="#d62728", line=dict(width=1, color="white")), name="Ziel"),
    ]


def _background(fig, inst, names=None, alpha=0.35):
    xy = inst.graph.xy
    if _is_trap(inst):
        ex, ey = [], []
        for u in range(inst.graph.n):
            for v in inst.graph.neighbors[u]:
                if u < v:
                    ex += [xy[u, 0], xy[v, 0], None]
                    ey += [xy[u, 1], xy[v, 1], None]
        fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(120,120,120,0.5)", width=1.5), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=xy[:, 0], y=xy[:, 1], mode="markers+text", text=names, textposition="top center", marker=dict(size=9, color=NODE_COLOR), hoverinfo="skip", showlegend=False))
    else:
        fig.add_trace(go.Scatter(x=xy[:, 0], y=xy[:, 1], mode="markers", marker=dict(size=5, color=f"rgba(76,120,168,{alpha})"), name="Zellen", hoverinfo="skip"))
        if len(inst.blocked_xy):
            fig.add_trace(go.Scatter(x=inst.blocked_xy[:, 0], y=inst.blocked_xy[:, 1], mode="markers", marker=dict(size=6, symbol="square", color=BLOCKED_COLOR), name="Hindernis"))


def build_instance(inst, names=None):
    fig = go.Figure()
    _background(fig, inst, names, alpha=0.9)
    for t in _start_goal_trace(inst):
        fig.add_trace(t)
    return _map_layout(fig, 340 if _is_trap(inst) else 460)


def build_solution_map(inst, solutions, k, names=None):
    """Die k-te (1-basiert) verbesserte Lösung dick, alle früheren blass - die Pfade werden mit jeder Lösung kürzer."""
    xy = inst.graph.xy
    fig = go.Figure()
    _background(fig, inst, names)
    for i, (_e, _c, path) in enumerate(solutions[:k - 1], start=1):
        p = xy[path]
        fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines", line=dict(color="rgba(228,87,86,0.25)", width=3), name="frühere Lösungen" if i == 1 else None, showlegend=i == 1, hoverinfo="skip"))
    _e, cost, path = solutions[k - 1]
    p = xy[path]
    fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines+markers", line=dict(color=BSS_COLOR, width=4), marker=dict(size=5, color=BSS_COLOR), name=f"Lösung {k}"))
    for t in _start_goal_trace(inst):
        fig.add_trace(t)
    return _map_layout(fig, 340 if _is_trap(inst) else 460)


def build_paths(inst, bss_path, beam_path, astar_path, names=None):
    xy = inst.graph.xy
    fig = go.Figure()
    _background(fig, inst, names)
    if astar_path:
        p = xy[astar_path]
        fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines", line=dict(color="rgba(76,120,168,0.5)", width=11), name="A* (optimal)"))
    if beam_path:
        p = xy[beam_path]
        fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines", line=dict(color=BEAM_COLOR, width=2.5, dash="dash"), name="Beam Search (gleiche Breite)"))
    if bss_path:
        p = xy[bss_path]
        fig.add_trace(go.Scatter(x=p[:, 0], y=p[:, 1], mode="lines+markers", line=dict(color=BSS_COLOR, width=3, dash="dot"), marker=dict(size=5, color=BSS_COLOR), name="Beam-Stack Search"))
    for t in _start_goal_trace(inst):
        fig.add_trace(t)
    return _map_layout(fig, 340 if _is_trap(inst) else 460)


def build_anytime(data, beam_point=None, highlight=None):
    """Kosten der besten Lösung über kumulierte Expansionen (log-x), je Breite eine Stufenkurve; x = Optimalitätsbeweis
    abgeschlossen, offener Kreis = gekappt (nicht bewiesen). Gestrichelt: Optimum; senkrecht gepunktet: Expansionen von A*."""
    fig = go.Figure()
    opt = data["optimum"]
    for i, (w, cur) in enumerate(sorted(data["curves"].items())):
        pts = cur["points"]
        if not pts:
            continue
        xs = [e for e, _c in pts] + [cur["total"]]
        ys = [c for _e, c in pts] + [pts[-1][1]]
        width = 4 if w == highlight else 2
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=PALETTE[i % len(PALETTE)], width=width, shape="hv"), marker=dict(size=5), name=f"BSS Breite {w}"))
        fig.add_trace(go.Scatter(x=[cur["total"]], y=[pts[-1][1]], mode="markers", marker=dict(size=12, symbol="x" if cur["proved"] else "circle-open", color=PALETTE[i % len(PALETTE)], line=dict(width=2)),
                                 showlegend=False, hovertemplate=("bewiesen" if cur["proved"] else "gekappt (nicht bewiesen)") + "<extra></extra>"))
    fig.add_hline(y=opt, line=dict(color=ASTAR_COLOR, dash="dash", width=1.5), annotation_text="Optimum", annotation_position="bottom right")
    fig.add_vline(x=data["astar_expansions"], line=dict(color=ASTAR_COLOR, dash="dot", width=1.5), annotation_text="A*", annotation_position="top")
    if beam_point is not None:
        fig.add_trace(go.Scatter(x=[beam_point[0]], y=[beam_point[1]], mode="markers", marker=dict(size=13, symbol="diamond", color=BEAM_COLOR, line=dict(width=1, color="white")), name="Beam Search (kein Zurück)"))
    xs_all = [data["astar_expansions"]] + [cur["total"] for cur in data["curves"].values()] + [e for cur in data["curves"].values() for e, _c in cur["points"]]
    if beam_point is not None:
        xs_all.append(beam_point[0])
    lo, hi = max(min(xs_all), 1), max(xs_all)
    fig.update_xaxes(title_text="kumulierte Expansionen (log)", type="log", range=[float(np.log10(lo)) - 0.15, float(np.log10(hi)) + 0.15])
    fig.update_yaxes(title_text="Kosten der besten Lösung")
    return _base(fig, 400, legend_y=-0.28)


def build_tradeoff(rows, ida_point=None):
    """Speicher-Zeit-Diagramm (Paper-Tab. 1): x = Speicher-Verhältnis A* / BSS (rechts = weniger Speicher), y = Expansionen / A*
    (log). Je Breite ein Punkt (Median über die 5 Instanzen); A* = (1, 1); optional IDA* als Gegenstück."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[r["memory_ratio"] for r in rows], y=[r["total_ratio"] for r in rows], mode="lines+markers+text", text=[f"w={r['value']}" for r in rows], textposition="top right",
                             line=dict(color=BSS_COLOR, width=2.5), marker=dict(size=9, color=BSS_COLOR), name="Beam-Stack Search"))
    fig.add_trace(go.Scatter(x=[1.0], y=[1.0], mode="markers+text", text=["A*"], textposition="bottom right", marker=dict(size=13, symbol="square", color=ASTAR_COLOR), name="A*"))
    if ida_point is not None and not np.isnan(ida_point[0]):
        fig.add_trace(go.Scatter(x=[ida_point[0]], y=[ida_point[1]], mode="markers+text", text=["IDA*"], textposition="top left", marker=dict(size=13, symbol="triangle-up", color=IDA_COLOR), name="IDA*"))
    fig.update_xaxes(title_text="Speicher-Verhältnis A* / Verfahren (rechts = weniger Speicher)")
    fig.update_yaxes(title_text="Expansionen / A* (log)", type="log")
    return _base(fig, 400, legend_y=-0.25)


def build_sweep(rows, param_label, series, y_label, log_y=False, ref_line=None, ref_label=None):
    """`series`: [(key, Name, Farbe)]; Median als Linie, Minimum bis Maximum als Band (`<key>_lo`/`<key>_hi`)."""
    xs = [r["value"] for r in rows]
    fig = go.Figure()
    for key, name, color in series:
        ys = [r[key] for r in rows]
        lo = [r[f"{key}_lo"] for r in rows]
        hi = [r[f"{key}_hi"] for r in rows]
        rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        fig.add_trace(go.Scatter(x=xs + xs[::-1], y=hi + lo[::-1], mode="lines", fill="toself", fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.13)", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=color, width=2.5), name=name))
    if ref_line is not None:
        fig.add_hline(y=ref_line, line=dict(color="#888", dash="dash", width=1.5), annotation_text=ref_label, annotation_position="top left")
    fig.update_xaxes(title_text=param_label, type="category")
    fig.update_yaxes(title_text=y_label, type="log" if log_y else "linear")
    return _base(fig, 360, legend_y=-0.3)


def build_share_bars(rows, param_label):
    """Anteile aller Läufe: bewiesen / gekappt (BSS) und "Beam scheitert"."""
    xs = [r["value"] for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=[r["proved_share"] for r in rows], name="BSS: Optimum bewiesen", marker_color=IDA_COLOR))
    fig.add_trace(go.Bar(x=xs, y=[r["capped_share"] for r in rows], name="BSS: gekappt (nicht bewiesen)", marker_color=BLOCKED_COLOR))
    fig.add_trace(go.Bar(x=xs, y=[r["beam_failed_share"] for r in rows], name="Beam Search: gescheitert", marker_color=BEAM_COLOR))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text=param_label, type="category")
    fig.update_yaxes(title_text="Anteil der Läufe (%)", range=[0, 100])
    return _base(fig, 330, legend_y=-0.35)


def build_revisits_bar(revisits):
    fig = go.Figure(go.Bar(x=list(range(len(revisits))), y=revisits, marker_color=BSS_COLOR,
                           hovertemplate="Schicht %{x}<br>%{y} Rücksprünge<extra></extra>"))
    fig.update_xaxes(title_text="Schicht (Kantenzahl vom Start)")
    fig.update_yaxes(title_text="Rücksprünge in diese Schicht", rangemode="tozero", **({"dtick": 1} if max(revisits, default=0) <= 6 else {}))
    return _base(fig, 300)
