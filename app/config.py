"""Konfiguration der App — config.json im Projektroot, im UI editierbar."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"

DEFAULTS = {
    "backend": "claude",           # "claude" | "kimi"
    "default_design_md": "",       # Pfad zu einer design.md, leer = Preset-Default
    "whisper_modus": "lokal",      # "lokal" | "api"
    "whisper_command": "whisper",  # lokale Transkription (Modus "lokal")
    # Modus "api": OpenAI-kompatibler Transkriptionsdienst (/v1/audio/transcriptions).
    # Zugangsdaten leben NUR in config.json (gitignored) — niemals ins Repo.
    "whisper_api_url": "",         # z. B. https://<dienst>/v1 — OpenRouter-Preset: https://openrouter.ai/api/v1
    "whisper_api_key": "",
    "whisper_api_model": "whisper-1",
    # Cloudflare Access (Service Token), falls der Dienst dahinter liegt
    "cf_access_client_id": "",
    "cf_access_client_secret": "",
    "port": 8710,
    # Default aus: LAN-Zugriff hat keinen Login, und der Agent arbeitet mit
    # Bash-Rechten — bewusst zuschalten statt versehentlich offen stehen.
    "lan_erreichbar": False,       # True = im LAN erreichbar (0.0.0.0), False = nur localhost
    # Portal-Cookie nur über HTTPS senden. Für die Entwicklung über
    # http://localhost abschaltbar — im Betrieb bleibt es an.
    "portal_secure_cookie": True,
    # Mailversand für Anmeldebestätigungen. Zugangsdaten leben nur hier.
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_passwort": "",
    "smtp_von": "",
    "smtp_starttls": True,
    # Öffentliche Adresse des Portals, für die Zugangsmail.
    "portal_url": "",
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
    if clean["whisper_modus"] not in ("lokal", "api"):
        clean["whisper_modus"] = "lokal"
    clean["lan_erreichbar"] = bool(clean["lan_erreichbar"])
    CONFIG_PATH.write_text(
        json.dumps(clean, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return clean


# Haus-Logo für den Präsentations-Skill. Liegt neben der config.json und ist
# gitignored — ins öffentliche Repo gehört keine Bildmarke.
LOGO_PFAD = ROOT / "config-logo.png"

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def standard_logo() -> bytes | None:
    """Das hinterlegte Logo, oder None."""
    try:
        return LOGO_PFAD.read_bytes()
    except OSError:
        return None


def logo_speichern(daten: bytes) -> None:
    """Legt das Logo ab. Nur PNG — der Skill bettet es unverändert ein."""
    if not daten.startswith(_PNG_MAGIC):
        raise ValueError("Nur PNG-Dateien werden angenommen")
    LOGO_PFAD.write_bytes(daten)


def logo_loeschen() -> None:
    LOGO_PFAD.unlink(missing_ok=True)
