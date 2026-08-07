"""SmartCon-Schulungen — FastAPI-Hauptmodul.

Start: .venv/bin/python -m app.main  →  http://localhost:8710
"""

import asyncio
import json
import queue
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config, curriculum, higgsfield, praesentation, preflight, projekte, prompts, pruefung, runner

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="SmartCon-Schulungen", version="0.2.0")


@app.get("/api/preflight")
def api_preflight():
    """Preflight-Ampel: alle Abhängigkeiten prüfen (live, dauert wenige Sekunden)."""
    return {"checks": preflight.run_all(config.load())}


@app.get("/api/config")
def api_config_get():
    return config.load()


@app.post("/api/config")
async def api_config_post(cfg: dict):
    return config.save(cfg)


@app.post("/api/config/logo")
async def api_config_logo(logo: UploadFile = File(...)):
    """Haus-Logo hinterlegen (PNG). Ersetzt ein vorhandenes."""
    daten = await logo.read()
    if not daten:
        raise HTTPException(400, "Leere Datei")
    try:
        config.logo_speichern(daten)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "groesse": len(daten)}


@app.delete("/api/config/logo")
def api_config_logo_loeschen():
    config.logo_loeschen()
    return {"ok": True}


# --- Projekte -------------------------------------------------------------

@app.get("/api/projekte")
def api_projekte():
    return {"projekte": projekte.liste()}


@app.get("/api/presets")
def api_presets():
    """Preset-Karten für das Formular (aus skill/schulung/reference/styles/)."""
    return {"presets": prompts.presets()}


def _projekt_oder_404(slug: str) -> dict:
    p = projekte.get(slug)
    if p is None:
        raise HTTPException(404, f"Projekt „{slug}“ nicht gefunden")
    return p


def _default_design_md() -> bytes | None:
    """Die in den Einstellungen hinterlegte design.md, falls eine gesetzt ist.

    Der Pfad wird dort aufgelöst, wo die App läuft — im Docker-Betrieb also im
    Container. Nur Gemountetes ist dort sichtbar (config.json, projects/, die
    Home-Verzeichnisse), das Repo-Verzeichnis selbst nicht.
    """
    pfad = config.load().get("default_design_md", "").strip()
    if not pfad:
        return None
    try:
        return Path(pfad).expanduser().read_bytes()
    except OSError as e:
        raise HTTPException(
            400,
            f"Default-design.md nicht lesbar: {pfad} ({e.strerror}). "
            "Im Docker-Betrieb muss der Pfad aus Sicht des Containers gelten "
            "(z. B. /app/projects/… oder /root/…) — oder die Datei beim "
            "Anlegen direkt hochladen.")


@app.post("/api/projekte", status_code=201)
async def api_projekt_neu(
    thema: str = Form(...),
    lernziele: str = Form(...),
    zielgruppe: str = Form(...),
    vorwissen: str = Form(""),
    sprache: str = Form(...),
    dauer: str = Form(...),
    stil: str = Form(...),
    ki_medien: str = Form("ja"),
    material_hinweise: str = Form(""),
    design_md: UploadFile | None = File(None),
    material: list[UploadFile] = File([]),
):
    if not thema.strip() or not lernziele.strip():
        raise HTTPException(400, "Thema und Lernziele sind Pflichtfelder")
    if stil != "design" and stil not in prompts.PRESET_NAMEN:
        raise HTTPException(400, f"Unbekannter Stil „{stil}“")
    design_bytes = None
    if design_md is not None and design_md.filename:
        design_bytes = await design_md.read()
    if not design_bytes:
        design_bytes = _default_design_md()
    if stil == "design" and not design_bytes:
        raise HTTPException(400, "Stil „eigene design.md“ gewählt, aber keine Datei hochgeladen")
    briefing = {
        "thema": thema.strip(),
        "lernziele": lernziele.strip(),
        "zielgruppe": zielgruppe.strip(),
        "vorwissen": vorwissen.strip(),
        "sprache": sprache.strip(),
        "dauer": dauer.strip(),
        "stil": stil,
        # Schalter „Higgsfield nutzen Ja/Nein" — Preset kostenlos erzwingt Nein
        "ki_medien": False if stil == "kostenlos"
                     else ki_medien.lower() in ("ja", "true", "1", "on"),
        "material_hinweise": material_hinweise.strip(),
    }
    dateien = [(f.filename, await f.read()) for f in material if f.filename]
    slug = projekte.create(briefing, design_md=design_bytes, material=dateien)
    return {"slug": slug}


