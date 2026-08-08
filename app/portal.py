"""Die Seiten des Teilnehmer-Portals.

Reine Funktionen von Daten zu HTML — ohne Server testbar. Die Routen liegen
in app/portal_routes.py.

Wichtigste Regel: Auf der Prüfungsseite steht nichts über die richtige
Antwort. Weder im Markup, noch in einem Attribut, noch in einem Skript.
"""

import html as _html
from datetime import datetime

# AI-SmartCon-CI, wie in app/pruefung.py
FARBEN = {
    "hintergrund": "#060611", "panel": "#1a1a22", "akzent": "#c9a84c",
    "akzent_hell": "#e0c274", "text": "#f6f1e8", "text_sekundaer": "#d8cdb4",
}

_STIL = f"""
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 16px; background: {FARBEN['hintergrund']};
    color: {FARBEN['text']}; font-family: Inter, system-ui, sans-serif;
    line-height: 1.5; overflow-wrap: break-word;
  }}
  main {{ max-width: 760px; margin: 0 auto; }}
  a {{ color: {FARBEN['akzent']}; }}
  h1 {{ font-size: 28px; line-height: 1.2; margin: 0 0 8px; }}
  .kopf {{
    border-bottom: 3px solid {FARBEN['akzent']}; padding-bottom: 16px;
    margin-bottom: 24px; display: flex; flex-wrap: wrap; gap: 12px;
    align-items: baseline; justify-content: space-between;
  }}
  .wortmarke {{ font-weight: 700; letter-spacing: .02em; }}
  .muted {{ color: {FARBEN['text_sekundaer']}; font-size: 14px; }}
  .karte {{
    background: {FARBEN['panel']}; border: 1px solid {FARBEN['akzent']};
    border-radius: 14px; padding: 20px; margin-bottom: 16px;
  }}
  .karte[hidden] {{ display: none; }}
  .zeile {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
  label {{ display: block; margin-bottom: 12px; }}
  label[hidden] {{ display: none; }}
  input[type=email], input[type=password] {{
    width: 100%; padding: 12px; border-radius: 10px;
    border: 1px solid {FARBEN['akzent']}; background: rgba(30,30,58,.5);
    color: {FARBEN['text']}; font-size: 16px;
  }}
  button, .knopf {{
    background: {FARBEN['akzent']}; color: #1a1a22; border: 0;
    border-radius: 10px; padding: 13px 22px; font-size: 15px; font-weight: 600;
    cursor: pointer; text-decoration: none; display: inline-block;
  }}
  button:hover, .knopf:hover {{ background: {FARBEN['akzent_hell']}; }}
  .option {{
    display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px;
    border-radius: 10px; background: rgba(255,255,255,.04); cursor: pointer;
  }}
  .option[hidden] {{ display: none; }}
  .option span {{ min-width: 0; }}
  .thema {{
    color: {FARBEN['akzent']}; font-size: 11px; letter-spacing: .14em;
    text-transform: uppercase; margin: 0 0 8px;
  }}
  .korrekt {{ border-color: #4ade80; }}
  .falsch {{ border-color: #f87171; }}
  .note {{ font-size: 34px; font-weight: 700; color: {FARBEN['akzent']}; }}
"""


