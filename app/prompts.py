"""Prompt-Templates — die App besitzt die State-Machine, der Agent bekommt pro
Phase einen Arbeitsauftrag, der auf die SKILL.md im Repo verweist."""

import json
import re
import shlex
from pathlib import Path

from . import folien, pruefung

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "skill" / "schulung" / "SKILL.md"
SKILL_SCRIPTS = ROOT / "skill" / "schulung" / "scripts"
STYLES_DIR = ROOT / "skill" / "schulung" / "reference" / "styles"

PRESET_NAMEN = ("cinematic", "comic", "corporate", "statisch", "kostenlos")


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


def _stil_zeile(projekt_dir: Path, stil: str) -> str:
    """Welche Stil-Quellen der Agent lesen soll.

    Preset und design.md sind zwei unabhängige Achsen: Das Preset bestimmt die
    Machart (und damit den Higgsfield-Einsatz), die optionale design.md nur die
    Optik. Eine hochgeladene Datei gilt deshalb ZUSÄTZLICH zum Preset und hat
    bei Farben/Typografie Vorrang — die Medien- und Kostenregeln bleiben beim
    Preset (sonst würde „kostenlos" seine 0-Credit-Garantie verlieren).

    `stil == "design"` legt die App nicht mehr an; der Zweig bleibt für
    Altprojekte, deren brief.json den Wert noch trägt.
    """
    design_datei = projekt_dir / "design.md"
    zeilen = []
    if stil != "design":
        zeilen.append(f"Lies danach das gewählte Preset vollständig: "
                      f"{STYLES_DIR / (stil + '.md')}")
    if design_datei.is_file():
        if stil == "design":
            zeilen.append(f"Lies danach die hochgeladene Design-Vorgabe: "
                          f"{design_datei}")
        else:
            zeilen.append(
                f"Im Projektordner liegt zusätzlich eine eigene Design-Vorgabe: "
                f"{design_datei}\n"
                "Lies sie ebenfalls vollständig. Bei Optik (Farben, Typografie, "
                "Tonalität) hat sie VORRANG vor dem Preset; die Medien- und "
                "Kostenregeln des Presets bleiben unverändert gültig.")
        zeilen.append(
            "Halte im Steckbrief des curriculum.md ausdrücklich fest, DASS eine "
            "design.md vorliegt, und übernimm ihre Farbwerte und Schriften dort "
            "wörtlich — die Produktion liest später nur das curriculum.md.")
    return "\n".join(zeilen)


def curriculum_prompt(projekt_dir: Path, brief: dict,
                      material_dateien: list[str]) -> str:
    """Arbeitsauftrag für Teil 1 (Phasen 0–2): Recherche + curriculum.md."""
    stil = brief.get("stil", "cinematic")
    stil_zeile = _stil_zeile(projekt_dir, stil)
    if material_dateien:
        material_zeile = (
            "Im Projektordner liegt vom Nutzer hochgeladenes Material — sichte es "
            "und behandle es als Primärquelle:\n"
            + "\n".join(f"- {projekt_dir / 'material' / name}"
                        for name in material_dateien))
    else:
        material_zeile = "Es wurde kein Ausgangsmaterial hochgeladen."
    ki_medien = (False if stil == "kostenlos"
                 else bool(brief.get("ki_medien", True)))
    if ki_medien:
        medien_block = ""
        abschluss_mix = "geplanter Medienmix (FILM/ANIMATION/BILD) und grobe Credit-Schätzung"
    else:
        medien_block = """
## KI-Medien: Nein — medienloses Curriculum (0 Credits)

Der Nutzer hat KI-Medien (Higgsfield) abgeschaltet. Folge im Skill dem
Abschnitt „Medienloser Zweig — Preset kostenlos": Der Medienplan ALLER Level
ist „schrittgesteuerte HTML-Szene" — KEIN FILM, KEIN BILD (KI), KEIN Voiceover.
Das Voiceover-Skript je Level wird als Sprechertext/Bildschirmtext der Szene
ausformuliert (nicht gestrichen). Die Produktionsschätzung lautet 0 Credits.
"""
        abschluss_mix = "Level-Anzahl und die Bestätigung, dass alle Level medienlos (0 Credits) geplant sind"
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
{medien_block}
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

