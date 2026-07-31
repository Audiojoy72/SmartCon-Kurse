# Preset: statisch

Budget-Variante: **kein einziger FILM-Level** — nur beat-synchrone HTML-Szenen plus wenige
KI-Bilder. Fast keine Credits, trotzdem voller Workflow (Curriculum, Gate, Voiceover,
Choreografie, Browser-Test). Gut für erste Entwürfe, kleine Budgets und schnelle
Inhalte-Tests.

## Parameter

- `AKZENT` (Hex) — Default `#4FA3A5` (ruhiges Petrol). Wird von einer design.md übersteuert.
- `AKZENT_HELL` (Hex) — Default `#7FC4BE`.

## Stil-Block (nur für die wenigen Bilder; Prompts immer Englisch)

```
STYLE: minimal dark illustration, deep charcoal background #0E1116, a single simple
geometric shape (circle or diamond) in muted teal #4FA3A5, subtle film grain, flat,
abstract, generous negative space, quiet and focused, no readable text, no captions,
no logos, no people, no faces
```

## Guide-Figur

Eine **reine CSS-Form** (Kreis oder Raute in der Akzentfarbe, dezenter Schein per
`box-shadow`) — **kein generiertes Referenzbild nötig, Phase 3 entfällt**. Lebendig wird
sie über Schweben per CSS-Keyframes und Nick-Impulse an den Beats (siehe SKILL.md,
Phase 6).

## Farbpalette

| Token | Hex | Verwendung |
|---|---|---|
| `--bg` | `#0E1116` | Seitenhintergrund |
| `--panel` | `#171C24` | Karten, Quiz-Optionen |
| `--panel2` | `#1E242E` | alternative Karten, Hover |
| `--steel` | `#242C38` | Chips, Balken-Spur, inaktive Badges |
| `--accent` | `#4FA3A5` | **der Akzent**: XP, Fortschritt, Buttons, richtige Antwort |
| `--accentlt` | `#7FC4BE` | Zwischenüberschriften, Hover |
| `--ink` | `#EAECEF` | Text |
| `--mute` | `#9AA3AF` | Unterzeilen, Hilfetexte |
| `--line` | `#2A323D` | Rahmen, Trennlinien |
| `--wrong` | `#D97A67` | **Funktionsfarbe, nur für falsche Antworten** |

## Medien-Defaults

| Medium | Anteil |
|---|---|
| FILM | **0** — ausnahmslos |
| ANIMATION | **alle** Level (HTML-Szenen, beat-synchron zum Voiceover) |
| BILD | max. 2–3 (Startscreen-Hero, ggf. 1 Szenario, Abschlussbild) |

## Kostenrahmen

≈ **10–40 Credits gesamt** (nur Bilder à ~2–4 Credits plus Voiceover à ~0,4 Credits/Szene).
Hinweis: Die Choreografie trägt die Produktion — Tempo-Regel (atempo), Beat-Sync aus den
Wort-Zeitstempeln und lebendige CSS-Figur gelten hier unverändert und sind umso wichtiger,
weil kein Filmmaterial ablenkt.
