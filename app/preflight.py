"""Preflight-Prüfung: alle externen Abhängigkeiten, als Ampel für das UI.

Jeder Check liefert {id, name, status, detail, hint, anleitung}.
status: "ok" | "warn" (optional, fehlt) | "fail" (Pflicht, fehlt)
anleitung: mehrzeilige Installations-/Reparatur-Schritte, wird im UI per Klick
auf die Kachel aufgeklappt.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 20

ANLEITUNG = {
    "claude": """\
1. Installieren:  curl -fsSL https://claude.ai/install.sh | bash
   (alternativ: npm i -g @anthropic-ai/claude-code)
2. Anmelden:  claude
   — beim ersten Start öffnet sich der Login im Browser.
3. Prüfen:  claude --version""",
    "kimi": """\
1. Installieren:  curl -fsSL https://code.kimi.com/install.sh | bash
2. Anmelden:  kimi
   — beim ersten Start läuft der Login durch.
3. Prüfen:  kimi --version""",
    "higgsfield": """\
1. Installieren:  npm i -g @higgsfield/cli
2. Anmelden:  higgsfield auth login
3. Workspace setzen (wird oft vergessen):
   higgsfield workspace list
   higgsfield workspace set <id>
   Ohne Workspace antwortet jeder Aufruf mit „No workspace selected".
4. Guthaben prüfen:  higgsfield account status""",
    "hf_auth": """\
Anmelden:  higgsfield auth login
Danach prüfen:  higgsfield account status""",
    "hf_ws": """\
1. Verfügbare Workspaces anzeigen:  higgsfield workspace list
2. Workspace wählen:  higgsfield workspace set <id>
3. Prüfen:  higgsfield workspace status""",
    "ffmpeg": """\
Debian/Ubuntu:  sudo apt install ffmpeg
macOS:          brew install ffmpeg
Prüfen:         ffmpeg -version""",
    "whisper": """\
Lokal (CPU, langsam aber ohne fremde Infrastruktur):
  python3 -m venv ~/.venv-whisper
  ~/.venv-whisper/bin/pip install openai-whisper
  — dann in den Einstellungen als Whisper-Befehl eintragen:
  ~/.venv-whisper/bin/whisper

Schneller: ein eigener GPU-Transkriptionsdienst (OpenAI-kompatibel,
verbose_json mit Wort-Zeitstempeln). Der Skill nutzt dafür die
Umgebungsvariable WHISPER_REMOTE_CMD — siehe skill/schulung/scripts/transkribieren.sh.
Wichtig: Der Skill braucht WORT-Zeitstempel, Segment-Granularität reicht nicht.""",
    "node22": """\
Nur nötig für gerenderte Erklär-Videos (HyperFrames); HTML-Szenen laufen ohne.
  nvm install 22
Nicht „nvm use" dauerhaft umstellen — der Wrapper skill/schulung/scripts/hyperframes.sh
sucht sich die 22er-Laufzeit selbst.""",
    "skill": """\
Der Skill gehört ins Repo: skill/schulung/SKILL.md
Wenn er fehlt, ist die Installation unvollständig — Repo neu klonen oder
den Stand aus dem Git-Verlauf wiederherstellen:
  git checkout -- skill/""",
    "design": """\
Der hinterlegte Pfad zur design.md existiert nicht.
Entweder den Pfad in den Einstellungen korrigieren oder die Datei anlegen —
Vorlage zum Ausfüllen: skill/schulung/reference/design-vorlage.md""",
    "whisper_api": """\
Der Dienst muss OpenAI-kompatibel sein und verbose_json mit WORT-Zeitstempeln
liefern (Segment-Granularität reicht dem Skill nicht — getestet wird hier
nur die Erreichbarkeit über GET <url>/models).

1. URL OHNE Pfad hinter /v1 eintragen, z. B. https://<dienst>/v1
   — der Endpunkt /audio/transcriptions wird vom Skill ergänzt.
2. API-Key eintragen, falls der Dienst einen verlangt.
3. Liegt der Dienst hinter Cloudflare Access: Service-Token anlegen
   (Cloudflare Zero Trust → Access → Service Auth → Service Token)
   und Client-Id + Client-Secret eintragen. Beide werden als Header
   CF-Access-Client-Id / CF-Access-Client-Secret mitgeschickt.
4. Modellname so eintragen, wie der Dienst ihn kennt (z. B. whisper-1,
   faster-whisper-large-v3, Systran/faster-whisper-large-v3).