@app.get("/api/projekte/{slug}")
def api_projekt(slug: str):
    return _projekt_oder_404(slug)


@app.delete("/api/projekte/{slug}")
def api_projekt_loeschen(slug: str):
    """Entfernt die Schulung samt Ordner — Medien, HTML und Verlauf inklusive."""
    _projekt_oder_404(slug)
    if runner.laeuft(slug):
        raise HTTPException(409, "Agent läuft — erst abwarten, dann löschen")
    projekte.loeschen(slug)
    return {"ok": True}


@app.post("/api/projekte/{slug}/curriculum/starten")
def api_curriculum_starten(slug: str):
    p = _projekt_oder_404(slug)
    if runner.laeuft(slug):
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    projekt_dir = projekte.projekt_dir(slug)
    prompt = prompts.curriculum_prompt(
        projekt_dir, p["briefing"],
        [f.name for f in projekte.material_dateien(slug)])
    projekte.set_phase(slug, projekte.PHASE_CURRICULUM_LAEUFT)
    try:
        runner.start(slug, "curriculum", prompt)
    except runner.LaufAktiv:
        projekte.set_phase(slug, p["status"].get("phase", projekte.PHASE_BRIEFING))
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "phase": projekte.PHASE_CURRICULUM_LAEUFT}


@app.get("/api/projekte/{slug}/events")
async def api_events(slug: str):
    """SSE-Stream: spielt events.jsonl nach und hängt dann live an."""
    _projekt_oder_404(slug)

    async def stream():
        q = runner.abonnieren(slug)
        try:
            nr = 0
            f = projekte.events_datei(slug)
            if f and f.exists():
                for zeile in f.read_text(encoding="utf-8").splitlines():
                    if not zeile.strip():
                        continue
                    try:
                        nr = max(nr, json.loads(zeile).get("nr", 0))
                    except json.JSONDecodeError:
                        continue
                    yield f"data: {zeile}\n\n"
            if not runner.laeuft(slug):
                return  # kein aktiver Lauf — nach dem Replay schließen
            while True:
                try:
                    ev = await asyncio.to_thread(q.get, True, 15)
                except queue.Empty:
                    yield ": keepalive\n\n"
                    if not runner.laeuft(slug):
                        return
                    continue
                if ev.get("nr", 0) <= nr:
                    continue  # schon im Replay enthalten
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if ev.get("typ") in ("fertig", "fehler"):
                    return
        finally:
            runner.abmelden(slug, q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/api/projekte/{slug}/curriculum", response_class=PlainTextResponse)
def api_curriculum_lesen(slug: str):
    _projekt_oder_404(slug)
    f = projekte.projekt_dir(slug) / "curriculum.md"
    if not f.is_file():
        raise HTTPException(404, "Noch kein curriculum.md vorhanden")
    return f.read_text(encoding="utf-8")


@app.put("/api/projekte/{slug}/curriculum")
async def api_curriculum_schreiben(slug: str, body: dict):
    _projekt_oder_404(slug)
    text = body.get("text")
    if not isinstance(text, str):
        raise HTTPException(400, "Feld „text“ fehlt")
    (projekte.projekt_dir(slug) / "curriculum.md").write_text(text, encoding="utf-8")
    projekte.touch(slug)
    return {"ok": True}


@app.post("/api/projekte/{slug}/curriculum/kommentar")
async def api_curriculum_kommentar(slug: str, body: dict):
    """Änderungswunsch an den Agenten — setzt die gespeicherte Session fort."""
    p = _projekt_oder_404(slug)
    kommentar = (body.get("kommentar") or "").strip()
    if not kommentar:
        raise HTTPException(400, "Kommentar darf nicht leer sein")
    if runner.laeuft(slug):
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    session_id = p["status"].get("sessions", {}).get("curriculum")
    # Sessions sind an das Arbeitsverzeichnis gebunden (Host- ≠ Container-Pfad):
    # nur resumen, wenn die Session-Datei hier tatsächlich existiert.
    if session_id and not runner.session_verfuegbar(
            session_id, projekte.projekt_dir(slug)):
        session_id = None
    prompt = prompts.kommentar_prompt(
        kommentar, projekte.projekt_dir(slug), hat_session=bool(session_id))
    projekte.set_phase(slug, projekte.PHASE_CURRICULUM_LAEUFT)
    try:
        runner.start(slug, "curriculum", prompt, session_id=session_id)
    except runner.LaufAktiv:
        projekte.set_phase(slug, p["status"].get("phase", projekte.PHASE_BRIEFING))
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "resume": bool(session_id)}


