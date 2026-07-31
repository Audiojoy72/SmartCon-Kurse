"""Konfiguration der App — config.json im Projektroot, im UI editierbar."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"

DEFAULTS = {
    "backend": "claude",           # "claude" | "kimi"
    "default_design_md": "",       # Pfad zu einer design.md, leer = Preset-Default
    "whisper_command": "whisper",  # lokale Transkription
    "port": 8710,
}


def load() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}
    return {**DEFAULTS, **data}


def save(cfg: dict) -> dict:
    clean = {k: cfg.get(k, v) for k, v in DEFAULTS.items()}
    if clean["backend"] not in ("claude", "kimi"):
        clean["backend"] = "claude"
    CONFIG_PATH.write_text(
        json.dumps(clean, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return clean
