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
