"""Projektart „Präsentation" — Arbeitsauftrag und Fundstellen.

Eigene Datei statt Anbau an prompts.py: Die Präsentation ist eine abgeschlossene
Sache mit eigenem Skill, eigenem Ausgabeformat und ohne Preset/design.md.
"""

import re
from pathlib import Path

SKILL_NAME = "smartcon-praesentation"

_UMLAUTE = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"),
            ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"))


def dateiname_aus_thema(thema: str) -> str:
    """Dateiname ohne Endung. Er landet in einem Download-Header, deshalb ASCII."""
    text = str(thema).strip()
    for zeichen, ersatz in _UMLAUTE:
        text = text.replace(zeichen, ersatz)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return f"AI-SmartCon_{text[:60]}" if text else "AI-SmartCon_Praesentation"


def dateien(projekt_dir: Path) -> list[Path]:
    """Erzeugte PowerPoint-Dateien, jüngste zuletzt.

    (mtime, name) statt nur mtime: gleiche mtime bei zwei Dateien darf nicht
    von der Dateisystem-Reihenfolge entschieden werden (siehe
    prompts.stoffquelle()).
    """
    return sorted(projekt_dir.glob("*.pptx"), key=lambda p: (p.stat().st_mtime, p.name))


def prompt(projekt_dir: Path, brief: dict, logo_pfad: Path | None) -> str:
    """Arbeitsauftrag: eine PPTX im AI-SmartCon-CI aus Thema und Quellen."""
    material = projekt_dir / "material"
    namen = sorted(p.name for p in material.iterdir()) if material.is_dir() else []
    if namen:
        material_block = (
            "Im Ordner `material/` liegen hochgeladene Unterlagen. **Sichte sie "
            "zuerst und behandle sie als Primärquelle** — sie gehen der "
            "Websuche vor:\n"
            + "\n".join(f"- {material / name}" for name in namen))
    else:
        material_block = "Es wurden keine Dateien hochgeladen."

    quellen = str(brief.get("quellen", "")).strip()
    quellen_block = (
        f"Zusätzlich hat der Nutzer diese Quellen genannt — arbeite sie ab:\n{quellen}"
        if quellen else
        "Es wurden keine einzelnen Quellen genannt; recherchiere selbst.")

    zeilen = [f"- {feld}: {brief.get(feld)}" for feld in
              ("thema", "zielgruppe", "vorwissen", "sprache", "dauer")
              if str(brief.get(feld, "")).strip()]
    if str(brief.get("lernziele", "")).strip():
        zeilen.append(f"- Lernziele/Inhalte: {brief['lernziele']}")
    briefing_block = "\n".join(zeilen)

    if logo_pfad is not None:
        logo_block = (
            f"- Das Haus-Logo liegt unter {logo_pfad} — verwende genau diese "
            "Datei für Titelfolie und Folgefolien. Nicht einfärben, nicht "
            "verzerren, keinen Ersatz erfinden.")
    else:
        logo_block = (
            "- Es ist **kein Logo hinterlegt**. Brich ab und melde das, statt "
            "ein Ersatz-Logo zu bauen — das Logo wird in den Einstellungen "
            "der App hochgeladen.")

    ziel = projekt_dir / f"{dateiname_aus_thema(brief.get('thema', ''))}.pptx"

    return f"""Du bist der Präsentations-Agent der App „SmartCon-Schulungen". Dein
Arbeitsverzeichnis ist der Projektordner: {projekt_dir}

## Auftrag

Erstelle eine vollständige PowerPoint-Präsentation im AI-SmartCon-CI.

**Nutze dazu den Skill `{SKILL_NAME}`** und halte dich an seine
Pflicht-Reihenfolge: Recherche → Storyline → Bau → QA. Findest du den Skill
nicht, brich ab und melde das — baue keine eigene Vorlage.

## Briefing

{briefing_block}

## Vorhandenes Material

{material_block}

{quellen_block}

## Vorgaben für diesen Lauf

- Schreibe die fertige Datei nach: {ziel}
{logo_block}
- **Jede Zahl, Norm, Frist und jeden Eigennamen belegen.** Die Quelle gehört
  in die Notizen (`notes`) der jeweiligen Folie. Diese Präsentation ist
  später die Grundlage einer Prüfung — was nicht belegt ist, gehört nicht
  hinein.
- Setze das Stand-Datum sichtbar auf die Titelfolie.
- Kein Text in erzeugten Bildern.
- Stelle keine Rückfragen (kein AskUserQuestion). Wo etwas fehlt, triff eine
  sinnvolle Annahme und halte sie auf der letzten Folie unter „Annahmen" fest.

## Abschluss

Beende den Lauf mit einer Zeile: Dateiname und Anzahl der Folien."""
