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

    # Zweiter Kurs ohne jeden Termin — das terminlose E-Learning. Nur dort ist
    # eine Anmeldung ohne Termin zulässig; beim Kurs mit offenen Terminen ist
    # die Terminwahl Pflicht.
    terminlos = kurse.anlegen("terminlos", "E-Learning jederzeit",
                              schulung_slug="ki-pflicht",
                              nachweis="AI-SmartCon-Zertifikat")
    return {"kurs": kid, "termin": kurse.termine(kid)[0]["id"],
            "terminlos": terminlos}


def test_annehmen_legt_an(umgebung):
    aid = anmeldung.annehmen(umgebung["kurs"], umgebung["termin"],
                             "Anna Beispiel", "anna@example.org", "Beispiel GmbH")
    e = anmeldung.eintrag(aid)
    assert e["name"] == "Anna Beispiel"
    assert e["email"] == "anna@example.org"
    assert e["status"] == "neu"


def test_email_wird_normalisiert_und_geprueft(umgebung):
    aid = anmeldung.annehmen(umgebung["terminlos"], None, "Anna",
                             "  Anna@EXAMPLE.org ")
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
    """Ohne buchbaren Termin gibt es nichts zu wählen — das ist zulässig."""
    aid = anmeldung.annehmen(umgebung["terminlos"], None, "Anna",
                             "anna@example.org")
    assert anmeldung.eintrag(aid)["termin_id"] is None


def test_ohne_termin_wird_abgewiesen_wenn_es_offene_gibt(umgebung):
    """Sonst wäre die Platzprüfung mit einem leeren termin_id zu umgehen."""
    with pytest.raises(anmeldung.AnmeldungFehler, match="Termin"):
        anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")


def test_ohne_termin_geht_wenn_alle_termine_vergeben_sind(umgebung):
    """Der Fall, den die Kursseite mit „trotzdem anmelden" bewusst anbietet."""
    for t in kurse.termine(umgebung["kurs"]):
        kurse.termin_status(t["id"], "geschlossen")
    aid = anmeldung.annehmen(umgebung["kurs"], None, "Anna", "anna@example.org")
    assert anmeldung.eintrag(aid)["termin_id"] is None


def test_ohne_termin_geht_wenn_alle_offenen_ausgebucht_sind(umgebung):
    """Ausgebucht heißt: nicht buchbar — also auch nichts zu wählen."""
    for t in kurse.termine(umgebung["kurs"]):
        if t["status"] != "offen":
            continue
        for i in range(t["frei"]):
            anmeldung.annehmen(umgebung["kurs"], t["id"], f"P{t['id']}-{i}",
                               f"p{t['id']}-{i}@example.org")
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
    aid = anmeldung.annehmen(umgebung["terminlos"], None, "Anna", "anna@example.org")
    anmeldung.status_setzen(aid, "bezahlt")
    assert anmeldung.eintrag(aid)["status"] == "bezahlt"
    with pytest.raises(anmeldung.AnmeldungFehler):
        anmeldung.status_setzen(aid, "quatsch")


def test_liste_kann_nach_status_filtern(umgebung):
    a = anmeldung.annehmen(umgebung["terminlos"], None, "Anna", "anna@example.org")
    anmeldung.annehmen(umgebung["terminlos"], None, "Bodo", "bodo@example.org")
    anmeldung.status_setzen(a, "bezahlt")
    assert len(anmeldung.liste()) == 2
    assert [e["name"] for e in anmeldung.liste(status="bezahlt")] == ["Anna"]


def test_liste_nennt_kurs_und_termin(umgebung):
    """Die Verwaltung zeigt beides nebeneinander und soll nicht nachladen müssen."""
    anmeldung.annehmen(umgebung["kurs"], umgebung["termin"], "Anna",
                       "anna@example.org")
    anmeldung.annehmen(umgebung["terminlos"], None, "Bodo", "bodo@example.org")
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
    aid = anmeldung.annehmen(umgebung["terminlos"], None, "Anna", "anna@example.org")
    with pytest.raises(anmeldung.AnmeldungFehler, match="bezahlt"):
        anmeldung.zu_teilnehmer(aid)


def test_zu_teilnehmer_nur_einmal(umgebung):
    aid = anmeldung.annehmen(umgebung["terminlos"], None, "Anna", "anna@example.org")
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
    a1 = anmeldung.annehmen(umgebung["terminlos"], None, "Anna", "anna@example.org")
    anmeldung.status_setzen(a1, "bezahlt")
    tid1, _ = anmeldung.zu_teilnehmer(a1)

    a2 = anmeldung.annehmen(kid2, None, "Anna", "anna@example.org")
    anmeldung.status_setzen(a2, "bezahlt")
    tid2, _ = anmeldung.zu_teilnehmer(a2)
    assert tid2 == tid1


def test_zu_langer_name_wird_abgewiesen(umgebung):
    """maxlength im Formular ist Bequemlichkeit — ein direkter POST kennt es nicht."""
    with pytest.raises(anmeldung.AnmeldungFehler, match="Name"):
        anmeldung.annehmen(umgebung["terminlos"], None,
                           "A" * (anmeldung.MAX_NAME + 1), "anna@example.org")


def test_zu_lange_firma_wird_abgewiesen(umgebung):
    with pytest.raises(anmeldung.AnmeldungFehler, match="Firmenname"):
        anmeldung.annehmen(umgebung["terminlos"], None, "Anna",
                           "anna@example.org", firma="F" * (anmeldung.MAX_FIRMA + 1))


def test_liste_nennt_den_terminstatus(umgebung):
    anmeldung.annehmen(umgebung["kurs"], umgebung["termin"], "Anna",
                       "anna@example.org")
    kurse.termin_status(umgebung["termin"], "abgesagt")
    assert anmeldung.liste()[0]["termin_status"] == "abgesagt"
