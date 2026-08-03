---
name: schulung
description: >
  Interaktive Schulung, Lektion oder Kursmodul als eine einzige offline lauffähige HTML-Datei
  erstellen — mit austauschbarem Stil (Preset-Bibliothek oder eigene design.md), cineastischen
  KI-Videos (Higgsfield/Seedance 2.0), beat-synchronen Erklär-Animationen (HyperFrames),
  Voiceover in beliebiger Sprache (ElevenLabs über Higgsfield), KI-Bildern, Gamification und
  Quiz-Interaktionen. Für Kundenschulungen, Mitarbeiterschulung, Compliance, Onboarding,
  Coaching-Module und E-Learning. Nutzen bei: "interaktive Schulung", "Schulungsvideo",
  "E-Learning", "Lernmodul", "Kursmodul", "Onboarding-Schulung".
---

# /schulung — Interaktive Lerneinheit

Erstellt eine story-getriebene, interaktive Lernreise als **eine einzige HTML-Datei**:
Level-Struktur, Videos mit Voiceover, Erklär-Animationen synchron zur Stimme, Spiele und
Entscheidungsszenarien, Wissenscheck, Fortschritt in localStorage. Läuft offline per
Doppelklick, teilbar per Mail/Drive/LMS.

## Preset und design.md: zwei Achsen, nicht eine Rangfolge

**Das Preset bestimmt die Machart**, die **`design.md` nur die Optik**. Beide
sind unabhängig und werden kombiniert — eine `design.md` ersetzt das Preset
nicht.

- **Presets** unter `reference/styles/` (`cinematic` = Default, `comic`,
  `corporate`, `statisch`, `kostenlos`) legen Machart, Guide-Figur,
  Medien-Defaults und Kostenrahmen fest. Damit entscheiden sie auch, **ob
  Higgsfield überhaupt zum Einsatz kommt** (`kostenlos` = nie, 0 Credits).
- Eine **`design.md`** im Projektordner (Kunden-CI: Akzentfarbe, Logo-Pfad,
  Wortmarke, Footer-Zeile, Stil-Hinweise — Vorlage:
  `reference/design-vorlage.md`) liefert Farben, Typografie und Tonalität.

Bei Konflikten gilt:

1. **Optik** (Farben, Schriften, Tonalität) → `design.md` schlägt das Preset
2. **Machart, Medienplan, Kosten** → immer das Preset, auch wenn die `design.md`
   dazu etwas sagt
3. ohne `design.md` → Optik ebenfalls aus dem Preset, Default `cinematic`

Eine `cinematic`-Schulung mit mitgegebener `design.md` ist also weiterhin
cinematic — nur eben in der CI des Kunden.

Das gewählte Preset (und ggf. die design.md) **vor Phase 2 lesen**, nicht erst vor Phase 9:
sie bestimmen schon die Guide-Figur und die Bild-Prompts.

## Der Ablauf hat zwei Teile — niemals vermischen

| | **TEIL 1 — Curriculum** | **TEIL 2 — Produktion** |
|---|---|---|
| Ergebnis | `curriculum.md` — der komplette Inhalt als Text | die fertige HTML-Datei |
| Kosten | 0 Credits | ~110–1000 Credits (Preset `statisch`: ~10–40, Preset `kostenlos`: 0) |
| Dauer | Minuten | ~1 Stunde |
| Dazwischen | **Freigabe-Gate: explizites „Go" des Users abwarten** | |

**Warum getrennt:** Eine Textänderung in Teil 1 ist gratis — dieselbe Änderung nach der
Produktion kostet neues Voiceover, neuen Render und ggf. einen neuen Film (bei 9 Credits pro
Videosekunde schnell dreistellig). Außerdem muss der Inhalt oft von Dritten freigegeben werden
(Recht, Compliance, Kunde, Fachabteilung) — die lesen ein Dokument, kein fertiges Video.

**Bringt der User bereits Material mit** (Skript, Kurskonzept, Foliensatz, Richtlinie), wird
Teil 1 zum Prüfen und Umbauen: Inhalt auf Level-Struktur mappen, Lücken benennen, Medienplan
und Interaktionen ergänzen. Nicht neu erfinden, was schon da ist.

---

# TEIL 1 — CURRICULUM (keine Credits)

## Phase 0 — Briefing (per AskUserQuestion, alle fünf Fragen auf einmal)

Ohne diese Angaben nicht starten — sie bestimmen Umfang, Ton, Stil und Produktionskosten.

1. **Thema & Lernziele** — Worum geht es, und was sollen die Lernenden danach können bzw.
   anders machen? Gibt es vorhandenes Material als Grundlage?
2. **Zielgruppe & Vorwissen** — Mitarbeitende / Coaching-Klienten / Kunden-Team /
   Schüler:innen / Kurskäufer; Einsteiger, Fortgeschrittene oder gemischt?
3. **Sprache** — Sprache aller Texte, Stimmen und Bildschirmtexte. Keine Annahme treffen.
4. **Dauer** — bestimmt die Level-Anzahl (Tabelle unten).
5. **Stil** — **Preset** aus `reference/styles/` (`cinematic` = Default, `comic`,
   `corporate`, `statisch`, `kostenlos`) oder eigene **`design.md`**? Bei design.md
   zusätzlich prüfen:
   Akzentfarbe (Hex), Logo-Datei, Wortmarke, Footer-Zeile, Stil-Hinweise. Fehlt etwas davon,
   im Curriculum als offene Position führen, nicht erfinden.

**„State, don't ask" (nennen, nicht fragen):** Ansprache leitet sich aus der Zielgruppe ab —
locker/duzend für Coaching, Kurse und interne Schulungen; formell/siezend für Compliance,
regulierte Branchen und fremde Kunden-Teams. Ebenso gesetzt: 16:9-Videos, das Theme und die
Guide-Figur des gewählten Presets, XP + Level-Badges. Im Curriculum sichtbar machen, damit
der User widersprechen kann.

### Dauer → Struktur (Level = 1 Video/Animation + 1 Interaktion)

| Gewünschte Dauer | Level | Voiceover je Szene |
|---|---|---|
| ~10–15 Min (Kompakt-Lektion) | 3–4 | ~25–35 s |
| ~20–30 Min (Standard-Modul) | 5–6 | ~30–40 s |
| ~30–45 Min (volle Schulung) | 7–8 | ~35–45 s |
| 60+ Min (Kurs) | in Module à 6–8 Level teilen, je eine HTML-Datei | — |

