# Beam-Stack Search – Beam Search mit Rückweg: optimal bei jeder Breite, aber zu welchem Preis? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-beam-stack-demo.streamlit.app/)**

Sechstes Stück der **Heuristische-Baumsuche-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning" - der **Konvergenzpunkt** von Beam Search und A\*. Beam Search begrenzt den Speicher durch die Breite w, verliert dabei aber Pfade **für immer**: bei Breite 1 scheitert es in 40 % der Läufe (Größe 12) und liefert bei schmaler Breite eine Lücke - gemessen in [beam-search-demo](../beam-search-demo) und [monobeam-demo](../monobeam-demo). A\* ist optimal, hält aber die ganze Grenzmenge im Speicher. **Beam-Stack Search** (Zhou & Hansen, ICAPS 2005) **springt zurück**: ein **Beam-Stack** merkt sich je Schicht den f-Bereich [fmin, fmax) der bereits zugelassenen Nachfolger und kehrt zu Schichten zurück, in denen beschnitten wurde. Ergebnis: ein Anytime-Algorithmus, der früh eine erste Lösung liefert (wie Beam Search), sie verbessert und am Ende das **Optimum beweist** - bei jeder Breite.

**Einordnung in die Linie:** derselbe Graph, dieselben Instanzen und dieselben Suchkerne wie in den Geschwister-Demos ([beam-search-demo](../beam-search-demo): Raster, Sackgassen-Falle, `beam_search`; [ida-star-demo](../ida-star-demo): `ida_star`, wortgleich kopiert und als Test auf die dortigen Zahlen geprüft). Beam Search (f-Rang, gleiche Breite) ist der Vergleich zur Wurzel des Zweigs, **IDA\*** das Gegenstück zur anderen Speicher-Antwort der Linie (Wiederholung statt begrenzter Breite + Backtracking).

```
Greedy Best-First Search (Wurzel)                                                          [gebaut]
 ├─ Beam Search → {Diverse Beam Search, Monobeam}          [Beam Search, Monobeam gebaut; Diverse nicht gebaut]
 ├─ A* → Iterative Deepening A* (IDA*)                                                     [gebaut]
 └─ Monte Carlo Tree Search (MCTS)                                                         [nicht gebaut]
Beam Search + A* → Beam Stack Search (Konvergenzpunkt)                     [DIESES STÜCK]
```

Ergebnis in Kürze: **BSS beweist bei jeder Breite das Optimum** (Satz 1 des Papers, im Test direkt geprüft) - auch dort, wo Beam Search scheitert. **Der Beweis ist aber teuer und der Speichergewinn kurzlebig:** bei Breite 1 / 2 / 4 braucht er im Median 87.5 / 17.0 / 2.7 Mal so viele Expansionen wie A\* (Größe 12), spart aber nur bei schmaler Breite Speicher (4.4x / 2.4x / 1.4x weniger als A\*; ab Breite ≈ 6 nicht mehr). Die erste Lösung kommt früh (nach 0.26x bzw. 0.47x A\*-Expansionen), die optimale nach 40x bzw. 4.9x - bei Breite 1 verbraucht der **Beweis** noch einmal etwa so viel wie das Finden. Gegen IDA\* schneidet BSS auf diesem Raster deutlich besser ab (Größe 8: 9.1x gegen 705x A\* bei gleicher Speicherersparnis). Und der **Median täuscht bei Breite 1**: über 40 Instanzen liegt das 90. Perzentil bei 1109x A\*, 10 % der Läufe bleiben bei 300 000 Expansionen ohne jede Lösung (Tiefensuche in einer Sackgassen-Region).

