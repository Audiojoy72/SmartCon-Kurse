# Tech Stack — SmartCon-Schulungen

Stand 2026-08-01. Verbindliches Pflichtenheft: [SPEC.md](SPEC.md).

## Sprachen & Runtimes

| Technologie | Version | Zweck |
|---|---|---|
| Python | 3.11 (Container: 3.11.15) | gesamtes Backend |
| Vanilla JS / HTML / CSS | — | gesamtes Frontend, kein Build-Schritt, kein Framework |
| Bash | 5.x | Skill-Skripte (Preflight, Transkription, HyperFrames) |
| Markdown + YAML-Frontmatter | — | Skill-Definition, Presets, design.md, Curriculum |

## Backend (Python, `app/`)

| Modul | Aufgabe |
|---|---|
| `main.py` | FastAPI-App, alle HTTP-Endpunkte, statisches Frontend |
| `runner.py` | AgentRunner: startet `claude`/`kimi` headless als Subprozess, parst stream-json (NDJSON), Session-Resume mit cwd-Prüfung, Event-Queues für SSE, `events.jsonl` pro Projekt |
| `projekte.py` | Projektverwaltung: Slugs, `brief.json`, `status.json`, Phasen-Modell |
| `prompts.py` | Prompt-Templates je Phase (Curriculum, Kommentar, Kostenplan, Freigabe, Produktion), baut `WHISPER_REMOTE_CMD` aus der Config |
| `preflight.py` | System-Check: alle Abhängigkeiten mit Status + Installationsanleitung |
| `curriculum.py` | Level-Parser für das Freigabe-Gate (Markdown-Tabelle → Medium-Dropdowns) |
| `higgsfield.py` | Guthaben-Abfrage mit 60-s-Cache |
| `config.py` | `config.json` laden/speichern (gitignored, enthält Zugangsdaten) |

**Dependencies** (`requirements.txt`): `fastapi`, `uvicorn[standard]`,
`python-multipart` (Uploads). Keine Datenbank — alles liegt als Dateien im
Dateisystem (`config.json`, `projects/<slug>/`).

## Frontend (`static/`)

`index.html` + `app.js` + `style.css`, keine Frameworks. Fortschritt über
Server-Sent Events (`GET /api/projekte/{slug}/events`, spielt `events.jsonl`
beim Reconnect nach). Verbrauchs-Zähler per 30-s-Polling.

Die Projektliste pollt sich alle 15 s selbst nach, solange irgendein Projekt in
einer `*_laeuft`-Phase steht, und hört von allein wieder auf — ohne das bliebe
„Produktion läuft …" bis zum manuellen Reload stehen (SSE hängt nur an der
Detailansicht).

Bedienbar auch vom Handy: geprüft bei 390 px und 320 px, kein horizontaler
Überlauf. Breite Tabellen (Level, Kostenplan) scrollen in einem eigenen Kasten
`.tabelle-scroll`, statt die Seite auseinanderzuziehen.

## API-Überblick

| Endpunkt | Zweck |
|---|---|
| `GET /api/preflight` · `GET/POST /api/config` | System-Check, Einstellungen |
| `GET /api/projekte` · `POST /api/projekte` · `GET /api/projekte/{slug}` | Projektliste, Anlage (multipart), Detail |
| `DELETE /api/projekte/{slug}` | Schulung samt Ordner entfernen (409, solange ein Agent läuft) |
| `GET /api/presets` | Stil-Presets aus `skill/schulung/reference/styles/` |
| `POST …/curriculum/starten` · `GET/PUT …/curriculum` · `POST …/curriculum/kommentar` | Curriculum-Phase inkl. Editor + Agenten-Kommentar |
| `GET …/gate` · `POST …/gate/kostenplan` · `POST …/go` | Freigabe-Gate: Level, Kosten, Guthaben, Go mit Medium-Overrides |
| `POST …/produktion/starten` · `GET …/produktion/status` | Produktion + Verbrauchs-Zähler |
| `GET …/ergebnis` · `GET …/ergebnis/{datei}` · `GET …/vorschau/{datei}` | History: Download + Vorschau |
| `GET …/events` | SSE-Fortschritt (mit Replay) |

## Infrastruktur & Deployment

| Komponente | Details |
|---|---|
| Container | `Dockerfile` (python:3.11-slim + ffmpeg + Node 22 + `@higgsfield/cli` + cloudflared + openssh + claude-/kimi-CLI), `docker-compose.yml` mit Auth-Mounts (`~/.claude`, `~/.kimi-code`, `~/.config/higgsfield` rw; `~/.ssh`, `~/.cloudflare` ro), `restart: unless-stopped`, `host.docker.internal:host-gateway` |
| Betrieb ohne Docker | `python3 -m venv .venv && .venv/bin/python -m app.main` |
| Netz | Port 8710; `lan_erreichbar` in `config.json` → Bind `0.0.0.0` oder `127.0.0.1`. Kein Login — LAN-Freigabe ist Vertrauenssache |
| Whisper-Tunnel (Referenz-Setup) | systemd-User-Unit `whisper-tunnel.service` (`ssh -N -L 0.0.0.0:18710:localhost:8000 dsski`), `Restart=always`, Linger |
| Repo | `github.com/Audiojoy72/SmartCon-Schulungen` (public, Branch `master`), Lizenz AGPL-3.0 |

## Der Skill (`skill/schulung/`)

