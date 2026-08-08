# SmartCon-Kurse — E-Learning-Portal (Etappe 4–5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die 149-€-Pflichtschulung nach Art. 4 KI-VO lieferbar machen: Teilnehmer bekommen einen eigenen Zugang, arbeiten die Lerneinheit im Portal durch, legen dort die Abschlussprüfung ab und laden bei Bestehen ihr AI-SmartCon-Zertifikat.

**Architecture:** Eine SQLite-Datei (`data/kurse.db`) hält Teilnehmer, Teilnahmen, Sitzungen und Prüfungsversuche; die Schulungsinhalte bleiben Dateien im Projektordner. Der Verwaltungsbereich liegt hinter dem bestehenden Zugriffsschutz, das Portal schützt sich selbst über scrypt-Passwörter und Sitzungs-Cookies. **Die Prüfung wird serverseitig ausgewertet** — die Lösungen verlassen den Server nie, sonst wäre das Zertifikat wertlos.

**Tech Stack:** Python 3.11, FastAPI, `sqlite3` + `hashlib.scrypt` + `secrets` aus der Standardbibliothek, Jinja-freies HTML aus f-Strings (wie `app/pruefung.py`), Vanilla JS ohne Build.

## Global Constraints

- UI-Texte, Doku und Kommentare **auf Deutsch**; Code-Identifier englisch.
- **Keine neuen Laufzeit-Dependencies.** `sqlite3`, `hashlib`, `secrets`, `hmac` sind Standardbibliothek. pytest/httpx bleiben in `requirements-dev.txt` und außerhalb des Images.
- Kein Framework im Frontend.
- Fehlerfälle: 404 unbekannt, 409 Konflikt, 400 Validierung, 401 nicht angemeldet, 403 Zugang abgelaufen.
- **Der Nachweis heißt „Teilnahmebestätigung", bei bestandener Prüfung „AI-SmartCon-Zertifikat".** Niemals „staatlich anerkannt", niemals „zertifiziert nach". Kein AZAV, kein Bildungsgutschein.
- Frontend bei **390 px und 320 px** ohne horizontalen Überlauf; Flex-Zeilen brauchen `flex-wrap`.
- `hidden` allein versteckt nichts: zu jeder neuen CSS-Regel mit eigenem `display` gehört eine `[hidden]`-Variante.
- Nach jeder Frontend-Änderung `?v=` in `static/index.html` für **beide** Assets hochzählen.
- Kein Test fasst den echten `projects/`-Ordner an, startet einen echten Agenten oder schreibt in die echte `data/kurse.db`.
- **Die Lösungen einer Prüfung werden im Portal niemals an den Browser gesendet** — weder im HTML, noch im JSON, noch in einem Attribut.
- Passwörter werden ausschließlich als scrypt-Hash gespeichert; Klartext existiert genau einmal, im Moment der Anzeige nach der Freischaltung.
- `data/` ist gitignored. Die Datenbank enthält Kundendaten.

## Zwei bewusste Abweichungen von der Vorbesprechung

