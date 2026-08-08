"""Endpunkte der Prüfungsphase."""

import json

from app import projekte

FORM = {"thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
        "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos"}

GUELTIG = {
    "titel": "Abschlussprüfung CRA",
    "bestehensgrenze": 70,
    "fragen": [{"frage": "Frage?", "optionen": ["a", "b", "c"], "richtig": 1,
                "thema": "Level 1", "hinweis": "Weil b."}],
}


def _projekt_mit_curriculum(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "curriculum.md").write_text("# Plan")
    return slug


def test_pruefung_starten_setzt_phase(client):
    slug = _projekt_mit_curriculum(client)
    antwort = client.post(f"/api/projekte/{slug}/pruefung")
    assert antwort.status_code == 200
    assert antwort.json()["phase"] == projekte.PHASE_PRUEFUNG_LAEUFT
    assert client.gestartet


def test_pruefung_ohne_curriculum_ist_404(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert client.post(f"/api/projekte/{slug}/pruefung").status_code == 404


def test_unsinnige_bestehensgrenze_ist_400(client):
    slug = _projekt_mit_curriculum(client)
    antwort = client.post(f"/api/projekte/{slug}/pruefung",
                          json={"bestehensgrenze": 250})
    assert antwort.status_code == 400


def test_lesen_ohne_datei_ist_404(client):
    slug = _projekt_mit_curriculum(client)
    assert client.get(f"/api/projekte/{slug}/pruefung").status_code == 404


def test_lesen_liefert_die_geprueften_daten(client):
    slug = _projekt_mit_curriculum(client)
    (projekte.projekt_dir(slug) / "pruefung.json").write_text(
        json.dumps(GUELTIG), encoding="utf-8")

    daten = client.get(f"/api/projekte/{slug}/pruefung").json()
    assert daten["titel"] == GUELTIG["titel"]
    assert len(daten["fragen"]) == 1


def test_kaputte_datei_ist_400_mit_klartext(client):
    slug = _projekt_mit_curriculum(client)
    (projekte.projekt_dir(slug) / "pruefung.json").write_text("```json\n{}\n```")

    antwort = client.get(f"/api/projekte/{slug}/pruefung")
    assert antwort.status_code == 400
    assert "Code-Zäune" in antwort.json()["detail"]
