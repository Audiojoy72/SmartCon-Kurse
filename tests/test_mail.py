"""Mailversand und Vorlagen. Verschickt in Tests nie etwas."""

import pytest

from app import config, mail

EINTRAG = {"name": "Anna Beispiel", "email": "anna@example.org",
           "firma": "Beispiel GmbH", "nachricht": ""}
KURS = {"titel": "KI-Pflichtschulung", "format": "E-Learning, 80–90 Min",
        "preis_cent": 14900, "preis_pauschal": 0}
TERMIN = {"beginn": "2026-09-02T09:00:00", "ende": "2026-09-02T13:00:00"}


def test_ohne_host_ist_nichts_konfiguriert(monkeypatch):
    monkeypatch.setattr(config, "load", lambda: {**config.DEFAULTS, "smtp_host": ""})
    assert mail.konfiguriert() is False


def test_mit_host_ist_es_konfiguriert(monkeypatch):
    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "smtp_host": "mail.example.org",
                                 "smtp_von": "kurse@example.org"})
    assert mail.konfiguriert() is True


def test_senden_ohne_konfiguration_wirft(monkeypatch):
    monkeypatch.setattr(config, "load", lambda: {**config.DEFAULTS, "smtp_host": ""})
    with pytest.raises(mail.MailFehler, match="nicht eingerichtet"):
        mail.senden("anna@example.org", "Betreff", "Text")


def test_bestaetigung_nennt_kurs_und_termin():
    betreff, text = mail.anmeldung_eingegangen(EINTRAG, KURS, TERMIN)
    assert "KI-Pflichtschulung" in betreff
    assert "Anna Beispiel" in text
    assert "02.09.2026" in text
    assert "149,00" in text


def test_bestaetigung_ohne_termin_sagt_das():
    betreff, text = mail.anmeldung_eingegangen(EINTRAG, KURS, None)
    assert "jederzeit" in text.lower() or "ohne festen Termin" in text


def test_pauschalpreis_wird_als_gesamtpreis_ausgewiesen():
    kurs = {**KURS, "preis_cent": 399900, "preis_pauschal": 1}
    _, text = mail.anmeldung_eingegangen(EINTRAG, kurs, None)
    assert "3.999,00" in text
    assert "gesamt" in text.lower()


def test_zugangsmail_enthaelt_passwort_und_adresse():
    betreff, text = mail.zugang_freigeschaltet(
        EINTRAG, KURS, "Abc23xyzQ7mn", "https://kurse.ai-smartcon.de/portal")
    assert "Abc23xyzQ7mn" in text
    assert "https://kurse.ai-smartcon.de/portal" in text
    assert "anna@example.org" in text


def test_keine_mail_behauptet_staatliche_anerkennung():
    for bauen in (lambda: mail.anmeldung_eingegangen(EINTRAG, KURS, TERMIN),
                  lambda: mail.zugang_freigeschaltet(EINTRAG, KURS, "x", "u")):
        _, text = bauen()
        for verboten in ("staatlich anerkannt", "azav", "bildungsgutschein"):
            assert verboten not in text.lower()


def test_kopfzeilen_koennen_nicht_eingeschleust_werden(monkeypatch):
    """Ein Zeilenumbruch im Namen darf keine zusätzliche Kopfzeile erzeugen."""
    gesendet = {}

    class FakeSMTP:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, **kw): pass
        def login(self, *a): pass
        def send_message(self, nachricht):
            gesendet["nachricht"] = nachricht

    monkeypatch.setattr(config, "load",
                        lambda: {**config.DEFAULTS, "smtp_host": "mail.example.org",
                                 "smtp_von": "kurse@example.org"})
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)

    mail.senden("anna@example.org\nBcc: fremd@example.org", "Betreff", "Text")
    an = str(gesendet["nachricht"]["To"])
    assert "\n" not in an and "\r" not in an
    assert gesendet["nachricht"]["Bcc"] is None


def test_bestaetigung_nennt_die_reihenfolge_wie_die_danke_seite():
    """Erst Rechnung, dann Zugang — nicht „in Kürze die Zugangsdaten"."""
    _, text = mail.anmeldung_eingegangen(EINTRAG, KURS, TERMIN)
    assert "Rechnung" in text
    assert text.index("Rechnung") < text.index("Zugangsdaten")


def test_unvollstaendiger_kurs_kippt_die_bestaetigung_nicht():
    """Wie anmeldung_seiten._preis(): ein fehlendes Feld ist kein Grund für 500."""
    _, text = mail.anmeldung_eingegangen(EINTRAG, {"titel": "T", "format": "F"},
                                         None)
    assert "0,00 €" in text