1. **`sqlite3` statt SQLModel.** Besprochen war „wie DSS", und DSS nutzt SQLModel. Das zieht SQLAlchemy plus Umfeld in ein Projekt mit heute vier Abhängigkeiten. Für vier Tabellen ohne Migrationsgeschichte ist die Standardbibliothek klarer und passt zur Projektregel „keine neuen Dependencies ohne Not". Wenn die Terminverwaltung in Etappe 6 mit Serienregeln und Platzzählung dazukommt, ist der Wechsel zu einem ORM eine bewusste eigene Entscheidung — und dann auf gewachsenen Anforderungen begründet statt auf Vorrat.
2. **Das Zertifikat ist eine druckoptimierte HTML-Seite, kein serverseitig erzeugtes PDF.** DSS nutzt `fpdf2`. Wir haben zwar LibreOffice im Image, aber dessen HTML-Rendering ist für ein Layout dieser Art untauglich, und Chrome ist nicht im Image. Eine Seite mit `@media print` kostet nichts, sieht im CI aus wie gewünscht, und der Teilnehmer erzeugt das PDF im Browser („Drucken → Als PDF sichern"). Falls später ein serverseitiges PDF nötig wird, ist die HTML-Vorlage die Grundlage dafür.

---

## File Structure

| Datei | Verantwortung | Status |
|---|---|---|
| `app/db.py` | SQLite-Verbindung, Schema, Schema-Version | neu |
| `app/zugang.py` | Passwörter (scrypt), Sitzungstoken — kennt weder DB noch HTTP | neu |
| `app/teilnehmer.py` | Teilnehmer und Teilnahmen: anlegen, freischalten, Fenster verlängern | neu |
| `app/versuche.py` | Prüfungsversuche: starten, auswerten, zählen | neu |
| `app/portal.py` | Portal-Seiten als HTML (Login, Kursliste, Prüfung, Zertifikat) | neu |
| `app/portal_routes.py` | Portal-Routen samt Sitzungsprüfung | neu |
| `app/verwaltung.py` | Verwaltungsrouten für Teilnehmer und Freischaltung | neu |
| `app/main.py` | bindet die zwei neuen Router ein | ändern |
| `static/index.html`, `app.js`, `style.css` | Reiter „Teilnehmer" | ändern |
| `.gitignore` | `data/` | ändern |
| `docker-compose.yml` | `./data:/app/data` | ändern |
| `tests/test_db.py`, `test_zugang.py`, `test_teilnehmer.py`, `test_versuche.py`, `test_portal.py`, `test_verwaltung.py` | je Modul | neu |

`app/portal.py` (Ansichten) und `app/portal_routes.py` (HTTP) sind bewusst getrennt: Die Seiten sind reine Funktionen von Daten zu HTML und damit ohne Server testbar — dieselbe Aufteilung, die `app/pruefung.py` bereits nutzt.

---

## Das Datenmodell

```sql
CREATE TABLE teilnehmer (
    id             INTEGER PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    firma          TEXT NOT NULL DEFAULT '',
    passwort_hash  TEXT NOT NULL DEFAULT '',   -- leer bis zur Freischaltung
    angelegt_am    TEXT NOT NULL
);

CREATE TABLE teilnahme (
    id                INTEGER PRIMARY KEY,
    teilnehmer_id     INTEGER NOT NULL REFERENCES teilnehmer(id) ON DELETE CASCADE,
    slug              TEXT NOT NULL,            -- Projektordner der Schulung
    titel             TEXT NOT NULL,
    nachweis          TEXT NOT NULL DEFAULT 'Teilnahmebestätigung',
    gueltig_bis       TEXT,                     -- NULL = noch nicht freigeschaltet
    freigeschaltet_am TEXT,
    UNIQUE (teilnehmer_id, slug)
);

CREATE TABLE sitzung (
    token_hash    TEXT PRIMARY KEY,
    teilnehmer_id INTEGER NOT NULL REFERENCES teilnehmer(id) ON DELETE CASCADE,
    gueltig_bis   TEXT NOT NULL
);

CREATE TABLE versuch (
    id           INTEGER PRIMARY KEY,
    teilnahme_id INTEGER NOT NULL REFERENCES teilnahme(id) ON DELETE CASCADE,
    begonnen_am  TEXT NOT NULL,
    beendet_am   TEXT,
    prozent      INTEGER,
    bestanden    INTEGER NOT NULL DEFAULT 0
);
```

Zeitstempel sind ISO-8601-Strings in UTC, wie `projekte._jetzt()` sie schon schreibt. Die Bestehensgrenze und die Fragen kommen aus `projects/<slug>/pruefung.json`, nicht aus der Datenbank — sonst gäbe es zwei Wahrheiten über dieselbe Prüfung.

---

# Etappe 4 — Datenmodell, Zugänge, Verwaltung

### Task 1: Datenbank und Schema

**Files:**
- Create: `app/db.py`, `tests/test_db.py`
- Modify: `.gitignore`, `docker-compose.yml`

**Interfaces:**
- Produces:
  - `app.db.DB_PFAD: Path` — `ROOT / "data" / "kurse.db"`
  - `app.db.verbinden() -> sqlite3.Connection` — Row-Factory gesetzt, Fremdschlüssel an
  - `app.db.schema_anlegen(conn: sqlite3.Connection) -> None` — idempotent
  - `app.db.init() -> None` — legt Ordner und Schema an, beim App-Start aufgerufen

- [ ] **Step 1: Den Test schreiben**

`tests/test_db.py`:
```python
"""SQLite-Ablage der Kursverwaltung."""

import sqlite3

import pytest

from app import db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    """Frische Datenbank je Test — die echte data/kurse.db bleibt unberührt."""
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    c = db.verbinden()
    db.schema_anlegen(c)
    yield c
    c.close()


def test_alle_tabellen_existieren(conn):
    namen = {z["name"] for z in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"teilnehmer", "teilnahme", "sitzung", "versuch"} <= namen


def test_schema_anlegen_ist_idempotent(conn):
    # Beim Start jedes Containers erneut aufgerufen — darf nie scheitern.
    db.schema_anlegen(conn)
    db.schema_anlegen(conn)


def test_zeilen_sind_wie_ein_dict_lesbar(conn):
    conn.execute(
        "INSERT INTO teilnehmer (email, name, angelegt_am) VALUES (?, ?, ?)",
        ("a@b.de", "Anna", "2026-08-08T10:00:00+00:00"))
    zeile = conn.execute("SELECT * FROM teilnehmer").fetchone()
    assert zeile["email"] == "a@b.de"
    assert zeile["passwort_hash"] == ""


def test_email_ist_eindeutig(conn):
    for _ in range(2):
        try:
            conn.execute(
                "INSERT INTO teilnehmer (email, name, angelegt_am) VALUES (?, ?, ?)",
                ("a@b.de", "Anna", "2026-08-08T10:00:00+00:00"))
        except sqlite3.IntegrityError:
            return
    pytest.fail("Die zweite Zeile mit derselben E-Mail hätte scheitern müssen")


def test_fremdschluessel_greifen(conn):
    # Ohne PRAGMA foreign_keys=ON schluckt SQLite das stillschweigend.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO teilnahme (teilnehmer_id, slug, titel) VALUES (?, ?, ?)",
            (999, "kurs", "Titel"))


def test_teilnahmen_verschwinden_mit_dem_teilnehmer(conn):
    conn.execute(
        "INSERT INTO teilnehmer (email, name, angelegt_am) VALUES (?, ?, ?)",
        ("a@b.de", "Anna", "2026-08-08T10:00:00+00:00"))
    tid = conn.execute("SELECT id FROM teilnehmer").fetchone()["id"]
    conn.execute(
        "INSERT INTO teilnahme (teilnehmer_id, slug, titel) VALUES (?, ?, ?)",
        (tid, "kurs", "Titel"))
    conn.execute("DELETE FROM teilnehmer WHERE id = ?", (tid,))
    assert conn.execute("SELECT count(*) AS n FROM teilnahme").fetchone()["n"] == 0


def test_dieselbe_schulung_nur_einmal_je_teilnehmer(conn):
    conn.execute(
        "INSERT INTO teilnehmer (email, name, angelegt_am) VALUES (?, ?, ?)",
        ("a@b.de", "Anna", "2026-08-08T10:00:00+00:00"))
    tid = conn.execute("SELECT id FROM teilnehmer").fetchone()["id"]
    conn.execute("INSERT INTO teilnahme (teilnehmer_id, slug, titel) VALUES (?, ?, ?)",
                 (tid, "kurs", "Titel"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO teilnahme (teilnehmer_id, slug, titel) VALUES (?, ?, ?)",
                     (tid, "kurs", "Titel"))
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_db.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.db'`.

- [ ] **Step 3: Implementieren**

`app/db.py`:
```python
"""SQLite-Ablage der Kursverwaltung.

Die Schulungsinhalte bleiben Dateien im Projektordner — hier liegt nur, was
Beziehungen und Zählung braucht: Teilnehmer, ihre Teilnahmen, Sitzungen und
Prüfungsversuche.

Bewusst ohne ORM: vier Tabellen, kein Migrationsverlauf, und die Projektregel
„keine neuen Dependencies ohne Not". sqlite3 ist Standardbibliothek.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PFAD = ROOT / "data" / "kurse.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS teilnehmer (
    id             INTEGER PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    firma          TEXT NOT NULL DEFAULT '',
    passwort_hash  TEXT NOT NULL DEFAULT '',
    angelegt_am    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teilnahme (
    id                INTEGER PRIMARY KEY,
    teilnehmer_id     INTEGER NOT NULL REFERENCES teilnehmer(id) ON DELETE CASCADE,
    slug              TEXT NOT NULL,
    titel             TEXT NOT NULL,
    nachweis          TEXT NOT NULL DEFAULT 'Teilnahmebestätigung',
    gueltig_bis       TEXT,
    freigeschaltet_am TEXT,
    UNIQUE (teilnehmer_id, slug)
);

CREATE TABLE IF NOT EXISTS sitzung (
    token_hash    TEXT PRIMARY KEY,
    teilnehmer_id INTEGER NOT NULL REFERENCES teilnehmer(id) ON DELETE CASCADE,
    gueltig_bis   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS versuch (
    id           INTEGER PRIMARY KEY,
    teilnahme_id INTEGER NOT NULL REFERENCES teilnahme(id) ON DELETE CASCADE,
    begonnen_am  TEXT NOT NULL,
    beendet_am   TEXT,
    prozent      INTEGER,
    bestanden    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_teilnahme_teilnehmer ON teilnahme(teilnehmer_id);
CREATE INDEX IF NOT EXISTS idx_versuch_teilnahme ON versuch(teilnahme_id);
"""


def verbinden() -> sqlite3.Connection:
    """Eine Verbindung mit Dict-artigen Zeilen und aktiven Fremdschlüsseln.

    SQLite prüft Fremdschlüssel nur, wenn man es je Verbindung einschaltet —
    ohne das PRAGMA verschwindet eine Teilnahme nicht mit ihrem Teilnehmer,
    sie bleibt als Waise liegen.
    """
    DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PFAD, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def schema_anlegen(conn: sqlite3.Connection) -> None:
    """Legt fehlende Tabellen an. Idempotent — läuft bei jedem Start."""
    conn.executescript(SCHEMA)


def init() -> None:
    """Beim App-Start: Ordner und Schema sicherstellen."""
    conn = verbinden()
    try:
        schema_anlegen(conn)
    finally:
        conn.close()
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_db.py -v`
Expected: 7 passed.

- [ ] **Step 5: Ablage und Mount**

In `.gitignore` ergänzen:
```
data/
```

In `docker-compose.yml` bei den Volumes, direkt nach der `projects`-Zeile:
```yaml
      # Kursverwaltung: Teilnehmer, Zugänge, Prüfungsversuche. Enthält
      # Kundendaten und gehört wie config.json nie ins Repo.
      - ./data:/app/data
```

Der Ordner muss vor dem ersten Start existieren, sonst legt Docker ihn als
`root` an: in `CLAUDE.md` unter „Commands" beim Docker-Block ergänzen:
```sh
mkdir -p data                                    # einmalig, vor dem ersten Start
```

- [ ] **Step 6: Commit**

```bash
git add app/db.py tests/test_db.py .gitignore docker-compose.yml CLAUDE.md
git commit -m "feat: SQLite-Ablage fuer die Kursverwaltung"
```

---

### Task 2: Passwörter und Sitzungstoken

**Files:**
- Create: `app/zugang.py`, `tests/test_zugang.py`

**Interfaces:**
- Produces:
  - `app.zugang.passwort_erzeugen(laenge: int = 12) -> str`
  - `app.zugang.passwort_hashen(passwort: str) -> str` — Format `scrypt$n$r$p$salz$hash`
  - `app.zugang.passwort_pruefen(passwort: str, hinterlegt: str) -> bool`
  - `app.zugang.token_erzeugen() -> tuple[str, str]` — (Klartext, Hash)
  - `app.zugang.token_hashen(token: str) -> str`

Dieses Modul kennt weder Datenbank noch HTTP — dadurch ist es ohne Vorbereitung testbar.

- [ ] **Step 1: Den Test schreiben**

`tests/test_zugang.py`:
```python
"""Passwörter und Sitzungstoken. Alles aus der Standardbibliothek."""

from app import zugang


def test_erzeugtes_passwort_hat_die_gewuenschte_laenge():
    assert len(zugang.passwort_erzeugen()) == 12
    assert len(zugang.passwort_erzeugen(20)) == 20


def test_passwort_meidet_verwechselbare_zeichen():
    # Wird am Telefon vorgelesen und abgetippt: I, l, 1, O und 0 fehlen.
    zeichen = set("".join(zugang.passwort_erzeugen(40) for _ in range(20)))
    assert not (zeichen & set("Il1O0"))


def test_zwei_passwoerter_sind_verschieden():
    assert zugang.passwort_erzeugen() != zugang.passwort_erzeugen()


def test_hash_enthaelt_die_parameter():
    h = zugang.passwort_hashen("geheim")
    assert h.startswith("scrypt$")
    assert len(h.split("$")) == 6


def test_gleiches_passwort_ergibt_verschiedene_hashes():
    # Salz je Hash — sonst verrät ein Hash, dass zwei Konten dasselbe nutzen.
    assert zugang.passwort_hashen("geheim") != zugang.passwort_hashen("geheim")


def test_richtiges_passwort_wird_erkannt():
    h = zugang.passwort_hashen("geheim")
    assert zugang.passwort_pruefen("geheim", h) is True


def test_falsches_passwort_wird_abgewiesen():
    h = zugang.passwort_hashen("geheim")
    assert zugang.passwort_pruefen("falsch", h) is False
    assert zugang.passwort_pruefen("", h) is False


def test_leerer_hash_ergibt_false_statt_fehler():
    # Ein Teilnehmer ohne Freischaltung hat noch keinen Hash. Ein Login-Versuch
    # darf daran nicht mit einem Serverfehler enden.
    assert zugang.passwort_pruefen("egal", "") is False
    assert zugang.passwort_pruefen("egal", "kaputt") is False
    assert zugang.passwort_pruefen("egal", "scrypt$nicht$zahlen$x$y$z") is False


def test_token_klartext_und_hash_gehoeren_zusammen():
    klartext, gehasht = zugang.token_erzeugen()
    assert zugang.token_hashen(klartext) == gehasht
    assert klartext != gehasht


def test_token_ist_lang_genug():
    klartext, _ = zugang.token_erzeugen()
    assert len(klartext) >= 32


def test_token_hash_ist_deterministisch():
    # Anders als beim Passwort: der Hash ist der Datenbankschlüssel.
    assert zugang.token_hashen("abc") == zugang.token_hashen("abc")
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_zugang.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.zugang'`.

- [ ] **Step 3: Implementieren**

`app/zugang.py`:
```python
"""Passwörter, Sitzungstoken und ihre Prüfung.

Alles aus der Standardbibliothek. `hashlib.scrypt` ist ein anerkanntes
Verfahren zum Ablegen von Passwörtern (RFC 7914); bcrypt oder argon2 wären
zusätzliche Abhängigkeiten ohne Gewinn für diesen Fall.

Dieses Modul kennt weder Datenbank noch HTTP — dadurch ist es ohne
Vorbereitung testbar.
"""

import hashlib
import hmac
import secrets

# Ohne verwechselbare Zeichen: I, l, 1, O und 0 fehlen bewusst. Das Passwort
# wird am Telefon vorgelesen und von Hand abgetippt.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"

# n = 2**14 braucht rund 16 MB Arbeitsspeicher und wenige Millisekunden —
# genug gegen Ausprobieren, wenig genug für einen Login ohne Wartezeit. Der
# Wert steht im Hash, ältere Passwörter bleiben also prüfbar, wenn er steigt.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALZ_LAENGE = 16
SCHLUESSEL_LAENGE = 32


def passwort_erzeugen(laenge: int = 12) -> str:
    """Ein neues Passwort. 12 Zeichen aus diesem Alphabet sind rund 71 Bit."""
    return "".join(secrets.choice(ALPHABET) for _ in range(laenge))


def passwort_hashen(passwort: str) -> str:
    """Ergibt `scrypt$n$r$p$salz$hash`, Salz und Hash hexadezimal."""
    salz = secrets.token_bytes(SALZ_LAENGE)
    abgeleitet = hashlib.scrypt(
        passwort.encode(), salt=salz, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        dklen=SCHLUESSEL_LAENGE)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salz.hex()}${abgeleitet.hex()}"


def passwort_pruefen(passwort: str, hinterlegt: str) -> bool:
    """Prüft ein Passwort gegen den hinterlegten Hash.

    Ein leeres oder unlesbares Feld ergibt False statt eines Fehlers: Ein
    Teilnehmer ohne Freischaltung hat noch keinen Hash, und ein Login-Versuch
    darf daran nicht mit einem Serverfehler enden.
    """
    try:
        kennung, n, r, p, salz_hex, hash_hex = hinterlegt.split("$")
        if kennung != "scrypt":
            return False
        abgeleitet = hashlib.scrypt(
            passwort.encode(), salt=bytes.fromhex(salz_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(hash_hex) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(abgeleitet.hex(), hash_hex)


def token_erzeugen() -> tuple[str, str]:
    """Ein Sitzungstoken: (Klartext fürs Cookie, Hash für die Datenbank)."""
    klartext = secrets.token_urlsafe(32)
    return klartext, token_hashen(klartext)


def token_hashen(token: str) -> str:
    """Der Datenbankschlüssel eines Tokens.

    Anders als beim Passwort ohne Salz: Der Hash muss ohne Zusatzwissen aus
    dem Cookie berechenbar sein. Das Token ist zufällig und kurzlebig, ein
    Wörterbuchangriff auf einen 256-Bit-Zufallswert ist gegenstandslos.
    """
    return hashlib.sha256(token.encode()).hexdigest()
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_zugang.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add app/zugang.py tests/test_zugang.py
git commit -m "feat: Passwoerter und Sitzungstoken"
```

---

### Task 3: Teilnehmer und Teilnahmen

**Files:**
- Create: `app/teilnehmer.py`, `tests/test_teilnehmer.py`

**Interfaces:**
- Consumes: `app.db.verbinden()`, `app.zugang.*`
- Produces:
  - `app.teilnehmer.TeilnehmerFehler(ValueError)`
  - `anlegen(email, name, firma="") -> int` — gibt die id zurück, 409-Fall wirft
  - `liste() -> list[dict]` — je Teilnehmer mit `teilnahmen`
  - `teilnahme_anlegen(teilnehmer_id: int, slug: str, titel: str, nachweis: str) -> int`
  - `freischalten(teilnehmer_id: int, tage: int = 30) -> str` — erzeugt das Passwort, gibt es **einmal** im Klartext zurück
  - `verlaengern(teilnahme_id: int, tage: int = 30) -> None`
  - `anmelden(email: str, passwort: str) -> str | None` — Sitzungstoken im Klartext
  - `sitzung_pruefen(token: str) -> dict | None` — Teilnehmer oder None
  - `abmelden(token: str) -> None`
  - `teilnahme_offen(teilnahme: dict) -> bool` — Zugangsfenster noch gültig

- [ ] **Step 1: Den Test schreiben**

`tests/test_teilnehmer.py`:
```python
"""Teilnehmer, Teilnahmen, Freischaltung und Anmeldung."""

from datetime import datetime, timedelta, timezone

import pytest

from app import db, teilnehmer


@pytest.fixture
def datenbank(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()
    return db.DB_PFAD


def test_anlegen_gibt_eine_id(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna Beispiel", "Beispiel GmbH")
    assert isinstance(tid, int)


def test_doppelte_email_wird_abgewiesen(datenbank):
    teilnehmer.anlegen("anna@example.org", "Anna")
    with pytest.raises(teilnehmer.TeilnehmerFehler, match="bereits"):
        teilnehmer.anlegen("anna@example.org", "Anna nochmal")


def test_email_wird_normalisiert(datenbank):
    teilnehmer.anlegen("  Anna@Example.ORG ", "Anna")
    assert teilnehmer.liste()[0]["email"] == "anna@example.org"


def test_email_und_name_sind_pflicht(datenbank):
    with pytest.raises(teilnehmer.TeilnehmerFehler):
        teilnehmer.anlegen("  ", "Anna")
    with pytest.raises(teilnehmer.TeilnehmerFehler):
        teilnehmer.anlegen("anna@example.org", "   ")


def test_ohne_at_ist_es_keine_email(datenbank):
    with pytest.raises(teilnehmer.TeilnehmerFehler, match="E-Mail"):
        teilnehmer.anlegen("anna", "Anna")


def test_neuer_teilnehmer_hat_keinen_zugang(datenbank):
    teilnehmer.anlegen("anna@example.org", "Anna")
    assert teilnehmer.liste()[0]["hat_zugang"] is False


def test_teilnahme_erscheint_beim_teilnehmer(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.teilnahme_anlegen(tid, "ki-pflichtschulung", "KI-Pflichtschulung",
                                 "AI-SmartCon-Zertifikat")
    eintrag = teilnehmer.liste()[0]
    assert len(eintrag["teilnahmen"]) == 1
    assert eintrag["teilnahmen"][0]["titel"] == "KI-Pflichtschulung"
    assert eintrag["teilnahmen"][0]["nachweis"] == "AI-SmartCon-Zertifikat"


def test_dieselbe_schulung_nicht_zweimal(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")
    with pytest.raises(teilnehmer.TeilnehmerFehler, match="bereits"):
        teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")


def test_freischalten_liefert_das_passwort_genau_einmal(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")
    passwort = teilnehmer.freischalten(tid)

    assert len(passwort) == 12
    assert teilnehmer.liste()[0]["hat_zugang"] is True
    # Der Klartext steht nirgends in der Datenbank.
    conn = db.verbinden()
    hash_ = conn.execute("SELECT passwort_hash FROM teilnehmer").fetchone()[0]
    conn.close()
    assert passwort not in hash_


def test_freischalten_setzt_das_zugangsfenster(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")
    teilnehmer.freischalten(tid, tage=14)

    t = teilnehmer.liste()[0]["teilnahmen"][0]
    assert t["gueltig_bis"] is not None
    assert teilnehmer.teilnahme_offen(t) is True


def test_abgelaufene_teilnahme_ist_zu(datenbank):
    gestern = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert teilnehmer.teilnahme_offen({"gueltig_bis": gestern}) is False


def test_nicht_freigeschaltete_teilnahme_ist_zu(datenbank):
    assert teilnehmer.teilnahme_offen({"gueltig_bis": None}) is False


def test_verlaengern_schiebt_das_fenster(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    tnid = teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")
    teilnehmer.freischalten(tid, tage=1)
    vorher = teilnehmer.liste()[0]["teilnahmen"][0]["gueltig_bis"]

    teilnehmer.verlaengern(tnid, tage=30)
    nachher = teilnehmer.liste()[0]["teilnahmen"][0]["gueltig_bis"]
    assert nachher > vorher


def test_anmelden_mit_richtigem_passwort(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")
    passwort = teilnehmer.freischalten(tid)

    token = teilnehmer.anmelden("anna@example.org", passwort)
    assert token
    assert teilnehmer.sitzung_pruefen(token)["email"] == "anna@example.org"


def test_anmelden_ist_unabhaengig_von_gross_kleinschreibung(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    passwort = teilnehmer.freischalten(tid)
    assert teilnehmer.anmelden("ANNA@example.org", passwort)


def test_falsches_passwort_ergibt_keinen_token(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.freischalten(tid)
    assert teilnehmer.anmelden("anna@example.org", "falsch") is None


def test_unbekannte_email_ergibt_keinen_token(datenbank):
    assert teilnehmer.anmelden("niemand@example.org", "egal") is None


def test_nicht_freigeschaltet_kann_sich_nicht_anmelden(datenbank):
    teilnehmer.anlegen("anna@example.org", "Anna")
    assert teilnehmer.anmelden("anna@example.org", "") is None


def test_unbekannter_token_ergibt_none(datenbank):
    assert teilnehmer.sitzung_pruefen("erfunden") is None
    assert teilnehmer.sitzung_pruefen("") is None


def test_abmelden_entwertet_den_token(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    passwort = teilnehmer.freischalten(tid)
    token = teilnehmer.anmelden("anna@example.org", passwort)

    teilnehmer.abmelden(token)
    assert teilnehmer.sitzung_pruefen(token) is None


def test_abgelaufene_sitzung_gilt_nicht_mehr(datenbank):
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    passwort = teilnehmer.freischalten(tid)
    token = teilnehmer.anmelden("anna@example.org", passwort)

    conn = db.verbinden()
    conn.execute("UPDATE sitzung SET gueltig_bis = ?",
                 ((datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),))
    conn.close()
    assert teilnehmer.sitzung_pruefen(token) is None
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_teilnehmer.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.teilnehmer'`.

- [ ] **Step 3: Implementieren**

`app/teilnehmer.py`:
```python
"""Teilnehmer, ihre Teilnahmen und der Zugang zum Portal.

Ein Teilnehmer entsteht in der Verwaltung, bekommt eine oder mehrere
Teilnahmen zugeordnet und wird dann freigeschaltet. Erst dabei entsteht ein
Passwort — vorher ist `passwort_hash` leer, und ein Login-Versuch scheitert.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

from . import db, zugang

SITZUNG_STUNDEN = 24


class TeilnehmerFehler(ValueError):
    """Eingabe oder Zustand passt nicht. Die Meldung ist für die Oberfläche."""


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _iso(zeitpunkt: datetime) -> str:
    return zeitpunkt.isoformat(timespec="seconds")


def _email_normalisieren(email: str) -> str:
    sauber = email.strip().lower()
    if not sauber:
        raise TeilnehmerFehler("E-Mail fehlt")
    if "@" not in sauber or sauber.startswith("@") or sauber.endswith("@"):
        raise TeilnehmerFehler("Das ist keine gültige E-Mail-Adresse")
    return sauber


def anlegen(email: str, name: str, firma: str = "") -> int:
    """Legt einen Teilnehmer ohne Zugang an und gibt seine id zurück."""
    email = _email_normalisieren(email)
    name = name.strip()
    if not name:
        raise TeilnehmerFehler("Name fehlt")

    conn = db.verbinden()
    try:
        cur = conn.execute(
            "INSERT INTO teilnehmer (email, name, firma, angelegt_am) "
            "VALUES (?, ?, ?, ?)",
            (email, name, firma.strip(), _iso(_jetzt())))
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise TeilnehmerFehler(f"„{email}“ ist bereits angelegt")
    finally:
        conn.close()


def teilnahme_anlegen(teilnehmer_id: int, slug: str, titel: str,
                      nachweis: str) -> int:
    """Ordnet einem Teilnehmer eine Schulung zu. Noch ohne Freischaltung."""
    conn = db.verbinden()
    try:
        cur = conn.execute(
            "INSERT INTO teilnahme (teilnehmer_id, slug, titel, nachweis) "
            "VALUES (?, ?, ?, ?)",
            (teilnehmer_id, slug, titel, nachweis))
        return cur.lastrowid
    except sqlite3.IntegrityError as e:
        if "FOREIGN KEY" in str(e):
            raise TeilnehmerFehler("Teilnehmer nicht gefunden")
        raise TeilnehmerFehler("Diese Schulung ist dem Teilnehmer bereits zugeordnet")
    finally:
        conn.close()


def liste() -> list[dict]:
    """Alle Teilnehmer mit ihren Teilnahmen, neueste zuerst."""
    conn = db.verbinden()
    try:
        eintraege = []
        for t in conn.execute(
                "SELECT * FROM teilnehmer ORDER BY angelegt_am DESC"):
            teilnahmen = [dict(z) for z in conn.execute(
                "SELECT * FROM teilnahme WHERE teilnehmer_id = ? ORDER BY id",
                (t["id"],))]
            for tn in teilnahmen:
                tn["offen"] = teilnahme_offen(tn)
            eintraege.append({
                "id": t["id"], "email": t["email"], "name": t["name"],
                "firma": t["firma"], "angelegt_am": t["angelegt_am"],
                "hat_zugang": bool(t["passwort_hash"]),
                "teilnahmen": teilnahmen,
            })
        return eintraege
    finally:
        conn.close()


def freischalten(teilnehmer_id: int, tage: int = 30) -> str:
    """Erzeugt ein Passwort, öffnet alle Teilnahmen und gibt den Klartext zurück.

    Der Klartext wird nirgends gespeichert. Wer ihn verliert, bekommt ein
    neues Passwort — dasselbe kann niemand wiederherstellen.
    """
    passwort = zugang.passwort_erzeugen()
    bis = _iso(_jetzt() + timedelta(days=tage))

    conn = db.verbinden()
    try:
        cur = conn.execute(
            "UPDATE teilnehmer SET passwort_hash = ? WHERE id = ?",
            (zugang.passwort_hashen(passwort), teilnehmer_id))
        if cur.rowcount == 0:
            raise TeilnehmerFehler("Teilnehmer nicht gefunden")
        conn.execute(
            "UPDATE teilnahme SET gueltig_bis = ?, freigeschaltet_am = ? "
            "WHERE teilnehmer_id = ?",
            (bis, _iso(_jetzt()), teilnehmer_id))
        return passwort
    finally:
        conn.close()


def verlaengern(teilnahme_id: int, tage: int = 30) -> None:
    """Schiebt das Zugangsfenster einer Teilnahme nach hinten."""
    conn = db.verbinden()
    try:
        cur = conn.execute(
            "UPDATE teilnahme SET gueltig_bis = ? WHERE id = ?",
            (_iso(_jetzt() + timedelta(days=tage)), teilnahme_id))
        if cur.rowcount == 0:
            raise TeilnehmerFehler("Teilnahme nicht gefunden")
    finally:
        conn.close()


def teilnahme_offen(teilnahme: dict) -> bool:
    """True, solange das Zugangsfenster läuft. Ohne Freischaltung: False."""
    bis = teilnahme.get("gueltig_bis")
    if not bis:
        return False
    try:
        return datetime.fromisoformat(bis) > _jetzt()
    except ValueError:
        return False


def anmelden(email: str, passwort: str) -> str | None:
    """Prüft die Zugangsdaten und legt eine Sitzung an. None = abgelehnt.

    Warum keine Unterscheidung zwischen „unbekannt" und „falsches Passwort":
    Die Antwort verrät sonst, welche Adressen Kunde sind.
    """
    try:
        email = _email_normalisieren(email)
    except TeilnehmerFehler:
        return None

    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT id, passwort_hash FROM teilnehmer WHERE email = ?",
            (email,)).fetchone()
        if zeile is None or not zugang.passwort_pruefen(passwort, zeile["passwort_hash"]):
            return None

        klartext, gehasht = zugang.token_erzeugen()
        conn.execute(
            "INSERT INTO sitzung (token_hash, teilnehmer_id, gueltig_bis) "
            "VALUES (?, ?, ?)",
            (gehasht, zeile["id"],
             _iso(_jetzt() + timedelta(hours=SITZUNG_STUNDEN))))
        return klartext
    finally:
        conn.close()


def sitzung_pruefen(token: str) -> dict | None:
    """Der Teilnehmer zu einem Sitzungstoken, oder None."""
    if not token:
        return None
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT t.id, t.email, t.name, t.firma, s.gueltig_bis "
            "FROM sitzung s JOIN teilnehmer t ON t.id = s.teilnehmer_id "
            "WHERE s.token_hash = ?",
            (zugang.token_hashen(token),)).fetchone()
        if zeile is None:
            return None
        try:
            if datetime.fromisoformat(zeile["gueltig_bis"]) <= _jetzt():
                return None
        except ValueError:
            return None
        return {"id": zeile["id"], "email": zeile["email"],
                "name": zeile["name"], "firma": zeile["firma"]}
    finally:
        conn.close()


def abmelden(token: str) -> None:
    """Entwertet eine Sitzung. Ein unbekanntes Token ist kein Fehler."""
    if not token:
        return
    conn = db.verbinden()
    try:
        conn.execute("DELETE FROM sitzung WHERE token_hash = ?",
                     (zugang.token_hashen(token),))
    finally:
        conn.close()


def teilnahmen_von(teilnehmer_id: int) -> list[dict]:
    """Die Teilnahmen eines Teilnehmers, mit `offen` je Eintrag."""
    conn = db.verbinden()
    try:
        teilnahmen = [dict(z) for z in conn.execute(
            "SELECT * FROM teilnahme WHERE teilnehmer_id = ? ORDER BY id",
            (teilnehmer_id,))]
        for tn in teilnahmen:
            tn["offen"] = teilnahme_offen(tn)
        return teilnahmen
    finally:
        conn.close()


def teilnahme(teilnahme_id: int, teilnehmer_id: int) -> dict | None:
    """Eine Teilnahme — aber nur, wenn sie diesem Teilnehmer gehört.

    Der Teilnehmer-Bezug ist Teil der Abfrage, nicht eine Prüfung danach:
    So kann keine Route ihn vergessen.
    """
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM teilnahme WHERE id = ? AND teilnehmer_id = ?",
            (teilnahme_id, teilnehmer_id)).fetchone()
        if zeile is None:
            return None
        eintrag = dict(zeile)
        eintrag["offen"] = teilnahme_offen(eintrag)
        return eintrag
    finally:
        conn.close()
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_teilnehmer.py -v`
Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
git add app/teilnehmer.py tests/test_teilnehmer.py
git commit -m "feat: Teilnehmer, Teilnahmen und Zugangsfenster"
```

---

### Task 4: Prüfungsversuche

**Files:**
- Create: `app/versuche.py`, `tests/test_versuche.py`

**Interfaces:**
- Consumes: `app.db.verbinden()`, `app.pruefung.laden()`, `app.projekte.projekt_dir()`
- Produces:
  - `app.versuche.MAX_VERSUCHE = 3`
  - `app.versuche.VersuchFehler(ValueError)`
  - `zaehlen(teilnahme_id: int) -> int`
  - `bestanden(teilnahme_id: int) -> dict | None` — der bestandene Versuch, falls es einen gibt
  - `starten(teilnahme_id: int) -> int` — id des Versuchs; wirft bei erschöpften Versuchen
  - `auswerten(versuch_id: int, slug: str, antworten: dict[str, int]) -> dict`
  - `liste(teilnahme_id: int) -> list[dict]`

Die Auswertung liest die richtigen Antworten aus `projects/<slug>/pruefung.json` — sie gehen nie an den Browser.

- [ ] **Step 1: Den Test schreiben**

`tests/test_versuche.py`:
```python
"""Prüfungsversuche: zählen, auswerten, begrenzen."""

import json

import pytest

from app import db, projekte, teilnehmer, versuche

PRUEFUNG = {
    "titel": "Abschlussprüfung KI-Verordnung",
    "bestehensgrenze": 70,
    "fragen": [
        {"frage": "Frage eins?", "optionen": ["a", "b", "c"], "richtig": 0,
         "thema": "Level 1", "hinweis": "Weil a."},
        {"frage": "Frage zwei?", "optionen": ["a", "b", "c"], "richtig": 1,
         "thema": "Level 2", "hinweis": "Weil b."},
        {"frage": "Frage drei?", "optionen": ["a", "b", "c"], "richtig": 2,
         "thema": "Level 3", "hinweis": "Weil c."},
        {"frage": "Frage vier?", "optionen": ["a", "b", "c"], "richtig": 0,
         "thema": "Level 4", "hinweis": "Weil a."},
    ],
}


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    """Datenbank und Projektordner, beide temporär."""
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    ziel = tmp_path / "projects"
    ziel.mkdir()
    monkeypatch.setattr(projekte, "PROJECTS", ziel)
    db.init()

    (ziel / "kurs").mkdir()
    (ziel / "kurs" / "pruefung.json").write_text(
        json.dumps(PRUEFUNG), encoding="utf-8")

    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    tnid = teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "AI-SmartCon-Zertifikat")
    teilnehmer.freischalten(tid)
    return tnid