Alle Werte stehen nur in der lokalen config.json (gitignored).""",
}


def _api_probe(cfg: dict) -> tuple[bool, str]:
    """Prüft den OpenAI-kompatiblen Whisper-Dienst über GET <url>/models."""
    import json
    import urllib.error
    import urllib.request

    url = cfg["whisper_api_url"].strip().rstrip("/")
    if not url:
        return False, "keine URL eingetragen"
    headers = {}
    if cfg["whisper_api_key"]:
        headers["Authorization"] = f"Bearer {cfg['whisper_api_key']}"
    if cfg["cf_access_client_id"]:
        headers["CF-Access-Client-Id"] = cfg["cf_access_client_id"]
        headers["CF-Access-Client-Secret"] = cfg["cf_access_client_secret"]
    req = urllib.request.Request(f"{url}/models", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
            modelle = len(data.get("data", [])) if isinstance(data, dict) else 0
            return True, f"erreichbar, {modelle} Modell(e) gemeldet"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} — Zugangsdaten/Cloudflare-Token prüfen"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, f"nicht erreichbar: {e}"


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        out = (p.stdout + p.stderr).strip().splitlines()
        return p.returncode == 0, (out[0] if out else "")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def _check_binary(check_id: str, name: str, cmd: list[str], pflicht: bool,
                  hint: str) -> dict:
    base = {"id": check_id, "name": name, "anleitung": ANLEITUNG.get(check_id, "")}
    if not shutil.which(cmd[0]):
        return {**base, "status": "fail" if pflicht else "warn",
                "detail": "nicht gefunden", "hint": hint}
    ok, first = _run(cmd)
    if ok:
        return {**base, "status": "ok", "detail": first, "hint": ""}
    return {**base, "status": "fail" if pflicht else "warn",
            "detail": first or "Aufruf fehlgeschlagen", "hint": hint}


def run_all(cfg: dict) -> list[dict]:
    checks = []

    checks.append(_check_binary(
        "claude", "Claude-Code-CLI (primäres Backend)", ["claude", "--version"],
        pflicht=cfg["backend"] == "claude",
        hint="Claude Code installieren und anmelden"))

    checks.append(_check_binary(
        "kimi", "Kimi-CLI (Fallback-Backend)", ["kimi", "--version"],
        pflicht=cfg["backend"] == "kimi",
        hint="Kimi Code installieren und anmelden"))

    checks.append(_check_binary(
        "higgsfield", "Higgsfield-CLI", ["higgsfield", "version"],
        pflicht=False,
        hint="nur für KI-Medien nötig — Preset kostenlos kommt ohne Higgsfield aus "
             "(ansonsten: npm i -g @higgsfield/cli, dann higgsfield auth login)"))

    # Auth + Workspace nur prüfen, wenn die CLI da ist
    if shutil.which("higgsfield"):
        ok, first = _run(["higgsfield", "account", "status"])
        checks.append({"id": "hf_auth", "name": "Higgsfield-Anmeldung & Guthaben",
                       "status": "ok" if ok else "fail", "detail": first,
                       "hint": "" if ok else "higgsfield auth login",
                       "anleitung": ANLEITUNG["hf_auth"]})
        ok, first = _run(["higgsfield", "workspace", "status"])
        checks.append({"id": "hf_ws", "name": "Higgsfield-Workspace",
                       "status": "ok" if ok else "fail", "detail": first,
                       "hint": "" if ok else "higgsfield workspace set <id>",
                       "anleitung": ANLEITUNG["hf_ws"]})

    checks.append(_check_binary(
        "ffmpeg", "ffmpeg", ["ffmpeg", "-version"], pflicht=True,
        hint="Distributionspaket installieren (z. B. apt install ffmpeg)"))

    if cfg["whisper_modus"] == "api":
        ok, first = _api_probe(cfg)
        checks.append({
            "id": "whisper_api", "name": "Whisper-API (Transkriptionsdienst)",
            "status": "ok" if ok else "fail",
            "detail": first,
            "hint": "" if ok else "URL/Key/Cloudflare-Token in den Einstellungen prüfen",
            "anleitung": ANLEITUNG["whisper_api"]})
    else:
        checks.append(_check_binary(
            "whisper", "Whisper (lokale Transkription)", [cfg["whisper_command"], "--help"],
            pflicht=False,
            hint="lokal installieren oder in den Einstellungen auf API-Modus wechseln "
                 "— nicht nötig beim Preset kostenlos"))

    # Node 22+ für HyperFrames (optional): erst System-Node prüfen, dann nvm
    node22 = ""
    if shutil.which("node"):
        ok, first = _run(["node", "--version"])
        if ok:
            try:
                if int(first.lstrip("v").split(".")[0]) >= 22:
                    node22 = first
            except ValueError:
                pass
    if not node22:
        nvm_dir = Path.home() / ".nvm" / "versions" / "node"
        if nvm_dir.is_dir():
            for v in sorted(nvm_dir.iterdir(), reverse=True):
                try:
                    major = int(v.name.lstrip("v").split(".")[0])
                except ValueError:
                    continue
                if major >= 22:
                    node22 = v.name
                    break
    checks.append({"id": "node22", "name": "Node 22+ (HyperFrames, optional)",
                   "status": "ok" if node22 else "warn",
                   "detail": node22 or "nicht gefunden",
                   "hint": "" if node22 else "nvm install 22 — nicht nötig beim "
                                              "Preset kostenlos",
                   "anleitung": ANLEITUNG["node22"]})

    # Neutraler Skill im Repo?
    skill_md = ROOT / "skill" / "schulung" / "SKILL.md"
    checks.append({"id": "skill", "name": "Schulungs-Skill (im Repo)",
                   "status": "ok" if skill_md.exists() else "fail",
                   "detail": str(skill_md.relative_to(ROOT)) if skill_md.exists()
                             else "fehlt",
                   "hint": "" if skill_md.exists()
                           else "skill/schulung/SKILL.md fehlt im Repo",
                   "anleitung": ANLEITUNG["skill"]})

    # design.md (optional)
    design = cfg.get("default_design_md", "").strip()
    if design:
        ok = Path(design).expanduser().is_file()
        checks.append({"id": "design", "name": "Default-design.md",
                       "status": "ok" if ok else "warn",
                       "detail": design if ok else f"nicht gefunden: {design}",
                       "hint": "" if ok else "Pfad in den Einstellungen korrigieren",
                       "anleitung": ANLEITUNG["design"]})

    checks.append({"id": "python", "name": "Python",
                   "status": "ok",
                   "detail": sys.version.split()[0], "hint": "", "anleitung": ""})

    return checks
