# SmartCon-Kurse — Werkstatt (Etappe 0–3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Schulungswerkstatt um eine vorgelagerte Präsentations-Phase (Thema + Quellen → `.pptx` im AI-SmartCon-CI), eine Prüfungs-Phase (`pruefung.json` + offline lauffähige Prüfungs-HTML aus dem *ausgelieferten* Stoff) und einen Schalter „Folien einbetten" erweitern — auf einem Fundament aus automatisierten Tests.

**Architecture:** Die App behält ihre State-Machine und ihr Dateisystem-Modell. Eine Präsentation ist ein eigenes Projekt (`brief.json` mit `"art": "praesentation"`), dessen Lauf den Skill `smartcon-praesentation` aufruft und eine `.pptx` in den Projektordner schreibt. Der Review-Bruch bleibt manuell: Matthias lädt die Datei herunter, überarbeitet sie und hängt sie beim Anlegen der Schulung als Material an. Die Prüfung entsteht aus `stoffquelle()` — hochgeladene Folien schlagen erzeugte HTML schlägt Curriculum.

**Tech Stack:** Python 3.11, FastAPI, Vanilla JS ohne Build, pytest + httpx (neu, nur Dev), python-pptx + LibreOffice + poppler-utils (neu, im Image), Skill `smartcon-praesentation` (deckkit).

## Global Constraints

- UI-Texte, Doku und Kommentare **auf Deutsch**; Code-Identifier englisch.
- Keine neuen Laufzeit-Dependencies in `requirements.txt` ohne Not. pytest/httpx kommen in eine getrennte `requirements-dev.txt` und **nicht** ins Image.
- Kein Framework im Frontend.
- Fehlerfälle: 404 Projekt unbekannt, 409 Agenten-Lauf aktiv, 400 Validierung.
- Pro Projekt nur ein Agenten-Lauf gleichzeitig (`runner.laeuft`).
- Dateipfade aus Nutzereingaben immer sanitizen (`projekte._dateiname()`, `_SLUG_RE`).
- Frontend muss bei **390 px und 320 px** ohne horizontalen Überlauf funktionieren. Flex-Zeilen brauchen `flex-wrap`, breite Tabellen `.tabelle-scroll`.
- `hidden` allein versteckt nichts: Zu jeder neuen CSS-Regel mit eigenem `display` gehört eine `[hidden]`-Variante. Sichtbarkeit im Test über `getComputedStyle(el).display` prüfen, nicht über `el.hidden`.
- Nach jeder Frontend-Änderung `?v=` in `static/index.html` hochzählen.
- **Nie rebuilden, während ein Agent arbeitet** — Container-Neustart killt laufende Produktionen. Vorher prüfen: `grep -l laeuft projects/*/status.json`.
- Das Projekt `claude-und-codex-sicher-und-rechtskonform-einsetzen` bleibt in Phase `curriculum_fertig` **unangetastet**.
- Preset und `design.md` bleiben zwei unabhängige Achsen. Die Präsentation nutzt **keine** von beiden — der Skill bringt sein eigenes Layout mit.

## File Structure

| Datei | Verantwortung | Status |
|---|---|---|
| `requirements-dev.txt` | pytest, httpx — nur Entwicklung | neu |
| `pytest.ini` | Testpfad, Marker | neu |
| `tests/conftest.py` | Fixtures: temporärer `PROJECTS`-Ordner, TestClient | neu |
| `tests/test_curriculum.py` | Level-Parser | neu |
| `tests/test_projekte.py` | Slugs, Dateinamen, Anlegen, Löschen | neu |
| `tests/test_prompts.py` | Prompt-Bausteine, Preset-Namen | neu |
| `tests/test_preflight.py` | Checks ohne echte Binaries | neu |
| `tests/test_api.py` | Endpunkte über TestClient | neu |
| `tests/test_stoffquelle.py` | Vorrangregel der Prüfungsgrundlage | neu (Etappe 2) |
| `tests/test_pruefung.py` | Schema-Validierung + Renderer | neu (Etappe 2) |
| `tests/test_folien.py` | Slide-Export | neu (Etappe 3) |
| `app/praesentation.py` | Alles zur Projektart „Präsentation": Prompt, Dateiname, Fundstellen | neu |
| `app/pruefung.py` | Schema-Validierung von `pruefung.json` + HTML-Renderer | neu |
| `app/folien.py` | PPTX → PDF → PNG über LibreOffice/pdftoppm | neu |
| `app/projekte.py` | + Phasen `praesentation_*`, `pruefung_*`; `art()`-Helfer | ändern |
| `app/prompts.py` | + `stoffquelle()`, `pruefung_prompt()`; delegiert Präsentation an `app/praesentation.py` | ändern |
| `app/config.py` | + `logo_pfad()`, `standard_logo()` | ändern |
| `app/preflight.py` | + Checks `pptx`, `libreoffice`, `logo`, `praesentation_skill` | ändern |
| `app/main.py` | + Routen für Präsentation, Prüfung, Logo-Upload | ändern |
| `static/index.html`, `app.js`, `style.css` | Reiter „Präsentationen", Prüfungsblock, Schalter | ändern |
| `Dockerfile` | + python-pptx, libreoffice-impress, poppler-utils | ändern |
| `skill/schulung/SKILL.md` | Produktionspfad „Folien einbetten" | ändern (Etappe 3) |

Neue Module statt Wachstum von `prompts.py` (404 Zeilen) und `main.py` (452 Zeilen): Präsentation, Prüfung und Folien-Export sind je eine abgeschlossene Verantwortung mit eigenem Testbedarf.

---

# Etappe 0 — Testfundament

Ziel: Der Bestand ist abgesichert, bevor Neues dazukommt. Erfolgskriterium: `pytest` läuft grün und hätte den Level-Parser-Bug vom 07.08. gefunden.

### Task 1: pytest-Gerüst und der Level-Parser

**Files:**
- Create: `requirements-dev.txt`, `pytest.ini`, `tests/__init__.py`, `tests/test_curriculum.py`
- Test: `tests/test_curriculum.py`

**Interfaces:**
- Consumes: `app.curriculum.parse_level(md: str) -> list[dict]`, `app.curriculum.normalisiere_medium(s: str) -> str`
- Produces: lauffähiges `pytest` für alle Folgetasks

- [ ] **Step 1: Dev-Abhängigkeiten und Konfiguration anlegen**

`requirements-dev.txt`:
```
-r requirements.txt
pytest==8.3.4
httpx==0.28.1
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

`tests/__init__.py`: leere Datei.

- [ ] **Step 2: Den Test schreiben, der den Bug vom 07.08. gefunden hätte**

`tests/test_curriculum.py`:
```python
"""Level-Parser: liest die Level-Übersicht aus einem curriculum.md."""

from app.curriculum import normalisiere_medium, parse_level

EINE_TABELLE = """
## 3. Level-Übersicht

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 1 | Ziel eins | Merk eins | **FILM** | Zeitleiste |
| 2 | Ziel zwei | Merk zwei | ANIMATION | Quiz |
| — | Abschluss-Check | — | — | 8 Fragen |
"""

ZWEI_TABELLEN = """
### Modul A

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 1 | Ziel eins | Merk eins | **FILM** | Zeitleiste |
| 2 | Ziel zwei | Merk zwei | ANIMATION | Quiz |

### Modul B

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 3 | Ziel drei | Merk drei | ANIMATION + BILD | Slider |
| 4 | Ziel vier | Merk vier | **FILM** | Story |
"""


def test_eine_tabelle_wird_gelesen():
    level = parse_level(EINE_TABELLE)
    assert [l["level"] for l in level] == ["1", "2"]
    assert level[0]["lernziel"] == "Ziel eins"
    assert level[1]["interaktion"] == "Quiz"


def test_zeile_ohne_nummer_wird_uebersprungen():
    # Die „Abschluss-Check"-Zeile hat keine Level-Nummer und ist kein Level.
    assert len(parse_level(EINE_TABELLE)) == 2


def test_zwei_tabellen_werden_zusammengefasst():
    # Der Bug vom 07.08.2026: Der Parser brach nach der ersten Tabelle ab,
    # dadurch fehlten im Freigabe-Gate fünf Level — darunter ein FILM für
    # 243 Credits, der so weder sichtbar noch herunterstufbar war.
    level = parse_level(ZWEI_TABELLEN)
    assert [l["level"] for l in level] == ["1", "2", "3", "4"]


def test_doppelte_level_nummer_erstes_gewinnt():
    md = ZWEI_TABELLEN + """
### Wiederholung

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 1 | Anderes Ziel | Merk | BILD | Anders |
"""
    level = parse_level(md)
    assert [l["level"] for l in level] == ["1", "2", "3", "4"]
    assert level[0]["lernziel"] == "Ziel eins"


def test_ohne_passende_tabelle_leere_liste():
    assert parse_level("# Nur Text, keine Tabelle") == []
    assert parse_level("| a | b |\n|---|---|\n| 1 | 2 |") == []


def test_tabelle_ohne_trennzeile_ist_keine_tabelle():
    md = "| Level | Medium |\n| 1 | FILM |"
    assert parse_level(md) == []


def test_medium_normalisierung():
    assert normalisiere_medium("**FILM**") == "FILM"
    assert normalisiere_medium("ANIMATION + BILD (Hero)") == "ANIMATION"
    assert normalisiere_medium("  bild  ") == "BILD"
    assert normalisiere_medium("Sonstiges") == "SONSTIGES"