def test_am_anfang_kein_versuch(umgebung):
    assert versuche.zaehlen(umgebung) == 0
    assert versuche.bestanden(umgebung) is None


def test_starten_zaehlt_hoch(umgebung):
    versuche.starten(umgebung)
    assert versuche.zaehlen(umgebung) == 1


def test_alles_richtig_ergibt_hundert_prozent(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    assert ergebnis["prozent"] == 100
    assert ergebnis["bestanden"] is True
    assert ergebnis["treffer"] == 4


def test_die_haelfte_richtig_besteht_nicht(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 0, "3": 1})
    assert ergebnis["prozent"] == 50
    assert ergebnis["bestanden"] is False


def test_genau_auf_der_grenze_besteht(umgebung):
    # 3 von 4 sind 75 Prozent, die Grenze liegt bei 70.
    vid = versuche.starten(umgebung)
    assert versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 1})["bestanden"] is True


def test_fehlende_antwort_zaehlt_als_falsch(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 0})
    assert ergebnis["treffer"] == 1
    assert ergebnis["bestanden"] is False


def test_das_ergebnis_nennt_die_richtige_antwort_erst_hinterher(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 1, "1": 1, "2": 2, "3": 0})
    rueckmeldung = ergebnis["rueckmeldung"]
    assert rueckmeldung[0]["korrekt"] is False
    assert rueckmeldung[0]["richtig"] == 0
    assert rueckmeldung[0]["hinweis"] == "Weil a."


def test_versuch_wird_gespeichert(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    eintrag = versuche.liste(umgebung)[0]
    assert eintrag["prozent"] == 100
    assert eintrag["bestanden"] == 1
    assert eintrag["beendet_am"] is not None


def test_drei_versuche_sind_das_maximum(umgebung):
    for _ in range(versuche.MAX_VERSUCHE):
        vid = versuche.starten(umgebung)
        versuche.auswerten(vid, "kurs", {"0": 1, "1": 0, "2": 0, "3": 1})
    with pytest.raises(versuche.VersuchFehler, match="Versuche"):
        versuche.starten(umgebung)


def test_nach_bestehen_kein_weiterer_versuch(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    with pytest.raises(versuche.VersuchFehler, match="bestanden"):
        versuche.starten(umgebung)


def test_bestanden_liefert_den_versuch(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    b = versuche.bestanden(umgebung)
    assert b is not None
    assert b["prozent"] == 100


def test_ein_offener_versuch_wird_nicht_doppelt_gestartet(umgebung):
    erst = versuche.starten(umgebung)
    zweit = versuche.starten(umgebung)
    assert erst == zweit
    assert versuche.zaehlen(umgebung) == 1


def test_auswerten_eines_beendeten_versuchs_wird_abgewiesen(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 1, "1": 0, "2": 0, "3": 1})
    with pytest.raises(versuche.VersuchFehler, match="abgeschlossen"):
        versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})


def test_unsinnige_antwortwerte_zaehlen_als_falsch(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 99, "1": -1, "2": 2, "3": 0})
    assert ergebnis["treffer"] == 2
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_versuche.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.versuche'`.

- [ ] **Step 3: Implementieren**

