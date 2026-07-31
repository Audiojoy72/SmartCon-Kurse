# Preset: cinematic

Dunkler, cineastischer Look mit genau **einer Akzentfarbe** — hohe Kontraste, reduziert,
keine Deko. Das ist das **Default-Preset** des Skills (gilt, wenn weder ein anderes Preset
noch eine design.md gewählt wurde).

## Parameter

- `AKZENT` (Hex) — Default `#C9A84C` (warmes Gold). Wird von einer design.md übersteuert.
- `AKZENT_HELL` (Hex) — Default `#E6CF8A` (hellere Stufe für Hover/Zwischenüberschriften).

## Stil-Block (wörtlich in jeden Bild- und Video-Prompt; Prompts immer Englisch)

```
STYLE: a single glowing orb (warm accent color #C9A84C, soft inner light, subtle
concentric ring) floating in a dark void (#060611), volumetric haze, thin rim-light
in the accent color, cinematic, minimal, high contrast, no other light sources,
no readable text, no captions, no logos, no people, no faces, nobody talking
```

Bei abweichender Akzentfarbe (design.md) beide Hex-Werte im Block ersetzen.

## Guide-Figur

Ein **leuchtender Orb in der Akzentfarbe** auf dunklem Grund — spricht die Lernenden direkt
an. Nie ein Mensch: abstrakte Objekte bleiben über alle KI-Generationen hinweg konsistent.
Die Akzentfarbe ist zugleich die Bildwelt.

Als CSS-Element in HyperFrames-Szenen und im HTML:

```css
.orb {
  width: 120px; height: 120px; border-radius: 50%;
  background: radial-gradient(circle at 38% 34%, #F2DFA6 0%, #C9A84C 45%, #8A6D1F 100%);
  box-shadow: 0 0 60px rgba(201,168,76,.45), 0 0 140px rgba(201,168,76,.18);
}
```

(Bei anderer Akzentfarbe Verlauf und Schatten-Farben entsprechend ableiten.)

## Farbpalette

| Token | Hex | Verwendung |
|---|---|---|
| `--navy` | `#060611` | Seitenhintergrund |
| `--panel` | `#101120` | Karten, Quiz-Optionen, Video-Rahmen |
| `--panel2` | `#17182B` | alternative Karten, Hover |
| `--steel` | `#22243A` | Chips, Fortschrittsbalken-Spur, inaktive Level-Badges |
| `--gold` | `#C9A84C` | **der Akzent**: XP, Fortschritt, aktives Level, Buttons, richtige Antwort |
| `--goldlt` | `#E6CF8A` | Zwischenüberschriften, Hover auf Akzent |
| `--ink` | `#F5F3EC` | Text |
| `--mute` | `#989AB2` | Unterzeilen, Hilfetexte |
| `--line` | `#3A3A52` | Rahmen, Trennlinien |
| `--wrong` | `#D97A67` | **Funktionsfarbe, nur für falsche Antworten** |

Akzent ist Akzent, nie Flächenfarbe — Ausnahme: der aktive Button und der Fortschrittsbalken.
Keine weiteren Farben einführen: keine Verläufe über mehrere Farbtöne, keine Deko-Emojis.
Für „richtig" ist der Akzent zuständig; `--wrong` darf ausschließlich Quiz-Feedback markieren,
nie Überschriften, Rahmen oder Flächen.

**Accessibility:** Richtig/falsch nie allein über Farbe — immer zusätzlich Zeichen
(`✓` / `✕`) und Feedbacktext. Alle Textfarben erfüllen WCAG AA auf beiden Kartenfarben
(nachgerechnet, nicht geschätzt):

| Farbe | auf `--navy` | auf `--panel` | auf `--panel2` |
|---|---|---|---|
| `--ink` | 18,2 | 16,8 | — |
| `--goldlt` | 13,1 | 12,2 | — |
| `--gold` | 8,8 | 8,2 | — |
| `--mute` | 7,3 | 6,8 | — |
| `--wrong` | 6,7 | 6,2 | 5,8 |

Wer die Farben ändert, rechnet nach: `python3 scripts/kontrast.py "#D97A67" "#101120"`.

## Medien-Defaults

| Medium | Anteil |
|---|---|
| FILM | 2–3 Filme pro Schulung (nur Story-Momente, Emotion, Situationen) |
| ANIMATION | der Großteil der Level (Konzepte, Listen, Modelle, Prozesse) |
| BILD | 1 Hero + 1 pro Entscheidungsszenario + Abschlussbild |

## Kostenrahmen

Kompakt-Lektion ≈ 110 Credits, volle Schulung ≈ 1000 Credits. Die Videosekunden dominieren
die Kosten zu über 95 % — Hebel: Filme sparsam, Shot-Längen exakt aufs Voiceover schneiden.
