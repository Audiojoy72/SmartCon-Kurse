# SmartCon-Kurse — Termine, Anmeldung, Betrieb (Etappe 6–7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die betreuten Kurse verkaufbar machen: Kurse und Terminserien pflegen, Interessenten melden sich selbst an, die Bestätigung geht automatisch raus — und aus einer bezahlten Anmeldung wird mit einem Klick ein Teilnehmer mit Portalzugang. Danach heißt das Projekt SmartCon-Kurse und ist von außen erreichbar.

**Architecture:** Vier Tabellen mehr in derselben SQLite-Datei (`kurs`, `serie`, `termin`, `anmeldung`). Die Anmeldestrecke ist der **dritte** öffentlich erreichbare Bereich neben Werkstatt und Portal und bekommt denselben Zuschnitt wie das Portal: eigene Seiten, eigene Routen, kein Zugriff auf Werkstatt-Fähigkeiten. Mailversand über `smtplib` aus der Standardbibliothek. Bezahlt wird per Rechnung, freigeschaltet von Hand — die Anmeldung erzeugt einen Teilnehmer ohne Zugang, den Rest macht die bestehende Verwaltung aus Etappe 4.

**Tech Stack:** Python 3.11, FastAPI, `sqlite3` + `smtplib` + `email.message` aus der Standardbibliothek, Vanilla JS ohne Build.

## Global Constraints

- UI-Texte, Doku und Kommentare **auf Deutsch**; Code-Identifier englisch.
- **Keine neuen Laufzeit-Dependencies.** `smtplib`, `ssl`, `email.message` sind Standardbibliothek.
- Kein Framework im Frontend.
- Fehlerfälle: 404 unbekannt, 409 Konflikt, 400 Validierung, 403 abgelaufen.
- **Nach außen nie Zahlen.** Die öffentliche Antwort nennt „offen" oder „ausgebucht", niemals freie oder belegte Plätze — auch nicht in einer Fehlermeldung. Wer die Auslastung kennt, kennt den Umsatz.
- Frontend bei **390 px und 320 px** ohne horizontalen Überlauf; Flex-Zeilen brauchen `flex-wrap`.
- `hidden` allein versteckt nichts: zu jeder neuen CSS-Regel mit eigenem `display` gehört eine `[hidden]`-Variante.
- Nach jeder Frontend-Änderung `?v=` in `static/index.html` für **beide** Assets hochzählen.
- Kein Test fasst den echten `projects/`-Ordner an, startet einen echten Agenten, schreibt in die echte `data/kurse.db` oder **verschickt eine echte Mail**.
- Die Prüfung wird serverseitig ausgewertet; die Lösungen verlassen den Server nie. Unverändert aus Etappe 5.
- Zugangsdaten (SMTP-Passwort) leben in `config.json`, das gitignored ist. Niemals in einen Test, ein Log oder eine Fehlermeldung.

## Der Zuschnitt, an dem alles hängt

Die App hat nach diesem Plan **drei** Bereiche mit drei verschiedenen Schutzmodellen:

| Bereich | Pfade | Schutz |
|---|---|---|
| Werkstatt | `/`, `/api/projekte*`, `/api/praesentationen*`, `/api/config*`, `/api/verwaltung*` | Cloudflare Access, nur Matthias |
| Portal | `/portal*` | eigenes Login, scrypt + Sitzungscookie |
| **Anmeldung (neu)** | `/anmeldung*`, `/api/anmeldung*` | **keiner** — öffentlich, das ist der Zweck |

Der dritte Bereich ist neu und der heikelste: Er nimmt Eingaben von Fremden entgegen, auf einem Dienst, der Agenten mit Bash-Rechten startet. Deshalb gilt für ihn:

- **Nur die Endpunkte, die er braucht.** Kein Zugriff auf Kurs-Bearbeitung, keine Teilnehmerliste, keine Projektdaten.
- **Eine Rate-Begrenzung**, sonst ist das Formular ein Mailversand-Werkzeug für Dritte.
- **Keine Zahlen nach außen** (siehe Global Constraints).
- Alles, was hereinkommt, ist unvertrauenswürdig — Länge begrenzen, escapen, in Mails nicht als Header verwenden.

---

## File Structure

| Datei | Verantwortung | Status |
|---|---|---|
| `app/db.py` | + vier Tabellen im Schema | ändern |
| `app/kurse.py` | Kurse, Serien, Termine: anlegen, ändern, Termine erzeugen, Platzstand | neu |
| `app/anmeldung.py` | Anmeldungen entgegennehmen, Platzprüfung, Statuswechsel | neu |
| `app/mail.py` | SMTP-Versand, Vorlagen — kennt weder DB noch HTTP | neu |
| `app/anmeldung_seiten.py` | die öffentlichen Seiten als HTML | neu |
| `app/anmeldung_routes.py` | die öffentlichen Routen samt Rate-Begrenzung | neu |
| `app/verwaltung.py` | + Kurse, Serien, Termine, Anmeldungen verwalten | ändern |
| `app/config.py` | + SMTP-Einstellungen | ändern |
| `app/preflight.py` | + Kachel „Mailversand" | ändern |
| `app/main.py` | bindet den neuen Router ein | ändern |
| `static/index.html`, `app.js`, `style.css` | Reiter „Kurse" und „Anmeldungen" | ändern |
| `tests/test_kurse.py`, `test_anmeldung.py`, `test_mail.py`, `test_anmeldung_routes.py` | je Modul | neu |

`app/anmeldung_seiten.py` und `app/anmeldung_routes.py` sind getrennt, wie `portal.py`/`portal_routes.py` — Seiten sind reine Funktionen von Daten zu HTML und ohne Server testbar.

---

## Das Datenmodell

```sql
CREATE TABLE kurs (
    id            INTEGER PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,      -- URL-Teil, [a-z0-9-]
    titel         TEXT NOT NULL,
    beschreibung  TEXT NOT NULL DEFAULT '',
    format        TEXT NOT NULL DEFAULT '',  -- „online mit Trainer, ca. 4 Std"
    preis_cent    INTEGER NOT NULL DEFAULT 0,
    preis_pauschal INTEGER NOT NULL DEFAULT 0,  -- 0 = pro Person, 1 = Gesamtpreis
    plaetze       INTEGER NOT NULL DEFAULT 10,
    nachweis      TEXT NOT NULL DEFAULT 'Teilnahmebestätigung',
    schulung_slug TEXT NOT NULL DEFAULT '',  -- Projektordner, für die Teilnahme
    aktiv         INTEGER NOT NULL DEFAULT 1,
    angelegt_am   TEXT NOT NULL
);

CREATE TABLE serie (
    id         INTEGER PRIMARY KEY,
    kurs_id    INTEGER NOT NULL REFERENCES kurs(id) ON DELETE CASCADE,
    wochentag  INTEGER NOT NULL,          -- 0 = Montag … 6 = Sonntag
    uhrzeit    TEXT NOT NULL,             -- „09:00"
    dauer_tage INTEGER NOT NULL DEFAULT 1,
    rhythmus   INTEGER NOT NULL DEFAULT 1, -- alle N Wochen
    aktiv      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE termin (
    id        INTEGER PRIMARY KEY,
    kurs_id   INTEGER NOT NULL REFERENCES kurs(id) ON DELETE CASCADE,
    serie_id  INTEGER REFERENCES serie(id) ON DELETE SET NULL,
    beginn    TEXT NOT NULL,              -- ISO, Ortszeit-naiv
    ende      TEXT NOT NULL,
    plaetze   INTEGER NOT NULL,           -- Kopie aus kurs zum Zeitpunkt der Erzeugung
    status    TEXT NOT NULL DEFAULT 'offen',  -- offen | geschlossen | abgesagt
    UNIQUE (kurs_id, beginn)
);

CREATE TABLE anmeldung (
    id           INTEGER PRIMARY KEY,
    termin_id    INTEGER REFERENCES termin(id) ON DELETE SET NULL,
    kurs_id      INTEGER NOT NULL REFERENCES kurs(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL,
    firma        TEXT NOT NULL DEFAULT '',
    nachricht    TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'neu',  -- neu | bestaetigt | bezahlt | storniert
    teilnehmer_id INTEGER REFERENCES teilnehmer(id) ON DELETE SET NULL,
    angelegt_am  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_termin_kurs ON termin(kurs_id, beginn);
CREATE INDEX IF NOT EXISTS idx_anmeldung_termin ON anmeldung(termin_id);
```

**Warum `termin.plaetze` eine Kopie ist:** Ändert jemand die Platzzahl am Kurs, dürfen bereits ausgeschriebene Termine nicht rückwirkend überbucht oder unterbelegt sein. Der Termin hält fest, was zum Zeitpunkt seiner Erzeugung galt.

**Warum `anmeldung.termin_id` NULL sein darf:** Das E-Learning nach Art. 4 ist terminlos. Eine Anmeldung ohne Termin ist gültig und bezieht sich nur auf den Kurs.

**Warum `teilnehmer_id` auf der Anmeldung liegt:** Sie ist die Brücke zu Etappe 4. Eine bezahlte Anmeldung wird zu einem Teilnehmer mit Teilnahme; danach zeigt die Anmeldung darauf und der Verwaltungsbildschirm kann beides nebeneinander zeigen.

---

# Etappe 6 — Kurse, Termine, Anmeldung

### Task 1: Schema erweitern

**Files:**
- Modify: `app/db.py`
- Test: `tests/test_db_kurse.py`

**Interfaces:**
- Produces: die vier Tabellen oben, über das bestehende `schema_anlegen()`

- [ ] **Step 1: Den Test schreiben**

`tests/test_db_kurse.py`:
```python
"""Die Tabellen der Kursverwaltung."""

import sqlite3

import pytest

from app import db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    c = db.verbinden()
    db.schema_anlegen(c)
    yield c
    c.close()


def _kurs(conn, slug="ki-pflicht"):
    conn.execute(
        "INSERT INTO kurs (slug, titel, angelegt_am) VALUES (?, ?, ?)",
        (slug, "KI-Pflichtschulung", "2026-08-09T10:00:00+00:00"))
    return conn.execute("SELECT id FROM kurs WHERE slug = ?", (slug,)).fetchone()["id"]


def test_alle_neuen_tabellen_existieren(conn):
    namen = {z["name"] for z in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"kurs", "serie", "termin", "anmeldung"} <= namen


def test_kurs_slug_ist_eindeutig(conn):
    _kurs(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _kurs(conn)


def test_kurs_hat_sinnvolle_vorgaben(conn):
    kid = _kurs(conn)
    k = conn.execute("SELECT * FROM kurs WHERE id = ?", (kid,)).fetchone()
    assert k["plaetze"] == 10
    assert k["preis_pauschal"] == 0
    assert k["nachweis"] == "Teilnahmebestätigung"
    assert k["aktiv"] == 1


def test_termine_verschwinden_mit_dem_kurs(conn):
    kid = _kurs(conn)
    conn.execute(
        "INSERT INTO termin (kurs_id, beginn, ende, plaetze) VALUES (?, ?, ?, ?)",
        (kid, "2026-09-02T09:00:00", "2026-09-02T13:00:00", 10))
    conn.execute("DELETE FROM kurs WHERE id = ?", (kid,))
    assert conn.execute("SELECT count(*) AS n FROM termin").fetchone()["n"] == 0


def test_derselbe_kurs_nicht_zweimal_zur_selben_zeit(conn):
    kid = _kurs(conn)
    for _ in range(2):
        try:
            conn.execute(
                "INSERT INTO termin (kurs_id, beginn, ende, plaetze) VALUES (?, ?, ?, ?)",
                (kid, "2026-09-02T09:00:00", "2026-09-02T13:00:00", 10))
        except sqlite3.IntegrityError:
            return
    pytest.fail("Der zweite Termin zur selben Zeit hätte scheitern müssen")


def test_anmeldung_ohne_termin_ist_erlaubt(conn):
    # Das E-Learning nach Art. 4 ist terminlos.
    kid = _kurs(conn)
    conn.execute(
        "INSERT INTO anmeldung (kurs_id, name, email, angelegt_am) "
        "VALUES (?, ?, ?, ?)",
        (kid, "Anna", "anna@example.org", "2026-08-09T10:00:00+00:00"))
    a = conn.execute("SELECT * FROM anmeldung").fetchone()
    assert a["termin_id"] is None
    assert a["status"] == "neu"


def test_abgesagter_termin_laesst_die_anmeldung_stehen(conn):
    # Sonst verschwindet die Historie, wer sich angemeldet hatte.
    kid = _kurs(conn)
    conn.execute(
        "INSERT INTO termin (kurs_id, beginn, ende, plaetze) VALUES (?, ?, ?, ?)",
        (kid, "2026-09-02T09:00:00", "2026-09-02T13:00:00", 10))
    tid = conn.execute("SELECT id FROM termin").fetchone()["id"]
    conn.execute(
        "INSERT INTO anmeldung (termin_id, kurs_id, name, email, angelegt_am) "
        "VALUES (?, ?, ?, ?, ?)",
        (tid, kid, "Anna", "anna@example.org", "2026-08-09T10:00:00+00:00"))

    conn.execute("DELETE FROM termin WHERE id = ?", (tid,))
    a = conn.execute("SELECT * FROM anmeldung").fetchone()
    assert a is not None
    assert a["termin_id"] is None
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_db_kurse.py -v`
Expected: FAIL — die Tabellen gibt es noch nicht.