`app/versuche.py`:
```python
"""Prüfungsversuche eines Teilnehmers.

Die Auswertung passiert hier, auf dem Server. Die richtigen Antworten stehen
in `projects/<slug>/pruefung.json` und verlassen den Server nicht — eine
Prüfung, deren Lösungen im Browser liegen, taugt nicht als Nachweis.
"""

from datetime import datetime, timezone

from . import db, projekte, pruefung

MAX_VERSUCHE = 3


class VersuchFehler(ValueError):
    """Der Versuch ist nicht zulässig. Die Meldung ist für die Oberfläche."""


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def zaehlen(teilnahme_id: int) -> int:
    conn = db.verbinden()
    try:
        return conn.execute(
            "SELECT count(*) AS n FROM versuch WHERE teilnahme_id = ?",
            (teilnahme_id,)).fetchone()["n"]
    finally:
        conn.close()


def bestanden(teilnahme_id: int) -> dict | None:
    """Der bestandene Versuch, falls es einen gibt."""
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM versuch WHERE teilnahme_id = ? AND bestanden = 1 "
            "ORDER BY beendet_am LIMIT 1", (teilnahme_id,)).fetchone()
        return dict(zeile) if zeile else None
    finally:
        conn.close()


def liste(teilnahme_id: int) -> list[dict]:
    conn = db.verbinden()
    try:
        return [dict(z) for z in conn.execute(
            "SELECT * FROM versuch WHERE teilnahme_id = ? ORDER BY id",
            (teilnahme_id,))]
    finally:
        conn.close()


def _offener(conn, teilnahme_id: int):
    return conn.execute(
        "SELECT * FROM versuch WHERE teilnahme_id = ? AND beendet_am IS NULL "
        "ORDER BY id LIMIT 1", (teilnahme_id,)).fetchone()


def starten(teilnahme_id: int) -> int:
    """Beginnt einen Versuch — oder gibt den offenen zurück.

    Ein Neuladen der Prüfungsseite darf keinen Versuch verbrauchen, deshalb
    zählt ein bereits offener Versuch weiter statt einen zweiten anzulegen.
    """
    if bestanden(teilnahme_id):
        raise VersuchFehler("Diese Prüfung ist bereits bestanden")

    conn = db.verbinden()
    try:
        offen = _offener(conn, teilnahme_id)
        if offen:
            return offen["id"]
        anzahl = conn.execute(
            "SELECT count(*) AS n FROM versuch WHERE teilnahme_id = ?",
            (teilnahme_id,)).fetchone()["n"]
        if anzahl >= MAX_VERSUCHE:
            raise VersuchFehler(
                f"Alle {MAX_VERSUCHE} Versuche sind aufgebraucht")
        cur = conn.execute(
            "INSERT INTO versuch (teilnahme_id, begonnen_am) VALUES (?, ?)",
            (teilnahme_id, _jetzt()))
        return cur.lastrowid
    finally:
        conn.close()


def auswerten(versuch_id: int, slug: str, antworten: dict) -> dict:
    """Wertet die Antworten gegen pruefung.json aus und schließt den Versuch.

    `antworten` bildet den Fragenindex als String auf die gewählte Option ab —
    so kommt es aus einem Formular. Fehlende, unbekannte oder unsinnige Werte
    zählen als falsch; ein Formular ohne Antwort darf nicht abstürzen.
    """
    d = projekte.projekt_dir(slug)
    if d is None:
        raise VersuchFehler(f"Schulung „{slug}“ nicht gefunden")
    daten = pruefung.laden(d / "pruefung.json")
    fragen = daten["fragen"]

    conn = db.verbinden()
    try:
        zeile = conn.execute("SELECT * FROM versuch WHERE id = ?",
                             (versuch_id,)).fetchone()
        if zeile is None:
            raise VersuchFehler("Versuch nicht gefunden")
        if zeile["beendet_am"] is not None:
            raise VersuchFehler("Dieser Versuch ist bereits abgeschlossen")

        rueckmeldung = []
        treffer = 0
        for nr, frage in enumerate(fragen):
            gewaehlt = antworten.get(str(nr))
            try:
                gewaehlt = int(gewaehlt)
            except (TypeError, ValueError):
                gewaehlt = None
            korrekt = gewaehlt == frage["richtig"]
            if korrekt:
                treffer += 1
            rueckmeldung.append({
                "frage": frage["frage"],
                "gewaehlt": gewaehlt,
                "richtig": frage["richtig"],
                "korrekt": korrekt,
                "hinweis": str(frage.get("hinweis", "")),
            })

        prozent = round(treffer / len(fragen) * 100)
        geschafft = prozent >= daten["bestehensgrenze"]
        conn.execute(
            "UPDATE versuch SET beendet_am = ?, prozent = ?, bestanden = ? "
            "WHERE id = ?",
            (_jetzt(), prozent, 1 if geschafft else 0, versuch_id))

        return {"prozent": prozent, "bestanden": geschafft, "treffer": treffer,
                "gesamt": len(fragen), "grenze": daten["bestehensgrenze"],
                "rueckmeldung": rueckmeldung}
    finally:
        conn.close()
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_versuche.py -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add app/versuche.py tests/test_versuche.py
git commit -m "feat: Pruefungsversuche mit serverseitiger Auswertung"
```

---

### Task 5: Verwaltungsrouten und Reiter „Teilnehmer"

**Files:**
- Create: `app/verwaltung.py`, `tests/test_verwaltung.py`
- Modify: `app/main.py`, `static/index.html`, `static/app.js`, `static/style.css`

**Interfaces:**
- Consumes: `app.teilnehmer.*`, `app.versuche.*`, `app.projekte.liste()`
- Produces:
  - `app.verwaltung.router: APIRouter` mit Präfix `/api/verwaltung`
  - `GET /api/verwaltung/teilnehmer` → `{"teilnehmer": [...]}`
  - `POST /api/verwaltung/teilnehmer` (JSON: `email`, `name`, `firma`) → `{"id": int}`
  - `POST /api/verwaltung/teilnehmer/{tid}/teilnahme` (JSON: `slug`) → `{"id": int}`
  - `POST /api/verwaltung/teilnehmer/{tid}/freischalten` (JSON: `tage`) → `{"passwort": str}`
  - `POST /api/verwaltung/teilnahme/{tnid}/verlaengern` (JSON: `tage`) → `{"ok": true}`

- [ ] **Step 1: Den Test schreiben**

`tests/test_verwaltung.py`:
```python
"""Verwaltungsrouten für Teilnehmer und Freischaltung."""

import json

import pytest

from app import db, projekte

PRUEFUNG = {
    "titel": "Abschlussprüfung", "bestehensgrenze": 70,
    "fragen": [{"frage": "F?", "optionen": ["a", "b", "c"], "richtig": 0,
                "thema": "Level 1", "hinweis": "Weil a."}],
}


@pytest.fixture
def verwaltung(client, projekte_tmp, tmp_path, monkeypatch):
    """TestClient mit temporärer Datenbank und einer fertigen Schulung."""
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()
    d = projekte_tmp / "ki-pflichtschulung"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "KI-Pflichtschulung"}))
    (d / "pruefung.json").write_text(json.dumps(PRUEFUNG), encoding="utf-8")
    (d / "status.json").write_text(json.dumps({"phase": "fertig"}))
    return client


def test_teilnehmer_anlegen_und_lesen(verwaltung):
    antwort = verwaltung.post("/api/verwaltung/teilnehmer",
                              json={"email": "anna@example.org", "name": "Anna",
                                    "firma": "Beispiel GmbH"})
    assert antwort.status_code == 201
    liste = verwaltung.get("/api/verwaltung/teilnehmer").json()["teilnehmer"]
    assert liste[0]["email"] == "anna@example.org"
    assert liste[0]["hat_zugang"] is False


def test_doppelte_email_ist_409(verwaltung):
    verwaltung.post("/api/verwaltung/teilnehmer",
                    json={"email": "anna@example.org", "name": "Anna"})
    antwort = verwaltung.post("/api/verwaltung/teilnehmer",
                              json={"email": "anna@example.org", "name": "Anna"})
    assert antwort.status_code == 409


def test_unsinnige_email_ist_400(verwaltung):
    antwort = verwaltung.post("/api/verwaltung/teilnehmer",
                              json={"email": "keine-mail", "name": "Anna"})
    assert antwort.status_code == 400


def test_teilnahme_zuordnen(verwaltung):
    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    antwort = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                              json={"slug": "ki-pflichtschulung"})
    assert antwort.status_code == 201
    eintrag = verwaltung.get("/api/verwaltung/teilnehmer").json()["teilnehmer"][0]
    assert eintrag["teilnahmen"][0]["slug"] == "ki-pflichtschulung"


def test_teilnahme_zu_unbekannter_schulung_ist_404(verwaltung):
    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    antwort = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                              json={"slug": "gibt-es-nicht"})
    assert antwort.status_code == 404


def test_teilnahme_ohne_pruefung_ist_400(verwaltung, projekte_tmp):
    # Ohne pruefung.json gäbe es nichts abzulegen — das gehört vorher gesagt.
    d = projekte_tmp / "ohne-pruefung"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "Ohne"}))
    (d / "status.json").write_text(json.dumps({"phase": "fertig"}))

    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    antwort = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                              json={"slug": "ohne-pruefung"})
    assert antwort.status_code == 400
    assert "Prüfung" in antwort.json()["detail"]


def test_freischalten_liefert_das_passwort(verwaltung):
    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                    json={"slug": "ki-pflichtschulung"})

    antwort = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/freischalten",
                              json={"tage": 30})
    assert antwort.status_code == 200
    assert len(antwort.json()["passwort"]) == 12


def test_freischalten_eines_unbekannten_ist_404(verwaltung):
    assert verwaltung.post("/api/verwaltung/teilnehmer/999/freischalten",
                           json={"tage": 30}).status_code == 404


def test_unsinnige_tage_sind_400(verwaltung):
    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    for tage in (0, -5, 4000, "dreißig"):
        antwort = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/freischalten",
                                  json={"tage": tage})
        assert antwort.status_code == 400, f"tage={tage!r} hätte 400 sein müssen"


def test_verlaengern(verwaltung):
    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    tnid = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                           json={"slug": "ki-pflichtschulung"}).json()["id"]
    verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/freischalten", json={"tage": 1})

    assert verwaltung.post(f"/api/verwaltung/teilnahme/{tnid}/verlaengern",
                           json={"tage": 30}).status_code == 200


def test_liste_nennt_den_pruefungsstand(verwaltung):
    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                    json={"slug": "ki-pflichtschulung"})
    t = verwaltung.get("/api/verwaltung/teilnehmer").json()["teilnehmer"][0]["teilnahmen"][0]
    assert t["versuche"] == 0
    assert t["bestanden"] is False
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_verwaltung.py -v`
Expected: FAIL, alle Routen liefern 404.

- [ ] **Step 3: Implementieren**

`app/verwaltung.py`:
```python
"""Verwaltungsrouten für Teilnehmer, Teilnahmen und Freischaltung.

Liegt hinter demselben Zugriffsschutz wie der Rest der App. Das Portal —
der Bereich, den Kunden sehen — ist in app/portal_routes.py und schützt sich
selbst.
"""

from fastapi import APIRouter, HTTPException

from . import projekte, teilnehmer, versuche

router = APIRouter(prefix="/api/verwaltung")

MAX_TAGE = 3650


def _tage(body: dict | None, vorgabe: int = 30) -> int:
    tage = (body or {}).get("tage", vorgabe)
    if not isinstance(tage, int) or isinstance(tage, bool) \
            or not 1 <= tage <= MAX_TAGE:
        raise HTTPException(
            400, f"„tage“ muss eine ganze Zahl zwischen 1 und {MAX_TAGE} sein")
    return tage


@router.get("/teilnehmer")
def api_teilnehmer_liste():
    """Alle Teilnehmer mit Teilnahmen, Versuchszahl und Prüfungsstand."""
    eintraege = teilnehmer.liste()
    for t in eintraege:
        for tn in t["teilnahmen"]:
            tn["versuche"] = versuche.zaehlen(tn["id"])
            tn["bestanden"] = versuche.bestanden(tn["id"]) is not None
    return {"teilnehmer": eintraege}


@router.post("/teilnehmer", status_code=201)
def api_teilnehmer_neu(body: dict):
    try:
        tid = teilnehmer.anlegen(
            str(body.get("email", "")), str(body.get("name", "")),
            str(body.get("firma", "")))
    except teilnehmer.TeilnehmerFehler as e:
        # „bereits angelegt“ ist ein Konflikt, alles andere ein Eingabefehler.
        raise HTTPException(409 if "bereits" in str(e) else 400, str(e))
    return {"id": tid}


@router.post("/teilnehmer/{tid}/teilnahme", status_code=201)
def api_teilnahme_neu(tid: int, body: dict):
    """Ordnet dem Teilnehmer eine fertige Schulung zu."""
    slug = str(body.get("slug", "")).strip()
    d = projekte.projekt_dir(slug)
    if d is None:
        raise HTTPException(404, f"Schulung „{slug}“ nicht gefunden")
    if not (d / "pruefung.json").is_file():
        raise HTTPException(
            400, "Für diese Schulung gibt es noch keine Prüfung — erst im "
                 "Projekt „Prüfung erzeugen“ starten")

    p = projekte.get(slug)
    titel = (p["briefing"].get("thema") or slug) if p else slug
    # Mit Prüfung heißt der Nachweis Zertifikat, sonst Teilnahmebestätigung.
    nachweis = "AI-SmartCon-Zertifikat"
    try:
        tnid = teilnehmer.teilnahme_anlegen(tid, slug, titel, nachweis)
    except teilnehmer.TeilnehmerFehler as e:
        raise HTTPException(409 if "bereits" in str(e) else 404, str(e))
    return {"id": tnid}


@router.post("/teilnehmer/{tid}/freischalten")
def api_freischalten(tid: int, body: dict | None = None):
    """Erzeugt das Passwort und öffnet das Zugangsfenster.

    Der Klartext wird genau hier einmal zurückgegeben und danach nie wieder.
    """
    tage = _tage(body)
    try:
        passwort = teilnehmer.freischalten(tid, tage=tage)
    except teilnehmer.TeilnehmerFehler as e:
        raise HTTPException(404, str(e))
    return {"passwort": passwort, "tage": tage}


@router.post("/teilnahme/{tnid}/verlaengern")
def api_verlaengern(tnid: int, body: dict | None = None):
    tage = _tage(body)
    try:
        teilnehmer.verlaengern(tnid, tage=tage)
    except teilnehmer.TeilnehmerFehler as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "tage": tage}
```

In `app/main.py` nach der App-Erzeugung ergänzen:
```python
from . import db, verwaltung  # zum bestehenden Import-Block hinzufügen

db.init()
app.include_router(verwaltung.router)
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_verwaltung.py -v`
Expected: 11 passed.

- [ ] **Step 5: Reiter „Teilnehmer" anlegen**

In `static/index.html` in die Reiterleiste nach `tab-decks`:
```html
    <button id="tab-teilnehmer" class="tab" data-tab="teilnehmer">Teilnehmer</button>
```

Neue Ansicht nach `#view-decks`:
```html
  <section id="view-teilnehmer" class="view">
    <div class="view-kopf">
      <h2>Teilnehmer</h2>
      <button id="btn-teilnehmer-neu">Teilnehmer anlegen</button>
    </div>
    <p class="muted">Zugang zum Portal unter <code>/portal</code>. Das Passwort
      wird beim Freischalten einmal angezeigt und ist danach nicht mehr
      abrufbar.</p>

    <form id="teilnehmer-form" hidden>
      <label>E-Mail <input name="email" type="email" required></label>
      <label>Name <input name="name" required></label>
      <label>Firma <input name="firma"></label>
      <div class="zeile">
        <button type="submit">Anlegen</button>
        <button type="button" id="btn-teilnehmer-abbrechen">Abbrechen</button>
        <span id="teilnehmer-status" class="muted"></span>
      </div>
    </form>

    <div id="passwort-kasten" class="karte" hidden>
      <p><strong>Passwort — jetzt notieren.</strong> Es wird nicht wieder
        angezeigt; gespeichert ist nur der Hash.</p>
      <p id="passwort-wert" class="passwort"></p>
      <p id="passwort-fehler" class="muted"></p>
      <div class="zeile">
        <button type="button" id="btn-passwort-schliessen">Schließen</button>
      </div>
    </div>

    <div id="teilnehmer-liste"></div>
  </section>
```

Dazu in `static/style.css`:
```css
.passwort {
  font-family: ui-monospace, monospace;
  font-size: 22px;
  letter-spacing: .08em;
  user-select: all;
  word-break: break-all;
}
.passwort[hidden] { display: none; }
```

`?v=` für beide Assets hochzählen.

