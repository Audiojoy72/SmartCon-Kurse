"""AgentRunner — führt claude/kimi headless pro Phase aus und streamt Fortschritt.

Pro Projekt (slug) läuft höchstens ein Agent. Die geparsten Fortschritts-Events
landen sowohl in events.jsonl im Projektordner (Replay bei SSE-Reconnect) als
auch in den Queues der gerade verbundenen SSE-Abonnenten.

Event-Typen:
    status  Phase gestartet / Zwischenmeldung        {text}
    tool    Tool-Aufruf des Agenten                  {tool, eingabe}
    text    Assistant-Text                           {text}
    fertig  Lauf erfolgreich beendet                 {text, dauer}
    fehler  Lauf fehlgeschlagen / abgebrochen        {text}
"""

import json
import queue
import subprocess
import threading
import time
from pathlib import Path

from . import config, projekte

# Tools, die der Agent ohne Rückfrage benutzen darf (Schreiben nur im Projektordner,
# weil cwd = Projektordner und permission-mode acceptEdits)
ALLOWED_TOOLS = "Bash,Edit,Write,Read,Glob,Grep,WebSearch,WebFetch"

# Nach erfolgreichem Lauf: Phase der App-State-Machine je Lauf-Typ.
# „kostenplan" ist nicht dabei — er kehrt zur Phase vor dem Lauf zurück
# (siehe _phase_nach_erfolg), damit ein bereits freigegebenes Projekt
# nicht auf „curriculum_fertig" zurückfällt.
PHASE_NACH_ERFOLG = {
    "curriculum": projekte.PHASE_CURRICULUM_FERTIG,
    "freigabe": projekte.PHASE_FREIGEGEBEN,
}

_laeufe: dict[str, dict] = {}          # slug -> {phase, gestartet}
_laeufe_lock = threading.Lock()
_abonnenten: dict[str, list[queue.Queue]] = {}
_abo_lock = threading.Lock()
_zaehler: dict[str, int] = {}          # slug -> letzte vergebene Event-Nr
_zaehler_lock = threading.Lock()


class LaufAktiv(Exception):
    """Es läuft bereits ein Agent für dieses Projekt."""


def laeuft(slug: str) -> bool:
    with _laeufe_lock:
        return slug in _laeufe


def session_verfuegbar(session_id: str | None, cwd) -> bool:
    """Prüft, ob claude die Session unter diesem Arbeitsverzeichnis kennt.

    claude legt Sessions als ~/.claude/projects/<pfad-mit-strichen>/<id>.jsonl
    ab — ein Resume mit fremder/veralteter ID bricht sofort mit
    „No conversation found" ab, deshalb vorher prüfen.
    """
    if not session_id or cwd is None:
        return False
    pfad_slug = str(cwd).replace("/", "-")
    return (Path.home() / ".claude" / "projects" / pfad_slug
            / f"{session_id}.jsonl").is_file()


def abonnieren(slug: str) -> queue.Queue:
    q: queue.Queue = queue.Queue()
    with _abo_lock:
        _abonnenten.setdefault(slug, []).append(q)
    return q


def abmelden(slug: str, q: queue.Queue) -> None:
    with _abo_lock:
        if slug in _abonnenten and q in _abonnenten[slug]:
            _abonnenten[slug].remove(q)


def _naechste_nr(slug: str) -> int:
    """Fortlaufende Event-Nr pro Projekt (über events.jsonl hinweg eindeutig)."""
    with _zaehler_lock:
        if slug not in _zaehler:
            n = 0
            f = projekte.events_datei(slug)
            if f and f.exists():
                try:
                    with f.open(encoding="utf-8") as fh:
                        n = sum(1 for _ in fh)
                except OSError:
                    n = 0
            _zaehler[slug] = n
        _zaehler[slug] += 1
        return _zaehler[slug]


def _emit(slug: str, typ: str, **daten) -> dict:
    ev = {"nr": _naechste_nr(slug), "ts": time.time(), "typ": typ, **daten}
    f = projekte.events_datei(slug)
    if f:
        try:
            with f.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except OSError:
            pass
    with _abo_lock:
        for q in _abonnenten.get(slug, []):
            q.put(ev)
    return ev


def start(slug: str, phase: str, prompt: str, session_id: str | None = None,
          zurueck_phase: str | None = None) -> None:
    """Startet den Agenten-Lauf in einem Hintergrund-Thread.

    Wirft LaufAktiv, wenn für das Projekt schon ein Lauf aktiv ist.
    zurueck_phase: Phase, zu der der Lauf-Typ „kostenplan" nach Erfolg
    zurückkehrt (die Phase, die vor dem Start aktiv war).
    """
    with _laeufe_lock:
        if slug in _laeufe:
            raise LaufAktiv(slug)
        _laeufe[slug] = {"phase": phase, "gestartet": time.time(),
                         "zurueck": zurueck_phase}
    t = threading.Thread(
        target=_fuehre_aus, args=(slug, phase, prompt, session_id), daemon=True)
    t.start()


