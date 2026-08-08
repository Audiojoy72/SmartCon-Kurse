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
