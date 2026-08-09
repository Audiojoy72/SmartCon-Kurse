# SmartCon-Schulungen — Pflichtenheft (v1)

Erarbeitet per grill-me-Interview am 2026-07-31. Jede Entscheidung einzeln bestätigt.
**Umsetzung beginnt erst nach expliziter Bestätigung dieses Dokuments.**

## Ziel

Eine lokale Formular-App, die den Schulungs-Workflow des `schulung`-Skills Schritt für
Schritt durch eine grafische Oberfläche führt — vom Briefing über das Curriculum mit
Freigabe-Gate bis zur fertigen, offline lauffähigen HTML-Lerneinheit. Die Denkarbeit
(Curriculum, Prompts, Choreografie) macht weiterhin ein KI-Agent im Hintergrund.

Spätere Veröffentlichung als Public-Repo auf GitHub, Lizenz **AGPL**, Doku deutsch,
selbstbeschreibend. Footer der App: **„AI-SmartCon – Matthias Geist"** und
**„Danke an Julian Ivanov für den tollen Skill"**.

## Die 16 Entscheidungen

| # | Frage | Entscheidung |
|---|---|---|
| 1 | Wer denkt? | **KI-Agent im Hintergrund**; die App ist Formular-Oberfläche, kein reiner Wizard |
| 2 | Welcher Agent? | **Umschaltbar, Default Claude Code** (`claude -p --output-format stream-json`), Kimi als Fallback; Skill bei Bedarf für Kimi anpassen |
| 3 | Nutzerkreis | **Nur Matthias, Default localhost** — kein Login, kein Deployment. **LAN-Zugriff ist seit 01.08.2026 zuschaltbar** (Einstellung „LAN erreichbar" → `0.0.0.0`), damit die Oberfläche vom Handy aus bedienbar ist; **Default bleibt aus**. Im offenen Netz nicht einschalten: es gibt keinen Login, und wer die App erreicht, kann über Briefing- oder Kommentartext Agenten-Läufe mit Bash-Rechten auslösen |
| 4 | Tech-Stack | **FastAPI + Vanilla JS**, kein Build-Schritt, `venv` im Projektordner; SSE für Fortschritt; CLIs als Subprozesse |
| 5 | Wer führt? | **Die App besitzt die State-Machine** (11 Phasen + Gate); der Agent bekommt pro Phase einen Arbeitsauftrag; Phasenlogik als Prompt-Templates, die auf die SKILL.md verweisen |
| 6 | Stil-Freiheit | **Preset-Bibliothek im Skill** (z. B. `reference/styles/*.md`): Stil-Block, Guide-Figur, Medien-Defaults, Kostenrahmen je Preset. Mehrere neutrale Presets, **ohne DSS-/AISC-Bezug**. Eigene `design.md` einles-/übergebbar; eigene Figuren hochladbar (→ Skill-Phase 6c); Custom-Prompt-Felder. **Präzisiert am 03.08.2026:** Preset und `design.md` sind zwei unabhängige Achsen — das Preset besitzt Machart, Medienplan und Higgsfield-Einsatz, die `design.md` nur die Optik (Farben, Schriften, Tonalität) und hat dort Vorrang. „Eigene design.md" ist deshalb **kein** eigener Stil mehr, sondern ein optionales Feld neben der Preset-Wahl |
| 7 | Öffentlich vs. privat | **Neutrale Skill-Kopie lebt im App-Repo** (`skill/`). Der private smartcon-skills-Skill bleibt unangetastet. Defaults ohne persönliche Infrastruktur: lokales Whisper, Auslieferung = Download; DSS-KI/Nextcloud nur als optionale Config |
| 8 | Curriculum-Eingriff | **Review + Markdown-Editor + Kommentar-Box**, dazu **Medium-Dropdown je Level** (Film/Animation/Bild/statisch) als Annotation beim Go |
| 9 | Kosten | **Kosten-Dashboard am Gate**: Schätzung je Posten, Summe, Higgsfield-Guthaben, reicht/reicht-nicht; Live-Nachmessung per `generate cost` beim Go; Verbrauchs-Zähler während der Produktion, soweit aus dem Stream ableitbar |
| 10 | Projektverwaltung | **Projektliste**, Ordner `projects/<slug>/` (Briefing, design.md, Figuren, curriculum.md, Medien, HTML, status.json), **Fortsetzen via Session-Resume** (`claude -r` / `kimi -r`), einzelne Phasen wiederholbar; **Löschen aus der UI** (Button unten im Projekt, zweistufig bestätigt, entfernt den ganzen Ordner; gesperrt während ein Agent läuft) — nachgereicht am 01.08.2026, in v1 war das noch ausgeschlossen |
| 11 | Setup | Name **„SmartCon-Schulungen"**, Ort `/media/synology/coding/AntiGravity/SmartCon-Schulungen`, **AGPL**, Doku deutsch |
| 12 | Einstellungen | **Settings-Screen + Preflight-Ampel** (Backend-Wahl, Pfade, Higgsfield-Workspace, Default-design.md), gespeichert als `config.json` |
| 13 | Nicht-Ziele v1 | kein Mehrnutzer, kein Login, kein Deployment; kein Budget-Deckel; keine strukturierte Curriculum-Bearbeitung; kein Zertifikat; keine eigenen Generatoren; kein SCORM/LMS |
| 14 | History | **Projektliste = Archiv**: fertige Schulungen bleiben gelistet (Status, Datum, Credits); HTML im Projektordner, aus der History **aufrufbar und herunterladbar**; **Nachbearbeiten** = Rücksprung in eine Phase über App+Agent (nicht: HTML direkt editieren), mit Kosten-Hinweis bei produktionsrelevanten Änderungen |
| 15 | Prüfung im Portal | **Serverseitige Auswertung.** Die richtigen Antworten stehen in `pruefung.json` und verlassen den Server nicht. Drei Versuche je Teilnahme, Zählung in `data/kurse.db`. Die verschickbare Prüfungsseite (`pruefung.als_html()`) bleibt daneben bestehen — sie hat einen anderen Zweck und darf ihre Lösungen mitbringen |
| 16 | Nachweis | **Druckbare HTML-Seite, kein serverseitiges PDF.** Bezeichnung aus der Teilnahme: „Teilnahmebestätigung", bei bestandener Prüfung „AI-SmartCon-Zertifikat". **Nie** „staatlich anerkannt", kein AZAV, kein Bildungsgutschein — Erwachsenenbildung ist erlaubnisfrei, AI-SmartCon stellt in eigenem Namen aus |

## Architektur in einem Bild

```
Browser (Vanilla JS Wizard)
   │  HTTP + SSE
FastAPI (lokal, localhost — LAN optional zuschaltbar)
   │  Subprozess + stream-json
claude -p  /  kimi -p   ← neutraler schulung-Skill (im Repo: skill/)
   │  CLI-Aufrufe
higgsfield · ffmpeg · whisper · (hyperframes)
   │
projects/<slug>/  — status.json, curriculum.md, Medien, fertige HTML
```

## Wizard-Schritte (aus den Skill-Phasen abgeleitet)

1. **Briefing** — Thema, Lernziele, Zielgruppe, Sprache, Dauer, Marke (Preset oder eigene design.md), Ansprache
2. **Stil & Figuren** — Preset-Karten, Figuren-Upload, statisch/bewegt, Custom-Prompts
3. **Curriculum erzeugen** — Agent schreibt `curriculum.md` (Fortschritt per SSE)
4. **Freigabe-Gate** — Markdown-Editor, Kommentar-Box, Medium-Dropdown je Level, Kosten-Dashboard → Go
5. **Produktion** — Phasen-Fortschrittsbalken, Verbrauchs-Zähler, abbrechbar/fortsetzbar
6. **Fertig** — Vorschau im Browser, Download, Eintrag in der History
