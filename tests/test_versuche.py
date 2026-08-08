"""Prüfungsversuche: zählen, auswerten, begrenzen."""

import json

import pytest

from app import db, projekte, teilnehmer, versuche

PRUEFUNG = {
    "titel": "Abschlussprüfung KI-Verordnung",
    "bestehensgrenze": 70,
    "fragen": [
        {"frage": "Frage eins?", "optionen": ["a", "b", "c"], "richtig": 0,
         "thema": "Level 1", "hinweis": "Weil a."},
        {"frage": "Frage zwei?", "optionen": ["a", "b", "c"], "richtig": 1,
         "thema": "Level 2", "hinweis": "Weil b."},
        {"frage": "Frage drei?", "optionen": ["a", "b", "c"], "richtig": 2,
         "thema": "Level 3", "hinweis": "Weil c."},
        {"frage": "Frage vier?", "optionen": ["a", "b", "c"], "richtig": 0,
         "thema": "Level 4", "hinweis": "Weil a."},
    ],
}


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    """Datenbank und Projektordner, beide temporär."""
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    ziel = tmp_path / "projects"
    ziel.mkdir()
    monkeypatch.setattr(projekte, "PROJECTS", ziel)
    db.init()

    (ziel / "kurs").mkdir()
    (ziel / "kurs" / "pruefung.json").write_text(
        json.dumps(PRUEFUNG), encoding="utf-8")

    tid = teilnehmer.anlegen("anna@example.org", "Anna")
    tnid = teilnehmer.teilnahme_anlegen(tid, "kurs", "Kurs", "AI-SmartCon-Zertifikat")
    teilnehmer.freischalten(tid)
    return tnid


def test_am_anfang_kein_versuch(umgebung):
    assert versuche.zaehlen(umgebung) == 0
    assert versuche.bestanden(umgebung) is None


def test_starten_zaehlt_hoch(umgebung):
    versuche.starten(umgebung)
    assert versuche.zaehlen(umgebung) == 1


def test_alles_richtig_ergibt_hundert_prozent(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    assert ergebnis["prozent"] == 100
    assert ergebnis["bestanden"] is True
    assert ergebnis["treffer"] == 4


def test_die_haelfte_richtig_besteht_nicht(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 0, "3": 1})
    assert ergebnis["prozent"] == 50
    assert ergebnis["bestanden"] is False


def test_genau_auf_der_grenze_besteht(umgebung):
    # 3 von 4 sind 75 Prozent, die Grenze liegt bei 70.
    vid = versuche.starten(umgebung)
    assert versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 1})["bestanden"] is True


def test_fehlende_antwort_zaehlt_als_falsch(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 0})
    assert ergebnis["treffer"] == 1
    assert ergebnis["bestanden"] is False


def test_das_ergebnis_nennt_die_richtige_antwort_erst_hinterher(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 1, "1": 1, "2": 2, "3": 0})
    rueckmeldung = ergebnis["rueckmeldung"]
    assert rueckmeldung[0]["korrekt"] is False
    assert rueckmeldung[0]["richtig"] == 0
    assert rueckmeldung[0]["hinweis"] == "Weil a."


def test_versuch_wird_gespeichert(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    eintrag = versuche.liste(umgebung)[0]
    assert eintrag["prozent"] == 100
    assert eintrag["bestanden"] == 1
    assert eintrag["beendet_am"] is not None


def test_drei_versuche_sind_das_maximum(umgebung):
    for _ in range(versuche.MAX_VERSUCHE):
        vid = versuche.starten(umgebung)
        versuche.auswerten(vid, "kurs", {"0": 1, "1": 0, "2": 0, "3": 1})
    with pytest.raises(versuche.VersuchFehler, match="Versuche"):
        versuche.starten(umgebung)


def test_nach_bestehen_kein_weiterer_versuch(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    with pytest.raises(versuche.VersuchFehler, match="bestanden"):
        versuche.starten(umgebung)


def test_bestanden_liefert_den_versuch(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})
    b = versuche.bestanden(umgebung)
    assert b is not None
    assert b["prozent"] == 100


def test_ein_offener_versuch_wird_nicht_doppelt_gestartet(umgebung):
    erst = versuche.starten(umgebung)
    zweit = versuche.starten(umgebung)
    assert erst == zweit
    assert versuche.zaehlen(umgebung) == 1


def test_auswerten_eines_beendeten_versuchs_wird_abgewiesen(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, "kurs", {"0": 1, "1": 0, "2": 0, "3": 1})
    with pytest.raises(versuche.VersuchFehler, match="abgeschlossen"):
        versuche.auswerten(vid, "kurs", {"0": 0, "1": 1, "2": 2, "3": 0})


def test_unsinnige_antwortwerte_zaehlen_als_falsch(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, "kurs", {"0": 99, "1": -1, "2": 2, "3": 0})
    assert ergebnis["treffer"] == 2
