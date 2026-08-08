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


def test_teilnahme_zu_unfertiger_schulung_ist_400(verwaltung, projekte_tmp):
    """Minor: Frontend filtert phase === 'fertig' — die API muss das auch."""
    d = projekte_tmp / "laeuft-noch"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "Läuft noch"}))
    (d / "pruefung.json").write_text(json.dumps(PRUEFUNG), encoding="utf-8")
    (d / "status.json").write_text(json.dumps({"phase": "produktion_laeuft"}))

    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    antwort = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                              json={"slug": "laeuft-noch"})
    assert antwort.status_code == 400


def test_teilnahme_zu_praesentation_ist_400(verwaltung, projekte_tmp):
    """Minor: Frontend filtert art !== 'praesentation' — die API muss das auch."""
    d = projekte_tmp / "deck"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "Deck", "art": "praesentation"}))
    (d / "pruefung.json").write_text(json.dumps(PRUEFUNG), encoding="utf-8")
    (d / "status.json").write_text(json.dumps({"phase": "fertig"}))

    tid = verwaltung.post("/api/verwaltung/teilnehmer",
                          json={"email": "anna@example.org", "name": "Anna"}).json()["id"]
    antwort = verwaltung.post(f"/api/verwaltung/teilnehmer/{tid}/teilnahme",
                              json={"slug": "deck"})
    assert antwort.status_code == 400


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
