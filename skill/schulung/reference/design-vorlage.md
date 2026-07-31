# design.md — ausfüllbare Vorlage (eigenes CI / Kunden-CI)

Diese Datei in den Projektordner legen und ausfüllen. Sie **übersteuert das gewählte
Preset** aus `reference/styles/` — es gilt: **design.md > Preset > Default (cinematic)**.
Alle Felder außer `basis_preset` und `akzent` sind optional; was fehlt, kommt aus dem
Basis-Preset. Fehlende Werte nicht erfinden — im Curriculum als offene Position führen.

```markdown
# design.md — CI-Vorgaben

basis_preset: cinematic        # cinematic | comic | corporate | statisch
akzent: "#RRGGBB"              # Pflicht: Akzentfarbe (Hex)
akzent_hell: "#RRGGBB"         # optional: hellere Stufe (Hover, Zwischenüberschriften);
                               #   fehlt sie, wird sie aus akzent abgeleitet
hintergrund: "#RRGGBB"         # optional: Seitenhintergrund. Dunkel empfohlen, wenn das
                               #   Basis-Preset dunkle Videos liefert (cinematic, statisch)
panel: "#RRGGBB"               # optional: Karten-Hintergrund
wortmarke: "Firmenname"        # optional: Text im Header der HTML-Datei
logo: "./logo.png"             # optional: Pfad relativ zum Projektordner; wird als
                               #   Data-URI eingebettet (nie einfärben oder verzerren)
footer: "Firma · Bereich · example.de"   # optional: Zeile im Abschluss-Footer;
                                         #   leer = neutraler Footer ohne Branding
ansprache: "du"                # optional: du | Sie (überschreibt die Ableitung aus der Zielgruppe)
stil_hinweise: |               # optional: zusätzliche englische Prompt-Zeilen, werden
  soft watercolor texture      #   wörtlich an den Stil-Block des Presets angehängt
  rounded friendly shapes
guide_figur: "kleiner Roboter in der Akzentfarbe, kastenförmig, runde Augen"
                               # optional: ersetzt die Guide-Figur des Presets
                               #   (Beschreibung geht in Referenzbild- und Video-Prompts)
medien_defaults:               # optional: überschreibt die Medien-Defaults des Presets
  film: 1                      #   Ziel-Anzahl Filme pro Schulung (0 = wie Preset statisch)
  bild: 5                      #   Ziel-Anzahl Bilder
```

## Regeln beim Anwenden

- **Kontrast nachrechnen:** `akzent` muss auf `hintergrund` und auf `panel` ≥ 4,5:1 liegen —
  `python3 scripts/kontrast.py "<akzent>" "<hintergrund>"`. Fällt der Wert durch: auf
  dunklem Grund eine hellere, auf hellem Grund eine dunklere Stufe nehmen und im
  Curriculum sichtbar machen, welche Werte gesetzt wurden.
- **Guide-Figur:** bleibt auch bei eigenem CI abstrakt (kein Mensch) und übernimmt die
  `akzent`-Farbe, sofern `guide_figur` nichts anderes sagt.
- **Stil-Block:** der englische Stil-Block des Basis-Presets bleibt die Grundlage;
  `akzent`-Hex im Block ersetzen, `stil_hinweise` anhängen.
- **Branding-Klammer:** Logo/Wortmarke/Footer nur aus dieser Datei — ohne design.md bleibt
  die Lerneinheit neutral (Texttitel, kein Footer-Branding).
- **Dateinamen der Auslieferung:** mit `wortmarke` optional
  `<Wortmarke>_Schulung_<Thema>_<YYYY-MM-DD>.html`, sonst `Schulung_<Thema>_<YYYY-MM-DD>.html`.
