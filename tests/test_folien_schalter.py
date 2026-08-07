"""Schalter „Folien einbetten": aus dem Briefing in den Produktionsauftrag."""

from app import projekte, prompts

FORM = {"thema": "CRA", "lernziele": "x", "zielgruppe": "KMU",
        "sprache": "Deutsch", "dauer": "60", "stil": "kostenlos"}


def test_default_ist_aus(client):
    slug = client.post("/api/projekte", data=FORM).json()["slug"]
    assert projekte.get(slug)["briefing"]["folien_einbetten"] is False


def test_schalter_wird_uebernommen(client):
    slug = client.post("/api/projekte",
                       data={**FORM, "folien_einbetten": "ja"}).json()["slug"]
    assert projekte.get(slug)["briefing"]["folien_einbetten"] is True


def test_block_ist_leer_wenn_aus(tmp_path):
    assert prompts.folien_block(tmp_path, {"folien_einbetten": False}) == ""


def test_block_ohne_stoffquelle_nennt_den_mangel(tmp_path):
    block = prompts.folien_block(tmp_path, {"folien_einbetten": True})
    assert "keine Folien" in block


def test_block_nennt_quelle_und_zielordner(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")

    block = prompts.folien_block(tmp_path, {"folien_einbetten": True})
    assert "deck.pptx" in block
    assert str(tmp_path / "folien") in block
    assert "app.folien" in block
    # Kein Higgsfield für Bilder, wenn die Folien die Optik liefern.
    assert "keine Bilder erzeugen" in block
