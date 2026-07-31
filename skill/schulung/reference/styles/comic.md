# Preset: comic

Zeichentrick/Comic-Look: flächige Farben, kräftige Outlines, verspielte Panel-Komposition.
Gut für lockere Themen, Coaching, Kinder/Jugendliche und interne Schulungen mit Humor.

## Parameter

- `AKZENT` (Hex) — Default `#E4572E` (kräftiges Orange-Rot). Wird von einer design.md
  übersteuert.
- `AKZENT_HELL` (Hex) — Default `#F2A65A`.

## Stil-Block (wörtlich in jeden Bild- und Video-Prompt; Prompts immer Englisch)

```
STYLE: flat 2D cartoon illustration, bold black outlines, bright flat colors, subtle
halftone texture, a small expressive mascot character (a round star-shaped figure in
accent color #E4572E with simple dot eyes, no mouth) as the guide, dynamic panel
composition, playful, clean vector look, warm paper background #F7F3E8, no readable
text, no captions, no written words anywhere, no logos, no photorealism
```

Bei abweichender Akzentfarbe (design.md) den Hex-Wert im Block ersetzen.

## Guide-Figur

Ein **gezeichnetes Maskottchen**: rundliche Stern-Figur in der Akzentfarbe mit einfachen
Punktaugen — spricht die Lernenden direkt an. Kein Mensch; die simple Form bleibt über alle
Generierungen konsistent. Für HTML-Szenen zwei Haltungen generieren und an den Beats
überblenden (siehe SKILL.md, Phase 6).

## Farbpalette

| Token | Hex | Verwendung |
|---|---|---|
| `--paper` | `#F7F3E8` | Seitenhintergrund |
| `--panel` | `#FFFFFF` | Karten, Quiz-Optionen |
| `--panel2` | `#F0EBDD` | alternative Karten, Hover |
| `--steel` | `#E2DCCB` | Chips, Balken-Spur, inaktive Badges |
| `--accent` | `#E4572E` | **der Akzent**: XP, Fortschritt, Buttons, richtige Antwort |
| `--accentlt` | `#F2A65A` | Zwischenüberschriften, Hover |
| `--ink` | `#1D1D24` | Text, Outlines |
| `--mute` | `#6B6759` | Unterzeilen, Hilfetexte |
| `--line` | `#1D1D24` | Rahmen (kräftige Comic-Outlines, 2–3 px) |
| `--wrong` | `#B03A2E` | **Funktionsfarbe, nur für falsche Antworten** |

Helles Theme: Rahmen dürfen hier kräftig und dunkel sein (Comic-Outlines). Akzent nie als
Flächenfarbe außer aktivem Button und Fortschrittsbalken. Kontrast nachrechnen:
`python3 scripts/kontrast.py "<farbe>" "#FFFFFF"` — auf hellem Grund braucht es dunklere
Stufen als auf dunklem.

## Medien-Defaults

| Medium | Anteil |
|---|---|
| FILM | 1–2 Filme pro Schulung (nur wenn Bewegung wirklich nötig ist) |
| ANIMATION | Hauptteil der Level |
| BILD | höherer Anteil als in cinematic — flächige Illustrationen rendert GPT Image 2 sehr konsistent; gern 1 Bild pro Interaktions-Screen |

## Kostenrahmen

≈ 40–300 Credits je nach Umfang (wenig Film, viele Bilder à ~2–4 Credits).
