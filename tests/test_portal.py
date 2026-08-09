"""Portal-Seiten. Reine HTML-Erzeugung, kein Server."""

from app import portal

TEILNEHMER = {"id": 1, "name": "Anna Beispiel", "email": "anna@example.org",
              "firma": "Beispiel GmbH"}
TEILNAHME = {"id": 7, "slug": "kurs", "titel": "KI-Pflichtschulung",
             "nachweis": "AI-SmartCon-Zertifikat", "gueltig_bis": "2026-09-30T12:00:00+00:00",
             "offen": True}
FRAGEN = [
    {"frage": "Seit wann wird Art. 4 durchgesetzt?",
     "optionen": ["seit 02.08.2026", "seit 2027", "gar nicht"], "thema": "Level 1"},
    {"frage": "Was leistet ein AVV <nicht>?",
     "optionen": ["Erlaubnis", "Weisung", "Vertraulichkeit"], "thema": "Level 2"},
]


def test_rahmen_ist_vollstaendig_und_ohne_fremdquellen():
    html = portal.seite("Titel", "<p>Inhalt</p>")
    assert html.startswith("<!doctype html>")
    assert "</html>" in html
    assert "http://" not in html and "https://" not in html
    assert "<script src=" not in html


def test_rahmen_traegt_die_ci_farben():
    html = portal.seite("Titel", "")
    for farbe in ("#060611", "#c9a84c", "#f6f1e8"):
        assert farbe in html


def test_login_seite_hat_die_felder():
    html = portal.login_seite()
    assert 'name="email"' in html
    assert 'name="passwort"' in html
    assert 'type="password"' in html


def test_login_fehler_wird_angezeigt_und_maskiert():
    html = portal.login_seite("E-Mail oder Passwort <falsch>")
    assert "&lt;falsch&gt;" in html
    assert "<falsch>" not in html


def test_kursliste_nennt_die_teilnahmen():
    html = portal.kursliste(TEILNEHMER, [TEILNAHME])
    assert "KI-Pflichtschulung" in html
    assert "Anna Beispiel" in html


def test_geschlossene_teilnahme_ist_nicht_verlinkt():
    zu = {**TEILNAHME, "offen": False}
    html = portal.kursliste(TEILNEHMER, [zu])
    assert "/portal/kurs/7" not in html
    assert "abgelaufen" in html.lower()


def test_geschlossene_aber_bestandene_teilnahme_verlinkt_den_nachweis():
    """Important 3: sonst gibt es nach Ablauf keinen Weg zum Zertifikat mehr."""
    zu = {**TEILNAHME, "offen": False, "bestanden": True}
    html = portal.kursliste(TEILNEHMER, [zu])
    assert "/portal/kurs/7/zertifikat" in html
    assert "abgelaufen" in html.lower()


def test_geschlossene_und_nicht_bestandene_teilnahme_bleibt_ohne_nachweis():
    zu = {**TEILNAHME, "offen": False, "bestanden": False}
    html = portal.kursliste(TEILNEHMER, [zu])
    assert "/portal/kurs/7/zertifikat" not in html


def test_pruefungsseite_zeigt_die_fragen_ohne_loesung():
    html = portal.pruefung_seite(TEILNAHME, FRAGEN, versuch_nr=1, max_versuche=3)
    assert "Seit wann wird Art. 4 durchgesetzt?" in html
    assert "seit 02.08.2026" in html
    # Entscheidend: nichts über die richtige Antwort im Dokument.
    assert "richtig" not in html
    assert "hinweis" not in html.lower()


def test_pruefungsseite_maskiert_html_in_fragen():
    html = portal.pruefung_seite(TEILNAHME, FRAGEN, versuch_nr=1, max_versuche=3)
    assert "&lt;nicht&gt;" in html
    assert "<nicht>" not in html


def test_pruefungsseite_nennt_den_versuch():
    html = portal.pruefung_seite(TEILNAHME, FRAGEN, versuch_nr=2, max_versuche=3)
    assert "2" in html and "3" in html


def test_ergebnisseite_zeigt_prozent_und_urteil():
    ergebnis = {"prozent": 80, "bestanden": True, "treffer": 4, "gesamt": 5,
                "grenze": 70, "rueckmeldung": [
                    {"frage": "F?", "gewaehlt": 0, "richtig": 0, "korrekt": True,
                     "hinweis": "Weil a."}]}
    html = portal.ergebnis_seite(TEILNAHME, ergebnis, weitere_versuche=0)
    assert "80" in html
    assert "bestanden" in html.lower()
    assert "Weil a." in html


def test_ergebnisseite_verschweigt_die_begruendung_solange_versuche_bleiben():
    """Decision: Begründungen nennen die richtige Antwort — ein zweiter
    Versuch darf keine Abschreibübung sein. Stattdessen die schwachen Themen."""
    ergebnis = {"prozent": 40, "bestanden": False, "treffer": 2, "gesamt": 5,
                "grenze": 70, "rueckmeldung": [
                    {"frage": "F1?", "gewaehlt": 1, "richtig": 0, "korrekt": False,
                     "hinweis": "Weil b richtig ist.", "thema": "Level 1"},
                    {"frage": "F2?", "gewaehlt": 1, "richtig": 1, "korrekt": True,
                     "hinweis": "Weil b richtig ist.", "thema": "Level 2"}]}
    html = portal.ergebnis_seite(TEILNAHME, ergebnis, weitere_versuche=2)
    assert "Weil b richtig ist." not in html
    assert "Level 1" in html
    assert "Level 2" not in html  # nur Themen der falschen Antworten