- [ ] **Step 3: Implementieren**

In `app/db.py` an die `SCHEMA`-Zeichenkette anhängen — genau die vier `CREATE TABLE` und die zwei `CREATE INDEX` aus dem Abschnitt „Das Datenmodell" oben, jeweils mit `IF NOT EXISTS`. Die Kommentare aus dem Abschnitt („Warum `termin.plaetze` eine Kopie ist", „Warum `termin_id` NULL sein darf") gehören als SQL-Kommentare mit ins Schema — sie erklären Entscheidungen, die man dem DDL sonst nicht ansieht.

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_db_kurse.py -v`
Expected: 7 passed.

- [ ] **Step 5: Volle Suite und Commit**

Run: `.venv/bin/python -m pytest -q` — 278 + 7 = 285.

```bash
git add app/db.py tests/test_db_kurse.py
git commit -m "feat: Schema fuer Kurse, Serien, Termine und Anmeldungen"
```

---

### Task 2: Kurse und Termine

**Files:**
- Create: `app/kurse.py`, `tests/test_kurse.py`

**Interfaces:**
- Consumes: `app.db.verbinden()`, `app.projekte.projekt_dir()`
- Produces:
  - `app.kurse.KursFehler(ValueError)`
  - `anlegen(slug, titel, **felder) -> int`
  - `aendern(kurs_id, **felder) -> None`
  - `liste(nur_aktive: bool = False) -> list[dict]`
  - `kurs(kurs_id: int) -> dict | None`, `kurs_nach_slug(slug: str) -> dict | None`
  - `serie_anlegen(kurs_id, wochentag, uhrzeit, dauer_tage=1, rhythmus=1) -> int`
  - `termine_erzeugen(serie_id: int, bis: date) -> int` — Anzahl neu erzeugter Termine
  - `termine(kurs_id: int | None = None, ab: datetime | None = None) -> list[dict]` — je Termin mit `belegt` und `frei`
  - `termin(termin_id: int) -> dict | None`
  - `termin_status(termin_id: int, status: str) -> None`
  - `naechste_offene(kurs_id: int, anzahl: int = 4) -> list[dict]` — **ohne** Platzzahlen

- [ ] **Step 1: Den Test schreiben**

`tests/test_kurse.py`:
```python
"""Kurse, Serien und Termine."""

from datetime import date, datetime, timedelta

import pytest

from app import db, kurse