```

- [ ] **Step 3: Tests laufen lassen — sie müssen grün sein**

Run: `.venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest tests/test_curriculum.py -v`
Expected: 7 passed. Der Parser wurde am 07.08. bereits gefixt; diese Tests sichern den Fix ab. Schlägt `test_zwei_tabellen_werden_zusammengefasst` fehl, ist der Fix verloren gegangen — dann `app/curriculum.py` gegen den Stand aus Commit `a02ef54`+ prüfen.

- [ ] **Step 4: `.gitignore` und Doku nachziehen**

In `.gitignore` ergänzen:
```
.pytest_cache/
```

In `CLAUDE.md` unter „Commands" den Block ersetzen:
```sh
# Checks
.venv/bin/pip install -r requirements-dev.txt   # einmalig
.venv/bin/python -m pytest                      # Testsuite
.venv/bin/python -m py_compile app/*.py
node --check static/app.js
bash -n skill/schulung/scripts/*.sh
```
Den Satz „Kein Test-Framework — Verifikation läuft über den System-Check…" ersetzen durch: „pytest für die Logik (`tests/`), dazu der System-Check der App (`GET /api/preflight`) und End-to-End-Testprojekte für alles, was einen echten Agentenlauf braucht."

- [ ] **Step 5: Commit**

```bash
git add requirements-dev.txt pytest.ini tests/ .gitignore CLAUDE.md
git commit -m "test: pytest-Gerüst und Absicherung des Level-Parsers"
```

---

### Task 2: Projektverwaltung testen

**Files:**
- Create: `tests/conftest.py`, `tests/test_projekte.py`

**Interfaces:**
- Consumes: `app.projekte.slugify`, `_dateiname`, `_gueltig`, `create`, `projekt_dir`, `loeschen`, `liste`, `load_status`, `set_phase`
- Produces: Fixture `projekte_tmp` — setzt `projekte.PROJECTS` auf ein temporäres Verzeichnis; von allen Folgetasks genutzt

- [ ] **Step 1: Fixture schreiben**

`tests/conftest.py`:
```python
"""Gemeinsame Fixtures. Kein Test darf den echten projects/-Ordner anfassen."""

import pytest

from app import projekte


@pytest.fixture
def projekte_tmp(tmp_path, monkeypatch):
    """Leitet den Projektordner auf ein temporäres Verzeichnis um.

    monkeypatch statt Zuweisung: Der Wert wird nach jedem Test automatisch
    zurückgesetzt, auch wenn der Test mit einer Ausnahme endet.
    """
    ziel = tmp_path / "projects"
    ziel.mkdir()
    monkeypatch.setattr(projekte, "PROJECTS", ziel)
    return ziel
```

- [ ] **Step 2: Den Test schreiben**

`tests/test_projekte.py`:
```python
"""Projektordner: Slugs, Dateinamen, Anlegen, Löschen."""

import json

from app import projekte

BRIEF = {
    "thema": "Cyber Resilience Act",
    "lernziele": "Pflichten kennen",
    "zielgruppe": "KMU",
    "sprache": "Deutsch",
    "dauer": "60 Minuten",
    "stil": "kostenlos",
    "ki_medien": False,
}


def test_slugify_wandelt_umlaute_und_sonderzeichen():
    assert projekte.slugify("Über Größe & Maß") == "ueber-groesse-mass"
    assert projekte.slugify("  Mehrere   Wörter  ") == "mehrere-woerter"
    assert projekte.slugify("!!!") == "projekt"


def test_gueltig_weist_pfadtricks_ab():
    assert projekte._gueltig("kurs-1")
    assert not projekte._gueltig("../etc")
    assert not projekte._gueltig("/absolut")
    assert not projekte._gueltig("Gross")


def test_dateiname_entfernt_pfadanteile_und_prozentkodierung():
    assert projekte._dateiname("../../etc/passwd") == "passwd"
    assert projekte._dateiname("T%C3%9CV%20Vortrag.pptx") == "TÜV Vortrag.pptx"
    # unquote macht aus %2F einen Schrägstrich — der zweite basename fängt das ab.
    assert projekte._dateiname("a%2F..%2Fb.md") == "b.md"


def test_create_legt_ordner_und_dateien_an(projekte_tmp):
    slug = projekte.create(BRIEF, design_md=b"# CI", material=[("q.md", b"Quelle")])
    d = projekte_tmp / slug
    assert slug == "cyber-resilience-act"
    assert json.loads((d / "brief.json").read_text())["thema"] == BRIEF["thema"]
    assert (d / "design.md").read_bytes() == b"# CI"
    assert (d / "material" / "q.md").read_bytes() == b"Quelle"
    assert projekte.load_status(slug)["phase"] == projekte.PHASE_BRIEFING


def test_create_vergibt_bei_gleichem_thema_einen_freien_slug(projekte_tmp):
    erst = projekte.create(BRIEF)
    zweit = projekte.create(BRIEF)
    assert erst == "cyber-resilience-act"
    assert zweit == "cyber-resilience-act-2"


def test_material_ohne_namen_wird_verworfen(projekte_tmp):
    slug = projekte.create(BRIEF, material=[("", b"x"), ("gut.md", b"y")])
    namen = [p.name for p in (projekte_tmp / slug / "material").iterdir()]
    assert namen == ["gut.md"]


def test_projekt_dir_liefert_nur_gueltige_vorhandene_ordner(projekte_tmp):
    slug = projekte.create(BRIEF)
    assert projekte.projekt_dir(slug) == projekte_tmp / slug
    assert projekte.projekt_dir("gibt-es-nicht") is None
    assert projekte.projekt_dir("../etc") is None


def test_loeschen_entfernt_den_ordner(projekte_tmp):
    slug = projekte.create(BRIEF)
    assert projekte.loeschen(slug) is True
    assert not (projekte_tmp / slug).exists()
    assert projekte.loeschen(slug) is False


def test_liste_ignoriert_lose_dateien(projekte_tmp):
    # projects/aisc-design.md liegt dort bewusst als Standard-CI und ist kein Projekt.
    projekte.create(BRIEF)
    (projekte_tmp / "aisc-design.md").write_text("# CI")
    assert [p["slug"] for p in projekte.liste()] == ["cyber-resilience-act"]


def test_set_phase_schreibt_zeitstempel_und_fehler(projekte_tmp):
    slug = projekte.create(BRIEF)
    projekte.set_phase(slug, projekte.PHASE_FEHLER, fehler="kaputt")
    status = projekte.load_status(slug)
    assert status["phase"] == projekte.PHASE_FEHLER
    assert status["letzter_fehler"] == "kaputt"
    assert status["geaendert_am"] >= status["erstellt_am"]
```

- [ ] **Step 3: Tests laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_projekte.py -v`
Expected: alle grün. Schlägt einer fehl, ist es ein echter Fund — **erst prüfen, ob der Test die Erwartung richtig beschreibt**, dann den Code korrigieren, nicht den Test anpassen, bis er passt.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_projekte.py
git commit -m "test: Projektordner, Slugs und Dateinamen-Sanitisierung"
```

---

### Task 3: Prompt-Bausteine und Preflight testen

**Files:**
- Create: `tests/test_prompts.py`, `tests/test_preflight.py`

**Interfaces:**
- Consumes: `app.prompts.PRESET_NAMEN`, `presets()`, `curriculum_prompt()`, `kostenplan_prompt()`; `app.preflight.run_all(cfg)`
- Produces: nichts Neues

- [ ] **Step 1: Prompt-Tests schreiben**

`tests/test_prompts.py`:
```python
"""Prompt-Bausteine: Was im Arbeitsauftrag steht, entscheidet über das Ergebnis."""

import json

from app import prompts

BRIEF = {
    "thema": "Cyber Resilience Act",
    "lernziele": "Pflichten kennen",
    "zielgruppe": "KMU",
    "vorwissen": "",
    "sprache": "Deutsch",
    "dauer": "60 Minuten",
    "stil": "cinematic",
    "ki_medien": True,
    "material_hinweise": "",
}


def test_presets_sind_vollstaendig_und_beschrieben():
    namen = [p["name"] for p in prompts.presets()]
    assert set(namen) == set(prompts.PRESET_NAMEN)
    assert all(p.get("titel") and p.get("beschreibung") for p in prompts.presets())


def test_kostenlos_erzwingt_keine_ki_medien():
    # Preset kostenlos ist die 0-Credit-Zusage der App — sie darf nicht kippen.
    kostenlos = [p for p in prompts.presets() if p["name"] == "kostenlos"][0]
    assert kostenlos.get("ki_medien") is False


def test_curriculum_prompt_nennt_projektordner_und_briefing(tmp_path):
    prompt = prompts.curriculum_prompt(tmp_path, BRIEF)
    assert str(tmp_path) in prompt
    assert BRIEF["thema"] in prompt
    assert BRIEF["lernziele"] in prompt


def test_curriculum_prompt_erwaehnt_design_md_nur_wenn_sie_existiert(tmp_path):
    ohne = prompts.curriculum_prompt(tmp_path, BRIEF)
    assert "design.md" not in ohne

    (tmp_path / "design.md").write_text("akzent: \"#c9a84c\"")
    mit = prompts.curriculum_prompt(tmp_path, BRIEF)
    assert str(tmp_path / "design.md") in mit


def test_kostenplan_prompt_nennt_zielpfad_und_verlangt_nur_json(tmp_path):
    prompt = prompts.kostenplan_prompt(tmp_path)
    assert str(tmp_path / "kosten.json") in prompt
    assert "JSON" in prompt
```

- [ ] **Step 2: Preflight-Tests schreiben**

`tests/test_preflight.py`:
```python
"""Preflight-Ampel. Läuft ohne echte Binaries — geprüft wird die Logik."""

from app import config, preflight


def test_jeder_check_hat_die_pflichtfelder():
    checks = preflight.run_all(config.DEFAULTS)
    assert checks, "run_all darf nie eine leere Liste liefern"
    for c in checks:
        assert set(("id", "name", "status", "detail")) <= set(c)
        assert c["status"] in ("ok", "warn", "fail")


def test_check_ids_sind_eindeutig():
    ids = [c["id"] for c in preflight.run_all(config.DEFAULTS)]
    assert len(ids) == len(set(ids))


def test_design_check_meldet_fehlenden_pfad(tmp_path):
    cfg = {**config.DEFAULTS, "default_design_md": str(tmp_path / "gibt-es-nicht.md")}
    check = _finde(preflight.run_all(cfg), "design")
    assert check["status"] != "ok"
    assert "nicht gefunden" in check["detail"]


def test_design_check_ok_bei_vorhandener_datei(tmp_path):
    datei = tmp_path / "design.md"
    datei.write_text("akzent: \"#c9a84c\"")
    cfg = {**config.DEFAULTS, "default_design_md": str(datei)}
    assert _finde(preflight.run_all(cfg), "design")["status"] == "ok"


def test_ohne_hinterlegten_pfad_gibt_es_keinen_design_check():
    cfg = {**config.DEFAULTS, "default_design_md": ""}
    assert _finde(preflight.run_all(cfg), "design") is None


def _finde(checks, check_id):
    return next((c for c in checks if c["id"] == check_id), None)
```

- [ ] **Step 3: Tests laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_prompts.py tests/test_preflight.py -v`
Expected: alle grün. `test_kostenlos_erzwingt_keine_ki_medien` schlägt fehl, wenn `presets()` das Feld nicht liefert — dann in `app/prompts.py:presets()` prüfen, wie das Preset `kostenlos` beschrieben ist, und den Test an die tatsächliche Feldbenennung anpassen (der *Sachverhalt* muss geprüft bleiben).

- [ ] **Step 4: Commit**

```bash
git add tests/test_prompts.py tests/test_preflight.py
git commit -m "test: Prompt-Bausteine und Preflight-Logik"
```

---

### Task 4: Endpunkte über den TestClient

**Files:**
- Create: `tests/test_api.py`
- Modify: `tests/conftest.py` (Fixture `client`)

**Interfaces:**
- Consumes: `app.main.app`
- Produces: Fixture `client` — `fastapi.testclient.TestClient` mit umgeleitetem Projektordner

- [ ] **Step 1: Client-Fixture ergänzen**

An `tests/conftest.py` anhängen:
```python
@pytest.fixture
def client(projekte_tmp, monkeypatch):
    """TestClient mit temporärem Projektordner und ohne echte Agentenläufe."""
    from fastapi.testclient import TestClient

    from app import main, runner

    # Kein Test startet je einen echten Agenten: start() wird ersetzt und
    # merkt sich nur, womit es aufgerufen wurde.
    gestartet = []
    monkeypatch.setattr(runner, "start",
                        lambda *a, **kw: gestartet.append((a, kw)))
    monkeypatch.setattr(runner, "laeuft", lambda slug: False)

    c = TestClient(main.app)
    c.gestartet = gestartet
    return c
```

- [ ] **Step 2: Den Test schreiben**

`tests/test_api.py`:
```python
"""Endpunkte. Agentenläufe sind ersetzt — geprüft wird die HTTP-Schicht."""

FORM = {
    "thema": "Cyber Resilience Act",
    "lernziele": "Pflichten kennen",
    "zielgruppe": "KMU",
    "sprache": "Deutsch",
    "dauer": "60 Minuten",
    "stil": "kostenlos",
}


def test_projekt_anlegen_liefert_slug(client):
    antwort = client.post("/api/projekte", data=FORM)
    assert antwort.status_code == 201
    assert antwort.json()["slug"] == "cyber-resilience-act"


def test_thema_und_lernziele_sind_pflicht(client):
    assert client.post("/api/projekte", data={**FORM, "thema": " "}).status_code == 400
    assert client.post("/api/projekte", data={**FORM, "lernziele": ""}).status_code == 400


def test_unbekannter_stil_wird_abgewiesen(client):
    assert client.post("/api/projekte", data={**FORM, "stil": "quatsch"}).status_code == 400


def test_unbekanntes_projekt_ist_404(client):
    assert client.get("/api/projekte/gibt-es-nicht").status_code == 404
    assert client.delete("/api/projekte/gibt-es-nicht").status_code == 404


def test_pfadtrick_im_slug_ist_kein_treffer(client):
    assert client.get("/api/projekte/..%2F..%2Fetc").status_code in (400, 404)


def test_curriculum_starten_setzt_phase_und_startet_den_agenten(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    antwort = client.post(f"/api/projekte/{slug}/curriculum/starten")
    assert antwort.status_code == 200
    assert antwort.json()["phase"] == "curriculum_laeuft"
    assert client.gestartet, "runner.start wurde nicht aufgerufen"


def test_kostenplan_ohne_curriculum_ist_404(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert client.post(f"/api/projekte/{slug}/gate/kostenplan").status_code == 404


def test_default_design_md_landet_im_projekt(client, tmp_path, monkeypatch):
    # Der Fix vom 06.08.2026: Der Pfad aus den Einstellungen wurde geprüft,
    # aber beim Anlegen nie gelesen — die Schulung entstand ohne CI.
    from app import config, projekte

    datei = tmp_path / "aisc-design.md"
    datei.write_text("akzent: \"#c9a84c\"")
    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "default_design_md": str(datei)})

    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert (projekte.projekt_dir(slug) / "design.md").read_text() == datei.read_text()


def test_unlesbarer_default_design_md_ist_400(client, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS,
                                 "default_design_md": "/gibt/es/nicht.md"})
    antwort = client.post("/api/projekte", data=FORM)
    assert antwort.status_code == 400
    assert "design" in antwort.json()["detail"].lower()


def test_hochgeladene_design_md_schlaegt_den_standard(client, tmp_path, monkeypatch):
    from app import config, projekte

    standard = tmp_path / "standard.md"
    standard.write_text("standard")
    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "default_design_md": str(standard)})

    slug = client.post("/api/projekte", data=FORM,
                       files={"design_md": ("eigen.md", b"eigen")}).json()["slug"]
    assert (projekte.projekt_dir(slug) / "design.md").read_bytes() == b"eigen"
```

- [ ] **Step 3: Tests laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_api.py -v`
Expected: alle grün.

- [ ] **Step 4: Die volle Suite laufen lassen**

Run: `.venv/bin/python -m pytest -v`
Expected: alles grün, keine Warnung über einen angefassten echten `projects/`-Ordner. Gegenprobe: `git status --short projects/` muss leer bleiben.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_api.py
git commit -m "test: Endpunkte über den TestClient, inkl. Default-design.md"
```

---

# Etappe 1 — Deck-Werkstatt

Ziel: Aus Thema und Quellen entsteht eine `.pptx` im AI-SmartCon-CI, herunterladbar aus der App. Erfolgskriterium: ein echter Lauf liefert eine Datei, die sich in PowerPoint öffnen lässt und Navy/Gold zeigt.

### Task 5: Das Risiko zuerst — Skill und Werkzeuge im Container

**Files:**
- Modify: `Dockerfile`
- Create: `docs/superpowers/notizen/2026-08-07-skill-verfuegbarkeit.md`

**Interfaces:**
- Produces: belegte Antwort auf die Frage, ob `claude -p` im Container den Plugin-Skill `smartcon-praesentation` lädt

**Diese Task steht bewusst vorn.** Fällt sie negativ aus, ändert sich der Zuschnitt der ganzen Etappe: Der Skill müsste dann ins Image kopiert oder als eigener Ordner gemountet werden, statt sich auf den Plugin-Mechanismus zu verlassen.

- [ ] **Step 1: Prüfen, ob ein Agent im Container den Skill sieht**

```bash
docker exec smartcon-schulungen sh -lc \
  'claude -p "Liste die Namen aller dir verfügbaren Skills auf, einer pro Zeile. Sonst nichts." \
   --permission-mode acceptEdits' | grep -i praesentation
```
Erwartet: eine Zeile mit `smartcon-praesentation`. Kommt nichts, ist der Plugin-Mechanismus im Container nicht aktiv.

- [ ] **Step 2: Ergebnis festhalten**

`docs/superpowers/notizen/2026-08-07-skill-verfuegbarkeit.md` anlegen mit: Datum, ausgeführtem Kommando, vollständiger Ausgabe, Schlussfolgerung. Bei negativem Ausgang zusätzlich notieren, welcher der beiden Auswege gewählt wurde:
- **Ausweg A (bevorzugt):** In `docker-compose.yml` den Skill-Ordner zusätzlich als eigenen Skill mounten:
  `- $HOME/.claude/plugins/cache/smartcon-skills/praesentation/1.1.0/skills/smartcon-praesentation:/root/.claude/skills/smartcon-praesentation:ro`
  Damit liegt er dort, wo DSS seinen `dss-praesentation` hat, und der Prompt kann den Pfad `/root/.claude/skills/smartcon-praesentation/` nennen.
- **Ausweg B:** Skill über `COPY` ins Image. Verwirft die Aktualisierung ohne Rebuild und verdoppelt die Pflege — nur, wenn A scheitert.

- [ ] **Step 3: Werkzeuge ins Image aufnehmen**

In `Dockerfile` den Systempaket-Block ersetzen:
```dockerfile
# Systempakete: ffmpeg (Muxing), curl/ca-certificates (Installer),
# openssh-client (Tunnel zum Transkriptionsdienst), git (Agent-Workflows),
# libreoffice-impress + poppler-utils (PPTX → PDF → PNG für Deck-QA und
# den Produktionspfad „Folien einbetten")
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl ca-certificates openssh-client git gnupg \
        libreoffice-impress poppler-utils fonts-inter \
    && rm -rf /var/lib/apt/lists/*
```

In `requirements.txt` ergänzen (der Skill baut damit die Datei, das ist Laufzeit, nicht Entwicklung):
```
python-pptx==1.0.2
```

- [ ] **Step 4: Bauen und die Werkzeuge nachweisen**

**Vorher prüfen, dass kein Agent läuft:** `grep -l laeuft projects/*/status.json` muss leer bleiben.

```bash
docker compose build && docker compose up -d && sleep 5
docker exec smartcon-schulungen sh -lc \
  'python3 -c "import pptx; print(\"python-pptx\", pptx.__version__)"; \
   soffice --version; pdftoppm -v'
```
Expected: eine python-pptx-Version, eine LibreOffice-Version, eine poppler-Version. Fehlt `soffice`, heißt das Binary im Image anders — dann `which libreoffice` gegenprüfen und den Namen in `app/folien.py` (Task 16) entsprechend setzen.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile requirements.txt docs/superpowers/notizen/
git commit -m "build: LibreOffice, poppler und python-pptx fuer die Deck-Werkstatt"
```

---

### Task 6: Logo in den Einstellungen

**Files:**
- Modify: `app/config.py`, `app/preflight.py`, `app/main.py`, `static/index.html`, `static/app.js`
- Test: `tests/test_config_logo.py`

**Interfaces:**
- Produces:
  - `app.config.LOGO_PFAD: Path` — `ROOT / "config-logo.png"`
  - `app.config.standard_logo() -> bytes | None`
  - `app.config.logo_speichern(daten: bytes) -> None`
  - `app.config.logo_loeschen() -> None`
  - Preflight-Check mit `id="logo"`
  - `POST /api/config/logo` (multipart, Feld `logo`), `DELETE /api/config/logo`

- [ ] **Step 1: Den Test schreiben**

