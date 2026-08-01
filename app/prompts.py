"""Prompt-Templates — die App besitzt die State-Machine, der Agent bekommt pro
Phase einen Arbeitsauftrag, der auf die SKILL.md im Repo verweist."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "skill" / "schulung" / "SKILL.md"
STYLES_DIR = ROOT / "skill" / "schulung" / "reference" / "styles"

PRESET_NAMEN = ("cinematic", "comic", "corporate", "statisch")


def presets() -> list[dict]:
    """Liest die Preset-Karten für das Formular aus reference/styles/*.md.

    Extrahiert simpel: Titel aus der ersten Überschrift, Beschreibung aus dem
    ersten Absatz danach, Kosten aus dem Abschnitt „## Kostenrahmen".
    """
    out = []
    for datei in sorted(STYLES_DIR.glob("*.md")):
        text = datei.read_text(encoding="utf-8")
        titel = datei.stem
        m = re.search(r"^#\s+Preset:\s*(.+)$", text, re.MULTILINE)
        if m:
            titel = m.group(1).strip()
        absaetze = [p.strip().replace("\n", " ") for p in
                    re.split(r"\n\s*\n", text) if p.strip()]
        beschreibung = ""
        for p in absaetze[1:]:
            if not p.startswith("#"):
                beschreibung = p
                break
        kosten = ""
        m = re.search(r"^##\s+Kostenrahmen\s*\n+(.+)$", text, re.MULTILINE)
        if m:
            kosten = re.sub(r"\*\*", "", m.group(1)).strip()
        out.append({"name": datei.stem, "titel": titel,
                    "beschreibung": beschreibung, "kosten": kosten})
    return out


def _briefing_block(brief: dict) -> str:
    zeilen = [
        f"- Thema: {brief.get('thema', '')}",
        f"- Lernziele: {brief.get('lernziele', '')}",
        f"- Zielgruppe: {brief.get('zielgruppe', '')}",
    ]
    if brief.get("vorwissen"):
        zeilen.append(f"- Vorwissen der Zielgruppe: {brief['vorwissen']}")
    zeilen.append(f"- Sprache aller Texte/Stimmen: {brief.get('sprache', '')}")
    zeilen.append(f"- Gewünschte Dauer: {brief.get('dauer', '')}")
    if brief.get("material_hinweise"):
        zeilen.append(f"- Hinweise zu vorhandenem Material: "
                      f"{brief['material_hinweise']}")
    return "\n".join(zeilen)


def curriculum_prompt(projekt_dir: Path, brief: dict,
                      material_dateien: list[str]) -> str:
    """Arbeitsauftrag für Teil 1 (Phasen 0–2): Recherche + curriculum.md."""
    stil = brief.get("stil", "cinematic")
    if stil == "design":
        stil_zeile = (f"Lies danach die hochgeladene Design-Vorgabe: "
                      f"{projekt_dir / 'design.md'}")
    else:
        stil_zeile = (f"Lies danach das gewählte Preset vollständig: "
                      f"{STYLES_DIR / (stil + '.md')}")
    if material_dateien:
        material_zeile = (
            "Im Projektordner liegt vom Nutzer hochgeladenes Material — sichte es "
            "und behandle es als Primärquelle:\n"
            + "\n".join(f"- {projekt_dir / 'material' / name}"
                        for name in material_dateien))
    else:
        material_zeile = "Es wurde kein Ausgangsmaterial hochgeladen."
    return f"""Du bist der Schulungs-Agent der App „SmartCon-Schulungen". Dein
Arbeitsverzeichnis ist der Projektordner: {projekt_dir}

Lies zuerst diese Skill-Anleitung vollständig: {SKILL_MD}
{stil_zeile}

Arbeite NUR Teil 1 des Skills (Phasen 0–2): Recherche und das Curriculum.
Schreibe das Ergebnis als Datei {projekt_dir / 'curriculum.md'}.
KEINE Produktion (kein Referenzbild, kein Voiceover, keine Videos/Bilder, kein
HTML), KEINE Credits ausgeben — rufe unter keinen Umständen „higgsfield generate"
oder andere kostenpflichtige Generierung auf.

Das Briefing ist vollständig — stelle KEINE Rückfragen (kein AskUserQuestion).
Wo etwas fehlt, triff eine sinnvolle Annahme und dokumentiere sie sichtbar im
Steckbrief des curriculum.md.

## Briefing

{_briefing_block(brief)}

## Vorhandenes Material

{material_zeile}

## Sprachregeln

- Lernenden-Texte (Voiceover, Bildschirmtexte, Quiz, Feedback) in der Sprache
  aus dem Briefing.
- Bild- und Video-Prompts im Medienplan IMMER auf Englisch (mit „no readable
  text, no captions").

## Abschluss

Beende den Lauf mit einer kurzen Zusammenfassung als letztem Text: Anzahl der
Level, geplanter Medienmix (FILM/ANIMATION/BILD) und grobe Credit-Schätzung
für die spätere Produktion."""


def kommentar_prompt(kommentar: str, projekt_dir: Path,
                     hat_session: bool) -> str:
    """Arbeitsauftrag für einen Änderungswunsch am bestehenden Curriculum."""
    vorspann = "" if hat_session else f"""Du arbeitest im Projektordner {projekt_dir}.
Lies zuerst die Skill-Anleitung {SKILL_MD} (nur Teil 1 ist relevant) und die
vorhandene Datei {projekt_dir / 'curriculum.md'}.

"""
    return f"""{vorspann}Arbeite diesen Änderungswunsch des Nutzers in die Datei
curriculum.md im Projektordner ein:

---
{kommentar}
---

Halte dabei die Struktur des curriculum.md aus der Skill-Anleitung ein. KEINE
Produktion, KEINE Credits (kein „higgsfield generate"). Stelle keine Rückfragen
— triff bei Unklarheiten eine dokumentierte Annahme.

Beende den Lauf mit einer kurzen Zusammenfassung der vorgenommenen Änderungen."""


def kostenplan_prompt(projekt_dir: Path) -> str:
    """Arbeitsauftrag: Kostenplan (kosten.json) aus dem curriculum.md erstellen."""
    schema = """
{
  "posten": [
    {"typ": "video|bild|voiceover|upscale|freisteller",
     "beschreibung": "kurze deutsche Beschreibung",
     "anzahl": 1,
     "credits_je": 0.0,
     "credits_summe": 0.0}
  ],
  "summe": 0.0
}
"""
    return f"""Du bist der Kostenplan-Agent der App „SmartCon-Schulungen". Dein
Arbeitsverzeichnis ist der Projektordner: {projekt_dir}

Lies die Datei {projekt_dir / 'curriculum.md'} (insbesondere Medienplan und
Produktionsschätzung) und die Kosten-Richtwerte am Ende der Skill-Anleitung
{SKILL_MD} (Abschnitt „Kosten-Richtwerte (Higgsfield-Credits)").

Erstelle daraus den Kostenplan für die Produktion (Teil 2 des Skills) und
schreibe ihn als maschinenlesbare JSON-Datei {projekt_dir / 'kosten.json'} —
exakt in diesem Schema:
{schema}
Regeln:
- „typ" ist genau einer der fünf aufgeführten Werte.
- „credits_summe" = anzahl × credits_je, „summe" = Summe aller Posten.
- Zahlen als JSON-Zahlen (Punkt als Dezimaltrennzeichen), keine Einheiten im
  JSON — Credits-Angaben nur als Zahl.
- Die Datei enthält NUR das JSON, keinen Kommentar, kein Markdown.

Miss die Preise nach, statt nur zu schätzen: rufe für die konkret geplanten
Generierungen „higgsfield generate cost <job_type> ..." auf (das ist kostenlos)
und setze die echten Werte ein. Wo der Aufruf nicht möglich ist, gelten die
Richtwerte aus der Skill-Anleitung (9 Credits pro Videosekunde, ~4/~2 Credits
je Bild, ~0,4 Credits je Voiceover-Szene).

STRIKT VERBOTEN: „higgsfield generate create" oder jeder andere Aufruf, der
Credits verbraucht. Es wird NUR gelesen und per „generate cost" gemessen.

Stelle keine Rückfragen. Beende den Lauf mit einer Zeile: Gesamtsumme und
Anzahl der Posten."""


def freigabe_prompt(aenderungen: list[str], projekt_dir: Path,
                    hat_session: bool) -> str:
    """Arbeitsauftrag beim Go mit Medien-Änderungen (Resume der Curriculum-
    Session): Änderungen ins curriculum.md einarbeiten, dann kurz bestätigen."""
    vorspann = "" if hat_session else f"""Du arbeitest im Projektordner {projekt_dir}.
Lies zuerst die Datei {projekt_dir / 'curriculum.md'}.

"""
    liste = "\n".join(f"- {a}" for a in aenderungen)
    return f"""{vorspann}Der Nutzer gibt das Curriculum frei — mit folgenden
Medien-Änderungen, die du zuerst in der Datei curriculum.md im Projektordner
einarbeitest:

{liste}

Die Änderungen müssen ÜBERALL konsistent sein: in der Level-Übersicht
(Tabelle) UND in den ausführlichen Level-Abschnitten inkl. Medienplan UND in
der Produktionsschätzung (Kosten neu rechnen, wenn das neue Medium günstiger
oder teurer ist).

KEINE Produktion, KEINE Credits (kein „higgsfield generate"). Stelle keine
Rückfragen. Bestätige danach kurz, was du geändert hast."""