Beende den Lauf mit einer kurzen Zusammenfassung als letztem Text: {abschluss_mix}."""


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


def whisper_remote_env(cfg: dict) -> dict[str, str]:
    """Baut WHISPER_REMOTE_CMD für den Produktions-Subprozess aus der Config.

    Modus „api": ein curl-Aufruf gegen den OpenAI-kompatiblen
    Transkriptionsdienst (<whisper_api_url>/audio/transcriptions), der die
    Audiodatei per stdin bekommt (-F file=@-) und verbose_json mit
    Wort-Zeitstempeln liefert — genau das Format, das transkribieren.sh vom
    Remote-Kommando erwartet. Modus „lokal" oder fehlende URL: leeres Dict,
    dann nutzt das Skript das lokale whisper.
    """
    if cfg.get("whisper_modus") != "api":
        return {}
    url = (cfg.get("whisper_api_url") or "").strip().rstrip("/")
    if not url:
        return {}
    teile = ["curl", "-sS", "-m", "600"]
    key = (cfg.get("whisper_api_key") or "").strip()
    if key:
        teile += ["-H", shlex.quote(f"Authorization: Bearer {key}")]
    cf_id = (cfg.get("cf_access_client_id") or "").strip()
    if cf_id:
        teile += ["-H", shlex.quote(f"CF-Access-Client-Id: {cf_id}")]
    cf_secret = (cfg.get("cf_access_client_secret") or "").strip()
    if cf_secret:
        teile += ["-H", shlex.quote(f"CF-Access-Client-Secret: {cf_secret}")]
    modell = (cfg.get("whisper_api_model") or "whisper-1").strip()
    teile += [
        shlex.quote(f"{url}/audio/transcriptions"),
        "-F", "file=@-",
        "-F", "response_format=verbose_json",
        "-F", "timestamp_granularities[]=word",
        "-F", shlex.quote(f"model={modell}"),
    ]
    return {"WHISPER_REMOTE_CMD": " ".join(teile)}


def _projekt_stil(projekt_dir: Path) -> str:
    """Liest das gewählte Preset aus der brief.json des Projekts."""
    try:
        brief = json.loads(
            (projekt_dir / "brief.json").read_text(encoding="utf-8"))
        return str(brief.get("stil", "")).strip()
    except (OSError, json.JSONDecodeError):
        return ""


def _projekt_ki_medien(projekt_dir: Path) -> bool:
    """Sollen KI-Medien (Higgsfield) genutzt werden?

    Nein, wenn der Schalter im Briefing auf „nein" steht ODER das Preset
    „kostenlos" gewählt wurde (das impliziert medienlos). Default: ja.
    """
    try:
        brief = json.loads(
            (projekt_dir / "brief.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if str(brief.get("stil", "")).strip() == "kostenlos":
        return False
    return bool(brief.get("ki_medien", True))


def produktion_prompt(projekt_dir: Path, whisper_remote: bool) -> str:
    """Arbeitsauftrag für Teil 2 (Phasen 2.5–11): die komplette Produktion."""
    if whisper_remote:
        transkription_zeile = (
            "Für die Transkription ist die Umgebungsvariable WHISPER_REMOTE_CMD\n"
            "bereits im Prozess gesetzt — scripts/transkribieren.sh nutzt sie\n"
            "automatisch. Nichts daran ändern und KEIN lokales whisper\n"
            "nachinstallieren.")
    else:
        transkription_zeile = (
            "Für die Transkription ist WHISPER_REMOTE_CMD NICHT gesetzt —\n"
            "scripts/transkribieren.sh nutzt dann das lokal installierte\n"
            "whisper (Default-Weg des Skills).")
    stil = _projekt_stil(projekt_dir)
    # design.md gilt auch hier, obwohl die Produktion sonst nur curriculum.md
    # liest — sonst geht die CI verloren, wenn sie im Curriculum zu knapp steht.
    if (projekt_dir / "design.md").is_file():
        design_block = f"""
## Eigene Design-Vorgabe (Vorrang vor dem Preset)

Im Projektordner liegt eine design.md: {projekt_dir / 'design.md'}
Lies sie vor dem HTML-Bau (Phase 6) vollständig. Farben, Typografie und
Tonalität der fertigen HTML richten sich nach dieser Datei, nicht nach dem
Preset. Medien- und Kostenregeln bleiben davon unberührt.
"""
    else:
        design_block = ""
    try:
        brief = json.loads(
            (projekt_dir / "brief.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        brief = {}
    folien_teil = folien_block(projekt_dir, brief)
    if not _projekt_ki_medien(projekt_dir):
        kostenlos_block = f"""
