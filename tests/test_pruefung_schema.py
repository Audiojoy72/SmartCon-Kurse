"""pruefung.json — was der Agent liefert, wird geprüft, bevor es zählt."""

import json

import pytest

from app import pruefung

GUELTIG = {
    "titel": "Abschlussprüfung KI-Verordnung",
    "bestehensgrenze": 70,
    "fragen": [
        {"frage": "Seit wann wird Art. 4 KI-VO durchgesetzt?",
         "optionen": ["seit 02.08.2026", "seit 2027", "gar nicht"],
         "richtig": 0,
         "thema": "Level 1",
         "hinweis": "Die nationale Marktüberwachung läuft seit dem 02.08.2026."},
    ],
}


def test_gueltige_datei_wird_geladen(tmp_path):
    pfad = tmp_path / "pruefung.json"
    pfad.write_text(json.dumps(GUELTIG), encoding="utf-8")
    assert pruefung.laden(pfad)["titel"] == GUELTIG["titel"]


def test_kaputtes_json_wird_gemeldet(tmp_path):
    pfad = tmp_path / "pruefung.json"
    pfad.write_text("{ das ist kein json")
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.laden(pfad)


def test_code_zaeune_werden_abgewiesen(tmp_path):
    # Häufigster Agentenfehler: JSON in ```json ... ``` verpackt.
    pfad = tmp_path / "pruefung.json"
    pfad.write_text("```json\n" + json.dumps(GUELTIG) + "\n```")
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.laden(pfad)


def test_ohne_fragen_ungueltig():
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": []})


def test_richtig_muss_auf_eine_option_zeigen():
    frage = {**GUELTIG["fragen"][0], "richtig": 5}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})

    frage = {**GUELTIG["fragen"][0], "richtig": -1}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_richtig_als_bool_wird_abgewiesen():
    # "richtig": true ist in Python isinstance(int) — ohne Bool-Ausschluss
    # würde das unbemerkt als Index 1 durchgehen.
    frage = {**GUELTIG["fragen"][0], "richtig": True}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_zu_wenige_optionen_ungueltig():
    frage = {**GUELTIG["fragen"][0], "optionen": ["nur eine"], "richtig": 0}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_zu_viele_optionen_ungueltig():
    frage = {**GUELTIG["fragen"][0], "optionen": list("abcdef"), "richtig": 0}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_leere_frage_ungueltig():
    frage = {**GUELTIG["fragen"][0], "frage": "  "}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_nicht_string_titel_ungueltig():
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "titel": 12345})


def test_nicht_string_frage_ungueltig():
    frage = {**GUELTIG["fragen"][0], "frage": {"nested": "obj"}}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


def test_nicht_string_option_ungueltig():
    frage = {**GUELTIG["fragen"][0], "optionen": ["a", "b", 3]}
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})


@pytest.mark.parametrize("grenze", [0, 101, "siebzig", None, True])
def test_unsinnige_bestehensgrenze_ungueltig(grenze):
    with pytest.raises(pruefung.PruefungFehler):
        pruefung.pruefe({**GUELTIG, "bestehensgrenze": grenze})


def test_fehlermeldung_nennt_die_fragennummer():
    frage = {**GUELTIG["fragen"][0], "richtig": 9}
    with pytest.raises(pruefung.PruefungFehler, match="Frage 1"):
        pruefung.pruefe({**GUELTIG, "fragen": [frage]})