@pytest.fixture
def datenbank(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()
    return db.DB_PFAD


def test_anlegen_und_lesen(datenbank):
    kid = kurse.anlegen("ki-pflicht", "KI-Pflichtschulung",
                        preis_cent=14900, plaetze=20)
    k = kurse.kurs(kid)
    assert k["slug"] == "ki-pflicht"
    assert k["preis_cent"] == 14900
    assert k["plaetze"] == 20


def test_slug_wird_normalisiert_und_geprueft(datenbank):
    kid = kurse.anlegen("  KI-Pflicht  ", "Titel")
    assert kurse.kurs(kid)["slug"] == "ki-pflicht"
    with pytest.raises(kurse.KursFehler):
        kurse.anlegen("nicht erlaubt!", "Titel")


def test_doppelter_slug_wird_abgewiesen(datenbank):
    kurse.anlegen("ki-pflicht", "Titel")
    with pytest.raises(kurse.KursFehler, match="bereits"):
        kurse.anlegen("ki-pflicht", "Anderer Titel")


def test_titel_ist_pflicht(datenbank):
    with pytest.raises(kurse.KursFehler):
        kurse.anlegen("slug", "   ")


def test_pauschalpreis_ist_moeglich(datenbank):
    # Die Masterclass kostet 3.999 EUR gesamt für bis zu drei Personen.
    kid = kurse.anlegen("masterclass", "Agentic-Coding-Masterclass",
                        preis_cent=399900, preis_pauschal=True, plaetze=3)
    assert kurse.kurs(kid)["preis_pauschal"] == 1


def test_aendern_setzt_nur_die_genannten_felder(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    kurse.aendern(kid, titel="Neuer Titel")
    k = kurse.kurs(kid)
    assert k["titel"] == "Neuer Titel"
    assert k["plaetze"] == 10


def test_aendern_eines_unbekannten_kurses_wirft(datenbank):
    with pytest.raises(kurse.KursFehler, match="nicht gefunden"):
        kurse.aendern(999, titel="X")


def test_liste_kann_auf_aktive_filtern(datenbank):
    kurse.anlegen("a", "A")
    kid = kurse.anlegen("b", "B")
    kurse.aendern(kid, aktiv=False)
    assert len(kurse.liste()) == 2
    assert [k["slug"] for k in kurse.liste(nur_aktive=True)] == ["a"]


def test_serie_erzeugt_termine_im_rhythmus(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    # Mittwochs, 14-tägig
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00", rhythmus=2)
    anzahl = kurse.termine_erzeugen(sid, bis=date(2026, 10, 1))

    t = kurse.termine(kid)
    assert anzahl == len(t)
    assert all(datetime.fromisoformat(x["beginn"]).weekday() == 2 for x in t)
    abstaende = {(datetime.fromisoformat(b["beginn"])
                  - datetime.fromisoformat(a["beginn"])).days
                 for a, b in zip(t, t[1:])}
    assert abstaende == {14}


def test_termine_erzeugen_ist_wiederholbar(datenbank):
    # Zweimal aufgerufen darf keine Dubletten anlegen.
    kid = kurse.anlegen("ki-pflicht", "Titel")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    erst = kurse.termine_erzeugen(sid, bis=date(2026, 10, 1))
    zweit = kurse.termine_erzeugen(sid, bis=date(2026, 10, 1))
    assert erst > 0
    assert zweit == 0
    assert len(kurse.termine(kid)) == erst


def test_mehrtaegiger_termin_endet_spaeter(datenbank):
    # Die Masterclass läuft vier Tage.
    kid = kurse.anlegen("masterclass", "Titel", plaetze=3)
    sid = kurse.serie_anlegen(kid, wochentag=0, uhrzeit="09:00", dauer_tage=4)
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    t = kurse.termine(kid)[0]
    dauer = datetime.fromisoformat(t["ende"]) - datetime.fromisoformat(t["beginn"])
    assert dauer.days == 3  # vier Kalendertage, drei Nächte


def test_termin_uebernimmt_die_platzzahl_des_kurses(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=7)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    assert kurse.termine(kid)[0]["plaetze"] == 7


def test_platzaenderung_wirkt_nicht_rueckwirkend(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=7)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    kurse.aendern(kid, plaetze=99)
    assert kurse.termine(kid)[0]["plaetze"] == 7


def test_termine_nennen_belegung_und_freie_plaetze(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    t = kurse.termine(kid)[0]
    assert t["belegt"] == 0
    assert t["frei"] == 10


def test_status_setzen(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    tid = kurse.termine(kid)[0]["id"]

    kurse.termin_status(tid, "abgesagt")
    assert kurse.termin(tid)["status"] == "abgesagt"
    with pytest.raises(kurse.KursFehler):
        kurse.termin_status(tid, "quatsch")


def test_naechste_offene_nennt_keine_zahlen(datenbank):
    """Nach außen nie Zahlen — nur offen oder ausgebucht."""
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 12, 31))

    offen = kurse.naechste_offene(kid)
    assert len(offen) <= 4
    for t in offen:
        assert "plaetze" not in t
        assert "belegt" not in t
        assert "frei" not in t
        assert t["status"] in ("offen", "ausgebucht")


def test_naechste_offene_ueberspringt_vergangene_und_abgesagte(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 12, 31))
    alle = kurse.termine(kid)
    kurse.termin_status(alle[0]["id"], "abgesagt")

    ids = {t["id"] for t in kurse.naechste_offene(kid, anzahl=99)}
    assert alle[0]["id"] not in ids
    jetzt = datetime.now()
    assert all(datetime.fromisoformat(t["beginn"]) > jetzt
               for t in kurse.naechste_offene(kid, anzahl=99))
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_kurse.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.kurse'`.

- [ ] **Step 3: Implementieren**

`app/kurse.py`. Die tragenden Punkte:

```python
"""Kurse, Terminserien und Termine.

Ein Kurs ist das Angebot, eine Serie die Regel („mittwochs, 14-tägig"), ein
Termin die einzelne Durchführung. Termine werden aus der Serie erzeugt und
halten die Platzzahl fest, die zum Zeitpunkt der Erzeugung galt — sonst
würde eine spätere Änderung am Kurs bereits ausgeschriebene Termine
rückwirkend überbuchen.
"""

import re
import sqlite3
from datetime import date, datetime, time, timedelta

from . import db

STATUS = ("offen", "geschlossen", "abgesagt")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Welche Felder `anlegen`/`aendern` annehmen. Alles andere wird abgewiesen,
# damit ein Tippfehler nicht stillschweigend ins Leere läuft.
FELDER = ("titel", "beschreibung", "format", "preis_cent", "preis_pauschal",
          "plaetze", "nachweis", "schulung_slug", "aktiv")


class KursFehler(ValueError):
    """Eingabe oder Zustand passt nicht. Die Meldung ist für die Oberfläche."""
```

`termine_erzeugen(serie_id, bis)` geht vom **nächsten** passenden Wochentag ab heute in Schritten von `rhythmus` Wochen bis `bis`, berechnet `ende = beginn + (dauer_tage - 1) Tage + 4 Stunden` und fügt mit `INSERT OR IGNORE` ein — der `UNIQUE (kurs_id, beginn)` macht den wiederholten Aufruf damit folgenlos. Rückgabe ist die Zahl der tatsächlich eingefügten Zeilen (`cur.rowcount` summiert).

`termine()` liefert je Termin zusätzlich `belegt` (Anmeldungen mit Status ungleich `storniert`) und `frei` (`plaetze - belegt`) über ein `LEFT JOIN` mit `GROUP BY`.

`naechste_offene()` ist die **einzige** Funktion, die für die Öffentlichkeit gedacht ist. Sie liefert `id`, `beginn`, `ende` und ein `status`-Feld, das nur `offen` oder `ausgebucht` enthält — die Zahlen bleiben drin. Ein eigener Test hält fest, dass keine Platzangabe durchrutscht.

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_kurse.py -v`
Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add app/kurse.py tests/test_kurse.py
git commit -m "feat: Kurse, Terminserien und Termine"
```

---

### Task 3: Anmeldungen

**Files:**
- Create: `app/anmeldung.py`, `tests/test_anmeldung.py`

**Interfaces:**
- Consumes: `app.db.verbinden()`, `app.kurse.*`, `app.teilnehmer.*`
- Produces:
  - `app.anmeldung.AnmeldungFehler(ValueError)`
  - `STATUS = ("neu", "bestaetigt", "bezahlt", "storniert")`
  - `MAX_NACHRICHT = 2000`
  - `annehmen(kurs_id, termin_id, name, email, firma="", nachricht="") -> int`
  - `liste(status: str | None = None) -> list[dict]` — je Eintrag zusätzlich `kurs_titel` und `beginn` (`None` bei terminloser Anmeldung), damit die Verwaltung in Task 7 nicht nachladen muss
  - `eintrag(anmeldung_id: int) -> dict | None`
  - `status_setzen(anmeldung_id: int, status: str) -> None`
  - `zu_teilnehmer(anmeldung_id: int) -> tuple[int, str]` — (teilnehmer_id, Passwort im Klartext)

- [ ] **Step 1: Den Test schreiben**

`tests/test_anmeldung.py`:
```python
"""Anmeldungen entgegennehmen und weiterverarbeiten."""

import json
from datetime import date

import pytest

from app import anmeldung, db, kurse, projekte, teilnehmer

PRUEFUNG = {"titel": "Abschlussprüfung", "bestehensgrenze": 70,
            "fragen": [{"frage": "F?", "optionen": ["a", "b", "c"],
                        "richtig": 0, "thema": "Level 1", "hinweis": "Weil a."}]}


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    ziel = tmp_path / "projects"
    ziel.mkdir()
    monkeypatch.setattr(projekte, "PROJECTS", ziel)
    db.init()

    d = ziel / "ki-pflicht"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "KI-Pflichtschulung"}))
    (d / "status.json").write_text(json.dumps({"phase": "fertig"}))
    (d / "pruefung.json").write_text(json.dumps(PRUEFUNG), encoding="utf-8")

    kid = kurse.anlegen("ki-pflicht", "KI-Pflichtschulung", plaetze=2,
                        schulung_slug="ki-pflicht",
                        nachweis="AI-SmartCon-Zertifikat")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 12, 31))
    return {"kurs": kid, "termin": kurse.termine(kid)[0]["id"]}


def test_annehmen_legt_an(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                             "Anna Beispiel", "anna@example.org", "Beispiel GmbH")
    e = anmeldung.eintrag(aid)
    assert e["name"] == "Anna Beispiel"
    assert e["email"] == "anna@example.org"
    assert e["status"] == "neu"


def test_email_wird_normalisiert_und_geprueft(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "  Anna@EXAMPLE.org ")
    assert anmeldung.eintrag(aid)["email"] == "anna@example.org"
    with pytest.raises(anmeldung.AnmeldungFehler, match="E-Mail"):
        anmeldung.annehmen(umgebung["kurs"], None, "Anna", "keine-mail")


def test_name_ist_pflicht(umgebung):
    with pytest.raises(anmeldung.AnmeldungFehler):
        anmeldung.annehmen(umgebung["kurs"], None, "  ", "anna@example.org")


def test_zu_lange_nachricht_wird_abgewiesen(umgebung):
    with pytest.raises(anmeldung.AnmeldungFehler, match="lang"):
        anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org",
                           nachricht="x" * (anmeldung.MAX_NACHRICHT + 1))


def test_unbekannter_kurs_wird_abgewiesen(umgebung):
    with pytest.raises(anmeldung.AnmeldungFehler, match="nicht gefunden"):
        anmeldung.annehmen(999, None, "Anna", "anna@example.org")


def test_termin_muss_zum_kurs_gehoeren(umgebung):
    anderer = kurse.anlegen("anderer", "Anderer Kurs")
    with pytest.raises(anmeldung.AnmeldungFehler, match="gehört nicht"):
        anmeldung.annehmen(anderer, umgebung["termin"], "Anna", "anna@example.org")


def test_terminlose_anmeldung_ist_erlaubt(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")
    assert anmeldung.eintrag(aid)["termin_id"] is None


def test_ausgebuchter_termin_wird_abgewiesen(umgebung):
    for i in range(2):  # plaetze=2
        anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                           f"Person {i}", f"p{i}@example.org")
    with pytest.raises(anmeldung.AnmeldungFehler, match="ausgebucht"):
        anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                           "Zuspaet", "spaet@example.org")


def test_die_absage_nennt_keine_zahlen(umgebung):
    """Nach außen nie Zahlen — auch nicht in einer Fehlermeldung."""
    for i in range(2):
        anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                           f"P{i}", f"p{i}@example.org")
    with pytest.raises(anmeldung.AnmeldungFehler) as fehler:
        anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                           "Zuspaet", "spaet@example.org")
    text = str(fehler.value)
    assert "2" not in text and "0" not in text


def test_stornierte_geben_den_platz_frei(umgebung):
    ids = [anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                              f"P{i}", f"p{i}@example.org") for i in range(2)]
    anmeldung.status_setzen(ids[0], "storniert")
    neu = anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                             "Nachrueckerin", "n@example.org")
    assert anmeldung.eintrag(neu) is not None


def test_geschlossener_termin_nimmt_nichts_an(umgebung):
    kurse.termin_status(umgebung["termin"], "geschlossen")
    with pytest.raises(anmeldung.AnmeldungFehler):
        anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                           "Anna", "anna@example.org")


def test_status_setzen_prueft_den_wert(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")
    anmeldung.status_setzen(aid, "bezahlt")
    assert anmeldung.eintrag(aid)["status"] == "bezahlt"
    with pytest.raises(anmeldung.AnmeldungFehler):
        anmeldung.status_setzen(aid, "quatsch")


def test_liste_kann_nach_status_filtern(umgebung):
    a = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")
    anmeldung.annehmen(umgebung["kurs"], None, "Bodo", "bodo@example.org")
    anmeldung.status_setzen(a, "bezahlt")
    assert len(anmeldung.liste()) == 2
    assert [e["name"] for e in anmeldung.liste(status="bezahlt")] == ["Anna"]


def test_liste_nennt_kurs_und_termin(umgebung):
    """Die Verwaltung zeigt beides nebeneinander und soll nicht nachladen müssen."""
    anmeldung.annehmen(umgebung["kurs"], umgebung["termin"], "Anna",
                       "anna@example.org")
    anmeldung.annehmen(umgebung["kurs"], None, "Bodo", "bodo@example.org")
    nach_name = {e["name"]: e for e in anmeldung.liste()}
    assert nach_name["Anna"]["kurs_titel"] == "KI-Pflichtschulung"
    assert nach_name["Anna"]["beginn"] is not None
    assert nach_name["Bodo"]["beginn"] is None
    assert nach_name["Bodo"]["teilnehmer_id"] is None


def test_zu_teilnehmer_legt_an_und_verknuepft(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                             "Anna Beispiel", "anna@example.org", "Beispiel GmbH")
    anmeldung.status_setzen(aid, "bezahlt")

    tid, passwort = anmeldung.zu_teilnehmer(aid)
    assert len(passwort) == 12
    assert anmeldung.eintrag(aid)["teilnehmer_id"] == tid

    t = [x for x in teilnehmer.liste() if x["id"] == tid][0]
    assert t["email"] == "anna@example.org"
    assert t["firma"] == "Beispiel GmbH"
    assert t["hat_zugang"] is True
    assert t["teilnahmen"][0]["slug"] == "ki-pflicht"
    assert t["teilnahmen"][0]["nachweis"] == "AI-SmartCon-Zertifikat"


def test_zu_teilnehmer_nur_bei_bezahlt(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")
    with pytest.raises(anmeldung.AnmeldungFehler, match="bezahlt"):
        anmeldung.zu_teilnehmer(aid)


def test_zu_teilnehmer_nur_einmal(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")
    anmeldung.status_setzen(aid, "bezahlt")
    anmeldung.zu_teilnehmer(aid)
    with pytest.raises(anmeldung.AnmeldungFehler, match="bereits"):
        anmeldung.zu_teilnehmer(aid)


def test_zu_teilnehmer_ohne_schulung_wirft(umgebung):
    kid = kurse.anlegen("ohne-schulung", "Kurs ohne Schulung")
    aid = anmeldung.annehmen(kid, None, "Anna", "anna@example.org")
    anmeldung.status_setzen(aid, "bezahlt")
    with pytest.raises(anmeldung.AnmeldungFehler, match="Schulung"):
        anmeldung.zu_teilnehmer(aid)


def test_zweiter_kurs_fuer_dieselbe_person(umgebung):
    """Wer schon Teilnehmer ist, bekommt die zweite Teilnahme, kein zweites Konto."""
    kid2 = kurse.anlegen("zweiter", "Zweiter Kurs", schulung_slug="ki-pflicht")
    a1 = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")
    anmeldung.status_setzen(a1, "bezahlt")
    tid1, _ = anmeldung.zu_teilnehmer(a1)

    a2 = anmeldung.annehmen(kid2, None, "Anna", "anna@example.org")
    anmeldung.status_setzen(a2, "bezahlt")
    tid2, _ = anmeldung.zu_teilnehmer(a2)
    assert tid2 == tid1
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_anmeldung.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.anmeldung'`.

- [ ] **Step 3: Implementieren**

`app/anmeldung.py`. Die Punkte, die Aufmerksamkeit brauchen:

**Die Platzprüfung ist eine Prüf-dann-Schreib-Stelle** und muss in `BEGIN IMMEDIATE`. Ohne das können zwei gleichzeitige Anmeldungen beide den letzten Platz bekommen — genau der Fehler, den `versuche.starten()` in der letzten Etappe hatte. `db.verbinden()` ist Autocommit, `with conn:` hilft nicht.

**Die Absage nennt keine Zahlen.** „Dieser Termin ist ausgebucht." — nicht „nur noch 0 von 10 Plätzen".

**`zu_teilnehmer()` ist die Brücke zu Etappe 4** und macht drei Dinge in einer Transaktion: Teilnehmer anlegen (oder den vorhandenen mit dieser E-Mail nehmen), Teilnahme auf `kurs.schulung_slug` anlegen, Anmeldung verknüpfen. Danach `teilnehmer.freischalten()`, was das Passwort erzeugt. Ein Kurs ohne `schulung_slug` kann das nicht — dann eine Meldung, die sagt, was fehlt.

**`liste()` joint mit** `LEFT JOIN kurs ON kurs.id = anmeldung.kurs_id` und `LEFT JOIN termin ON termin.id = anmeldung.termin_id` und liefert `kurs.titel AS kurs_titel` sowie `termin.beginn AS beginn` mit — die Verwaltung soll für eine Liste nicht je Zeile nachladen. Sortierung: neueste zuerst (`ORDER BY angelegt_am DESC, id DESC`).

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_anmeldung.py -v`
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add app/anmeldung.py tests/test_anmeldung.py
git commit -m "feat: Anmeldungen mit Platzpruefung und Bruecke zum Teilnehmer"
```

---

### Task 4: Mailversand

**Files:**
- Create: `app/mail.py`, `tests/test_mail.py`
- Modify: `app/config.py`, `app/preflight.py`

**Interfaces:**
- Produces:
  - `app.mail.MailFehler(RuntimeError)`
  - `app.mail.konfiguriert() -> bool`
  - `app.mail.senden(an: str, betreff: str, text: str) -> None`
  - `app.mail.anmeldung_eingegangen(eintrag: dict, kurs: dict, termin: dict | None) -> tuple[str, str]` — (Betreff, Text)
  - `app.mail.zugang_freigeschaltet(eintrag: dict, kurs: dict, passwort: str, portal_url: str) -> tuple[str, str]`
  - Konfigurationsschlüssel `smtp_host`, `smtp_port`, `smtp_user`, `smtp_passwort`, `smtp_von`, `smtp_starttls`, `portal_url`

- [ ] **Step 1: Den Test schreiben**

`tests/test_mail.py`:
```python
"""Mailversand und Vorlagen. Verschickt in Tests nie etwas."""

import pytest

from app import config, mail

EINTRAG = {"name": "Anna Beispiel", "email": "anna@example.org",
           "firma": "Beispiel GmbH", "nachricht": ""}
KURS = {"titel": "KI-Pflichtschulung", "format": "E-Learning, 80–90 Min",
        "preis_cent": 14900, "preis_pauschal": 0}
TERMIN = {"beginn": "2026-09-02T09:00:00", "ende": "2026-09-02T13:00:00"}


def test_ohne_host_ist_nichts_konfiguriert(monkeypatch):
    monkeypatch.setattr(config, "load", lambda: {**config.DEFAULTS, "smtp_host": ""})
    assert mail.konfiguriert() is False


def test_mit_host_ist_es_konfiguriert(monkeypatch):
    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "smtp_host": "mail.example.org",
                                 "smtp_von": "kurse@example.org"})
    assert mail.konfiguriert() is True


def test_senden_ohne_konfiguration_wirft(monkeypatch):
    monkeypatch.setattr(config, "load", lambda: {**config.DEFAULTS, "smtp_host": ""})
    with pytest.raises(mail.MailFehler, match="nicht eingerichtet"):
        mail.senden("anna@example.org", "Betreff", "Text")


def test_bestaetigung_nennt_kurs_und_termin():
    betreff, text = mail.anmeldung_eingegangen(EINTRAG, KURS, TERMIN)
    assert "KI-Pflichtschulung" in betreff
    assert "Anna Beispiel" in text
    assert "02.09.2026" in text
    assert "149,00" in text


def test_bestaetigung_ohne_termin_sagt_das():
    betreff, text = mail.anmeldung_eingegangen(EINTRAG, KURS, None)
    assert "jederzeit" in text.lower() or "ohne festen Termin" in text


def test_pauschalpreis_wird_als_gesamtpreis_ausgewiesen():
    kurs = {**KURS, "preis_cent": 399900, "preis_pauschal": 1}
    _, text = mail.anmeldung_eingegangen(EINTRAG, kurs, None)
    assert "3.999,00" in text
    assert "gesamt" in text.lower()


def test_zugangsmail_enthaelt_passwort_und_adresse():
    betreff, text = mail.zugang_freigeschaltet(
        EINTRAG, KURS, "Abc23xyzQ7mn", "https://kurse.ai-smartcon.de/portal")
    assert "Abc23xyzQ7mn" in text
    assert "https://kurse.ai-smartcon.de/portal" in text
    assert "anna@example.org" in text


def test_keine_mail_behauptet_staatliche_anerkennung():
    for bauen in (lambda: mail.anmeldung_eingegangen(EINTRAG, KURS, TERMIN),
                  lambda: mail.zugang_freigeschaltet(EINTRAG, KURS, "x", "u")):
        _, text = bauen()
        for verboten in ("staatlich anerkannt", "azav", "bildungsgutschein"):
            assert verboten not in text.lower()


def test_kopfzeilen_koennen_nicht_eingeschleust_werden(monkeypatch):
    """Ein Zeilenumbruch im Namen darf keine zusätzliche Kopfzeile erzeugen."""
    gesendet = {}

    class FakeSMTP:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, **kw): pass
        def login(self, *a): pass
        def send_message(self, nachricht):
            gesendet["nachricht"] = nachricht

    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "smtp_host": "mail.example.org",
                                 "smtp_von": "kurse@example.org"})
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)

    mail.senden("anna@example.org\nBcc: fremd@example.org", "Betreff", "Text")
    an = str(gesendet["nachricht"]["To"])
    assert "\n" not in an and "\r" not in an
    assert gesendet["nachricht"]["Bcc"] is None
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_mail.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.mail'`.

- [ ] **Step 3: Implementieren**

`app/mail.py`:

```python
"""Mailversand über SMTP und die Vorlagen dafür.

Standardbibliothek: smtplib, ssl, email.message. Kein Dienstleister, kein
Webhook — die App bleibt eigenständig lauffähig, und die Zustellbarkeit hängt
am Postfach von ai-smartcon.de.

`EmailMessage.__setitem__` weist Zeilenumbrüche in Kopfzeilen zurück, was
Header-Injection über einen Namen oder eine Adresse ausschließt. Der
zusätzliche Riegel unten ist trotzdem da: Er macht die Absicht sichtbar und
überlebt einen Umbau auf eine andere Bibliothek.
"""

import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from . import config

_ZEILENUMBRUCH = re.compile(r"[\r\n]")


class MailFehler(RuntimeError):
    """Versand nicht möglich. Die Meldung ist für die Oberfläche."""
```

`senden()` baut eine `EmailMessage`, setzt `From`/`To`/`Subject` **nach** `_ZEILENUMBRUCH.sub("", …)`, verbindet über `smtplib.SMTP` mit `starttls(context=ssl.create_default_context())` (bzw. `SMTP_SSL` bei Port 465), meldet sich an, wenn ein Benutzer konfiguriert ist, und schickt. Jede `smtplib`- oder `OSError`-Ausnahme wird zu `MailFehler` mit dem Servertext — **ohne das Passwort**.

Preise werden als `f"{cent/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")` deutsch formatiert; bei `preis_pauschal` steht „gesamt" dabei, sonst „pro Person".

In `app/config.py` bei den `DEFAULTS`:
```python
    # Mailversand für Anmeldebestätigungen. Zugangsdaten leben nur hier.
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_passwort": "",
    "smtp_von": "",
    "smtp_starttls": True,
    # Öffentliche Adresse des Portals, für die Zugangsmail.
    "portal_url": "",
```

In `app/preflight.py` eine Kachel `id="mail"`: `warn`, wenn `smtp_host` leer ist („nur nötig, wenn Anmeldebestätigungen verschickt werden"), sonst `ok` mit Host und Absender im Detail. **Kein Verbindungstest beim Preflight** — der würde bei jedem Aufruf des System-Checks eine SMTP-Verbindung öffnen. Die `ANLEITUNG` erklärt, wo die Werte herkommen und dass das Passwort nur in der gitignorierten `config.json` steht.

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_mail.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add app/mail.py app/config.py app/preflight.py tests/test_mail.py
git commit -m "feat: Mailversand ueber SMTP mit Vorlagen"
```

---

### Task 5: Die öffentlichen Seiten

**Files:**
- Create: `app/anmeldung_seiten.py`, `tests/test_anmeldung_seiten.py`
- Modify: `app/portal.py` (nur die Umbenennung `_STIL` → `STIL`)

**Interfaces:**
- Consumes: `html.escape`, `app.portal.FARBEN`, `app.portal.STIL`
- Produces:
  - `seite(titel: str, inhalt: str) -> str` — Rahmen im CI, wie `portal.seite`
  - `kursliste(kurse: list[dict]) -> str`
  - `kursseite(kurs: dict, termine: list[dict], fehler: str = "", werte: dict | None = None) -> str`
  - `danke_seite(kurs: dict) -> str`

- [ ] **Step 1: Den Test schreiben**

`tests/test_anmeldung_seiten.py`:
```python
"""Die öffentlichen Anmeldeseiten."""

from app import anmeldung_seiten as seiten

KURS = {"id": 1, "slug": "ki-pflicht", "titel": "KI-Pflichtschulung",
        "beschreibung": "Pflicht nach Art. 4 KI-VO.",
        "format": "E-Learning, 80–90 Min", "preis_cent": 14900,
        "preis_pauschal": 0}
TERMINE = [{"id": 7, "beginn": "2026-09-02T09:00:00",
            "ende": "2026-09-02T13:00:00", "status": "offen"},
           {"id": 8, "beginn": "2026-09-16T09:00:00",
            "ende": "2026-09-16T13:00:00", "status": "ausgebucht"}]


def test_rahmen_ohne_fremdquellen():
    html = seiten.seite("Titel", "<p>Inhalt</p>")
    assert html.startswith("<!doctype html>")
    assert "http://" not in html and "https://" not in html
    assert "<script src=" not in html


def test_kursliste_verlinkt_die_kurse():
    html = seiten.kursliste([KURS])
    assert "KI-Pflichtschulung" in html
    assert "/anmeldung/ki-pflicht" in html
    assert "149,00" in html


def test_kursseite_zeigt_offene_termine_als_auswahl():
    html = seiten.kursseite(KURS, TERMINE)
    assert 'value="7"' in html
    assert "02.09.2026" in html


def test_ausgebuchte_termine_sind_nicht_waehlbar():
    html = seiten.kursseite(KURS, TERMINE)
    assert 'value="8"' not in html
    assert "ausgebucht" in html.lower()


def test_keine_platzzahlen_auf_der_seite():
    """Nach außen nie Zahlen."""
    html = seiten.kursseite(KURS, TERMINE).lower()
    for verboten in ("plätze", "plaetze", "belegt", "frei "):
        assert verboten not in html


def test_terminloser_kurs_zeigt_kein_auswahlfeld():
    html = seiten.kursseite(KURS, [])
    assert "<select" not in html
    assert "jederzeit" in html.lower()


def test_formular_hat_die_felder():
    html = seiten.kursseite(KURS, TERMINE)
    for feld in ('name="name"', 'name="email"', 'name="firma"',
                 'name="nachricht"'):
        assert feld in html


def test_fehler_wird_angezeigt_und_maskiert():
    html = seiten.kursseite(KURS, TERMINE, fehler="Termin <voll>")
    assert "&lt;voll&gt;" in html
    assert "<voll>" not in html


def test_eingaben_bleiben_nach_einem_fehler_stehen():
    html = seiten.kursseite(KURS, TERMINE, fehler="Fehler",
                            werte={"name": "Anna", "email": "anna@example.org"})
    assert 'value="Anna"' in html
    assert 'value="anna@example.org"' in html


def test_eingaben_werden_maskiert():
    html = seiten.kursseite(KURS, TERMINE, fehler="F",
                            werte={"name": '"><script>alert(1)</script>'})
    assert "<script>alert(1)</script>" not in html


def test_danke_seite_nennt_die_naechsten_schritte():
    html = seiten.danke_seite(KURS)
    assert "Rechnung" in html
    assert "KI-Pflichtschulung" in html


def test_seiten_behaupten_keine_staatliche_anerkennung():
    for html in (seiten.kursliste([KURS]), seiten.kursseite(KURS, TERMINE),
                 seiten.danke_seite(KURS)):
        for verboten in ("staatlich anerkannt", "azav", "bildungsgutschein"):
            assert verboten not in html.lower()
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_anmeldung_seiten.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.anmeldung_seiten'`.

- [ ] **Step 3: Das Stylesheet des Portals öffentlich machen**

In `app/portal.py` heißt die Stilkonstante `_STIL` und wird nur in `seite()` benutzt. Die Anmeldeseiten brauchen dasselbe Aussehen; eine Kopie wäre zwei Stellen, die auseinanderlaufen. Deshalb umbenennen — es ist genau eine Definition und genau eine Verwendung:

```python
STIL = f"""
  * {{ box-sizing: border-box; }}
```
(unverändertes Innere), und in `seite()`:
```python
<style>{STIL}</style>
```

Run: `.venv/bin/python -m pytest tests/test_portal.py -v`
Expected: unverändert grün — die Umbenennung darf nichts am Markup ändern.

- [ ] **Step 4: `app/anmeldung_seiten.py` schreiben**

```python
"""Die öffentlichen Anmeldeseiten.

Reine Funktionen von Daten zu HTML — ohne Server testbar. Die Routen liegen
in app/anmeldung_routes.py.

Wichtigste Regel: Hier steht nie eine Platzzahl. Ein Termin ist „offen" oder
„ausgebucht". Wer die Auslastung sieht, sieht den Umsatz.
"""

import html as _html
from datetime import datetime

from .portal import FARBEN, STIL

# Das Portal kennt nur E-Mail- und Passwortfelder. Die Anmeldung braucht
# zusätzlich Text, Auswahl und Mehrzeiler.
_ZUSATZ = f"""
  input[type=text], textarea, select {{
    width: 100%; padding: 12px; border-radius: 10px;
    border: 1px solid {FARBEN['akzent']}; background: rgba(30,30,58,.5);
    color: {FARBEN['text']}; font-size: 16px; font-family: inherit;
  }}
  textarea {{ resize: vertical; }}
  h2 {{ font-size: 20px; margin: 0 0 6px; }}
  .warnung {{ color: #f87171; }}
  ul {{ padding-left: 20px; margin: 6px 0 0; }}
"""


def _preis(kurs: dict) -> str:
    """Betrag deutsch, mit dem Zusatz, worauf er sich bezieht."""
    betrag = f"{int(kurs.get('preis_cent', 0)) / 100:,.2f}"
    betrag = betrag.replace(",", "X").replace(".", ",").replace("X", ".")
    zusatz = "gesamt" if kurs.get("preis_pauschal") else "pro Person"
    return f"{betrag} € {zusatz}"


def _datum(iso: str) -> str:
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(iso)


def _uhrzeit(iso: str) -> str:
    try:
        return datetime.fromisoformat(str(iso)).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def seite(titel: str, inhalt: str) -> str:
    """Der gemeinsame Rahmen. Keine externe Quelle, kein Skript."""
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(titel)} · AI-SmartCon</title>
<style>{STIL}{_ZUSATZ}</style>
</head>
<body>
<main>
  <div class="kopf">
    <span class="wortmarke">AI-SmartCon</span>
    <span class="muted">Kurse und Termine</span>
  </div>
{inhalt}
</main>
</body>
</html>
"""


def kursliste(kurse: list[dict]) -> str:
    """Alle ausgeschriebenen Kurse als Karten."""
    if not kurse:
        karten = '  <p class="muted">Zurzeit ist nichts ausgeschrieben.</p>'
    else:
        karten = "".join(f"""  <div class="karte">
    <h2>{_html.escape(str(k["titel"]))}</h2>
    <p class="muted">{_html.escape(str(k.get("format", "")))} · {_preis(k)}</p>
    <p>{_html.escape(str(k.get("beschreibung", "")))}</p>
    <a class="knopf" href="/anmeldung/{_html.escape(str(k["slug"]))}">Zum Kurs</a>
  </div>
""" for k in kurse)
    return seite("Kurse", f"  <h1>Kurse und Termine</h1>\n{karten}")


def kursseite(kurs: dict, termine: list[dict], fehler: str = "",
              werte: dict | None = None) -> str:
    """Kursbeschreibung und Anmeldeformular.

    `termine` kommt aus `kurse.naechste_offene()` und enthält deshalb keine
    Platzzahlen — nur `status` mit „offen" oder „ausgebucht".
    """
    werte = werte or {}

    def wert(feld: str) -> str:
        return _html.escape(str(werte.get(feld, "")))

    offen = [t for t in termine if t.get("status") == "offen"]
    vergeben = [t for t in termine if t.get("status") != "offen"]

    if offen:
        optionen = "".join(
            f'<option value="{int(t["id"])}">{_datum(t["beginn"])}, '
            f'{_uhrzeit(t["beginn"])} Uhr</option>' for t in offen)
        auswahl = f"""      <label>Termin
        <select name="termin_id" required>{optionen}</select>
      </label>"""
    elif termine:
        auswahl = ('      <p class="muted">Alle ausgeschriebenen Termine sind '
                   'vergeben. Melden Sie sich trotzdem an — wir nehmen Sie für '
                   'den nächsten Durchgang auf.</p>')
    else:
        auswahl = ('      <p class="muted">Diese Schulung läuft ohne festen '
                   'Termin. Sie können jederzeit starten.</p>')

    hinweis = ""
    if vergeben:
        zeilen = "".join(f"<li>{_datum(t['beginn'])} — ausgebucht</li>"
                         for t in vergeben)
        hinweis = (f'  <p class="muted">Bereits vergeben:</p>\n'
                   f'  <ul class="muted">{zeilen}</ul>\n')

    meldung = (f'    <p class="warnung">{_html.escape(fehler)}</p>\n'
               if fehler else "")

    inhalt = f"""  <h1>{_html.escape(str(kurs["titel"]))}</h1>
  <p class="muted">{_html.escape(str(kurs.get("format", "")))} · {_preis(kurs)}</p>
  <p>{_html.escape(str(kurs.get("beschreibung", "")))}</p>
  <div class="karte">
{meldung}    <form method="post" action="/anmeldung/{_html.escape(str(kurs["slug"]))}">
{auswahl}
      <label>Name
        <input name="name" type="text" maxlength="120" required value="{wert("name")}">
      </label>
      <label>E-Mail
        <input name="email" type="email" maxlength="200" required value="{wert("email")}">
      </label>
      <label>Firma (optional)
        <input name="firma" type="text" maxlength="120" value="{wert("firma")}">
      </label>
      <label>Nachricht (optional)
        <textarea name="nachricht" rows="4" maxlength="2000">{wert("nachricht")}</textarea>
      </label>
      <button type="submit">Verbindlich anmelden</button>
    </form>
  </div>
{hinweis}"""
    return seite(str(kurs["titel"]), inhalt)


def danke_seite(kurs: dict) -> str:
    """Was nach der Anmeldung passiert — ohne Versprechen, die nicht gelten."""
    inhalt = f"""  <h1>Danke für Ihre Anmeldung</h1>
  <div class="karte">
    <p>Ihre Anmeldung zu <strong>{_html.escape(str(kurs["titel"]))}</strong> ist
      eingegangen. Eine Bestätigung geht per E-Mail an Sie raus.</p>
    <p>Sie bekommen von uns eine <strong>Rechnung</strong>. Sobald die Zahlung
      da ist, schalten wir Ihren Zugang frei und schicken Ihnen die Zugangsdaten
      für das Lernportal.</p>
    <p class="muted">Fragen? Antworten Sie einfach auf die Bestätigungsmail.</p>
  </div>
  <a class="knopf" href="/anmeldung">Zurück zur Übersicht</a>
"""
    return seite("Danke", inhalt)
```

Die Fallen dabei:

- **Der Test `test_keine_platzzahlen_auf_der_seite` liest das ganze Dokument in Kleinschreibung**, CSS eingeschlossen. Kein „Plätze", kein „belegt", kein „frei " darf irgendwo auftauchen — auch nicht in einem Klassennamen.
- `test_rahmen_ohne_fremdquellen` verbietet **jedes** `http://` und `https://` im Rahmen. Kein Link nach draußen, keine Schriftart von einem CDN, kein `xmlns`.
- `value="{wert(…)}"` steht in doppelten Anführungszeichen, und `html.escape` maskiert mit `quote=True` genau die — daran hängt `test_eingaben_werden_maskiert`.

- [ ] **Step 5: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_anmeldung_seiten.py tests/test_portal.py -v`
Expected: 12 passed in `test_anmeldung_seiten.py`, `test_portal.py` unverändert grün.

- [ ] **Step 6: Commit**

```bash
git add app/anmeldung_seiten.py app/portal.py tests/test_anmeldung_seiten.py
git commit -m "feat: oeffentliche Anmeldeseiten"
```

---

### Task 6: Die öffentlichen Routen

**Files:**
- Create: `app/anmeldung_routes.py`, `tests/test_anmeldung_routes.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `app.anmeldung.*`, `app.kurse.*`, `app.mail.*`, `app.anmeldung_seiten.*`
- Produces:
  - `router` mit Präfix `/anmeldung`
  - `GET /anmeldung` — Kursliste
  - `GET /anmeldung/{slug}` — Kursseite mit Formular
  - `POST /anmeldung/{slug}` — Anmeldung entgegennehmen
  - `RATE_FENSTER = 3600`, `RATE_MAX = 5`

- [ ] **Step 1: Den Test schreiben**

`tests/test_anmeldung_routes.py`:
```python
"""Die öffentlichen Anmelderouten. Schwerpunkt: was Fremde auslösen können."""

from datetime import date, timedelta

import pytest

from app import anmeldung, anmeldung_routes, db, kurse

FORMULAR = {"name": "Anna Beispiel", "email": "anna@example.org",
            "firma": "Beispiel GmbH", "nachricht": "Bitte um Rechnung."}


@pytest.fixture
def anmeldeclient(client, tmp_path, monkeypatch):
    """TestClient mit eigener Datenbank, einem Kurs — und ohne echten Versand."""
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()
    # Die Bremse ist Modulzustand: ohne Rücksetzen färbt ein Test den nächsten.
    monkeypatch.setattr(anmeldung_routes, "_ZUGRIFFE", {})

    gesendet = []
    monkeypatch.setattr(anmeldung_routes.mail, "konfiguriert", lambda: True)
    monkeypatch.setattr(anmeldung_routes.mail, "senden",
                        lambda an, betreff, text: gesendet.append(an))

    kid = kurse.anlegen("ki-pflicht", "KI-Pflichtschulung", plaetze=2,
                        preis_cent=14900, format="E-Learning, 80–90 Min",
                        schulung_slug="ki-pflicht")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date.today() + timedelta(days=60))

    client.kurs = kid
    client.termin = kurse.termine(kid)[0]["id"]
    client.gesendet = gesendet
    return client


def _absenden(c, **felder):
    daten = {**FORMULAR, "termin_id": str(c.termin), **felder}
    return c.post("/anmeldung/ki-pflicht", data=daten)


def test_kursliste_ist_ohne_anmeldung_erreichbar(anmeldeclient):
    antwort = anmeldeclient.get("/anmeldung")
    assert antwort.status_code == 200
    assert "KI-Pflichtschulung" in antwort.text


def test_nur_aktive_kurse_erscheinen(anmeldeclient):
    kurse.aendern(anmeldeclient.kurs, aktiv=False)
    text = anmeldeclient.get("/anmeldung").text
    assert "KI-Pflichtschulung" not in text
    assert anmeldeclient.get("/anmeldung/ki-pflicht").status_code == 404


def test_unbekannter_kurs_ist_404(anmeldeclient):
    assert anmeldeclient.get("/anmeldung/gibts-nicht").status_code == 404


def test_kursseite_nennt_keine_platzzahlen(anmeldeclient):
    text = anmeldeclient.get("/anmeldung/ki-pflicht").text.lower()
    for verboten in ("plätze", "plaetze", "belegt", "frei "):
        assert verboten not in text


def test_anmelden_legt_an_und_dankt(anmeldeclient):
    antwort = _absenden(anmeldeclient)
    assert antwort.status_code == 200
    assert "Rechnung" in antwort.text
    eintraege = anmeldung.liste()
    assert len(eintraege) == 1
    assert eintraege[0]["email"] == "anna@example.org"
    assert eintraege[0]["termin_id"] == anmeldeclient.termin


def test_anmelden_verschickt_eine_bestaetigung(anmeldeclient):
    _absenden(anmeldeclient)
    assert anmeldeclient.gesendet == ["anna@example.org"]


def test_versand_fehler_verliert_die_anmeldung_nicht(anmeldeclient, monkeypatch):
    """Ein klemmendes Postfach kostet einen Anruf, keinen Kunden."""
    def kaputt(*a, **kw):
        raise anmeldung_routes.mail.MailFehler("Postfach antwortet nicht")

    monkeypatch.setattr(anmeldung_routes.mail, "senden", kaputt)
    antwort = _absenden(anmeldeclient)
    assert antwort.status_code == 200
    assert len(anmeldung.liste()) == 1


def test_fehlerhafte_eingabe_zeigt_die_seite_mit_den_werten(anmeldeclient):
    antwort = _absenden(anmeldeclient, email="keine-mail")
    assert antwort.status_code == 400
    assert 'value="Anna Beispiel"' in antwort.text
    assert anmeldung.liste() == []


def test_ausgebucht_zeigt_die_seite_statt_eines_fehlers(anmeldeclient):
    for i in range(2):  # plaetze=2
        _absenden(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org")
    antwort = _absenden(anmeldeclient, name="Zu spät", email="spaet@example.org")
    assert antwort.status_code == 400
    assert "ausgebucht" in antwort.text.lower()


def test_fehlermeldung_nennt_keine_zahlen(anmeldeclient):
    for i in range(2):
        _absenden(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org")
    text = _absenden(anmeldeclient, name="Zu spät", email="spaet@example.org").text
    # Der Kurspreis steht auf der Seite; die Meldung selbst darf nichts zählen.
    meldung = text.split('class="warnung"')[1].split("</p>")[0]
    assert not any(z.isdigit() for z in meldung)


def test_zu_viele_anmeldungen_werden_gebremst(anmeldeclient):
    for i in range(anmeldung_routes.RATE_MAX):
        antwort = _absenden(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org",
                            termin_id="")
        assert antwort.status_code == 200, i
    letzte = _absenden(anmeldeclient, name="Zuviel", email="zuviel@example.org",
                       termin_id="")
    assert letzte.status_code == 429
    assert len(anmeldung.liste()) == anmeldung_routes.RATE_MAX


def test_die_bremse_gilt_je_absender(anmeldeclient):
    for i in range(anmeldung_routes.RATE_MAX):
        _absenden(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org",
                  termin_id="")
    daten = {**FORMULAR, "termin_id": ""}
    andere = anmeldeclient.post("/anmeldung/ki-pflicht", data=daten,
                                headers={"CF-Connecting-IP": "203.0.113.9"})
    assert andere.status_code == 200


def test_gebremste_anfrage_verschickt_nichts(anmeldeclient):
    for i in range(anmeldung_routes.RATE_MAX + 3):
        _absenden(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org",
                  termin_id="")
    assert len(anmeldeclient.gesendet) == anmeldung_routes.RATE_MAX


def test_der_slug_kann_nicht_aus_dem_bereich_ausbrechen(anmeldeclient):
    """%2f wird im Pfadparameter dekodiert — der Slug darf trotzdem nur ein Slug sein."""
    antwort = anmeldeclient.get("/anmeldung/%2e%2e%2fapi%2fverwaltung%2fteilnehmer")
    assert antwort.status_code == 404
    assert "teilnehmer" not in antwort.text.lower()


def test_der_router_hat_nur_diese_drei_wege(anmeldeclient):
    from app import main

    wege = {r.path for r in main.app.routes
            if getattr(r, "path", "").startswith("/anmeldung")}
    assert wege == {"/anmeldung", "/anmeldung/{slug}"}
```

Die Rate-Begrenzung ist der Punkt, der ohne Test nicht überlebt: Ohne sie ist das Formular ein Mailversand-Werkzeug für Dritte, mit dem Absender von ai-smartcon.de. Fünf Anmeldungen je Stunde und Absender reichen für jeden echten Fall.

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_anmeldung_routes.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.anmeldung_routes'`.

- [ ] **Step 3: `app/anmeldung_routes.py` schreiben**

```python
"""Die öffentlichen Anmelderouten — der dritte Bereich der App.

Kein Login, keine Werkstatt-Fähigkeiten, genau drei Wege: Kursliste,
Kursseite, Anmeldung. Alles, was hier hereinkommt, kommt von Fremden.

Die Bremse ist bewusst ein Wörterbuch im Prozess: kein Redis, keine
Abhängigkeit, ein Neustart setzt sie zurück. Bei diesem Volumen ist das
richtig. Sie ist eine Höflichkeitsbremse gegen Formular-Missbrauch, keine
Sicherheitsgrenze — wer die App direkt erreicht, kann `CF-Connecting-IP`
selbst setzen. Genau deshalb steht die App hinter dem Tunnel (Task 10).
"""

import logging
import time

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from . import anmeldung, anmeldung_seiten as seiten, kurse, mail

router = APIRouter(prefix="/anmeldung")
log = logging.getLogger(__name__)

RATE_FENSTER = 3600      # Sekunden
RATE_MAX = 5             # Anmeldungen je Absender und Fenster
RATE_EINTRAEGE_MAX = 5000  # danach wird beim Zugriff aufgeräumt
PROXY_KOPF = "cf-connecting-ip"

_ZUGRIFFE: dict[str, list[float]] = {}


def _absender(request: Request) -> str:
    """Wer fragt. Hinter dem Tunnel steht die echte Adresse im Cloudflare-Kopf."""
    kopf = request.headers.get(PROXY_KOPF, "").strip()
    if kopf:
        return kopf.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unbekannt"


def _bremse(request: Request) -> None:
    """Wirft 429, wenn ein Absender das Fenster ausgeschöpft hat."""
    jetzt = time.monotonic()
    wer = _absender(request)
    fenster = [t for t in _ZUGRIFFE.get(wer, []) if jetzt - t < RATE_FENSTER]
    if len(fenster) >= RATE_MAX:
        _ZUGRIFFE[wer] = fenster
        raise HTTPException(
            429, "Zu viele Anmeldungen von hier. Bitte später noch einmal "
                 "versuchen oder eine Mail schreiben.")
    fenster.append(jetzt)
    _ZUGRIFFE[wer] = fenster

    # Sonst wächst das Wörterbuch mit jeder gesehenen Adresse weiter.
    if len(_ZUGRIFFE) > RATE_EINTRAEGE_MAX:
        for k, v in list(_ZUGRIFFE.items()):
            if not v or jetzt - v[-1] >= RATE_FENSTER:
                _ZUGRIFFE.pop(k, None)


def _kurs_oder_404(slug: str) -> dict:
    k = kurse.kurs_nach_slug(slug)
    if k is None or not k["aktiv"]:
        # Dieselbe Antwort für „gibt es nicht" und „nicht ausgeschrieben".
        raise HTTPException(404, "Diesen Kurs gibt es nicht.")
    return k


@router.get("", response_class=HTMLResponse)
def seite_kursliste():
    return seiten.kursliste(kurse.liste(nur_aktive=True))


@router.get("/{slug}", response_class=HTMLResponse)
def seite_kurs(slug: str):
    k = _kurs_oder_404(slug)
    return seiten.kursseite(k, kurse.naechste_offene(k["id"]))


@router.post("/{slug}", response_class=HTMLResponse)
def anmelden(request: Request, slug: str,
             name: str = Form(""), email: str = Form(""),
             firma: str = Form(""), nachricht: str = Form(""),
             termin_id: str = Form("")):
    k = _kurs_oder_404(slug)
    _bremse(request)
    werte = {"name": name, "email": email, "firma": firma, "nachricht": nachricht}

    tid: int | None = None
    if termin_id.strip():
        try:
            tid = int(termin_id)
        except ValueError:
            return _mit_fehler(k, "Bitte einen Termin aus der Liste wählen.", werte)

    try:
        neu = anmeldung.annehmen(k["id"], tid, name, email, firma, nachricht)
    except anmeldung.AnmeldungFehler as e:
        return _mit_fehler(k, str(e), werte)

    _bestaetigen(neu, k, tid)
    return seiten.danke_seite(k)


def _mit_fehler(kurs: dict, meldung: str, werte: dict) -> HTMLResponse:
    """Das Formular noch einmal, mit Meldung und den eingegebenen Werten."""
    return HTMLResponse(
        seiten.kursseite(kurs, kurse.naechste_offene(kurs["id"]),
                         fehler=meldung, werte=werte),
        status_code=400)


def _bestaetigen(anmeldung_id: int, kurs: dict, termin_id: int | None) -> None:
    """Bestätigungsmail. Ein Fehler hier darf die Anmeldung nicht kippen.

    Erst speichern, dann senden. Eine Anmeldung, die verlorengeht, weil das
    Postfach klemmte, ist ein verlorener Kunde; eine Bestätigung, die nicht
    ankam, ist ein Anruf.
    """
    if not mail.konfiguriert():
        log.warning("Kein SMTP eingerichtet — Anmeldung %s unbestätigt",
                    anmeldung_id)
        return
    try:
        eintrag = anmeldung.eintrag(anmeldung_id)
        termin = kurse.termin(termin_id) if termin_id else None
        betreff, text = mail.anmeldung_eingegangen(eintrag, kurs, termin)
        mail.senden(eintrag["email"], betreff, text)
    except Exception:  # auch ein Vorlagenfehler darf die Anmeldung nicht kippen
        log.exception("Bestätigung zu Anmeldung %s nicht verschickt", anmeldung_id)
```

- [ ] **Step 4: Router in `app/main.py` einbinden**

Bei den anderen Routern (`app/main.py:42`):
```python
from . import anmeldung_routes
...
app.include_router(verwaltung.router)
app.include_router(portal_routes.router)
app.include_router(anmeldung_routes.router)   # öffentlich, ohne Login
```

- [ ] **Step 5: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_anmeldung_routes.py -v`
Expected: 15 passed.

- [ ] **Step 6: Volle Suite, dann Commit**

Run: `.venv/bin/python -m pytest`
Expected: alles grün — insbesondere `test_api.py`, weil ein neuer Router die Routenliste ändert.

```bash
git add app/anmeldung_routes.py app/main.py tests/test_anmeldung_routes.py
git commit -m "feat: oeffentliche Anmelderouten mit Rate-Begrenzung"
```

---

### Task 7: Verwaltung für Kurse, Termine und Anmeldungen

**Files:**
- Modify: `app/verwaltung.py`, `static/index.html`, `static/app.js`, `static/style.css`
- Test: `tests/test_verwaltung_kurse.py`

**Interfaces:**
- Consumes: `app.kurse.*`, `app.anmeldung.*`, `app.mail.*`, `app.config.load()`
- Produces (alle unter `/api/verwaltung`, alle hinter dem Werkstatt-Schutz):
  - `GET /kurse` → `{"kurse": [ … , "termine": [ … mit "belegt" und "plaetze" ]]}`
  - `POST /kurse` → `{"id": int}`
  - `POST /kurse/{kid}` → `{"ok": true}` (ändern)
  - `POST /kurse/{kid}/serie` → `{"serie_id": int, "termine": int}`
  - `POST /termine/{tid}/status` → `{"ok": true}`
  - `GET /anmeldungen` → `{"anmeldungen": [ … mit "kurs_titel" und "beginn" ]}`
  - `POST /anmeldungen/{aid}/status` → `{"ok": true}`
  - `POST /anmeldungen/{aid}/freischalten` → `{"passwort": str, "mail": bool}`

- [ ] **Step 1: Den Test schreiben**

`tests/test_verwaltung_kurse.py`:
```python
"""Verwaltungsrouten für Kurse, Termine und Anmeldungen (die Innensicht)."""

import json
from datetime import date, timedelta

import pytest

from app import anmeldung, db, kurse, verwaltung

PRUEFUNG = {"titel": "Abschlussprüfung", "bestehensgrenze": 70,
            "fragen": [{"frage": "F?", "optionen": ["a", "b", "c"],
                        "richtig": 0, "thema": "Level 1", "hinweis": "Weil a."}]}


@pytest.fixture
def verwaltungsclient(client, projekte_tmp, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()

    d = projekte_tmp / "ki-pflicht"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "KI-Pflichtschulung"}))
    (d / "status.json").write_text(json.dumps({"phase": "fertig"}))
    (d / "pruefung.json").write_text(json.dumps(PRUEFUNG), encoding="utf-8")

    gesendet = []
    monkeypatch.setattr(verwaltung.mail, "konfiguriert", lambda: True)
    monkeypatch.setattr(verwaltung.mail, "senden",
                        lambda an, betreff, text: gesendet.append(an))
    client.gesendet = gesendet
    return client


def _kurs(c, **felder):
    antwort = c.post("/api/verwaltung/kurse",
                     json={"slug": "ki-pflicht", "titel": "KI-Pflichtschulung",
                           "plaetze": 2, "schulung_slug": "ki-pflicht", **felder})
    assert antwort.status_code == 201, antwort.text
    return antwort.json()["id"]


def test_kurs_anlegen_und_listen(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    liste = verwaltungsclient.get("/api/verwaltung/kurse").json()["kurse"]
    assert [k["id"] for k in liste] == [kid]
    assert liste[0]["titel"] == "KI-Pflichtschulung"


def test_doppelter_slug_ist_409(verwaltungsclient):
    _kurs(verwaltungsclient)
    antwort = verwaltungsclient.post(
        "/api/verwaltung/kurse", json={"slug": "ki-pflicht", "titel": "Noch mal"})
    assert antwort.status_code == 409


def test_unsinnige_eingabe_ist_400(verwaltungsclient):
    antwort = verwaltungsclient.post(
        "/api/verwaltung/kurse", json={"slug": "nicht erlaubt!", "titel": "X"})
    assert antwort.status_code == 400


def test_kurs_aendern(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    assert verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}",
                                  json={"titel": "Neu"}).status_code == 200
    liste = verwaltungsclient.get("/api/verwaltung/kurse").json()["kurse"]
    assert liste[0]["titel"] == "Neu"


def test_unbekanntes_feld_wird_abgewiesen(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    antwort = verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}",
                                     json={"gibtsnicht": 1})
    assert antwort.status_code == 400


