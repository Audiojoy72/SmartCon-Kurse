"""Kurse, Serien und Termine."""

from datetime import date, datetime, timedelta

import pytest

from app import db, kurse


@pytest.fixture
def datenbank(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()
    return db.DB_PFAD


def test_anlegen_und_lesen(datenbank):
    kid = kurse.anlegen("ki-pflicht", "KI-Pflichtschulung",
                        preis_cent=14900, plaetze=20)
    k = kurse.kurs(kid)
    assert k["slug"] == "ki-pflicht"
    assert k["preis_cent"] == 14900
    assert k["plaetze"] == 20


def test_slug_wird_normalisiert_und_geprueft(datenbank):
    kid = kurse.anlegen("  KI-Pflicht  ", "Titel")
    assert kurse.kurs(kid)["slug"] == "ki-pflicht"
    with pytest.raises(kurse.KursFehler):
        kurse.anlegen("nicht erlaubt!", "Titel")


def test_doppelter_slug_wird_abgewiesen(datenbank):
    kurse.anlegen("ki-pflicht", "Titel")
    with pytest.raises(kurse.KursFehler, match="bereits"):
        kurse.anlegen("ki-pflicht", "Anderer Titel")


def test_titel_ist_pflicht(datenbank):
    with pytest.raises(kurse.KursFehler):
        kurse.anlegen("slug", "   ")


def test_pauschalpreis_ist_moeglich(datenbank):
    # Die Masterclass kostet 3.999 EUR gesamt für bis zu drei Personen.
    kid = kurse.anlegen("masterclass", "Agentic-Coding-Masterclass",
                        preis_cent=399900, preis_pauschal=True, plaetze=3)
    assert kurse.kurs(kid)["preis_pauschal"] == 1


def test_aendern_setzt_nur_die_genannten_felder(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    kurse.aendern(kid, titel="Neuer Titel")
    k = kurse.kurs(kid)
    assert k["titel"] == "Neuer Titel"
    assert k["plaetze"] == 10


def test_aendern_eines_unbekannten_kurses_wirft(datenbank):
    with pytest.raises(kurse.KursFehler, match="nicht gefunden"):
        kurse.aendern(999, titel="X")


def test_liste_kann_auf_aktive_filtern(datenbank):
    kurse.anlegen("a", "A")
    kid = kurse.anlegen("b", "B")
    kurse.aendern(kid, aktiv=False)
    assert len(kurse.liste()) == 2
    assert [k["slug"] for k in kurse.liste(nur_aktive=True)] == ["a"]


@pytest.mark.parametrize("uhrzeit", ["abc", "25:70", "9:00", "", "09:0",
                                     "24:00", "09:60"])
def test_ungueltige_uhrzeit_legt_keine_serie_an(datenbank, uhrzeit):
    """Sonst bliebe die Serie als Leiche liegen und termine_erzeugen wirft 500."""
    kid = kurse.anlegen("ki-pflicht", "Titel")
    with pytest.raises(kurse.KursFehler, match="Uhrzeit"):
        kurse.serie_anlegen(kid, wochentag=2, uhrzeit=uhrzeit)
    conn = db.verbinden()
    try:
        assert conn.execute("SELECT count(*) FROM serie").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize("wochentag", [-1, 7, "2", True])
def test_ungueltiger_wochentag_legt_keine_serie_an(datenbank, wochentag):
    kid = kurse.anlegen("ki-pflicht", "Titel")
    with pytest.raises(kurse.KursFehler, match="Wochentag"):
        kurse.serie_anlegen(kid, wochentag=wochentag, uhrzeit="09:00")


def test_serie_erzeugt_termine_im_rhythmus(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    # Mittwochs, 14-tägig
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00", rhythmus=2)
    anzahl = kurse.termine_erzeugen(sid, bis=date(2026, 10, 1))

    t = kurse.termine(kid)
    assert anzahl == len(t)
    assert all(datetime.fromisoformat(x["beginn"]).weekday() == 2 for x in t)
    abstaende = {(datetime.fromisoformat(b["beginn"])
                  - datetime.fromisoformat(a["beginn"])).days
                 for a, b in zip(t, t[1:])}
    assert abstaende == {14}


def test_termine_erzeugen_ist_wiederholbar(datenbank):
    # Zweimal aufgerufen darf keine Dubletten anlegen.
    kid = kurse.anlegen("ki-pflicht", "Titel")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    erst = kurse.termine_erzeugen(sid, bis=date(2026, 10, 1))
    zweit = kurse.termine_erzeugen(sid, bis=date(2026, 10, 1))
    assert erst > 0
    assert zweit == 0
    assert len(kurse.termine(kid)) == erst


def test_mehrtaegiger_termin_endet_spaeter(datenbank):
    # Die Masterclass läuft vier Tage.
    kid = kurse.anlegen("masterclass", "Titel", plaetze=3)
    sid = kurse.serie_anlegen(kid, wochentag=0, uhrzeit="09:00", dauer_tage=4)
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    t = kurse.termine(kid)[0]
    dauer = datetime.fromisoformat(t["ende"]) - datetime.fromisoformat(t["beginn"])
    assert dauer.days == 3  # vier Kalendertage, drei Nächte


def test_termin_uebernimmt_die_platzzahl_des_kurses(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=7)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    assert kurse.termine(kid)[0]["plaetze"] == 7


def test_platzaenderung_wirkt_nicht_rueckwirkend(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=7)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    kurse.aendern(kid, plaetze=99)
    assert kurse.termine(kid)[0]["plaetze"] == 7


def test_termine_nennen_belegung_und_freie_plaetze(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    t = kurse.termine(kid)[0]
    assert t["belegt"] == 0
    assert t["frei"] == 10


def test_status_setzen(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 9, 30))
    tid = kurse.termine(kid)[0]["id"]

    kurse.termin_status(tid, "abgesagt")
    assert kurse.termin(tid)["status"] == "abgesagt"
    with pytest.raises(kurse.KursFehler):
        kurse.termin_status(tid, "quatsch")


def test_naechste_offene_nennt_keine_zahlen(datenbank):
    """Nach außen nie Zahlen — nur offen oder ausgebucht."""
    kid = kurse.anlegen("ki-pflicht", "Titel", plaetze=10)
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 12, 31))

    offen = kurse.naechste_offene(kid)
    assert len(offen) <= 4
    for t in offen:
        assert "plaetze" not in t
        assert "belegt" not in t
        assert "frei" not in t
        assert t["status"] in ("offen", "ausgebucht")


def test_naechste_offene_ueberspringt_vergangene_und_abgesagte(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date(2026, 12, 31))
    alle = kurse.termine(kid)
    kurse.termin_status(alle[0]["id"], "abgesagt")

    ids = {t["id"] for t in kurse.naechste_offene(kid, anzahl=99)}
    assert alle[0]["id"] not in ids
    jetzt = datetime.now()
    assert all(datetime.fromisoformat(t["beginn"]) > jetzt
               for t in kurse.naechste_offene(kid, anzahl=99))


def test_nachweis_wird_uebernommen(datenbank):
    kid = kurse.anlegen("ki-pflicht", "Titel",
                        nachweis="AI-SmartCon-Zertifikat")
    assert kurse.kurs(kid)["nachweis"] == "AI-SmartCon-Zertifikat"


def test_nachweis_nur_aus_der_erlaubten_liste(datenbank):
    """Was hier steht, steht später als Überschrift auf einer Urkunde."""
    with pytest.raises(kurse.KursFehler, match="Nachweis"):
        kurse.anlegen("ki-pflicht", "Titel", nachweis="staatlich anerkannt")
    kid = kurse.anlegen("ki-pflicht", "Titel")
    with pytest.raises(kurse.KursFehler, match="Nachweis"):
        kurse.aendern(kid, nachweis="IHK-geprüft")
