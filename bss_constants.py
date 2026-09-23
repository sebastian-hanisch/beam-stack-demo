"""Konstanten der Beam-Stack-Demo: Raster-Geometrie (wortgleich zur Beam-Search-Demo), Regler, gemessene Werte, Presets."""

AREA = 100.0                     # Kantenlänge des Gebiets in km
JITTER = 0.35                    # Lageabweichung je Zelle, Anteil des Zellenabstands

SIDE_MIN, SIDE_MAX, DEFAULT_SIDE, SIDE_STEP = 5, 20, 12, 1     # Rastergröße (Zellen je Kante)
OBSTACLE_MIN, OBSTACLE_MAX, DEFAULT_OBSTACLE, OBSTACLE_STEP = 0, 40, 15, 5   # Prozent gesperrte Zellen
SEED_MAX = 999999
DEFAULT_SEED = 35

WIDTHS = (1, 2, 3, 4, 6, 8, 12, 16, 24)        # Breiten des Reglers und des Breiten-Sweeps
DEFAULT_WIDTH = 2                              # MUSS Mitglied von WIDTHS sein (st.select_slider snappt sonst still)
CURVE_WIDTHS = (1, 2, 4, 8)                    # Breiten der Anytime-Kurven
BOUND_WIDTHS = (0, 4, 8, 24)                   # Startschranke: Breite des vorab laufenden Beam Search (0 = keine)
CAPS = (10000, 100000, 300000, 1000000)        # Expansions-Obergrenze von BSS (Sicherheitsnetz)
DEFAULT_CAP = 300000                           # MUSS Mitglied von CAPS sein
IDA_CAP = 300000                               # Obergrenze des IDA*-Vergleichslaufs

SWEEP_SEEDS = tuple(range(100000, 100005))
SCALING_SIDES = (8, 10, 12, 14, 16)
OBSTACLE_SWEEP = (0, 10, 20, 30, 40)
TAIL_SEEDS = tuple(range(200000, 200040))      # 40 feste Instanzen für den Ausreißer-Test
TAIL_WIDTHS = (1, 2, 3, 4)

