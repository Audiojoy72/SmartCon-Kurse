# Preset: corporate

Heller, sachlicher Business-Look: viel Weißraum, ruhige Karten, eine seriöse Akzentfarbe.
Gut für Compliance, Onboarding in Unternehmen und formelle Kundenschulungen.

## Parameter

- `AKZENT` (Hex) — Default `#1F6FEB` (sachliches Blau). Wird von einer design.md übersteuert.
- `AKZENT_DUNKEL` (Hex) — Default `#1A5FCC` (Hover/aktive Zustände auf hellem Grund).

## Stil-Block (wörtlich in jeden Bild- und Video-Prompt; Prompts immer Englisch)

```
STYLE: clean corporate scene, bright airy atmosphere, soft diffused daylight, muted
neutral tones with a single accent color #1F6FEB, an abstract geometric guide figure
(a small floating faceted prism in the accent color, subtle soft glow) present in the
scene, minimal composition, professional, calm, shallow depth of field, generous
negative space, no readable text, no captions, no logos, no close-up faces, nobody
talking
```

Bei abweichender Akzentfarbe (design.md) den Hex-Wert im Block ersetzen.

## Guide-Figur

Ein **kleines, schwebendes facettiertes Prisma** in der Akzentfarbe mit dezentem Glanz —
spricht die Lernenden direkt an. Kein Mensch; die geometrische Form bleibt über alle
Generierungen konsistent und passt zum sachlichen Look.

## Farbpalette

| Token | Hex | Verwendung |
|---|---|---|
| `--bg` | `#F5F7FA` | Seitenhintergrund |
| `--panel` | `#FFFFFF` | Karten, Quiz-Optionen, Video-Rahmen |
| `--panel2` | `#EEF2F7` | alternative Karten, Hover |
| `--steel` | `#D9E0EA` | Chips, Balken-Spur, inaktive Badges |
| `--accent` | `#1F6FEB` | **der Akzent**: XP, Fortschritt, Buttons, richtige Antwort |
| `--accentdk` | `#1A5FCC` | Hover auf Akzent |
| `--ink` | `#1A2332` | Text |
| `--mute` | `#5A6B80` | Unterzeilen, Hilfetexte |
| `--line` | `#D9E0EA` | Rahmen, Trennlinien (fein, 1 px) |
| `--wrong` | `#C0392B` | **Funktionsfarbe, nur für falsche Antworten** |

Hinweis: Auf hellem Grund sind Kontraste kritischer als auf dunklem — jede gesetzte
Text-/Akzentfarbe gegen `#FFFFFF` und `#F5F7FA` nachrechnen (≥ 4,5:1):
`python3 scripts/kontrast.py "#1F6FEB" "#FFFFFF"`. Fällt eine Farbe durch, eine dunklere
Stufe nehmen (auf hellem Grund dunkler, auf dunklem heller).

## Medien-Defaults

| Medium | Anteil |
|---|---|
| FILM | 1–2 Filme (Eröffnung und/oder Abschluss; heller Look beachten — Stil-Block verwenden) |
| ANIMATION | Hauptteil der Level (Konzepte, Prozesse, Zahlen) |
| BILD | sparsam: Hero + 1–2 Szenario-Illustrationen |

## Kostenrahmen

≈ 60–500 Credits je nach Film-Anteil.