def test_serie_erzeugt_termine(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    antwort = verwaltungsclient.post(
        f"/api/verwaltung/kurse/{kid}/serie",
        json={"wochentag": 2, "uhrzeit": "09:00", "rhythmus": 2, "wochen": 12})
    assert antwort.status_code == 201
    assert antwort.json()["termine"] > 0
    kurs = verwaltungsclient.get("/api/verwaltung/kurse").json()["kurse"][0]
    assert len(kurs["termine"]) == antwort.json()["termine"]


def test_die_innensicht_nennt_die_zahlen(verwaltungsclient):
    """Nach außen nie Zahlen — hier drin schon, sonst ist die Liste nutzlos."""
    kid = _kurs(verwaltungsclient)
    verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}/serie",
                           json={"wochentag": 2, "uhrzeit": "09:00", "wochen": 8})
    termin = verwaltungsclient.get(
        "/api/verwaltung/kurse").json()["kurse"][0]["termine"][0]
    assert termin["plaetze"] == 2
    assert termin["belegt"] == 0


def test_termin_absagen(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}/serie",
                           json={"wochentag": 2, "uhrzeit": "09:00", "wochen": 8})
    tid = verwaltungsclient.get(
        "/api/verwaltung/kurse").json()["kurse"][0]["termine"][0]["id"]
    assert verwaltungsclient.post(f"/api/verwaltung/termine/{tid}/status",
                                  json={"status": "abgesagt"}).status_code == 200
    assert verwaltungsclient.post(f"/api/verwaltung/termine/{tid}/status",
                                  json={"status": "quatsch"}).status_code == 400


