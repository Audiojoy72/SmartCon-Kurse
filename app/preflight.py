"""Preflight-Prüfung: alle externen Abhängigkeiten, als Ampel für das UI.

Jeder Check liefert {id, name, status, detail, hint}.
status: "ok" | "warn" (optional, fehlt) | "fail" (Pflicht, fehlt)
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 20


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        out = (p.stdout + p.stderr).strip().splitlines()
        return p.returncode == 0, (out[0] if out else "")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def _check_binary(check_id: str, name: str, cmd: list[str], pflicht: bool,
                  hint: str) -> dict:
    if not shutil.which(cmd[0]):
        return {"id": check_id, "name": name,
                "status": "fail" if pflicht else "warn",
                "detail": "nicht gefunden", "hint": hint}
    ok, first = _run(cmd)
    if ok:
        return {"id": check_id, "name": name, "status": "ok",
                "detail": first, "hint": ""}
    return {"id": check_id, "name": name,
            "status": "fail" if pflicht else "warn",
            "detail": first or "Aufruf fehlgeschlagen", "hint": hint}


def run_all(cfg: dict) -> list[dict]:
    checks = []

    checks.append(_check_binary(
        "claude", "Claude-Code-CLI (primäres Backend)", ["claude", "--version"],
        pflicht=cfg["backend"] == "claude",
        hint="Claude Code installieren und anmelden: https://claude.ai/code"))

    checks.append(_check_binary(
        "kimi", "Kimi-CLI (Fallback-Backend)", ["kimi", "--version"],
        pflicht=cfg["backend"] == "kimi",
        hint="Kimi Code installieren und anmelden"))

    checks.append(_check_binary(
        "higgsfield", "Higgsfield-CLI", ["higgsfield", "version"],
        pflicht=True,
        hint="npm i -g higgsfield, dann: higgsfield auth login"))

    # Auth + Workspace nur prüfen, wenn die CLI da ist
    if shutil.which("higgsfield"):
        ok, first = _run(["higgsfield", "account", "status"])
        checks.append({"id": "hf_auth", "name": "Higgsfield-Anmeldung & Guthaben",
                       "status": "ok" if ok else "fail", "detail": first,
                       "hint": "" if ok else "higgsfield auth login"})
        ok, first = _run(["higgsfield", "workspace", "status"])
        checks.append({"id": "hf_ws", "name": "Higgsfield-Workspace",
                       "status": "ok" if ok else "fail", "detail": first,
                       "hint": "" if ok else "higgsfield workspace set <id>"})

    checks.append(_check_binary(
        "ffmpeg", "ffmpeg", ["ffmpeg", "-version"], pflicht=True,
        hint="Distributionspaket installieren (z. B. apt install ffmpeg)"))

    checks.append(_check_binary(
        "whisper", "Whisper (lokale Transkription)", [cfg["whisper_command"], "--help"],
        pflicht=False,
        hint="pip install openai-whisper — oder einen eigenen Transkriptionsbefehl "
             "in den Einstellungen hinterlegen"))

    # Node 22+ für HyperFrames (optional): unter nvm suchen
    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    node22 = ""
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
                   "hint": "" if node22 else "nvm install 22 — nur nötig für "
                                             "gerenderte Erklär-Videos"})

    # Neutraler Skill im Repo?
    skill_md = ROOT / "skill" / "schulung" / "SKILL.md"
    checks.append({"id": "skill", "name": "Schulungs-Skill (im Repo)",
                   "status": "ok" if skill_md.exists() else "fail",
                   "detail": str(skill_md.relative_to(ROOT)) if skill_md.exists()
                             else "fehlt",
                   "hint": "" if skill_md.exists()
                           else "skill/schulung/SKILL.md fehlt im Repo"})

    # design.md (optional)
    design = cfg.get("default_design_md", "").strip()
    if design:
        ok = Path(design).expanduser().is_file()
        checks.append({"id": "design", "name": "Default-design.md",
                       "status": "ok" if ok else "warn",
                       "detail": design if ok else f"nicht gefunden: {design}",
                       "hint": "" if ok else "Pfad in den Einstellungen korrigieren"})

    checks.append({"id": "python", "name": "Python",
                   "status": "ok",
                   "detail": sys.version.split()[0], "hint": ""})

    return checks
