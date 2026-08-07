"""Abschlussprüfung: Schema-Validierung und HTML-Ausgabe.

Der Agent liefert pruefung.json. Diese Datei prüft, was ankam, bevor daraus
ein Nachweis wird — ein Zeiger auf eine nicht vorhandene Option macht eine
Frage unlösbar, und das fällt sonst erst dem Teilnehmer auf.
"""

import json
from pathlib import Path

MIN_OPTIONEN = 3
MAX_OPTIONEN = 5


class PruefungFehler(ValueError):
    """Die Datei ist nicht verwendbar. Die Meldung nennt die Fundstelle."""


def laden(pfad: Path) -> dict:
    """Liest und validiert pruefung.json."""
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError as e:
        raise PruefungFehler(f"{pfad.name} nicht lesbar: {e}") from e
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as e:
        raise PruefungFehler(
            f"{pfad.name} ist kein gültiges JSON ({e.msg}, Zeile {e.lineno}). "
            "Häufigste Ursache: Der Agent hat Code-Zäune (```json) mitgeschrieben."
        ) from e
    pruefe(daten)
    return daten


def pruefe(daten: dict) -> None:
    """Wirft PruefungFehler, wenn die Struktur unbrauchbar ist."""
    if not isinstance(daten, dict):
        raise PruefungFehler("Die Datei muss ein JSON-Objekt enthalten")
    if not str(daten.get("titel", "")).strip():
        raise PruefungFehler("„titel“ fehlt oder ist leer")

    grenze = daten.get("bestehensgrenze")
    if not isinstance(grenze, int) or isinstance(grenze, bool) \
            or not 1 <= grenze <= 100:
        raise PruefungFehler(
            "„bestehensgrenze“ muss eine ganze Zahl zwischen 1 und 100 sein")

    fragen = daten.get("fragen")
    if not isinstance(fragen, list) or not fragen:
        raise PruefungFehler("„fragen“ fehlt oder ist leer")

    for nr, frage in enumerate(fragen, start=1):
        _pruefe_frage(nr, frage)


def _pruefe_frage(nr: int, frage) -> None:
    if not isinstance(frage, dict):
        raise PruefungFehler(f"Frage {nr}: kein Objekt")
    if not str(frage.get("frage", "")).strip():
        raise PruefungFehler(f"Frage {nr}: Fragetext fehlt")

    optionen = frage.get("optionen")
    if not isinstance(optionen, list) or not MIN_OPTIONEN <= len(optionen) <= MAX_OPTIONEN:
        raise PruefungFehler(
            f"Frage {nr}: „optionen“ braucht {MIN_OPTIONEN} bis {MAX_OPTIONEN} Einträge")
    if any(not str(o).strip() for o in optionen):
        raise PruefungFehler(f"Frage {nr}: leere Antwortoption")

    richtig = frage.get("richtig")
    if not isinstance(richtig, int) or isinstance(richtig, bool) \
            or not 0 <= richtig < len(optionen):
        raise PruefungFehler(
            f"Frage {nr}: „richtig“ muss auf eine vorhandene Option zeigen "
            f"(0 bis {len(optionen) - 1})")
