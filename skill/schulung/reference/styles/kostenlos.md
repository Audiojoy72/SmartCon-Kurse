# Preset: kostenlos

Null-Credit-Variante: **kein Higgsfield nötig** — keine Videos, keine KI-Bilder,
kein Voiceover. Die komplette interaktive Lerneinheit (Level, Interaktionen,
Quiz, XP, Gamification, Merkblatt) entsteht aus reinem HTML/CSS/JS. Alle Level
sind schrittgesteuerte HTML-Szenen (siehe SKILL.md, „Medienloser Zweig").

## Parameter

- `AKZENT` (Hex) — Default `#E8A33D` (warmes Amber). Wird von einer design.md
  übersteuert.
- `AKZENT_HELL` (Hex) — Default `#F2C063`.

## Stil-Block

Es gibt **keine** KI-Generierung — der Stil-Block entfällt. Die Optik kommt
vollständig aus CSS: dunkles Theme, ein Akzent, geometrische CSS-Formen und
CSS-Icons (Shapes, Rahmen, Pseudoelemente) statt KI-Bilder. Trotzdem hochwertig:
großzügige Abstände, ruhige Typografie, dezente Übergänge.

## Guide-Figur

Eine **reine CSS-Form** (Raute oder Kreis in der Akzentfarbe, dezenter Schein
per `box-shadow`) — **kein Referenzbild, Phase 3 entfällt**. Lebendig wird sie
über Schweben per CSS-Keyframes und einen kurzen Impuls bei jedem neuen Schritt
(siehe SKILL.md, Phase 6 — schrittgesteuerte Variante). `prefers-reduced-motion`
respektieren.

## Farbpalette

| Token | Hex | Verwendung |
|---|---|---|
| `--bg` | `#101318` | Seitenhintergrund |
| `--panel` | `#181D24` | Karten, Quiz-Optionen |
| `--panel2` | `#1F2630` | alternative Karten, Hover |
| `--steel` | `#27303C` | Chips, Balken-Spur, inaktive Badges |
| `--accent` | `#E8A33D` | **der Akzent**: XP, Fortschritt, Buttons, richtige Antwort |
| `--accentlt` | `#F2C063` | Zwischenüberschriften, Hover |
| `--ink` | `#EDEFF2` | Text |
| `--mute` | `#9AA3AF` | Unterzeilen, Hilfetexte |
| `--line` | `#2C3540` | Rahmen, Trennlinien |
| `--wrong` | `#D97A67` | **Funktionsfarbe, nur für falsche Antworten** |

## Medien-Defaults

| Medium | Anteil |
|---|---|
| FILM | **0** — ausnahmslos |
| ANIMATION | **alle** Level (HTML-Szenen, schrittgesteuert — keine Tonspur) |
| BILD | **0** — CSS-Formen und CSS-Icons statt KI-Bilder |
| Voiceover | **0** — das Skript wird Bildschirmtext (Sprechertext der Szene) |

## Kostenrahmen

**0 Credits — kein Higgsfield nötig.**

Hinweis: Ohne Voiceover und Filmmaterial tragen die Schritt-Choreografie
(Weiter-Tippen, sichtbarer Schrittzähler) und die CSS-Figur die Produktion —
die Regeln des medienlosen Zweigs in der SKILL.md gelten hier vollständig.
