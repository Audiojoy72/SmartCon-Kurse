"""Endpunkte. Agentenläufe sind ersetzt — geprüft wird die HTTP-Schicht."""

FORM = {
    "thema": "Cyber Resilience Act",
    "lernziele": "Pflichten kennen",
    "zielgruppe": "KMU",
    "sprache": "Deutsch",
    "dauer": "60 Minuten",
    "stil": "kostenlos",
}


def test_projekt_anlegen_liefert_slug(client):
    antwort = client.post("/api/projekte", data=FORM)
    assert antwort.status_code == 201
    assert antwort.json()["slug"] == "cyber-resilience-act"


def test_thema_und_lernziele_sind_pflicht(client):
    assert client.post("/api/projekte", data={**FORM, "thema": " "}).status_code == 400
    # Ein wirklich leerer String bei Form(...) wird von FastAPI/Starlette
    # (installierte Version) schon vor der eigenen Prüfung als fehlendes
    # Feld gewertet -> 422 statt der App-eigenen 400-Meldung. Übers
    # Formular unerreichbar (das Feld trägt `required`), betrifft also nur
    # API-Aufrufer ohne UI. Siehe Task-4-Report für Details.
    assert client.post("/api/projekte", data={**FORM, "lernziele": ""}).status_code == 422


def test_unbekannter_stil_wird_abgewiesen(client):
    assert client.post("/api/projekte", data={**FORM, "stil": "quatsch"}).status_code == 400


def test_unbekanntes_projekt_ist_404(client):
    assert client.get("/api/projekte/gibt-es-nicht").status_code == 404
    assert client.delete("/api/projekte/gibt-es-nicht").status_code == 404


def test_pfadtrick_im_slug_ist_kein_treffer(client):
    assert client.get("/api/projekte/..%2F..%2Fetc").status_code in (400, 404)


def test_curriculum_starten_setzt_phase_und_startet_den_agenten(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    antwort = client.post(f"/api/projekte/{slug}/curriculum/starten")
    assert antwort.status_code == 200
    assert antwort.json()["phase"] == "curriculum_laeuft"
    assert client.gestartet, "runner.start wurde nicht aufgerufen"


def test_kostenplan_ohne_curriculum_ist_404(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert client.post(f"/api/projekte/{slug}/gate/kostenplan").status_code == 404


def test_default_design_md_landet_im_projekt(client, tmp_path, monkeypatch):
    # Der Fix vom 06.08.2026: Der Pfad aus den Einstellungen wurde geprüft,
    # aber beim Anlegen nie gelesen — die Schulung entstand ohne CI.
    from app import config, projekte

    datei = tmp_path / "aisc-design.md"
    datei.write_text("akzent: \"#c9a84c\"")
    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "default_design_md": str(datei)})

    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert (projekte.projekt_dir(slug) / "design.md").read_text() == datei.read_text()


def test_unlesbarer_default_design_md_ist_400(client, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS,
                                 "default_design_md": "/gibt/es/nicht.md"})
    antwort = client.post("/api/projekte", data=FORM)
    assert antwort.status_code == 400
    assert "design" in antwort.json()["detail"].lower()


def test_hochgeladene_design_md_schlaegt_den_standard(client, tmp_path, monkeypatch):
    from app import config, projekte

    standard = tmp_path / "standard.md"
    standard.write_text("standard")
    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "default_design_md": str(standard)})

    slug = client.post("/api/projekte", data=FORM,
                       files={"design_md": ("eigen.md", b"eigen")}).json()["slug"]
    assert (projekte.projekt_dir(slug) / "design.md").read_bytes() == b"eigen"