| Frage | Ergebnis (Rastergröße 12, Hindernisdichte 15 %, Startschranke aus; **Median** über 5 feste Instanzen, Seeds 100000–100004; vollständig deterministisch; gekappte Läufe getrennt ausgewiesen) |
|---|---|
| **Findet BSS bei jeder Breite das Optimum?** | ✅ ja: alle 5 Instanzen bei allen Breiten des Reglers (1–24) **bewiesen optimal**, nichts gekappt; Beam Search scheitert bei Breite 1 in **40 %** der Läufe (Breite 2–24: 0 %). Im Test zusätzlich: Raster (Breiten 2–24 und "unbegrenzt"; Breite 1 auf kleinen Rastern), die Falle, Brute-Force auf kleinen Instanzen und **1500 zufällige kleine Graphen** mit nicht konsistenter Heuristik (Breiten 1–3, 0 Abweichungen) |
| **Was kostet der Beweis?** | ⚠️ Expansionen bis Beweis / A\* bei Breite 1/2/3/4/6/8/12/16/24: **87.5 / 17.0 / 4.9 / 2.7 / 1.5 / 1.2 / 1.25 / 1.25 / 1.25**; Rücksprünge 1924/193/30/8/3/0/0/0/0 |
| **Was bleibt vom Speichervorteil?** | ⚠️ Speicher-Verhältnis (A\* gespeichert / BSS-Spitze): **4.4 / 2.4 / 1.7 / 1.4 / 1.05 / 0.97 / 0.90 / 0.90 / 0.90** - der Tausch ist steil: Breite 1 spart 4.4x Speicher für 88x Zeit, Breite 4 nur 1.4x für 2.7x. Ab Breite 8 (≥ größte Schicht) kein Rücksprung mehr: Breitensuche-Branch-and-Bound, ~1.25x A\* mit mehr Speicher als A\* |
| **Anytime: wann kommt was?** | Erste Lösung bei Breite 1/2 nach 0.26x / 0.47x A\*-Expansionen (Lücke 7.1 % / 4.5 %; Beam Search gleicher Breite 6.0 % / 4.5 %), Lücke ≤ 1 % nach 39.8x / 4.9x, die optimale Lösung nach 40.3x / 4.9x, der Beweis nach 87.5x / 17.0x |
| **BSS gegen IDA\*** | Größe 8: IDA\* im Median **705x** A\* (Speicher 3.0x weniger), BSS bei Breite 1 **9.1x** bei gleicher Speicherersparnis (3.0x). Ab Größe 12 bricht IDA\* bei 300 000 Expansionen ab (80 % der Läufe bei Größe 12, 100 % bei 14 und 16), BSS beweist bei Breite 2 bis Größe 16 in 100 %. Warum genau, wird nicht isoliert (BSS hat eine obere Schranke und Dominanz-Duplikate, IDA\* nur die Schwelle) |
| **Hilft eine Startschranke aus Beam Search?** | ⚠️ nur bei schwachem ersten Abstieg: bei Breite 1 sinken die Expansionen von 87.5x auf **55x** A\* (-37 %), bei Breite 2 von 17.0x auf 15.4–15.8x, bei Breite 4 **steigen** sie von 2.7x auf 3.3–3.8x (die Expansionen des Beam zählen mit) |
| **Hindernisdichte (Breite 2; 0/10/20/30/40 %)** | Expansionen bis Beweis 32 / 9.8 / 11.7 / 3.6 / 3.2x A\*, Speicher 2.8 / 2.4 / 2.2 / 1.5 / 1.25x; Beam Search scheitert in 0 / 0 / 20 / 60 / 20 % der Läufe, BSS beweist in 100 % |
| **Rastergröße (Breite 2; 8/10/12/14/16)** | 2.8 / 5.2 / 17 / 10 / 50x A\*, Speicher 1.6 / 2.0 / 2.4 / 2.4 / 2.6x. Breite 1: 9.1 / 14 / 88 / 68 / **352x** A\* (bei Größe 16 sind 20 % der Läufe bei 300 000 Expansionen gekappt - dann nicht bewiesen) |
| **Der Median täuscht (40 feste Instanzen, Seeds 200000–200039)** | ⚠️ Breite 1: Median 49x, 75. Perzentil 123x, **90. Perzentil 1109x, Maximum 4054x** A\*; **4 von 40 Läufen (10 %) gekappt, alle ohne jede Lösung**. Breite 2 / 3 / 4: Maximum 35x / 30x / 8x, nichts gekappt. Extrembeispiel Größe 8, Seed 200001: A\* 37 Expansionen, BSS Breite 1 **573 409**, Breite 2 643, Breite 3 84 |
| **Handgebaute Falle** | Breite 1: erste Lösung 14.46 (der Köder, wie Beam und Greedy Best-First), ein Rücksprung, Optimum 13.46 nach 8 Expansionen (A\* 7); Breite 2: 13.46 nach 6 Expansionen ohne Rücksprung |

## Was die Demo zeigt

