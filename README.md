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

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

Danach http://localhost:8710 im Browser öffnen.

## Lizenz

AGPL-3.0, siehe [LICENSE](LICENSE).