# --- Freigabe-Gate ---------------------------------------------------------

@app.get("/api/projekte/{slug}/gate")
def api_gate(slug: str):
    """Daten fürs Freigabe-Gate: Level-Tabelle, Kostenplan, Higgsfield-Guthaben."""
    _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    level = []
    cur = d / "curriculum.md"
    if cur.is_file():
        level = curriculum.parse_level(cur.read_text(encoding="utf-8"))
    kosten = None
    kf = d / "kosten.json"
    if kf.is_file():
        try:
            kosten = json.loads(kf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            kosten = None
    return {"level": level, "kosten": kosten, "guthaben": higgsfield.guthaben()}


@app.post("/api/projekte/{slug}/gate/kostenplan")
def api_kostenplan_starten(slug: str):
    """Startet die Runner-Phase „kostenplan" (Hintergrund) → kosten.json."""
    p = _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    if not (d / "curriculum.md").is_file():
        raise HTTPException(404, "Noch kein curriculum.md vorhanden")
    if runner.laeuft(slug):
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    vorher = p["status"].get("phase", projekte.PHASE_CURRICULUM_FERTIG)
    projekte.set_phase(slug, projekte.PHASE_KOSTENPLAN_LAEUFT)
    try:
        runner.start(slug, "kostenplan", prompts.kostenplan_prompt(d),
                     zurueck_phase=vorher)
    except runner.LaufAktiv:
        projekte.set_phase(slug, vorher)
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "phase": projekte.PHASE_KOSTENPLAN_LAEUFT}


@app.post("/api/projekte/{slug}/pruefung")
def api_pruefung_starten(slug: str, body: dict | None = None):
    """Startet die Prüfungs-Phase → pruefung.json aus der Stoffquelle."""
    p = _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    if not (d / "curriculum.md").is_file():
        raise HTTPException(404, "Noch kein curriculum.md vorhanden")
    if runner.laeuft(slug):
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")

    grenze = (body or {}).get("bestehensgrenze", 70)
    if not isinstance(grenze, int) or isinstance(grenze, bool) \
            or not 1 <= grenze <= 100:
        raise HTTPException(400, "bestehensgrenze muss zwischen 1 und 100 liegen")

    vorher = p["status"].get("phase", projekte.PHASE_FERTIG)
    projekte.set_phase(slug, projekte.PHASE_PRUEFUNG_LAEUFT)
    try:
        runner.start(slug, "pruefung", prompts.pruefung_prompt(d, grenze),
                     zurueck_phase=vorher)
    except runner.LaufAktiv:
        projekte.set_phase(slug, vorher)
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "phase": projekte.PHASE_PRUEFUNG_LAEUFT}