1. **Beam-Stack Search in Aktion** (Schritt-Slider): **Instanz** → **Lösungsfolge** (Slider über die verbesserten Lösungen: die k-te dick, frühere blass, mit Expansionszahl und Lücke; die letzte ist das bewiesene Optimum oder - bei Abbruch - die beste unbewiesene) → **Ergebnis** (BSS, Beam Search gleicher Breite und A\* überlagert).
2. **🎯 Was der Beweis kostet:** Status (bewiesen / gekappt), Expansionen bis Beweis gegen A\* (bei Abbruch als "≥" gekennzeichnet), Speicher A\* / BSS, Beam Search gleicher Breite.
3. **⏱️ Anytime:** Kosten der besten Lösung über die kumulierten Expansionen (logarithmisch), je Breite eine Stufenkurve, x = bewiesen, offener Kreis = gekappt; dazu **Rücksprünge je Schicht** (wie bei Tiefensuche vor allem in die tieferen Schichten).
4. **🔍 Beam-Stack Schritt für Schritt** (an der Falle): pro Schritt die Schichten, ihre Knoten und die Stack-Elemente [fmin, fmax) - man sieht, wie fmax beim Beschneiden sinkt und beim Rücksprung fmin nachrückt.
5. **📐 Speicher-Zeit-Diagramm** (Analogon zu Tab. 1 des Papers: je Breite Speicher gegen Expansionen, A\* und IDA\* als Referenz) und **Sweeps** über Breite, Hindernisse und Größe (Median, Min-Max-Band; Expansionen, Speicher, Lücke der ersten Lösung, Anytime-Zeitpunkte, bewiesen / gekappt / Beam scheitert).
6. **🔬 Ausreißer-Test:** Verteilung des Aufwands über 40 feste Instanzen je Breite 1–4.
7. **🚧 Grenzen:** Tabelle "Annahme – was passiert – wer setzt an".

Regler: Instanz (Raster / Falle), Rastergröße (5–20), Hindernisdichte (0–40 %), Seed (+ 🎲), **Breite** (1 bis 24), **Startschranke** (Breite eines vorab laufenden Beam Search, 0 = keine), **Expansions-Obergrenze** (10 000 bis 1 Mio.). Kein Zufall im Kern - vollständig deterministisch.

## Messwerte der Presets

| Preset | Instanz | Ergebnis |
|---|---|---|
| Standardfall (Voreinstellung) | Größe 12, Breite 2, Seed 35 | Beam findet das Optimum (175.9 km) nach 43 Expansionen, BSS ebenfalls nach 43, **beweist** es nach 651 (A\*: 82) bei höchstens 44 gespeicherten Knoten (A\*: 100) |
| Beam scheitert (Breite 1) | Seed 100000 | Beam ohne Pfad; BSS: erste Lösung nach 27 Expansionen (232.9 km), 22 Lösungen, bewiesenes Optimum 188.1 km nach 8488 Expansionen, höchstens 25 gespeicherte Knoten (A\*: 110) |
| Handgebaute Falle (Breite 1) | Falle | erste Lösung 14.46 (Köder), ein Rücksprung, Optimum 13.46 nach 8 Expansionen (A\*: 7) |
| Breite 1 = Tiefensuche | Seed 35 | 577 Rücksprünge, 2546 Expansionen (31x A\*), 23 gespeicherte Knoten (A\*: 100); erste Lösung 177.7 km nach 22, optimale 175.9 km nach 25 Expansionen |
| Große Breite: kein Rücksprung | Seed 35, Breite 24 | 0 Rücksprünge, 125 Expansionen (A\*: 82), 126 gespeicherte Knoten (mehr als A\*) |
| Startschranke (Beam 8) | Seed 100002, Breite 1 | Expansionen (einschließlich der 120 des Beam) 1190 → 615 |
| Ausreißer (Breite 1) | Größe 8, Seed 200001, Obergrenze 100 000 | gekappt, keine Lösung; erst nach 573 409 Expansionen die optimale (A\*: 37); Breite 2: 643, Breite 3: 84 |
| Kappung (Obergrenze 10 000) | Größe 16, Breite 1, Seed 35 | gekappt: beste Lösung 181.0 km (11 Lösungen) **nicht bewiesen**, Optimum 177.8 km; mit Obergrenze 300 000 bewiesen nach 53 661 Expansionen |

Die einzelne Instanz weicht von den Sweep-Medianen ab - die Mediane oben sind die belastbaren Zahlen; die Raster-Presets prüfen sich zusätzlich über die 5 festen Sweep-Instanzen gegen eine gemessene Spannweite, alle Aussagen der Presets sind als eigene Tests hinterlegt (`tests/test_presets.py`).

## Modell und Verfahren