# --- Gemessene Werte (MEDIAN über 5 feste Sweep-Instanzen, Seeds 100000-100004; Rastergröße 12, Hindernisdichte 15 %,
# --- Startschranke aus; 2026-09-23, alle Werte über ev.run_config/ev.sweep nachgerechnet, s. tests/test_claims.py).
# --- Faktoren sind schief verteilt - deshalb Median; gekappte Läufe werden getrennt ausgewiesen (Faktor dort nur Untergrenze). ---
# ZENTRALE FRAGE 1 - findet BSS bei jeder Breite den optimalen Pfad? JA, ohne Ausnahme: Satz 1 des Papers ist im Test direkt
#   geprüft (Raster, Falle und 1500 zufällige kleine Graphen mit nicht konsistenter Heuristik, Breiten 1-3, 0 Abweichungen) -
#   auch dort, wo Beam Search scheitert (Breite 1: Beam scheitert in 40 % der Läufe, BSS beweist in 100 % das Optimum).
# ZENTRALE FRAGE 2 - was kostet der Beweis? Expansionen bis zum Beweis, relativ zu A*, bei Breite 1/2/3/4/6/8/12/16/24:
#   87.5 / 17.0 / 4.9 / 2.7 / 1.5 / 1.2 / 1.25 / 1.25 / 1.25; Rücksprünge 1924/193/30/8/3/0/0/0/0. Ab Breite 8 (>= größte
#   Schicht) kein Rücksprung mehr: Breitensuche-Branch-and-Bound, ~1.25x A*. Speicher-Verhältnis (A* gespeichert / BSS-Spitze):
#   4.4 / 2.4 / 1.7 / 1.4 / 1.05 / 0.97 / 0.90 / 0.90 / 0.90 - nur bei schmaler Breite spart BSS Speicher, ab Breite ~6 nicht mehr.
#   Speicher-Zeit-Tausch also steil: Breite 1 spart 4.4x Speicher für 88x Zeit, Breite 4 nur 1.4x Speicher für 2.7x Zeit.
# ANYTIME: die erste Lösung liegt sehr früh vor (Breite 1: nach 0.26x, Breite 2: nach 0.47x A*-Expansionen), mit Lücke 7.1 % / 4.5 %
#   (Beam Search gleicher Breite: 6.0 % / 4.5 %, bei Breite 1 scheitert Beam in 40 % der Läufe); Lücke <= 1 % nach 39.8x / 4.9x,
#   die optimale Lösung nach 40.3x / 4.9x A*-Expansionen - bei Breite 1 verbraucht der BEWEIS (87.5x) also noch einmal etwa so
#   viel wie das Finden.
# IDA* ALS GEGENSTÜCK (dieselben Instanzen, Obergrenze 300 000 Expansionen): bei Rastergröße 8 braucht IDA* im Median 705x A*
#   (Speicher 3.0x weniger), BSS bei Breite 1 nur 9.1x A* bei gleicher Speicherersparnis (3.0x). Ab Größe 12 bricht IDA* bei der
#   Obergrenze ab (80 % der Läufe bei Größe 12, 100 % bei 14 und 16), BSS beweist bei Breite 2 bis Größe 16 in 100 % der Läufe.
#   Erklärung nicht isoliert: BSS hat eine obere Schranke (jede gefundene Lösung) und Dominanz-Duplikate gegen die Schichten, IDA*
#   nur die Schwelle - welcher Anteil woher kommt, wird hier nicht getrennt.
# STARTSCHRANKE (Beam Search der Breite b vorab; dessen Expansionen zählen mit): bei Breite 1 sinken die Expansionen von 87.5x auf
#   55x A* (b = 4/8/16/24 gleich), bei Breite 2 von 17.0x auf 15.4-15.8x, bei Breite 4 STEIGEN sie von 2.7x auf 3.3-3.8x - die
#   Schranke lohnt nur, wenn der Beam-artige erste Abstieg schwach ist.
# HINDERNISDICHTE (Breite 2; 0/10/20/30/40 %): Expansionen bis Beweis 32/9.8/11.7/3.6/3.2x A*, Speicher 2.8/2.4/2.2/1.5/1.25x,
#   Beam scheitert in 0/0/20/60/20 % der Läufe, BSS beweist in 100 %.
# RASTERGRÖSSE (Breite 2; 8/10/12/14/16): 2.8/5.2/17/10/50x A*, Speicher 1.6/2.0/2.4/2.4/2.6x. Breite 1: 9.1/14/88/68/352x A*
#   (bei Größe 16 sind 20 % der Läufe bei 300 000 Expansionen gekappt - dann nicht bewiesen), Speicher 3.0/3.6/4.4/4.7/4.9x.
# AUSREISSER (40 feste Instanzen, Seeds 200000-200039, Größe 12 / 15 %, Obergrenze 300 000): der Median täuscht bei Breite 1 - Expansionen
#   bis Beweis / A*: Median 49 / 75. Perzentil 123 / 90. Perzentil 1109 / Maximum 4054, und 4 von 40 Läufen (10 %) sind gekappt, alle OHNE jede
#   Lösung (Tiefensuche in einer Sackgassen-Region). Breite 2: Maximum 35, Breite 3: 30, Breite 4: 8, nichts gekappt. Extrembeispiel Größe 8,
#   Seed 200001: A* braucht 37 Expansionen, BSS mit Breite 1 573 409 (Obergrenze 1 Mio. nötig), mit Breite 2 643, mit Breite 3 84.
# HANDGEBAUTE FALLE: Breite 1: erste Lösung 14.46 (der Köder, wie Beam/GBFS), ein Rücksprung, Optimum 13.46 nach 8 Expansionen
#   (A* 7); Breite 2: ohne Rücksprung 13.46 nach 6 Expansionen.
# NICHT gebaut: Divide-and-Conquer-Lösungsrekonstruktion (4w-Speicher), Externspeicher, BSIDA*.

