"""Eine Prüfung darf die Projektphase nie verändern — weder bei Erfolg noch
bei Fehlschlag (siehe Kommentar bei runner.PHASE_NACH_ERFOLG)."""

import json
import time

from app import projekte, runner

FORM = {"thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
        "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos"}


def _laufender_pruefungslauf(slug, vorher_phase):
    """Simuliert, was runner.start(..., zurueck_phase=vorher_phase) anlegt."""
    projekte.set_phase(slug, projekte.PHASE_PRUEFUNG_LAEUFT)
    runner._laeufe[slug] = {"phase": "pruefung", "gestartet": time.time(),
                            "zurueck": vorher_phase}


def _result_zeile(subtype, text=""):
    return json.dumps({"type": "result", "subtype": subtype,
                       "duration_ms": 100, "result": text})


def test_erfolgreiche_pruefung_aendert_fertig_nicht(projekte_tmp):
    slug = projekte.create(FORM)
    projekte.set_phase(slug, projekte.PHASE_FERTIG)
    _laufender_pruefungslauf(slug, projekte.PHASE_FERTIG)
    try:
        runner._parse_claude_zeile(
            slug, "pruefung", _result_zeile("success"),
            {"session_gespeichert": False, "fertig_gesehen": False})
        assert projekte.load_status(slug)["phase"] == projekte.PHASE_FERTIG
    finally:
        runner._laeufe.pop(slug, None)


def test_fehlgeschlagene_pruefung_aendert_fertig_nicht(projekte_tmp):
    """Ein gescheiterter Prüfungslauf darf „fertig" nicht auf „fehler" werfen —
    sonst verschwinden Ergebnis-Liste und Prüfungsblock aus der UI."""
    slug = projekte.create(FORM)
    projekte.set_phase(slug, projekte.PHASE_FERTIG)
    _laufender_pruefungslauf(slug, projekte.PHASE_FERTIG)
    try:
        runner._parse_claude_zeile(
            slug, "pruefung", _result_zeile("error_max_turns", "Fehlgeschlagen"),
            {"session_gespeichert": False, "fertig_gesehen": False})
        status = projekte.load_status(slug)
        assert status["phase"] == projekte.PHASE_FERTIG
        # Der Fehler wird trotzdem festgehalten, nur die Phase bleibt stabil.
        assert status["letzter_fehler"] == "Fehlgeschlagen"
    finally:
        runner._laeufe.pop(slug, None)


def test_pruefung_aus_curriculum_fertig_bleibt_dort(projekte_tmp):
    """Konsequenz 1 aus dem Review: eine Prüfung, vor der Freigabe gestartet,
    darf ein Projekt nicht auf „fertig" springen lassen — sonst ist die
    Produktion (nur aus „freigegeben" erreichbar) nie mehr startbar."""
    slug = projekte.create(FORM)
    projekte.set_phase(slug, projekte.PHASE_CURRICULUM_FERTIG)
    _laufender_pruefungslauf(slug, projekte.PHASE_CURRICULUM_FERTIG)
    try:
        runner._parse_claude_zeile(
            slug, "pruefung", _result_zeile("success"),
            {"session_gespeichert": False, "fertig_gesehen": False})
        assert (projekte.load_status(slug)["phase"]
                == projekte.PHASE_CURRICULUM_FERTIG)
    finally:
        runner._laeufe.pop(slug, None)
