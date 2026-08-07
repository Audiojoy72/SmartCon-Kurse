"""Prompt-Bausteine: Was im Arbeitsauftrag steht, entscheidet über das Ergebnis."""

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


def test_kostenlos_erzwingt_keine_ki_medien(tmp_path):
    # Preset kostenlos ist die 0-Credit-Zusage der App — sie darf nicht kippen.
    # Die Erzwingung lebt in curriculum_prompt() (Zeile 110-111):
    # "ki_medien = (False if stil == 'kostenlos' else ...)"
    # Wir testen die tatsächliche Enforcement, indem wir curriculum_prompt()
    # mit stil="kostenlos" aufrufen und prüfen, dass der medienlose Block
    # im Output erscheint.
    brief_kostenlos = {**BRIEF, "stil": "kostenlos"}
    prompt = prompts.curriculum_prompt(tmp_path, brief_kostenlos, [])
    # Wenn stil="kostenlos", wird ki_medien zwingend False → der Prompt
    # enthält den Block "## KI-Medien: Nein — medienloses Curriculum (0 Credits)"
    assert "KI-Medien: Nein" in prompt
    assert "0 Credits" in prompt
    assert "schrittgesteuerte HTML-Szene" in prompt


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
