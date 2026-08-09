# SmartCon-Kurse

Interaktive Schulungen per Formular-App erstellen: Eine lokale Web-Oberfläche führt
Schritt für Schritt vom Briefing über das Curriculum (mit Freigabe-Gate) bis zur
fertigen, offline lauffähigen HTML-Lerneinheit — mit KI-Videos, Erklär-Animationen,
Voiceover, Gamification und Quiz. Die Denkarbeit übernimmt ein KI-Agent im Hintergrund
(Claude Code oder Kimi, umschaltbar), die App steuert die Phasen.

Auf Wunsch komplett **kostenlos**: Der Schalter „KI-Medien" erzeugt dieselbe
interaktive Lerneinheit ohne Higgsfield — schrittgesteuerte HTML-Szenen statt
Beat-Choreografie, null Credits.

Gebaut von **AI-SmartCon – Matthias Geist**.
Danke an **Julian Ivanov** für den tollen Skill.

## Funktionsumfang

- **Projekt-Wizard**: Briefing-Formular (Thema, Lernziele, Zielgruppe, Sprache, Dauer),
  Stil-Presets als Karten, Upload eigener `design.md` (Kunden-CI) und Quellmaterial
- **Stil-System**: fünf Presets (`cinematic`, `comic`, `corporate`, `statisch`,
  `kostenlos`) bestimmen die Machart und damit den Higgsfield-Einsatz
- **Eigenes Design (optional)**: eine mitgegebene `design.md` setzt Farben,
  Schriften und Tonalität — kombinierbar mit jedem Preset. Eine `cinematic`-
  Schulung bleibt cinematic, nur eben in der CI des Kunden
- **KI-Medien-Schalter (Ja/Nein)**: mit oder ohne Higgsfield produzieren, frei
  kombinierbar mit jedem Preset. „Nein" = 0 Credits, keine Higgsfield-Abhängigkeit
- **Curriculum-Phase (kostenlos)**: Der Agent recherchiert und schreibt das komplette
  Curriculum (Lernziele, Lehrtexte, Voiceover-/Sprechertexte, Interaktionen,
  Kosten-Schätzung) als Markdown — im Browser editierbar, Änderungswünsche per
  Kommentar-Box direkt an den Agenten (Session-Resume)
- **Freigabe-Gate**: Medium je Level per Dropdown umschalten (FILM/ANIMATION/BILD),
  Kosten-Dashboard mit Posten, Summe und Guthaben-Abgleich — der Agent misst jede
  geplante Generierung vorab mit `higgsfield generate cost` nach
- **Produktion**: Live-Fortschritt (SSE), Verbrauchs-Zähler, Preflight vor jeder
  kostenpflichtigen Aktion, Abbruch statt „so weit es reicht"
- **History**: fertige Schulungen bleiben gelistet; Ergebnis im Browser ansehen oder
  herunterladen; Nachbearbeiten per Phasen-Rücksprung; Löschen mit Rückfrage
- **System-Check**: prüft alle Abhängigkeiten live — jede Kachel ist anklickbar und
  zeigt eine Schritt-für-Schritt-Installationsanleitung
- **Kurse, Termine und Anmeldung**: Kurse mit Preis, Plätzen und Terminserien
  pflegen; Interessenten melden sich selbst an und bekommen eine
  Bestätigungsmail; aus einer bezahlten Anmeldung wird per Klick ein Teilnehmer
  mit Portalzugang. Öffentlich sichtbar ist nie eine Platzzahl, nur „offen" oder
  „ausgebucht"
- **Teilnehmer-Portal mit Nachweis**: Lerneinheit, serverseitig ausgewertete
  Prüfung (drei Versuche) und ein druckbarer Nachweis — Zertifikat bei
  bestandener Prüfung, sonst Teilnahmebestätigung
- **Auch vom Handy bedienbar**: die Oberfläche ist auf schmale Displays ausgelegt,
  die Projektliste aktualisiert sich während eines Laufs von selbst — man kann die
  Seite verlassen und später wieder reinschauen, der Agent läuft im Server weiter

## So läuft eine Schulung durch

1. **Briefing** — Formular ausfüllen, Preset wählen, KI-Medien Ja/Nein
2. **Curriculum erzeugen** — der Agent schreibt `curriculum.md` (Minuten, 0 Credits)
3. **Prüfen** — Editor, Kommentar-Box, Medium-Dropdowns, Kosten-Dashboard
4. **Freigeben** — erst jetzt darf produziert werden
5. **Produktion** — Voiceover, Bilder, Videos, HTML-Bau, Browser-Test (~15–60 Min)
6. **Ergebnis** — eine einzige offline lauffähige HTML-Datei zum Ansehen/Teilen