- [ ] **Step 6: Logik ergänzen**

An `static/app.js` anhängen:
```javascript
/* ---------- Teilnehmer ---------- */

function zeigePasswort(passwort, fehler) {
  /* Einmalige Anzeige des Passworts, bzw. eine Fehlermeldung.
     Kein alert/prompt: ein modaler Dialog blockiert die Browser-Automatisierung,
     mit der diese Oberfläche geprüft wird. */
  const kasten = document.getElementById('passwort-kasten');
  const feld = document.getElementById('passwort-wert');
  const meldung = document.getElementById('passwort-fehler');
  meldung.textContent = fehler || '';
  feld.textContent = passwort || '';
  kasten.hidden = !(passwort || fehler);
}

document.getElementById('btn-passwort-schliessen').addEventListener('click', () => {
  zeigePasswort('', '');
});

async function ladeTeilnehmer() {
  const antwort = await fetch('/api/verwaltung/teilnehmer');
  const ziel = document.getElementById('teilnehmer-liste');
  if (!antwort.ok) { ziel.innerHTML = '<p class="muted">Nicht lesbar.</p>'; return; }
  const liste = (await antwort.json()).teilnehmer;
  if (!liste.length) {
    ziel.innerHTML = '<p class="muted">Noch niemand angelegt.</p>';
    return;
  }
  ziel.innerHTML = liste.map((t) => `
    <div class="karte">
      <strong>${esc(t.name)}</strong> <span class="muted">${esc(t.email)}</span>
      ${t.firma ? `<span class="muted"> · ${esc(t.firma)}</span>` : ''}
      <span class="badge">${t.hat_zugang ? 'Zugang aktiv' : 'kein Zugang'}</span>
      <div class="teilnahmen">
        ${t.teilnahmen.map((tn) => `
          <div class="zeile">
            <span>${esc(tn.titel)}</span>
            <span class="muted">${tn.versuche}/3 Versuche${tn.bestanden ? ' · bestanden' : ''}</span>
            <span class="muted">${tn.offen ? 'offen bis ' + esc((tn.gueltig_bis || '').slice(0, 10)) : 'geschlossen'}</span>
            <button data-verlaengern="${tn.id}">30 Tage verlängern</button>
          </div>`).join('') || '<p class="muted">Noch keine Schulung zugeordnet.</p>'}
      </div>
      <div class="zeile">
        <select data-schulung="${t.id}"></select>
        <button data-zuordnen="${t.id}">Schulung zuordnen</button>
        <button data-freischalten="${t.id}">Freischalten</button>
      </div>
    </div>`).join('');

  // Schulungen mit Prüfung in die Auswahlfelder
  const projekteAntwort = await fetch('/api/projekte');
  const fertige = (await projekteAntwort.json()).projekte
    .filter((p) => p.art !== 'praesentation' && p.phase === 'fertig');
  ziel.querySelectorAll('[data-schulung]').forEach((sel) => {
    sel.innerHTML = fertige.map((p) =>
      `<option value="${esc(p.slug)}">${esc(p.thema || p.slug)}</option>`).join('')
      || '<option value="">keine fertige Schulung</option>';
  });

  ziel.querySelectorAll('[data-zuordnen]').forEach((el) => {
    el.addEventListener('click', async () => {
      const tid = el.dataset.zuordnen;
      const slug = ziel.querySelector(`[data-schulung="${tid}"]`).value;
      const a = await fetch(`/api/verwaltung/teilnehmer/${tid}/teilnahme`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ slug }) });
      if (!a.ok) zeigePasswort('', (await a.json()).detail);
      ladeTeilnehmer();
    });
  });

  ziel.querySelectorAll('[data-freischalten]').forEach((el) => {
    el.addEventListener('click', async () => {
      const a = await fetch(`/api/verwaltung/teilnehmer/${el.dataset.freischalten}/freischalten`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tage: 30 }) });
      const e = await a.json();
      if (!a.ok) { zeigePasswort('', e.detail); return; }
      // Einmalige Anzeige: danach ist der Klartext nicht mehr zu bekommen.
      // Bewusst kein window.prompt/alert — ein modaler Dialog blockiert jede
      // Browser-Automatisierung, mit der diese Oberfläche später geprüft wird.
      zeigePasswort(e.passwort, '');
      ladeTeilnehmer();
    });
  });

  ziel.querySelectorAll('[data-verlaengern]').forEach((el) => {
    el.addEventListener('click', async () => {
      await fetch(`/api/verwaltung/teilnahme/${el.dataset.verlaengern}/verlaengern`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tage: 30 }) });
      ladeTeilnehmer();
    });
  });
}

document.getElementById('btn-teilnehmer-neu').addEventListener('click', () => {
  document.getElementById('teilnehmer-form').hidden = false;
});
document.getElementById('btn-teilnehmer-abbrechen').addEventListener('click', () => {
  document.getElementById('teilnehmer-form').hidden = true;
});
document.getElementById('teilnehmer-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const status = document.getElementById('teilnehmer-status');
  const daten = Object.fromEntries(new FormData(e.target));
  const a = await fetch('/api/verwaltung/teilnehmer',
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(daten) });
  const ergebnis = await a.json();
  if (!a.ok) { status.textContent = `Fehler: ${ergebnis.detail}`; return; }
  status.textContent = '';
  e.target.reset();
  e.target.hidden = true;
  ladeTeilnehmer();
});
```

Im Reiter-Umschalter beim Wechsel auf `teilnehmer` `ladeTeilnehmer()` aufrufen.

In `static/style.css`:
```css
.teilnahmen { margin: 10px 0; }
.teilnahmen[hidden] { display: none; }
```

- [ ] **Step 7: Prüfen**

`node --check static/app.js`, dann Container bauen (vorher: kein Agent aktiv) und in der Oberfläche einen Teilnehmer anlegen, ihm eine Schulung mit Prüfung zuordnen und freischalten. Bei 390 px und 320 px auf Überlauf prüfen.

- [ ] **Step 8: Commit**

```bash
git add app/verwaltung.py app/main.py static/ tests/test_verwaltung.py
git commit -m "feat: Verwaltung fuer Teilnehmer und Zugaenge"
```

---

# Etappe 5 — Das Portal

Ziel: Ein Teilnehmer meldet sich an, arbeitet die Lerneinheit durch, legt die Prüfung ab und lädt bei Bestehen seinen Nachweis. Erfolgskriterium: der Durchlauf funktioniert in einem privaten Browserfenster, ohne dass die Lösungen im Quelltext auffindbar sind.

### Task 6: Portal-Seiten als HTML

**Files:**
- Create: `app/portal.py`, `tests/test_portal.py`

**Interfaces:**
- Produces:
  - `app.portal.seite(titel: str, inhalt: str, teilnehmer: dict | None = None) -> str` — Rahmen im CI
  - `app.portal.login_seite(fehler: str = "") -> str`
  - `app.portal.kursliste(teilnehmer: dict, teilnahmen: list[dict]) -> str`
  - `app.portal.kurs_seite(teilnehmer: dict, teilnahme: dict, versuche_offen: int, bestanden: bool) -> str`
  - `app.portal.pruefung_seite(teilnahme: dict, fragen: list[dict], versuch_nr: int, max_versuche: int) -> str`
  - `app.portal.ergebnis_seite(teilnahme: dict, ergebnis: dict, weitere_versuche: int) -> str`
  - `app.portal.zertifikat_seite(teilnehmer: dict, teilnahme: dict, versuch: dict) -> str`

Reine Funktionen von Daten zu HTML — ohne Server testbar, wie `app/pruefung.py`.

- [ ] **Step 1: Den Test schreiben**

`tests/test_portal.py`:
```python
"""Portal-Seiten. Reine HTML-Erzeugung, kein Server."""

from app import portal

TEILNEHMER = {"id": 1, "name": "Anna Beispiel", "email": "anna@example.org",
              "firma": "Beispiel GmbH"}
TEILNAHME = {"id": 7, "slug": "kurs", "titel": "KI-Pflichtschulung",
             "nachweis": "AI-SmartCon-Zertifikat", "gueltig_bis": "2026-09-30T12:00:00+00:00",
             "offen": True}
FRAGEN = [
    {"frage": "Seit wann wird Art. 4 durchgesetzt?",
     "optionen": ["seit 02.08.2026", "seit 2027", "gar nicht"], "thema": "Level 1"},
    {"frage": "Was leistet ein AVV <nicht>?",
     "optionen": ["Erlaubnis", "Weisung", "Vertraulichkeit"], "thema": "Level 2"},
]


def test_rahmen_ist_vollstaendig_und_ohne_fremdquellen():
    html = portal.seite("Titel", "<p>Inhalt</p>")
    assert html.startswith("<!doctype html>")
    assert "</html>" in html
    assert "http://" not in html and "https://" not in html
    assert "<script src=" not in html


def test_rahmen_traegt_die_ci_farben():
    html = portal.seite("Titel", "")
    for farbe in ("#060611", "#c9a84c", "#f6f1e8"):
        assert farbe in html


def test_login_seite_hat_die_felder():
    html = portal.login_seite()
    assert 'name="email"' in html
    assert 'name="passwort"' in html
    assert 'type="password"' in html


def test_login_fehler_wird_angezeigt_und_maskiert():
    html = portal.login_seite("E-Mail oder Passwort <falsch>")
    assert "&lt;falsch&gt;" in html
    assert "<falsch>" not in html


def test_kursliste_nennt_die_teilnahmen():
    html = portal.kursliste(TEILNEHMER, [TEILNAHME])
    assert "KI-Pflichtschulung" in html
    assert "Anna Beispiel" in html


def test_geschlossene_teilnahme_ist_nicht_verlinkt():
    zu = {**TEILNAHME, "offen": False}
    html = portal.kursliste(TEILNEHMER, [zu])
    assert "/portal/kurs/7" not in html
    assert "abgelaufen" in html.lower()


def test_pruefungsseite_zeigt_die_fragen_ohne_loesung():
    html = portal.pruefung_seite(TEILNAHME, FRAGEN, versuch_nr=1, max_versuche=3)
    assert "Seit wann wird Art. 4 durchgesetzt?" in html
    assert "seit 02.08.2026" in html
    # Entscheidend: nichts über die richtige Antwort im Dokument.
    assert "richtig" not in html
    assert "hinweis" not in html.lower()


def test_pruefungsseite_maskiert_html_in_fragen():
    html = portal.pruefung_seite(TEILNAHME, FRAGEN, versuch_nr=1, max_versuche=3)
    assert "&lt;nicht&gt;" in html
    assert "<nicht>" not in html


def test_pruefungsseite_nennt_den_versuch():
    html = portal.pruefung_seite(TEILNAHME, FRAGEN, versuch_nr=2, max_versuche=3)
    assert "2" in html and "3" in html


def test_ergebnisseite_zeigt_prozent_und_urteil():
    ergebnis = {"prozent": 80, "bestanden": True, "treffer": 4, "gesamt": 5,
                "grenze": 70, "rueckmeldung": [
                    {"frage": "F?", "gewaehlt": 0, "richtig": 0, "korrekt": True,
                     "hinweis": "Weil a."}]}
    html = portal.ergebnis_seite(TEILNAHME, ergebnis, weitere_versuche=0)
    assert "80" in html
    assert "bestanden" in html.lower()
    assert "Weil a." in html


def test_ergebnisseite_nennt_die_restversuche_bei_nichtbestehen():
    ergebnis = {"prozent": 40, "bestanden": False, "treffer": 2, "gesamt": 5,
                "grenze": 70, "rueckmeldung": []}
    html = portal.ergebnis_seite(TEILNAHME, ergebnis, weitere_versuche=2)
    assert "2" in html
    assert "nicht bestanden" in html.lower()


def test_zertifikat_nennt_person_kurs_und_datum():
    versuch = {"prozent": 90, "beendet_am": "2026-08-08T12:00:00+00:00"}
    html = portal.zertifikat_seite(TEILNEHMER, TEILNAHME, versuch)
    assert "Anna Beispiel" in html
    assert "KI-Pflichtschulung" in html
    assert "08.08.2026" in html
    assert "AI-SmartCon-Zertifikat" in html


def test_zertifikat_behauptet_keine_staatliche_anerkennung():
    versuch = {"prozent": 90, "beendet_am": "2026-08-08T12:00:00+00:00"}
    html = portal.zertifikat_seite(TEILNEHMER, TEILNAHME, versuch).lower()
    for verboten in ("staatlich anerkannt", "azav", "bildungsgutschein",
                     "zertifiziert nach"):
        assert verboten not in html


def test_zertifikat_ist_druckbar():
    versuch = {"prozent": 90, "beendet_am": "2026-08-08T12:00:00+00:00"}
    html = portal.zertifikat_seite(TEILNEHMER, TEILNAHME, versuch)
    assert "@media print" in html


def test_kursseite_bettet_die_lerneinheit_ein():
    html = portal.kurs_seite(TEILNEHMER, TEILNAHME, versuche_offen=3, bestanden=False)
    assert 'src="/portal/kurs/7/datei"' in html
    assert "/portal/kurs/7/pruefung" in html


def test_kursseite_zeigt_nach_bestehen_den_nachweis_statt_der_pruefung():
    html = portal.kurs_seite(TEILNEHMER, TEILNAHME, versuche_offen=0, bestanden=True)
    assert "/portal/kurs/7/zertifikat" in html
    assert "/portal/kurs/7/pruefung" not in html


def test_kursseite_ohne_versuche_bietet_keine_pruefung_an():
    html = portal.kurs_seite(TEILNEHMER, TEILNAHME, versuche_offen=0, bestanden=False)
    assert "/portal/kurs/7/pruefung" not in html
    assert "aufgebraucht" in html.lower()
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_portal.py -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'app.portal'`.

- [ ] **Step 3: Implementieren**

`app/portal.py` — Aufbau wie `app/pruefung.py`: ein `_html.escape` für jeden Fremdtext, CSS inline, keine Fremdquellen. Der Rahmen:

