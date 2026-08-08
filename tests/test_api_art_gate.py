"""Schulungs-Phasen-Endpunkte müssen Präsentationsprojekte abweisen.

ladeDecks() filtert die Projektliste nur in eine Richtung (art ===
"praesentation"); ohne serverseitige Prüfung öffnet die normale
Projekt-Detailansicht trotzdem ein Deck, und ihre Buttons feuern auf
Schulungs-Endpunkten, die den Präsentationsordner überschreiben würden.
"""

import pytest

from app import config, projekte

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def deck_slug(client, tmp_path, monkeypatch):
    logo = tmp_path / "config-logo.png"
    logo.write_bytes(PNG)
    monkeypatch.setattr(config, "LOGO_PFAD", logo)
    antwort = client.post("/api/praesentationen",
                          data={"thema": "Die KI-Verordnung für KMU"})
    slug = antwort.json()["slug"]
    (projekte.projekt_dir(slug) / "curriculum.md").write_text("# Plan")
    projekte.set_phase(slug, projekte.PHASE_FREIGEGEBEN)
    return slug


def test_curriculum_starten_ist_409(client, deck_slug):
    laeufe_vorher = len(client.gestartet)
    antwort = client.post(f"/api/projekte/{deck_slug}/curriculum/starten")
    assert antwort.status_code == 409
    assert len(client.gestartet) == laeufe_vorher


def test_curriculum_schreiben_ist_409(client, deck_slug):
    antwort = client.put(f"/api/projekte/{deck_slug}/curriculum",
                         json={"text": "x"})
    assert antwort.status_code == 409


def test_curriculum_kommentar_ist_409(client, deck_slug):
    antwort = client.post(f"/api/projekte/{deck_slug}/curriculum/kommentar",
                          json={"kommentar": "bitte ändern"})
    assert antwort.status_code == 409


def test_kostenplan_ist_409(client, deck_slug):
    antwort = client.post(f"/api/projekte/{deck_slug}/gate/kostenplan")
    assert antwort.status_code == 409


def test_pruefung_starten_ist_409(client, deck_slug):
    antwort = client.post(f"/api/projekte/{deck_slug}/pruefung")
    assert antwort.status_code == 409


def test_go_ist_409(client, deck_slug):
    antwort = client.post(f"/api/projekte/{deck_slug}/go")
    assert antwort.status_code == 409


def test_produktion_starten_ist_409(client, deck_slug):
    laeufe_vorher = len(client.gestartet)
    antwort = client.post(f"/api/projekte/{deck_slug}/produktion/starten")
    assert antwort.status_code == 409
    assert len(client.gestartet) == laeufe_vorher


def test_schulung_ist_unbetroffen(client):
    slug = client.post("/api/projekte", data={
        "thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
        "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos"}).json()["slug"]
    antwort = client.post(f"/api/projekte/{slug}/curriculum/starten")
    assert antwort.status_code == 200
