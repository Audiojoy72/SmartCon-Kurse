"""Verwaltungsrouten für Teilnehmer, Teilnahmen und Freischaltung.

Liegt hinter demselben Zugriffsschutz wie der Rest der App. Das Portal —
der Bereich, den Kunden sehen — ist in app/portal_routes.py und schützt sich
selbst.
"""

from fastapi import APIRouter, HTTPException

from . import projekte, teilnehmer, versuche

router = APIRouter(prefix="/api/verwaltung")

MAX_TAGE = 3650


def _tage(body: dict | None, vorgabe: int = 30) -> int:
    tage = (body or {}).get("tage", vorgabe)
    if not isinstance(tage, int) or isinstance(tage, bool) \
            or not 1 <= tage <= MAX_TAGE:
        raise HTTPException(
            400, f"„tage“ muss eine ganze Zahl zwischen 1 und {MAX_TAGE} sein")
    return tage


@router.get("/teilnehmer")
def api_teilnehmer_liste():
    """Alle Teilnehmer mit Teilnahmen, Versuchszahl und Prüfungsstand."""
    eintraege = teilnehmer.liste()
    for t in eintraege:
        for tn in t["teilnahmen"]:
            tn["versuche"] = versuche.zaehlen(tn["id"])
            tn["bestanden"] = versuche.bestanden(tn["id"]) is not None
    return {"teilnehmer": eintraege}


@router.post("/teilnehmer", status_code=201)
def api_teilnehmer_neu(body: dict):
    try:
        tid = teilnehmer.anlegen(
            str(body.get("email", "")), str(body.get("name", "")),
            str(body.get("firma", "")))
    except teilnehmer.TeilnehmerFehler as e:
        # „bereits angelegt“ ist ein Konflikt, alles andere ein Eingabefehler.
        raise HTTPException(409 if "bereits" in str(e) else 400, str(e))
    return {"id": tid}


@router.post("/teilnehmer/{tid}/teilnahme", status_code=201)
def api_teilnahme_neu(tid: int, body: dict):
    """Ordnet dem Teilnehmer eine fertige Schulung zu.

    Spiegelt die Filter des Frontends (`art !== 'praesentation' && phase ===
    'fertig'`) serverseitig — sonst ließe sich über einen direkten API-Aufruf
    eine unfertige Schulung oder eine Präsentation zuordnen.
    """
    slug = str(body.get("slug", "")).strip()
    p = projekte.get(slug)
    if p is None:
        raise HTTPException(404, f"Schulung „{slug}“ nicht gefunden")
    if (p["briefing"].get("art") or projekte.ART_SCHULUNG) != projekte.ART_SCHULUNG:
        raise HTTPException(400, f"„{slug}“ ist eine Präsentation, keine Schulung")
    if p["status"].get("phase") != projekte.PHASE_FERTIG:
        raise HTTPException(400, f"„{slug}“ ist noch nicht fertig")
    d = projekte.projekt_dir(slug)
    if not (d / "pruefung.json").is_file():
        raise HTTPException(
            400, "Für diese Schulung gibt es noch keine Prüfung — erst im "
                 "Projekt „Prüfung erzeugen“ starten")

    titel = p["briefing"].get("thema") or slug
    nachweis = "AI-SmartCon-Zertifikat"
    try:
        tnid = teilnehmer.teilnahme_anlegen(tid, slug, titel, nachweis)
    except teilnehmer.TeilnehmerFehler as e:
        raise HTTPException(409 if "bereits" in str(e) else 404, str(e))
    return {"id": tnid}


@router.post("/teilnehmer/{tid}/freischalten")
def api_freischalten(tid: int, body: dict | None = None):
    """Erzeugt das Passwort und öffnet das Zugangsfenster.

    Der Klartext wird genau hier einmal zurückgegeben und danach nie wieder.
    """
    tage = _tage(body)
    try:
        passwort = teilnehmer.freischalten(tid, tage=tage)
    except teilnehmer.TeilnehmerFehler as e:
        raise HTTPException(404, str(e))
    return {"passwort": passwort, "tage": tage}


@router.post("/teilnahme/{tnid}/verlaengern")
def api_verlaengern(tnid: int, body: dict | None = None):
    tage = _tage(body)
    try:
        teilnehmer.verlaengern(tnid, tage=tage)
    except teilnehmer.TeilnehmerFehler as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "tage": tage}