def test_ergebnisseite_zeigt_die_begruendung_beim_letzten_versuch():
    ergebnis = {"prozent": 40, "bestanden": False, "treffer": 2, "gesamt": 5,
                "grenze": 70, "rueckmeldung": [
                    {"frage": "F1?", "gewaehlt": 1, "richtig": 0, "korrekt": False,
                     "hinweis": "Weil a richtig ist.", "thema": "Level 1"}]}
    html = portal.ergebnis_seite(TEILNAHME, ergebnis, weitere_versuche=0)
    assert "Weil a richtig ist." in html


def test_ergebnisseite_nennt_die_restversuche_bei_nichtbestehen():
    ergebnis = {"prozent": 40, "bestanden": False, "treffer": 2, "gesamt": 5,
                "grenze": 70, "rueckmeldung": []}
    html = portal.ergebnis_seite(TEILNAHME, ergebnis, weitere_versuche=2)
    assert "2" in html
    assert "nicht bestanden" in html.lower()


def test_zertifikat_nennt_person_kurs_und_datum():
    versuch = {"prozent": 90, "beendet_am": "2026-08-08T12:00:00+00:00"}
    html = portal.zertifikat_seite(TEILNEHMER, TEILNAHME, versuch)
    assert "Anna Beispiel" in html
    assert "KI-Pflichtschulung" in html
    assert "08.08.2026" in html
    assert "AI-SmartCon-Zertifikat" in html


def test_zertifikat_behauptet_keine_staatliche_anerkennung():
    versuch = {"prozent": 90, "beendet_am": "2026-08-08T12:00:00+00:00"}
    html = portal.zertifikat_seite(TEILNEHMER, TEILNAHME, versuch).lower()
    for verboten in ("staatlich anerkannt", "azav", "bildungsgutschein",
                     "zertifiziert nach"):
        assert verboten not in html


def test_zertifikat_ist_druckbar():
    versuch = {"prozent": 90, "beendet_am": "2026-08-08T12:00:00+00:00"}
    html = portal.zertifikat_seite(TEILNEHMER, TEILNAHME, versuch)
    assert "@media print" in html


def test_kursseite_bettet_die_lerneinheit_ein():
    html = portal.kurs_seite(TEILNEHMER, TEILNAHME, versuche_offen=3, bestanden=False)
    assert 'src="/portal/kurs/7/datei"' in html
    assert "/portal/kurs/7/pruefung" in html


def test_kursseite_zeigt_nach_bestehen_den_nachweis_statt_der_pruefung():
    html = portal.kurs_seite(TEILNEHMER, TEILNAHME, versuche_offen=0, bestanden=True)
    assert "/portal/kurs/7/zertifikat" in html
    assert "/portal/kurs/7/pruefung" not in html


def test_kursseite_ohne_versuche_bietet_keine_pruefung_an():
    html = portal.kurs_seite(TEILNEHMER, TEILNAHME, versuche_offen=0, bestanden=False)
    assert "/portal/kurs/7/pruefung" not in html
    assert "aufgebraucht" in html.lower()


def test_teilnahmebestaetigung_behauptet_keine_pruefung():
    """Ohne Prüfung darf der Nachweis keinen Leistungsnachweis behaupten."""
    t = {"name": "Anna Beispiel", "firma": "Beispiel GmbH"}
    tn = {"id": 1, "titel": "Kurs ohne Prüfung",
          "nachweis": portal.NACHWEIS_TEILNAHME,
          "freigeschaltet_am": "2026-08-09T10:00:00"}
    html = portal.zertifikat_seite(t, tn, None)
    assert "Teilnahmebestätigung" in html
    assert "hat teilgenommen" in html
    assert "erfolgreich abgeschlossen" not in html
    assert "bestanden" not in html
    assert "09.08.2026" in html
    for verboten in ("staatlich anerkannt", "azav", "bildungsgutschein"):
        assert verboten not in html.lower()


def test_zertifikat_nennt_die_pruefung_weiterhin():
    t = {"name": "Anna Beispiel"}
    tn = {"id": 1, "titel": "Kurs mit Prüfung",
          "nachweis": "AI-SmartCon-Zertifikat"}
    html = portal.zertifikat_seite(
        t, tn, {"beendet_am": "2026-08-09T10:00:00", "prozent": 87})
    assert "erfolgreich abgeschlossen" in html
    assert "87 %" in html


def test_kurs_ohne_pruefung_zeigt_keine_pruefung():
    t = {"name": "Anna"}
    tn = {"id": 5, "titel": "Kurs ohne Prüfung"}
    html = portal.kurs_seite(t, tn, versuche_offen=3, bestanden=False,
                             mit_pruefung=False)
    assert "Prüfung starten" not in html
    assert "Versuche" not in html
    assert "/portal/kurs/5/zertifikat" in html


def test_kursliste_verlinkt_die_bestaetigung_auch_nach_ablauf():
    """Sie hängt nur an der Teilnahme, nicht an einem Versuch."""
    t = {"name": "Anna"}
    tn = {"id": 5, "titel": "Kurs", "offen": False, "bestanden": False,
          "nachweis": portal.NACHWEIS_TEILNAHME}
    assert "/portal/kurs/5/zertifikat" in portal.kursliste(t, [tn])

    ohne = {**tn, "nachweis": "AI-SmartCon-Zertifikat"}
    assert "/portal/kurs/5/zertifikat" not in portal.kursliste(t, [ohne])