@app.get("/api/projekte/{slug}/pruefung")
def api_pruefung_lesen(slug: str):
    """Die geprüfte pruefung.json. 400 nennt den Grund im Klartext."""
    _projekt_oder_404(slug)
    pfad = projekte.projekt_dir(slug) / "pruefung.json"
    if not pfad.is_file():
        raise HTTPException(404, "Noch keine Prüfung erzeugt")
    try:
        return pruefung.laden(pfad)
    except pruefung.PruefungFehler as e:
        raise HTTPException(400, str(e))


@app.get("/api/projekte/{slug}/pruefung.html")
def api_pruefung_html(slug: str):
    """Die Prüfung als offline lauffähige HTML-Datei."""
    _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    pfad = d / "pruefung.json"
    if not pfad.is_file():
        raise HTTPException(404, "Noch keine Prüfung erzeugt")
    try:
        daten = pruefung.laden(pfad)
    except pruefung.PruefungFehler as e:
        raise HTTPException(400, str(e))

    ziel = d / "pruefung.html"
    ziel.write_text(pruefung.als_html(daten), encoding="utf-8")
    return FileResponse(ziel, filename=ziel.name, media_type="text/html")


@app.post("/api/projekte/{slug}/go")
async def api_go(slug: str, body: dict | None = None):
    """Freigabe-Gate: optionale Medien-Änderungen einarbeiten, dann freigeben.

    Ohne overrides: Phase direkt auf „freigegeben".
    Mit overrides: Agent (Resume der Curriculum-Session) arbeitet die Änderungen
    zuerst ins curriculum.md ein; bei Erfolg setzt der Runner „freigegeben".
    """
    p = _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    if not (d / "curriculum.md").is_file():
        raise HTTPException(404, "Noch kein curriculum.md vorhanden")
    if runner.laeuft(slug):
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    overrides = (body or {}).get("medium_overrides") or {}
    if not isinstance(overrides, dict):
        raise HTTPException(400, "medium_overrides muss ein Objekt sein")
    overrides = {str(k).strip(): str(v).strip().upper()
                 for k, v in overrides.items() if str(v).strip()}
    projekte.set_medium_overrides(slug, overrides)
    if not overrides:
        projekte.set_phase(slug, projekte.PHASE_FREIGEGEBEN)
        return {"ok": True, "phase": projekte.PHASE_FREIGEGEBEN, "resume": False}
    # „von→zu"-Zeilen für den Prompt bauen (Original-Medium aus dem Parser)
    bekannt = {e["level"]: e["medium"] for e in curriculum.parse_level(
        (d / "curriculum.md").read_text(encoding="utf-8"))}

    def _sortierschluessel(kv):
        return (0, int(kv[0])) if kv[0].isdigit() else (1, 0)

    aenderungen = [
        f"Level {lvl}: {curriculum.normalisiere_medium(bekannt.get(lvl, '?'))}"
        f"→{neu}"
        for lvl, neu in sorted(overrides.items(), key=_sortierschluessel)]
    session_id = p["status"].get("sessions", {}).get("curriculum")
    # Session nur nutzen, wenn claude sie unter diesem Arbeitsverzeichnis
    # wirklich kennt — sonst frischer Lauf mit Lese-Anweisung im Prompt
    if session_id and not runner.session_verfuegbar(session_id, d):
        session_id = None
    prompt = prompts.freigabe_prompt(aenderungen, d, hat_session=bool(session_id))
    vorher = p["status"].get("phase", projekte.PHASE_CURRICULUM_FERTIG)
    projekte.set_phase(slug, projekte.PHASE_FREIGABE_LAEUFT)
    try:
        runner.start(slug, "freigabe", prompt, session_id=session_id)
    except runner.LaufAktiv:
        projekte.set_phase(slug, vorher)
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "phase": projekte.PHASE_FREIGABE_LAEUFT,
            "resume": bool(session_id)}


# --- Produktion --------------------------------------------------------------