def test_anmeldungen_zeigen_kurs_und_termin(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    aid = anmeldung.annehmen(kid, None, "Anna", "anna@example.org")
    liste = verwaltungsclient.get("/api/verwaltung/anmeldungen").json()["anmeldungen"]
    assert [e["id"] for e in liste] == [aid]
    assert liste[0]["kurs_titel"] == "KI-Pflichtschulung"
    assert liste[0]["status"] == "neu"


def test_status_setzen(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    aid = anmeldung.annehmen(kid, None, "Anna", "anna@example.org")
    assert verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/status",
                                  json={"status": "bezahlt"}).status_code == 200
    assert anmeldung.eintrag(aid)["status"] == "bezahlt"
    assert verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/status",
                                  json={"status": "quatsch"}).status_code == 400


def test_freischalten_gibt_das_passwort_einmal_und_mailt(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    aid = anmeldung.annehmen(kid, None, "Anna", "anna@example.org")
    verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/status",
                           json={"status": "bezahlt"})

    antwort = verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/freischalten")
    assert antwort.status_code == 200
    assert len(antwort.json()["passwort"]) == 12
    assert antwort.json()["mail"] is True
    assert verwaltungsclient.gesendet == ["anna@example.org"]


def test_freischalten_ohne_bezahlt_ist_400(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    aid = anmeldung.annehmen(kid, None, "Anna", "anna@example.org")
    assert verwaltungsclient.post(
        f"/api/verwaltung/anmeldungen/{aid}/freischalten").status_code == 400


def test_freischalten_zweimal_ist_409(verwaltungsclient):
    kid = _kurs(verwaltungsclient)
    aid = anmeldung.annehmen(kid, None, "Anna", "anna@example.org")
    verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/status",
                           json={"status": "bezahlt"})
    verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/freischalten")
    assert verwaltungsclient.post(
        f"/api/verwaltung/anmeldungen/{aid}/freischalten").status_code == 409


