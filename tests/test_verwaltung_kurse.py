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


def test_unsinnige_uhrzeit_ist_400_und_legt_keine_serie_an(verwaltungsclient):
    """Vorher: 500 aus termine_erzeugen — und die Serie blieb als Leiche liegen."""
    kid = _kurs(verwaltungsclient)
    antwort = verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}/serie",
                                     json={"wochentag": 2, "uhrzeit": "25:70"})
    assert antwort.status_code == 400
    conn = db.verbinden()
    try:
        assert conn.execute("SELECT count(*) FROM serie").fetchone()[0] == 0
    finally:
        conn.close()


def test_kurs_aendern_prueft_die_typen(verwaltungsclient):
    """SQLite-Affinität legt "viele" klaglos in einer INTEGER-Spalte ab."""
    kid = _kurs(verwaltungsclient)
    assert verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}",
                                  json={"plaetze": "viele"}).status_code == 400
    assert verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}",
                                  json={"preis_cent": "teuer"}).status_code == 400
    assert verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}",
                                  json={"aktiv": "ja"}).status_code == 400
    assert kurse.kurs(kid)["plaetze"] == 2


def test_kurs_aendern_nimmt_den_schalter_als_wahrheitswert(verwaltungsclient):
    """Das Frontend schickt aktiv als true/false — das muss weiter gehen."""
    kid = _kurs(verwaltungsclient)
    assert verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}",
                                  json={"aktiv": False}).status_code == 200
    assert kurse.kurs(kid)["aktiv"] == 0


def test_anmeldungen_zeigen_den_terminstatus(verwaltungsclient):
    """Sonst schaltet der Betreiber den Zugang zu einem abgesagten Termin frei."""
    kid = _kurs(verwaltungsclient)
    verwaltungsclient.post(f"/api/verwaltung/kurse/{kid}/serie",
                           json={"wochentag": 2, "uhrzeit": "09:00", "wochen": 8})
    tid = verwaltungsclient.get(
        "/api/verwaltung/kurse").json()["kurse"][0]["termine"][0]["id"]
    anmeldung.annehmen(kid, tid, "Anna", "anna@example.org")
    kurse.termin_status(tid, "abgesagt")

    liste = verwaltungsclient.get("/api/verwaltung/anmeldungen").json()["anmeldungen"]
    assert liste[0]["termin_status"] == "abgesagt"
