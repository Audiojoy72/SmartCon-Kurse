"""Die Grundlage der Prüfung: was ausgeliefert wurde, nicht was geplant war."""

import os

from app.prompts import stoffquelle

FOLIEN = (".pptx", ".pdf", ".key", ".odp")


def test_ohne_alles_ist_es_none(tmp_path):
    assert stoffquelle(tmp_path) is None


def test_curriculum_allein_zaehlt_nicht(tmp_path):
    # Das Curriculum ist der Plan. Zwischen Plan und Auslieferung liegt die
    # Produktion, die kürzt und gewichtet.
    (tmp_path / "curriculum.md").write_text("# Plan")
    assert stoffquelle(tmp_path) is None


def test_erzeugte_html_wird_genommen(tmp_path):
    seite = tmp_path / "schulung.html"
    seite.write_text("<html></html>")
    assert stoffquelle(tmp_path) == seite


def test_juengste_html_gewinnt(tmp_path):
    alt = tmp_path / "alt.html"
    neu = tmp_path / "neu.html"
    alt.write_text("a")
    neu.write_text("b")
    os.utime(alt, (1, 1))
    assert stoffquelle(tmp_path) == neu


def test_hochgeladene_folien_schlagen_die_html(tmp_path):
    # Bei einer Live-Schulung ist der Foliensatz der behandelte Stoff,
    # nicht die Nacharbeit im Portal.
    (tmp_path / "schulung.html").write_text("<html></html>")
    material = tmp_path / "material"
    material.mkdir()
    deck = material / "deck.pptx"
    deck.write_bytes(b"x")
    assert stoffquelle(tmp_path) == deck


def test_alle_folienformate_zaehlen(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    for endung in FOLIEN:
        datei = material / f"deck{endung}"
        datei.write_bytes(b"x")
        assert stoffquelle(tmp_path) == datei
        datei.unlink()


def test_material_ohne_folien_zaehlt_nicht(tmp_path):
    seite = tmp_path / "schulung.html"
    seite.write_text("<html></html>")
    material = tmp_path / "material"
    material.mkdir()
    (material / "notiz.pdf.txt").write_text("x")
    assert stoffquelle(tmp_path) == seite


def test_verzeichnis_mit_foliensuffix_wird_nicht_genommen(tmp_path):
    # Extraktions- und Sync-Tools erstellen manchmal Verzeichnisse statt
    # Dateien mit gleichen Namen (z.B. deck.pptx/). Das darf nicht als Datei
    # zurückgegeben werden.
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").mkdir()  # Verzeichnis, kein File
    echte_datei = material / "real_deck.pptx"
    echte_datei.write_bytes(b"x")
    assert stoffquelle(tmp_path) == echte_datei


def test_html_verzeichnis_wird_nicht_genommen(tmp_path):
    # Das Gleiche für *.html im Projektordner: auch hier kann ein Verzeichnis
    # statt einer Datei existieren.
    (tmp_path / "schulung.html").mkdir()  # Verzeichnis
    echte_seite = tmp_path / "real_schulung.html"
    echte_seite.write_text("<html></html>")
    assert stoffquelle(tmp_path) == echte_seite


def test_pruefung_html_zaehlt_nicht_als_stoffquelle(tmp_path):
    # Eine Prüfung ist nicht der Stoff, den sie abfragt. Sonst würde ein
    # geöffneter Prüfungsbogen (der bei jedem GET neu geschrieben wird) per
    # mtime zur Stoffquelle der nächsten Prüfung — die Prüfung würde sich
    # selbst zur Grundlage.
    (tmp_path / "pruefung.html").write_text("<html></html>")
    assert stoffquelle(tmp_path) is None


def test_juengere_pruefung_html_verdraengt_die_echte_seite_nicht(tmp_path):
    seite = tmp_path / "schulung.html"
    seite.write_text("<html></html>")
    pruefungsseite = tmp_path / "pruefung.html"
    pruefungsseite.write_text("<html></html>")
    os.utime(seite, (1, 1))  # pruefung.html ist die jüngere Datei
    assert stoffquelle(tmp_path) == seite
