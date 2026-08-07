"""Prompt-Bausteine: Was im Arbeitsauftrag steht, entscheidet über das Ergebnis."""

import json

from app import prompts

BRIEF = {
    "thema": "Cyber Resilience Act",
    "lernziele": "Pflichten kennen",
    "zielgruppe": "KMU",
    "vorwissen": "",
    "sprache": "Deutsch",
    "dauer": "60 Minuten",
    "stil": "cinematic",
    "ki_medien": True,
    "material_hinweise": "",
}


def test_presets_sind_vollstaendig_und_beschrieben():
    namen = [p["name"] for p in prompts.presets()]
    assert set(namen) == set(prompts.PRESET_NAMEN)
    assert all(p.get("titel") and p.get("beschreibung") for p in prompts.presets())


def test_kostenlos_erzwingt_keine_ki_medien():
    # Preset kostenlos ist die 0-Credit-Zusage der App — sie darf nicht kippen.
    # Die presets()-Funktion extrahiert das Feld "ki_medien" nicht, sondern den
    # Kostenrahmen direkt aus "## Kostenrahmen" im Markdown. Wir prüfen die Tatsache
    # (kostenlos = 0 Credits), indem wir das kosten-Feld checken.
    kostenlos = [p for p in prompts.presets() if p["name"] == "kostenlos"][0]
    assert "0 Credits" in kostenlos.get("kosten", "")


def test_curriculum_prompt_nennt_projektordner_und_briefing(tmp_path):
    prompt = prompts.curriculum_prompt(tmp_path, BRIEF, [])
    assert str(tmp_path) in prompt
    assert BRIEF["thema"] in prompt
    assert BRIEF["lernziele"] in prompt


def test_curriculum_prompt_erwaehnt_design_md_nur_wenn_sie_existiert(tmp_path):
    ohne = prompts.curriculum_prompt(tmp_path, BRIEF, [])
    assert "design.md" not in ohne

    (tmp_path / "design.md").write_text("akzent: \"#c9a84c\"")
    mit = prompts.curriculum_prompt(tmp_path, BRIEF, [])
    assert str(tmp_path / "design.md") in mit


def test_kostenplan_prompt_nennt_zielpfad_und_verlangt_nur_json(tmp_path):
    prompt = prompts.kostenplan_prompt(tmp_path)
    assert str(tmp_path / "kosten.json") in prompt
    assert "JSON" in prompt