```python
"""Die Seiten des Teilnehmer-Portals.

Reine Funktionen von Daten zu HTML — ohne Server testbar. Die Routen liegen
in app/portal_routes.py.

Wichtigste Regel: Auf der Prüfungsseite steht nichts über die richtige
Antwort. Weder im Markup, noch in einem Attribut, noch in einem Skript.
"""

import html as _html
from datetime import datetime

# AI-SmartCon-CI, wie in app/pruefung.py
FARBEN = {
    "hintergrund": "#060611", "panel": "#1a1a22", "akzent": "#c9a84c",
    "akzent_hell": "#e0c274", "text": "#f6f1e8", "text_sekundaer": "#d8cdb4",
}

_STIL = f"""
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 16px; background: {FARBEN['hintergrund']};
    color: {FARBEN['text']}; font-family: Inter, system-ui, sans-serif;
    line-height: 1.5; overflow-wrap: break-word;
  }}
  main {{ max-width: 760px; margin: 0 auto; }}
  a {{ color: {FARBEN['akzent']}; }}
  h1 {{ font-size: 28px; line-height: 1.2; margin: 0 0 8px; }}
  .kopf {{
    border-bottom: 3px solid {FARBEN['akzent']}; padding-bottom: 16px;
    margin-bottom: 24px; display: flex; flex-wrap: wrap; gap: 12px;
    align-items: baseline; justify-content: space-between;
  }}
  .wortmarke {{ font-weight: 700; letter-spacing: .02em; }}
  .muted {{ color: {FARBEN['text_sekundaer']}; font-size: 14px; }}
  .karte {{
    background: {FARBEN['panel']}; border: 1px solid {FARBEN['akzent']};
    border-radius: 14px; padding: 20px; margin-bottom: 16px;
  }}
  .karte[hidden] {{ display: none; }}
  .zeile {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
  label {{ display: block; margin-bottom: 12px; }}
  label[hidden] {{ display: none; }}
  input[type=email], input[type=password] {{
    width: 100%; padding: 12px; border-radius: 10px;
    border: 1px solid {FARBEN['akzent']}; background: rgba(30,30,58,.5);
    color: {FARBEN['text']}; font-size: 16px;
  }}
  button, .knopf {{
    background: {FARBEN['akzent']}; color: #1a1a22; border: 0;
    border-radius: 10px; padding: 13px 22px; font-size: 15px; font-weight: 600;
    cursor: pointer; text-decoration: none; display: inline-block;
  }}
  button:hover, .knopf:hover {{ background: {FARBEN['akzent_hell']}; }}
  .option {{
    display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px;
    border-radius: 10px; background: rgba(255,255,255,.04); cursor: pointer;
  }}
  .option[hidden] {{ display: none; }}
  .option span {{ min-width: 0; }}
  .thema {{
    color: {FARBEN['akzent']}; font-size: 11px; letter-spacing: .14em;
    text-transform: uppercase; margin: 0 0 8px;
  }}
  .korrekt {{ border-color: #4ade80; }}
  .falsch {{ border-color: #f87171; }}
  .note {{ font-size: 34px; font-weight: 700; color: {FARBEN['akzent']}; }}
"""


def seite(titel: str, inhalt: str, teilnehmer: dict | None = None) -> str:
    """Der gemeinsame Rahmen: Kopf mit Wortmarke, Inhalt, Abmelden."""
    rechts = ""
    if teilnehmer:
        rechts = (f'<span class="muted">{_html.escape(teilnehmer["name"])} · '
                  f'<a href="/portal/abmelden">abmelden</a></span>')
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(titel)} · AI-SmartCon</title>
<style>{_STIL}</style>
</head>
<body>
<main>
  <div class="kopf">
    <span class="wortmarke">AI-SmartCon</span>
    {rechts}
  </div>
{inhalt}
</main>
</body>
</html>
"""
```

Die übrigen Funktionen, an dieselbe Datei angehängt:

```python
def _datum(iso: str) -> str:
    """ISO-Zeitstempel als deutsches Datum. Unlesbares bleibt unverändert."""
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(iso)


def login_seite(fehler: str = "") -> str:
    """Die Anmeldung. Ohne Hinweis darauf, ob es die Adresse gibt."""
    meldung = (f'<p class="muted" style="color:#f87171">{_html.escape(fehler)}</p>'
               if fehler else "")
    inhalt = f"""  <h1>Anmeldung</h1>
  <p class="muted">Zugangsdaten haben Sie nach der Buchung per E-Mail erhalten.</p>
  <div class="karte">
    {meldung}
    <form method="post" action="/portal/anmelden">
      <label>E-Mail
        <input name="email" type="email" autocomplete="username" required>
      </label>
      <label>Passwort
        <input name="passwort" type="password" autocomplete="current-password" required>
      </label>
      <div class="zeile"><button type="submit">Anmelden</button></div>
    </form>
  </div>
  <p class="muted">Passwort verloren? Melden Sie sich bei AI-SmartCon, wir
    schalten einen neuen Zugang frei.</p>"""
    return seite("Anmeldung", inhalt)


def kursliste(teilnehmer: dict, teilnahmen: list[dict]) -> str:
    """Die Kurse einer Person. Geschlossene Teilnahmen sind nicht verlinkt."""
    if not teilnahmen:
        karten = ('<p class="muted">Für Sie ist noch keine Schulung '
                  'freigeschaltet.</p>')
    else:
        stuecke = []
        for tn in teilnahmen:
            titel = _html.escape(str(tn["titel"]))
            if tn.get("offen"):
                stuecke.append(f"""    <div class="karte">
      <h2>{titel}</h2>
      <p class="muted">Zugang bis {_datum(tn.get("gueltig_bis") or "")}</p>
      <div class="zeile">
        <a class="knopf" href="/portal/kurs/{int(tn["id"])}">Zur Schulung</a>
      </div>
    </div>""")
            else:
                stuecke.append(f"""    <div class="karte">
      <h2>{titel}</h2>
      <p class="muted">Der Zugang ist abgelaufen. Wenden Sie sich an
        AI-SmartCon, wenn Sie ihn verlängern möchten.</p>
    </div>""")
        karten = "\n".join(stuecke)

    inhalt = f"""  <h1>Ihre Schulungen</h1>
{karten}"""
    return seite("Ihre Schulungen", inhalt, teilnehmer)


def kurs_seite(teilnehmer: dict, teilnahme: dict, versuche_offen: int,
               bestanden: bool) -> str:
    """Die Lerneinheit im Rahmen, plus der Weg zur Prüfung."""
    tnid = int(teilnahme["id"])
    if bestanden:
        pruefungsteil = f"""    <p>Sie haben die Prüfung bestanden.</p>
      <div class="zeile">
        <a class="knopf" href="/portal/kurs/{tnid}/zertifikat">Nachweis anzeigen</a>
      </div>"""
    elif versuche_offen > 0:
        wort = "Versuch" if versuche_offen == 1 else "Versuche"
        pruefungsteil = f"""    <p>Sie haben noch {versuche_offen} {wort}.</p>
      <div class="zeile">
        <a class="knopf" href="/portal/kurs/{tnid}/pruefung">Prüfung starten</a>
      </div>"""
    else:
        pruefungsteil = """    <p>Alle Versuche sind aufgebraucht. Wenden Sie sich
        an AI-SmartCon, wenn Sie die Prüfung erneut ablegen möchten.</p>"""

    inhalt = f"""  <h1>{_html.escape(str(teilnahme["titel"]))}</h1>
  <div class="karte">
    <iframe src="/portal/kurs/{tnid}/datei" title="Lerneinheit"
            style="width:100%;height:70vh;border:0;border-radius:10px;background:#fff"></iframe>
  </div>
  <div class="karte">
    <h2>Abschlussprüfung</h2>
{pruefungsteil}
  </div>
  <p class="muted"><a href="/portal/kurse">Zurück zur Übersicht</a></p>"""
    return seite(str(teilnahme["titel"]), inhalt, teilnehmer)


def pruefung_seite(teilnahme: dict, fragen: list[dict], versuch_nr: int,
                   max_versuche: int) -> str:
    """Die Fragen. Ohne jede Angabe darüber, welche Antwort richtig ist.

    Das ist die Regel, an der diese Seite hängt: keine Lösung im Markup, in
    keinem Attribut, in keinem Skript. Deshalb bekommt der Aufrufer die
    Fragen auch ohne die Felder „richtig" und „hinweis" gereicht.
    """
    stuecke = []
    for nr, frage in enumerate(fragen):
        optionen = "\n".join(
            f'          <label class="option">'
            f'<input type="radio" name="f{nr}" value="{i}" required> '
            f'<span>{_html.escape(str(o))}</span></label>'
            for i, o in enumerate(frage["optionen"]))
        stuecke.append(f"""      <li class="karte">
        <p class="thema">{_html.escape(str(frage.get("thema", "")))}</p>
        <p><strong>{_html.escape(str(frage["frage"]))}</strong></p>
        <div>
{optionen}
        </div>
      </li>""")

    inhalt = f"""  <h1>Abschlussprüfung</h1>
  <p class="muted">{_html.escape(str(teilnahme["titel"]))} · Versuch
    {versuch_nr} von {max_versuche} · {len(fragen)} Fragen · je genau eine
    Antwort ist richtig.</p>
  <form method="post" action="/portal/kurs/{int(teilnahme["id"])}/pruefung">
    <ol style="list-style:none;padding:0">
{chr(10).join(stuecke)}
    </ol>
    <div class="zeile"><button type="submit">Prüfung abgeben</button></div>
  </form>"""
    return seite("Abschlussprüfung", inhalt)


def ergebnis_seite(teilnahme: dict, ergebnis: dict, weitere_versuche: int) -> str:
    """Die Auswertung samt Begründung je Frage."""
    zeilen = []
    for nr, r in enumerate(ergebnis["rueckmeldung"], start=1):
        klasse = "korrekt" if r["korrekt"] else "falsch"
        urteil = "Richtig." if r["korrekt"] else "Nicht richtig."
        zeilen.append(f"""    <div class="karte {klasse}">
      <p><strong>{nr}. {_html.escape(str(r["frage"]))}</strong></p>
      <p class="muted">{urteil} {_html.escape(str(r["hinweis"]))}</p>
    </div>""")

    tnid = int(teilnahme["id"])
    if ergebnis["bestanden"]:
        weiter = f"""    <p>Bestanden.</p>
    <div class="zeile">
      <a class="knopf" href="/portal/kurs/{tnid}/zertifikat">Nachweis anzeigen</a>
    </div>"""
    elif weitere_versuche > 0:
        wort = "Versuch" if weitere_versuche == 1 else "Versuche"
        weiter = f"""    <p>Nicht bestanden. Sie haben noch {weitere_versuche} {wort}.</p>
    <div class="zeile">
      <a class="knopf" href="/portal/kurs/{tnid}/pruefung">Erneut versuchen</a>
    </div>"""
    else:
        weiter = """    <p>Nicht bestanden, und alle Versuche sind aufgebraucht.
      Wenden Sie sich an AI-SmartCon.</p>"""

    inhalt = f"""  <h1>Ergebnis</h1>
  <div class="karte">
    <p class="note">{ergebnis["prozent"]} %</p>
    <p>{ergebnis["treffer"]} von {ergebnis["gesamt"]} Fragen richtig,
      bestanden ab {ergebnis["grenze"]} %.</p>
{weiter}
  </div>
  <h2>Im Einzelnen</h2>
{chr(10).join(zeilen)}
  <p class="muted"><a href="/portal/kurse">Zurück zur Übersicht</a></p>"""
    return seite("Ergebnis", inhalt)


# Der Druckstil steht getrennt: Er gilt nur für den Nachweis.
_DRUCK = """
  @media print {
    body { background: #fff; color: #111; padding: 0; }
    .kopf, .nicht-drucken { display: none; }
    .urkunde { border: 2px solid #c9a84c; page-break-inside: avoid; }
    .urkunde h1, .urkunde .name { color: #111; }
    .urkunde .muted { color: #444; }
  }
"""


def zertifikat_seite(teilnehmer: dict, teilnahme: dict, versuch: dict) -> str:
    """Der Nachweis, druckbar.

    Kein serverseitiges PDF: Eine Seite mit @media print kostet keine
    Abhängigkeit, und der Teilnehmer erzeugt das PDF im Browser.

    Was hier NICHT stehen darf: „staatlich anerkannt", ein Verweis auf AZAV
    oder einen Bildungsgutschein, „zertifiziert nach". AI-SmartCon stellt den
    Nachweis in eigenem Namen aus — nicht mehr und nicht weniger.
    """
    bezeichnung = _html.escape(str(teilnahme.get("nachweis") or "Teilnahmebestätigung"))
    inhalt = f"""  <div class="karte urkunde" style="text-align:center;padding:40px 24px">
    <p class="thema">{bezeichnung}</p>
    <h1>{_html.escape(str(teilnahme["titel"]))}</h1>
    <p class="muted">hat erfolgreich abgeschlossen</p>
    <p class="name" style="font-size:26px;font-weight:700;margin:16px 0">
      {_html.escape(str(teilnehmer["name"]))}</p>
    {f'<p class="muted">{_html.escape(str(teilnehmer["firma"]))}</p>'
     if teilnehmer.get("firma") else ''}
    <hr style="border:0;border-top:1px solid #c9a84c;margin:24px auto;max-width:280px">
    <p class="muted">Abschlussprüfung bestanden am
      {_datum(str(versuch.get("beendet_am") or ""))} mit
      {int(versuch.get("prozent") or 0)} %.</p>
    <p class="muted">Ausgestellt von AI-SmartCon · www.ai-smartcon.de</p>
  </div>
  <div class="zeile nicht-drucken">
    <button onclick="window.print()">Drucken oder als PDF sichern</button>
    <a class="muted" href="/portal/kurse">Zurück zur Übersicht</a>
  </div>"""
    html = seite(bezeichnung, inhalt, teilnehmer)
    # Den Druckstil in den vorhandenen <style>-Block schieben.
    return html.replace("</style>", _DRUCK + "</style>", 1)
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_portal.py -v`
Expected: 17 passed.

- [ ] **Step 5: Ansehen**

```bash
.venv/bin/python - <<'PY'
import pathlib
from app import portal
t = {"id": 1, "name": "Anna Beispiel", "email": "a@b.de", "firma": "Beispiel GmbH"}
tn = {"id": 7, "slug": "kurs", "titel": "KI-Pflichtschulung",
      "nachweis": "AI-SmartCon-Zertifikat", "gueltig_bis": "2026-09-30T12:00:00+00:00",
      "offen": True}
v = {"prozent": 90, "beendet_am": "2026-08-08T12:00:00+00:00"}
pathlib.Path("/tmp/zertifikat.html").write_text(portal.zertifikat_seite(t, tn, v))
PY
```
Im Browser öffnen und die Druckvorschau prüfen: Das Zertifikat muss auf eine Seite passen und auf weißem Grund lesbar sein.

- [ ] **Step 6: Commit**

```bash
git add app/portal.py tests/test_portal.py
git commit -m "feat: Portal-Seiten im AI-SmartCon-CI"
```

---

### Task 7: Portal-Routen

