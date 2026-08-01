"""Projektverwaltung — ein Ordner projects/<slug>/ pro Schulung.

Struktur pro Projekt:
    brief.json      Briefing-Felder aus dem Formular
    status.json     phase, sessions (Session-IDs je Phase für Resume),
                    erstellt_am, geaendert_am, ggf. letzter_fehler,
                    ggf. medium_overrides (Medien-Änderungen aus dem Gate)
    design.md       optional, hochgeladen
    material/       optional, hochgeladene Quelldateien
    curriculum.md   Artefakt des Agenten (Teil 1)
    kosten.json     Kostenplan des Agenten (Freigabe-Gate)
    events.jsonl    Fortschritts-Events der Läufe (für SSE-Replay)
"""

import json
import re
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"

_lock = threading.Lock()

# Phasen der App-State-Machine (bis Freigabe-Gate; Produktion folgt später)
PHASE_BRIEFING = "briefing"
PHASE_CURRICULUM_LAEUFT = "curriculum_laeuft"
PHASE_CURRICULUM_FERTIG = "curriculum_fertig"
PHASE_KOSTENPLAN_LAEUFT = "kostenplan_laeuft"
PHASE_FREIGABE_LAEUFT = "freigabe_laeuft"
PHASE_FREIGEGEBEN = "freigegeben"
PHASE_FEHLER = "fehler"

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(thema: str) -> str:
    """Macht aus dem Thema einen URL-/ordnertauglichen Slug."""
    s = thema.strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "projekt"


def _gueltig(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug))


def projekt_dir(slug: str) -> Path | None:
    """Pfad zum Projektordner, None wenn ungültig oder nicht vorhanden."""
    if not _gueltig(slug):
        return None
    d = PROJECTS / slug
    return d if d.is_dir() else None


def _freier_slug(base: str) -> str:
    slug, n = base, 2
    while (PROJECTS / slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def create(briefing: dict, design_md: bytes | None = None,
           material: list[tuple[str, bytes]] | None = None) -> str:
    """Legt ein neues Projekt an und gibt den Slug zurück."""
    PROJECTS.mkdir(exist_ok=True)
    with _lock:
        slug = _freier_slug(slugify(briefing["thema"]))
    d = PROJECTS / slug
    d.mkdir(parents=True)
    (d / "brief.json").write_text(
        json.dumps(briefing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if design_md:
        (d / "design.md").write_bytes(design_md)
    material = [(Path(name).name, data) for name, data in (material or [])]
    material = [(name, data) for name, data in material if name]
    if material:
        (d / "material").mkdir()
        for name, data in material:
            (d / "material" / name).write_bytes(data)
    jetzt = _jetzt()
    save_status(slug, {
        "phase": PHASE_BRIEFING,
        "sessions": {},
        "erstellt_am": jetzt,
        "geaendert_am": jetzt,
    })
    return slug


def load_status(slug: str) -> dict | None:
    d = projekt_dir(slug)
    if not d:
        return None
    f = d / "status.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_status(slug: str, status: dict) -> None:
    d = projekt_dir(slug)
    if not d:
        return
    status["geaendert_am"] = _jetzt()
    with _lock:
        (d / "status.json").write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def set_phase(slug: str, phase: str, fehler: str | None = None) -> None:
    status = load_status(slug)
    if status is None:
        return
    status["phase"] = phase
    if fehler:
        status["letzter_fehler"] = fehler
    elif phase != PHASE_FEHLER:
        status.pop("letzter_fehler", None)
    save_status(slug, status)


def set_medium_overrides(slug: str, overrides: dict) -> None:
    """Hält die Medien-Änderungen aus dem Freigabe-Gate im Status fest."""
    status = load_status(slug)
    if status is None:
        return
    status["medium_overrides"] = overrides
    save_status(slug, status)


def set_session(slug: str, phase_key: str, session_id: str) -> None:
    """Merkt sich die Agenten-Session-ID einer Phase (für Resume)."""
    status = load_status(slug)
    if status is None:
        return
    status.setdefault("sessions", {})[phase_key] = session_id
    save_status(slug, status)


def touch(slug: str) -> None:
    """Aktualisiert nur geaendert_am (z. B. nach manuellem Edit)."""
    status = load_status(slug)
    if status is not None:
        save_status(slug, status)


def liste() -> list[dict]:
    """Alle Projekte, neueste zuerst."""
    if not PROJECTS.is_dir():
        return []
    out = []
    for d in PROJECTS.iterdir():
        if not d.is_dir() or not _gueltig(d.name):
            continue
        status = load_status(d.name)
        if status is None:
            continue
        thema = ""
        brief = d / "brief.json"
        if brief.exists():
            try:
                thema = json.loads(brief.read_text(encoding="utf-8")).get("thema", "")
            except (json.JSONDecodeError, OSError):
                pass
        out.append({
            "slug": d.name,
            "thema": thema,
            "phase": status.get("phase", PHASE_BRIEFING),
            "geaendert_am": status.get("geaendert_am", ""),
        })
    out.sort(key=lambda p: p["geaendert_am"], reverse=True)
    return out


def get(slug: str) -> dict | None:
    """Detaildatensatz für die API."""
    d = projekt_dir(slug)
    if not d:
        return None
    status = load_status(slug) or {}
    briefing = {}
    brief = d / "brief.json"
    if brief.exists():
        try:
            briefing = json.loads(brief.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    mat = d / "material"
    return {
        "slug": slug,
        "briefing": briefing,
        "status": status,
        "hat_design": (d / "design.md").is_file(),
        "hat_curriculum": (d / "curriculum.md").is_file(),
        "material": sorted(p.name for p in mat.iterdir() if p.is_file())
                    if mat.is_dir() else [],
    }


def material_dateien(slug: str) -> list[Path]:
    d = projekt_dir(slug)
    if not d:
        return []
    mat = d / "material"
    return sorted(p for p in mat.iterdir() if p.is_file()) if mat.is_dir() else []


def events_datei(slug: str) -> Path | None:
    d = projekt_dir(slug)
    return (d / "events.jsonl") if d else None
