"""SmartCon-Schulungen — FastAPI-Hauptmodul.

Start: .venv/bin/python -m app.main  →  http://localhost:8710
"""

import asyncio
import json
import queue
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config, curriculum, higgsfield, preflight, projekte, prompts, runner

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


@app.post("/api/projekte", status_code=201)
async def api_projekt_neu(
    thema: str = Form(...),
    lernziele: str = Form(...),
    zielgruppe: str = Form(...),
    vorwissen: str = Form(""),
    sprache: str = Form(...),
    dauer: str = Form(...),
    stil: str = Form(...),
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
        "material_hinweise": material_hinweise.strip(),
    }
    dateien = [(f.filename, await f.read()) for f in material if f.filename]
    slug = projekte.create(briefing, design_md=design_bytes, material=dateien)
    return {"slug": slug}


@app.get("/api/projekte/{slug}")
def api_projekt(slug: str):
    return _projekt_oder_404(slug)


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


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


def main():
    import uvicorn

    cfg = config.load()
    host = "0.0.0.0" if cfg.get("lan_erreichbar") else "127.0.0.1"
    uvicorn.run(app, host=host, port=cfg["port"])


if __name__ == "__main__":
    main()