Faustregel: Ein Level kostet die Lernenden ~4–6 Minuten. Bei 60+ Min NICHT eine Riesendatei
bauen — mehrere Modul-Dateien plus Startscreen mit Modulübersicht.

### Sprachregeln (bei jeder Sprache gleich)

- **Lernenden-Texte** (Voiceover, Bildschirmtexte, Quiz, Feedback) in der Zielsprache.
- **Bild- und Video-Prompts IMMER auf Englisch** — die Modelle sind darauf trainiert. Dazu
  „no readable text, no captions" im Prompt, damit kein falschsprachiger Text im Bild landet.
- **Stimme muss zur Sprache passen:** `higgsfield voices list` → Preset-Stimme der Zielsprache wählen,
  Test-Sample generieren und in dieser Sprache transkribieren (`transkribieren.sh <datei> <code>`).
- **Layout je Sprache prüfen:** Deutsch/Finnisch haben lange Komposita, die Titel sprengen;
  Spanisch/Französisch brauchen mehr Zeilen.

## Phase 1 — Recherche & Stoffsammlung

- Bei Fach-, Rechts- und Compliance-Themen: **aktuellen Stand recherchieren** (WebSearch).
  Gesetze und Standards ändern sich; Quellen mit Datum notieren.
- Vorhandenes Material des Users sichten und als Primärquelle behandeln.
- Aussortieren: Was ist wirklich handlungsrelevant für diese Zielgruppe? Lieber 5 Dinge, die
  sitzen, als 15 zum Vergessen.

## Phase 2 — Curriculum-Dokument schreiben

Als `curriculum.md` im Projektordner anlegen — es ist ein eigenständiges Dokument, das auch
ohne die spätere HTML-Datei Sinn ergibt und weitergereicht werden kann.

**Story-Rahmen mit Guide-Figur:** Default ist die **abstrakte Guide-Figur des gewählten
Presets** (bei `cinematic` ein leuchtender Orb) — NIEMALS ein Mensch, weil abstrakte Objekte
über alle KI-Generationen hinweg konsistent bleiben. Die Figur spricht die Lernenden direkt
an. Bei design.md übernimmt die Figur die dort gesetzte Akzentfarbe bzw. Beschreibung.

### Aufbau von `curriculum.md`

1. **Steckbrief** — Thema, Zielgruppe, Sprache, Dauer, Ansprache, **Stil (Preset/design.md)
   und gesetzte CI-Werte**, Guide-Figur, Stand/Datum
2. **Lernziele** — übergeordnet plus eines pro Level, formuliert als „Die Lernenden können …"
3. **Level-Übersicht** als Tabelle: Level | Lernziel | Merksatz | Medium | Interaktion
4. **Pro Level ausführlich:**
   - Lernziel und **Merksatz** (der eine Satz, der hängenbleiben soll)
   - **Lehrtext** — die eigentliche fachliche Substanz in Prosa. Das ist der Kern des
     Dokuments und die Grundlage für Voiceover und Bildschirmtexte.
   - **Voiceover-Skript** in der Zielsprache (Wortzahl zur Zieldauer: ~2,5 Wörter/Sekunde)
   - **Medienplan** — genau eine Festlegung pro Level:
     - `FILM` → Seedance-Prompt (Englisch, mit dem Stil-Block des gewählten Presets)
       + geplante Shot-Längen
     - `ANIMATION` → HyperFrames-Beat-Plan (welches Element erscheint zu welcher Aussage)
     - optional `BILD` → GPT-Image-2-Prompt (Englisch) für den Interaktions-Screen
   - **Interaktion vollständig ausformuliert** — Fragen, Optionen, Auflösungen, Feedbacktexte, XP
5. **Abschluss-Check** — alle Fragen mit richtiger Antwort und Ablenkern
6. **Zusammenfassung / Merkblatt** — alle Merksätze für den Abschluss-Screen
7. **Quellen & Stand** — bei Fachthemen Pflicht (Gesetze, Normen, Standards mit Datum). Das
   ist fachliche Belegpflicht und fällt **nicht** unter die Quellen- und Herkunftsregel
   (Abschnitt unten), die sich auf die Herkunft des Ausgangsmaterials bezieht.
8. **Produktionsschätzung** — Credits nach der Tabelle unten

**Medium richtig wählen** (bestimmt Kosten und Qualität):
| Inhalt | Medium |
|---|---|
| Story-Moment, Emotion, Menschen in Situationen | FILM (Seedance) — teuer, sparsam einsetzen |
| Konzepte, Listen, Modelle, Regeln, Prozesse, Zahlen | ANIMATION (HyperFrames) — gratis, scharfer Text |
| Kontext für einen Interaktions-Screen | BILD (GPT Image 2) — fast gratis |

Richtwert: 2–3 Filme pro Schulung, alles andere Animation — die Presets legen eigene
Medien-Defaults fest (Preset `statisch`: 0 Filme).

### Interaktions-Baukasten (pro Level eine ANDERE Form — Abwechslung ist der Punkt)

| Interaktion | Wofür |
|---|---|
| Selbsteinschätzung (Slider) | Onboarding, Vorwissen abholen, Personalisierung |
| Vorhersage-Spiel mit Wahrscheinlichkeits-Balken | Aha-Momente, Intuition vs. Realität |
| Irrtum-oder-Fakt-Karten (Flip) | Fakten vs. verbreitete Irrtümer |
| „Finde die N Fehler" (Sätze/Elemente anklicken) | Kritisches Prüfen, Fehlersuche |
| Drag & Drop in Kategorien | Klassifizierungen, Hierarchien, Zuordnungen |
| Szenario-Quiz mit 2 Buttons | Binäre Unterscheidungen |
| Klickbare Zeitleiste | Abläufe, Daten, Meilensteine |
| Branching-Story (3 Optionen, Konsequenz-Feedback) | Alltagsentscheidungen, Verhalten |
| Rapid-Fire mit Timer | Do's & Don'ts, schnelles Urteil |
| Sortier-/Reihenfolge-Aufgabe | Prozesse, Schritt-für-Schritt-Abläufe |
| Abschluss-Check (8–10 Fragen, gemischt) | Wissenssicherung am Ende |

