"""Teilnehmer, Teilnahmen, Freischaltung und Anmeldung."""

import sqlite3
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


class _KaputteVerbindung(sqlite3.Connection):
    """Wirft beim UPDATE auf `teilnahme`, um einen Teilausfall zu simulieren."""

    def execute(self, sql, *args, **kwargs):
        if sql.strip().startswith("UPDATE teilnahme"):
            raise sqlite3.OperationalError("simulierter Fehler")
        return super().execute(sql, *args, **kwargs)


def test_freischalten_ist_atomar_bei_fehler(datenbank, monkeypatch):
    """Schlägt der zweite Schreibvorgang fehl, darf der erste nicht stehen bleiben.

    db.verbinden() öffnet die Verbindung im Autocommit-Modus
    (isolation_level=None) — ohne explizites BEGIN/COMMIT/ROLLBACK würde das
    Passwort schon in der Datenbank stehen, wenn das UPDATE auf `teilnahme`
    scheitert. Das simulieren wir, indem genau dieses UPDATE eine Exception
    auslöst; sqlite3.Connection selbst lässt sich nicht monkeypatchen
    („immutable type"), daher eine Connection-Subklasse per Factory.
    """
    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "Teilnahmebestätigung")

    def kaputte_verbinden():
        db.DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db.DB_PFAD, isolation_level=None,
                                factory=_KaputteVerbindung)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    echte_verbinden = teilnehmer.db.verbinden
    monkeypatch.setattr(teilnehmer.db, "verbinden", kaputte_verbinden)
    with pytest.raises(sqlite3.OperationalError):
        teilnehmer.freischalten(tid)
    monkeypatch.setattr(teilnehmer.db, "verbinden", echte_verbinden)

    # Kein Passwort darf hängen geblieben sein.
    eintrag = teilnehmer.liste()[0]
    assert eintrag["hat_zugang"] is False
    assert eintrag["teilnahmen"][0]["gueltig_bis"] is None


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


def test_anmelden_mit_nicht_string_feldern_crasht_nicht(datenbank):
    """Ein Login-Formular kann fehlende Felder als None schicken.

    _email_normalisieren() rief bislang ungeprüft email.strip() auf — ein
    None (fehlendes Formularfeld) hätte anmelden() mit AttributeError statt
    kontrolliert mit None enden lassen. Das ist der real erreichbare
    Absturzpfad über das Login-Formular, den dieser Test schließt.
    """
    teilnehmer.anlegen("anna@example.org", "Anna")
    assert teilnehmer.anmelden(None, "irgendwas") is None
    assert teilnehmer.anmelden("anna@example.org", None) is None


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
