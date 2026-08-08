"""Level-Parser: liest die Level-Übersicht aus einem curriculum.md."""

from app.curriculum import normalisiere_medium, parse_level

EINE_TABELLE = """
## 3. Level-Übersicht

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 1 | Ziel eins | Merk eins | **FILM** | Zeitleiste |
| 2 | Ziel zwei | Merk zwei | ANIMATION | Quiz |
| — | Abschluss-Check | — | — | 8 Fragen |
"""

ZWEI_TABELLEN = """
### Modul A

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 1 | Ziel eins | Merk eins | **FILM** | Zeitleiste |
| 2 | Ziel zwei | Merk zwei | ANIMATION | Quiz |

### Modul B

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 3 | Ziel drei | Merk drei | ANIMATION + BILD | Slider |
| 4 | Ziel vier | Merk vier | **FILM** | Story |
"""


def test_eine_tabelle_wird_gelesen():
    level = parse_level(EINE_TABELLE)
    assert [l["level"] for l in level] == ["1", "2"]
    assert level[0]["lernziel"] == "Ziel eins"
    assert level[1]["interaktion"] == "Quiz"


def test_zeile_ohne_nummer_wird_uebersprungen():
    # Die „Abschluss-Check"-Zeile hat keine Level-Nummer und ist kein Level.
    assert len(parse_level(EINE_TABELLE)) == 2


def test_zwei_tabellen_werden_zusammengefasst():
    # Der Bug vom 07.08.2026: Der Parser brach nach der ersten Tabelle ab,
    # dadurch fehlten im Freigabe-Gate fünf Level — darunter ein FILM für
    # 243 Credits, der so weder sichtbar noch herunterstufbar war.
    level = parse_level(ZWEI_TABELLEN)
    assert [l["level"] for l in level] == ["1", "2", "3", "4"]


def test_doppelte_level_nummer_erstes_gewinnt():
    md = ZWEI_TABELLEN + """
### Wiederholung

| Level | Lernziel | Merksatz | Medium | Interaktion |
|---|---|---|---|---|
| 1 | Anderes Ziel | Merk | BILD | Anders |
"""
    level = parse_level(md)
    assert [l["level"] for l in level] == ["1", "2", "3", "4"]
    assert level[0]["lernziel"] == "Ziel eins"


def test_ohne_passende_tabelle_leere_liste():
    assert parse_level("# Nur Text, keine Tabelle") == []
    assert parse_level("| a | b |\n|---|---|\n| 1 | 2 |") == []


def test_tabelle_ohne_trennzeile_ist_keine_tabelle():
    md = "| Level | Medium |\n| 1 | FILM |"
    assert parse_level(md) == []


def test_medium_normalisierung():
    assert normalisiere_medium("**FILM**") == "FILM"
    assert normalisiere_medium("ANIMATION + BILD (Hero)") == "ANIMATION"
    assert normalisiere_medium("  bild  ") == "BILD"
    assert normalisiere_medium("Sonstiges") == "SONSTIGES"