def test_versand_fehler_verliert_den_zugang_nicht(verwaltungsclient, monkeypatch):
    """Das Passwort gibt es nur einmal — es darf nicht an der Mail hängen."""
    def kaputt(*a, **kw):
        raise verwaltung.mail.MailFehler("Postfach antwortet nicht")

    monkeypatch.setattr(verwaltung.mail, "senden", kaputt)
    kid = _kurs(verwaltungsclient)
    aid = anmeldung.annehmen(kid, None, "Anna", "anna@example.org")
    verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/status",
                           json={"status": "bezahlt"})

    antwort = verwaltungsclient.post(f"/api/verwaltung/anmeldungen/{aid}/freischalten")
    assert antwort.status_code == 200
    assert len(antwort.json()["passwort"]) == 12
    assert antwort.json()["mail"] is False
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_verwaltung_kurse.py -v`
Expected: FAIL mit 404 auf `/api/verwaltung/kurse` bzw. `AttributeError: module 'app.verwaltung' has no attribute 'mail'`.

- [ ] **Step 3: `app/verwaltung.py` erweitern**

An die vorhandene Datei anhängen; der Import oben wird zu
`from . import anmeldung, kurse, mail, projekte, teilnehmer, versuche`.

```python
TERMIN_WOCHEN_MAX = 104  # zwei Jahre im Voraus reicht


def _int(body: dict, feld: str, vorgabe: int, min_: int, max_: int) -> int:
    wert = body.get(feld, vorgabe)
    if not isinstance(wert, int) or isinstance(wert, bool) \
            or not min_ <= wert <= max_:
        raise HTTPException(
            400, f"„{feld}“ muss eine ganze Zahl zwischen {min_} und {max_} sein")
    return wert


@router.get("/kurse")
def api_kurse_liste():
    """Alle Kurse mit ihren kommenden Terminen — hier **mit** Platzzahlen.

    Das ist die Innensicht hinter dem Zugriffsschutz. Die öffentliche Sicht
    in app/anmeldung_seiten.py nennt nie eine Zahl.
    """
    eintraege = kurse.liste()
    for k in eintraege:
        k["termine"] = kurse.termine(k["id"])
    return {"kurse": eintraege}


@router.post("/kurse", status_code=201)
def api_kurs_neu(body: dict):
    felder = {f: body[f] for f in kurse.FELDER if f in body}
    try:
        kid = kurse.anlegen(str(body.get("slug", "")), str(body.get("titel", "")),
                            **{f: v for f, v in felder.items() if f != "titel"})
    except kurse.KursFehler as e:
        raise HTTPException(409 if "bereits" in str(e) else 400, str(e))
    return {"id": kid}


@router.post("/kurse/{kid}")
def api_kurs_aendern(kid: int, body: dict):
    unbekannt = set(body) - set(kurse.FELDER)
    if unbekannt:
        raise HTTPException(400, f"Unbekannte Felder: {', '.join(sorted(unbekannt))}")
    try:
        kurse.aendern(kid, **body)
    except kurse.KursFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"ok": True}


@router.post("/kurse/{kid}/serie", status_code=201)
def api_serie_neu(kid: int, body: dict):
    """Legt die Regel an und erzeugt gleich die Termine der nächsten Wochen."""
    wochen = _int(body, "wochen", 26, 1, TERMIN_WOCHEN_MAX)
    try:
        sid = kurse.serie_anlegen(
            kid, wochentag=_int(body, "wochentag", 0, 0, 6),
            uhrzeit=str(body.get("uhrzeit", "09:00")),
            dauer_tage=_int(body, "dauer_tage", 1, 1, 30),
            rhythmus=_int(body, "rhythmus", 1, 1, 52))
        anzahl = kurse.termine_erzeugen(
            sid, bis=date.today() + timedelta(weeks=wochen))
    except kurse.KursFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"serie_id": sid, "termine": anzahl}


