# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

SmartCon-Schulungen ist eine lokale Formular-App, die interaktive Schulungen als
eine einzige offline lauffähige HTML-Datei erzeugt. Die App besitzt die
State-Machine (Briefing → Curriculum → Freigabe-Gate → Produktion → fertig) und
schickt pro Phase einen KI-Agenten (Claude Code headless, Kimi als Fallback) mit
einem klaren Arbeitsauftrag los. Der Agent folgt dem Skill `skill/schulung/`.
Mit dem Schalter „KI-Medien = Nein" läuft alles ohne Higgsfield (0 Credits).
Öffentliches Repo (AGPL-3.0): github.com/Audiojoy72/SmartCon-Schulungen.
Pflichtenheft mit allen 14 Grundsatz-Entscheidungen: `SPEC.md`.

## Tech Stack

Details in `TECH_STACK.md`. Kern: Python 3.11 + FastAPI + uvicorn, Frontend
Vanilla JS ohne Build, kein DB (Dateisystem), Docker als empfohlener Betrieb.

## Commands

```sh
# Betrieb (empfohlen)
docker compose build && docker compose up -d     # App auf Port 8710

# Entwicklung ohne Docker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main

# Checks
.venv/bin/python -m py_compile app/*.py
node --check static/app.js
bash -n skill/schulung/scripts/*.sh
```

Kein Test-Framework — Verifikation läuft über den System-Check der App
(`GET /api/preflight`) und End-to-End-Testprojekte (Preset `kostenlos` kostet
nichts).

## Project Structure

```
app/            FastAPI-Backend (main, runner, projekte, prompts, preflight,
                curriculum, higgsfield, config)
static/         Frontend (index.html, app.js, style.css)
skill/schulung/ der neutrale Schulungs-Skill (SKILL.md, reference/styles/,
                reference/design-vorlage.md, scripts/, assets/)
projects/       Projektordner je Schulung (gitignored, Nutzdaten)
config.json     Einstellungen + Zugangsdaten (gitignored)
docs/           Screenshots für die README
SPEC.md         Pflichtenheft (14 Entscheidungen)
TECH_STACK.md   Technik-Überblick inkl. „Bekannte Fallen"
Dockerfile, docker-compose.yml
```

## Architecture

```
Browser (Vanilla JS) ──HTTP+SSE──> FastAPI ──Subprozess──> claude -p / kimi -p
                                        │                     │
                                   projects/<slug>/      higgsfield, ffmpeg,
                                   (status.json,           Whisper-API
                                    curriculum.md, …)
```

- **Die App führt, der Agent arbeitet zu.** Jede Phase bekommt ein
  Prompt-Template aus `app/prompts.py`; Ergebnisse landen als Dateien im
  Projektordner.
- **Fortschritt:** Runner parst claude stream-json (NDJSON) → Queue → SSE;
  `events.jsonl` pro Projekt erlaubt Replay nach Reconnect.
- **Resume:** Agenten-Session-IDs je Phase in `status.json`; vor jedem Resume
  `runner.session_verfuegbar()` (Sessions sind cwd-gebunden!).
- **Preset vs. design.md:** zwei unabhängige Achsen. Das Preset
  (`skill/schulung/reference/styles/`, Default `cinematic`) bestimmt Machart,
  Medienplan und Higgsfield-Einsatz; `kostenlos` erzwingt `ki_medien=false`.
  Eine optionale `design.md` im Projektordner liefert nur die Optik (Farben,
  Schriften, Tonalität) und hat dort Vorrang — sie ersetzt das Preset nicht.
- **Kosten-Disziplin:** Curriculum ist immer gratis; vor der Produktion
  Kostenplan (`kosten.json`) + Guthaben-Abgleich; Preflight vor jeder
  kostenpflichtigen Aktion.

## Code Patterns

