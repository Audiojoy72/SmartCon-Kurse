"""Die Routen des Teilnehmer-Portals.

Anders als der Verwaltungsbereich schützt sich dieser Teil selbst: Kunden
haben keine Konten im vorgelagerten Zugriffsschutz. Die Anmeldung läuft über
E-Mail und Passwort, die Sitzung über ein HttpOnly-Cookie.

Zwei Regeln ziehen sich durch alle Routen:

1. Jede Teilnahme wird über `teilnehmer.teilnahme(tnid, t["id"])` geholt —
   der Teilnehmerbezug steht in der Abfrage, nicht in einer Prüfung danach.
   So kann keine Route ihn vergessen.
2. Ein fremder Kurs ergibt 404, nicht 403. Eine 403 würde bestätigen, dass
   es die Teilnahme gibt.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from . import config, portal, projekte, pruefung, teilnehmer, versuche

router = APIRouter(prefix="/portal")

COOKIE = "sitzung"


def angemeldet(request: Request) -> dict:
    """Der angemeldete Teilnehmer, sonst Weiterleitung zum Login."""
    t = teilnehmer.sitzung_pruefen(request.cookies.get(COOKIE, ""))
    if t is None:
        raise HTTPException(status_code=302, headers={"Location": "/portal"})
    return t


def _teilnahme_oder_404(tnid: int, t: dict) -> dict:
    """Die Teilnahme dieses Teilnehmers. Fremde oder unbekannte: 404."""
    tn = teilnehmer.teilnahme(tnid, t["id"])
    if tn is None:
        raise HTTPException(404, "Kurs nicht gefunden")
    return tn


def _offen_oder_403(tn: dict) -> dict:
    if not tn.get("offen"):
        raise HTTPException(
            403, "Der Zugang zu diesem Kurs ist abgelaufen. Wenden Sie sich an "
                 "AI-SmartCon, wenn Sie ihn verlängern möchten.")
    return tn


def _pruefung_laden_oder_fehler(slug: str) -> dict:
    """pruefung.json einer Teilnahme — oder ein sprechender Fehler.

    Eine Teilnahme kann eine Schulung referenzieren, deren Projektordner
    inzwischen gelöscht wurde (`DELETE /api/projekte/{slug}` kennt keinen
    Papierkorb), oder deren pruefung.json defekt ist. Beides ist ein
    erreichbarer Zustand, kein theoretischer — hier abgefangen, statt den
    Teilnehmer eine Serverausnahme sehen zu lassen.
    """
    d = projekte.projekt_dir(slug)
    if d is None:
        raise HTTPException(404, "Schulung nicht gefunden")
    try:
        return pruefung.laden(d / "pruefung.json")
    except pruefung.PruefungFehler:
        raise HTTPException(
            409, "Diese Prüfung steht gerade nicht zur Verfügung. Wenden Sie "
                 "sich an AI-SmartCon.")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def portal_start(request: Request):
    """Login — oder gleich weiter, wenn die Sitzung noch läuft."""
    if teilnehmer.sitzung_pruefen(request.cookies.get(COOKIE, "")):
        return RedirectResponse("/portal/kurse", status_code=302)
    return HTMLResponse(portal.login_seite())


@router.post("/anmelden")
def portal_anmelden(email: str = Form(...), passwort: str = Form(...)):
    """Prüft die Zugangsdaten und setzt das Sitzungscookie.

    Bei Ablehnung bewusst dieselbe Meldung für „unbekannt" und „falsches
    Passwort" — sonst verrät die Maske, welche Adressen Kunde sind.
    """
    token = teilnehmer.anmelden(email, passwort)
    if token is None:
        return HTMLResponse(
            portal.login_seite("E-Mail oder Passwort stimmt nicht."),
            status_code=200)

    antwort = RedirectResponse("/portal/kurse", status_code=302)
    antwort.set_cookie(
        COOKIE, token, httponly=True, samesite="Lax",
        secure=config.load().get("portal_secure_cookie", True),
        max_age=teilnehmer.SITZUNG_STUNDEN * 3600, path="/portal")
    return antwort


@router.get("/abmelden")
def portal_abmelden(request: Request):
    """Entwertet die Sitzung serverseitig und löscht das Cookie."""
    teilnehmer.abmelden(request.cookies.get(COOKIE, ""))
    antwort = RedirectResponse("/portal", status_code=302)
    antwort.delete_cookie(COOKIE, path="/portal")
    return antwort


@router.get("/kurse", response_class=HTMLResponse)
def portal_kurse(t: dict = Depends(angemeldet)):
    return HTMLResponse(portal.kursliste(t, teilnehmer.teilnahmen_von(t["id"])))


def _mit_pruefung(tn: dict) -> bool:
    """Ob dieser Kurs eine Prüfung hat — entschieden an der Bezeichnung.

    Das Zertifikat setzt eine bestandene Prüfung voraus, die Teilnahme-
    bestätigung nicht. Die Bezeichnung ist damit die eine Stelle, an der das
    hängt: sie kommt beim Freischalten aus `kurs.nachweis` und ist die
    Entscheidung des Betreibers.
    """
    return tn.get("nachweis") != teilnehmer.NACHWEIS_TEILNAHME


def _pruefung_oder_404(tn: dict) -> None:
    """Sperrt die Prüfungsrouten für Kurse, die keine Prüfung haben.

    Ohne das ließe sich der Weg über die Adresszeile trotzdem gehen — und ein
    Versuch würde gezählt, auf einen Nachweis, der davon nicht abhängt.
    """
    if not _mit_pruefung(tn):
        raise HTTPException(404, "Für diesen Kurs gibt es keine Prüfung")


@router.get("/kurs/{tnid}", response_class=HTMLResponse)
def portal_kurs(tnid: int, t: dict = Depends(angemeldet)):
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    geschafft = versuche.bestanden(tnid) is not None
    offen = max(0, versuche.MAX_VERSUCHE - versuche.zaehlen(tnid))
    return HTMLResponse(
        portal.kurs_seite(t, tn, offen, geschafft, _mit_pruefung(tn)))


# Die Lerneinheit ist agent-generiert und ihr Input schließt vom Kunden
# geliefertes Stoffquelle-Material ein — eine Prompt-Injection dort, die zu
# Skript im HTML wird, könnte sonst (same-origin, kein Login nötig) gegen
# die Werkstatt-API laufen, z. B. DELETE /api/projekte/<slug> (unwiederherstell-
# bar, siehe CLAUDE.md). `sandbox` ist keine Option: ohne `allow-same-origin`
# bräche das laut skill/schulung/SKILL.md vorgeschriebene localStorage für den
# Fortschritt. Also stattdessen per CSP den Netzwerkzugriff kappen —
# `connect-src 'none'` ist die tragende Direktive, sie unterbindet
# fetch/XHR/WebSocket aus der Lerneinheit heraus.
#
# `style-src 'unsafe-inline'` steht zusätzlich zur ursprünglich geplanten
# Direktive da: Ohne sie fällt style-src auf default-src zurück (kein
# `unsafe-inline` dort) und blockt den kompletten <style>-Block der
# Lerneinheit — nicht nur einzelne style="…"-Attribute. Live gegen
# projects/passwort-hygiene-im-team/ geprüft: ohne diese Zeile rendert die
# Seite mit dem Browser-Default-Stylesheet (Times New Roman, transparenter
# Hintergrund), das eigentliche Design kommt nie an. Für die Sicherheit ist
# das ohne Bedeutung — style-src betrifft CSS, keinen Code-Ausführungspfad.
#
# `frame-src 'none'; child-src 'none'; object-src 'none'` schließen einen
# tatsächlichen Umgehungsweg, keinen theoretischen: Ein Skript in der
# Lerneinheit kann `/static/index.html` (selbst same-origin, ohne jede CSP
# ausgeliefert) in ein `<iframe>` laden und dann
# `frame.contentWindow.fetch('/api/projekte/<slug>', {method:'DELETE'})`
# aufrufen. CSP gilt pro Dokument, und `fetch` läuft im "relevant settings
# object" des Globals, auf dem es aufgerufen wird — also dem des geframeten
# Dokuments mit dessen (fehlender) Policy, nicht der des Elternteils.
# `connect-src 'none'` allein bindet nur das Dokument der Lerneinheit selbst
# und verhindert diesen Umweg über ein zweites Dokument nicht. Reproduziert
# im Browser gegen projects/passwort-hygiene-im-team/ — ohne diese drei
# Direktiven lief der DELETE-Aufruf über das geframete /static/index.html
# durch. `frame-src`/`child-src` fallen sonst auf `default-src 'self' …`
# zurück, das Framing wäre also erlaubt; kein Preset erzeugt je ein
# `<iframe>` (`grep -l "<iframe" projects/*/*.html` ist leer, der Skill
# erwähnt weder Frames noch Workers), die Direktiven kosten also nichts.
#
# Was diese Policy NICHT schließt: `window.open('/static/index.html')` +
# `postMessage` oder ein direkter Tab-Wechsel sind keine Framing-Vorgänge
# und damit nicht CSP-gebunden — eine geöffnete Seite bringt ihre eigene
# (hier: fehlende) Policy mit. Das vollständig zu schließen bräuchte einen
# restriktiven Header auch auf den Werkstatt- und /static-Antworten selbst,
# nicht nur auf der Lerneinheit — eine eigene, hier bewusst nicht gemachte
# Änderung.
_LERNEINHEIT_CSP = (
    "default-src 'self' data: blob:; "
    "script-src 'unsafe-inline' 'unsafe-eval' data: blob:; "
    "style-src 'unsafe-inline'; "
    "connect-src 'none'; form-action 'none'; frame-ancestors 'self'; "
    "frame-src 'none'; child-src 'none'; object-src 'none'"
)


@router.get("/kurs/{tnid}/datei")
def portal_kurs_datei(tnid: int, t: dict = Depends(angemeldet)):
    """Die Lerneinheit selbst — rund 3 MB, deshalb mit Cache-Erlaubnis.

    `private` statt `public`: Ein geteilter Zwischenspeicher darf die Datei
    nicht an andere ausliefern.
    """
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    d = projekte.projekt_dir(tn["slug"])
    if d is None:
        raise HTTPException(404, "Schulung nicht gefunden")
    seiten = sorted(
        (p for p in d.glob("*.html")
         if p.is_file() and p.name != pruefung.HTML_DATEINAME),
        key=lambda p: (p.stat().st_mtime, p.name))
    if not seiten:
        raise HTTPException(404, "Für diese Schulung liegt keine Lerneinheit vor")
    return FileResponse(seiten[-1], media_type="text/html",
                        headers={"Cache-Control": "private, max-age=3600",
                                 "Content-Security-Policy": _LERNEINHEIT_CSP})


@router.get("/kurs/{tnid}/pruefung", response_class=HTMLResponse)
def portal_pruefung(tnid: int, t: dict = Depends(angemeldet)):
    """Die Fragen — ohne Lösungen.

    Der Aufbau ist Absicht: `pruefung.laden()` liefert die vollständigen
    Fragen, und hier wird genau das weitergereicht, was der Teilnehmer sehen
    darf. „richtig" und „hinweis" bleiben auf dem Server.
    """
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    _pruefung_oder_404(tn)
    daten = _pruefung_laden_oder_fehler(tn["slug"])

    try:
        versuche.starten(tnid)
    except versuche.VersuchFehler as e:
        raise HTTPException(409, str(e))

    ohne_loesung = [{"frage": f["frage"], "optionen": f["optionen"],
                     "thema": f.get("thema", "")} for f in daten["fragen"]]
    return HTMLResponse(portal.pruefung_seite(
        tn, ohne_loesung, versuch_nr=versuche.zaehlen(tnid),
        max_versuche=versuche.MAX_VERSUCHE))


@router.post("/kurs/{tnid}/pruefung", response_class=HTMLResponse)
async def portal_pruefung_abgeben(tnid: int, request: Request,
                                  t: dict = Depends(angemeldet)):
    """Nimmt das Formular und wertet serverseitig aus."""
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    _pruefung_oder_404(tn)
    formular = await request.form()
    # Die Felder heißen f0, f1, … — der Index ist der Fragenindex.
    antworten = {schluessel[1:]: wert for schluessel, wert in formular.items()
                 if schluessel.startswith("f") and schluessel[1:].isdigit()}

    try:
        versuch_id = versuche.starten(tnid)
        ergebnis = versuche.auswerten(versuch_id, antworten)
    except versuche.VersuchFehler as e:
        raise HTTPException(409, str(e))
    except pruefung.PruefungFehler:
        # Der Ordner oder die pruefung.json ist zwischen Start und Abgabe
        # verschwunden oder kaputt gegangen — siehe _pruefung_laden_oder_fehler.
        raise HTTPException(
            409, "Diese Prüfung steht gerade nicht zur Verfügung. Wenden Sie "
                 "sich an AI-SmartCon.")

    offen = max(0, versuche.MAX_VERSUCHE - versuche.zaehlen(tnid))
    return HTMLResponse(portal.ergebnis_seite(tn, ergebnis, offen))


@router.get("/kurs/{tnid}/zertifikat", response_class=HTMLResponse)
def portal_zertifikat(tnid: int, t: dict = Depends(angemeldet)):
    """Der Nachweis.

    Das Zertifikat gibt es nur nach bestandener Prüfung; die Teilnahme-
    bestätigung hängt allein an der Teilnahme und ist ab der Freischaltung
    abrufbar — der Kurs hat ja keine Prüfung, die man bestehen könnte.

    Kein Zugangsfenster-Check: Ein einmal erworbener Nachweis bleibt auch
    nach Ablauf des Zugangs abrufbar.
    """
    tn = _teilnahme_oder_404(tnid, t)
    if not _mit_pruefung(tn):
        return HTMLResponse(portal.zertifikat_seite(t, tn, None))
    versuch = versuche.bestanden(tnid)
    if versuch is None:
        raise HTTPException(404, "Für diesen Kurs liegt noch kein Nachweis vor")
    return HTMLResponse(portal.zertifikat_seite(t, tn, versuch))