@router.post("/termine/{tid}/status")
def api_termin_status(tid: int, body: dict):
    try:
        kurse.termin_status(tid, str(body.get("status", "")))
    except kurse.KursFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"ok": True}


@router.get("/anmeldungen")
def api_anmeldungen_liste():
    return {"anmeldungen": anmeldung.liste()}


@router.post("/anmeldungen/{aid}/status")
def api_anmeldung_status(aid: int, body: dict):
    try:
        anmeldung.status_setzen(aid, str(body.get("status", "")))
    except anmeldung.AnmeldungFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"ok": True}


@router.post("/anmeldungen/{aid}/freischalten")
def api_anmeldung_freischalten(aid: int):
    """Aus der bezahlten Anmeldung wird ein Teilnehmer mit Portalzugang.

    Das Passwort wird hier genau einmal zurückgegeben. Deshalb darf ein
    Fehler beim Mailversand die Antwort nicht kippen — sonst ist der Zugang
    angelegt und der Klartext für immer weg.
    """
    try:
        _, passwort = anmeldung.zu_teilnehmer(aid)
    except anmeldung.AnmeldungFehler as e:
        text = str(e)
        if "nicht gefunden" in text:
            raise HTTPException(404, text)
        raise HTTPException(409 if "bereits" in text else 400, text)

    eintrag = anmeldung.eintrag(aid)
    kurs = kurse.kurs(eintrag["kurs_id"])
    versendet = False
    if mail.konfiguriert():
        try:
            betreff, text = mail.zugang_freigeschaltet(
                eintrag, kurs, passwort,
                (config.load().get("portal_url") or "").rstrip("/") or "/portal")
            mail.senden(eintrag["email"], betreff, text)
            versendet = True
        except Exception:
            log.exception("Zugangsmail zu Anmeldung %s nicht verschickt", aid)
    return {"passwort": passwort, "mail": versendet}
```

Dazu oben in der Datei: `import logging`, `from datetime import date, timedelta`, `from . import config` und `log = logging.getLogger(__name__)`.

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_verwaltung_kurse.py tests/test_verwaltung.py -v`
Expected: 14 passed in `test_verwaltung_kurse.py`, `test_verwaltung.py` unverändert grün.

- [ ] **Step 5: Commit des Backends**

```bash
git add app/verwaltung.py tests/test_verwaltung_kurse.py
git commit -m "feat: Verwaltungsrouten fuer Kurse, Termine und Anmeldungen"
```

- [ ] **Step 6: Die beiden Reiter in `static/index.html`**

In der `<nav>` (Zeile 15–20) nach „Teilnehmer" einfügen:
```html
    <button id="tab-kurse" class="tab" data-tab="kurse">Kurse</button>
    <button id="tab-anmeldungen" class="tab" data-tab="anmeldungen">Anmeldungen</button>
```

Nach `<section id="view-teilnehmer">` die beiden neuen Abschnitte:
```html
  <section id="view-kurse" class="view">
    <div class="view-kopf">
      <h2>Kurse</h2>
      <button id="btn-kurs-neu">Kurs anlegen</button>
    </div>
    <p class="muted">Die öffentliche Ansicht liegt unter <code>/anmeldung</code>.
      Dort stehen nie Platzzahlen — hier schon, das ist die Innensicht.</p>

    <form id="kurs-form" hidden>
      <label>Kürzel für die Adresse <input name="slug" required
        pattern="[a-z0-9][a-z0-9-]*" placeholder="ki-pflicht"></label>
      <label>Titel <input name="titel" required></label>
      <label>Format <input name="format" placeholder="E-Learning, 80–90 Min"></label>
      <label>Beschreibung <textarea name="beschreibung" rows="3"></textarea></label>
      <label>Preis in Euro <input name="preis_euro" type="number" min="0"
        step="0.01" value="0"></label>
      <label><input name="preis_pauschal" type="checkbox"> Gesamtpreis statt pro Person</label>
      <label>Plätze <input name="plaetze" type="number" min="1" value="10"></label>
      <label>Schulung im Portal
        <select name="schulung_slug"><option value="">— keine —</option></select>
      </label>
      <div class="zeile">
        <button type="submit">Anlegen</button>
        <button type="button" id="btn-kurs-abbrechen">Abbrechen</button>
        <span id="kurs-status" class="muted"></span>
      </div>
    </form>

    <div id="kurse-liste"></div>
  </section>

  <section id="view-anmeldungen" class="view">
    <div class="view-kopf">
      <h2>Anmeldungen</h2>
      <button id="btn-anmeldungen-neu-laden">Neu laden</button>
    </div>
    <p class="muted">Weg einer Anmeldung: <strong>neu</strong> → Rechnung raus →
      <strong>bezahlt</strong> → „Zugang freischalten“. Das Passwort wird einmal
      angezeigt und geht zusätzlich per Mail an den Teilnehmer.</p>
    <div id="anmeldungen-liste"></div>
  </section>
```

Der Passwort-Kasten liegt in `view-teilnehmer` und wird hier mitbenutzt: Er zieht mit an den Anfang von `<main>`, damit `zeigePasswort()` aus beiden Reitern sichtbar ist. Alternativ ein zweiter Kasten — **nicht** machen, dann gibt es zwei Wahrheiten über dasselbe Passwort.

Beide `?v=`-Nummern in `static/index.html` von `10` auf `11` hochzählen.

- [ ] **Step 7: `static/app.js` erweitern**

Im Reiter-Umschalter (Zeile 21) neben `teilnehmer` die beiden neuen Fälle:
```js
  if (btn.dataset.tab === "kurse") { ladeKurse(); }
  if (btn.dataset.tab === "anmeldungen") { ladeAnmeldungen(); }
```

Ans Dateiende:
```js
/* ---------- Kurse und Termine ---------- */

function euro(cent) {
  return (cent / 100).toLocaleString('de-DE',
    { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function datumZeit(iso) {
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString('de-DE',
    { day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit' });
}

async function ladeKurse() {
  const antwort = await fetch('/api/verwaltung/kurse');
  const ziel = document.getElementById('kurse-liste');
  if (!antwort.ok) { ziel.innerHTML = '<p class="muted">Nicht lesbar.</p>'; return; }
  const liste = (await antwort.json()).kurse;
  if (!liste.length) {
    ziel.innerHTML = '<p class="muted">Noch kein Kurs angelegt.</p>';
  } else {
    ziel.innerHTML = liste.map((k) => `
      <div class="karte">
        <strong>${esc(k.titel)}</strong>
        <span class="muted">/anmeldung/${esc(k.slug)} · ${euro(k.preis_cent)} €
          ${k.preis_pauschal ? 'gesamt' : 'pro Person'}</span>
        <span class="badge">${k.aktiv ? 'ausgeschrieben' : 'nicht sichtbar'}</span>
        <div class="tabelle-scroll"><table class="gate-tabelle">
          <thead><tr><th>Termin</th><th>Belegt</th><th>Status</th><th></th></tr></thead>
          <tbody>${k.termine.map((t) => `
            <tr>
              <td>${esc(datumZeit(t.beginn))}</td>
              <td>${t.belegt}/${t.plaetze}</td>
              <td>${esc(t.status)}</td>
              <td><button data-absagen="${t.id}">absagen</button></td>
            </tr>`).join('') || '<tr><td colspan="4">Noch keine Termine.</td></tr>'}
          </tbody>
        </table></div>
        <div class="zeile">
          <select data-wochentag="${k.id}">
            ${['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map((tag, i) =>
              `<option value="${i}">${tag}</option>`).join('')}
          </select>
          <input data-uhrzeit="${k.id}" type="time" value="09:00">
          <input data-rhythmus="${k.id}" type="number" min="1" max="52" value="1"
            title="alle N Wochen">
          <button data-serie="${k.id}">Termine für 26 Wochen erzeugen</button>
          <button data-sichtbar="${k.id}" data-aktiv="${k.aktiv ? 1 : 0}">
            ${k.aktiv ? 'Nicht mehr ausschreiben' : 'Ausschreiben'}</button>
        </div>
      </div>`).join('');
  }

  ziel.querySelectorAll('[data-serie]').forEach((el) => {
    el.addEventListener('click', async () => {
      const kid = el.dataset.serie;
      const a = await fetch(`/api/verwaltung/kurse/${kid}/serie`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wochentag: Number(ziel.querySelector(`[data-wochentag="${kid}"]`).value),
          uhrzeit: ziel.querySelector(`[data-uhrzeit="${kid}"]`).value,
          rhythmus: Number(ziel.querySelector(`[data-rhythmus="${kid}"]`).value),
          wochen: 26,
        }),
      });
      if (!a.ok) zeigePasswort('', (await a.json()).detail);
      ladeKurse();
    });
  });

  ziel.querySelectorAll('[data-absagen]').forEach((el) => {
    el.addEventListener('click', async () => {
      await fetch(`/api/verwaltung/termine/${el.dataset.absagen}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'abgesagt' }) });
      ladeKurse();
    });
  });

  ziel.querySelectorAll('[data-sichtbar]').forEach((el) => {
    el.addEventListener('click', async () => {
      await fetch(`/api/verwaltung/kurse/${el.dataset.sichtbar}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aktiv: el.dataset.aktiv !== '1' }) });
      ladeKurse();
    });
  });

  // Fertige Schulungen für das Auswahlfeld im Anlegen-Formular
  const p = await fetch('/api/projekte');
  const fertige = (await p.json()).projekte
    .filter((x) => x.art !== 'praesentation' && x.phase === 'fertig');
  document.querySelector('#kurs-form [name=schulung_slug]').innerHTML =
    '<option value="">— keine —</option>' + fertige.map((x) =>
      `<option value="${esc(x.slug)}">${esc(x.thema || x.slug)}</option>`).join('');
}

document.getElementById('btn-kurs-neu').addEventListener('click', () => {
  document.getElementById('kurs-form').hidden = false;
});
document.getElementById('btn-kurs-abbrechen').addEventListener('click', () => {
  document.getElementById('kurs-form').hidden = true;
});
document.getElementById('kurs-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const status = document.getElementById('kurs-status');
  const f = new FormData(e.target);
  const daten = {
    slug: f.get('slug'), titel: f.get('titel'), format: f.get('format'),
    beschreibung: f.get('beschreibung'),
    // Cent statt Euro: Fließkomma-Preise werden irgendwann falsch gerundet.
    preis_cent: Math.round(Number(f.get('preis_euro') || 0) * 100),
    preis_pauschal: f.get('preis_pauschal') ? 1 : 0,
    plaetze: Number(f.get('plaetze')),
    schulung_slug: f.get('schulung_slug') || '',
  };
  const a = await fetch('/api/verwaltung/kurse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(daten) });
  const ergebnis = await a.json();
  if (!a.ok) { status.textContent = `Fehler: ${ergebnis.detail}`; return; }
  status.textContent = '';
  e.target.reset();
  e.target.hidden = true;
  ladeKurse();
});

/* ---------- Anmeldungen ---------- */

const ANMELDUNG_STATUS = ['neu', 'bestaetigt', 'bezahlt', 'storniert'];

async function ladeAnmeldungen() {
  const antwort = await fetch('/api/verwaltung/anmeldungen');
  const ziel = document.getElementById('anmeldungen-liste');
  if (!antwort.ok) { ziel.innerHTML = '<p class="muted">Nicht lesbar.</p>'; return; }
  const liste = (await antwort.json()).anmeldungen;
  if (!liste.length) {
    ziel.innerHTML = '<p class="muted">Noch keine Anmeldung.</p>';
    return;
  }
  ziel.innerHTML = liste.map((a) => `
    <div class="karte">
      <strong>${esc(a.name)}</strong> <span class="muted">${esc(a.email)}</span>
      ${a.firma ? `<span class="muted"> · ${esc(a.firma)}</span>` : ''}
      <span class="badge">${esc(a.status)}</span>
      <p class="muted">${esc(a.kurs_titel)}${a.beginn ? ' · ' + esc(datumZeit(a.beginn)) : ' · ohne Termin'}</p>
      ${a.nachricht ? `<p>${esc(a.nachricht)}</p>` : ''}
      <div class="zeile">
        <select data-status="${a.id}">
          ${ANMELDUNG_STATUS.map((s) =>
            `<option value="${s}"${s === a.status ? ' selected' : ''}>${s}</option>`).join('')}
        </select>
        <button data-status-setzen="${a.id}">Status setzen</button>
        <button data-freigeben="${a.id}"${a.status === 'bezahlt' && !a.teilnehmer_id ? '' : ' disabled'}>
          Zugang freischalten</button>
        ${a.teilnehmer_id ? '<span class="muted">Zugang angelegt</span>' : ''}
      </div>
    </div>`).join('');

  ziel.querySelectorAll('[data-status-setzen]').forEach((el) => {
    el.addEventListener('click', async () => {
      const aid = el.dataset.statusSetzen;
      const a = await fetch(`/api/verwaltung/anmeldungen/${aid}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: ziel.querySelector(`[data-status="${aid}"]`).value }) });
      if (!a.ok) zeigePasswort('', (await a.json()).detail);
      ladeAnmeldungen();
    });
  });

  ziel.querySelectorAll('[data-freigeben]').forEach((el) => {
    el.addEventListener('click', async () => {
      const a = await fetch(
        `/api/verwaltung/anmeldungen/${el.dataset.freigeben}/freischalten`,
        { method: 'POST' });
      const e = await a.json();
      if (!a.ok) { zeigePasswort('', e.detail); return; }
      // Einmalige Anzeige, wie beim Teilnehmer. Kein alert/prompt — ein modaler
      // Dialog blockiert die Browser-Prüfung aus Task 8.
      zeigePasswort(e.passwort, e.mail ? '' :
        'Achtung: Die Zugangsmail ging nicht raus. Passwort selbst weitergeben.');
      ladeAnmeldungen();
    });
  });
}