## Status

Produktiv im Eigenbetrieb, privates Repo. Die Anmeldung ist seit dem
09.08.2026 öffentlich erreichbar unter
**https://kurse.smartcon-ai.de/anmeldung**. Das verbindliche Pflichtenheft
steht in [SPEC.md](SPEC.md), der Technik-Überblick in
[TECH_STACK.md](TECH_STACK.md).

## Screenshots

| Projekte & History | Projekt-Detail mit Curriculum |
|---|---|
| ![Projekte](docs/screenshots/projekte.png) | ![Projekt-Detail](docs/screenshots/projekt-detail.png) |

| System-Check mit Installationsanleitungen | Einstellungen |
|---|---|
| ![System-Check](docs/screenshots/ampel.png) | ![Einstellungen](docs/screenshots/einstellungen.png) |

## Voraussetzungen

- **Docker** (empfohlener Weg) — das Image enthält alles Weitere
- Ohne Docker: Python 3.11+, dazu je nach Nutzung:
  - `claude`-CLI (Claude Code) und/oder `kimi`-CLI, jeweils angemeldet
  - Higgsfield-CLI (`npm i -g @higgsfield/cli`, dann `higgsfield auth login` und
    `higgsfield workspace set <id>`) — **nicht nötig** bei KI-Medien = Nein
  - `ffmpeg`, optional lokales `whisper` oder ein OpenAI-kompatibler
    Transkriptionsdienst, optional Node 22+ (HyperFrames-Renders)

## Start

### Mit Docker (empfohlen)

Die Anmeldungen der CLIs kommen nicht ins Image, sondern werden aus dem
Home-Verzeichnis gemountet (Pfade in `docker-compose.yml` anpassen):

```sh
docker compose build
docker compose up -d
```

Danach http://localhost:8710 im Browser öffnen (bzw. http://\<host-ip\>:8710 aus dem
LAN — abschaltbar in den Einstellungen).

Dienste auf dem Host (z. B. ein SSH-Tunnel zum Whisper-Dienst) sind im Container
über `host.docker.internal` erreichbar — in den Einstellungen also
`http://host.docker.internal:<port>/v1` eintragen.

### Ohne Docker (Entwicklung)

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

Der System-Check in der App zeigt, was fehlt (Kacheln anklicken für Anleitungen).

## Konfiguration

