"""Prüfungs-HTML: offline lauffähig, ohne Server, im AI-SmartCon-CI."""

from app import pruefung

DATEN = {
    "titel": "Abschlussprüfung KI-Verordnung",
    "bestehensgrenze": 70,
    "fragen": [
        {"frage": "Seit wann wird Art. 4 durchgesetzt?",
         "optionen": ["seit 02.08.2026", "seit 2027", "gar nicht"],
         "richtig": 0, "thema": "Level 1", "hinweis": "Marktüberwachung seit 02.08.2026."},
        {"frage": "Was leistet ein AVV <nicht>?",
         "optionen": ["Erlaubnis", "Weisungsbindung", "Vertraulichkeit"],
         "richtig": 0, "thema": "Level 3", "hinweis": "Er macht nichts erlaubt."},
    ],
}


def test_html_ist_vollstaendig_und_eigenstaendig():
    html = pruefung.als_html(DATEN)
    assert html.startswith("<!doctype html>")
    assert "</html>" in html
    # Offline lauffähig: kein Verweis nach draußen.
    assert "http://" not in html
    assert "https://" not in html
    assert "<script src=" not in html
    assert "<link rel=\"stylesheet\"" not in html


def test_titel_und_fragen_stehen_drin():
    html = pruefung.als_html(DATEN)
    assert DATEN["titel"] in html
    assert "Seit wann wird Art. 4 durchgesetzt?" in html
    assert "seit 02.08.2026" in html


def test_html_wird_maskiert():
    # Ein „<" im Fragetext darf kein Markup werden.
    html = pruefung.als_html(DATEN)
    assert "&lt;nicht&gt;" in html
    assert "<nicht>" not in html


def test_ci_farben_sind_gesetzt():
    html = pruefung.als_html(DATEN)
    for farbe in ("#060611", "#c9a84c", "#f6f1e8"):
        assert farbe in html


def test_design_ueberschreibt_die_vorgabe():
    html = pruefung.als_html(DATEN, design={"akzent": "#ff0000"})
    assert "#ff0000" in html


def test_bestehensgrenze_und_fragenzahl_stehen_im_javascript():
    html = pruefung.als_html(DATEN)
    assert "70" in html
    assert "\"richtig\": 0" in html or "richtig:0" in html.replace(" ", "")


def test_lösungen_stehen_nicht_im_sichtbaren_text():
    # Die Auswertung braucht die Lösungen im Skript — sie dürfen aber nicht
    # als Markierung im Fragebogen selbst auftauchen.
    html = pruefung.als_html(DATEN)
    fragebogen = html.split("<script")[0]
    assert "richtig" not in fragebogen


def test_hinweis_kann_das_script_nicht_vorzeitig_beenden():
    # "hinweis" ist ungeprüfter Agenten-Freitext (siehe _pruefe_frage). Ein
    # "</script>" darin darf den Script-Block nicht vorzeitig schließen —
    # sonst stehen die restlichen Lösungen als Klartext-Markup auf der Seite.
    daten = {
        "titel": "Sicherheit",
        "bestehensgrenze": 70,
        "fragen": [
            {"frage": "Was ist XSS?", "optionen": ["Angriff", "Feature", "Bug"],
             "richtig": 0, "thema": "Level 1",
             "hinweis": "Testet z.B. </script><script>alert(1)</script>"},
        ],
    }
    html = pruefung.als_html(daten)
    assert "</script><script>alert(1)</script>" not in html
    # Der HTML-Tokenizer beendet script-Inhalt nur bei "</script" — genau
    # eine solche Sequenz darf im gesamten Dokument stehen (die echte,
    # schließende). Der injizierte Text darf keine zweite erzeugen.
    assert html.count("</script>") == 1


def test_design_ueberschreibt_gueltige_hex_farbe():
    html = pruefung.als_html(DATEN, design={"akzent": "#ff0000"})
    assert "--akzent: #ff0000;" in html


def test_design_mit_css_injection_wird_verworfen():
    # design ist Agenten-Freitext (z. B. aus einer design.md) und landet
    # ungeprüft in einem <style>-Block — nur gültige Hex-Farben übernehmen.
    boese = "red; } body { background: url(javascript:alert(1)"
    html = pruefung.als_html(DATEN, design={"akzent": boese})
    assert boese not in html
    assert f"--akzent: {pruefung.FARBEN['akzent']};" in html


def test_hinweis_kann_tokenizer_nicht_ueber_kommentar_umleiten():
    # Ein reines "</" → "<\/" reicht nicht: "<!--<script" schickt den
    # HTML-Tokenizer schon vor dem "/" in den script-data-double-escaped-
    # Zustand — das echte "</script>" der Vorlage terminiert das Element
    # dann nicht mehr, und alles danach (inkl. der übrigen Lösungen) wird
    # als Skriptinhalt statt als Markup interpretiert.
    daten = {
        "titel": "Sicherheit",
        "bestehensgrenze": 70,
        "fragen": [
            {"frage": "Was ist XSS?", "optionen": ["Angriff", "Feature", "Bug"],
             "richtig": 0, "thema": "Level 1",
             "hinweis": "Testet z.B. <!--<script"},
        ],
    }
    html = pruefung.als_html(daten)
    assert "<!--<script" not in html
    assert html.count("</script>") == 1