PRESETS = {
    "Standardfall (Voreinstellung)": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 2, "bound_width": 0, "cap": 300000},
    "Beam scheitert (Breite 1)": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 100000, "width": 1, "bound_width": 0, "cap": 300000},
    "Handgebaute Falle (Breite 1)": {"network": "trap", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 1, "bound_width": 0, "cap": 300000},
    "Breite 1 = Tiefensuche": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 1, "bound_width": 0, "cap": 300000},
    "Große Breite: kein Rücksprung": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 35, "width": 24, "bound_width": 0, "cap": 300000},
    "Startschranke (Beam 8)": {"network": "grid", "side": 12, "obstacle_pct": 15, "seed": 100002, "width": 1, "bound_width": 8, "cap": 300000},
    "Ausreißer (Breite 1)": {"network": "grid", "side": 8, "obstacle_pct": 15, "seed": 200001, "width": 1, "bound_width": 0, "cap": 100000},
    "Kappung (Obergrenze 10 000)": {"network": "grid", "side": 16, "obstacle_pct": 15, "seed": 35, "width": 1, "bound_width": 0, "cap": 10000},
}
PRESET_HELP = {
    "Standardfall (Voreinstellung)": "Rastergröße 12, Breite 2, Seed 35: Beam Search findet den optimalen Pfad (175.9 km) nach 43 Expansionen - BSS findet ihn ebenfalls nach 43, braucht aber 651 Expansionen (A\\*: 82), um zu BEWEISEN, dass es der optimale ist, und speichert dabei höchstens 44 Knoten (A\\*: 100).",
    "Beam scheitert (Breite 1)": "Seed 100000: Beam Search mit Breite 1 läuft in eine Sackgasse und findet keinen Pfad. BSS springt zurück: erste Lösung nach 27 Expansionen (232.9 km), dann 21 Verbesserungen bis zum bewiesenen Optimum (188.1 km) nach 8488 Expansionen, bei höchstens 25 gespeicherten Knoten (A\\*: 110).",
    "Handgebaute Falle (Breite 1)": "Der 8-Knoten-Graph aus der Wurzel: mit Breite 1 folgt BSS zuerst dem Köder (14.46, wie Beam und Greedy Best-First), springt dann einmal zurück und findet den optimalen Pfad (13.46) nach 8 Expansionen (A\\*: 7). Die Beam-Stack-Ansicht zeigt jeden Schritt.",
    "Breite 1 = Tiefensuche": "Breite 1 ist Tiefensuche-Branch-and-Bound: Seed 35, 577 Rücksprünge, 2546 Expansionen (31x A\\*), aber nur 23 gespeicherte Knoten (A\\*: 100, 4.3x weniger). Die erste Lösung (177.7 km) kommt nach 22 Expansionen, die optimale (175.9 km) nach 25 - der Rest ist Beweis.",
    "Große Breite: kein Rücksprung": "Breite 24 >= größte Schicht: Breitensuche-Branch-and-Bound, 0 Rücksprünge, 125 Expansionen (A\\*: 82) - aber 126 gespeicherte Knoten, mehr als A\\* (100): kein Speichergewinn mehr.",
    "Startschranke (Beam 8)": "Seed 100002, Breite 1: ein vorab laufender Beam Search der Breite 8 liefert schon die optimale Lösung als obere Schranke - die Expansionen (einschließlich der 120 des Beam) sinken von 1190 auf 615. Bei Breite 4 kostet die Schranke im Median mehr, als sie spart.",
    "Ausreißer (Breite 1)": "Rastergröße 8, Seed 200001: A\\* braucht 37 Expansionen, BSS mit Breite 1 (Tiefensuche) findet innerhalb von 100 000 Expansionen NICHTS - erst nach 573 409 Expansionen die (optimale) Lösung. Mit Breite 2 sind es 643, mit Breite 3 nur 84. Breite 1 ist ein Glücksspiel mit schwerem Schwanz.",
    "Kappung (Obergrenze 10 000)": "Rastergröße 16, Breite 1, Obergrenze 10 000 Expansionen: BSS bricht ab, die beste Lösung bis dahin (181.0 km, 11 Lösungen) ist NICHT bewiesen - das Optimum liegt bei 177.8 km. Mit Obergrenze 300 000 beweist BSS es nach 53 661 Expansionen.",
}
# Beobachtete Spannweite des MEDIANS des Expansions-Faktors bis Beweis (BSS / A*) über die 5 festen Sweep-Instanzen (mit
# Sicherheitsabstand), nur für die Raster-Presets (die Falle ist ein fester Graph, ihre Zahlen stehen als Tests). Bei
# gekappten Läufen Untergrenze.
PRESET_EXPECTED_BANDS = {
    "Standardfall (Voreinstellung)": (10.0, 25.0),
    "Beam scheitert (Breite 1)": (50.0, 130.0),
    "Breite 1 = Tiefensuche": (50.0, 130.0),
    "Große Breite: kein Rücksprung": (1.0, 1.6),
    "Startschranke (Beam 8)": (35.0, 80.0),
    "Ausreißer (Breite 1)": (5.0, 13.0),
    "Kappung (Obergrenze 10 000)": (30.0, 120.0),
}