- **Instanz und Graph** (`bss_scenario.py`, `bss_graph.py`): das gestörte Raster mit Hindernissen und die handgebaute Sackgassen-Falle aus [beam-search-demo](../beam-search-demo) (Kantengewicht = echter euklidischer Abstand, Heuristik = Luftlinie, zulässig).
- **Suchkern** (`bss_algorithm.py`): `_search`, `greedy_best_first`, `uniform_cost_search`, `a_star`, `beam_search` (beam-search-demo) und `ida_star` (ida-star-demo) wortgleich; NEU `beam_stack_search`: Schichten (Schicht = Kantenzahl), je Schicht höchstens w Knoten nach dem Schlüssel (f, Zustand); Beam-Stack-Element je Schicht [fmin, fmax); Nachfolger nur mit Schlüssel in diesem Bereich und f < U; beim Beschneiden wird fmax der kleinste Schlüssel der verworfenen Knoten; Zielfund setzt U (anytime, Suche läuft weiter); leere nächste Schicht → vom Stack oben alle Elemente mit fmax ≥ U entfernen, am obersten verbleibenden fmin := fmax, fmax := ∞, diese Schicht neu expandieren; Stack leer → bewiesen (`proved`). Startschranke: mit `bound_width > 0` läuft vorab ein Beam Search dieser Breite, seine Lösung wird zum Inkumbent, seine Expansionen zählen mit. `max_expansions` ist ein Sicherheitsnetz (`capped`): die beste bis dahin gefundene Lösung bleibt gültig, ein Optimalitätsanspruch entfällt.
- **Duplikate:** je Zustand innerhalb einer Schicht das kleinste g; zusätzlich Dominanz gegen alle gespeicherten früheren Schichten (derselbe Zustand mit g' ≤ g dort → verwerfen) - das sichert die Terminierung auch mit U = ∞. Die Korrektheit dieser Regel wird nicht angenommen, sondern durch Satz 1 im Test belegt.
- **Speichermodell:** "gespeicherte Knoten" = Summe der Schichtgrößen aller Schichten der aktuellen Tiefe (das Beam-Stack-"dw"-Modell); die Spitze im Lauf wird gegen die von A\* gespeicherten (entdeckten) Knoten gestellt.
- **Auswertung** (`bss_evaluation.py`): Expansions-Faktor bis Beweis, Speicher-Verhältnis, Lücke der ersten Lösung gegen Beam Search gleicher Breite, Expansionen bis erste Lösung / Lücke ≤ 1 % / optimale Lösung, Rücksprünge, Anteile bewiesen / gekappt / Beam scheitert; IDA\* als Gegenstück; Median mit Minimum/Maximum, **gekappte Läufe getrennt**; `tail` = Verteilung über 40 feste Instanzen; `anytime_curves`.

## Was nicht funktioniert hat / Grenzen

- **Der Beweis ist nicht billig.** 87.5x / 17.0x / 2.7x A\* bei Breite 1 / 2 / 4 (Größe 12); bei Breite 1 und Größe 16 sind 20 % der Läufe bei 300 000 Expansionen gekappt.
- **Der Median genügt nicht.** Breite 1 ist Tiefensuche und hat einen schweren Schwanz (90. Perzentil 1109x A\*, 10 % der Läufe ganz ohne Lösung im Cap); die "frühe erste Lösung" gilt im Median, nicht garantiert. Breite 2–4 ist gutartig (Maximum 35x / 30x / 8x). Mögliche Ursache: ein transpositionsreiches Raster, in dem die Tiefensuche viele Wege zum selben Knoten neu durchläuft - hier nicht isoliert untersucht, gemessen ist nur die Verteilung.
- **Der Speichervorteil ist auf schmale Breiten beschränkt** (bis ca. Breite 4) und im hier gezählten Modell (alle Schichten der Tiefe) gerechnet. **Nicht gebaut:** Divide-and-Conquer-Lösungsrekonstruktion des Papers (4w-Speicher, tiefenunabhängig), Externspeicher, BSIDA\*.
- **BSS gegen IDA\*** fällt hier klar zugunsten von BSS aus; das ist eine Aussage über dieses Raster (IDA\* hat weder Inkumbent noch Transpositionstabelle im Vergleichslauf), nicht über die beiden Verfahren im Allgemeinen. IDA\*-Läufe sind bei 300 000 Expansionen gekappt (Untergrenze).
- **Eine Startschranke hilft nur bei schwachem ersten Abstieg** (Breite 1: -37 %; Breite 4: mehr Aufwand).
- **Synthetische Instanzen:** ein Raster mit Jitter, Vierer-Nachbarschaft, keine Zeitfenster, keine gerichteten Kanten; Größen bis 20 im Regler. Andere Graphstrukturen wurden nicht gemessen.

## Verifikation

- **Satz 1 direkt:** BSS-Kosten == UCS-Optimum, `proved`, für die Breiten 2/3/4/8/24 und "unbegrenzt" über 60 Rasterinstanzen (0/15/40 % Hindernisse), Breite 1 zusätzlich auf 60 kleinen Rastern (Größe 6), für Breiten 1/2/3/5 gegen **Brute-Force** auf kleinen Instanzen, die Falle bei jeder Breite, und über **1500 zufällige kleine Graphen mit zulässiger, nicht konsistenter Heuristik** (Breiten 1–3).
- **Gültiger Pfad** (zusammenhängend, ohne Wiederholung, Kosten gegen unabhängige Neuberechnung); Determinismus; ein nicht erreichbares Ziel wird als "kein Pfad" bewiesen (Stack leer, keine Lösung).
- **Anytime-Folge:** Kosten streng fallend, Expansionszähler steigend, letzte Lösung == bewiesenes Optimum, jede Lösung ein gültiger Pfad.
- **Sonderfälle des Papers:** Breite ≥ größte Schicht → 0 Rücksprünge und identische Expansionen wie unbegrenzt (30 Instanzen); Breite 1 → jede Schicht höchstens ein Knoten, Rücksprünge > 0.
- **Schranken und Invarianten:** je Schicht ≤ w Knoten, Speicherspitze ≤ w · Schichtzahl; Beam-Stack an der Falle: fmin ≤ fmax, U nur fallend, Stack am Ende leer.
- **Startschranke:** gleiche Kosten, die Expansionen des Beam zählen mit (erste Lösung bei genau diesen Expansionen). **Kappung:** `capped` genau bei Erreichen der Grenze, beste Lösung bleibt gültig, kein Beweis.
- **Alle Zahlen der App-Texte sind als Tests hinterlegt**, über dieselben Auswertungsfunktionen wie die App selbst (`ev.run_config`/`ev.sweep`/`ev.tail`), NIE über ein Ad-hoc-Skript; AppTest-Rauchtests (Voreinstellung, jedes Preset, jeder Schritt für beide Instanz-Typen, gekappte Läufe ohne jede Lösung in jedem Schritt, Lösungs-Slider und Beam-Stack-Verlauf mit Klemmung bei Instanzwechsel, Extremwerte, Würfel, Permalink-Grenzen, ausgeblendete Regler bei der Falle, Speicher-Zeit-Diagramm, alle Sweeps und der Ausreißer-Test auf Abruf, Footer). Die Vor-Messung auf den 5 Sweep-Instanzen hatte den schweren Schwanz zunächst verdeckt - er fiel erst im Optimalitätstest auf (Größe 8, Seed 200001) und wurde daraufhin über 40 Instanzen gemessen.

Literatur: Zhou, R., & Hansen, E. A. (2005). *Beam-Stack Search: Integrating Backtracking with Beam Search.* Proceedings of the 15th International Conference on Automated Planning and Scheduling (ICAPS). Korf, R. E. (1985). *Depth-first iterative-deepening: An optimal admissible tree search.* Artificial Intelligence, 27(1), 97-109.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `app.py` | Streamlit-App: Instanz-Umschalter, Schritte (Lösungsfolge), Kennzahlen, ⏱️ Anytime, 🔍 Beam-Stack-Verlauf, 📐 Speicher-Zeit und Sweeps, 🔬 Ausreißer, 🚧 Grenzen, Mathe |
| `bss_algorithm.py` | Suchkerne, `beam_search`, `ida_star` (Kopien) + `beam_stack_search` |
| `bss_graph.py`, `bss_scenario.py` | Graph, Raster- und Fallen-Instanz (Kopie) |
| `bss_constants.py` | Konstanten, Presets, gemessene Werte |
| `bss_evaluation.py` | Kennzahlen, Sweeps, Anytime-Kurven, Ausreißer-Verteilung |
| `bss_presets.py`, `bss_visualization.py` | Permalink/Presets, Plotly-Figuren (Lösungsfolge, Anytime, Speicher-Zeit, Sweeps, Rücksprünge) |
| `tests/` | Zentrale Korrektheitskette (Satz 1, Anytime, Sonderfälle), Szenario/Auswertung, Aussagen der App, Presets, AppTest |

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von
[Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning.
Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