Neutrale, eigenständige Version des Schulungs-Skills — die App orchestriert ihn,
er funktioniert aber auch ohne App in jeder Agenten-Session.

| Artefakt | Zweck |
|---|---|
| `SKILL.md` | 11-Phasen-Workflow (Teil 1 Curriculum / Freigabe-Gate / Teil 2 Produktion) + medienloser Zweig + Tabelle „Aufruf durch die App" |
| `reference/styles/*.md` | Presets `cinematic` (Default), `comic`, `corporate`, `statisch`, `kostenlos` — je Stil-Block, Guide-Figur, Palette, Medien-Defaults, Kostenrahmen |
| `reference/design-vorlage.md` | Vorlage für eigene CI (`design.md` schlägt Preset schlägt Default) |
| `scripts/preflight.sh` | Umgebungsprüfung; `SCHULUNG_KOSTENLOS=1` überspringt Higgsfield/ffmpeg/Whisper |
| `scripts/transkribieren.sh` | Whisper → Wort-Beats; lokal (Default) oder `WHISPER_REMOTE_CMD` (OpenAI-kompatibel) |
| `scripts/hyperframes.sh` | Node-22-Wrapper für HyperFrames-Renders (optional) |
| `scripts/kontrast.py` | WCAG-Kontrastrechner für den Browser-Test |

## Externe Werkzeuge & Dienste

| Werkzeug | Zweck | Pflicht? |
|---|---|---|
| `claude` (Claude Code) | primärer Agent, headless `claude -p --output-format stream-json --verbose`, Resume via `--resume <session_id>` | eines von beiden |
| `kimi` | Fallback-Agent (`kimi -p`) | eines von beiden |
| `@higgsfield/cli` | Bilder (`gpt_image_2`), Videos (`seedance_2_0`), Voiceover (`text2speech_v2`/ElevenLabs), Upscale, Freisteller; Kostenmessung `generate cost` | nur KI-Medien = Ja |
| `ffmpeg` | Tempoanpassung (atempo), Muxing, Kompression | nur KI-Medien = Ja |
| Whisper lokal oder OpenAI-kompatible API (`/v1/audio/transcriptions`, verbose_json + Wort-Zeitstempel; optional Cloudflare-Access-Header) | Transkription → Beat-Choreografie | nur mit Voiceover |
| Node 22 + HyperFrames | gerenderte Erklär-Videos (optional; HTML-Szenen sind Standard) | optional |

**Kostenrelevant (Higgsfield-Credits, Stand 2026-08-01):** 9/s Video (1080p) ·
~4/~2 pro Bild · ~1,5 pro Voiceover · 2 Upscale · 1 Freisteller · HyperFrames,
HTML-Szenen, Transkription und Curriculum: 0. KI-Medien = Nein: **0 Credits
gesamt.**

## Sicherheit & Datenschutz

- `config.json`, `projects/`, `.venv/` sind gitignored — Zugangsdaten (API-Keys,
  Cloudflare-Tokens, Higgsfield-Auth) verlassen die Maschine nicht über das Repo
- Agenten-Sessions sind ans Arbeitsverzeichnis gebunden; der Runner prüft vor
  jedem Resume, ob die Session-Datei existiert (Host- ≠ Container-Pfade)
- Die App hat kein Login — LAN-Freigabe nur in vertrauten Netzen

## Bekannte Fallen (harte Lernerfahrungen)

1. **npm-Paketname:** `npm i -g higgsfield` schlägt fehl (404) — das Paket heißt
   `@higgsfield/cli`.
2. **Session-Resume:** `claude --resume <id>` kennt die Session nur unter dem
   cwd, in dem sie entstanden ist → Runner-Funktion `session_verfuegbar()`.
3. **Host-Localhost ≠ Container-Localhost:** Dienste auf dem Host im Container
   über `host.docker.internal` ansprechen; ein SSH-Tunnel auf `127.0.0.1` ist
   vom Container aus unsichtbar (Tunnel auf `0.0.0.0` binden).
4. **pkill -f:** Suchstrings, die im eigenen Kommando vorkommen, killen die
   eigene Shell — Zeichenklassen verwenden (`app[.]main`).
5. **Guthaben-Parsing:** „1082.5 credits" — Nachkommastellen nicht abschneiden.
6. **Frontend-Cache:** Ohne `Cache-Control: no-cache` auf der Index-Route hält
   ein Handy-Browser die alte `index.html` samt der darin stehenden
   `?v=`-Verweise fest — Änderungen an CSS/JS bleiben dann unsichtbar, egal wie
   oft man neu lädt. Bei jeder Frontend-Änderung das `?v=` in `index.html`
   hochzählen.
7. **`static/` liegt im Image**, nicht als Volume. Ein Frontend-Fix wird also
   erst durch `docker compose build` dauerhaft. Läuft gerade eine Produktion,
   ist Bauen tabu — dann `docker cp <datei> smartcon-schulungen:/app/…` in den
   laufenden Container kopieren (wirkt sofort, überlebt aber kein Recreate).
8. **Dateinamen aus dem Browser:** Beim Drag & Drop aus einem Browser-Tab
   liefert der Browser den URL-kodierten Namen (`T%C3%9CV%20Vortrag.pptx`).
   `projekte._dateiname()` dreht das zurück — und macht danach **erneut**
   `Path(...).name`, weil `unquote` aus `%2F` ein `/` macht und der Upload
   sonst aus dem Projektordner herausschreiben könnte.
