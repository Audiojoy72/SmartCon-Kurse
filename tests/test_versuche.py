"""Prüfungsversuche: zählen, auswerten, begrenzen."""

import json
import sqlite3

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
    ergebnis = versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 0})
    assert ergebnis["prozent"] == 100
    assert ergebnis["bestanden"] is True
    assert ergebnis["treffer"] == 4


def test_die_haelfte_richtig_besteht_nicht(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, {"0": 0, "1": 1, "2": 0, "3": 1})
    assert ergebnis["prozent"] == 50
    assert ergebnis["bestanden"] is False


def test_genau_auf_der_grenze_besteht(umgebung):
    # 3 von 4 sind 75 Prozent, die Grenze liegt bei 70.
    vid = versuche.starten(umgebung)
    assert versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 1})["bestanden"] is True


def test_fehlende_antwort_zaehlt_als_falsch(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, {"0": 0})
    assert ergebnis["treffer"] == 1
    assert ergebnis["bestanden"] is False


def test_das_ergebnis_nennt_die_richtige_antwort_erst_hinterher(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, {"0": 1, "1": 1, "2": 2, "3": 0})
    rueckmeldung = ergebnis["rueckmeldung"]
    assert rueckmeldung[0]["korrekt"] is False
    assert rueckmeldung[0]["richtig"] == 0
    assert rueckmeldung[0]["hinweis"] == "Weil a."


def test_rueckmeldung_traegt_das_thema(umgebung):
    """portal.ergebnis_seite braucht das Thema, um schwache Themen zu nennen
    (Decision: Begründung erst beim letzten Versuch)."""
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, {"0": 1, "1": 1, "2": 2, "3": 0})
    assert ergebnis["rueckmeldung"][0]["thema"] == "Level 1"


def test_versuch_wird_gespeichert(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 0})
    eintrag = versuche.liste(umgebung)[0]
    assert eintrag["prozent"] == 100
    assert eintrag["bestanden"] == 1
    assert eintrag["beendet_am"] is not None


def test_drei_versuche_sind_das_maximum(umgebung):
    for _ in range(versuche.MAX_VERSUCHE):
        vid = versuche.starten(umgebung)
        versuche.auswerten(vid, {"0": 1, "1": 0, "2": 0, "3": 1})
    with pytest.raises(versuche.VersuchFehler, match="Versuche"):
        versuche.starten(umgebung)


def test_nach_bestehen_kein_weiterer_versuch(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 0})
    with pytest.raises(versuche.VersuchFehler, match="bestanden"):
        versuche.starten(umgebung)


def test_bestanden_liefert_den_versuch(umgebung):
    vid = versuche.starten(umgebung)
    versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 0})
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
    versuche.auswerten(vid, {"0": 1, "1": 0, "2": 0, "3": 1})
    with pytest.raises(versuche.VersuchFehler, match="abgeschlossen"):
        versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 0})


def test_unsinnige_antwortwerte_zaehlen_als_falsch(umgebung):
    vid = versuche.starten(umgebung)
    ergebnis = versuche.auswerten(vid, {"0": 99, "1": -1, "2": 2, "3": 0})
    assert ergebnis["treffer"] == 2


def test_auswerten_scort_gegen_die_eigene_teilnahme(umgebung, tmp_path):
    """Die Schulung kommt aus dem Versuch selbst, nicht von außen.

    Da `auswerten()` keinen slug-Parameter mehr annimmt, ist eine
    Verwechslung strukturell ausgeschlossen: Ein Versuch von "kurs" kann gar
    nicht gegen die pruefung.json eines anderen Kurses ausgewertet werden,
    selbst wenn dessen Bestehensgrenze niedriger wäre.
    """
    andere_pruefung = {
        "titel": "Leichtere Prüfung",
        "bestehensgrenze": 10,  # würde 50% locker bestehen lassen
        "fragen": PRUEFUNG["fragen"],
    }
    (projekte.PROJECTS / "anderer-kurs").mkdir()
    (projekte.PROJECTS / "anderer-kurs" / "pruefung.json").write_text(
        json.dumps(andere_pruefung), encoding="utf-8")

    vid = versuche.starten(umgebung)
    # Nur die Hälfte richtig — würde gegen "anderer-kurs" (Grenze 10) mit
    # Leichtigkeit bestehen, gegen "kurs" (Grenze 70) nicht.
    ergebnis = versuche.auswerten(vid, {"0": 0, "1": 1, "2": 0, "3": 1})
    assert ergebnis["grenze"] == 70
    assert ergebnis["bestanden"] is False


def _kurzer_timeout(monkeypatch):
    """db.verbinden() nutzt sqlite3-Default-Timeout (5 s) fürs Warten auf
    einen Schreib-Lock. Für den Lock-Beweis unten reicht ein Bruchteil davon
    — sonst würde jeder der beiden Tests den Suite-Lauf um 5 Sekunden
    verlängern, nur um denselben Punkt zu belegen."""
    orig = db.verbinden

    def kurz():
        conn = orig()
        conn.execute("PRAGMA busy_timeout = 300")
        return conn

    monkeypatch.setattr(db, "verbinden", kurz)


def test_starten_verweigert_zweiten_schreiber_waehrend_offener_transaktion(umgebung, monkeypatch):
    """Beweis, dass BEGIN IMMEDIATE den Schreib-Lock tatsächlich hält.

    Echte Nebenläufigkeit lässt sich in pytest nicht sauber erzwingen — aber
    eine zweite Verbindung, die per BEGIN IMMEDIATE selbst den Schreib-Lock
    hält, erzeugt dieselbe Situation wie zwei sich überschneidende Aufrufe:
    `starten()` kann dann keinen eigenen Schreib-Lock mehr bekommen und muss
    mit `sqlite3.OperationalError` scheitern statt stillschweigend einen
    weiteren Versuch anzulegen. Das ist der Beweis für den Race-Schutz aus
    Important 1.
    """
    _kurzer_timeout(monkeypatch)
    sperre = sqlite3.connect(db.DB_PFAD, timeout=0.3)
    sperre.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            versuche.starten(umgebung)
    finally:
        sperre.execute("ROLLBACK")
        sperre.close()

    # Nach der Freigabe funktioniert starten() normal — der fehlgeschlagene
    # Aufruf hat keinen Versuch angelegt.
    assert versuche.zaehlen(umgebung) == 0
    versuche.starten(umgebung)
    assert versuche.zaehlen(umgebung) == 1


def test_auswerten_verweigert_zweiten_schreiber_waehrend_offener_transaktion(umgebung, monkeypatch):
    """Derselbe Beweis wie oben, für auswerten() (Important 2)."""
    vid = versuche.starten(umgebung)
    _kurzer_timeout(monkeypatch)

    sperre = sqlite3.connect(db.DB_PFAD, timeout=0.3)
    sperre.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 0})
    finally:
        sperre.execute("ROLLBACK")
        sperre.close()

    # Der Versuch ist noch offen — der fehlgeschlagene Aufruf hat nichts
    # geschrieben.
    assert versuche.liste(umgebung)[0]["beendet_am"] is None
    ergebnis = versuche.auswerten(vid, {"0": 0, "1": 1, "2": 2, "3": 0})
    assert ergebnis["prozent"] == 100
