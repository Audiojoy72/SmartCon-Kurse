# Skill-Verfügbarkeit: lädt `claude -p` im Container den Plugin-Skill `smartcon-praesentation`?

Datum: 2026-08-07

## Ausgangslage

`skill/schulung/` ist der neutrale Schulungs-Skill der App; er wird per `COPY`
ins Image gebacken. Der neue Präsentations-Skill `smartcon-praesentation`
liegt dagegen nicht im Repo, sondern als **Plugin-Skill** auf dem Host unter
`~/.claude/plugins/cache/smartcon-skills/praesentation/1.1.0/skills/smartcon-praesentation`.
Der Host-Ordner `~/.claude` ist bereits nach `/root/.claude` gemountet
(`docker-compose.yml`), die Dateien sind im Container also sichtbar. Offen war,
ob `claude -p` im Container den Plugin-Mechanismus auch tatsächlich lädt —
sichtbare Dateien sind nicht dasselbe wie ein geladener Skill.

## Test 1: vor der Änderung

Kommando (aus dem Task-Brief; `-lc` musste zu `-c` geändert werden — der
Login-Shell-Modus (`-l`) setzt im `python:3.11-slim`-Image die `PATH`-ENV aus
dem Dockerfile über `/etc/profile` zurück, wodurch `claude` nicht gefunden
wurde; mit `-c` bleibt die vom Container ererbte `PATH` erhalten und
`claude -p ...` verhält sich identisch zum Brief-Kommando):

```bash
docker exec smartcon-schulungen sh -c \
  'claude -p "Liste die Namen aller dir verfügbaren Skills auf, einer pro Zeile. Sonst nichts." \
   --permission-mode acceptEdits' | grep -i praesentation
```

Vollständige Ausgabe von `claude -p` (vor `grep`):

```
grill-me
hyperframes
hyperframes-animation
hyperframes-cli
hyperframes-core
hyperframes-keyframes
impeccable
commit
create-prd
execute
init-project
plan-feature
prime
refactor
shutdown
dataviz
update-config
keybindings-help
simplify
fewer-permission-prompts
loop
schedule
claude-api
run
init
security-review
```

`grep -i praesentation` liefert **keinen Treffer** (Exit-Code 1).

**Ergebnis: negativ.** Der Plugin-Mechanismus (Skills aus
`~/.claude/plugins/cache/...`) ist in `claude -p` im Container nicht aktiv,
obwohl die Dateien über den `.claude`-Mount sichtbar sind. Alle gelisteten
Skills stammen aus lokal referenzierten Skill-Verzeichnissen
(`~/.claude/skills/...`), nicht aus dem Plugin-Cache.

## Gewählter Ausweg: A (bevorzugt)

Der Skill-Ordner wird zusätzlich direkt unter `/root/.claude/skills/` gemountet
— dort, wo auch das DSS-Vergleichssystem seinen `dss-praesentation`-Skill
ablegt. In `docker-compose.yml`:

```yaml
- $HOME/.claude/plugins/cache/smartcon-skills/praesentation/1.1.0/skills/smartcon-praesentation:/root/.claude/skills/smartcon-praesentation:ro
```

Begründung für A statt B (`COPY` ins Image): der Skill bleibt so am
Plugin-Ursprungsort einzig gepflegt und aktualisiert sich beim nächsten
Container-Neustart automatisch mit — kein Doppel-Pflegeaufwand, kein Rebuild
nötig, wenn sich nur der Skill-Inhalt ändert.

## Test 2: nach der Änderung (Verifikation)

Nach `docker compose build && docker compose up -d`:

```bash
docker exec smartcon-schulungen sh -c 'ls -la /root/.claude/skills/'
```

zeigt `smartcon-praesentation` neben den anderen lokalen Skills.

Erneuter Skill-Check (gleiches Kommando wie oben, ohne `grep`) listet jetzt
zusätzlich:

```
...
impeccable
smartcon-praesentation
commit
...
```

**Ergebnis: positiv.** `claude -p` im Container sieht `smartcon-praesentation`
jetzt als verfügbaren Skill. Der Prompt für die Präsentations-Phase kann sich
auf den Pfad `/root/.claude/skills/smartcon-praesentation/` verlassen.

## Nebenbefund

`soffice` ist im Image unter diesem Namen direkt vorhanden (`/usr/bin/soffice`,
LibreOffice 25.2.3.2) — der in Task 16 (`app/folien.py`) vorgesehene
Fallback-Check auf `libreoffice` war nicht nötig.
