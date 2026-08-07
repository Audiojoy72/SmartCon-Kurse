"""Arbeitsauftrag an den Präsentations-Agenten."""

from pathlib import Path

from app import praesentation

BRIEF = {
    "art": "praesentation",
    "thema": "Die KI-Verordnung für KMU",
    "zielgruppe": "Geschäftsführung",
    "lernziele": "Pflichten aus Art. 4 kennen",
    "sprache": "Deutsch",
    "dauer": "45 Minuten",
    "quellen": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
}


def test_dateiname_ohne_umlaute_und_sonderzeichen():
    assert praesentation.dateiname_aus_thema("Größe & Maß") == "AI-SmartCon_Groesse-Mass"
    assert praesentation.dateiname_aus_thema("") == "AI-SmartCon_Praesentation"
    assert praesentation.dateiname_aus_thema("!!!") == "AI-SmartCon_Praesentation"


def test_dateiname_wird_gekuerzt():
    lang = praesentation.dateiname_aus_thema("Wort " * 40)
    assert len(lang) <= 72


def test_prompt_nennt_skill_arbeitsordner_und_ziel(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, tmp_path / "logo.png")
    assert praesentation.SKILL_NAME in p
    assert str(tmp_path) in p
    assert "AI-SmartCon_Die-KI-Verordnung-fuer-KMU.pptx" in p


def test_prompt_uebergibt_briefing_und_quellen(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert BRIEF["thema"] in p
    assert BRIEF["zielgruppe"] in p
    assert BRIEF["quellen"] in p


def test_prompt_ohne_quellen_fordert_eigene_recherche(tmp_path):
    p = praesentation.prompt(tmp_path, {**BRIEF, "quellen": ""}, None)
    assert "recherchiere selbst" in p.lower()


def test_prompt_nennt_hochgeladenes_material_als_primaerquelle(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "entwurf.md").write_text("x")
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert "entwurf.md" in p
    assert "Primärquelle" in p


def test_prompt_ohne_material_sagt_das(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert "keine Dateien hochgeladen" in p


def test_prompt_verlangt_belege_fuer_die_spaetere_pruefung(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    # Die Präsentation ist später Grundlage der Prüfung — Unbelegtes darf nicht rein.
    assert "notes" in p.lower()
    assert "prüfung" in p.lower()


def test_prompt_verbietet_rueckfragen(tmp_path):
    p = praesentation.prompt(tmp_path, BRIEF, None)
    assert "AskUserQuestion" in p


def test_prompt_nennt_das_logo_wenn_vorhanden(tmp_path):
    logo = tmp_path / "logo.png"
    mit = praesentation.prompt(tmp_path, BRIEF, logo)
    ohne = praesentation.prompt(tmp_path, BRIEF, None)
    assert str(logo) in mit
    assert str(logo) not in ohne
    assert "kein Logo hinterlegt" in ohne


def test_dateien_liefert_pptx_juengste_zuletzt(tmp_path):
    import os

    alt = tmp_path / "alt.pptx"
    neu = tmp_path / "neu.pptx"
    alt.write_bytes(b"a")
    neu.write_bytes(b"b")
    os.utime(alt, (1, 1))
    os.utime(neu, (2, 2))
    assert praesentation.dateien(tmp_path) == [alt, neu]


def test_dateien_ignoriert_andere_endungen(tmp_path):
    (tmp_path / "notiz.md").write_text("x")
    assert praesentation.dateien(tmp_path) == []
