"""Endpunkte der Deck-Werkstatt."""

import pytest

from app import config, projekte

FORM = {"thema": "Die KI-Verordnung für KMU",
        "zielgruppe": "Geschäftsführung",
        "quellen": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def mit_logo(tmp_path, monkeypatch):
    logo = tmp_path / "config-logo.png"
    logo.write_bytes(PNG)
    monkeypatch.setattr(config, "LOGO_PFAD", logo)
    return logo


def test_anlegen_startet_lauf_und_setzt_phase(client, mit_logo):
    antwort = client.post("/api/praesentationen", data=FORM)
    assert antwort.status_code == 201
    slug = antwort.json()["slug"]
    assert antwort.json()["phase"] == projekte.PHASE_PRAESENTATION_LAEUFT
    assert projekte.art(slug) == projekte.ART_PRAESENTATION
    assert client.gestartet, "runner.start wurde nicht aufgerufen"


def test_thema_ist_pflicht(client, mit_logo):
    assert client.post("/api/praesentationen", data={"thema": "  "}).status_code == 400


def test_ohne_logo_ist_es_400_statt_eines_vergeblichen_laufs(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGO_PFAD", tmp_path / "fehlt.png")
    antwort = client.post("/api/praesentationen", data=FORM)
    assert antwort.status_code == 400
    assert "logo" in antwort.json()["detail"].lower()
    assert not client.gestartet


def test_zu_lange_quellenliste_wird_abgewiesen(client, mit_logo):
    antwort = client.post("/api/praesentationen",
                          data={**FORM, "quellen": "x" * 20001})
    assert antwort.status_code == 400


def test_stand_meldet_erzeugte_dateien(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "AI-SmartCon_Test.pptx").write_bytes(b"x" * 10)

    stand = client.get(f"/api/praesentationen/{slug}").json()
    assert stand["dateien"] == [{"name": "AI-SmartCon_Test.pptx", "groesse": 10}]
    assert stand["fertig"] is True


def test_stand_unbekannt_ist_404(client):
    assert client.get("/api/praesentationen/gibt-es-nicht").status_code == 404


def test_download_liefert_die_datei(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "AI-SmartCon_Test.pptx").write_bytes(b"inhalt")

    antwort = client.get(f"/api/praesentationen/{slug}/datei/AI-SmartCon_Test.pptx")
    assert antwort.status_code == 200
    assert antwort.content == b"inhalt"


def test_download_nur_pptx(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    (projekte.projekt_dir(slug) / "geheim.json").write_text("{}")
    assert client.get(f"/api/praesentationen/{slug}/datei/geheim.json").status_code == 400


def test_download_kein_pfadausbruch(client, mit_logo):
    slug = client.post("/api/praesentationen", data=FORM).json()["slug"]
    antwort = client.get(f"/api/praesentationen/{slug}/datei/..%2F..%2Fconfig.json")
    assert antwort.status_code in (400, 404)
