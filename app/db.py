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

CREATE TABLE IF NOT EXISTS kurs (
    id            INTEGER PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,
    titel         TEXT NOT NULL,
    beschreibung  TEXT NOT NULL DEFAULT '',
    format        TEXT NOT NULL DEFAULT '',
    preis_cent    INTEGER NOT NULL DEFAULT 0,
    preis_pauschal INTEGER NOT NULL DEFAULT 0,
    plaetze       INTEGER NOT NULL DEFAULT 10,
    nachweis      TEXT NOT NULL DEFAULT 'Teilnahmebestätigung',
    schulung_slug TEXT NOT NULL DEFAULT '',
    aktiv         INTEGER NOT NULL DEFAULT 1,
    angelegt_am   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS serie (
    id         INTEGER PRIMARY KEY,
    kurs_id    INTEGER NOT NULL REFERENCES kurs(id) ON DELETE CASCADE,
    wochentag  INTEGER NOT NULL,
    uhrzeit    TEXT NOT NULL,
    dauer_tage INTEGER NOT NULL DEFAULT 1,
    rhythmus   INTEGER NOT NULL DEFAULT 1,
    aktiv      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS termin (
    id        INTEGER PRIMARY KEY,
    kurs_id   INTEGER NOT NULL REFERENCES kurs(id) ON DELETE CASCADE,
    serie_id  INTEGER REFERENCES serie(id) ON DELETE SET NULL,
    beginn    TEXT NOT NULL,
    ende      TEXT NOT NULL,
    plaetze   INTEGER NOT NULL,
    -- Warum termin.plaetze eine Kopie ist: Ändert jemand die Platzzahl am Kurs,
    -- dürfen bereits ausgeschriebene Termine nicht rückwirkend überbucht oder
    -- unterbelegt sein. Der Termin hält fest, was zum Zeitpunkt seiner Erzeugung galt.
    status    TEXT NOT NULL DEFAULT 'offen',
    UNIQUE (kurs_id, beginn)
);

CREATE TABLE IF NOT EXISTS anmeldung (
    id           INTEGER PRIMARY KEY,
    termin_id    INTEGER REFERENCES termin(id) ON DELETE SET NULL,
    kurs_id      INTEGER NOT NULL REFERENCES kurs(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL,
    firma        TEXT NOT NULL DEFAULT '',
    nachricht    TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'neu',
    teilnehmer_id INTEGER REFERENCES teilnehmer(id) ON DELETE SET NULL,
    -- Warum anmeldung.termin_id NULL sein darf: Das E-Learning nach Art. 4 ist
    -- terminlos. Eine Anmeldung ohne Termin ist gültig und bezieht sich nur auf den Kurs.
    angelegt_am  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_termin_kurs ON termin(kurs_id, beginn);
CREATE INDEX IF NOT EXISTS idx_anmeldung_termin ON anmeldung(termin_id);
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
    # Explizit statt dem sqlite3-Default (5000 ms) überlassen — der Wert
    # entscheidet mitten in einer Prüfung zwischen kurzem Warten und einer
    # Fehlerseite und soll nicht heimlich verschwinden, wenn jemand künftig
    # timeout=0 an connect() übergibt.
    conn.execute("PRAGMA busy_timeout = 5000")
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
