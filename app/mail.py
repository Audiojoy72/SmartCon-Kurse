"""Mailversand über SMTP und die Vorlagen dafür.

Standardbibliothek: smtplib, ssl, email.message. Kein Dienstleister, kein
Webhook — die App bleibt eigenständig lauffähig, und die Zustellbarkeit hängt
am Postfach von ai-smartcon.de.

`EmailMessage.__setitem__` weist Zeilenumbrüche in Kopfzeilen zurück, was
Header-Injection über einen Namen oder eine Adresse ausschließt. Der
zusätzliche Riegel unten ist trotzdem da: Er macht die Absicht sichtbar und
überlebt einen Umbau auf eine andere Bibliothek.
"""

import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from . import config

_ZEILENUMBRUCH = re.compile(r"[\r\n]")


class MailFehler(RuntimeError):
    """Versand nicht möglich. Die Meldung ist für die Oberfläche."""


def konfiguriert() -> bool:
    """Ob SMTP-Zugangsdaten hinterlegt sind — nur Host/Absender geprüft, kein Verbindungstest."""
    cfg = config.load()
    return bool(cfg["smtp_host"] and cfg["smtp_von"])


def senden(an: str, betreff: str, text: str) -> None:
    cfg = config.load()
    if not konfiguriert():
        raise MailFehler("Mailversand ist nicht eingerichtet (SMTP-Host/Absender fehlen)")

    nachricht = EmailMessage()
    nachricht["From"] = _ZEILENUMBRUCH.sub("", cfg["smtp_von"])
    nachricht["To"] = _ZEILENUMBRUCH.sub("", an)
    nachricht["Subject"] = _ZEILENUMBRUCH.sub("", betreff)
    nachricht.set_content(text)

    try:
        if cfg["smtp_port"] == 465:
            with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"],
                                  context=ssl.create_default_context()) as server:
                if cfg["smtp_user"]:
                    server.login(cfg["smtp_user"], cfg["smtp_passwort"])
                server.send_message(nachricht)
        else:
            with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
                if cfg["smtp_starttls"]:
                    server.starttls(context=ssl.create_default_context())
                if cfg["smtp_user"]:
                    server.login(cfg["smtp_user"], cfg["smtp_passwort"])
                server.send_message(nachricht)
    except (smtplib.SMTPException, OSError) as e:
        raise MailFehler(f"Versand fehlgeschlagen: {e}") from None


def _preis_text(kurs: dict) -> str:
    betrag = f"{kurs['preis_cent'] / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    zusatz = "gesamt" if kurs["preis_pauschal"] else "pro Person"
    return f"{betrag} € {zusatz}"


def anmeldung_eingegangen(eintrag: dict, kurs: dict, termin: dict | None) -> tuple[str, str]:
    betreff = f"Anmeldung erhalten: {kurs['titel']}"
    if termin:
        beginn = datetime.fromisoformat(termin["beginn"])
        termin_zeile = f"Termin: {beginn.strftime('%d.%m.%Y, %H:%M')} Uhr"
    else:
        termin_zeile = "Termin: ohne festen Termin — jederzeit startbar"

    text = f"""Hallo {eintrag['name']},

vielen Dank für Ihre Anmeldung zu „{kurs['titel']}".

{termin_zeile}
Format: {kurs['format']}
Preis: {_preis_text(kurs)}

Sie erhalten in Kürze eine weitere E-Mail mit Ihren Zugangsdaten zum
Teilnehmer-Portal.

Diese Bescheinigung wird von AI-SmartCon in eigenem Namen ausgestellt.

Viele Grüße
AI-SmartCon
"""
    return betreff, text


def zugang_freigeschaltet(eintrag: dict, kurs: dict, passwort: str, portal_url: str) -> tuple[str, str]:
    betreff = f"Ihr Zugang zu „{kurs['titel']}\""

    text = f"""Hallo {eintrag['name']},

Ihr Zugang zum Teilnehmer-Portal ist freigeschaltet.

Portal: {portal_url}
Benutzername (E-Mail): {eintrag['email']}
Passwort: {passwort}

Bitte bewahren Sie das Passwort sicher auf — nach dieser E-Mail ist es nicht
mehr abrufbar.

Diese Bescheinigung wird von AI-SmartCon in eigenem Namen ausgestellt.

Viele Grüße
AI-SmartCon
"""
    return betreff, text