## KI-Medien: Nein (0 Credits — medienloser Zweig)

Dieses Projekt wird OHNE Higgsfield produziert (Schalter „KI-Medien" auf
Nein im Briefing oder Preset „kostenlos" — steht so in der brief.json).
Das hat drei harte Konsequenzen:

1. Preflight im Kostenlos-Modus aufrufen (Higgsfield wird dann nicht gebraucht):
     SCHULUNG_KOSTENLOS=1 bash {SKILL_SCRIPTS / 'preflight.sh'}
2. KEINE higgsfield-Aufrufe — weder „generate create" noch „generate cost"
   noch „account status". Es werden 0 Credits ausgegeben.
3. TEIL 2 läuft im medienlosen Zweig gemäß SKILL.md (Abschnitt „Medienloser
   Zweig — Preset kostenlos"): Die Phasen 3, 4, 5, 7 und 8 ENTFALLEN. Ablauf:
   Phase 2.5 (Preflight, Kostenlos-Modus) → Phase 6 (schrittgesteuerte
   HTML-Szenen ohne Tonspur; das Voiceover-Skript wird Bildschirmtext) →
   Phase 9 (HTML ohne <video>/<audio>, ohne „Ton an!"-Hinweis) → Phase 10
   (Browser-Test inkl. Schritt-Steuerung) → Phase 11 (Auslieferung).
"""
        reihenfolge = f"""## Reihenfolge (verbindlich)

1. ZUERST der Preflight im Kostenlos-Modus:
     SCHULUNG_KOSTENLOS=1 bash {SKILL_SCRIPTS / 'preflight.sh'}
   Bricht der Preflight ab (Exit-Code ungleich 0): sofort stoppen und klar
   melden, was fehlt.
2. KEINE Transkription, KEINE Kostenkontrolle — es gibt kein Voiceover und
   keine Generierungen (0 Credits).
3. Auslieferung (Phase 11): Die fertige HTML-Datei bleibt im Projektordner
   ({projekt_dir}). NICHT irgendwo hochladen — kein rclone, kein
   Filesharing-Dienst, kein externer Ablageort."""
    else:
        kostenlos_block = ""
        reihenfolge = f"""## Reihenfolge (verbindlich)

1. ZUERST der Preflight — vor jeder kostenpflichtigen Aktion:
     bash {SKILL_SCRIPTS / 'preflight.sh'}
   Bricht der Preflight ab (Exit-Code ungleich 0): sofort stoppen, nichts
   generieren und klar melden, was fehlt.
2. Transkription: {transkription_zeile}
3. Kostenkontrolle: vor kostenpflichtigen Generierungen die geplanten Aufrufe
   mit „higgsfield generate cost …" durchrechnen und die Summe gegen
   „higgsfield account status" halten. Reicht das Guthaben nicht: NICHT „so
   weit es reicht" produzieren, sondern stoppen und klar melden (die App kann
   keine Rückfragen beantworten).
4. Auslieferung (Phase 11): Die fertige HTML-Datei bleibt im Projektordner
   ({projekt_dir}). NICHT irgendwo hochladen — kein rclone, kein
   Filesharing-Dienst, kein externer Ablageort."""
    return f"""Du bist der Produktions-Agent der App „SmartCon-Schulungen". Dein
Arbeitsverzeichnis ist der Projektordner: {projekt_dir}

Lies zuerst diese Skill-Anleitung vollständig: {SKILL_MD}
Arbeite danach TEIL 2 vollständig ab — von Phase 2.5 (Preflight) bis Phase 11
(Auslieferung). Quelle ist ausschließlich die Datei curriculum.md in diesem
Projektordner: was produziert wird, steht dort. Nicht improvisieren, keine
Rückfragen (kein AskUserQuestion).
{design_block}{kostenlos_block}{folien_teil}
{reihenfolge}

## Abschluss

Beende den Lauf mit einer kurzen Zusammenfassung als letztem Text: Name der
fertigen HTML-Datei, Anzahl produzierter Medien (Bilder/Videos/Voiceovers)
und die von dir mitgezählten Credits."""


# Formate, die einen Foliensatz tragen können.
_FOLIEN_ENDUNGEN = (".pptx", ".pdf", ".key", ".odp")


def stoffquelle(projekt_dir: Path) -> Path | None:
    """Die Datei, die den tatsächlich behandelten Stoff trägt.

    Das ist NICHT das curriculum.md: Das ist der Plan, und zwischen Plan und
    Auslieferung liegt die Produktion, die kürzt und gewichtet. Geprüft werden
    darf nur, was die Teilnehmer auch bekommen haben.

    Vorrang hat eine hochgeladene Präsentation im material/-Ordner — bei einer
    Live-Schulung ist der Foliensatz der behandelte Stoff, nicht die Nacharbeit.
    Fehlt sie, gilt die erzeugte Lerneinheit. Ohne beides: None; der Aufrufer
    fällt dann sichtbar auf das Curriculum zurück.
    """
    material = projekt_dir / "material"
    if material.is_dir():
        folien = sorted(
            (p for p in material.iterdir()
             if p.is_file() and p.suffix.lower() in _FOLIEN_ENDUNGEN),
            key=lambda p: p.stat().st_mtime)
        if folien:
            return folien[-1]

    # Jüngste statt alphabetisch erste: Im Projektordner liegen während des
    # Laufs regelmäßig Zwischendateien. pruefung.html ist ausgeschlossen —
    # sie ist die Prüfung, nicht der Stoff, den sie abfragt; sonst würde ein
    # geöffneter Prüfungsbogen per mtime zur Stoffquelle der nächsten Prüfung.
    seiten = sorted(
        (p for p in projekt_dir.glob("*.html")
         if p.is_file() and p.name != pruefung.HTML_DATEINAME),
        key=lambda p: p.stat().st_mtime)
    return seiten[-1] if seiten else None


def folien_block(projekt_dir: Path, brief: dict) -> str:
    """Textbaustein für den Produktions-Prompt. Leer, wenn der Schalter aus ist."""
    if not brief.get("folien_einbetten"):
        return ""

    quelle = stoffquelle(projekt_dir)
    ziel = projekt_dir / "folien"
    if quelle is None or quelle.suffix.lower() not in folien.QUELLFORMATE:
        return """
## Folien einbetten — nicht möglich

Der Schalter „Folien einbetten" ist an, aber es liegen **keine Folien** vor
(weder im Ordner `material/` noch als PDF). Erzeuge die Medien wie üblich und
halte im Curriculum unter „Offene Positionen" fest, dass der Schalter ins
Leere lief.
"""
    # quelle stammt (über stoffquelle -> material/) ggf. aus einem
    # hochgeladenen Dateinamen. projekte._dateiname() entschärft nur
    # Pfad-Traversal, nicht Anführungszeichen/Backticks/$ — die dürfen daher
    # NIE roh in den Bash-Codeblock interpoliert werden. Beide Pfade laufen
    # deshalb als shlex-gequotete Kommandozeilen-Argumente (sys.argv) in den
    # Python-Code, der selbst keine Pfad-Daten mehr enthält.
    quelle_arg = shlex.quote(str(quelle))
    ziel_arg = shlex.quote(str(ziel))
    return f"""
## Folien einbetten (Schalter ist an)

Die Optik der Level kommt aus dem ausgelieferten Foliensatz, nicht aus neu
erzeugten Medien. Grundlage: {quelle}

1. Rendere die Folien einmalig als PNG-Sequenz:

```bash
cd /app && python3 -c "
import sys
from pathlib import Path
import app.folien as folien
bilder = folien.exportiere(Path(sys.argv[1]), Path(sys.argv[2]))
print(len(bilder), 'Folien gerendert')
" {quelle_arg} {ziel_arg}
```

2. Binde die entstandenen `folie-NN.png` als Data-URI in die Lerneinheit ein —
   je Level die Folien, die den Stoff dieses Levels tragen.
3. **Für die Level keine Bilder erzeugen** und keine Filme anfordern: Der
   Foliensatz ist die Optik. Voiceover und Animationen bleiben erlaubt.
4. Halte im Curriculum fest, welche Folie zu welchem Level gehört.
"""


def pruefung_prompt(projekt_dir: Path, bestehensgrenze: int = 70) -> str:
    """Arbeitsauftrag: pruefung.json aus dem ausgelieferten Stoff.

    Schema als Literal, absoluter Zielpfad, „nur JSON“ — dieselbe Bauart wie
    kostenplan_prompt. Eine erzwungene Datei ist nötig, weil der Abschluss-Check
    im curriculum.md in wechselnden Notationen steht.
    """
    quelle = stoffquelle(projekt_dir)
    schema = f"""
{{
  "titel": "Abschlussprüfung <Thema>",
  "bestehensgrenze": {bestehensgrenze},
  "fragen": [
    {{"frage": "vollständig ausformulierte Frage auf Deutsch",
     "optionen": ["Antwort A", "Antwort B", "Antwort C", "Antwort D"],
     "richtig": 0,
     "thema": "Level 3",
     "hinweis": "Ein Satz, warum das die richtige Antwort ist."}}
  ]
}}
"""
    if quelle is not None:
        grundlage = f"""Lies zuerst {quelle} vollständig. **Das ist der Stoff,
der behandelt wurde, und die alleinige Grundlage der Prüfung.**

Lies danach {projekt_dir / 'curriculum.md'} — aber nur, um die Gliederung zu kennen
und jede Frage einem Level zuzuordnen. Inhalte, die dort stehen und in
{quelle.name} fehlen, sind NICHT Stoff und dürfen nicht gefragt werden."""
        stoff_regeln = f"""- **Jede Frage muss sich aus {quelle.name} allein beantworten lassen.**
  Prüfe das für jede einzelne Frage, bevor du sie aufnimmst: Steht die
  richtige Antwort dort? Wenn nein, verwirf die Frage. Kein Vorwissen, keine
  Ergänzung aus eigener Kenntnis, nichts aus der Recherche — auch dann nicht,
  wenn es fachlich richtig wäre.
- Was mündlich ergänzt wurde, steht dir nicht zur Verfügung und ist kein Stoff.
- Lieber weniger Fragen als eine, die im Material nicht gedeckt ist.
- 10 bis 15 Fragen, verteilt über die Level, die in {quelle.name} tatsächlich
  vorkommen — ein dort nicht behandeltes Level bleibt ohne Frage."""
    else:
        grundlage = f"""Lies {projekt_dir / 'curriculum.md'} vollständig — alle
Level mit ihren Lernzielen und Merksätzen.

ACHTUNG: Es liegt weder eine hochgeladene Präsentation noch eine erzeugte
Lerneinheit vor. Du arbeitest deshalb auf dem Lernplan statt auf dem
ausgelieferten Material. Halte dich streng an das, was im Plan steht."""
        stoff_regeln = """- 10 bis 15 Fragen, über alle Level verteilt. Kein Level ohne Frage.
- Frage nur ab, was im Curriculum ausformuliert ist — nichts aus eigener
  Kenntnis ergänzen."""

    return f"""Du bist der Prüfungs-Agent der App „SmartCon-Schulungen". Dein
Arbeitsverzeichnis ist der Projektordner: {projekt_dir}

{grundlage}

Erstelle daraus die Abschlussprüfung und schreibe sie als maschinenlesbare
JSON-Datei {projekt_dir / 'pruefung.json'} — exakt in diesem Schema:
{schema}
Regeln:
{stoff_regeln}
- „optionen“ hat drei bis fünf Einträge. „richtig“ ist der nullbasierte Zeiger
  auf die richtige Option — genau eine Antwort ist richtig, Mehrfachauswahl
  gibt es nicht.
- Die Ablenker müssen plausibel sein: falsche Antworten, die jemand ohne die
  Schulung für richtig halten könnte. Keine absurden Optionen und keine, die
  sich schon durch ihre Länge verraten.
- „thema“ nennt das Level, auf das sich die Frage bezieht („Level 3“).
- „hinweis“ ist ein Satz Begründung, der nach der Auswertung gezeigt wird.
- „bestehensgrenze“ ist {bestehensgrenze}.
- Frage nach Verständnis, nicht nach Wortlaut.
- Alles auf Deutsch, mit korrekten Umlauten.
- Die Datei enthält NUR das JSON: kein Kommentar, kein Markdown, keine Code-Zäune.

Stelle keine Rückfragen. Beende den Lauf mit einer Zeile: Anzahl der Fragen
und die abgedeckten Level."""
