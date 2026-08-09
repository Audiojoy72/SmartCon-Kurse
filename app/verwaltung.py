"""Verwaltungsrouten für Teilnehmer, Teilnahmen und Freischaltung.

Liegt hinter demselben Zugriffsschutz wie der Rest der App. Das Portal —
der Bereich, den Kunden sehen — ist in app/portal_routes.py und schützt sich
selbst.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

from . import anmeldung, config, kurse, mail, projekte, teilnehmer, versuche

router = APIRouter(prefix="/api/verwaltung")

log = logging.getLogger(__name__)

MAX_TAGE = 3650
TERMIN_WOCHEN_MAX = 104  # zwei Jahre im Voraus reicht


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
    # Dieser Weg verlangt oben eine pruefung.json, also gibt es hier immer
    # eine Prüfung — und damit das Zertifikat. Über einen Kurs entscheidet
    # das stattdessen dessen `nachweis`.
    nachweis = teilnehmer.NACHWEIS_ZERTIFIKAT
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


def _int(body: dict, feld: str, vorgabe: int, min_: int, max_: int) -> int:
    wert = body.get(feld, vorgabe)
    if not isinstance(wert, int) or isinstance(wert, bool) \
            or not min_ <= wert <= max_:
        raise HTTPException(
            400, f"„{feld}“ muss eine ganze Zahl zwischen {min_} und {max_} sein")
    return wert


@router.get("/kurse")
def api_kurse_liste():
    """Alle Kurse mit ihren kommenden Terminen — hier **mit** Platzzahlen.

    Das ist die Innensicht hinter dem Zugriffsschutz. Die öffentliche Sicht
    in app/anmeldung_seiten.py nennt nie eine Zahl.
    """
    eintraege = kurse.liste()
    for k in eintraege:
        k["termine"] = kurse.termine(k["id"])
    return {"kurse": eintraege}


@router.post("/kurse", status_code=201)
def api_kurs_neu(body: dict):
    felder = _kurs_zahlen_pruefen({f: body[f] for f in kurse.FELDER if f in body})
    try:
        kid = kurse.anlegen(str(body.get("slug", "")), str(body.get("titel", "")),
                            **{f: v for f, v in felder.items() if f != "titel"})
    except kurse.KursFehler as e:
        raise HTTPException(409 if "bereits" in str(e) else 400, str(e))
    return {"id": kid}


# Zahlenfelder des Kurses mit ihren Grenzen. Ohne Typprüfung landet
# {"plaetze": "viele"} dank SQLite-Affinität als Text in einer
# INTEGER-NOT-NULL-Spalte und fällt erst irgendwo später auf.
KURS_ZAHLEN = {"preis_cent": (0, 100_000_000), "plaetze": (0, 10_000)}
# Schalter. Das Frontend schickt sie mal als true/false, mal als 1/0.
KURS_FLAGGEN = ("preis_pauschal", "aktiv")


def _kurs_zahlen_pruefen(body: dict) -> dict:
    """Gibt `body` mit geprüften Zahlen- und Schalterfeldern zurück."""
    body = dict(body)
    for feld in KURS_FLAGGEN:
        if feld not in body:
            continue
        wert = body[feld]
        if isinstance(wert, bool) or (isinstance(wert, int) and wert in (0, 1)):
            body[feld] = int(wert)
        else:
            raise HTTPException(400, f"„{feld}“ muss wahr oder falsch sein")
    for feld, (min_, max_) in KURS_ZAHLEN.items():
        if feld in body:
            body[feld] = _int(body, feld, min_, min_, max_)
    return body


@router.post("/kurse/{kid}")
def api_kurs_aendern(kid: int, body: dict):
    unbekannt = set(body) - set(kurse.FELDER)
    if unbekannt:
        raise HTTPException(400, f"Unbekannte Felder: {', '.join(sorted(unbekannt))}")
    body = _kurs_zahlen_pruefen(body)
    try:
        kurse.aendern(kid, **body)
    except kurse.KursFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"ok": True}


@router.post("/kurse/{kid}/serie", status_code=201)
def api_serie_neu(kid: int, body: dict):
    """Legt die Regel an und erzeugt gleich die Termine der nächsten Wochen."""
    wochen = _int(body, "wochen", 26, 1, TERMIN_WOCHEN_MAX)
    try:
        sid = kurse.serie_anlegen(
            kid, wochentag=_int(body, "wochentag", 0, 0, 6),
            uhrzeit=str(body.get("uhrzeit", "09:00")),
            dauer_tage=_int(body, "dauer_tage", 1, 1, 30),
            rhythmus=_int(body, "rhythmus", 1, 1, 52))
        anzahl = kurse.termine_erzeugen(
            sid, bis=date.today() + timedelta(weeks=wochen))
    except kurse.KursFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"serie_id": sid, "termine": anzahl}


@router.post("/termine/{tid}/status")
def api_termin_status(tid: int, body: dict):
    try:
        kurse.termin_status(tid, str(body.get("status", "")))
    except kurse.KursFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"ok": True}


@router.get("/anmeldungen")
def api_anmeldungen_liste():
    return {"anmeldungen": anmeldung.liste()}


@router.post("/anmeldungen/{aid}/status")
def api_anmeldung_status(aid: int, body: dict):
    try:
        anmeldung.status_setzen(aid, str(body.get("status", "")))
    except anmeldung.AnmeldungFehler as e:
        raise HTTPException(404 if "nicht gefunden" in str(e) else 400, str(e))
    return {"ok": True}


@router.post("/anmeldungen/{aid}/freischalten")
def api_anmeldung_freischalten(aid: int):
    """Aus der bezahlten Anmeldung wird ein Teilnehmer mit Portalzugang.

    Das Passwort wird hier genau einmal zurückgegeben. Deshalb darf ein
    Fehler beim Mailversand die Antwort nicht kippen — sonst ist der Zugang
    angelegt und der Klartext für immer weg.
    """
    try:
        _, passwort = anmeldung.zu_teilnehmer(aid)
    except anmeldung.AnmeldungFehler as e:
        text = str(e)
        if "nicht gefunden" in text:
            raise HTTPException(404, text)
        raise HTTPException(409 if "bereits" in text else 400, text)

    eintrag = anmeldung.eintrag(aid)
    kurs = kurse.kurs(eintrag["kurs_id"])
    versendet = False
    if mail.konfiguriert():
        try:
            betreff, text = mail.zugang_freigeschaltet(
                eintrag, kurs, passwort,
                (config.load().get("portal_url") or "").rstrip("/") or "/portal")
            mail.senden(eintrag["email"], betreff, text)
            versendet = True
        except Exception:
            log.exception("Zugangsmail zu Anmeldung %s nicht verschickt", aid)
    return {"passwort": passwort, "mail": versendet}
