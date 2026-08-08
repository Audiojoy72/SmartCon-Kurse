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
Pflichtenheft mit allen 16 Grundsatz-Entscheidungen: `SPEC.md`.

## Tech Stack

Details in `TECH_STACK.md`. Kern: Python 3.11 + FastAPI + uvicorn, Frontend
Vanilla JS ohne Build, SQLite (`data/kurse.db`) für Kursverwaltung/Portal neben
dem Dateisystem (`config.json`, `projects/<slug>/`), Docker als empfohlener
Betrieb.

## Commands

```sh
# Betrieb (empfohlen)
touch config-logo.png                             # sonst legt Docker dort ein Verzeichnis an
mkdir -p data                                    # einmalig, vor dem ersten Start
docker compose build && docker compose up -d     # App auf Port 8710

# Entwicklung ohne Docker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main

# Checks
.venv/bin/pip install -r requirements-dev.txt   # einmalig
.venv/bin/python -m pytest                      # Testsuite
.venv/bin/python -m py_compile app/*.py
node --check static/app.js
bash -n skill/schulung/scripts/*.sh
```

pytest für die Logik (`tests/`), dazu der System-Check der App (`GET /api/preflight`)
und End-to-End-Testprojekte für alles, was einen echten Agentenlauf braucht.

## Project Structure

```
app/            FastAPI-Backend (main, runner, projekte, prompts, preflight,
                curriculum, higgsfield, config, praesentation, pruefung, folien,
                db, zugang, teilnehmer, versuche, portal, portal_routes,
                verwaltung)
static/         Frontend (index.html, app.js, style.css)
skill/schulung/ der neutrale Schulungs-Skill (SKILL.md, reference/styles/,
                reference/design-vorlage.md, scripts/, assets/)
tests/          pytest-Suite für app/ (kein Test-Framework fürs Frontend)
projects/       Projektordner je Schulung (gitignored, Nutzdaten)
data/           SQLite der Kursverwaltung (gitignored, Kundendaten)
config.json     Einstellungen + Zugangsdaten (gitignored)
docs/           Screenshots für die README
SPEC.md         Pflichtenheft (16 Entscheidungen)
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
- **Zwei Bereiche, zwei Schutzmechanismen.** Die Werkstatt (Projekte,
  Präsentationen, Einstellungen) liegt hinter dem vorgelagerten
  Zugriffsschutz. Das Portal unter `/portal` schützt sich selbst über
  scrypt-Passwörter und Sitzungscookies — Kunden haben dort keine Konten.
- **Die Prüfung im Portal wird serverseitig ausgewertet.** `versuche.auswerten()`
  liest die richtigen Antworten aus `projects/<slug>/pruefung.json`; sie gehen
  nie an den Browser. Die verschickbare Prüfungsseite aus
  `pruefung.als_html()` ist etwas anderes: Sie wertet im Browser aus und
  bringt ihre Lösungen mit — das ist für eine Datei zum Weitergeben richtig
  und für einen Nachweis untauglich. Die beiden nie verwechseln.

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
| `app/portal_routes.py` | alle `/portal`-Routen: Login, Sitzungscookie, Lernen, Prüfung, Zertifikat — der selbstgeschützte zweite Bereich |
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
- `config-logo.png` ist wie `config.json` per Bind-Mount eingebunden (Dateipfad,
  nicht Verzeichnis). Fehlt die Datei auf dem Host beim ersten `docker compose
  up`, legt Docker an der Stelle ein Verzeichnis an — danach schlägt jeder
  Logo-Upload fehl. Vor dem ersten Start: `touch config-logo.png`.
- `data/kurse.db` enthält Kundendaten und ist gitignored. Ein `rm -rf data/`
  löscht alle Teilnehmer, Zugänge und Prüfungsergebnisse — es gibt keinen
  Papierkorb. Sicherung im laufenden Betrieb:
  `sqlite3 data/kurse.db ".backup data/kurse-$(date +%F).db"`
- Der Ordner `data/` muss vor dem ersten `docker compose up` existieren
  (`mkdir -p data`), sonst legt Docker ihn als root an und die App kann nicht
  schreiben.
- `portal_secure_cookie` steht im Betrieb auf `true`. Für die Entwicklung über
  `http://localhost` muss es auf `false`, sonst schickt der Browser das
  Sitzungscookie nicht zurück und die Anmeldung wirkt, als hätte sie nicht
  gegriffen. **Vor dem Betrieb zurückstellen.**
- Ein Teilnehmer-Passwort ist nach der Anzeige nicht mehr abrufbar — gespeichert
  ist nur der scrypt-Hash. Verloren heißt: neu freischalten.