def _phase_nach_erfolg(slug: str, phase: str) -> str | None:
    """Phase, die nach einem erfolgreichen Lauf gesetzt wird (None = keine)."""
    if phase == "kostenplan":
        # Der Kostenplan ändert den Gate-Status nicht — zurück zur Vorher-Phase
        return (_laeufe.get(slug, {}).get("zurueck")
                or projekte.PHASE_CURRICULUM_FERTIG)
    return PHASE_NACH_ERFOLG.get(phase)


def _kommando(backend: str, prompt: str, session_id: str | None) -> list[str]:
    if backend == "kimi":
        # Fallback: kein stream-json, stdout wird als Text durchgereicht.
        cmd = ["kimi", "-p", prompt]
        if session_id:
            cmd += ["-r", session_id]
        return cmd
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--permission-mode", "acceptEdits",
        "--allowedTools", ALLOWED_TOOLS,
    ]
    if session_id:
        cmd += ["--resume", session_id]
    return cmd


def _kurz_eingabe(tool_input: dict) -> str:
    """Kurzer, lesbarer Auszug aus einem Tool-Input für das Fortschritts-Log."""
    if not isinstance(tool_input, dict):
        return str(tool_input)[:120]
    for schluessel in ("file_path", "command", "pattern", "path", "url", "prompt",
                       "query", "description"):
        wert = tool_input.get(schluessel)
        if isinstance(wert, str) and wert.strip():
            return wert.strip().splitlines()[0][:120]
    return json.dumps(tool_input, ensure_ascii=False)[:120]


def _parse_claude_zeile(slug: str, phase: str, zeile: str,
                        zustand: dict) -> None:
    try:
        ev = json.loads(zeile)
    except json.JSONDecodeError:
        return
    typ = ev.get("type")
    if typ == "system":
        sid = ev.get("session_id")
        if sid and not zustand["session_gespeichert"]:
            projekte.set_session(slug, phase, sid)
            zustand["session_gespeichert"] = True
    elif typ == "assistant":
        for block in ev.get("message", {}).get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text", "").strip():
                _emit(slug, "text", text=block["text"])
            elif block.get("type") == "tool_use":
                _emit(slug, "tool", tool=block.get("name", ""),
                      eingabe=_kurz_eingabe(block.get("input", {})))
    elif typ == "result":
        zustand["fertig_gesehen"] = True
        if ev.get("subtype") == "success":
            dauer = round(ev.get("duration_ms", 0) / 1000)
            neue_phase = _phase_nach_erfolg(slug, phase)
            if neue_phase:
                projekte.set_phase(slug, neue_phase)
            _emit(slug, "fertig", text=ev.get("result", ""), dauer=dauer)
        else:
            meldung = ev.get("result") or f"Agent abgebrochen ({ev.get('subtype')})"
            projekte.set_phase(slug, projekte.PHASE_FEHLER, fehler=meldung[:500])
            _emit(slug, "fehler", text=meldung)


def _fuehre_aus(slug: str, phase: str, prompt: str,
                session_id: str | None) -> None:
    backend = config.load().get("backend", "claude")
    cwd = projekte.projekt_dir(slug)
    zustand = {"session_gespeichert": False, "fertig_gesehen": False}
    _emit(slug, "status",
          text=f"Phase „{phase}“ gestartet (Backend: {backend}"
               + (", mit Session-Resume" if session_id else "") + ")")
    try:
        proc = subprocess.Popen(
            _kommando(backend, prompt, session_id),
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
    except FileNotFoundError:
        projekte.set_phase(slug, projekte.PHASE_FEHLER,
                           fehler=f"CLI „{backend}“ nicht gefunden")
        _emit(slug, "fehler",
              text=f"CLI „{backend}“ nicht gefunden — System-Check prüfen.")
        with _laeufe_lock:
            _laeufe.pop(slug, None)
        return
    try:
        assert proc.stdout is not None
        for zeile in proc.stdout:
            zeile = zeile.strip()
            if not zeile:
                continue
            if backend == "claude":
                _parse_claude_zeile(slug, phase, zeile, zustand)
            else:
                _emit(slug, "text", text=zeile)
        rc = proc.wait()
        if not zustand["fertig_gesehen"]:
            fehltext = ""
            if proc.stderr is not None:
                fehltext = proc.stderr.read().strip()
            if rc == 0:
                neue_phase = _phase_nach_erfolg(slug, phase)
                if neue_phase:
                    projekte.set_phase(slug, neue_phase)
                dauer = round(time.time() - _laeufe.get(slug, {}).get(
                    "gestartet", time.time()))
                _emit(slug, "fertig", text="", dauer=dauer)
            else:
                meldung = fehltext[-500:] or f"Agent mit Exit-Code {rc} beendet"
                projekte.set_phase(slug, projekte.PHASE_FEHLER,
                                   fehler=meldung[:500])
                _emit(slug, "fehler", text=meldung)
    except Exception as e:  # nie still verschlucken — der Nutzer sieht nur den Stream
        projekte.set_phase(slug, projekte.PHASE_FEHLER, fehler=str(e)[:500])
        _emit(slug, "fehler", text=f"Interner Fehler im Runner: {e}")
    finally:
        with _laeufe_lock:
            _laeufe.pop(slug, None)