`tests/test_config_logo.py`:
```python
"""Haus-Logo: liegt neben der config.json, nicht im Repo."""

import pytest

from app import config, preflight

PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)


@pytest.fixture
def logo_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGO_PFAD", tmp_path / "config-logo.png")
    return config.LOGO_PFAD


def test_ohne_datei_kein_logo(logo_tmp):
    assert config.standard_logo() is None


def test_speichern_und_lesen(logo_tmp):
    config.logo_speichern(PNG)
    assert config.standard_logo() == PNG


def test_loeschen_ist_auch_ohne_datei_harmlos(logo_tmp):
    config.logo_loeschen()
    config.logo_speichern(PNG)
    config.logo_loeschen()
    assert config.standard_logo() is None


def test_kein_png_wird_abgewiesen(logo_tmp):
    with pytest.raises(ValueError):
        config.logo_speichern(b"das ist kein PNG")


def test_preflight_meldet_fehlendes_logo(logo_tmp):
    check = _finde(preflight.run_all(config.DEFAULTS), "logo")
    assert check["status"] == "warn"


def test_preflight_ok_mit_logo(logo_tmp):
    config.logo_speichern(PNG)
    assert _finde(preflight.run_all(config.DEFAULTS), "logo")["status"] == "ok"


def _finde(checks, check_id):
    return next((c for c in checks if c["id"] == check_id), None)
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_config_logo.py -v`
Expected: FAIL mit `AttributeError: module 'app.config' has no attribute 'LOGO_PFAD'`.

- [ ] **Step 3: Implementieren**

An `app/config.py` anhängen:
```python
# Haus-Logo für den Präsentations-Skill. Liegt neben der config.json und ist
# gitignored — ins öffentliche Repo gehört keine Bildmarke.
LOGO_PFAD = ROOT / "config-logo.png"

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def standard_logo() -> bytes | None:
    """Das hinterlegte Logo, oder None."""
    try:
        return LOGO_PFAD.read_bytes()
    except OSError:
        return None


def logo_speichern(daten: bytes) -> None:
    """Legt das Logo ab. Nur PNG — der Skill bettet es unverändert ein."""
    if not daten.startswith(_PNG_MAGIC):
        raise ValueError("Nur PNG-Dateien werden angenommen")
    LOGO_PFAD.write_bytes(daten)


def logo_loeschen() -> None:
    LOGO_PFAD.unlink(missing_ok=True)
```

In `app/preflight.py` im Wörterbuch `ANLEITUNG` ergänzen:
```python
    "logo": """\
Der Präsentations-Skill bettet das AI-SmartCon-Logo in jede Folie ein und
bricht ohne Logo bewusst ab, statt einen Ersatz zu erfinden.

Hochladen unter Einstellungen → „Haus-Logo (PNG)". Die Datei liegt danach als
config-logo.png neben der config.json und wird nicht mitversioniert.
Vorlage: logo-glow.png aus dem AI-SmartCon-Brand-Kit.""",
```

In `run_all()` vor der `return`-Zeile ergänzen:
```python
    # Haus-Logo (optional, aber Pflicht für Präsentationsläufe)
    hat_logo = config.standard_logo() is not None
    checks.append({"id": "logo", "name": "Haus-Logo (Präsentationen)",
                   "status": "ok" if hat_logo else "warn",
                   "detail": (f"hinterlegt, {len(config.standard_logo())} Bytes"
                              if hat_logo else "keins hinterlegt"),
                   "hint": "" if hat_logo else "nur für Präsentationen nötig",
                   "anleitung": ANLEITUNG["logo"]})
```
Dazu oben in `app/preflight.py` `from . import config` ergänzen, falls noch nicht vorhanden.

In `app/main.py` nach der bestehenden Config-Route:
```python
@app.post("/api/config/logo")
async def api_config_logo(logo: UploadFile = File(...)):
    """Haus-Logo hinterlegen (PNG). Ersetzt ein vorhandenes."""
    daten = await logo.read()
    if not daten:
        raise HTTPException(400, "Leere Datei")
    try:
        config.logo_speichern(daten)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "groesse": len(daten)}


@app.delete("/api/config/logo")
def api_config_logo_loeschen():
    config.logo_loeschen()
    return {"ok": True}
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_config_logo.py -v`
Expected: 6 passed.

- [ ] **Step 5: Oberfläche ergänzen**

In `static/index.html` im Einstellungsformular nach dem `default_design_md`-Label:
```html
      <label>Haus-Logo (PNG, optional)
        <input id="logo-datei" type="file" accept="image/png">
        <small>Wird in Präsentationen eingebettet. Ohne Logo bricht ein
          Präsentationslauf ab, statt einen Ersatz zu erfinden.</small>
      </label>
      <div class="zeile">
        <button type="button" id="btn-logo-upload">Logo hochladen</button>
        <button type="button" id="btn-logo-loeschen">Entfernen</button>
        <span id="logo-status" class="muted"></span>
      </div>
```

In `static/app.js` bei den Einstellungen ergänzen:
```javascript
document.getElementById('btn-logo-upload').addEventListener('click', async () => {
  const feld = document.getElementById('logo-datei');
  const status = document.getElementById('logo-status');
  if (!feld.files.length) { status.textContent = 'Keine Datei gewählt.'; return; }
  const daten = new FormData();
  daten.append('logo', feld.files[0]);
  const antwort = await fetch('/api/config/logo', { method: 'POST', body: daten });
  const ergebnis = await antwort.json();
  status.textContent = antwort.ok
    ? `Gespeichert (${ergebnis.groesse} Bytes).`
    : `Fehler: ${ergebnis.detail}`;
  ladeAmpel();
});

document.getElementById('btn-logo-loeschen').addEventListener('click', async () => {
  await fetch('/api/config/logo', { method: 'DELETE' });
  document.getElementById('logo-status').textContent = 'Entfernt.';
  ladeAmpel();
});
```

In `.gitignore` ergänzen:
```
config-logo.png
```

`?v=` in `static/index.html` um eins hochzählen.

- [ ] **Step 6: In der App prüfen**

Container neu bauen und starten (vorher: kein Agent aktiv). Dann in den Einstellungen `logo-glow.png` aus `~/.aios-assets/ai-smartcon/` hochladen und den System-Check aufrufen — die Kachel „Haus-Logo" muss grün sein. Bei 390 px und 320 px Breite gegenprüfen, dass die Knopfzeile umbricht und nichts überläuft.

- [ ] **Step 7: Commit**

```bash
git add app/config.py app/preflight.py app/main.py static/ tests/test_config_logo.py .gitignore
git commit -m "feat: Haus-Logo in den Einstellungen hinterlegen"
```

---

### Task 7: Projektart „Präsentation" im Datenmodell

**Files:**
- Modify: `app/projekte.py`
- Test: `tests/test_projekte_art.py`

**Interfaces:**
- Produces:
  - `app.projekte.PHASE_PRAESENTATION_LAEUFT = "praesentation_laeuft"`
  - `app.projekte.PHASE_PRAESENTATION_FERTIG = "praesentation_fertig"`
  - `app.projekte.ART_SCHULUNG = "schulung"`, `ART_PRAESENTATION = "praesentation"`
  - `app.projekte.art(slug: str) -> str` — liest `brief.json["art"]`, Default `ART_SCHULUNG`
  - `liste()`-Einträge enthalten zusätzlich `"art"`

- [ ] **Step 1: Den Test schreiben**

`tests/test_projekte_art.py`:
```python
"""Projektart: Schulung oder Präsentation."""

from app import projekte

SCHULUNG = {"thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
            "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos",
            "ki_medien": False}
PRAESENTATION = {**SCHULUNG, "art": projekte.ART_PRAESENTATION,
                 "quellen": "https://example.org"}


def test_ohne_feld_gilt_schulung(projekte_tmp):
    # Die fünf bestehenden Projekte haben kein art-Feld und bleiben Schulungen.
    slug = projekte.create(SCHULUNG)
    assert projekte.art(slug) == projekte.ART_SCHULUNG


def test_praesentation_wird_erkannt(projekte_tmp):
    slug = projekte.create(PRAESENTATION)
    assert projekte.art(slug) == projekte.ART_PRAESENTATION


def test_unbekanntes_projekt_gilt_als_schulung(projekte_tmp):
    assert projekte.art("gibt-es-nicht") == projekte.ART_SCHULUNG


def test_liste_nennt_die_art(projekte_tmp):
    projekte.create(SCHULUNG)
    projekte.create(PRAESENTATION)
    arten = {p["slug"]: p["art"] for p in projekte.liste()}
    assert set(arten.values()) == {projekte.ART_SCHULUNG, projekte.ART_PRAESENTATION}


def test_praesentationsphasen_existieren():
    assert projekte.PHASE_PRAESENTATION_LAEUFT == "praesentation_laeuft"
    assert projekte.PHASE_PRAESENTATION_FERTIG == "praesentation_fertig"
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_projekte_art.py -v`
Expected: FAIL mit `AttributeError: module 'app.projekte' has no attribute 'ART_PRAESENTATION'`.

- [ ] **Step 3: Implementieren**

In `app/projekte.py` bei den Phasen ergänzen:
```python
PHASE_PRAESENTATION_LAEUFT = "praesentation_laeuft"
PHASE_PRAESENTATION_FERTIG = "praesentation_fertig"

# Projektarten. Bestandsprojekte haben kein art-Feld und sind Schulungen.
ART_SCHULUNG = "schulung"
ART_PRAESENTATION = "praesentation"
```

Neue Funktion nach `get()`:
```python
def art(slug: str) -> str:
    """Projektart aus der brief.json. Fehlt sie, ist es eine Schulung."""
    p = get(slug)
    if not p:
        return ART_SCHULUNG
    return (p["briefing"].get("art") or ART_SCHULUNG)
```

In `liste()` das Eintragswörterbuch um `"art": brief.get("art") or ART_SCHULUNG` erweitern (die Funktion liest die `brief.json` bereits ein — den vorhandenen Namen der lokalen Variablen übernehmen, nicht neu einlesen).

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_projekte_art.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/projekte.py tests/test_projekte_art.py
git commit -m "feat: Projektart Praesentation im Datenmodell"
```

---

### Task 8: Der Arbeitsauftrag für den Präsentations-Agenten

**Files:**
- Create: `app/praesentation.py`, `tests/test_praesentation.py`

**Interfaces:**
- Consumes: `app.config.standard_logo()`, `app.projekte.projekt_dir()`
- Produces:
  - `app.praesentation.SKILL_NAME = "smartcon-praesentation"`
  - `app.praesentation.dateiname_aus_thema(thema: str) -> str` — ohne Endung, Präfix `AI-SmartCon_`
  - `app.praesentation.prompt(projekt_dir: Path, brief: dict, logo_pfad: Path | None) -> str`
  - `app.praesentation.dateien(projekt_dir: Path) -> list[Path]` — vorhandene `.pptx`, jüngste zuletzt

- [ ] **Step 1: Den Test schreiben**

`tests/test_praesentation.py`:
```python
"""Arbeitsauftrag an den Präsentations-Agenten."""

from pathlib import Path

from app import praesentation

BRIEF = {
    "art": "praesentation",
    "thema": "Die KI-Verordnung für KMU",
    "zielgruppe": "Geschäftsführung",
    "lernziele": "Pflichten aus Art. 4 kennen",
    "sprache": "Deutsch",
    "dauer": "45 Minuten",
    "quellen": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
}


def test_dateiname_ohne_umlaute_und_sonderzeichen():
    assert praesentation.dateiname_aus_thema("Größe & Maß") == "AI-SmartCon_Groesse-Mass"
    assert praesentation.dateiname_aus_thema("") == "AI-SmartCon_Praesentation"
    assert praesentation.dateiname_aus_thema("!!!") == "AI-SmartCon_Praesentation"


def test_dateiname_wird_gekuerzt():
    lang = praesentation.dateiname_aus_thema("Wort " * 40)
    assert len(lang) <= 72


def test_prompt_nennt_skill_arbeitsordner_und_ziel(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, tmp_path / "logo.png")
    assert praesentation.SKILL_NAME in p
    assert str(tmp_path) in p
    assert "AI-SmartCon_Die-KI-Verordnung-fuer-KMU.pptx" in p