- UI-Texte, Doku und Kommentare auf Deutsch; Code-Identifier englisch.
- Kein Framework im Frontend; keine neuen Python-Dependencies ohne Not.
- Fehlerfälle: 404 Projekt unbekannt, 409 Agenten-Lauf aktiv, 400 Validierung.
- Pro Projekt nur ein Agenten-Lauf gleichzeitig (`runner.laeuft`).
- Dateipfade aus Nutzereingaben immer sanitizen (siehe Ergebnis-Endpunkte,
  `projekte.loeschen()` und `projekte._dateiname()`).
- Frontend muss auf dem Handy funktionieren: nach jeder UI-Änderung bei 390 px
  und 320 px gegen horizontalen Überlauf prüfen. Flex-Zeilen brauchen
  `flex-wrap`, breite Tabellen den Kasten `.tabelle-scroll`.
- `hidden` allein versteckt nichts: `form label { display: block }` in
  `style.css` schlägt das Attribut (Autor-Stylesheet gewinnt gegen das
  UA-Stylesheet). Dafür gibt es `form label[hidden] { display: none }` — bei
  neuen Regeln mit eigenem `display` immer eine `[hidden]`-Variante nachziehen.
  Sichtbarkeit im Test über `getComputedStyle(el).display` prüfen, nicht über
  `el.hidden` — sonst meldet der Test „versteckt", während das Feld dasteht.

## Key Files

| Datei | Zweck |
|---|---|
| `app/runner.py` | AgentRunner: Subprozess, stream-json, SSE, Resume |
| `app/prompts.py` | alle Arbeitsaufträge an den Agenten |
| `skill/schulung/SKILL.md` | der 11-Phasen-Workflow (Source of Truth fachlich) |
| `config.json` | Backend-Wahl, Whisper-API, Keys — niemals committen |
| `SPEC.md` | warum die App so ist, wie sie ist |

## Notes / Gotchas

- npm-Paket ist `@higgsfield/cli`, NICHT `higgsfield` (404 sonst).
- claude-Sessions überleben keinen cwd-Wechsel (Host ↔ Container) — Resume
  immer über `session_verfuegbar()` absichern.
- Container: Host-Dienste über `host.docker.internal`; Tunnels auf `0.0.0.0`
  binden, nicht `127.0.0.1`.
- `pkill -f` mit Strings, die im eigenen Kommando vorkommen, killt die eigene
  Shell — Zeichenklassen nutzen (`app[.]main`).
- Guthaben hat Nachkommastellen („1082.5 credits") — Float parsen.
- Container-Neustart killt laufende Produktionen — nie rebuilden, während ein
  Agent arbeitet. Muss trotzdem ein Frontend-Fix sofort raus: `docker cp
  static/app.js smartcon-schulungen:/app/static/app.js` wirkt ohne Neustart
  (`static/` liegt im Image, nicht als Volume), überlebt aber kein Recreate —
  nach der Produktion `docker compose build` nachziehen.
- Läuft ein Agent noch? `projects/*/status.json` zeigt die Phase, die letzte
  Zeile in `events.jsonl` den letzten Lebenszeichen-Zeitstempel.
- Frontend-Änderung: `?v=` in `index.html` hochzählen. Die Index-Route liefert
  `Cache-Control: no-cache`, sonst hält der Handy-Browser die alte Seite samt
  alter Asset-Verweise fest.
- `DELETE /api/projekte/{slug}` entfernt den ganzen Ordner — **kein Papierkorb, kein
  Export**. Damit ist auch das `curriculum.md` weg, und ohne das ist die Schulung nicht
  mehr nachbearbeitbar. Am 01.08.2026 genau so passiert; die fertige HTML ließ sich nur
  retten, weil noch ein Browser-Tab offen war (`fetch(url, {cache: 'force-cache'})`).
- `projects/` ist gitignored — fertige Schulungen liegen also **nirgendwo sonst**. Wer
  eine behalten will, sichert sie selbst weg (Nextcloud `AI-SmartCon/Schulungen/`).
- Whisper-Tunnel (Referenz-Setup): systemd-User-Unit `whisper-tunnel.service`.
