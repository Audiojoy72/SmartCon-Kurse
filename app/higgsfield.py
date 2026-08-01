"""Higgsfield-Guthaben — per CLI abfragen und kurz cachen.

Der Aufruf von „higgsfield account status" kostet keine Credits, dauert aber
spürbar — deshalb wird das Ergebnis 60 s zwischengespeichert, statt bei jedem
Gate-Request die CLI neu zu starten.
"""

import re
import subprocess
import threading
import time

CACHE_SEKUNDEN = 60
TIMEOUT = 20

# z. B. „1082.5 credits" — Nachkommastellen (Punkt oder Komma) mitnehmen
_ZAHL_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*credits", re.IGNORECASE)

_lock = threading.Lock()
_cache = {"ts": 0.0, "wert": None}


def _merken(wert: float | None) -> float | None:
    with _lock:
        _cache["ts"] = time.time()
        _cache["wert"] = wert
    return wert


def guthaben() -> float | None:
    """Aktuelles Higgsfield-Guthaben in Credits, None bei jedem Fehler."""
    with _lock:
        if time.time() - _cache["ts"] < CACHE_SEKUNDEN:
            return _cache["wert"]
    try:
        p = subprocess.run(["higgsfield", "account", "status"],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return _merken(None)
    if p.returncode != 0:
        return _merken(None)
    m = _ZAHL_RE.search(p.stdout + "\n" + p.stderr)
    if not m:
        return _merken(None)
    try:
        return _merken(float(m.group(1).replace(",", ".")))
    except ValueError:
        return _merken(None)
