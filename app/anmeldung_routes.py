"""Die öffentlichen Anmelderouten — der dritte Bereich der App.

Kein Login, keine Werkstatt-Fähigkeiten, genau drei Wege: Kursliste,
Kursseite, Anmeldung. Alles, was hier hereinkommt, kommt von Fremden.

Die Bremse ist bewusst ein Wörterbuch im Prozess: kein Redis, keine
Abhängigkeit, ein Neustart setzt sie zurück. Bei diesem Volumen ist das
richtig. Sie ist eine Höflichkeitsbremse gegen Formular-Missbrauch, keine
Sicherheitsgrenze — wer die App direkt erreicht, kann `CF-Connecting-IP`
selbst setzen. Genau deshalb steht die App hinter dem Tunnel (Task 10).
"""

import logging
import time

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from . import anmeldung, anmeldung_seiten as seiten, kurse, mail

router = APIRouter(prefix="/anmeldung")
log = logging.getLogger(__name__)

RATE_FENSTER = 3600      # Sekunden
RATE_MAX = 5             # Anmeldungen je Absender und Fenster
RATE_EINTRAEGE_MAX = 5000  # danach wird beim Zugriff aufgeräumt
PROXY_KOPF = "cf-connecting-ip"

_ZUGRIFFE: dict[str, list[float]] = {}


def _absender(request: Request) -> str:
    """Wer fragt. Hinter dem Tunnel steht die echte Adresse im Cloudflare-Kopf."""
    kopf = request.headers.get(PROXY_KOPF, "").strip()
    if kopf:
        return kopf.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unbekannt"


def _bremse(request: Request) -> None:
    """Wirft 429, wenn ein Absender das Fenster ausgeschöpft hat."""
    jetzt = time.monotonic()
    wer = _absender(request)
    fenster = [t for t in _ZUGRIFFE.get(wer, []) if jetzt - t < RATE_FENSTER]
    if len(fenster) >= RATE_MAX:
        _ZUGRIFFE[wer] = fenster
        raise HTTPException(
            429, "Zu viele Anmeldungen von hier. Bitte später noch einmal "
                 "versuchen oder eine Mail schreiben.")
    fenster.append(jetzt)
    _ZUGRIFFE[wer] = fenster

    # Sonst wächst das Wörterbuch mit jeder gesehenen Adresse weiter.
    if len(_ZUGRIFFE) > RATE_EINTRAEGE_MAX:
        for k, v in list(_ZUGRIFFE.items()):
            if not v or jetzt - v[-1] >= RATE_FENSTER:
                _ZUGRIFFE.pop(k, None)


def _kurs_oder_404(slug: str) -> dict:
    k = kurse.kurs_nach_slug(slug)
    if k is None or not k["aktiv"]:
        # Dieselbe Antwort für „gibt es nicht" und „nicht ausgeschrieben".
        raise HTTPException(404, "Diesen Kurs gibt es nicht.")
    return k


@router.get("", response_class=HTMLResponse)
def seite_kursliste():
    return seiten.kursliste(kurse.liste(nur_aktive=True))


@router.get("/{slug}", response_class=HTMLResponse)
def seite_kurs(slug: str):
    k = _kurs_oder_404(slug)
    return seiten.kursseite(k, kurse.naechste_offene(k["id"]))


@router.post("/{slug}", response_class=HTMLResponse)
def anmelden(request: Request, slug: str,
             name: str = Form(""), email: str = Form(""),
             firma: str = Form(""), nachricht: str = Form(""),
             termin_id: str = Form("")):
    k = _kurs_oder_404(slug)
    _bremse(request)
    werte = {"name": name, "email": email, "firma": firma, "nachricht": nachricht}

    tid: int | None = None
    if termin_id.strip():
        try:
            tid = int(termin_id)
        except ValueError:
            return _mit_fehler(k, "Bitte einen Termin aus der Liste wählen.", werte)

    try:
        neu = anmeldung.annehmen(k["id"], tid, name, email, firma, nachricht)
    except anmeldung.AnmeldungFehler as e:
        return _mit_fehler(k, str(e), werte)

    _bestaetigen(neu, k, tid)
    return seiten.danke_seite(k)


def _mit_fehler(kurs: dict, meldung: str, werte: dict) -> HTMLResponse:
    """Das Formular noch einmal, mit Meldung und den eingegebenen Werten."""
    return HTMLResponse(
        seiten.kursseite(kurs, kurse.naechste_offene(kurs["id"]),
                         fehler=meldung, werte=werte),
        status_code=400)


def _bestaetigen(anmeldung_id: int, kurs: dict, termin_id: int | None) -> None:
    """Bestätigungsmail. Ein Fehler hier darf die Anmeldung nicht kippen.

    Erst speichern, dann senden. Eine Anmeldung, die verlorengeht, weil das
    Postfach klemmte, ist ein verlorener Kunde; eine Bestätigung, die nicht
    ankam, ist ein Anruf.
    """
    if not mail.konfiguriert():
        log.warning("Kein SMTP eingerichtet — Anmeldung %s unbestätigt",
                    anmeldung_id)
        return
    try:
        eintrag = anmeldung.eintrag(anmeldung_id)
        termin = kurse.termin(termin_id) if termin_id else None
        betreff, text = mail.anmeldung_eingegangen(eintrag, kurs, termin)
        mail.senden(eintrag["email"], betreff, text)
    except Exception:  # auch ein Vorlagenfehler darf die Anmeldung nicht kippen
        log.exception("Bestätigung zu Anmeldung %s nicht verschickt", anmeldung_id)
