"""Die öffentlichen Anmeldeseiten.

Reine Funktionen von Daten zu HTML — ohne Server testbar. Die Routen liegen
in app/anmeldung_routes.py.

Wichtigste Regel: Hier steht nie eine Platzzahl. Ein Termin ist „offen" oder
„ausgebucht". Wer die Auslastung sieht, sieht den Umsatz.
"""

import html as _html
from datetime import datetime

from .portal import FARBEN, STIL

# Das Portal kennt nur E-Mail- und Passwortfelder. Die Anmeldung braucht
# zusätzlich Text, Auswahl und Mehrzeiler.
_ZUSATZ = f"""
  input[type=text], textarea, select {{
    width: 100%; padding: 12px; border-radius: 10px;
    border: 1px solid {FARBEN['akzent']}; background: rgba(30,30,58,.5);
    color: {FARBEN['text']}; font-size: 16px; font-family: inherit;
  }}
  textarea {{ resize: vertical; }}
  h2 {{ font-size: 20px; margin: 0 0 6px; }}
  .warnung {{ color: #f87171; }}
  ul {{ padding-left: 20px; margin: 6px 0 0; }}
"""


def _preis(kurs: dict) -> str:
    """Betrag deutsch, mit dem Zusatz, worauf er sich bezieht."""
    betrag = f"{int(kurs.get('preis_cent', 0)) / 100:,.2f}"
    betrag = betrag.replace(",", "X").replace(".", ",").replace("X", ".")
    zusatz = "gesamt" if kurs.get("preis_pauschal") else "pro Person"
    return f"{betrag} € {zusatz}"


def _datum(iso: str) -> str:
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(iso)


def _uhrzeit(iso: str) -> str:
    try:
        return datetime.fromisoformat(str(iso)).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def seite(titel: str, inhalt: str) -> str:
    """Der gemeinsame Rahmen. Keine externe Quelle, kein Skript."""
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(titel)} · AI-SmartCon</title>
<style>{STIL}{_ZUSATZ}</style>
</head>
<body>
<main>
  <div class="kopf">
    <span class="wortmarke">AI-SmartCon</span>
    <span class="muted">Kurse und Termine</span>
  </div>
{inhalt}
</main>
</body>
</html>
"""


def kursliste(kurse: list[dict]) -> str:
    """Alle ausgeschriebenen Kurse als Karten."""
    if not kurse:
        karten = '  <p class="muted">Zurzeit ist nichts ausgeschrieben.</p>'
    else:
        karten = "".join(f"""  <div class="karte">
    <h2>{_html.escape(str(k["titel"]))}</h2>
    <p class="muted">{_html.escape(str(k.get("format", "")))} · {_preis(k)}</p>
    <p>{_html.escape(str(k.get("beschreibung", "")))}</p>
    <a class="knopf" href="/anmeldung/{_html.escape(str(k["slug"]))}">Zum Kurs</a>
  </div>
""" for k in kurse)
    return seite("Kurse", f"  <h1>Kurse und Termine</h1>\n{karten}")


def kursseite(kurs: dict, termine: list[dict], fehler: str = "",
              werte: dict | None = None) -> str:
    """Kursbeschreibung und Anmeldeformular.

    `termine` kommt aus `kurse.naechste_offene()` und enthält deshalb keine
    Platzzahlen — nur `status` mit „offen" oder „ausgebucht".
    """
    werte = werte or {}

    def wert(feld: str) -> str:
        return _html.escape(str(werte.get(feld, "")))

    offen = [t for t in termine if t.get("status") == "offen"]
    vergeben = [t for t in termine if t.get("status") != "offen"]

    if offen:
        optionen = "".join(
            f'<option value="{int(t["id"])}">{_datum(t["beginn"])}, '
            f'{_uhrzeit(t["beginn"])} Uhr</option>' for t in offen)
        auswahl = f"""      <label>Termin
        <select name="termin_id" required>{optionen}</select>
      </label>"""
    elif termine:
        auswahl = ('      <p class="muted">Alle ausgeschriebenen Termine sind '
                   'vergeben. Melden Sie sich trotzdem an — wir nehmen Sie für '
                   'den nächsten Durchgang auf.</p>')
    else:
        auswahl = ('      <p class="muted">Diese Schulung läuft ohne festen '
                   'Termin. Sie können jederzeit starten.</p>')

    hinweis = ""
    if vergeben:
        zeilen = "".join(f"<li>{_datum(t['beginn'])} — ausgebucht</li>"
                         for t in vergeben)
        hinweis = (f'  <p class="muted">Bereits vergeben:</p>\n'
                   f'  <ul class="muted">{zeilen}</ul>\n')

    meldung = (f'    <p class="warnung">{_html.escape(fehler)}</p>\n'
               if fehler else "")

    inhalt = f"""  <h1>{_html.escape(str(kurs["titel"]))}</h1>
  <p class="muted">{_html.escape(str(kurs.get("format", "")))} · {_preis(kurs)}</p>
  <p>{_html.escape(str(kurs.get("beschreibung", "")))}</p>
  <div class="karte">
{meldung}    <form method="post" action="/anmeldung/{_html.escape(str(kurs["slug"]))}">
{auswahl}
      <label>Name
        <input name="name" type="text" maxlength="120" required value="{wert("name")}">
      </label>
      <label>E-Mail
        <input name="email" type="email" maxlength="200" required value="{wert("email")}">
      </label>
      <label>Firma (optional)
        <input name="firma" type="text" maxlength="120" value="{wert("firma")}">
      </label>
      <label>Nachricht (optional)
        <textarea name="nachricht" rows="4" maxlength="2000">{wert("nachricht")}</textarea>
      </label>
      <button type="submit">Verbindlich anmelden</button>
    </form>
  </div>
{hinweis}"""
    return seite(str(kurs["titel"]), inhalt)


def danke_seite(kurs: dict) -> str:
    """Was nach der Anmeldung passiert — ohne Versprechen, die nicht gelten."""
    inhalt = f"""  <h1>Danke für Ihre Anmeldung</h1>
  <div class="karte">
    <p>Ihre Anmeldung zu <strong>{_html.escape(str(kurs["titel"]))}</strong> ist
      eingegangen. Eine Bestätigung geht per E-Mail an Sie raus.</p>
    <p>Sie bekommen von uns eine <strong>Rechnung</strong>. Sobald die Zahlung
      da ist, schalten wir Ihren Zugang frei und schicken Ihnen die Zugangsdaten
      für das Lernportal.</p>
    <p class="muted">Fragen? Antworten Sie einfach auf die Bestätigungsmail.</p>
  </div>
  <a class="knopf" href="/anmeldung">Zurück zur Übersicht</a>
"""
    return seite("Danke", inhalt)
