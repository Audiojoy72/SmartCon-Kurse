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


@router.get("/kurs/{tnid}", response_class=HTMLResponse)
def portal_kurs(tnid: int, t: dict = Depends(angemeldet)):
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    geschafft = versuche.bestanden(tnid) is not None
    offen = max(0, versuche.MAX_VERSUCHE - versuche.zaehlen(tnid))
    return HTMLResponse(portal.kurs_seite(t, tn, offen, geschafft))


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
                        headers={"Cache-Control": "private, max-age=3600"})


@router.get("/kurs/{tnid}/pruefung", response_class=HTMLResponse)
def portal_pruefung(tnid: int, t: dict = Depends(angemeldet)):
    """Die Fragen — ohne Lösungen.

    Der Aufbau ist Absicht: `pruefung.laden()` liefert die vollständigen
    Fragen, und hier wird genau das weitergereicht, was der Teilnehmer sehen
    darf. „richtig" und „hinweis" bleiben auf dem Server.
    """
    tn = _offen_oder_403(_teilnahme_oder_404(tnid, t))
    try:
        versuche.starten(tnid)
    except versuche.VersuchFehler as e:
        raise HTTPException(409, str(e))

    d = projekte.projekt_dir(tn["slug"])
    daten = pruefung.laden(d / "pruefung.json")
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
    formular = await request.form()
    # Die Felder heißen f0, f1, … — der Index ist der Fragenindex.
    antworten = {schluessel[1:]: wert for schluessel, wert in formular.items()
                 if schluessel.startswith("f") and schluessel[1:].isdigit()}

    try:
        versuch_id = versuche.starten(tnid)
        ergebnis = versuche.auswerten(versuch_id, antworten)
    except versuche.VersuchFehler as e:
        raise HTTPException(409, str(e))

    offen = max(0, versuche.MAX_VERSUCHE - versuche.zaehlen(tnid))
    return HTMLResponse(portal.ergebnis_seite(tn, ergebnis, offen))


@router.get("/kurs/{tnid}/zertifikat", response_class=HTMLResponse)
def portal_zertifikat(tnid: int, t: dict = Depends(angemeldet)):
    """Der Nachweis. Nur nach bestandener Prüfung.

    Kein Zugangsfenster-Check: Wer bestanden hat, soll seinen Nachweis auch
    nach Ablauf noch herunterladen können.
    """
    tn = _teilnahme_oder_404(tnid, t)
    versuch = versuche.bestanden(tnid)
    if versuch is None:
        raise HTTPException(404, "Für diesen Kurs liegt noch kein Nachweis vor")
    return HTMLResponse(portal.zertifikat_seite(t, tn, versuch))