**Abschluss:** Zusammenfassungs-Screen mit den Merksätzen aller Level, erreichten XP und
Ergebnis des Abschluss-Checks — plus druckbarem Merkblatt (Print-CSS). (Ein Zertifikat ist
standardmäßig NICHT Teil der Schulung; nur bauen, wenn der User es ausdrücklich verlangt.)

## ⛔ Freigabe-Gate

`curriculum.md` an den User ausliefern und **auf ein explizites „Go" warten**. Vorher wird
kein einziger Credit ausgegeben. Beim Übergeben diese Punkte zur Prüfung nennen:

- Decken die Level die Lernziele ab — fehlt etwas Handlungsrelevantes?
- Stimmen Fakten und Rechtsstand (Quellen genannt)?
- Passen Ansprache und Beispiele zur Zielgruppe?
- Stimmen Stil und CI-Werte (Preset/design.md)?
- Ist die geschätzte Dauer realistisch?
- Ist die Credit-Schätzung in Ordnung?

Änderungswünsche im Dokument einarbeiten und erneut vorlegen. Erst nach dem „Go" → Teil 2.

## Quellen- und Herkunftsregel

Entsteht die Schulung aus fremdem Material (Video, Foliensatz, Blogpost, Richtlinie eines
Dritten), erscheint sie **als eigenständige Publikation**:

- Keine Nennung von Autoren, Kanälen, Original-Titeln oder „basierend auf …"-Hinweisen im
  Curriculum, in der HTML-Datei oder im Voiceover.
- Personen nur nennen, wenn sie **fachlicher Inhalt** sind (der Urheber eines Konzepts, ein
  Buchautor) — nicht als Quellenangabe des verarbeiteten Materials.
- **Ausnahme, die bleibt:** Bei Fach-, Rechts- und Compliance-Themen gehören Gesetze,
  Normen und Standards mit Stand-Datum ins Curriculum-Kapitel „Quellen & Stand". Das ist
  fachliche Belegpflicht, keine Herkunftsangabe.
- Zweifel an der Verlässlichkeit des Ausgangsmaterials **im Chat mit dem Auftraggeber
  klären**, nie in der Lerneinheit.

---

# TEIL 2 — PRODUKTION (verbraucht Credits — außer Preset `kostenlos`)

Ab hier ist `curriculum.md` die verbindliche Quelle. Nicht improvisieren, nicht umformulieren —
was produziert wird, steht im Dokument. Fällt bei der Produktion doch ein inhaltlicher Fehler
auf: erst das Curriculum korrigieren, dann produzieren.

## Medienloser Zweig — Preset `kostenlos` (0 Credits)

Beim Preset `kostenlos` (oder einem Medienplan ganz ohne FILM/BILD/Voiceover) **entfallen die
Phasen 3, 4, 5, 7 und 8**. TEIL 2 läuft dann so:

**Phase 2.5 (Preflight im Kostenlos-Modus) → Phase 6 (HTML-Szenen) → Phase 9 (HTML-Bau) →
Phase 10 (Browser-Test) → Phase 11 (Auslieferung).**

Es wird **kein einziger `higgsfield`-Aufruf** gemacht — weder `generate` noch `cost`.
Das Ergebnis bleibt die komplette interaktive Lerneinheit (Level, Interaktionen, Quiz, XP,
Gamification, Merkblatt) — nur ohne Videos, ohne KI-Bilder, ohne Voiceover.

- **Preflight im Kostenlos-Modus:** `SCHULUNG_KOSTENLOS=1 bash scripts/preflight.sh` —
  Higgsfield, ffmpeg, Node und Whisper werden als „nicht nötig" gemeldet statt zu failen.