**Files:**
- Create: `app/portal_routes.py`, `tests/test_portal_routes.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `app.portal.*`, `app.teilnehmer.*`, `app.versuche.*`, `app.pruefung.laden()`
- Produces:
  - `app.portal_routes.router: APIRouter` mit Präfix `/portal`
  - `COOKIE = "sitzung"`
  - `GET /portal` — Login oder Weiterleitung zur Kursliste
  - `POST /portal/anmelden` — Formular, setzt das Cookie
  - `GET /portal/abmelden`
  - `GET /portal/kurse`
  - `GET /portal/kurs/{tnid}` — Lerneinheit
  - `GET /portal/kurs/{tnid}/datei` — die HTML der Lerneinheit
  - `GET /portal/kurs/{tnid}/pruefung` — Fragen ohne Lösungen
  - `POST /portal/kurs/{tnid}/pruefung` — Auswertung
  - `GET /portal/kurs/{tnid}/zertifikat`

- [ ] **Step 1: Die Testvorbereitung schreiben**

An `tests/conftest.py` anhängen:
```python
@pytest.fixture
def portal_umgebung(client, projekte_tmp, tmp_path, monkeypatch):
    """TestClient mit Datenbank, einer fertigen Schulung und zwei Teilnehmern.

    Zwei sind nötig, weil der wichtigste Test ist, dass der eine nicht an die
    Kurse des anderen kommt.
    """
    import json

    from app import db, teilnehmer

    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()

    d = projekte_tmp / "kurs"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "KI-Pflichtschulung"}))
    (d / "status.json").write_text(json.dumps({"phase": "fertig"}))
    (d / "Schulung_KI_2026-08-01.html").write_text(
        "<html><body>Lerneinheit</body></html>", encoding="utf-8")
    (d / "pruefung.json").write_text(json.dumps({
        "titel": "Abschlussprüfung", "bestehensgrenze": 70,
        "fragen": [
            {"frage": "Frage eins?", "optionen": ["a", "b", "c"], "richtig": 0,
             "thema": "Level 1", "hinweis": "Weil a richtig ist."},
            {"frage": "Frage zwei?", "optionen": ["a", "b", "c"], "richtig": 1,
             "thema": "Level 2", "hinweis": "Weil b richtig ist."},
            {"frage": "Frage drei?", "optionen": ["a", "b", "c"], "richtig": 2,
             "thema": "Level 3", "hinweis": "Weil c richtig ist."},
            {"frage": "Frage vier?", "optionen": ["a", "b", "c"], "richtig": 0,
             "thema": "Level 4", "hinweis": "Weil a richtig ist."},
        ]}), encoding="utf-8")

    anna = teilnehmer.anlegen("anna@example.org", "Anna Beispiel", "Beispiel GmbH")
    anna_tn = teilnehmer.teilnahme_anlegen(anna, "kurs", "KI-Pflichtschulung",
                                           "AI-SmartCon-Zertifikat")
    anna_pw = teilnehmer.freischalten(anna)

    bodo = teilnehmer.anlegen("bodo@example.org", "Bodo Beispiel")
    bodo_tn = teilnehmer.teilnahme_anlegen(bodo, "kurs", "KI-Pflichtschulung",
                                           "AI-SmartCon-Zertifikat")
    teilnehmer.freischalten(bodo)

    client.anna = {"id": anna, "teilnahme": anna_tn, "passwort": anna_pw,
                   "email": "anna@example.org"}
    client.bodo = {"id": bodo, "teilnahme": bodo_tn}
    return client


def _anmelden(c, email, passwort):
    """Meldet an und lässt das Cookie im Client. Gibt die Antwort zurück."""
    return c.post("/portal/anmelden",
                  data={"email": email, "passwort": passwort},
                  follow_redirects=False)
```

- [ ] **Step 2: Den Test schreiben**

`tests/test_portal_routes.py`:
```python
"""Portal-Routen. Der Schwerpunkt liegt auf der Zugriffskontrolle."""

import json

from tests.conftest import _anmelden

ALLES_RICHTIG = {"f0": "0", "f1": "1", "f2": "2", "f3": "0"}
ALLES_FALSCH = {"f0": "1", "f1": "0", "f2": "0", "f3": "1"}


def test_ohne_anmeldung_fuehrt_alles_zum_login(portal_umgebung):
    c = portal_umgebung
    for weg in ("/portal/kurse", f"/portal/kurs/{c.anna['teilnahme']}",
                f"/portal/kurs/{c.anna['teilnahme']}/pruefung",
                f"/portal/kurs/{c.anna['teilnahme']}/zertifikat"):
        antwort = c.get(weg, follow_redirects=False)
        assert antwort.status_code == 302, weg
        assert antwort.headers["location"] == "/portal"


def test_login_seite_ist_ohne_anmeldung_erreichbar(portal_umgebung):
    antwort = portal_umgebung.get("/portal")
    assert antwort.status_code == 200
    assert 'name="passwort"' in antwort.text


def test_falsches_passwort_setzt_kein_cookie(portal_umgebung):
    antwort = _anmelden(portal_umgebung, "anna@example.org", "falsch")
    assert antwort.status_code == 200
    assert "sitzung" not in antwort.cookies
    assert "E-Mail oder Passwort" in antwort.text


def test_unbekannte_adresse_bekommt_dieselbe_meldung(portal_umgebung):
    # Sonst ist die Login-Maske ein Kundenverzeichnis.
    falsch = _anmelden(portal_umgebung, "anna@example.org", "falsch").text
    unbekannt = _anmelden(portal_umgebung, "niemand@example.org", "x").text
    assert "E-Mail oder Passwort" in falsch
    assert "E-Mail oder Passwort" in unbekannt


def test_richtiges_passwort_meldet_an(portal_umgebung):
    c = portal_umgebung
    antwort = _anmelden(c, c.anna["email"], c.anna["passwort"])
    assert antwort.status_code == 302
    assert antwort.headers["location"] == "/portal/kurse"
    keks = antwort.headers["set-cookie"]
    assert "HttpOnly" in keks
    assert "SameSite=Lax" in keks


def test_kursliste_zeigt_nur_die_eigenen_kurse(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    text = c.get("/portal/kurse").text
    assert "KI-Pflichtschulung" in text
    assert f'/portal/kurs/{c.anna["teilnahme"]}' in text
    assert f'/portal/kurs/{c.bodo["teilnahme"]}' not in text


def test_fremder_kurs_ist_404_nicht_403(portal_umgebung):
    # 403 würde bestätigen, dass es die Teilnahme gibt.
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    assert c.get(f"/portal/kurs/{c.bodo['teilnahme']}").status_code == 404
    assert c.get(f"/portal/kurs/{c.bodo['teilnahme']}/pruefung").status_code == 404
    assert c.get(f"/portal/kurs/{c.bodo['teilnahme']}/datei").status_code == 404


def test_abgelaufenes_fenster_ist_403(portal_umgebung):
    from datetime import datetime, timedelta, timezone

    from app import db

    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    conn = db.verbinden()
    conn.execute("UPDATE teilnahme SET gueltig_bis = ? WHERE id = ?",
                 ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                  c.anna["teilnahme"]))
    conn.close()

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}")
    assert antwort.status_code == 403
    assert "abgelaufen" in antwort.json()["detail"].lower()


def test_abmelden_entwertet_die_sitzung_serverseitig(portal_umgebung):
    c = portal_umgebung
    antwort = _anmelden(c, c.anna["email"], c.anna["passwort"])
    token = antwort.cookies["sitzung"]

    c.get("/portal/abmelden", follow_redirects=False)
    # Auch mit dem alten Token von Hand: die Sitzung ist weg.
    c.cookies.set("sitzung", token)
    assert c.get("/portal/kurse", follow_redirects=False).status_code == 302