document.getElementById('btn-anmeldungen-neu-laden')
  .addEventListener('click', ladeAnmeldungen);
```

Zwei Dinge, die hier leicht schiefgehen:

- `anmeldung.liste()` muss `kurs_titel`, `beginn` und `teilnehmer_id` mitliefern, sonst zeigt der Reiter `undefined`. Das ist ein `LEFT JOIN` auf `kurs` und `termin` in Task 3 — steht dort schon in der Rückgabe, hier ist die Nutzung.
- `data-status-setzen` heißt in JS `dataset.statusSetzen`. Bindestrich zu camelCase — ein häufiger stiller Fehler.

Kein `alert`, kein `confirm`, kein `window.prompt` — sie blockieren die Browser-Prüfung in Task 8.

- [ ] **Step 8: Frontend prüfen und committen**

Run: `node --check static/app.js && .venv/bin/python -m pytest`
Expected: kein Syntaxfehler, volle Suite grün.

```bash
git add app/verwaltung.py static/ tests/test_verwaltung_kurse.py
git commit -m "feat: Reiter Kurse und Anmeldungen in der Werkstatt"
```

---

### Task 8: Der Durchlauf im Browser

**Files:** keine — Prüfung im laufenden Container.

Wie in der letzten Etappe: kein Code, sondern der Beweis, dass die Kette trägt. Der Test-Kurs heißt durchgehend `zzz-testkurs`, damit am Ende klar ist, was wieder weg muss.

- [ ] **Step 1: Vorher absichern**

```bash
# Läuft ein Agent? Dann warten — ein Rebuild killt die Produktion.
grep -l '"laeuft"' projects/*/status.json 2>/dev/null; echo "---"
mkdir -p data && sqlite3 data/kurse.db ".backup data/kurse-vor-etappe6-$(date +%F).db"
sqlite3 data/kurse.db "SELECT COUNT(*) FROM teilnehmer;" \
                      "SELECT COUNT(*) FROM anmeldung;"
docker compose build && docker compose up -d
docker compose logs --tail=30 smartcon-schulungen
```
Die beiden Zählungen notieren — sie sind der Vergleichswert für Step 9.

- [ ] **Step 2: SMTP eintragen und den System-Check ansehen**

In den Einstellungen `smtp_host`, `smtp_port`, `smtp_user`, `smtp_passwort`, `smtp_von` und `portal_url` setzen. Dann `http://localhost:8710/api/preflight` aufrufen: Die Kachel `mail` muss von `warn` auf `ok` springen und Host und Absender nennen — **ohne das Passwort**.

- [ ] **Step 3: Kurs und Termine anlegen**

Reiter „Kurse" → „Kurs anlegen": Kürzel `zzz-testkurs`, Titel „Testkurs", Preis 1,00 €, **Plätze 2**, Schulung = eine fertige Schulung mit Prüfung. Dann in der Kurskarte Wochentag und Uhrzeit wählen und „Termine für 26 Wochen erzeugen". Erwartung: Die Tabelle zeigt Termine mit `0/2`.

- [ ] **Step 4: Die öffentliche Sicht — der eigentliche Prüfpunkt**

`http://localhost:8710/anmeldung` in einem **privaten Fenster** (keine Sitzung, kein Cache):

- Erscheint „Testkurs" mit Preis und Format?
- Auf `/anmeldung/zzz-testkurs`: sind die Termine als Auswahl da?
- **Steht nirgends eine Platzzahl?** Seitenquelltext prüfen, nicht nur die Ansicht:
  ```bash
  curl -s http://localhost:8710/anmeldung/zzz-testkurs \
    | grep -iE 'plätze|plaetze|belegt|frei ' ; echo "Treffer: $?"
  ```
  Erwartung: keine Ausgabe, `Treffer: 1`.

- [ ] **Step 5: Anmelden, mit echter Mail**

Zweimal anmelden, mit zwei verschiedenen echten Adressen (die Plätze sind 2).

- Kommt die Dankesseite mit dem Wort „Rechnung"?
- **Kommt die Bestätigungsmail an?** Das ist der Punkt dieses Schritts: Betreff, Kursname, Termin im deutschen Format, Preis mit Komma. Im Spam-Ordner nachsehen — ein selbst gehostetes Postfach landet dort gern.
- Dritter Versuch: Wird der Termin nicht mehr angeboten? Wenn er noch dasteht (Cache), neu laden; wenn er verschwunden ist, über einen zweiten Termin anmelden und prüfen, dass die Ausgebucht-Meldung beim direkten Absenden **keine Zahl** enthält.

- [ ] **Step 6: Die Bremse**

```bash
for i in $(seq 1 7); do
  printf '%s ' "$(curl -s -o /dev/null -w '%{http_code}' \
    -X POST http://localhost:8710/anmeldung/zzz-testkurs \
    --data-urlencode "name=Bremse $i" \
    --data-urlencode "email=bremse$i@example.org" \
    --data-urlencode "termin_id=")"
done; echo
```
Erwartung: die ersten Antworten `200` oder `400`, ab der sechsten `429`. **Diese sechs bis sieben Zeilen gehören zu den Aufräumzahlen in Step 9.**

- [ ] **Step 7: Freischalten und ins Portal**

Reiter „Anmeldungen": erste Anmeldung auf „bezahlt" setzen, dann „Zugang freischalten".

- Erscheint das Passwort im Kasten, genau einmal?
- Kommt die Zugangsmail mit Passwort und der Portal-Adresse aus `portal_url`?
- Mit diesen Daten auf `/portal` anmelden, Lerneinheit öffnen, Prüfung schreiben, Nachweis ansehen. Die Kette aus Etappe 5 muss unverändert laufen.
- Zweiter Klick auf „Zugang freischalten": der Knopf ist aus, und der direkte Aufruf antwortet 409.

- [ ] **Step 8: Handybreite**

Mit dem Browser-Werkzeug auf **390 px** und **320 px**, je für `/anmeldung`, `/anmeldung/zzz-testkurs`, den Reiter „Kurse" und den Reiter „Anmeldungen". Kein horizontaler Überlauf; die Termintabelle scrollt in ihrem eigenen Kasten (`.tabelle-scroll`), nicht die Seite. Prüfen statt schätzen:
```js
document.documentElement.scrollWidth <= window.innerWidth
```

- [ ] **Step 9: Aufräumen und belegen**

```bash
sqlite3 data/kurse.db "DELETE FROM anmeldung WHERE kurs_id IN
    (SELECT id FROM kurs WHERE slug = 'zzz-testkurs');"
sqlite3 data/kurse.db "DELETE FROM kurs WHERE slug = 'zzz-testkurs';"  # Serien und Termine per CASCADE
sqlite3 data/kurse.db "SELECT COUNT(*) FROM teilnehmer;" \
                      "SELECT COUNT(*) FROM anmeldung;" \
                      "SELECT COUNT(*) FROM kurs;" \
                      "SELECT COUNT(*) FROM termin;"
```
Die Teilnehmer aus Step 7 sind **echte** Zeilen in `teilnehmer` und `teilnahme` — die Zählung wird also um die freigeschalteten Testpersonen höher liegen als in Step 1. Diese ID einzeln benennen und entfernen, statt pauschal zu löschen:
```bash
sqlite3 data/kurse.db "SELECT id, email FROM teilnehmer ORDER BY id DESC LIMIT 5;"
sqlite3 data/kurse.db "DELETE FROM teilnehmer WHERE id = <die eine ID>;"
```
Am Ende müssen `teilnehmer` und `anmeldung` wieder auf den Zahlen aus Step 1 stehen. Beide Zählungen in den Bericht.

Findet sich etwas, **nicht still reparieren** — melden mit dem, was zu sehen war.

---

# Etappe 7 — Umbenennung und Betrieb

Ab hier ist es Konfiguration, kein Code. Die Schritte sind einzeln umkehrbar und sollten in dieser Reihenfolge laufen.

### Task 9: Umbenennung auf SmartCon-Kurse

- [ ] **Repo umbenennen** auf GitHub (`Audiojoy72/SmartCon-Kurse`). GitHub legt eine Weiterleitung vom alten Namen an, `git remote set-url` trotzdem gleich nachziehen.
- [ ] **Ordner umbenennen** — das ist der Schritt mit Nebenwirkungen: `docker-compose.yml` mountet relativ, das überlebt; aber **claude-Sessions sind an das Arbeitsverzeichnis gebunden** und ein laufender Agent überlebt es nicht. Vorher prüfen, dass keiner läuft.
- [ ] **Container neu erstellen** — der Name `smartcon-schulungen` steckt in `docker-compose.yml` und in jedem `docker exec` in der Doku.
- [ ] Alle Vorkommen von „SmartCon-Schulungen" in `README.md`, `CLAUDE.md`, `SPEC.md`, `TECH_STACK.md` und den Prompt-Vorlagen (`app/prompts.py`, `app/praesentation.py` nennen die App im Arbeitsauftrag) durchgehen. **Der Skill `skill/schulung/` behält seinen Namen** — er ist neutral und wird auch anderswo genutzt.
- [ ] Vault-Projektnotiz umbenennen und die Verweise in `current-priorities.md` nachziehen.

### Task 10: Erreichbarkeit von außen

- [ ] **Cloudflare-Tunnel** für `kurse.ai-smartcon.de` auf Port 8710. Die Konvention im Haus ist `*.smartcon-ai.de` für Infrastruktur (so läuft `os.smartcon-ai.de`); hier sehen aber **Kunden die Adresse**, deshalb die Kundendomain. Beide Schreibweisen existieren und werden gern verwechselt — auf Deliverables gehört ausschließlich `ai-smartcon.de`.
- [ ] **Cloudflare Access** vor der ganzen Anwendung, Policy nur auf die eigene Mailadresse.
- [ ] **Bypass für zwei Pfadgruppen**: `/portal*` und `/anmeldung*` (samt `/api/anmeldung*`, falls Task 6 dort etwas ablegt). Alles andere bleibt hinter Access — insbesondere `/api/projekte*` und `/api/verwaltung*`.
- [ ] **Gegenprobe von einem fremden Netz** (Mobilfunk, nicht das Hausnetz): `/anmeldung` und `/portal` müssen ohne Anmeldung erreichbar sein, `/` und `/api/projekte` müssen die Access-Anmeldung zeigen. **Diese Prüfung ist der eigentliche Sicherheitstest der ganzen Etappe** — ein Tippfehler in der Bypass-Regel legt die Werkstatt offen, und die startet Agenten mit Bash-Rechten.
- [ ] `portal_secure_cookie` auf `true` und `portal_url` auf die öffentliche Adresse setzen.
- [ ] `lan_erreichbar` bewusst entscheiden: Mit Tunnel braucht es den offenen LAN-Port nicht mehr.

### Task 11: Betriebsdoku

- [ ] `README.md`: Abschnitt „Anmeldung und Kurse" mit dem Weg von der Anmeldung bis zum Portalzugang.
- [ ] `CLAUDE.md`: die drei Bereiche und ihre drei Schutzmodelle als Tabelle; die Warnung, dass ein Fehler in der Bypass-Regel die Werkstatt öffnet.
- [ ] Ein **Backup, das läuft**, nicht nur dokumentiert ist: `data/kurse.db` enthält jetzt Kundendaten und Anmeldungen. Ein Cron-Eintrag mit `sqlite3 … ".backup …"` und einer Aufbewahrung von 30 Tagen. Ohne das ist ein `rm -rf data/` das Ende der Kundenliste.
- [ ] Vault-Notiz und `current-priorities.md` nachziehen.

---

## Abschluss

- [ ] Volle Suite grün; `git status --short projects/` und `data/` unverändert
- [ ] Der Durchlauf aus Task 8 einmal vollständig, mit echter Mail
- [ ] Die Gegenprobe aus einem fremden Netz aus Task 10
- [ ] Backup einmal eingespielt, um zu sehen, dass es sich zurückspielen lässt

## Was dieser Plan bewusst nicht enthält

- **Online-Zahlung.** Rechnung und Freischaltung von Hand, wie besprochen. Stripe bringt Widerrufsbelehrung für digitale Inhalte, Rechnungsstellung und Kleinunternehmer-Ausweisung mit — ein eigenes Vorhaben.
- **Löschen von Teilnehmern und Anmeldungen.** Fehlt weiterhin, auch für eine DSGVO-Auskunft. Der nächste Kandidat nach diesem Plan.
- **Erinnerungsmails vor dem Termin.** Nützlich, aber nicht nötig, um verkaufen zu können.
