"""Projektart: Schulung oder Präsentation."""

from pathlib import Path

from app import projekte

SCHULUNG = {"thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
            "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos",
            "ki_medien": False}
PRAESENTATION = {**SCHULUNG, "art": projekte.ART_PRAESENTATION,
                 "quellen": "https://example.org"}


def test_ohne_feld_gilt_schulung(projekte_tmp):
    # Die fünf bestehenden Projekte haben kein art-Feld und bleiben Schulungen.
    slug = projekte.create(SCHULUNG)
    assert projekte.art(slug) == projekte.ART_SCHULUNG


def test_praesentation_wird_erkannt(projekte_tmp):
    slug = projekte.create(PRAESENTATION)
    assert projekte.art(slug) == projekte.ART_PRAESENTATION


def test_unbekanntes_projekt_gilt_als_schulung(projekte_tmp):
    assert projekte.art("gibt-es-nicht") == projekte.ART_SCHULUNG


def test_liste_nennt_die_art(projekte_tmp):
    projekte.create(SCHULUNG)
    projekte.create(PRAESENTATION)
    arten = {p["slug"]: p["art"] for p in projekte.liste()}
    assert set(arten.values()) == {projekte.ART_SCHULUNG, projekte.ART_PRAESENTATION}


def test_praesentationsphasen_stimmen_mit_dem_frontend_ueberein():
    # Das Frontend kennt die Phasen nicht über den Wert, sondern nur als
    # Schlüssel in DECK_PHASEN_LABEL (static/app.js) — driften Backend-
    # Konstante und Frontend-Schlüssel auseinander, zeigt die Deck-Karte
    # den rohen Phasenstring statt eines Labels.
    app_js = (Path(__file__).resolve().parent.parent / "static" / "app.js").read_text()
    block = app_js.split("DECK_PHASEN_LABEL")[1].split("};")[0]
    assert f"{projekte.PHASE_PRAESENTATION_LAEUFT}:" in block
    assert f"{projekte.PHASE_PRAESENTATION_FERTIG}:" in block