def test_lerneinheit_wird_ausgeliefert(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/datei")
    assert antwort.status_code == 200
    assert "Lerneinheit" in antwort.text
    assert "private" in antwort.headers.get("cache-control", "")


def test_pruefungsseite_enthaelt_keine_loesung(portal_umgebung, projekte_tmp):
    """Die wichtigste Zusicherung des Portals."""
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    seite = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung").text

    daten = json.loads((projekte_tmp / "kurs" / "pruefung.json").read_text())
    for frage in daten["fragen"]:
        assert frage["hinweis"] not in seite
    assert "richtig" not in seite
    # Die Fragen und Optionen sind da — nur eben ohne Auszeichnung.
    assert "Frage eins?" in seite


def test_pruefung_bestehen_und_zertifikat(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")

    ergebnis = c.post(f"/portal/kurs/{c.anna['teilnahme']}/pruefung",
                      data=ALLES_RICHTIG)
    assert ergebnis.status_code == 200
    assert "100" in ergebnis.text
    assert "zertifikat" in ergebnis.text.lower()

    nachweis = c.get(f"/portal/kurs/{c.anna['teilnahme']}/zertifikat")
    assert nachweis.status_code == 200
    assert "Anna Beispiel" in nachweis.text
    assert "AI-SmartCon-Zertifikat" in nachweis.text


def test_zertifikat_vor_dem_bestehen_ist_404(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    assert c.get(f"/portal/kurs/{c.anna['teilnahme']}/zertifikat").status_code == 404


def test_der_vierte_versuch_wird_abgewiesen(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    for _ in range(3):
        c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
        c.post(f"/portal/kurs/{c.anna['teilnahme']}/pruefung", data=ALLES_FALSCH)

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert antwort.status_code == 409
    assert "aufgebraucht" in antwort.json()["detail"].lower()


def test_nach_bestehen_keine_weitere_pruefung(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    c.post(f"/portal/kurs/{c.anna['teilnahme']}/pruefung", data=ALLES_RICHTIG)

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert antwort.status_code == 409
    assert "bestanden" in antwort.json()["detail"].lower()


def test_neuladen_der_pruefung_verbraucht_keinen_versuch(portal_umgebung):
    from app import versuche

    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    for _ in range(3):
        c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert versuche.zaehlen(c.anna["teilnahme"]) == 1


def test_fremde_pruefung_kann_nicht_abgegeben_werden(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    antwort = c.post(f"/portal/kurs/{c.bodo['teilnahme']}/pruefung",
                     data=ALLES_RICHTIG)
    assert antwort.status_code == 404
```

- [ ] **Step 3: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_portal_routes.py -v`
Expected: FAIL, alle Portal-Routen liefern 404.

- [ ] **Step 4: Implementieren**

`app/portal_routes.py`:
```python
"""Die Routen des Teilnehmer-Portals.

Anders als der Verwaltungsbereich schützt sich dieser Teil selbst: Kunden
haben keine Konten im vorgelagerten Zugriffsschutz. Die Anmeldung läuft über
E-Mail und Passwort, die Sitzung über ein HttpOnly-Cookie.

Zwei Regeln ziehen sich durch alle Routen:

1. Jede Teilnahme wird über `teilnehmer.teilnahme(tnid, t["id"])` geholt —
   der Teilnehmerbezug steht in der Abfrage, nicht in einer Prüfung danach.
   So kann keine Route ihn vergessen.
2. Ein fremder Kurs ergibt 404, nicht 403. Eine 403 würde bestätigen, dass
   es die Teilnahme gibt.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from . import config, portal, projekte, pruefung, teilnehmer, versuche

router = APIRouter(prefix="/portal")

COOKIE = "sitzung"


def angemeldet(request: Request) -> dict:
    """Der angemeldete Teilnehmer, sonst Weiterleitung zum Login."""
    t = teilnehmer.sitzung_pruefen(request.cookies.get(COOKIE, ""))
    if t is None:
        raise HTTPException(status_code=302, headers={"Location": "/portal"})
    return t


def _teilnahme_oder_404(tnid: int, t: dict) -> dict:
    """Die Teilnahme dieses Teilnehmers. Fremde oder unbekannte: 404."""
    tn = teilnehmer.teilnahme(tnid, t["id"])
    if tn is None:
        raise HTTPException(404, "Kurs nicht gefunden")
    return tn


def _offen_oder_403(tn: dict) -> dict:
    if not tn.get("offen"):
        raise HTTPException(
            403, "Der Zugang zu diesem Kurs ist abgelaufen. Wenden Sie sich an "
                 "AI-SmartCon, wenn Sie ihn verlängern möchten.")
    return tn


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def portal_start(request: Request):
    """Login — oder gleich weiter, wenn die Sitzung noch läuft."""
    if teilnehmer.sitzung_pruefen(request.cookies.get(COOKIE, "")):
        return RedirectResponse("/portal/kurse", status_code=302)
    return HTMLResponse(portal.login_seite())


@router.post("/anmelden")
def portal_anmelden(response: Response, email: str = Form(...),
                    passwort: str = Form(...)):
    """Prüft die Zugangsdaten und setzt das Sitzungscookie.

    Bei Ablehnung bewusst dieselbe Meldung für „unbekannt" und „falsches
    Passwort" — sonst verrät die Maske, welche Adressen Kunde sind.
    """
    token = teilnehmer.anmelden(email, passwort)
    if token is None:
        return HTMLResponse(
            portal.login_seite("E-Mail oder Passwort stimmt nicht."),
            status_code=200)

    antwort = RedirectResponse("/portal/kurse", status_code=302)
    antwort.set_cookie(
        COOKIE, token, httponly=True, samesite="lax",
        secure=config.load().get("portal_secure_cookie", True),
        max_age=teilnehmer.SITZUNG_STUNDEN * 3600, path="/portal")
    return antwort


@router.get("/abmelden")
def portal_abmelden(request: Request):
    """Entwertet die Sitzung serverseitig und löscht das Cookie."""
    teilnehmer.abmelden(request.cookies.get(COOKIE, ""))
    antwort = RedirectResponse("/portal", status_code=302)
    antwort.delete_cookie(COOKIE, path="/portal")
    return antwort


@router.get("/kurse", response_class=HTMLResponse)
def portal_kurse(t: dict = Depends(angemeldet)):
    return HTMLResponse(portal.kursliste(t, teilnehmer.teilnahmen_von(t["id"])))


@router.get("/kurs/{tnid}", response_class=HTMLResponse)
def portal_kurs(tnid: int, t: dict = Depends(angemeldet)):
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    geschafft = versuche.bestanden(tnid) is not None
    offen = max(0, versuche.MAX_VERSUCHE - versuche.zaehlen(tnid))
    return HTMLResponse(portal.kurs_seite(t, tn, offen, geschafft))


@router.get("/kurs/{tnid}/datei")
def portal_kurs_datei(tnid: int, t: dict = Depends(angemeldet)):
    """Die Lerneinheit selbst — rund 3 MB, deshalb mit Cache-Erlaubnis.

    `private` statt `public`: Ein geteilter Zwischenspeicher darf die Datei
    nicht an andere ausliefern.
    """
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    d = projekte.projekt_dir(tn["slug"])
    if d is None:
        raise HTTPException(404, "Schulung nicht gefunden")
    seiten = sorted(
        (p for p in d.glob("*.html")
         if p.is_file() and p.name != pruefung.HTML_DATEINAME),
        key=lambda p: (p.stat().st_mtime, p.name))
    if not seiten:
        raise HTTPException(404, "Für diese Schulung liegt keine Lerneinheit vor")
    return FileResponse(seiten[-1], media_type="text/html",
                        headers={"Cache-Control": "private, max-age=3600"})


@router.get("/kurs/{tnid}/pruefung", response_class=HTMLResponse)
def portal_pruefung(tnid: int, t: dict = Depends(angemeldet)):
    """Die Fragen — ohne Lösungen.

    Der Aufbau ist Absicht: `pruefung.laden()` liefert die vollständigen
    Fragen, und hier wird genau das weitergereicht, was der Teilnehmer sehen
    darf. „richtig" und „hinweis" bleiben auf dem Server.
    """
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    try:
        versuch_id = versuche.starten(tnid)
    except versuche.VersuchFehler as e:
        raise HTTPException(409, str(e))

    d = projekte.projekt_dir(tn["slug"])
    daten = pruefung.laden(d / "pruefung.json")
    ohne_loesung = [{"frage": f["frage"], "optionen": f["optionen"],
                     "thema": f.get("thema", "")} for f in daten["fragen"]]
    return HTMLResponse(portal.pruefung_seite(
        tn, ohne_loesung, versuch_nr=versuche.zaehlen(tnid),
        max_versuche=versuche.MAX_VERSUCHE))


@router.post("/kurs/{tnid}/pruefung", response_class=HTMLResponse)
async def portal_pruefung_abgeben(tnid: int, request: Request,
                                  t: dict = Depends(angemeldet)):
    """Nimmt das Formular und wertet serverseitig aus."""
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    formular = await request.form()
    # Die Felder heißen f0, f1, … — der Index ist der Fragenindex.
    antworten = {schluessel[1:]: wert for schluessel, wert in formular.items()
                 if schluessel.startswith("f") and schluessel[1:].isdigit()}

    try:
        versuch_id = versuche.starten(tnid)
        ergebnis = versuche.auswerten(versuch_id, tn["slug"], antworten)
    except versuche.VersuchFehler as e:
        raise HTTPException(409, str(e))

    offen = max(0, versuche.MAX_VERSUCHE - versuche.zaehlen(tnid))
    return HTMLResponse(portal.ergebnis_seite(tn, ergebnis, offen))


@router.get("/kurs/{tnid}/zertifikat", response_class=HTMLResponse)
def portal_zertifikat(tnid: int, t: dict = Depends(angemeldet)):
    """Der Nachweis. Nur nach bestandener Prüfung.

    Kein Zugangsfenster-Check: Wer bestanden hat, soll seinen Nachweis auch
    nach Ablauf noch herunterladen können.
    """
    tn = _teilnahme_oder_404(tnid, t)
    versuch = versuche.bestanden(tnid)
    if versuch is None:
        raise HTTPException(404, "Für diesen Kurs liegt noch kein Nachweis vor")
    return HTMLResponse(portal.zertifikat_seite(t, tn, versuch))
```

In `app/config.py` bei den `DEFAULTS` ergänzen:
```python
    # Portal-Cookie nur über HTTPS senden. Für die Entwicklung über
    # http://localhost abschaltbar — im Betrieb bleibt es an.
    "portal_secure_cookie": True,
```

In `app/main.py` den Router einbinden:
```python
from . import portal_routes  # zum bestehenden Import-Block

app.include_router(portal_routes.router)
```

- [ ] **Step 5: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_portal_routes.py -v`
Expected: 17 passed.

Schlägt `test_ohne_anmeldung_fuehrt_alles_zum_login` mit einem 500er statt 302 fehl, wirft die `angemeldet`-Abhängigkeit die `HTTPException` mit Status 302, aber ohne dass FastAPI daraus eine Weiterleitung macht. Dann statt der Ausnahme eine `RedirectResponse` aus der Route zurückgeben — und den Fall im Bericht nennen.

- [ ] **Step 6: Commit**

```bash
git add app/portal_routes.py app/config.py app/main.py tests/conftest.py tests/test_portal_routes.py
git commit -m "feat: Portal-Routen mit Anmeldung und Zugriffskontrolle"
```

---

### Task 8: Der Durchlauf im Browser

**Files:**
- Modify: `README.md`
- Test: manuell, im laufenden Container

Dieser Task schreibt keinen neuen Code. Er prüft, ob die Kette in einem echten Browser trägt — die Tests decken die Logik ab, nicht die Erfahrung.

**Interfaces:**
- Consumes: alles aus den Tasks 1–7

- [ ] **Step 1: Container bauen**

Vorher prüfen, dass kein Agent läuft:
```bash
grep -l laeuft projects/*/status.json || echo "kein Agent aktiv"
mkdir -p data
docker compose build && docker compose up -d && sleep 5
curl -s http://localhost:8710/api/preflight | head -5
```

- [ ] **Step 2: Für die Entwicklung das Secure-Flag abschalten**

Über `http://localhost` sendet der Browser ein `Secure`-Cookie nicht zurück — die Anmeldung schiene dann zu gelingen und wäre auf der nächsten Seite wieder weg. In den Einstellungen `portal_secure_cookie` auf `false` setzen, oder direkt:
```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("config.json")
cfg = json.loads(p.read_text())
cfg["portal_secure_cookie"] = False
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
print("Secure-Cookie für die Entwicklung aus")
PY
docker compose restart
```
**Vor dem Betrieb wieder auf `true`.** Das gehört in die Betriebsdoku aus Task 10.

- [ ] **Step 3: Den Durchlauf gehen**

Im **privaten** Browserfenster (damit keine Verwaltungs-Sitzung mitspielt):

1. Im Verwaltungsbereich einen Teilnehmer anlegen, ihm eine fertige Schulung mit Prüfung zuordnen, freischalten. Passwort notieren.
2. `http://localhost:8710/portal` öffnen, anmelden.
3. Kursliste: Der Kurs ist da, das Ablaufdatum stimmt.
4. Kurs öffnen: Die Lerneinheit erscheint im Rahmen und ist bedienbar — scrollen, ein Level anklicken.
5. **Quelltext der Prüfungsseite ansehen** (`Strg+U`): keine Lösung, kein Hinweistext auffindbar.
6. Prüfung absichtlich falsch abgeben: Ergebnis zeigt Prozent, Begründung je Frage und die Restversuche.
7. Zweiter Versuch, diesmal richtig: bestanden, Link auf den Nachweis.
8. Nachweis öffnen, Druckvorschau: passt auf eine Seite, auf weißem Grund lesbar.
9. Abmelden, dann zurück auf `/portal/kurse`: leitet zum Login.

- [ ] **Step 4: Breiten prüfen**

Bei 390 px und 320 px durch dieselben Seiten gehen. Kein horizontaler Überlauf. Die Lerneinheit im Rahmen darf innen scrollen — der Portal-Rahmen nicht.

- [ ] **Step 5: README ergänzen**

In `README.md` nach dem Abschnitt „Datenablage" einfügen:

```markdown
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
verlassen ihn nicht. Die Daten liegen in `data/kurse.db` (gitignored) und
gehören ins Backup:

    sqlite3 data/kurse.db ".backup data/kurse-$(date +%F).db"
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: Teilnehmer-Portal im README"
```

---

### Task 9: Preflight-Kachel für das Portal

**Files:**
- Modify: `app/preflight.py`
- Test: `tests/test_preflight_portal.py`

**Interfaces:**
- Consumes: `app.db.DB_PFAD`, `app.db.verbinden()`
- Produces: ein Check mit `id="portal"` in `preflight.run_all()`

- [ ] **Step 1: Den Test schreiben**

`tests/test_preflight_portal.py`:
```python
"""Die Portal-Kachel im System-Check."""

from app import config, db, preflight


def _finde(checks, check_id):
    return next((c for c in checks if c["id"] == check_id), None)


def test_ohne_datenbank_ist_die_kachel_gelb(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "gibt-es-nicht.db")
    check = _finde(preflight.run_all(config.DEFAULTS), "portal")
    assert check["status"] == "warn"
    assert "noch nicht" in check["detail"].lower()


def test_mit_datenbank_nennt_die_kachel_die_zahlen(tmp_path, monkeypatch):
    from app import teilnehmer

    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")

    check = _finde(preflight.run_all(config.DEFAULTS), "portal")
    assert check["status"] == "ok"
    assert "1" in check["detail"]


def test_kaputte_datenbank_ist_ein_fehler(tmp_path, monkeypatch):
    kaputt = tmp_path / "kurse.db"
    kaputt.write_text("das ist keine SQLite-Datei")
    monkeypatch.setattr(db, "DB_PFAD", kaputt)
    assert _finde(preflight.run_all(config.DEFAULTS), "portal")["status"] == "fail"
```

- [ ] **Step 2: Test laufen lassen — er muss fehlschlagen**

Run: `.venv/bin/python -m pytest tests/test_preflight_portal.py -v`
Expected: FAIL — `check` ist `None`, weil es die Kachel noch nicht gibt.

- [ ] **Step 3: Implementieren**

In `app/preflight.py` im `ANLEITUNG`-Wörterbuch ergänzen:
```python
    "portal": """\
Die Kursverwaltung legt ihre Daten in data/kurse.db ab — Teilnehmer, Zugänge
und Prüfungsversuche.

Fehlt die Datei, wurde noch kein Teilnehmer angelegt; die App erzeugt sie beim
ersten Start selbst. Im Docker-Betrieb muss der Ordner vorher existieren,
sonst legt Docker ihn als root an:
  mkdir -p data && docker compose up -d

Die Datei enthält Kundendaten. Sie gehört ins Backup und nie ins Repo:
  sqlite3 data/kurse.db ".backup data/kurse-$(date +%F).db\"""",
```

In `run_all()` vor der `return`-Zeile:
```python
    # Kursverwaltung (optional — nur nötig, wenn das Portal genutzt wird)
    checks.append(_portal_check())
```

Und die Hilfsfunktion oberhalb von `run_all()`:
```python
def _portal_check() -> dict:
    """Zustand der Kursverwaltung: Datenbank lesbar, mit Zahlen als Detail."""
    from . import db

    base = {"id": "portal", "name": "Teilnehmer-Portal (Kursverwaltung)",
            "anleitung": ANLEITUNG["portal"]}
    if not db.DB_PFAD.exists():
        return {**base, "status": "warn",
                "detail": "noch nicht angelegt — entsteht beim ersten Teilnehmer",
                "hint": "nur nötig, wenn Schulungen an Teilnehmer ausgegeben werden"}
    try:
        conn = db.verbinden()
        try:
            personen = conn.execute(
                "SELECT count(*) AS n FROM teilnehmer").fetchone()["n"]
            teilnahmen = conn.execute(
                "SELECT count(*) AS n FROM teilnahme").fetchone()["n"]
        finally:
            conn.close()
    except Exception as e:  # sqlite3.Error, aber auch ein kaputter Dateiinhalt
        return {**base, "status": "fail", "detail": f"nicht lesbar: {e}",
                "hint": "data/kurse.db prüfen oder aus dem Backup zurückholen"}
    return {**base, "status": "ok",
            "detail": f"{personen} Teilnehmer, {teilnahmen} Teilnahmen", "hint": ""}
```

- [ ] **Step 4: Test laufen lassen**

Run: `.venv/bin/python -m pytest tests/test_preflight_portal.py -v`
Expected: 3 passed.

- [ ] **Step 5: Volle Suite**

Run: `.venv/bin/python -m pytest -q`
Expected: alles grün. Danach `git status --short` prüfen — `data/` darf nicht auftauchen.

- [ ] **Step 6: Commit**

```bash
git add app/preflight.py tests/test_preflight_portal.py
git commit -m "feat: Portal-Kachel im System-Check"
```

---

### Task 10: Doku und Betriebsübergabe

**Files:**
- Modify: `CLAUDE.md`, `SPEC.md`

**Interfaces:**
- Consumes: nichts — reine Dokumentation

- [ ] **Step 1: `CLAUDE.md` nachziehen**

Im Abschnitt „Project Structure" die `app/`-Zeile ersetzen:
```
app/            FastAPI-Backend (main, runner, projekte, prompts, preflight,
                curriculum, higgsfield, config, praesentation, pruefung, folien,
                db, zugang, teilnehmer, versuche, portal, portal_routes,
                verwaltung)
data/           SQLite der Kursverwaltung (gitignored, Kundendaten)
```

Im Abschnitt „Architecture" nach dem Absatz zur State-Machine ergänzen:
```markdown
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
```

Im Abschnitt „Notes / Gotchas" ergänzen:
```markdown
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
```

- [ ] **Step 2: `SPEC.md` um die Entscheidungen ergänzen**

Als Nummern 17 und 18 an die Entscheidungstabelle anhängen:

| 17 | Prüfung im Portal | **Serverseitige Auswertung.** Die richtigen Antworten stehen in `pruefung.json` und verlassen den Server nicht. Drei Versuche je Teilnahme, Zählung in `data/kurse.db`. Die verschickbare Prüfungsseite (`pruefung.als_html()`) bleibt daneben bestehen — sie hat einen anderen Zweck und darf ihre Lösungen mitbringen |
| 18 | Nachweis | **Druckbare HTML-Seite, kein serverseitiges PDF.** Bezeichnung aus der Teilnahme: „Teilnahmebestätigung", bei bestandener Prüfung „AI-SmartCon-Zertifikat". **Nie** „staatlich anerkannt", kein AZAV, kein Bildungsgutschein — Erwachsenenbildung ist erlaubnisfrei, AI-SmartCon stellt in eigenem Namen aus |

- [ ] **Step 3: Prüfen**

Run: `.venv/bin/python -m pytest -q`
Expected: alles grün.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md SPEC.md
git commit -m "docs: Portal in CLAUDE.md und SPEC.md"
```

---

## Abschluss von Plan 2

- [ ] Volle Suite grün, `git status --short projects/` und `data/` unverändert
- [ ] Ein Durchlauf im privaten Browserfenster: anlegen → freischalten → anmelden → lernen → prüfen → Zertifikat
- [ ] Gegenprobe: In der Prüfungsseite ist per „Quelltext anzeigen" keine Lösung zu finden
- [ ] Gegenprobe: Nach Ablauf des Fensters ist der Kurs zu, Verlängern öffnet ihn wieder
- [ ] Vault-Projektnotiz nachziehen

---

# Etappe 6–7 (Skizze) — Termine, Anmeldung, Betrieb

Eigener Plan, sobald das Portal läuft. Festgelegt ist:

**Etappe 6 — Kurse, Termine, Anmeldestrecke.** Zusätzliche Tabellen `kurs`, `serie`, `termin`, `anmeldung`; Serienregeln erzeugen Termine, zehn Plätze je Termin, bei der zehnten Anmeldung schaltet der Termin auf „ausgebucht". Die Anmeldung läuft vollständig in der App unter `kurse.ai-smartcon.de`, im CI, damit der Übergang von der Website nicht auffällt — ai-smartcon.de verlinkt nur. Mailversand über `smtplib` gegen das Postfach von ai-smartcon.de, Zugangsdaten in den Einstellungen. Bezahlung per Rechnung, Freischaltung von Hand: die Anmeldung erzeugt einen Teilnehmer ohne Zugang, den Rest macht Etappe 4.

**Nach außen nie Zahlen** — die öffentliche Antwort nennt „offen" oder „ausgebucht", nie freie oder belegte Plätze, auch nicht in Fehlermeldungen.

**Etappe 7 — Umbenennung und Betrieb.** Repo auf `SmartCon-Kurse`, auf privat gestellt; Cloudflare Access vor der ganzen App mit Bypass für `/portal*`; Domain; Betriebsdoku. **Vorher zu klären:** die Lizenzlage von `skill/schulung/` (Danksagung an Julian Ivanov im README, keine Lizenzangabe im Skill selbst), bevor AGPL-3.0 wechselt. Bereits veröffentlichte Stände bleiben AGPL.
