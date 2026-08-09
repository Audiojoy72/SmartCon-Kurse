"""Die öffentlichen Anmeldeseiten."""

from app import anmeldung_seiten as seiten

KURS = {"id": 1, "slug": "ki-pflicht", "titel": "KI-Pflichtschulung",
        "beschreibung": "Pflicht nach Art. 4 KI-VO.",
        "format": "E-Learning, 80–90 Min", "preis_cent": 14900,
        "preis_pauschal": 0}
TERMINE = [{"id": 7, "beginn": "2026-09-02T09:00:00",
            "ende": "2026-09-02T13:00:00", "status": "offen"},
           {"id": 8, "beginn": "2026-09-16T09:00:00",
            "ende": "2026-09-16T13:00:00", "status": "ausgebucht"}]


def test_rahmen_ohne_fremdquellen():
    html = seiten.seite("Titel", "<p>Inhalt</p>")
    assert html.startswith("<!doctype html>")
    assert "http://" not in html and "https://" not in html
    assert "<script src=" not in html


def test_kursliste_verlinkt_die_kurse():
    html = seiten.kursliste([KURS])
    assert "KI-Pflichtschulung" in html
    assert "/anmeldung/ki-pflicht" in html
    assert "149,00" in html


def test_kursseite_zeigt_offene_termine_als_auswahl():
    html = seiten.kursseite(KURS, TERMINE)
    assert 'value="7"' in html
    assert "02.09.2026" in html


def test_ausgebuchte_termine_sind_nicht_waehlbar():
    html = seiten.kursseite(KURS, TERMINE)
    assert 'value="8"' not in html
    assert "ausgebucht" in html.lower()


def test_keine_platzzahlen_auf_der_seite():
    """Nach außen nie Zahlen."""
    html = seiten.kursseite(KURS, TERMINE).lower()
    for verboten in ("plätze", "plaetze", "belegt", "frei "):
        assert verboten not in html


def test_terminloser_kurs_zeigt_kein_auswahlfeld():
    html = seiten.kursseite(KURS, [])
    assert "<select" not in html
    assert "jederzeit" in html.lower()


def test_formular_hat_die_felder():
    html = seiten.kursseite(KURS, TERMINE)
    for feld in ('name="name"', 'name="email"', 'name="firma"',
                 'name="nachricht"'):
        assert feld in html


def test_fehler_wird_angezeigt_und_maskiert():
    html = seiten.kursseite(KURS, TERMINE, fehler="Termin <voll>")
    assert "&lt;voll&gt;" in html
    assert "<voll>" not in html


def test_eingaben_bleiben_nach_einem_fehler_stehen():
    html = seiten.kursseite(KURS, TERMINE, fehler="Fehler",
                            werte={"name": "Anna", "email": "anna@example.org"})
    assert 'value="Anna"' in html
    assert 'value="anna@example.org"' in html


def test_eingaben_werden_maskiert():
    html = seiten.kursseite(KURS, TERMINE, fehler="F",
                            werte={"name": '"><script>alert(1)</script>'})
    assert "<script>alert(1)</script>" not in html


def test_danke_seite_nennt_die_naechsten_schritte():
    html = seiten.danke_seite(KURS)
    assert "Rechnung" in html
    assert "KI-Pflichtschulung" in html


def test_seiten_behaupten_keine_staatliche_anerkennung():
    for html in (seiten.kursliste([KURS]), seiten.kursseite(KURS, TERMINE),
                 seiten.danke_seite(KURS)):
        for verboten in ("staatlich anerkannt", "azav", "bildungsgutschein"):
            assert verboten not in html.lower()
