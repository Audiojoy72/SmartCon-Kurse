# SmartCon-Schulungen

Interaktive Schulungen per Formular-App erstellen: Eine lokale Web-Oberfläche führt
Schritt für Schritt vom Briefing über das Curriculum (mit Freigabe-Gate) bis zur
fertigen, offline lauffähigen HTML-Lerneinheit — mit KI-Videos, Erklär-Animationen,
Voiceover, Gamification und Quiz. Die Denkarbeit übernimmt ein KI-Agent im Hintergrund
(Claude Code oder Kimi, umschaltbar), die App steuert die Phasen.

Gebaut von **AI-SmartCon – Matthias Geist**.
Danke an **Julian Ivanov** für den tollen Skill.

## Status

Frühe Entwicklung. Das verbindliche Pflichtenheft steht in [SPEC.md](SPEC.md).

## Voraussetzungen

- Python 3.11+
- `claude`-CLI (Claude Code) und/oder `kimi`-CLI, jeweils angemeldet
- Higgsfield-CLI (`npm i -g higgsfield`, danach `higgsfield auth login` und
  `higgsfield workspace set <id>`) für Videos, Bilder und Voiceover
- `ffmpeg`
- optional: lokales `whisper` für Transkription, Node 22+ für HyperFrames

## Start

### Mit Docker (empfohlen)

Das Image enthält die App **und** alle Werkzeuge (claude-/kimi-CLI, Higgsfield-CLI,
ffmpeg, Node 22, cloudflared, openssh). Die Anmeldungen der CLIs kommen nicht ins
Image, sondern werden aus dem Home-Verzeichnis gemountet (Pfade in
`docker-compose.yml` anpassen):

```sh
docker compose build
docker compose up -d
```

Danach http://localhost:8710 im Browser öffnen (bzw. http://<host-ip>:8710 aus dem LAN).

Dienste, die auf dem Host laufen (z. B. ein SSH-Tunnel zum Whisper-Dienst), sind im
Container über `host.docker.internal` erreichbar — in den Einstellungen also
`http://host.docker.internal:<port>/v1` eintragen.

### Ohne Docker (Entwicklung)

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

Dabei müssen die Werkzeuge auf dem Host installiert sein — der System-Check in der
App zeigt, was fehlt (Kacheln anklicken für Installationsanleitungen).

## Lizenz

AGPL-3.0, siehe [LICENSE](LICENSE).