@app.post("/api/projekte/{slug}/produktion/starten")
def api_produktion_starten(slug: str):
    """Startet die Produktion (Teil 2 des Skills) — nur aus Phase „freigegeben"."""
    p = _projekt_oder_404(slug)
    phase = p["status"].get("phase", projekte.PHASE_BRIEFING)
    if phase != projekte.PHASE_FREIGEGEBEN:
        raise HTTPException(
            409, f"Produktion nur aus der Phase „freigegeben“ möglich "
                 f"(aktuell: „{phase}“)")
    if runner.laeuft(slug):
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    d = projekte.projekt_dir(slug)
    if not (d / "curriculum.md").is_file():
        raise HTTPException(404, "Kein curriculum.md vorhanden")
    cfg = config.load()
    env = prompts.whisper_remote_env(cfg)
    guthaben_start = higgsfield.guthaben()
    projekte.set_guthaben_start(slug, guthaben_start)
    projekte.set_phase(slug, projekte.PHASE_PRODUKTION_LAEUFT)
    try:
        runner.start(slug, "produktion",
                     prompts.produktion_prompt(d, whisper_remote=bool(env)),
                     env=env)
    except runner.LaufAktiv:
        projekte.set_phase(slug, projekte.PHASE_FREIGEGEBEN)
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "phase": projekte.PHASE_PRODUKTION_LAEUFT,
            "guthaben_start": guthaben_start,
            "whisper_remote": bool(env)}


@app.get("/api/projekte/{slug}/produktion/status")
def api_produktion_status(slug: str):
    """Verbrauchs-Zähler: Guthaben beim Start, jetzt (60-s-Cache) und Differenz."""
    p = _projekt_oder_404(slug)
    start_wert = p["status"].get("guthaben_start")
    jetzt = higgsfield.guthaben()
    verbraucht = None
    if (isinstance(start_wert, (int, float))
            and isinstance(jetzt, (int, float))):
        verbraucht = round(start_wert - jetzt, 1)
    return {"phase": p["status"].get("phase"),
            "guthaben_start": start_wert,
            "guthaben_jetzt": jetzt,
            "verbraucht": verbraucht}


# --- Ergebnis (Fertig-Ansicht) ------------------------------------------------

_DATEINAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _html_datei_oder_404(slug: str, dateiname: str) -> Path:
    """Validiert den Dateinamen und liefert die HTML-Datei im Projektordner."""
    _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    if not _DATEINAME_RE.match(dateiname) or not dateiname.endswith(".html"):
        raise HTTPException(400, "Ungültiger Dateiname")
    f = d / dateiname
    if not f.is_file() or f.resolve().parent != d.resolve():
        raise HTTPException(404, f"Datei „{dateiname}“ nicht gefunden")
    return f


@app.get("/api/projekte/{slug}/ergebnis")
def api_ergebnis_liste(slug: str):
    """Liste der fertigen HTML-Dateien im Projektordner (neueste zuerst)."""
    _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    dateien = [
        {"name": f.name, "groesse": f.stat().st_size,
         "mtime": f.stat().st_mtime}
        for f in d.glob("*.html") if f.is_file()
    ]
    dateien.sort(key=lambda e: e["mtime"], reverse=True)
    return {"dateien": dateien}


@app.get("/api/projekte/{slug}/ergebnis/{dateiname}")
def api_ergebnis_download(slug: str, dateiname: str):
    """Download der fertigen HTML-Datei (Content-Disposition: attachment)."""
    f = _html_datei_oder_404(slug, dateiname)
    return FileResponse(f, filename=f.name)


@app.get("/api/projekte/{slug}/vorschau/{dateiname}")
def api_ergebnis_vorschau(slug: str, dateiname: str):
    """Dieselbe Datei als text/html — zum Ansehen im Browser (neuer Tab)."""
    f = _html_datei_oder_404(slug, dateiname)
    return FileResponse(f, media_type="text/html")


# --- Deck-Werkstatt (Präsentationen) ---------------------------------------

PRAESENTATION_QUELLEN_MAX = 20000