- **HTML-Szenen ohne Tonspur — schrittgesteuert statt `timeupdate`-Choreografie:** Die
  Elemente der Szene erscheinen nacheinander per „Weiter"-Tippen/Klick (optional mit sanftem
  Auto-Takt ~4 s), dazu Tastatur-Steuerung (Pfeiltasten/Enter) und ein sichtbarer
  Schrittzähler („2 von 7"). Die Regel bleibt: Der Inhalt darf nie am Abspielen hängen —
  wer vorspult oder die Szene verlässt, bekommt beim Verlassen **alle Elemente sichtbar**
  geschaltet.
- **Das Voiceover-Skript wird Sprechertext:** Es wird im Curriculum NICHT gestrichen, sondern
  erscheint als Fließtext/Bildschirmtext der Szene — die Substanz bleibt vollständig erhalten.
- **Phase 9 im medienlosen Zweig:** kein `<audio>`, kein `<video>`, kein „Ton an!"-Hinweis,
  kein Video-Screen — stattdessen der Schritt-Mechanismus. Die Base64-Einbettung entfällt
  größtenteils (keine Medien) — die Datei wird klein (deutlich unter 1 MB).
- **Phase 10 im medienlosen Zweig:** zusätzlich die Schritt-Steuerung vollständig
  durchklicken — vor/zurück, Tastatur (Pfeiltasten/Enter), Schrittzähler, und prüfen, dass
  beim Verlassen einer Szene alle Elemente sichtbar sind.

## Phase 2.5 — Preflight (Pflicht, direkt nach dem „Go")

```sh
bash scripts/preflight.sh
```

Prüft ffmpeg, Node-Version, den Transkriptions-Weg und die Higgsfield-CLI samt Guthaben.
**Bricht der Preflight ab, nichts produzieren** — sonst scheitert die Kette mitten
in einer bezahlten Sequenz. Beim Preset `kostenlos` stattdessen der Kostenlos-Modus:
`SCHULUNG_KOSTENLOS=1 bash scripts/preflight.sh` (siehe „Medienloser Zweig" oben).

Danach jede geplante Generierung mit `higgsfield generate cost <job_type> …` durchrechnen und
die Summe gegen `higgsfield account status` halten (entfällt im medienlosen Zweig — dort gibt
es keine Generierungen). **Reicht das Guthaben nicht, den User
fragen, bevor irgendetwas generiert wird** — nicht „so weit es reicht" produzieren, das
hinterlässt eine halbe Schulung und leere Credits.

## Phase 3 — Referenzbild der Guide-Figur (Konsistenz-Anker!)

```sh
higgsfield generate create gpt_image_2 --prompt "<Stil-Block + Figur>" \
  --aspect_ratio "16:9" --resolution 1k --quality high --wait
```
- Den Stil-Block des gewählten Presets wörtlich verwenden, Figur exakt beschreiben
  (Farben, Form, Details, Umgebung) + „no text, no captions". Entfällt beim Preset
  `statisch` (dort ist die Figur reines CSS) und wenn eine design.md eigene Figuren liefert.
- Zwei Kandidaten erzeugen (zweimal aufrufen, 4 Credits je Bild). **Beide ansehen und den
  OHNE eingebrannten Text wählen** — GPT Image 2 ist stark im Text-Rendering und schreibt
  deshalb besonders gern den Namen ins Bild; der würde über die Referenz in alle Videos
  durchbluten.
- Das gewählte Bild herunterladen und in **jedem** Video-Aufruf als
  `--image-references <datei>` mitgeben. Lokale Pfade lädt die CLI selbst hoch — ein
  separater Upload-Schritt ist nicht nötig.

## Phase 4 — Voiceover (ElevenLabs ÜBER Higgsfield)

**Warum über Higgsfield:** Direkte ElevenLabs-Free-Accounts blockieren Library-Stimmen per API
und erlauben keine kommerzielle Nutzung. Higgsfields `text2speech_v2` mit `variant elevenlabs`
ist derselbe Stack, läuft über Higgsfield-Credits (~0,45 Credits für ein 35-s-Skript, nachgemessen)
mit kommerzieller Lizenz.

```sh
higgsfield generate create text2speech_v2 --variant elevenlabs \
  --voice_type preset --voice_id 023ebf5e-1970-40d8-825c-a5ef6a1dd4ff \
  --prompt "<Voiceover-Skript des Levels>" --wait
```
- Bewährt für Deutsch: **„Ines"** (`023ebf5e-1970-40d8-825c-a5ef6a1dd4ff`) — ruhig, klar;
  „Elena" (`ca83ca7f-c186-493d-bd69-0d765fa861b2`) spricht von Haus aus schneller.
  Beide IDs am 31.07.2026 gegen `higgsfield voices list` geprüft. Für andere Sprachen
  `higgsfield voices list --json` abfragen und per Test-Sample prüfen.
- **⚠ TEMPO-REGEL:** TTS-Erzählstimmen sind fürs Lernen zu langsam. IMMER nachbeschleunigen:
  ```sh
  ffmpeg -i vo.mp3 -filter:a "atempo=1.15" -b:a 128k vo_fast.mp3
  ```
  1,15x klingt natürlich (tonhöhen-neutral); Ziel ist normales Sprechtempo, nicht Hörbuch-Ruhe.
  Faktor am Test-Sample verifizieren — je nach Stimme und Sprache passen auch 1,1 oder 1,2.
- Danach die **beschleunigten** MP3s transkribieren — die Segment-Timestamps sind die
  Choreografie-Grundlage für Phase 6 und legen die endgültigen Szenenlängen fest:
  ```sh
  bash scripts/transkribieren.sh vo_fast.mp3 de > vo.json
  ```
  Das Skript nutzt standardmäßig ein **lokal installiertes whisper**
  (`--output_format json --word_timestamps True`, Modell per `WHISPER_MODEL` wählbar,
  Default `large-v3`; läuft notfalls auf CPU, dann deutlich langsamer) und gibt JSON mit
  **Wort**-Zeitstempeln zurück, dazu unter `beats` die daraus abgeleiteten Satzgrenzen.
  **Segment-Granularität reicht nicht:** Ein 35-Sekunden-Text kommt als ein bis zwei Segmente
  zurück, damit lässt sich nichts choreografieren. Erst die Satz-Beats (10 bis 12 je Level)
  ergeben eine Choreografie, die zur Stimme passt.
  Ist ein schnellerer Transkriptionsdienst verfügbar (z. B. ein eigener GPU-Server), lässt
  er sich über die Umgebungsvariable **`WHISPER_REMOTE_CMD`** anbinden: ein Kommando, das
  die Audiodatei auf stdin bekommt und `verbose_json` mit Wort-Zeitstempeln auf stdout
  liefert (Beispiel im Skriptkopf von `transkribieren.sh`).

## Phase 5 — Cineastische Videos (Seedance 2.0) — nur für die `FILM`-Level

**Immer Seedance 2.0, immer 1080p, immer 16:9** — die Länge ist der einzige variable Parameter
und wird pro Shot passend gewählt.

```sh
higgsfield generate create seedance_2_0 --prompt "<Stil-Block + Shot>" \
  --aspect_ratio "16:9" --resolution 1080p --mode std \
  --duration <4–15> --generate_audio false \
  --image-references <referenzbild.png> --wait --wait-timeout 20m
```
- `--mode std` ist Pflicht — 1080p und 4k funktionieren nicht mit `fast` (die CLI lehnt die
  Kombination ab). Ebenso wenig taugt `seedance_2_0_mini`: es kann nur 480p/720p.
- `--generate_audio false` nicht vergessen, sonst kommt eine Tonspur mit, die das Voiceover
  stört.
- **Länge pro Shot bewusst wählen** (4–15 s erlaubt, kostet 9 Credits/Sekunde):

  | Shot-Typ | Dauer |
  |---|---|
  | Kurzer Beat, Übergang, Stimmungsbild | 4–6 s |
  | Standard-Szene mit einer Aktion | 8–10 s |
  | Ausdrucksvolle Szene mit Handlungsbogen | 12–15 s |

  Bei Sequenzen die Shot-Längen so planen, dass ihre **Summe knapp über der Voiceover-Länge**
  liegt — jede überschüssige Sekunde wird weggeschnitten und ist bezahlt. Beispiel: 38 s
  Voiceover → 15 + 15 + 9 s statt 15 + 15 + 15 s (spart 54 Credits).
- Identischer Stil-Block in jedem Prompt (der des gewählten Presets, inklusive
  „no readable text, no captions, no speech, nobody talking") — Seedance kann keinen sauberen
  Text rendern.
- `higgsfield generate cost seedance_2_0 …` mit denselben Parametern, bevor eine ganze
  Sequenz beauftragt wird — kostet nichts und nennt den Preis auf den Credit genau.
- Schlägt der Server einen Preset vor: mit `--declined_preset_id` wörtlich generieren.

**⚠ LÄNGE-REGEL: Voiceover länger als 15 s → Shots VERKETTEN, NIEMALS loopen.**
Boomerang-Loops (vor/zurück) sehen kaputt aus — die Figur verschwindet und taucht wieder auf.
Stattdessen nahtlose Sequenz:
1. Letzten Frame extrahieren: `ffmpeg -sseof -0.1 -i clip.mp4 -frames:v 1 last.jpg`
2. Nächsten Shot mit `--start-image last.jpg` generieren (die CLI lädt die lokale Datei
   selbst hoch), Prompt beginnt mit „SHOT: continuing seamlessly from the start frame — …"
   (Kamera/Handlung weiterführen)
3. Shots per ffmpeg concat (vorher auf einheitliche fps/Auflösung normalisieren), auf
   VO-Länge + 1 s trimmen; fehlt < 1,5 s: letzten Frame einfrieren (`tpad=stop_mode=clone`).
   So entsteht z. B. ein 38-s-Intro aus 3 Shots (15+15+9).
- Dramaturgie nutzen: Die Sequenz darf einen Bogen erzählen (Warnung → Zögern → Entwarnung).

## Phase 6 — Erklär-Szenen — für alle `ANIMATION`-Level

**Erst entscheiden: gerendertes Video oder animiertes HTML?** Das Ziel ist eine HTML-Datei,
deshalb ist der Umweg über MP4 meist der schlechtere Weg.

| | **HTML-Szene** (Standard) | **HyperFrames-Video** |
|---|---|---|
| Text | in jeder Bildschirmgröße scharf, echtes Markup | auf die Renderauflösung festgelegt |
| Dateigröße | nur die Tonspur, ~1 MB je Level | 4–8 MB je Szene |
| Textkorrektur später | eine Zeile im Quelltext | neuer Render, neues Voiceover |
| Vorlesbarkeit, Zoom, Kontrast | bleibt erhalten | verloren, es ist ein Bild |
| Wofür trotzdem sinnvoll | — | wenn die Szene als Video weiterverwendet wird (LMS, Social, Deck) |

**HTML-Szene bauen:** Elemente als `<div>` mit Klasse je Typ (Kopf, Merksatz, Aufzählung),
alle unsichtbar, und ein `timeupdate`-Handler auf dem `<audio>`, der sie an ihrem Beat
einblendet. Wer die Szene überspringt, bekommt beim Verlassen alle Elemente sichtbar
geschaltet — der Inhalt darf nie am Abspielen hängen. **Ohne Tonspur** (Preset `kostenlos`)
gilt stattdessen die schrittgesteuerte Variante — siehe „Medienloser Zweig" oben.

**Figuren lebendig machen, ohne Credits:** Zwei Haltungen derselben Figur übereinanderlegen
und an jedem dritten Beat überblenden, dazu ein ruhiges Schweben per CSS-Keyframes und einen
kurzen Nick-Impuls bei jedem neu erscheinenden Element. Das wirkt deutlich lebendiger als
eine starre Figur und bleibt exakt im Zeichenstil der Vorlage. `prefers-reduced-motion`
respektieren.

## Phase 6b — Erklär-Animationen als Video (HyperFrames) — nur wenn wirklich Video gebraucht wird

Konzepte, Listen, Modelle, Regeln, Prozesse: als HTML/CSS/GSAP-Komposition bauen und zu MP4
rendern — gestochen scharfer Text in JEDER Sprache (kann Seedance nicht), beat-genau zur Stimme.

- Pro Szene ein Ordner mit `index.html` nach dem HyperFrames-Kontrakt (`/hyperframes-core`):
  Root mit `data-composition-id/-width/-height/-duration` (**1920×1080**, damit die Animationen
  zu den 1080p-Seedance-Clips passen; Dauer = VO_fast + 1 s), mindestens ein `class="clip"`,
  EIN pausiertes GSAP-Timeline auf `window.__timelines["<id>"]`.
- **Design = gewähltes Preset/design.md:** Hintergrund- und Akzentfarben des Presets,
  Guide-Figur als CSS-Element in jeder Szene → Stil-Klammer. Tokens und Größen aus dem
  Preset, Schriftgrößen gegenüber einem 720p-Layout um Faktor 1,5 skalieren.
- **Beats aus den Segment-Timestamps** der beschleunigten Voiceover (`vo.json`): Wenn die
  Stimme Punkt 3 nennt, erscheint GENAU DANN Punkt 3. Elemente per `tl.to/from` an die
  Segment-Startzeiten setzen.
- Stolperfallen (erspart Lint-Runden):
  - Initialzustände mit `gsap.set(...)` VOR der Timeline, nie `tl.set(..., 0)`
  - kein `repeat: -1` (endliche Wiederholungen), keine Uhr, kein Random
  - Titel einzeilig halten (`white-space: nowrap`) — Umbrüche kollidieren mit Inhalten
  - Elemente nicht überlappen lassen — `hyperframes check` prüft Layout + WCAG-Kontrast
- Loop, immer über den Wrapper (er wählt die Node-22-Laufzeit, ohne die Shell umzustellen —
  ein blankes `npx hyperframes` läuft sonst in die System-Node und bricht ab):
  ```sh
  bash scripts/hyperframes.sh lint     # → fixen
  bash scripts/hyperframes.sh check    # Layout + WCAG-Kontrast
  bash scripts/hyperframes.sh render --quality draft
  #   Frames extrahieren und ansehen!
  bash scripts/hyperframes.sh render --quality high --output final.mp4
  ```
- Ergebnis wiegt ~4–8 MB pro 40-s-Szene in 1080p und kostet keine Credits.
- `hyperframes.sh doctor` prüft die Umgebung. Drei Posten meldet es als fehlend, die dieser
  Ablauf **nicht braucht** — nicht nachinstallieren: `whisper-cpp` (wir transkribieren mit
  dem whisper-CLI bzw. über `WHISPER_REMOTE_CMD`), `TTS (Kokoro)` und `BGM (MusicGen)`
  (Stimmen kommen von ElevenLabs über Higgsfield, Musik ist nicht vorgesehen).

## Phase 6c — Eigene Figuren des Nutzers verwenden

Bringt der Nutzer eigene Zeichnungen/Figuren mit, sind die fast immer besser als alles
Generierte — sie sind die Marke. Ablauf, am 31.07.2026 an gescannten Karikaturen erprobt:

1. **Zuschneiden** auf die Figur, Sprechblasen und Fremdtext aus der Vorlage ausschließen.
2. **Hochskalieren** mit `bytedance_image_upscale --resolution 2k` (~2 Credits). Aus 295×392
   wurden 2160×2899 ohne sichtbaren Qualitätsverlust; Strichführung und Buntstift-Textur
   bleiben erhalten. ⚠ Text im Bild wird dabei „rekonstruiert" und dabei verfälscht — solche
   Stellen wegschneiden.
3. **Freistellen** mit `image_background_remover` (1 Credit). Er schneidet die Figur sauber
   aus, behält aber Möbel und Bodenflächen als Teil der Szene.
4. **Reste entfernen:** auf Halbfigur zuschneiden und die unteren 10–20 % weich auslaufen
   lassen (Alpha-Rampe). Sieht besser aus als eine harte Kante. **Keine Randflutung über
   Farbähnlichkeit** — helle Flächen im Inneren sind oft mit dem Rand verbunden, die Figur
   wird zerfressen.
5. **Auf Anzeigegröße bringen** (max. doppelte Darstellungsbreite). Ein 1340-px-PNG für eine
   150-px-Anzeige treibt die Dateigröße ohne jeden Nutzen nach oben.

**Nicht** ins Videomodell geben: Ein handgezeichneter Stil wird dort neu interpretiert und
driftet zwischen Shots. Bei ~30 s Szene wären das zudem rund 300 Credits pro Level.

## Phase 7 — Bilder (GPT Image 2) für die interaktiven Screens

```sh
higgsfield generate create gpt_image_2 --prompt "<Stil-Block + Motiv>" \
  --aspect_ratio "16:9" --resolution 1k --quality high --wait
```
Bilder machen die Quiz-Screens lebendig — gleiche Bildwelt wie die Videos:
- Startscreen-Hero (das Referenzbild wiederverwenden — kostenlos)
- eine Illustration PRO Entscheidungsszenario
- Vergleichs-Panels für Gegenüberstellungen
- Header-Bild für Suchspiele, Abschlussbild für den Zusammenfassungs-Screen
- Immer: Stil-Block der Videos + „no readable text, no faces" — bei GPT Image 2 besonders
  wichtig, sonst landen (oft falschsprachige) Beschriftungen im Bild
- `quality: "high"` für Hero- und Szenario-Bilder, `"medium"` reicht für Deko im Hintergrund
- Komprimieren: `ffmpeg -i in.png -vf "scale=1024:-2" -q:v 4 out.jpg` → ~80 KB/Bild

## Phase 8 — Muxing (ffmpeg)

- Animationen (exakt VO+1 s lang): Video kopieren, Audio padden:
  `-filter_complex "[1:a]apad[a]" -map 0:v -map "[a]" -t <videodauer> -c:v copy -c:a aac -b:a 96k -ac 1 -movflags +faststart`
- Film-Sequenzen: concat → trim auf VO+1 s → `-c:v libx264 -crf 27 -pix_fmt yuv420p`
- **Größe managen:** Die 1080p-Master bleiben als Archiv erhalten (wiederverwendbar für
  Social, LMS, Präsentationen). Für das Einbetten in die HTML-Datei gilt: Der Player zeigt
  die Videos ~800–900 px breit — wird die Gesamtdatei größer als ~50 MB, die Embed-Kopien mit
  `-vf "scale=1280:-2"` herunterskalieren. Sichtbar ist kein Unterschied, die Datei halbiert sich.
- Ziel: ≤ 5 MB pro eingebettetem Clip, Gesamtdatei ≤ 50 MB.

## Phase 9 — Die HTML-Lerneinheit (eine Datei, Vanilla JS)

Template mit Platzhaltern (`{{VIDEO_V0}}`, `{{IMG_SZ1}}` …) bauen, am Ende per Python-Skript
alle Medien als Base64-Data-URIs einsetzen. Architektur:
- SPA mit Screens (`.screen.active`), **Header mit Logo + Wortmarke** links (beides aus
  design.md; ohne design.md nur ein neutraler Texttitel), Level-Badges und XP rechts,
  Fortschrittsbalken in der Akzentfarbe
- Farben, Größen und die Stil-Klammer nach dem gewählten Preset (`reference/styles/`) bzw.
  der design.md — keine eigenen Farben erfinden, keine Verläufe, keine Deko-Emojis
- Video-Screen wiederverwendbar (ein `<video>`-Element, src wird gewechselt; „Weiter"-Button
  pulsiert nach `ended`; Hinweis „Ton an!" in der Zielsprache). Entfällt beim Preset
  `kostenlos` — dort ersetzt der Schritt-Mechanismus (siehe „Medienloser Zweig") Video-
  und Audio-Screens.
- XP-Ökonomie: richtige Antwort volle Punkte, zweiter Versuch halbe, Level-Abschluss +25
- Level-Sperre: Interaktion muss abgeschlossen sein, Videos sind überspringbar
- Namenseingabe optional (nur zur Personalisierung des Feedbacks), nicht erzwingen
- Quiz-Feedback **nie allein über Farbe**: `✓`/`✕` plus Feedbacktext, richtig in der
  Akzentfarbe, falsch in `--wrong`
- Abschluss-Check: Fragen UND Antwortreihenfolge shuffeln, Auswertung mit Themen-Hinweisen
  zu falschen Antworten, Wiederholung möglich
- Zusammenfassungs-Screen: alle Merksätze aus dem Curriculum, XP-Stand, **Footer mit
  Oberlinie in Akzentfarbe und Footer-Zeile aus der design.md** (ohne design.md: neutral,
  kein Branding), Print-CSS fürs Merkblatt
- localStorage: Fortschritt speichern, „Fortsetzen"-Button, Reset-Funktion
- `lang`-Attribut auf die Zielsprache setzen
- ⚠ In JS-Strings typografische Anführungszeichen der Zielsprache verwenden (deutsch „…“,
  englisch “…”) — gerade `"` zerbrechen die Strings

### Typografie und Layout (gilt für alle Presets)

- Font **Inter**, in CSS als `"Inter Variable", "Inter", system-ui, Arial, sans-serif`
  ansprechen — unter dem Namen `Inter` allein landet fontconfig auf DejaVu Sans.
- Bildschirmgrößen (px): Screen-Titel 40 · Level-Titel 30 · Merksatz 24 · Fließtext 18 ·
  Quiz-Optionen 18 · Unterzeilen 15 · Chips 14.
- HyperFrames-Szenen laufen in 1920 × 1080 — dort alle Größen mit Faktor 1,5 gegenüber
  einem 720p-Layout ansetzen (Titel ~60 px, Fließtext ~30 px).
- Die Akzentfarbe ist Akzent, nie Flächenfarbe — Ausnahmen: der aktive Button und der
  Fortschrittsbalken. `--wrong` nur für falsche Antworten, nie für Deko.
- Das Basis-Theme liegt in `assets/lerneinheit-theme.css` (Tokens des Presets `cinematic`);
  bei anderem Preset/design.md nur die Tokens im `:root` austauschen und danach den
  Kontrast nachrechnen.

#### Diagramme und Grafiken: nichts absolut positionieren

Eigene Schaubilder (Venn, Zeitstrahl, Pyramide, Kreislauf) **nie** aus absolut
positionierten Kästen bauen. Das sieht bei genau einer Fensterbreite richtig aus und
verrutscht bei jeder anderen — Kreise driften auseinander, Beschriftungen legen sich
übereinander, und niemand merkt es, weil der Browser-Test nur eine Breite prüft.

- **Fließendes Layout:** Flexbox oder Grid, Überlappungen über negative `margin`,
  nicht über `position: absolute` + `left: %`. Prozentuale Positionen und feste
  Pixelgrößen niemals mischen — genau daraus entsteht das Verrutschen.
- **Oder Inline-SVG** mit `viewBox` und `width: 100%`: skaliert von selbst mit,
  Beschriftungen bleiben, wo sie hingehören. Für alles Geometrische die bessere Wahl.
- **Kein Text über Text.** Ein zentrales Label („gilt für alle") gehört unter oder
  neben die Formen, nicht als Overlay darüber — sonst verdeckt es sie.
- **Bei drei Breiten gegenprüfen** (Phase 10): 390 px, 800 px und 1400 px. An allen
  dreien muss jede Beschriftung vollständig lesbar sein und darf nichts überdecken.
  Ein `@media`-Zweig für Handys reicht nicht — die Desktop-Breiten sind der häufigere
  Fehlerfall.

## Phase 10 — Browser-Test (Pflicht, vollständig)

Lokal serven (`python3 -m http.server`), dann komplett durchklicken:
1. Alle Videos dekodieren (Probe-Element je VIDEOS-Key, Dauer prüfen) + Bilder eingebettet
2. Jede Interaktion inkl. FEHLER-Pfaden (falsche Antworten, Timer ablaufen lassen)
3. Abschluss-Check absichtlich schlecht abschließen → Auswertung und Retry prüfen
4. Neu laden → „Fortsetzen" funktioniert; Konsole: null Fehler
5. Beim Preset `kostenlos` zusätzlich: Schritt-Steuerung vollständig durchklicken
   (vor/zurück, Pfeiltasten/Enter, Schrittzähler) und prüfen, dass beim Verlassen
   einer Szene alle Elemente sichtbar werden
6. **Layout bei 390 px, 800 px und 1400 px prüfen** — die Seite darf nie horizontal
   scrollen, und in eigenen Schaubildern darf sich nichts überlappen. Schnelltest je
   Breite in der Konsole:
   ```js
   [...document.querySelectorAll('body *')].filter(e => {
     const r = e.getBoundingClientRect();
     return r.width && r.right > innerWidth + 1;
   }).map(e => e.className)          // muss [] sein
   ```
7. Kontrast der tatsächlich gesetzten Farben nachrechnen:
   `python3 scripts/kontrast.py "<akzent>" "<panel>"` (mit den Werten des Presets bzw.
   der design.md aufrufen — Akzent auf Hintergrund muss ≥ 4,5:1 liegen)
8. Dateigröße prüfen; Server stoppen, Datei ausliefern

## Phase 11 — Benennen und ausliefern

```
Schulung_<Thema>_<YYYY-MM-DD>.html
```
Mit design.md optional `<Wortmarke>_Schulung_<Thema>_<YYYY-MM-DD>.html`.

Die fertige Datei bleibt **im Projektordner** und wird von dort ausgeliefert (Download,
Mail, beliebiger Filesharing-Dienst). Wer einen zentralen Ablageort nutzt (z. B. einen
eigenen Cloud-Speicher per `rclone`), kann das als optionalen, selbst konfigurierten
Schritt anhängen — der Skill setzt kein bestimmtes Remote voraus. Die 1080p-Master und
`curriculum.md` gehören mit ins Projektarchiv.

---

## Kosten-Richtwerte (Higgsfield-Credits)

| Posten | Credits |
|---|---|
| **Seedance-Video 1080p** | **9 Credits pro Sekunde** (5 s = 45, 10 s = 90, 15 s = 135) |
| Bild (gpt_image_2, 1k) | ~4 bei `high`, ~2 bei `medium` |
| Referenzbild (2 Kandidaten) | ~8 |
| Voiceover pro Szene | ~0,4 |
| HyperFrames-Renders | 0 (lokal) |
| Transkription (lokales whisper) | 0 (eigene Hardware) |

Alle Werte am 31.07.2026 mit `higgsfield generate cost` nachgemessen, nicht geschätzt. Vor
jeder Produktion trotzdem neu abfragen — Preise können sich ändern.

**Beispielrechnung:** Kompakt-Lektion (4 Level, 1 Story-Video à 10 s, 3 Animationen, 3 Bilder)
≈ 110 Credits · Volle Schulung (8 Level, 3 Story-Sequenzen mit zusammen ~105 s Filmmaterial,
5 Animationen, 7 Bilder) ≈ 980 Credits · Preset `statisch` (0 Filme, nur HTML-Szenen +
2–3 Bilder) ≈ 10–40 Credits · Preset `kostenlos` (0 Filme, 0 Bilder, 0 Voiceover —
nur schrittgesteuerte HTML-Szenen) = **0 Credits**.

Die Videosekunden dominieren die Kosten zu über 95 % — Bilder, Stimmen und die
HyperFrames-Animationen fallen kaum ins Gewicht. Zwei Hebel: Konzepte konsequent als
(kostenlose) HyperFrames-Animation lösen statt als Film, und Shot-Längen exakt auf die
Voiceover zuschneiden. Die Schätzung gehört ins Curriculum, `higgsfield account status` vor der
Produktion prüfen.

## Einrichtung je Maschine

| Baustein | Nötig für | Einrichten |
|---|---|---|
| Higgsfield-CLI | Video, Bild, Voiceover | `npm i -g @higgsfield/cli` (Aliase `hf`, `higgs`), dann `higgsfield auth login` und **`higgsfield workspace set <id>`** — ohne gesetzten Workspace antwortet jeder Aufruf mit „No workspace selected" |
| Node 22+ | HyperFrames | `nvm install 22` (parallel zu vorhandenen Versionen). **Nicht** `nvm use` — der Wrapper `scripts/hyperframes.sh` wählt die Laufzeit selbst |
| HyperFrames-Skills | HyperFrames | **nicht** alle 31 installieren — das Repo hat auch Captions-, Talking-Head- und Figma-Workflows, die hier nur die Skill-Liste aufblähen. Nötig sind fünf, und `-s` nimmt nur **einen** Namen je Aufruf: `for s in hyperframes hyperframes-core hyperframes-cli hyperframes-animation hyperframes-keyframes; do npx -y skills add heygen-com/hyperframes -g -y -s "$s" -a claude-code; done` |
| ffmpeg | alles ab Phase 4 | Distributionspaket |
| whisper (lokal) | Transkription (Default) | `pip install openai-whisper` — läuft auf CPU, mit GPU deutlich schneller; Modell per `WHISPER_MODEL` wählbar |
| Remote-Transkription (optional) | schnellere Transkription | Umgebungsvariable `WHISPER_REMOTE_CMD` auf ein Kommando setzen, das Audio per stdin nimmt und `verbose_json` mit Wort-Zeitstempeln auf stdout liefert (z. B. ein ssh-Aufruf auf einen eigenen GPU-Server) |

`scripts/preflight.sh` prüft all das und sagt, was fehlt.

## Beispiel-Prompt (das gibt der User dir)

> /schulung — Erstelle eine interaktive Lerneinheit zum Thema **[THEMA]** als eine einzige
> offline lauffähige HTML-Datei. Zielgruppe: **[z. B. neue Mitarbeitende / meine
> Coaching-Klienten / das Team von Kunde X]**, Sprache: **[z. B. Deutsch]**,
> Dauer: **[z. B. ~20 Min]**, Stil: **[Preset cinematic / comic / corporate / statisch
> / kostenlos oder eigene design.md]**.
> Inhalte sollen abdecken: **[Stichpunkte oder vorhandenes Material]**.
> Erstelle zuerst das Curriculum als Dokument — erst nach meiner Freigabe produzieren.

Fehlt eine der fünf Kernangaben (Thema, Zielgruppe, Sprache, Dauer, Stil) — nachfragen,
nicht raten.

---

## Aufruf durch die App

Die aufrufende Anwendung besitzt die State-Machine und ruft diesen Skill phasenweise auf.
Pro Aufruf bekommt der Skill die Eingabe der Phase und liefert das Artefakt zurück —
Prompt-Templates können gegen diese Tabelle gebaut werden:

| Phase | Erwartete Eingabe | Erwartetes Artefakt |
|---|---|---|
| 0 Briefing | Thema, Lernziele, Zielgruppe, Sprache, Dauer, Stil (Preset oder design.md) | strukturierter Steckbrief (Markdown) |
| 1 Recherche | Steckbrief, vorhandenes Material | Quellenliste mit Stand-Datum |
| 2 Curriculum | Steckbrief, Quellen, gewähltes Preset/design.md | `curriculum.md` im Projektordner |
| Gate | `curriculum.md`, Review-Kommentare, ggf. Medium-Override je Level | aktualisiertes `curriculum.md` + explizites „Go" |
| 2.5 Preflight | „Go" | Preflight-Protokoll; Kostensumme vs. Guthaben |
| 3 Referenzbild | Preset/design.md (Guide-Figur) | `referenzbild.png` im Projektordner |
| 4 Voiceover | Voiceover-Skripte aus dem Curriculum | `vo_level<N>_fast.mp3` + `vo_level<N>.json` (Wort-Zeiten + Beats) |
| 5 Videos | FILM-Level des Medienplans, Referenzbild | `film_level<N>_shot<K>.mp4` |
| 6 HTML-Szenen | ANIMATION-Level, `vo.json` | Szenen-Markup mit verdrahteten Beats |
| 6b HyperFrames | nur falls Video nötig: Szenen-HTML | `anim_level<N>.mp4` |
| 6c Eigene Figuren | hochgeladene Vorlagen des Nutzers | freigestellte, skalierte PNGs |
| 7 Bilder | BILD-Level des Medienplans | komprimierte JPGs (~80 KB) |
| 8 Muxing | alle Medien + `vo.json` | finale Clips ≤ 5 MB, VO+1 s |
| 9 HTML | Template, Theme, alle Medien | Arbeitsstand `lerneinheit.html` |
| 10 Browser-Test | fertige HTML-Datei | Testprotokoll inkl. Kontrast-Nachweis |
| 11 Auslieferung | getestete HTML-Datei | `Schulung_<Thema>_<YYYY-MM-DD>.html` im Projektordner |

Jede Phase ist einzeln wiederholbar; produktionsrelevante Wiederholungen (ab Phase 3)
kosten Credits — vorher die Kosten erneut schätzen.

**Variante `kostenlos`:** Die Phasen 3, 4, 5, 7 und 8 entfallen komplett (keine Artefakte,
keine Credits). Phase 2.5 läuft mit `SCHULUNG_KOSTENLOS=1`, Phase 6 liefert schrittgesteuerte
HTML-Szenen ohne Tonspur; Phase 9 baut die Datei ohne `<video>`/`<audio>` direkt aus dem
Curriculum. Der Ablauf ist: 2.5 → 6 → 9 → 10 → 11.