def seite(titel: str, inhalt: str, teilnehmer: dict | None = None) -> str:
    """Der gemeinsame Rahmen: Kopf mit Wortmarke, Inhalt, Abmelden."""
    rechts = ""
    if teilnehmer:
        rechts = (f'<span class="muted">{_html.escape(str(teilnehmer["name"]))} · '
                  f'<a href="/portal/abmelden">abmelden</a></span>')
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(titel)} · AI-SmartCon</title>
<style>{_STIL}</style>
</head>
<body>
<main>
  <div class="kopf">
    <span class="wortmarke">AI-SmartCon</span>
    {rechts}
  </div>
{inhalt}
</main>
</body>
</html>
"""


def _datum(iso: str) -> str:
    """ISO-Zeitstempel als deutsches Datum. Unlesbares bleibt unverändert."""
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(iso)


def login_seite(fehler: str = "") -> str:
    """Die Anmeldung. Ohne Hinweis darauf, ob es die Adresse gibt."""
    meldung = (f'<p class="muted" style="color:#f87171">{_html.escape(fehler)}</p>'
               if fehler else "")
    inhalt = f"""  <h1>Anmeldung</h1>
  <p class="muted">Zugangsdaten haben Sie nach der Buchung per E-Mail erhalten.</p>
  <div class="karte">
    {meldung}
    <form method="post" action="/portal/anmelden">
      <label>E-Mail
        <input name="email" type="email" autocomplete="username" required>
      </label>
      <label>Passwort
        <input name="passwort" type="password" autocomplete="current-password" required>
      </label>
      <div class="zeile"><button type="submit">Anmelden</button></div>
    </form>
  </div>
  <p class="muted">Passwort verloren? Melden Sie sich bei AI-SmartCon, wir
    schalten einen neuen Zugang frei.</p>"""
    return seite("Anmeldung", inhalt)


def kursliste(teilnehmer: dict, teilnahmen: list[dict]) -> str:
    """Die Kurse einer Person. Geschlossene Teilnahmen sind nicht verlinkt."""
    if not teilnahmen:
        karten = ('<p class="muted">Für Sie ist noch keine Schulung '
                  'freigeschaltet.</p>')
    else:
        stuecke = []
        for tn in teilnahmen:
            titel = _html.escape(str(tn["titel"]))
            if tn.get("offen"):
                stuecke.append(f"""    <div class="karte">
      <h2>{titel}</h2>
      <p class="muted">Zugang bis {_datum(tn.get("gueltig_bis") or "")}</p>
      <div class="zeile">
        <a class="knopf" href="/portal/kurs/{int(tn["id"])}">Zur Schulung</a>
      </div>
    </div>""")
            else:
                stuecke.append(f"""    <div class="karte">
      <h2>{titel}</h2>
      <p class="muted">Der Zugang ist abgelaufen. Wenden Sie sich an
        AI-SmartCon, wenn Sie ihn verlängern möchten.</p>
    </div>""")
        karten = "\n".join(stuecke)

    inhalt = f"""  <h1>Ihre Schulungen</h1>
{karten}"""
    return seite("Ihre Schulungen", inhalt, teilnehmer)


def kurs_seite(teilnehmer: dict, teilnahme: dict, versuche_offen: int,
               bestanden: bool) -> str:
    """Die Lerneinheit im Rahmen, plus der Weg zur Prüfung."""
    tnid = int(teilnahme["id"])
    if bestanden:
        pruefungsteil = f"""    <p>Sie haben die Prüfung bestanden.</p>
      <div class="zeile">
        <a class="knopf" href="/portal/kurs/{tnid}/zertifikat">Nachweis anzeigen</a>
      </div>"""
    elif versuche_offen > 0:
        wort = "Versuch" if versuche_offen == 1 else "Versuche"
        pruefungsteil = f"""    <p>Sie haben noch {versuche_offen} {wort}.</p>
      <div class="zeile">
        <a class="knopf" href="/portal/kurs/{tnid}/pruefung">Prüfung starten</a>
      </div>"""
    else:
        pruefungsteil = """    <p>Alle Versuche sind aufgebraucht. Wenden Sie sich
        an AI-SmartCon, wenn Sie die Prüfung erneut ablegen möchten.</p>"""

    inhalt = f"""  <h1>{_html.escape(str(teilnahme["titel"]))}</h1>
  <div class="karte">
    <iframe src="/portal/kurs/{tnid}/datei" title="Lerneinheit"
            style="width:100%;height:70vh;border:0;border-radius:10px;background:#fff"></iframe>
  </div>
  <div class="karte">
    <h2>Abschlussprüfung</h2>
{pruefungsteil}
  </div>
  <p class="muted"><a href="/portal/kurse">Zurück zur Übersicht</a></p>"""
    return seite(str(teilnahme["titel"]), inhalt, teilnehmer)


def pruefung_seite(teilnahme: dict, fragen: list[dict], versuch_nr: int,
                   max_versuche: int) -> str:
    """Die Fragen. Ohne jede Angabe darüber, welche Antwort richtig ist.

    Das ist die Regel, an der diese Seite hängt: keine Lösung im Markup, in
    keinem Attribut, in keinem Skript. Deshalb bekommt der Aufrufer die
    Fragen auch ohne die Felder „richtig" und „hinweis" gereicht — und diese
    Funktion liest sie auch dann nicht aus, wenn sie im Dict vorhanden sind.
    """
    stuecke = []
    for nr, frage in enumerate(fragen):
        optionen = "\n".join(
            f'          <label class="option">'
            f'<input type="radio" name="f{nr}" value="{i}" required> '
            f'<span>{_html.escape(str(o))}</span></label>'
            for i, o in enumerate(frage["optionen"]))
        stuecke.append(f"""      <li class="karte">
        <p class="thema">{_html.escape(str(frage.get("thema", "")))}</p>
        <p><strong>{_html.escape(str(frage["frage"]))}</strong></p>
        <div>
{optionen}
        </div>
      </li>""")

    inhalt = f"""  <h1>Abschlussprüfung</h1>
  <p class="muted">{_html.escape(str(teilnahme["titel"]))} · Versuch
    {versuch_nr} von {max_versuche} · {len(fragen)} Fragen · je Frage zählt
    genau eine Antwort.</p>
  <form method="post" action="/portal/kurs/{int(teilnahme["id"])}/pruefung">
    <ol style="list-style:none;padding:0">
{chr(10).join(stuecke)}
    </ol>
    <div class="zeile"><button type="submit">Prüfung abgeben</button></div>
  </form>"""
    return seite("Abschlussprüfung", inhalt)


def ergebnis_seite(teilnahme: dict, ergebnis: dict, weitere_versuche: int) -> str:
    """Die Auswertung samt Begründung je Frage."""
    zeilen = []
    for nr, r in enumerate(ergebnis["rueckmeldung"], start=1):
        klasse = "korrekt" if r["korrekt"] else "falsch"
        urteil = "Richtig." if r["korrekt"] else "Nicht richtig."
        zeilen.append(f"""    <div class="karte {klasse}">
      <p><strong>{nr}. {_html.escape(str(r["frage"]))}</strong></p>
      <p class="muted">{urteil} {_html.escape(str(r["hinweis"]))}</p>
    </div>""")

    tnid = int(teilnahme["id"])
    if ergebnis["bestanden"]:
        weiter = f"""    <p>Bestanden.</p>
    <div class="zeile">
      <a class="knopf" href="/portal/kurs/{tnid}/zertifikat">Nachweis anzeigen</a>
    </div>"""
    elif weitere_versuche > 0:
        wort = "Versuch" if weitere_versuche == 1 else "Versuche"
        weiter = f"""    <p>Nicht bestanden. Sie haben noch {weitere_versuche} {wort}.</p>
    <div class="zeile">
      <a class="knopf" href="/portal/kurs/{tnid}/pruefung">Erneut versuchen</a>
    </div>"""
    else:
        weiter = """    <p>Nicht bestanden, und alle Versuche sind aufgebraucht.
      Wenden Sie sich an AI-SmartCon.</p>"""

    inhalt = f"""  <h1>Ergebnis</h1>
  <div class="karte">
    <p class="note">{ergebnis["prozent"]} %</p>
    <p>{ergebnis["treffer"]} von {ergebnis["gesamt"]} Fragen richtig,
      bestanden ab {ergebnis["grenze"]} %.</p>
{weiter}
  </div>
  <h2>Im Einzelnen</h2>
{chr(10).join(zeilen)}
  <p class="muted"><a href="/portal/kurse">Zurück zur Übersicht</a></p>"""
    return seite("Ergebnis", inhalt)


# Der Druckstil steht getrennt: Er gilt nur für den Nachweis.
_DRUCK = """
  @media print {
    body { background: #fff; color: #111; padding: 0; }
    .kopf, .nicht-drucken { display: none; }
    .urkunde {
      background: #fff; border: 2px solid #c9a84c; page-break-inside: avoid;
    }
    .urkunde h1, .urkunde .name { color: #111; }
    .urkunde .muted { color: #444; }
    .urkunde .thema { color: #7a5e16; }
  }
"""


def zertifikat_seite(teilnehmer: dict, teilnahme: dict, versuch: dict) -> str:
    """Der Nachweis, druckbar.

    Kein serverseitiges PDF: Eine Seite mit @media print kostet keine
    Abhängigkeit, und der Teilnehmer erzeugt das PDF im Browser.

    Was hier NICHT stehen darf: „staatlich anerkannt", ein Verweis auf AZAV
    oder einen Bildungsgutschein, „zertifiziert nach". AI-SmartCon stellt den
    Nachweis in eigenem Namen aus — nicht mehr und nicht weniger.
    """
    bezeichnung = _html.escape(str(teilnahme.get("nachweis") or "Teilnahmebestätigung"))
    firma_html = (f'<p class="muted">{_html.escape(str(teilnehmer["firma"]))}</p>'
                  if teilnehmer.get("firma") else '')
    inhalt = f"""  <div class="karte urkunde" style="text-align:center;padding:40px 24px">
    <p class="thema">{bezeichnung}</p>
    <h1>{_html.escape(str(teilnahme["titel"]))}</h1>
    <p class="muted">hat erfolgreich abgeschlossen</p>
    <p class="name" style="font-size:26px;font-weight:700;margin:16px 0">
      {_html.escape(str(teilnehmer["name"]))}</p>
    {firma_html}
    <hr style="border:0;border-top:1px solid #c9a84c;margin:24px auto;max-width:280px">
    <p class="muted">Abschlussprüfung bestanden am
      {_datum(str(versuch.get("beendet_am") or ""))} mit
      {int(versuch.get("prozent") or 0)} %.</p>
    <p class="muted">Ausgestellt von AI-SmartCon · www.ai-smartcon.de</p>
  </div>
  <div class="zeile nicht-drucken">
    <button onclick="window.print()">Drucken oder als PDF sichern</button>
    <a class="muted" href="/portal/kurse">Zurück zur Übersicht</a>
  </div>"""
    html = seite(bezeichnung, inhalt, teilnehmer)
    # Den Druckstil in den vorhandenen <style>-Block schieben.
    return html.replace("</style>", _DRUCK + "</style>", 1)