@app.post("/api/praesentationen", status_code=201)
async def api_praesentation_neu(
    thema: str = Form(...),
    zielgruppe: str = Form(""),
    lernziele: str = Form(""),
    vorwissen: str = Form(""),
    sprache: str = Form("Deutsch"),
    dauer: str = Form(""),
    quellen: str = Form(""),
    material: list[UploadFile] = File([]),
):
    """Legt ein Präsentationsprojekt an und startet den Lauf.

    `quellen` ist Freitext, eine Fundstelle je Zeile. Dateien kommen über
    `material` und gehen der Websuche vor.
    """
    if not thema.strip():
        raise HTTPException(400, "Thema ist ein Pflichtfeld")
    if len(quellen) > PRAESENTATION_QUELLEN_MAX:
        raise HTTPException(400, "Die Quellenliste ist zu lang")
    if config.standard_logo() is None:
        # Lieber hier abweisen als einen Lauf starten, der am Logo scheitert.
        raise HTTPException(
            400, "Kein Haus-Logo hinterlegt — in den Einstellungen hochladen. "
                 "Der Präsentations-Skill bricht ohne Logo ab.")

    dateien = [(f.filename, await f.read()) for f in material if f.filename]
    briefing = {
        "art": projekte.ART_PRAESENTATION,
        "thema": thema.strip(),
        "zielgruppe": zielgruppe.strip(),
        "lernziele": lernziele.strip(),
        "vorwissen": vorwissen.strip(),
        "sprache": sprache.strip() or "Deutsch",
        "dauer": dauer.strip(),
        "quellen": quellen.strip(),
    }
    slug = projekte.create(briefing, material=dateien)
    d = projekte.projekt_dir(slug)

    projekte.set_phase(slug, projekte.PHASE_PRAESENTATION_LAEUFT)
    try:
        runner.start(slug, "praesentation",
                     praesentation.prompt(d, briefing, config.LOGO_PFAD))
    except runner.LaufAktiv:
        projekte.set_phase(slug, projekte.PHASE_FEHLER)
        raise HTTPException(409, "Für dieses Projekt läuft bereits ein Agent")
    return {"ok": True, "slug": slug,
            "phase": projekte.PHASE_PRAESENTATION_LAEUFT}


@app.get("/api/praesentationen/{slug}")
def api_praesentation_stand(slug: str):
    p = _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    dateien = [{"name": f.name, "groesse": f.stat().st_size}
               for f in praesentation.dateien(d)]
    return {"slug": slug,
            "phase": p["status"].get("phase"),
            "laeuft": runner.laeuft(slug),
            "thema": p["briefing"].get("thema"),
            "dateien": dateien,
            "fertig": bool(dateien) and not runner.laeuft(slug)}


@app.get("/api/praesentationen/{slug}/datei/{dateiname}")
def api_praesentation_download(slug: str, dateiname: str):
    """Download der erzeugten PowerPoint-Datei.

    Eigene Route statt einer Erweiterung von /ergebnis: Dort ist die
    Beschränkung auf .html Teil der Prüfung, und eine Route, die je nach
    Endung anderes zulässt, lädt zum nächsten Schlupfloch ein.
    """
    _projekt_oder_404(slug)
    d = projekte.projekt_dir(slug)
    if not _DATEINAME_RE.match(dateiname) or not dateiname.endswith(".pptx"):
        raise HTTPException(400, "Ungültiger Dateiname")
    f = d / dateiname
    if not f.is_file() or f.resolve().parent != d.resolve():
        raise HTTPException(404, f"Datei „{dateiname}“ nicht gefunden")
    return FileResponse(
        f, filename=f.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/")
def index():
    # Nicht cachen: sonst hält ein Handy-Browser die alte index.html fest und
    # holt damit auch die alten ?v=-Verweise auf CSS/JS — Änderungen am
    # Frontend blieben unsichtbar. Die Assets selbst dürfen gecacht werden.
    return FileResponse(STATIC / "index.html",
                        headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=STATIC), name="static")


def main():
    import uvicorn

    cfg = config.load()
    host = "0.0.0.0" if cfg.get("lan_erreichbar") else "127.0.0.1"
    uvicorn.run(app, host=host, port=cfg["port"])


if __name__ == "__main__":
    main()