Alle Einstellungen im UI (Tab „Einstellungen"), gespeichert in `config.json`
(**gitignored** — dort liegen auch API-Keys und Cloudflare-Tokens):

| Einstellung | Bedeutung |
|---|---|
| Agenten-Backend | `claude` (primär) oder `kimi` (Fallback) |
| Default-design.md | Pfad zu einer eigenen CI-Datei |
| Transkription | lokal (Whisper-Befehl) oder API (OpenAI-kompatibel: URL, Key, Modell, optional Cloudflare-Access-Token) |
| LAN erreichbar | **Default aus** = nur localhost; an = `0.0.0.0` (kein Login — jedes Gerät im Netz darf). Nur in vertrauten Netzen einschalten |
| Port | Default 8710 |

## Datenablage

Pro Schulung ein Ordner `projects/<slug>/` (gitignored): `brief.json`,
`status.json` (Phase, Agenten-Sessions, Guthaben), `curriculum.md`, `kosten.json`,
`events.jsonl` (Fortschritts-Protokoll), `material/`, `medien/`, fertige HTML.
Löschen geht direkt in der App: im Projekt ganz unten „Schulung löschen", nach
einer Rückfrage verschwindet der komplette Ordner. Während ein Agent arbeitet,
ist das gesperrt.

## Teilnehmer-Portal

Fertige Schulungen lassen sich an Teilnehmer ausgeben. Der Weg:

1. **Teilnehmer anlegen** (Reiter „Teilnehmer"): E-Mail, Name, Firma.
2. **Schulung zuordnen** — nur Schulungen, für die eine Prüfung erzeugt wurde.
3. **Freischalten**: erzeugt das Passwort und öffnet den Zugang für 30 Tage.
   Das Passwort wird **einmal** angezeigt und ist danach nicht mehr abrufbar.
4. Der Teilnehmer meldet sich unter `/portal` an, arbeitet die Lerneinheit
   durch und legt die Abschlussprüfung ab — drei Versuche.
5. Bei Bestehen gibt es den Nachweis als druckbare Seite.

Die Prüfung wird **auf dem Server** ausgewertet; die richtigen Antworten
verlassen ihn nicht. Die Daten liegen in `data/kurse.db` (gitignored); ein
Cron sichert sie täglich (`scripts/backup-kurse-db.sh`, 30 Tage).

**Welchen Nachweis es gibt, entscheidet der Kurs.** „AI-SmartCon-Zertifikat"
heißt: mit Prüfung, Nachweis erst nach Bestehen. „Teilnahmebestätigung" heißt:
ohne Prüfung, Nachweis ab der Freischaltung — der Ausdruck sagt dann „hat
teilgenommen" statt „hat erfolgreich abgeschlossen". Nie „staatlich
anerkannt", kein AZAV, kein Bildungsgutschein: Erwachsenenbildung ist
erlaubnisfrei, AI-SmartCon stellt in eigenem Namen aus.

## Anmeldung und Kurse

Der Weg vom Interessenten zum Teilnehmer, ohne Handarbeit an der Datenbank:

1. **Kurs anlegen** (Reiter „Kurse"): Kürzel, Titel, Preis, Plätze, die
   zugehörige Schulung und die Nachweis-Bezeichnung.
2. **Termine erzeugen** — Wochentag, Uhrzeit und Rhythmus ergeben eine Serie,
   daraus werden die Termine der nächsten 26 Wochen angelegt. Ein Kurs ohne
   Serie ist terminloses E-Learning und jederzeit buchbar.
3. **Der Interessent meldet sich selbst an** unter `/anmeldung/<kürzel>` und
   bekommt eine Bestätigungsmail. Öffentlich sichtbar ist nie eine Platzzahl,
   nur „offen" oder „ausgebucht".
4. **Rechnung stellen** (von Hand), dann im Reiter „Anmeldungen" auf
   `bezahlt` setzen.
5. **„Zugang freischalten"** macht daraus einen Teilnehmer mit Portalzugang
   und schickt die Zugangsdaten per Mail. Das Passwort erscheint zusätzlich
   **einmal** im Kasten oben — danach ist es nicht mehr abrufbar.

Der Mailversand läuft über SMTP aus der `config.json` (`smtp_host`,
`smtp_port`, `smtp_user`, `smtp_passwort`, `smtp_von`, `portal_url`). Ohne
diese Werte funktioniert die Anmeldung weiter, nur ohne Mail — die Kachel
„Mailversand" im System-Check zeigt das an.

## Erreichbarkeit von außen

Öffentlich sind **nur** `/anmeldung*` und `/portal*`. Die Werkstatt wird über
den Tunnel gar nicht erst geroutet — sie startet Agenten mit Bash-Rechten und
gehört ins Hausnetz.

Die App hat dafür einen **eigenen** Cloudflare-Tunnel (`smartcon-kurse`,
Konfiguration `~/.cloudflared/smartcon-kurse.yml`, Dienst
`cloudflared-smartcon-kurse.service`) — getrennt von den übrigen Diensten des
Hauses, damit ein Neustart hier nichts anderes mitnimmt. Die Regel:

```yaml
  - hostname: kurse.smartcon-ai.de
    path: ^/(anmeldung|portal)(/.*)?$
    service: http://localhost:8710
  - hostname: kurse.smartcon-ai.de
    service: http_status:404
```

Nach jeder Änderung daran aus einem **fremden** Netz gegenprüfen:
`/anmeldung` muss 200 liefern, `/api/projekte` 404.

## Architektur in Kürze

```
Browser (Vanilla JS Wizard)
   │  HTTP + SSE
FastAPI (lokal/Docker)
   │  Subprozess + stream-json
claude -p  /  kimi -p   ← schulung-Skill (im Repo: skill/schulung/)
   │  CLI-Aufrufe
higgsfield · ffmpeg · Whisper-API · (HyperFrames)
   │
projects/<slug>/  — status.json, curriculum.md, Medien, fertige HTML
```

Die App besitzt die State-Machine (Briefing → Curriculum → Gate → Produktion →
fertig), der Agent arbeitet pro Phase mit klaren Arbeitsaufträgen zu. Details:
[TECH_STACK.md](TECH_STACK.md) und [SPEC.md](SPEC.md).
