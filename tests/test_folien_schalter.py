"""Schalter „Folien einbetten": aus dem Briefing in den Produktionsauftrag."""

import re
import subprocess

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


def test_block_verspricht_kein_festes_zwei_ziffern_format(tmp_path):
    """folien._normalisiere_nummerierung() polstert auf die tatsächliche
    Foliensahl (mindestens zweistellig, ab 100 Folien dreistellig) — der
    Block darf daher kein festes „folie-NN.png" versprechen, sondern muss
    auf das tatsächliche Glob-Muster verweisen, das folien.py selbst nutzt
    (ziel_dir.glob("folie-*.png"))."""
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")

    block = prompts.folien_block(tmp_path, {"folien_einbetten": True})
    assert "folie-NN" not in block
    assert "folie-*.png" in block


def test_block_ist_shellsicher_bei_heiklem_dateinamen(tmp_path):
    """Ein hochgeladener Dateiname mit Quote/Backtick/$ darf im emittierten
    Bash-Kommando NICHT als Command-Substitution oder Syntaxbruch wirken —
    die Pfade müssen als gequotete Argumente ankommen, nicht als roher Text
    im Python-Code."""
    material = tmp_path / "material"
    material.mkdir()
    heikel = "deck`whoami`$(id)'.pptx"
    (material / heikel).write_bytes(b"x")

    block = prompts.folien_block(tmp_path, {"folien_einbetten": True})
    fence = re.search(r"```bash\n(.*?)\n```", block, re.DOTALL).group(1)
    argzeile = fence.strip().splitlines()[-1]
    assert argzeile.startswith('"')
    argteil = argzeile[1:].strip()  # hinter dem schließenden Anführungszeichen

    ergebnis = subprocess.run(
        f'printf "%s\\n" {argteil}', shell=True,
        capture_output=True, text=True, timeout=5)

    ausgabe = ergebnis.stdout.splitlines()
    assert ausgabe == [str(material / heikel), str(tmp_path / "folien")]
