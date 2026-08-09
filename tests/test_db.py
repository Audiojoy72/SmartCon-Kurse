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