def test_prompt_uebergibt_briefing_und_quellen(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert BRIEF["thema"] in p
    assert BRIEF["zielgruppe"] in p
    assert BRIEF["quellen"] in p


def test_prompt_ohne_quellen_fordert_eigene_recherche(tmp_path):
    p = praesentation.prompt(tmp_path, {**BRIEF, "quellen": ""}, None)
    assert "recherchiere selbst" in p.lower()


def test_prompt_nennt_hochgeladenes_material_als_primaerquelle(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "entwurf.md").write_text("x")
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert "entwurf.md" in p
    assert "Primärquelle" in p


def test_prompt_ohne_material_sagt_das(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert "keine Dateien hochgeladen" in p


def test_prompt_verlangt_belege_fuer_die_spaetere_pruefung(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    # Die Präsentation ist später Grundlage der Prüfung — Unbelegtes darf nicht rein.
    assert "notes" in p.lower()
    assert "prüfung" in p.lower()


def test_prompt_verbietet_rueckfragen(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert "AskUserQuestion" in p


def test_prompt_nennt_das_logo_wenn_vorhanden(tmp_path):
    logo = tmp_path / "logo.png"
    mit = praesentation.prompt(tmp_path, BRIEF, logo)
    ohne = praesentation.prompt(tmp_path, BRIEF, None)
    assert str(logo) in mit
    assert str(logo) not in ohne
    assert "kein Logo hinterlegt" in ohne


def test_dateien_liefert_pptx_juengste_zuletzt(tmp_path):
    import os
    import time

    alt = tmp_path / "alt.pptx"
    neu = tmp_path / "neu.pptx"
    alt.write_bytes(b"a")
    time.sleep(0.01)
    neu.write_bytes(b"b")
    os.utime(alt, (1, 1))
    assert praesentation.dateien(tmp_path) == [alt, neu]


def test_dateien_ignoriert_andere_endungen(tmp_path):
    (tmp_path / "notiz.md").write_text("x")
    assert praesentation.dateien(tmp_path) == []
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_praesentation.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.praesentation'`.

- [ ] **Step 3: Implementieren**

`app/praesentation.py`:
```python
"""Projektart „Präsentation" — Arbeitsauftrag und Fundstellen.

Eigene Datei statt Anbau an prompts.py: Die Präsentation ist eine abgeschlossene
Sache mit eigenem Skill, eigenem Ausgabeformat und ohne Preset/design.md.
"""

import re
from pathlib import Path

SKILL_NAME = "smartcon-praesentation"

_UMLAUTE = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"),
            ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"))


def dateiname_aus_thema(thema: str) -> str:
    """Dateiname ohne Endung. Er landet in einem Download-Header, deshalb ASCII."""
    text = str(thema).strip()
    for zeichen, ersatz in _UMLAUTE:
        text = text.replace(zeichen, ersatz)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return f"AI-SmartCon_{text[:60]}" if text else "AI-SmartCon_Praesentation"


def dateien(projekt_dir: Path) -> list[Path]:
    """Erzeugte PowerPoint-Dateien, jüngste zuletzt."""
    return sorted(projekt_dir.glob("*.pptx"), key=lambda p: p.stat().st_mtime)


def prompt(projekt_dir: Path, brief: dict, logo_pfad: Path | None) -> str:
    """Arbeitsauftrag: eine PPTX im AI-SmartCon-CI aus Thema und Quellen."""
    material = projekt_dir / "material"
    namen = sorted(p.name for p in material.iterdir()) if material.is_dir() else []
    if namen:
        material_block = (
            "Im Ordner `material/` liegen hochgeladene Unterlagen. **Sichte sie "
            "zuerst und behandle sie als Primärquelle** — sie gehen der "
            "Websuche vor:\n"
            + "\n".join(f"- {material / name}" for name in namen))
    else:
        material_block = "Es wurden keine Dateien hochgeladen."

    quellen = str(brief.get("quellen", "")).strip()
    quellen_block = (
        f"Zusätzlich hat der Nutzer diese Quellen genannt — arbeite sie ab:\n{quellen}"
        if quellen else
        "Es wurden keine einzelnen Quellen genannt; recherchiere selbst.")

    zeilen = [f"- {feld}: {brief.get(feld)}" for feld in
              ("thema", "zielgruppe", "vorwissen", "sprache", "dauer")
              if str(brief.get(feld, "")).strip()]
    if str(brief.get("lernziele", "")).strip():
        zeilen.append(f"- Lernziele/Inhalte: {brief['lernziele']}")
    briefing_block = "\n".join(zeilen)

    if logo_pfad is not None:
        logo_block = (
            f"- Das Haus-Logo liegt unter {logo_pfad} — verwende genau diese "
            "Datei für Titelfolie und Folgefolien. Nicht einfärben, nicht "
            "verzerren, keinen Ersatz erfinden.")
    else:
        logo_block = (
            "- Es ist **kein Logo hinterlegt**. Brich ab und melde das, statt "
            "ein Ersatz-Logo zu bauen — das Logo wird in den Einstellungen "
            "der App hochgeladen.")

    ziel = projekt_dir / f"{dateiname_aus_thema(brief.get('thema', ''))}.pptx"

    return f"""Du bist der Präsentations-Agent der App „SmartCon-Kurse". Dein
Arbeitsverzeichnis ist der Projektordner: {projekt_dir}

## Auftrag

Erstelle eine vollständige PowerPoint-Präsentation im AI-SmartCon-CI.

**Nutze dazu den Skill `{SKILL_NAME}`** und halte dich an seine
Pflicht-Reihenfolge: Recherche → Storyline → Bau → QA. Findest du den Skill
nicht, brich ab und melde das — baue keine eigene Vorlage.

## Briefing

{briefing_block}

## Vorhandenes Material

{material_block}

{quellen_block}

## Vorgaben für diesen Lauf

- Schreibe die fertige Datei nach: {ziel}
{logo_block}
- **Jede Zahl, Norm, Frist und jeden Eigennamen belegen.** Die Quelle gehört
  in die Notizen (`notes`) der jeweiligen Folie. Diese Präsentation ist
  später die Grundlage einer Prüfung — was nicht belegt ist, gehört nicht
  hinein.
- Setze das Stand-Datum sichtbar auf die Titelfolie.
- Kein Text in erzeugten Bildern.
- Stelle keine Rückfragen (kein AskUserQuestion). Wo etwas fehlt, triff eine
  sinnvolle Annahme und halte sie auf der letzten Folie unter „Annahmen" fest.

## Abschluss

Beende den Lauf mit einer Zeile: Dateiname und Anzahl der Folien."""
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_praesentation.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add app/praesentation.py tests/test_praesentation.py
git commit -m "feat: Arbeitsauftrag fuer den Praesentations-Agenten"
```

---

### Task 9: Routen für Präsentationsläufe

**Files:**
- Modify: `app/main.py`, `app/runner.py`
- Test: `tests/test_api_praesentation.py`

**Interfaces:**
- Consumes: `app.praesentation.prompt()`, `dateien()`, `app.config.standard_logo()`
- Produces:
  - `POST /api/praesentationen` (Form: `thema` Pflicht, `zielgruppe`, `lernziele`, `vorwissen`, `sprache`, `dauer`, `quellen`; Files: `material`) → `{"ok": True, "slug": ..., "phase": ...}`
  - `GET /api/praesentationen/{slug}` → `{"slug", "phase", "laeuft", "thema", "dateien": [{"name", "groesse"}], "fertig"}`
  - `GET /api/praesentationen/{slug}/datei/{dateiname}` → FileResponse, nur `.pptx`
  - `runner.PHASE_NACH_ERFOLG["praesentation"] = PHASE_PRAESENTATION_FERTIG`

- [ ] **Step 1: Den Test schreiben**

`tests/test_api_praesentation.py`:
```python
"""Endpunkte der Deck-Werkstatt."""

import pytest

from app import config, projekte

FORM = {"thema": "Die KI-Verordnung für KMU",
        "zielgruppe": "Geschäftsführung",
        "quellen": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def mit_logo(tmp_path, monkeypatch):
    logo = tmp_path / "config-logo.png"
    logo.write_bytes(PNG)
    monkeypatch.setattr(config, "LOGO_PFAD", logo)
    return logo


def test_anlegen_startet_lauf_und_setzt_phase(client, mit_logo):
    antwort = client.post("/api/praesentationen", data=FORM)
    assert antwort.status_code == 201
    slug = antwort.json()["slug"]
    assert antwort.json()["phase"] == projekte.PHASE_PRAESENTATION_LAEUFT
    assert projekte.art(slug) == projekte.ART_PRAESENTATION
    assert client.gestartet, "runner.start wurde nicht aufgerufen"


def test_thema_ist_pflicht(client, mit_logo):
    assert client.post("/api/praesentationen", data={"thema": "  "}).status_code == 400


def test_ohne_logo_ist_es_400_statt_eines_vergeblichen_laufs(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGO_PFAD", tmp_path / "fehlt.png")
    antwort = client.post("/api/praesentationen", data=FORM)
    assert antwort.status_code == 400
    assert "logo" in antwort.json()["detail"].lower()
    assert not client.gestartet


def test_zu_lange_quellenliste_wird_abgewiesen(client, mit_logo):
    antwort = client.post("/api/praesentationen",
                          data={**FORM, "quellen": "x" * 20001})
    assert antwort.status_code == 400


def test_stand_meldet_erzeugte_dateien(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "AI-SmartCon_Test.pptx").write_bytes(b"x" * 10)

    stand = client.get(f"/api/praesentationen/{slug}").json()
    assert stand["dateien"] == [{"name": "AI-SmartCon_Test.pptx", "groesse": 10}]
    assert stand["fertig"] is True


def test_stand_unbekannt_ist_404(client):
    assert client.get("/api/praesentationen/gibt-es-nicht").status_code == 404


def test_download_liefert_die_datei(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "AI-SmartCon_Test.pptx").write_bytes(b"inhalt")

    antwort = client.get(f"/api/praesentationen/{slug}/datei/AI-SmartCon_Test.pptx")
    assert antwort.status_code == 200
    assert antwort.content == b"inhalt"


def test_download_nur_pptx(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "geheim.json").write_text("{}")
    assert client.get(f"/api/praesentationen/{slug}/datei/geheim.json").status_code == 400


def test_download_kein_pfadausbruch(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    antwort = client.get(f"/api/praesentationen/{slug}/datei/..%2F..%2Fconfig.json")
    assert antwort.status_code in (400, 404)
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_api_praesentation.py -v`
Expected: FAIL, alle Routen liefern 404.

- [ ] **Step 3: Implementieren**

In `app/runner.py` das Wörterbuch `PHASE_NACH_ERFOLG` um den Eintrag erweitern:
```python
    "praesentation": projekte.PHASE_PRAESENTATION_FERTIG,
```

In `app/main.py` ergänzen (Importe `praesentation` und, falls nicht vorhanden, `re`):
```python
PRAESENTATION_QUELLEN_MAX = 20000
_DATEINAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@app.post("/api/praesentationen", status_code=201)
async def api_praesentation_neu(
    thema: str = Form(...),
    zielgruppe: str = Form(""),
    lernziele: str = Form(""),
    vorwissen: str = Form(""),
    sprache: str = Form("Deutsch"),
    dauer: str = Form(""),
    quellen: str = Form(""),
    material: list[UploadFile] = File([]),
):
    """Legt ein Präsentationsprojekt an und startet den Lauf.

    `quellen` ist Freitext, eine Fundstelle je Zeile. Dateien kommen über
    `material` und gehen der Websuche vor.
    """
    if not thema.strip():
        raise HTTPException(400, "Thema ist ein Pflichtfeld")
    if len(quellen) > PRAESENTATION_QUELLEN_MAX:
        raise HTTPException(400, "Die Quellenliste ist zu lang")
    if config.standard_logo() is None:
        # Lieber hier abweisen als einen Lauf starten, der am Logo scheitert.
        raise HTTPException(
            400, "Kein Haus-Logo hinterlegt — in den Einstellungen hochladen. "
                 "Der Präsentations-Skill bricht ohne Logo ab.")

    dateien = [(f.filename, await f.read()) for f in material if f.filename]
    briefing = {
        "art": projekte.ART_PRAESENTATION,
        "thema": thema.strip(),
        "zielgruppe": zielgruppe.strip(),
        "lernziele": lernziele.strip(),
        "vorwissen": vorwissen.strip(),
        "sprache": sprache.strip() or "Deutsch",
        "dauer": dauer.strip(),
        "quellen": quellen.strip(),
    }
    slug = projekte.create(briefing, material=dateien)
    d = projekte.projekt_dir(slug)

    projekte.set_phase(slug, projekte.PHASE_PRAESENTATION_LAEUFT)
    try:
        runner.start(slug, "praesentation",
                     praesentation.prompt(d, briefing, config.LOGO_PFAD))
    except runner.LaufAktiv:
        projekte.set_phase(slug, projekte.PHASE_FEHLER)
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "slug": slug,
            "phase": projekte.PHASE_PRAESENTATION_LAEUFT}


@app.get("/api/praesentationen/{slug}")
def api_praesentation_stand(slug: str):
    p = _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    dateien = [{"name": f.name, "groesse": f.stat().st_size}
               for f in praesentation.dateien(d)]
    return {"slug": slug,
            "phase": p["status"].get("phase"),
            "laeuft": runner.laeuft(slug),
            "thema": p["briefing"].get("thema"),
            "dateien": dateien,
            "fertig": bool(dateien) and not runner.laeuft(slug)}


@app.get("/api/praesentationen/{slug}/datei/{dateiname}")
def api_praesentation_download(slug: str, dateiname: str):
    """Download der erzeugten PowerPoint-Datei.

    Eigene Route statt einer Erweiterung von /ergebnis: Dort ist die
    Beschränkung auf .html Teil der Prüfung, und eine Route, die je nach
    Endung anderes zulässt, lädt zum nächsten Schlupfloch ein.
    """
    _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    if not _DATEINAME_RE.match(dateiname) or not dateiname.endswith(".pptx"):
        raise HTTPException(400, "Ungültiger Dateiname")
    f = d / dateiname
    if not f.is_file() or f.resolve().parent != d.resolve():
        raise HTTPException(404, f"Datei „{dateiname}“ nicht gefunden")
    return FileResponse(
        f, filename=f.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_api_praesentation.py -v`
Expected: 9 passed.

- [ ] **Step 5: Volle Suite und Commit**

Run: `.venv/bin/python -m pytest -q`
Expected: alles grün.

```bash
git add app/main.py app/runner.py tests/test_api_praesentation.py
git commit -m "feat: Routen fuer Praesentationslaeufe"
```

---

### Task 10: Reiter „Präsentationen" in der Oberfläche

**Files:**
- Modify: `static/index.html`, `static/app.js`, `static/style.css`

**Interfaces:**
- Consumes: die drei Routen aus Task 9, `GET /api/projekte/{slug}/events` (SSE, existiert)
- Produces: nichts für andere Tasks

- [ ] **Step 1: Reiter und Ansicht anlegen**

In `static/index.html` in die Reiterleiste, nach `tab-projekte`:
```html
    <button id="tab-decks" class="tab" data-tab="decks">Präsentationen</button>
```

Neue Ansicht nach `#view-projekte`:
```html
  <section id="view-decks" class="view">
    <div id="dv-liste">
      <div class="zeile">
        <h2>Präsentationen</h2>
        <button id="btn-deck-neu">Neue Präsentation</button>
      </div>
      <p class="muted">Thema und Quellen rein, PowerPoint im AI-SmartCon-CI
        raus. Kostet keine Higgsfield-Credits.</p>
      <div id="deck-liste"></div>
    </div>

    <div id="dv-formular" hidden>
      <div class="zeile">
        <h2>Neue Präsentation</h2>
        <button id="btn-deck-form-zurueck">Zurück</button>
      </div>
      <form id="deck-form">
        <label>Thema <input name="thema" required></label>
        <label>Zielgruppe <input name="zielgruppe"></label>
        <label>Inhalte / Lernziele <textarea name="lernziele" rows="3"></textarea></label>
        <label>Vorwissen <input name="vorwissen"></label>
        <label>Sprache <input name="sprache" value="Deutsch"></label>
        <label>Dauer <input name="dauer" placeholder="45 Minuten"></label>
        <label>Quellen (eine je Zeile)
          <textarea name="quellen" rows="4"
            placeholder="https://eur-lex.europa.eu/…"></textarea></label>
        <label>Material (optional, geht der Websuche vor)
          <input name="material" type="file" multiple></label>
        <div class="zeile">
          <button type="submit">Präsentation erzeugen</button>
          <span id="deck-form-status" class="muted"></span>
        </div>
      </form>
    </div>

    <div id="dv-detail" hidden>
      <div class="zeile">
        <h2 id="deck-titel">Präsentation</h2>
        <button id="btn-deck-zurueck">Zurück zur Liste</button>
      </div>
      <div class="zeile">
        <span id="deck-badge" class="badge"></span>
      </div>
      <div id="deck-log" class="log"><p class="muted">Noch kein Lauf gestartet.</p></div>
      <div id="deck-dateien"></div>
    </div>
  </section>
```

`?v=` hochzählen.

- [ ] **Step 2: Logik ergänzen**

An `static/app.js` anhängen:
```javascript
/* ---------- Präsentationen ---------- */

const DECK_PHASEN_LABEL = {
  praesentation_laeuft: 'Präsentation läuft',
  praesentation_fertig: 'fertig',
  fehler: 'Fehler',
};
let deckSlug = null;
let deckQuelle = null;
let deckTimer = null;

function deckPanel(id) {
  ['dv-liste', 'dv-formular', 'dv-detail'].forEach((p) => {
    document.getElementById(p).hidden = p !== id;
  });
}

async function ladeDecks() {
  const antwort = await fetch('/api/projekte');
  const alle = await antwort.json();
  const decks = alle.filter((p) => p.art === 'praesentation');
  const ziel = document.getElementById('deck-liste');
  if (!decks.length) {
    ziel.innerHTML = '<p class="muted">Noch keine Präsentation erzeugt.</p>';
    return;
  }
  ziel.innerHTML = decks.map((p) => `
    <button class="karte" data-slug="${esc(p.slug)}">
      <strong>${esc(p.thema || p.slug)}</strong>
      <span class="badge">${esc(DECK_PHASEN_LABEL[p.phase] || p.phase)}</span>
    </button>`).join('');
  ziel.querySelectorAll('[data-slug]').forEach((el) => {
    el.addEventListener('click', () => oeffneDeck(el.dataset.slug));
  });
}

async function oeffneDeck(slug) {
  deckSlug = slug;
  deckPanel('dv-detail');
  document.getElementById('deck-log').innerHTML = '';
  await aktualisiereDeck();
  deckSseVerbinden(slug);
}

async function aktualisiereDeck() {
  const antwort = await fetch(`/api/praesentationen/${deckSlug}`);
  if (!antwort.ok) return;
  const stand = await antwort.json();
  document.getElementById('deck-titel').textContent = stand.thema || deckSlug;
  document.getElementById('deck-badge').textContent =
    DECK_PHASEN_LABEL[stand.phase] || stand.phase;

  const ziel = document.getElementById('deck-dateien');
  ziel.innerHTML = stand.dateien.length
    ? `<h3>Ergebnis</h3>` + stand.dateien.map((d) => `
        <a class="download" href="/api/praesentationen/${encodeURIComponent(deckSlug)}/datei/${encodeURIComponent(d.name)}">
          ${esc(d.name)} <span class="muted">${fmtGroesse(d.groesse)}</span></a>`).join('')
    : '';

  if (stand.laeuft) {
    if (!deckTimer) deckTimer = setInterval(aktualisiereDeck, 5000);
  } else if (deckTimer) {
    clearInterval(deckTimer);
    deckTimer = null;
  }
}

function deckSseVerbinden(slug) {
  if (deckQuelle) deckQuelle.close();
  deckQuelle = new EventSource(`/api/projekte/${encodeURIComponent(slug)}/events`);
  const log = document.getElementById('deck-log');
  deckQuelle.onmessage = (e) => {
    const ereignis = JSON.parse(e.data);
    const zeile = document.createElement('p');
    zeile.textContent = ereignis.text || `${ereignis.typ}: ${ereignis.tool || ''}`;
    log.appendChild(zeile);
    log.scrollTop = log.scrollHeight;
    if (ereignis.typ === 'fertig') aktualisiereDeck();
  };
}

document.getElementById('btn-deck-neu').addEventListener('click', () => deckPanel('dv-formular'));
document.getElementById('btn-deck-form-zurueck').addEventListener('click', () => deckPanel('dv-liste'));
document.getElementById('btn-deck-zurueck').addEventListener('click', () => {
  if (deckQuelle) deckQuelle.close();
  if (deckTimer) { clearInterval(deckTimer); deckTimer = null; }
  deckPanel('dv-liste');
  ladeDecks();
});

document.getElementById('deck-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const status = document.getElementById('deck-form-status');
  status.textContent = 'Wird angelegt …';
  const antwort = await fetch('/api/praesentationen',
    { method: 'POST', body: new FormData(e.target) });
  const ergebnis = await antwort.json();
  if (!antwort.ok) { status.textContent = `Fehler: ${ergebnis.detail}`; return; }
  status.textContent = '';
  e.target.reset();
  oeffneDeck(ergebnis.slug);
});
```

Im vorhandenen Reiter-Umschalter dafür sorgen, dass beim Wechsel auf `decks` `ladeDecks()` aufgerufen und `deckPanel('dv-liste')` gesetzt wird.

- [ ] **Step 3: Stil ergänzen**

In `static/style.css`:
```css
.karte {
  display: block;
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  margin-bottom: 8px;
}
.karte[hidden] { display: none; }

.download {
  display: inline-block;
  margin-right: 12px;
  margin-bottom: 6px;
  word-break: break-all;
}
.download[hidden] { display: none; }
```

Zu jeder Regel mit eigenem `display` gehört die `[hidden]`-Variante — sonst schlägt das Autor-Stylesheet das Attribut.

- [ ] **Step 4: Syntax prüfen**

Run: `node --check static/app.js`
Expected: keine Ausgabe.

- [ ] **Step 5: In der App prüfen**

Container bauen (kein Agent aktiv!), Reiter „Präsentationen" öffnen, eine Präsentation zu einem kleinen Thema anlegen und den Lauf beobachten. Erfolgskriterium: Die `.pptx` erscheint, lässt sich herunterladen und in PowerPoint öffnen, zeigt Navy/Gold und das Logo. Breite bei 390 px und 320 px gegenprüfen.

- [ ] **Step 6: Commit**

```bash
git add static/
git commit -m "feat: Reiter Praesentationen in der Oberflaeche"
```

---

# Etappe 2 — Prüfung aus dem ausgelieferten Stoff

Ziel: `pruefung.json` und eine offline lauffähige Prüfungs-HTML, erzeugt aus dem, was die Teilnehmer bekommen haben. Erfolgskriterium: Für eine bestehende Schulung entsteht eine Prüfung, deren Fragen sich alle aus der Stoffquelle beantworten lassen.

### Task 11: Die Stoffquelle

**Files:**
- Modify: `app/prompts.py`
- Test: `tests/test_stoffquelle.py`

**Interfaces:**
- Produces: `app.prompts.stoffquelle(projekt_dir: Path) -> Path | None`

- [ ] **Step 1: Den Test schreiben**

`tests/test_stoffquelle.py`:
```python
"""Die Grundlage der Prüfung: was ausgeliefert wurde, nicht was geplant war."""

import os

from app.prompts import stoffquelle

FOLIEN = (".pptx", ".pdf", ".key", ".odp")


def test_ohne_alles_ist_es_none(tmp_path):
    assert stoffquelle(tmp_path) is None


def test_curriculum_allein_zaehlt_nicht(tmp_path):
    # Das Curriculum ist der Plan. Zwischen Plan und Auslieferung liegt die
    # Produktion, die kürzt und gewichtet.
    (tmp_path / "curriculum.md").write_text("# Plan")
    assert stoffquelle(tmp_path) is None


def test_erzeugte_html_wird_genommen(tmp_path):
    seite = tmp_path / "schulung.html"
    seite.write_text("<html></html>")
    assert stoffquelle(tmp_path) == seite


def test_juengste_html_gewinnt(tmp_path):
    alt = tmp_path / "alt.html"
    neu = tmp_path / "neu.html"
    alt.write_text("a")
    neu.write_text("b")
    os.utime(alt, (1, 1))
    assert stoffquelle(tmp_path) == neu


def test_hochgeladene_folien_schlagen_die_html(tmp_path):
    # Bei einer Live-Schulung ist der Foliensatz der behandelte Stoff,
    # nicht die Nacharbeit im Portal.
    (tmp_path / "schulung.html").write_text("<html></html>")
    material = tmp_path / "material"
    material.mkdir()
    deck = material / "deck.pptx"
    deck.write_bytes(b"x")
    assert stoffquelle(tmp_path) == deck


def test_alle_folienformate_zaehlen(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    for endung in FOLIEN:
        datei = material / f"deck{endung}"
        datei.write_bytes(b"x")
        assert stoffquelle(tmp_path) == datei
        datei.unlink()


def test_material_ohne_folien_zaehlt_nicht(tmp_path):
    seite = tmp_path / "schulung.html"
    seite.write_text("<html></html>")
    material = tmp_path / "material"
    material.mkdir()
    (material / "notiz.md").write_text("x")
    assert stoffquelle(tmp_path) == seite
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_stoffquelle.py -v`
Expected: FAIL mit `ImportError: cannot import name 'stoffquelle'`.

- [ ] **Step 3: Implementieren**

In `app/prompts.py` ergänzen:
```python
# Formate, die einen Foliensatz tragen können.
_FOLIEN_ENDUNGEN = (".pptx", ".pdf", ".key", ".odp")


def stoffquelle(projekt_dir: Path) -> Path | None:
    """Die Datei, die den tatsächlich behandelten Stoff trägt.

    Das ist NICHT das curriculum.md: Das ist der Plan, und zwischen Plan und
    Auslieferung liegt die Produktion, die kürzt und gewichtet. Geprüft werden
    darf nur, was die Teilnehmer auch bekommen haben.

    Vorrang hat eine hochgeladene Präsentation im material/-Ordner — bei einer
    Live-Schulung ist der Foliensatz der behandelte Stoff, nicht die Nacharbeit.
    Fehlt sie, gilt die erzeugte Lerneinheit. Ohne beides: None; der Aufrufer
    fällt dann sichtbar auf das Curriculum zurück.
    """
    material = projekt_dir / "material"
    if material.is_dir():
        folien = sorted(
            (p for p in material.iterdir()
             if p.suffix.lower() in _FOLIEN_ENDUNGEN),
            key=lambda p: p.stat().st_mtime)
        if folien:
            return folien[-1]

    # Jüngste statt alphabetisch erste: Im Projektordner liegen während des
    # Laufs regelmäßig Zwischendateien.
    seiten = sorted(projekt_dir.glob("*.html"), key=lambda p: p.stat().st_mtime)
    return seiten[-1] if seiten else None
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_stoffquelle.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add app/prompts.py tests/test_stoffquelle.py
git commit -m "feat: stoffquelle - geprueft wird der ausgelieferte Stoff"
```

---

### Task 12: Schema und Validierung von `pruefung.json`

**Files:**
- Create: `app/pruefung.py`, `tests/test_pruefung_schema.py`

**Interfaces:**
- Produces:
  - `app.pruefung.PruefungFehler(ValueError)`
  - `app.pruefung.laden(pfad: Path) -> dict` — validiert, wirft `PruefungFehler`
  - `app.pruefung.pruefe(daten: dict) -> None`

- [ ] **Step 1: Den Test schreiben**

`tests/test_pruefung_schema.py`:
```python
"""pruefung.json — was der Agent liefert, wird geprüft, bevor es zählt."""

import json

import pytest

from app import pruefung

GUELTIG = {
    "titel": "Abschlussprüfung KI-Verordnung",
    "bestehensgrenze": 70,
    "fragen": [
        {"frage": "Seit wann wird Art. 4 KI-VO durchgesetzt?",
         "optionen": ["seit 02.08.2026", "seit 2027", "gar nicht"],
         "richtig": 0,
         "thema": "Level 1",
         "hinweis": "Die nationale Marktüberwachung läuft seit dem 02.08.2026."},
    ],
}


def test_gueltige_datei_wird_geladen(tmp_path):
    pfad = tmp_path / "pruefung.json"
    pfad.write_text(json.dumps(GUELTIG), encoding="utf-8")
    assert pruefung.laden(pfad)["titel"] == GUELTIG["titel"]


def test_kaputtes_json_wird_gemeldet(tmp_path):
    pfad = tmp_path / "pruefung.json"
    pfad.write_text("{ das ist kein json")
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.laden(pfad)


def test_code_zaeune_werden_abgewiesen(tmp_path):
    # Häufigster Agentenfehler: JSON in ```json ... ``` verpackt.
    pfad = tmp_path / "pruefung.json"
    pfad.write_text("```json\n" + json.dumps(GUELTIG) + "\n```")
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.laden(pfad)


def test_ohne_fragen_ungueltig():
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": []})


def test_richtig_muss_auf_eine_option_zeigen():
    frage = {**GUELTIG["fragen"][0], "richtig": 5}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})

    frage = {**GUELTIG["fragen"][0], "richtig": -1}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_zu_wenige_optionen_ungueltig():
    frage = {**GUELTIG["fragen"][0], "optionen": ["nur eine"], "richtig": 0}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_zu_viele_optionen_ungueltig():
    frage = {**GUELTIG["fragen"][0], "optionen": list("abcdef"), "richtig": 0}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_leere_frage_ungueltig():
    frage = {**GUELTIG["fragen"][0], "frage": "  "}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


@pytest.mark.parametrize("grenze", [0, 101, "siebzig", None])
def test_unsinnige_bestehensgrenze_ungueltig(grenze):
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "bestehensgrenze": grenze})


def test_fehlermeldung_nennt_die_fragennummer():
    frage = {**GUELTIG["fragen"][0], "richtig": 9}
    with pytest.raises(pruefung.PruefungFehler, match="Frage 1"):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_pruefung_schema.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.pruefung'`.

- [ ] **Step 3: Implementieren**

`app/pruefung.py` (erster Teil — der Renderer kommt in Task 14):
```python
"""Abschlussprüfung: Schema-Validierung und HTML-Ausgabe.

Der Agent liefert pruefung.json. Diese Datei prüft, was ankam, bevor daraus
ein Nachweis wird — ein Zeiger auf eine nicht vorhandene Option macht eine
Frage unlösbar, und das fällt sonst erst dem Teilnehmer auf.
"""

import json
from pathlib import Path

MIN_OPTIONEN = 3
MAX_OPTIONEN = 5


class PruefungFehler(ValueError):
    """Die Datei ist nicht verwendbar. Die Meldung nennt die Fundstelle."""


def laden(pfad: Path) -> dict:
    """Liest und validiert pruefung.json."""
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError as e:
        raise PruefungFehler(f"{pfad.name} nicht lesbar: {e}") from e
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as e:
        raise PruefungFehler(
            f"{pfad.name} ist kein gültiges JSON ({e.msg}, Zeile {e.lineno}). "
            "Häufigste Ursache: Der Agent hat Code-Zäune (```json) mitgeschrieben."
        ) from e
    pruefe(daten)
    return daten


def pruefe(daten: dict) -> None:
    """Wirft PruefungFehler, wenn die Struktur unbrauchbar ist."""
    if not isinstance(daten, dict):
        raise PruefungFehler("Die Datei muss ein JSON-Objekt enthalten")
    if not str(daten.get("titel", "")).strip():
        raise PruefungFehler("„titel" fehlt oder ist leer")

    grenze = daten.get("bestehensgrenze")
    if not isinstance(grenze, int) or isinstance(grenze, bool) \
            or not 1 <= grenze <= 100:
        raise PruefungFehler(
            "„bestehensgrenze" muss eine ganze Zahl zwischen 1 und 100 sein")

    fragen = daten.get("fragen")
    if not isinstance(fragen, list) or not fragen:
        raise PruefungFehler("„fragen" fehlt oder ist leer")

    for nr, frage in enumerate(fragen, start=1):
        _pruefe_frage(nr, frage)


def _pruefe_frage(nr: int, frage) -> None:
    if not isinstance(frage, dict):
        raise PruefungFehler(f"Frage {nr}: kein Objekt")
    if not str(frage.get("frage", "")).strip():
        raise PruefungFehler(f"Frage {nr}: Fragetext fehlt")

    optionen = frage.get("optionen")
    if not isinstance(optionen, list) or not MIN_OPTIONEN <= len(optionen) <= MAX_OPTIONEN:
        raise PruefungFehler(
            f"Frage {nr}: „optionen" braucht {MIN_OPTIONEN} bis {MAX_OPTIONEN} Einträge")
    if any(not str(o).strip() for o in optionen):
        raise PruefungFehler(f"Frage {nr}: leere Antwortoption")

    richtig = frage.get("richtig")
    if not isinstance(richtig, int) or isinstance(richtig, bool) \
            or not 0 <= richtig < len(optionen):
        raise PruefungFehler(
            f"Frage {nr}: „richtig" muss auf eine vorhandene Option zeigen "
            f"(0 bis {len(optionen) - 1})")
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_pruefung_schema.py -v`
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add app/pruefung.py tests/test_pruefung_schema.py
git commit -m "feat: Schema-Validierung fuer pruefung.json"
```

---

### Task 13: Arbeitsauftrag und Route für die Prüfung

**Files:**
- Modify: `app/prompts.py`, `app/projekte.py`, `app/runner.py`, `app/main.py`
- Test: `tests/test_pruefung_prompt.py`, `tests/test_api_pruefung.py`

**Interfaces:**
- Produces:
  - `app.projekte.PHASE_PRUEFUNG_LAEUFT = "pruefung_laeuft"`
  - `app.prompts.pruefung_prompt(projekt_dir: Path, bestehensgrenze: int = 70) -> str`
  - `POST /api/projekte/{slug}/pruefung` (JSON-Body optional: `{"bestehensgrenze": int}`)
  - `GET /api/projekte/{slug}/pruefung` → validierte Prüfung oder 404/400
  - `runner.PHASE_NACH_ERFOLG["pruefung"] = PHASE_FERTIG`

- [ ] **Step 1: Prompt-Test schreiben**

`tests/test_pruefung_prompt.py`:
```python
"""Der Arbeitsauftrag entscheidet, ob die Prüfung fair ist."""

from app.prompts import pruefung_prompt


def test_prompt_nennt_stoffquelle_und_zielpfad(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")
    (tmp_path / "curriculum.md").write_text("# Plan")

    p = pruefung_prompt(tmp_path)
    assert "deck.pptx" in p
    assert str(tmp_path / "pruefung.json") in p


def test_prompt_verbietet_fragen_ausserhalb_der_stoffquelle(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")

    p = pruefung_prompt(tmp_path)
    assert "verwirf die Frage" in p
    assert "Kein Vorwissen" in p


def test_curriculum_dient_nur_der_gliederung(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")
    (tmp_path / "curriculum.md").write_text("# Plan")

    p = pruefung_prompt(tmp_path)
    assert "nur, um die Gliederung zu kennen" in p


def test_ohne_stoffquelle_wird_der_mangel_benannt(tmp_path):
    (tmp_path / "curriculum.md").write_text("# Plan")
    p = pruefung_prompt(tmp_path)
    assert "ACHTUNG" in p
    assert "Lernplan" in p


def test_bestehensgrenze_steht_im_prompt(tmp_path):
    (tmp_path / "curriculum.md").write_text("# Plan")
    assert "80" in pruefung_prompt(tmp_path, bestehensgrenze=80)


def test_prompt_verlangt_nur_json(tmp_path):
    (tmp_path / "curriculum.md").write_text("# Plan")
    p = pruefung_prompt(tmp_path)
    assert "keine Code-Zäune" in p
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_pruefung_prompt.py -v`
Expected: FAIL mit `ImportError: cannot import name 'pruefung_prompt'`.

- [ ] **Step 3: Prompt implementieren**

In `app/prompts.py` ergänzen:
```python
def pruefung_prompt(projekt_dir: Path, bestehensgrenze: int = 70) -> str:
    """Arbeitsauftrag: pruefung.json aus dem ausgelieferten Stoff.

    Schema als Literal, absoluter Zielpfad, „nur JSON" — dieselbe Bauart wie
    kostenplan_prompt. Eine erzwungene Datei ist nötig, weil der Abschluss-Check
    im curriculum.md in wechselnden Notationen steht.
    """
    quelle = stoffquelle(projekt_dir)
    schema = f"""
{{
  "titel": "Abschlussprüfung <Thema>",
  "bestehensgrenze": {bestehensgrenze},
  "fragen": [
    {{"frage": "vollständig ausformulierte Frage auf Deutsch",
     "optionen": ["Antwort A", "Antwort B", "Antwort C", "Antwort D"],
     "richtig": 0,
     "thema": "Level 3",
     "hinweis": "Ein Satz, warum das die richtige Antwort ist."}}
  ]
}}
"""
    if quelle is not None:
        grundlage = f"""Lies zuerst {quelle} vollständig. **Das ist der Stoff,
der behandelt wurde, und die alleinige Grundlage der Prüfung.**

Lies danach {projekt_dir / 'curriculum.md'} — aber nur, um die Gliederung zu
kennen und jede Frage einem Level zuzuordnen. Inhalte, die dort stehen und in
{quelle.name} fehlen, sind NICHT Stoff und dürfen nicht gefragt werden."""
        stoff_regeln = f"""- **Jede Frage muss sich aus {quelle.name} allein beantworten lassen.**
  Prüfe das für jede einzelne Frage, bevor du sie aufnimmst: Steht die
  richtige Antwort dort? Wenn nein, verwirf die Frage. Kein Vorwissen, keine
  Ergänzung aus eigener Kenntnis, nichts aus der Recherche — auch dann nicht,
  wenn es fachlich richtig wäre.
- Was mündlich ergänzt wurde, steht dir nicht zur Verfügung und ist kein Stoff.
- Lieber weniger Fragen als eine, die im Material nicht gedeckt ist.
- 10 bis 15 Fragen, verteilt über die Level, die in {quelle.name} tatsächlich
  vorkommen — ein dort nicht behandeltes Level bleibt ohne Frage."""
    else:
        grundlage = f"""Lies {projekt_dir / 'curriculum.md'} vollständig — alle
Level mit ihren Lernzielen und Merksätzen.

ACHTUNG: Es liegt weder eine hochgeladene Präsentation noch eine erzeugte
Lerneinheit vor. Du arbeitest deshalb auf dem Lernplan statt auf dem
ausgelieferten Material. Halte dich streng an das, was im Plan steht."""
        stoff_regeln = """- 10 bis 15 Fragen, über alle Level verteilt. Kein Level ohne Frage.
- Frage nur ab, was im Curriculum ausformuliert ist — nichts aus eigener
  Kenntnis ergänzen."""

    return f"""Du bist der Prüfungs-Agent der App „SmartCon-Kurse". Dein
Arbeitsverzeichnis ist der Projektordner: {projekt_dir}

{grundlage}

Erstelle daraus die Abschlussprüfung und schreibe sie als maschinenlesbare
JSON-Datei {projekt_dir / 'pruefung.json'} — exakt in diesem Schema:
{schema}
Regeln:
{stoff_regeln}
- „optionen" hat drei bis fünf Einträge. „richtig" ist der nullbasierte Zeiger
  auf die richtige Option — genau eine Antwort ist richtig, Mehrfachauswahl
  gibt es nicht.
- Die Ablenker müssen plausibel sein: falsche Antworten, die jemand ohne die
  Schulung für richtig halten könnte. Keine absurden Optionen und keine, die
  sich schon durch ihre Länge verraten.
- „thema" nennt das Level, auf das sich die Frage bezieht („Level 3").
- „hinweis" ist ein Satz Begründung, der nach der Auswertung gezeigt wird.
- „bestehensgrenze" ist {bestehensgrenze}.
- Frage nach Verständnis, nicht nach Wortlaut.
- Alles auf Deutsch, mit korrekten Umlauten.
- Die Datei enthält NUR das JSON: kein Kommentar, kein Markdown, keine
  Code-Zäune.

Stelle keine Rückfragen. Beende den Lauf mit einer Zeile: Anzahl der Fragen
und die abgedeckten Level."""
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_pruefung_prompt.py -v`
Expected: 6 passed.

- [ ] **Step 5: Routen-Test schreiben**

`tests/test_api_pruefung.py`:
```python
"""Endpunkte der Prüfungsphase."""

import json

from app import projekte

FORM = {"thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
        "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos"}

GUELTIG = {
    "titel": "Abschlussprüfung CRA",
    "bestehensgrenze": 70,
    "fragen": [{"frage": "Frage?", "optionen": ["a", "b", "c"], "richtig": 1,
                "thema": "Level 1", "hinweis": "Weil b."}],
}


def _projekt_mit_curriculum(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "curriculum.md").write_text("# Plan")
    return slug


def test_pruefung_starten_setzt_phase(client):
    slug = _projekt_mit_curriculum(client)
    antwort = client.post(f"/api/projekte/{slug}/pruefung")
    assert antwort.status_code == 200
    assert antwort.json()["phase"] == projekte.PHASE_PRUEFUNG_LAEUFT
    assert client.gestartet


def test_pruefung_ohne_curriculum_ist_404(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert client.post(f"/api/projekte/{slug}/pruefung").status_code == 404


def test_unsinnige_bestehensgrenze_ist_400(client):
    slug = _projekt_mit_curriculum(client)
    antwort = client.post(f"/api/projekte/{slug}/pruefung",
                          json={"bestehensgrenze": 250})
    assert antwort.status_code == 400


def test_lesen_ohne_datei_ist_404(client):
    slug = _projekt_mit_curriculum(client)
    assert client.get(f"/api/projekte/{slug}/pruefung").status_code == 404


def test_lesen_liefert_die_geprueften_daten(client):
    slug = _projekt_mit_curriculum(client)
    (projekte.projekt_dir(slug) / "pruefung.json").write_text(
        json.dumps(GUELTIG), encoding="utf-8")

    daten = client.get(f"/api/projekte/{slug}/pruefung").json()
    assert daten["titel"] == GUELTIG["titel"]
    assert len(daten["fragen"]) == 1


def test_kaputte_datei_ist_400_mit_klartext(client):
    slug = _projekt_mit_curriculum(client)
    (projekte.projekt_dir(slug) / "pruefung.json").write_text("```json\n{}\n```")

    antwort = client.get(f"/api/projekte/{slug}/pruefung")
    assert antwort.status_code == 400
    assert "Code-Zäune" in antwort.json()["detail"]
```

- [ ] **Step 6: Routen implementieren**

In `app/projekte.py` bei den Phasen: `PHASE_PRUEFUNG_LAEUFT = "pruefung_laeuft"`.

In `app/runner.py` bei `PHASE_NACH_ERFOLG`: `"pruefung": projekte.PHASE_FERTIG,`.

In `app/main.py`:
```python
@app.post("/api/projekte/{slug}/pruefung")
def api_pruefung_starten(slug: str, body: dict | None = None):
    """Startet die Prüfungs-Phase → pruefung.json aus der Stoffquelle."""
    p = _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    if not (d / "curriculum.md").is_file():
        raise HTTPException(404, "Noch kein curriculum.md vorhanden")
    if runner.laeuft(slug):
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")

    grenze = (body or {}).get("bestehensgrenze", 70)
    if not isinstance(grenze, int) or isinstance(grenze, bool) \
            or not 1 <= grenze <= 100:
        raise HTTPException(400, "bestehensgrenze muss zwischen 1 und 100 liegen")

    vorher = p["status"].get("phase", projekte.PHASE_FERTIG)
    projekte.set_phase(slug, projekte.PHASE_PRUEFUNG_LAEUFT)
    try:
        runner.start(slug, "pruefung", prompts.pruefung_prompt(d, grenze),
                     zurueck_phase=vorher)
    except runner.LaufAktiv:
        projekte.set_phase(slug, vorher)
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "phase": projekte.PHASE_PRUEFUNG_LAEUFT}


@app.get("/api/projekte/{slug}/pruefung")
def api_pruefung_lesen(slug: str):
    """Die geprüfte pruefung.json. 400 nennt den Grund im Klartext."""
    _projekt_oder_404(slug)
    pfad = projekte.projekt_dir(slug) / "pruefung.json"
    if not pfad.is_file():
        raise HTTPException(404, "Noch keine Prüfung erzeugt")
    try:
        return pruefung.laden(pfad)
    except pruefung.PruefungFehler as e:
        raise HTTPException(400, str(e))
```
Import `pruefung` in `app/main.py` ergänzen.

- [ ] **Step 7: Tests laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_api_pruefung.py tests/test_pruefung_prompt.py -v`
Expected: 12 passed.

- [ ] **Step 8: Commit**

```bash
git add app/prompts.py app/projekte.py app/runner.py app/main.py tests/test_pruefung_prompt.py tests/test_api_pruefung.py
git commit -m "feat: Pruefungsphase - Arbeitsauftrag und Routen"
```

---

### Task 14: Prüfungs-HTML rendern

**Files:**
- Modify: `app/pruefung.py`, `app/main.py`
- Test: `tests/test_pruefung_html.py`

**Interfaces:**
- Consumes: `app.pruefung.laden()`, `app.projekte.projekt_dir()`
- Produces:
  - `app.pruefung.als_html(daten: dict, design: dict | None = None) -> str`
  - `app.pruefung.FARBEN: dict` — Vorgabewerte Navy/Gold/Cream
  - `GET /api/projekte/{slug}/pruefung.html` → HTML zum Download

- [ ] **Step 1: Den Test schreiben**

`tests/test_pruefung_html.py`:
```python
"""Prüfungs-HTML: offline lauffähig, ohne Server, im AI-SmartCon-CI."""

from app import pruefung

DATEN = {
    "titel": "Abschlussprüfung KI-Verordnung",
    "bestehensgrenze": 70,
    "fragen": [
        {"frage": "Seit wann wird Art. 4 durchgesetzt?",
         "optionen": ["seit 02.08.2026", "seit 2027", "gar nicht"],
         "richtig": 0, "thema": "Level 1", "hinweis": "Marktüberwachung seit 02.08.2026."},
        {"frage": "Was leistet ein AVV <nicht>?",
         "optionen": ["Erlaubnis", "Weisungsbindung", "Vertraulichkeit"],
         "richtig": 0, "thema": "Level 3", "hinweis": "Er macht nichts erlaubt."},
    ],
}


def test_html_ist_vollstaendig_und_eigenstaendig():
    html = pruefung.als_html(DATEN)
    assert html.startswith("<!doctype html>")
    assert "</html>" in html
    # Offline lauffähig: kein Verweis nach draußen.
    assert "http://" not in html
    assert "https://" not in html
    assert "<script src=" not in html
    assert "<link rel=\"stylesheet\"" not in html


def test_titel_und_fragen_stehen_drin():
    html = pruefung.als_html(DATEN)
    assert DATEN["titel"] in html
    assert "Seit wann wird Art. 4 durchgesetzt?" in html
    assert "seit 02.08.2026" in html


def test_html_wird_maskiert():
    # Ein „<" im Fragetext darf kein Markup werden.
    html = pruefung.als_html(DATEN)
    assert "&lt;nicht&gt;" in html
    assert "<nicht>" not in html


def test_ci_farben_sind_gesetzt():
    html = pruefung.als_html(DATEN)
    for farbe in ("#060611", "#c9a84c", "#f6f1e8"):
        assert farbe in html


def test_design_ueberschreibt_die_vorgabe():
    html = pruefung.als_html(DATEN, design={"akzent": "#ff0000"})
    assert "#ff0000" in html


def test_bestehensgrenze_und_fragenzahl_stehen_im_javascript():
    html = pruefung.als_html(DATEN)
    assert "70" in html
    assert "\"richtig\": 0" in html or "richtig:0" in html.replace(" ", "")


def test_lösungen_stehen_nicht_im_sichtbaren_text():
    # Die Auswertung braucht die Lösungen im Skript — sie dürfen aber nicht
    # als Markierung im Fragebogen selbst auftauchen.
    html = pruefung.als_html(DATEN)
    fragebogen = html.split("<script")[0]
    assert "richtig" not in fragebogen
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_pruefung_html.py -v`
Expected: FAIL mit `AttributeError: module 'app.pruefung' has no attribute 'als_html'`.

- [ ] **Step 3: Implementieren**

An `app/pruefung.py` anhängen:
```python
import html as _html

# AI-SmartCon-CI. Eine design.md im Projekt kann sie überschreiben.
FARBEN = {
    "hintergrund": "#060611",
    "panel": "#1a1a22",
    "akzent": "#c9a84c",
    "akzent_hell": "#e0c274",
    "text": "#f6f1e8",
    "text_sekundaer": "#d8cdb4",
}


def als_html(daten: dict, design: dict | None = None) -> str:
    """Eine offline lauffähige Prüfungsseite. Kein Server, keine Fremdquellen.

    Die Lösungen stehen im Skript, nicht im Fragebogen — sonst genügt ein
    Blick in den Quelltext des sichtbaren Teils.
    """
    pruefe(daten)
    farben = {**FARBEN, **(design or {})}

    fragen_html = []
    for nr, frage in enumerate(daten["fragen"], start=1):
        optionen = "\n".join(
            f'          <label class="option">'
            f'<input type="radio" name="f{nr}" value="{i}"> '
            f'{_html.escape(str(o))}</label>'
            for i, o in enumerate(frage["optionen"]))
        thema = _html.escape(str(frage.get("thema", "")))
        fragen_html.append(f"""      <li class="frage" id="frage-{nr}">
        <p class="thema">{thema}</p>
        <p class="text">{_html.escape(str(frage["frage"]))}</p>
        <div class="optionen">
{optionen}
        </div>
        <p class="rueckmeldung" hidden></p>
      </li>""")

    # Nur das, was die Auswertung braucht.
    loesungen = json.dumps(
        [{"richtig": f["richtig"], "hinweis": str(f.get("hinweis", ""))}
         for f in daten["fragen"]], ensure_ascii=False)

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(str(daten["titel"]))}</title>
<style>
  :root {{
    --bg: {farben["hintergrund"]};
    --panel: {farben["panel"]};
    --akzent: {farben["akzent"]};
    --akzent-hell: {farben["akzent_hell"]};
    --text: {farben["text"]};
    --text2: {farben["text_sekundaer"]};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 16px;
    background: var(--bg); color: var(--text);
    font-family: Inter, system-ui, sans-serif; line-height: 1.5;
  }}
  main {{ max-width: 760px; margin: 0 auto; }}
  h1 {{ font-size: 28px; line-height: 1.2; margin: 0 0 8px; }}
  .kopf {{ border-bottom: 3px solid var(--akzent); padding-bottom: 16px; margin-bottom: 24px; }}
  .muted {{ color: var(--text2); font-size: 14px; }}
  ol {{ list-style: none; padding: 0; margin: 0; }}
  .frage {{
    background: var(--panel); border: 1px solid var(--akzent);
    border-radius: 14px; padding: 20px; margin-bottom: 16px;
  }}
  .thema {{
    color: var(--akzent); font-size: 11px; letter-spacing: .14em;
    text-transform: uppercase; margin: 0 0 8px;
  }}
  .text {{ font-weight: 600; margin: 0 0 12px; }}
  .optionen {{ display: flex; flex-direction: column; gap: 8px; }}
  .option {{
    display: flex; gap: 10px; align-items: flex-start;
    padding: 10px 12px; border-radius: 10px;
    background: rgba(255,255,255,.04); cursor: pointer;
  }}
  .option[hidden] {{ display: none; }}
  .rueckmeldung {{ margin: 12px 0 0; font-size: 14px; color: var(--text2); }}
  .rueckmeldung[hidden] {{ display: none; }}
  .richtig {{ border-color: #4ade80; }}
  .falsch {{ border-color: #f87171; }}
  .zeile {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
  button {{
    background: var(--akzent); color: #1a1a22; border: 0;
    border-radius: 10px; padding: 13px 22px; font-size: 15px;
    font-weight: 600; cursor: pointer;
  }}
  button:hover {{ background: var(--akzent-hell); }}
  #ergebnis {{
    margin-top: 24px; padding: 20px; border-radius: 14px;
    background: var(--panel); border: 1px solid var(--akzent);
  }}
  #ergebnis[hidden] {{ display: none; }}
  #ergebnis .note {{ font-size: 34px; font-weight: 700; color: var(--akzent); }}
</style>
</head>
<body>
<main>
  <div class="kopf">
    <h1>{_html.escape(str(daten["titel"]))}</h1>
    <p class="muted">{len(daten["fragen"])} Fragen · bestanden ab
      {daten["bestehensgrenze"]} % · genau eine Antwort je Frage ist richtig.</p>
  </div>

  <form id="pruefung">
    <ol>
{chr(10).join(fragen_html)}
    </ol>
    <div class="zeile">
      <button type="submit">Auswerten</button>
      <span id="hinweis" class="muted"></span>
    </div>
  </form>

  <div id="ergebnis" hidden>
    <p class="note" id="note"></p>
    <p id="urteil"></p>
    <div class="zeile"><button type="button" id="nochmal">Noch einmal</button></div>
  </div>
</main>
<script>
const LOESUNGEN = {loesungen};
const GRENZE = {daten["bestehensgrenze"]};
const form = document.getElementById('pruefung');

form.addEventListener('submit', (e) => {{
  e.preventDefault();
  const offen = LOESUNGEN.findIndex((_, i) => !form[`f${{i + 1}}`].value);
  if (offen !== -1) {{
    document.getElementById('hinweis').textContent =
      `Frage ${{offen + 1}} ist noch offen.`;
    document.getElementById(`frage-${{offen + 1}}`).scrollIntoView({{block: 'center'}});
    return;
  }}
  document.getElementById('hinweis').textContent = '';

  let treffer = 0;
  LOESUNGEN.forEach((loesung, i) => {{
    const gewaehlt = Number(form[`f${{i + 1}}`].value);
    const kasten = document.getElementById(`frage-${{i + 1}}`);
    const rueck = kasten.querySelector('.rueckmeldung');
    const ok = gewaehlt === loesung.richtig;
    if (ok) treffer++;
    kasten.classList.remove('richtig', 'falsch');
    kasten.classList.add(ok ? 'richtig' : 'falsch');
    rueck.textContent = (ok ? 'Richtig. ' : 'Nicht richtig. ') + loesung.hinweis;
    rueck.hidden = false;
  }});

  const prozent = Math.round((treffer / LOESUNGEN.length) * 100);
  document.getElementById('note').textContent = `${{prozent}} %`;
  document.getElementById('urteil').textContent = prozent >= GRENZE
    ? `Bestanden — ${{treffer}} von ${{LOESUNGEN.length}} Fragen richtig.`
    : `Nicht bestanden — ${{treffer}} von ${{LOESUNGEN.length}} richtig, nötig sind ${{GRENZE}} %.`;
  document.getElementById('ergebnis').hidden = false;
  document.getElementById('ergebnis').scrollIntoView({{behavior: 'smooth'}});
}});

document.getElementById('nochmal').addEventListener('click', () => {{
  form.reset();
  document.querySelectorAll('.frage').forEach((k) => {{
    k.classList.remove('richtig', 'falsch');
    k.querySelector('.rueckmeldung').hidden = true;
  }});
  document.getElementById('ergebnis').hidden = true;
  window.scrollTo({{top: 0, behavior: 'smooth'}});
}});
</script>
</body>
</html>
"""
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_pruefung_html.py -v`
Expected: 7 passed.

- [ ] **Step 5: Route ergänzen**

In `app/main.py`:
```python
@app.get("/api/projekte/{slug}/pruefung.html")
def api_pruefung_html(slug: str):
    """Die Prüfung als offline lauffähige HTML-Datei."""
    _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    pfad = d / "pruefung.json"
    if not pfad.is_file():
        raise HTTPException(404, "Noch keine Prüfung erzeugt")
    try:
        daten = pruefung.laden(pfad)
    except pruefung.PruefungFehler as e:
        raise HTTPException(400, str(e))

    ziel = d / "pruefung.html"
    ziel.write_text(pruefung.als_html(daten), encoding="utf-8")
    return FileResponse(ziel, filename=ziel.name, media_type="text/html")
```

- [ ] **Step 6: Von Hand ansehen**

```bash
.venv/bin/python - <<'PY'
import json, pathlib
from app import pruefung
daten = json.loads(pathlib.Path("tests/beispiel-pruefung.json").read_text())
pathlib.Path("/tmp/pruefung.html").write_text(pruefung.als_html(daten))
PY
```
Vorher `tests/beispiel-pruefung.json` anlegen:
```json
{
  "titel": "Abschlussprüfung KI-Verordnung",
  "bestehensgrenze": 70,
  "fragen": [
    {"frage": "Seit wann wird Art. 4 KI-VO praktisch durchgesetzt?",
     "optionen": ["seit 02.08.2026", "seit 02.02.2025", "noch gar nicht"],
     "richtig": 0,
     "thema": "Level 1",
     "hinweis": "Anwendbar seit 02.02.2025, durchgesetzt wird seit dem 02.08.2026."},
    {"frage": "Was leistet ein AVV nach Art. 28 DSGVO nicht?",
     "optionen": ["Er erlaubt die Verarbeitung",
                  "Er bindet den Anbieter an Weisungen",
                  "Er regelt Vertraulichkeit"],
     "richtig": 0,
     "thema": "Level 4",
     "hinweis": "Ein AVV macht keine Verarbeitung erlaubt, er macht sie vertragsfest."}
  ]
}
```
Die Datei im Browser öffnen: absenden ohne Antwort muss zur ersten offenen Frage springen, die Auswertung muss Prozent und Urteil zeigen, „Noch einmal" muss zurücksetzen. Bei 390 px und 320 px gegenprüfen.

- [ ] **Step 7: Commit**

```bash
git add app/pruefung.py app/main.py tests/test_pruefung_html.py tests/beispiel-pruefung.json
git commit -m "feat: Pruefung als offline lauffaehige HTML-Datei"
```

---

### Task 15: Prüfungsblock in der Projektansicht

**Files:**
- Modify: `static/index.html`, `static/app.js`

- [ ] **Step 1: Block anlegen**

In `static/index.html` in `#pv-detail` nach dem Ergebnis-Bereich:
```html
      <div id="pruefungsblock" hidden>
        <h3>Abschlussprüfung</h3>
        <p class="muted">Gefragt wird nur, was ausgeliefert wurde: eine
          hochgeladene Präsentation schlägt die erzeugte Lerneinheit, beide
          schlagen das Curriculum.</p>
        <p class="muted" id="pruefung-quelle"></p>
        <div class="zeile">
          <label>Bestehensgrenze (%)
            <input id="bestehensgrenze" type="number" min="1" max="100" value="70">
          </label>
          <button id="btn-pruefung-start">Prüfung erzeugen</button>
          <span id="pruefung-status" class="muted"></span>
        </div>
        <div id="pruefung-ergebnis"></div>
      </div>
```

`?v=` hochzählen.

- [ ] **Step 2: Logik ergänzen**

An `static/app.js`:
```javascript
/* ---------- Prüfung ---------- */

const PRUEFUNG_PHASEN = ['fertig', 'pruefung_laeuft'];

async function ladePruefung(projekt) {
  const block = document.getElementById('pruefungsblock');
  block.hidden = !PRUEFUNG_PHASEN.includes(projekt.phase);
  if (block.hidden) return;

  const ziel = document.getElementById('pruefung-ergebnis');
  const antwort = await fetch(`/api/projekte/${encodeURIComponent(aktuellerSlug)}/pruefung`);
  if (antwort.status === 404) {
    ziel.innerHTML = '<p class="muted">Noch keine Prüfung erzeugt.</p>';
    return;
  }
  const daten = await antwort.json();
  if (!antwort.ok) {
    ziel.innerHTML = `<p class="fehler">${esc(daten.detail)}</p>`;
    return;
  }
  ziel.innerHTML = `
    <p><strong>${esc(daten.titel)}</strong> — ${daten.fragen.length} Fragen,
       bestanden ab ${daten.bestehensgrenze} %.</p>
    <a class="download" href="/api/projekte/${encodeURIComponent(aktuellerSlug)}/pruefung.html">
      Prüfung als HTML herunterladen</a>`;
}

document.getElementById('btn-pruefung-start').addEventListener('click', async () => {
  const status = document.getElementById('pruefung-status');
  const grenze = Number(document.getElementById('bestehensgrenze').value);
  status.textContent = 'Wird erzeugt …';
  const antwort = await fetch(`/api/projekte/${encodeURIComponent(aktuellerSlug)}/pruefung`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bestehensgrenze: grenze }) });
  const ergebnis = await antwort.json();
  status.textContent = antwort.ok ? '' : `Fehler: ${ergebnis.detail}`;
  if (antwort.ok) aktualisiereDetail();
});
```

`ladePruefung(projekt)` in `aktualisiereDetail()` aufrufen, dort wo `ladeErgebnis()` aufgerufen wird.

- [ ] **Step 3: Syntax prüfen**

Run: `node --check static/app.js`
Expected: keine Ausgabe.

- [ ] **Step 4: End-to-End an einer bestehenden Schulung**

Container bauen (kein Agent aktiv!). Eine der fünf fertigen Schulungen öffnen, „Prüfung erzeugen" drücken, Lauf abwarten, HTML herunterladen und ausfüllen. **Stichprobe von drei Fragen:** Lässt sich jede allein aus der Stoffquelle beantworten? Wenn nicht, ist der Prompt zu weich — Regel im `pruefung_prompt` schärfen, nicht die Frage von Hand korrigieren.

- [ ] **Step 5: Commit**

```bash
git add static/
git commit -m "feat: Pruefungsblock in der Projektansicht"
```

---

# Etappe 3 — Folien einbetten

Ziel: Die Lerneinheit zeigt wahlweise die gerenderten Folien statt neu erzeugter Medien. Erfolgskriterium: Eine Schulung mit eingeschaltetem Schalter verbraucht 0 Higgsfield-Credits und zeigt genau die Folien des Decks.

### Task 16: Folien als PNG

**Files:**
- Create: `app/folien.py`, `tests/test_folien.py`

**Interfaces:**
- Produces:
  - `app.folien.FolienFehler(RuntimeError)`
  - `app.folien.werkzeuge_vorhanden() -> bool`
  - `app.folien.exportiere(quelle: Path, ziel_dir: Path, dpi: int = 150) -> list[Path]` — PNGs `folie-01.png` …

- [ ] **Step 1: Den Test schreiben**

`tests/test_folien.py`:
```python
"""PPTX/PDF → PNG über LibreOffice und pdftoppm."""

import shutil

import pytest

from app import folien

hat_werkzeuge = pytest.mark.skipif(
    not folien.werkzeuge_vorhanden(),
    reason="LibreOffice/pdftoppm nicht installiert (läuft im Container)")


def test_werkzeuge_vorhanden_prueft_beide():
    erwartet = bool(shutil.which("soffice") or shutil.which("libreoffice")) \
        and bool(shutil.which("pdftoppm"))
    assert folien.werkzeuge_vorhanden() is erwartet


def test_fehlende_quelle_wirft(tmp_path):
    with pytest.raises(folien.FolienFehler, match="nicht gefunden"):
        folien.exportiere(tmp_path / "gibt-es-nicht.pptx", tmp_path)


def test_unbekanntes_format_wirft(tmp_path):
    quelle = tmp_path / "notiz.txt"
    quelle.write_text("x")
    with pytest.raises(folien.FolienFehler, match="Format"):
        folien.exportiere(quelle, tmp_path)


@hat_werkzeuge
def test_pptx_wird_zu_pngs(tmp_path):
    from pptx import Presentation
    from pptx.util import Inches

    quelle = tmp_path / "deck.pptx"
    p = Presentation()
    for text in ("Erste Folie", "Zweite Folie"):
        folie = p.slides.add_slide(p.slide_layouts[5])
        folie.shapes.title.text = text
    p.save(quelle)

    ziel = tmp_path / "folien"
    bilder = folien.exportiere(quelle, ziel)
    assert [b.name for b in bilder] == ["folie-01.png", "folie-02.png"]
    assert all(b.stat().st_size > 0 for b in bilder)


@hat_werkzeuge
def test_zielordner_wird_vorher_geleert(tmp_path):
    from pptx import Presentation

    quelle = tmp_path / "deck.pptx"
    p = Presentation()
    p.slides.add_slide(p.slide_layouts[5])
    p.save(quelle)

    ziel = tmp_path / "folien"
    ziel.mkdir()
    (ziel / "folie-99.png").write_bytes(b"alt")
    bilder = folien.exportiere(quelle, ziel)
    assert not (ziel / "folie-99.png").exists()
    assert len(bilder) == 1
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_folien.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.folien'`.

- [ ] **Step 3: Implementieren**

`app/folien.py`:
```python
"""Foliensatz → PNG. LibreOffice macht das PDF, pdftoppm die Bilder.

Zwei Schritte statt einem: LibreOffice kann zwar direkt Bilder schreiben,
aber nur die erste Folie je Aufruf. Der Umweg über PDF ist der einzige, der
einen ganzen Satz in einem Durchgang liefert.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

QUELLFORMATE = (".pptx", ".ppt", ".odp", ".pdf")
ZEITLIMIT = 300


class FolienFehler(RuntimeError):
    """Export nicht möglich. Die Meldung nennt den Grund."""


def _soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def werkzeuge_vorhanden() -> bool:
    return bool(_soffice()) and bool(shutil.which("pdftoppm"))


def exportiere(quelle: Path, ziel_dir: Path, dpi: int = 150) -> list[Path]:
    """Rendert jede Folie als folie-NN.png. Leert ziel_dir vorher."""
    if not quelle.is_file():
        raise FolienFehler(f"Quelldatei nicht gefunden: {quelle}")
    if quelle.suffix.lower() not in QUELLFORMATE:
        raise FolienFehler(
            f"Format {quelle.suffix} wird nicht unterstützt "
            f"(möglich: {', '.join(QUELLFORMATE)})")
    if not werkzeuge_vorhanden():
        raise FolienFehler(
            "LibreOffice oder pdftoppm fehlt — im Container sind sie enthalten, "
            "auf dem Host nicht zwingend")

    if ziel_dir.exists():
        shutil.rmtree(ziel_dir)
    ziel_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as tmp:
        pdf = _als_pdf(quelle, Path(tmp))
        _als_pngs(pdf, ziel_dir, dpi)

    return sorted(ziel_dir.glob("folie-*.png"))


def _als_pdf(quelle: Path, arbeit: Path) -> Path:
    if quelle.suffix.lower() == ".pdf":
        return quelle
    # -env:UserInstallation: eigenes Profil, sonst blockieren sich parallele
    # Aufrufe gegenseitig und der zweite endet ohne Ausgabe.
    befehl = [_soffice(), "--headless",
              f"-env:UserInstallation=file://{arbeit / 'profil'}",
              "--convert-to", "pdf", "--outdir", str(arbeit), str(quelle)]
    _laufen_lassen(befehl, "LibreOffice")
    pdf = arbeit / f"{quelle.stem}.pdf"
    if not pdf.is_file():
        raise FolienFehler(
            f"LibreOffice hat kein PDF geschrieben (erwartet: {pdf.name})")
    return pdf


def _als_pngs(pdf: Path, ziel_dir: Path, dpi: int) -> None:
    befehl = ["pdftoppm", "-png", "-r", str(dpi),
              str(pdf), str(ziel_dir / "folie")]
    _laufen_lassen(befehl, "pdftoppm")
    # pdftoppm nummeriert je nach Seitenzahl unterschiedlich breit
    # (folie-1.png bei <10 Seiten, folie-01.png ab 10). Einheitlich machen,
    # damit die Sortierung stimmt und der Skill feste Namen erwarten kann.
    for datei in sorted(ziel_dir.glob("folie-*.png")):
        nummer = datei.stem.split("-")[-1]
        ziel = ziel_dir / f"folie-{int(nummer):02d}.png"
        if datei != ziel:
            datei.rename(ziel)


def _laufen_lassen(befehl: list[str], name: str) -> None:
    try:
        ergebnis = subprocess.run(befehl, capture_output=True, text=True,
                                  timeout=ZEITLIMIT)
    except subprocess.TimeoutExpired as e:
        raise FolienFehler(f"{name} hat das Zeitlimit überschritten") from e
    if ergebnis.returncode != 0:
        raise FolienFehler(
            f"{name} fehlgeschlagen: {ergebnis.stderr.strip() or ergebnis.stdout.strip()}")
```

- [ ] **Step 4: Test laufen lassen — auf dem Host und im Container**

Run (Host): `.venv/bin/python -m pytest tests/test_folien.py -v`
Expected: 3 passed, 2 skipped (Werkzeuge fehlen auf dem Host).

Run (Container): `docker exec smartcon-schulungen sh -lc 'cd /app && python -m pytest tests/test_folien.py -v'`
Expected: 5 passed. Läuft dort pytest nicht, die Testdateien einmalig hineinkopieren: `docker cp tests smartcon-schulungen:/app/tests`.

- [ ] **Step 5: Commit**

```bash
git add app/folien.py tests/test_folien.py
git commit -m "feat: Foliensatz als PNG-Sequenz exportieren"
```

---

### Task 17: Schalter „Folien einbetten"

**Files:**
- Modify: `app/main.py`, `app/prompts.py`, `static/index.html`, `static/app.js`
- Test: `tests/test_folien_schalter.py`

**Interfaces:**
- Produces:
  - `brief.json` bekommt `"folien_einbetten": bool` (Default `False`)
  - `app.prompts.folien_block(projekt_dir: Path, brief: dict) -> str` — Textbaustein für den Produktions-Prompt, leer wenn aus

- [ ] **Step 1: Den Test schreiben**

`tests/test_folien_schalter.py`:
```python
"""Schalter „Folien einbetten": aus dem Briefing in den Produktionsauftrag."""

from app import projekte, prompts

FORM = {"thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
        "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos"}


def test_default_ist_aus(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert projekte.get(slug)["briefing"]["folien_einbetten"] is False


def test_schalter_wird_uebernommen(client):
    slug = client.post("/api/projekte",
                       data={**FORM, "folien_einbetten": "ja"}).json()["slug"]
    assert projekte.get(slug)["briefing"]["folien_einbetten"] is True


def test_block_ist_leer_wenn_aus(tmp_path):
    assert prompts.folien_block(tmp_path, {"folien_einbetten": False}) == ""


def test_block_ohne_stoffquelle_nennt_den_mangel(tmp_path):
    block = prompts.folien_block(tmp_path, {"folien_einbetten": True})
    assert "keine Folien" in block


def test_block_nennt_quelle_und_zielordner(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")

    block = prompts.folien_block(tmp_path, {"folien_einbetten": True})
    assert "deck.pptx" in block
    assert str(tmp_path / "folien") in block
    assert "app.folien" in block
    # Kein Higgsfield für Bilder, wenn die Folien die Optik liefern.
    assert "keine Bilder erzeugen" in block
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_folien_schalter.py -v`
Expected: FAIL — `folien_einbetten` fehlt im Briefing.

- [ ] **Step 3: Implementieren**

In `app/main.py` in `api_projekt_neu` den Parameter ergänzen:
```python
    folien_einbetten: str = Form("nein"),
```
und im `briefing`-Wörterbuch:
```python
        # Folien der Stoffquelle als Bilder verwenden statt neue Medien zu
        # erzeugen — spart Credits und hält Deck und Einheit deckungsgleich.
        "folien_einbetten": folien_einbetten.lower() in ("ja", "true", "1", "on"),
```

In `app/prompts.py`:
```python
def folien_block(projekt_dir: Path, brief: dict) -> str:
    """Textbaustein für den Produktions-Prompt. Leer, wenn der Schalter aus ist."""
    if not brief.get("folien_einbetten"):
        return ""

    quelle = stoffquelle(projekt_dir)
    ziel = projekt_dir / "folien"
    if quelle is None or quelle.suffix.lower() not in (".pptx", ".ppt", ".odp", ".pdf"):
        return f"""
## Folien einbetten — nicht möglich

Der Schalter „Folien einbetten" ist an, aber es liegen **keine Folien** vor
(weder im Ordner `material/` noch als PDF). Erzeuge die Medien wie üblich und
halte im Curriculum unter „Offene Positionen" fest, dass der Schalter ins
Leere lief.
"""
    return f"""
## Folien einbetten (Schalter ist an)

Die Optik der Level kommt aus dem ausgelieferten Foliensatz, nicht aus neu
erzeugten Medien. Grundlage: {quelle}

1. Rendere die Folien einmalig als PNG-Sequenz:

```bash
cd /app && python3 -c "
from pathlib import Path
from app import folien
bilder = folien.exportiere(Path('{quelle}'), Path('{ziel}'))
print(len(bilder), 'Folien gerendert')
"
```

2. Binde die entstandenen `folie-NN.png` als Data-URI in die Lerneinheit ein —
   je Level die Folien, die den Stoff dieses Levels tragen.
3. **Für die Level keine Bilder erzeugen** und keine Filme anfordern: Der
   Foliensatz ist die Optik. Voiceover und Animationen bleiben erlaubt.
4. Halte im Curriculum fest, welche Folie zu welchem Level gehört.
"""
```

Im Produktions-Prompt (`produktion_prompt`) den Baustein einsetzen: `folien_block(projekt_dir, brief)` an derselben Stelle einfügen, an der heute `design_block` und `kostenlos_block` stehen.

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_folien_schalter.py -v`
Expected: 6 passed.

- [ ] **Step 5: Schalter in die Oberfläche**

In `static/index.html` im Projektformular neben den KI-Medien-Schalter:
```html
        <label class="checkbox" id="folien-wrap">
          <input name="folien_einbetten" type="checkbox" value="ja">
          Folien der hochgeladenen Präsentation einbetten
        </label>
        <p class="muted" id="folien-hinweis">Die Lerneinheit zeigt dann genau
          die Folien statt neu erzeugter Bilder — kostet keine Credits und hält
          Deck und Einheit deckungsgleich.</p>
```

`?v=` hochzählen, `node --check static/app.js`.

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/prompts.py static/ tests/test_folien_schalter.py
git commit -m "feat: Schalter Folien einbetten im Briefing"
```

---

### Task 18: Produktionspfad im Skill

**Files:**
- Modify: `skill/schulung/SKILL.md`

- [ ] **Step 1: Abschnitt ergänzen**

In `skill/schulung/SKILL.md` nach dem Abschnitt zu Preset und `design.md` einfügen:

```markdown
## Folien einbetten: der zweite Produktionspfad

Enthält der Arbeitsauftrag einen Abschnitt „Folien einbetten (Schalter ist an)",
gilt dieser Pfad **anstelle** der Bild- und Filmproduktion:

- Die PNG-Sequenz aus `folien/` ist die Optik der Level. Jede Folie wird als
  Data-URI eingebettet, damit die Datei offline lauffähig bleibt.
- **Keine Higgsfield-Bilder, keine Filme.** Voiceover und HTML-Animationen
  bleiben erlaubt und kosten wie gewohnt.
- Eine Folie kann mehrere Level tragen und ein Level mehrere Folien. Die
  Zuordnung gehört ins Curriculum, damit sie nachvollziehbar bleibt.
- Folien sind 16:9 und breit. Auf schmalen Displays skaliert das Bild auf
  `max-width: 100%`; Text auf der Folie darf **nicht** die einzige Quelle einer
  Information sein — der Lehrtext daneben trägt den Inhalt.
- Der Kostenplan führt in diesem Fall nur Voiceover-Posten. Die Bild- und
  Filmzeilen entfallen ersatzlos, nicht mit 0 Credits.

Fehlt der Abschnitt im Auftrag, gilt unverändert der bisherige Pfad.
```

- [ ] **Step 2: Syntax prüfen**

Run: `bash -n skill/schulung/scripts/*.sh`
Expected: keine Ausgabe (die Skripte sind unverändert; der Aufruf sichert nur, dass nichts kaputt ging).

- [ ] **Step 3: End-to-End**

Eine kleine Schulung anlegen: Preset `kostenlos`, Schalter „Folien einbetten" an, ein zweiseitiges Deck als Material. Curriculum erzeugen, freigeben, produzieren. Erfolgskriterien:
- Der Kostenplan führt **keine** Bild- oder Filmposten.
- Die fertige HTML zeigt die Folien.
- `higgsfield account status` vor und nach dem Lauf zeigt **denselben** Guthabenstand, wenn kein Voiceover angefordert wurde.

- [ ] **Step 4: Commit**

```bash
git add skill/schulung/SKILL.md
git commit -m "docs(skill): Produktionspfad Folien einbetten"
```

---

## Abschluss von Plan 1

- [ ] Volle Suite: `.venv/bin/python -m pytest -q` — alles grün
- [ ] `git status --short projects/` — leer (kein Test hat echte Projektdaten angefasst)
- [ ] `CLAUDE.md` nachziehen: neue Module (`praesentation`, `pruefung`, `folien`), neue Phasen, Projektart, der Hinweis auf `stoffquelle()` und die Regel „Prüfung nur aus dem ausgelieferten Stoff"
- [ ] `TECH_STACK.md`: LibreOffice, poppler, python-pptx, pytest
- [ ] `SPEC.md`: Präsentation als Projektart und die Prüfungsentscheidung als Nummern 15 und 16 ergänzen
- [ ] Vault-Projektnotiz `~/vault/04-projects/smartcon-kurse/README.md` anlegen

---

# Plan 2 (Skizze) — Kursverwaltung, Etappe 4–7

Diese Etappen bekommen einen eigenen Plan, sobald Plan 1 steht. Ihre Details hängen an Entscheidungen, die während Etappe 0–3 fallen (Modulschnitt, Testkonventionen, Umgang mit dem Skill im Container). Festgelegt ist bereits:

**Datenmodell** (SQLModel, SQLite unter `data/kurse.db`, getrennt vom Projektordner):

| Tabelle | Kern |
|---|---|
| `Kurs` | Slug, Titel, Beschreibung, Preis, Dauer, Bezeichnung des Nachweises |
| `Serie` | Rhythmus, Platzzahl, Laufzeit — erzeugt Termine |
| `Termin` | Kurs, Beginn, Ende, Plätze, Status (offen/ausgebucht/abgesagt) |
| `Anmeldung` | Termin (oder Kurs bei terminlosem E-Learning), Person, Firma, Mail, Zahlungsvermerk |
| `Teilnehmer` | Mail, `passwort_hash` (leer bis Freischaltung), Zugangsfenster |
| `Sitzung` | `token_hash`, `gueltig_bis` |
| `Pruefungsfrage`, `Pruefungsversuch` | aus `pruefung.json` übernommen, Versuche gezählt |

**Etappe 4** — Datenmodell, Migrationen, Kurse und Termine in der Verwaltung.
**Etappe 5** — Anmeldestrecke, `smtplib`-Versand, Bestätigungsmail, Rechnungsvermerk. Die Anmeldung läuft **vollständig in der App** unter `kurse.ai-smartcon.de`, im AI-SmartCon-CI, damit der Übergang von der Website nicht auffällt. ai-smartcon.de bleibt unverändert und verlinkt nur — kein API-Schlüssel in einem Browser-Bundle, kein CORS, keine Änderung am Website-Repo.
**Etappe 6** — Teilnehmerzugänge (scrypt, Einmalanzeige des Passworts), Portal mit Unterlagen und Prüfung, Zertifikats-PDF im AI-SmartCon-CI.
**Etappe 7** — Umbenennung auf SmartCon-Kurse, Repo auf privat, Cloudflare Access mit Bypass für `/portal*`, Domain, Betriebsdoku.

**Vor Etappe 7 zu klären:** Herkunft und Lizenzlage des `skill/schulung/` (Danksagung an Julian Ivanov im README, keine Lizenzangabe im Skill selbst), bevor die Lizenz von AGPL-3.0 wechselt. Bereits veröffentlichte Stände bleiben AGPL.
