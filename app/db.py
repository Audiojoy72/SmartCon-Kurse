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
