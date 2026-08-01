"""Level-Parser — liest die Level-Übersicht-Tabelle aus einem curriculum.md.

Gesucht wird die erste Markdown-Tabelle, deren Kopfzeile die Spalten „Level"
und „Medium" enthält. Tolerant gegen Spaltenreihenfolge, fehlende Spalten
(liefern dann leere Felder), Groß-/Kleinschreibung und Leerzeichen.
Kein Match → leere Liste, kein Fehler.
"""

import re

# Auswahl im Freigabe-Gate (Reihenfolge = Vorrang bei der Normalisierung)
MEDIEN = ("FILM", "ANIMATION", "BILD")

_LEVEL_NR = re.compile(r"^(\d+)")
_TRENNZEILE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def _zellen(zeile: str) -> list[str]:
    """Zerlegt eine Markdown-Tabellenzeile in getrimmte Zellen."""
    zeile = zeile.strip()
    if zeile.startswith("|"):
        zeile = zeile[1:]
    if zeile.endswith("|"):
        zeile = zeile[:-1]
    return [z.strip() for z in zeile.split("|")]


def parse_level(curriculum_md: str) -> list[dict]:
    """Gibt [{level, lernziel, medium, interaktion}] aus der Level-Übersicht.

    „level" ist die führende Nummer der Level-Spalte als String („1", „2", …).
    Zeilen ohne führende Nummer (z. B. „Ende" / Abschluss-Check) werden
    übersprungen. Ohne passende Tabelle: leere Liste.
    """
    zeilen = curriculum_md.splitlines()
    for i, zeile in enumerate(zeilen):
        if "|" not in zeile:
            continue
        kopf = [z.lower() for z in _zellen(zeile)]
        if not any("level" in z for z in kopf):
            continue
        if not any("medium" in z for z in kopf):
            continue
        # Direkt darunter muss die Trennzeile stehen, sonst keine Tabelle
        if i + 1 >= len(zeilen) or not _TRENNZEILE.match(zeilen[i + 1]):
            continue
        idx: dict[str, int] = {}
        for j, z in enumerate(kopf):
            for name in ("level", "lernziel", "medium", "interaktion"):
                if name in z and name not in idx:
                    idx[name] = j
        level = []
        for zeile2 in zeilen[i + 2:]:
            if not zeile2.strip().startswith("|"):
                break  # Ende der Tabelle
            z = _zellen(zeile2)

            def feld(name: str) -> str:
                j = idx.get(name)
                return z[j] if j is not None and j < len(z) else ""

            m = _LEVEL_NR.match(feld("level"))
            if not m:
                continue  # z. B. die „Ende"-Zeile (Abschluss-Check)
            level.append({
                "level": m.group(1),
                "lernziel": feld("lernziel"),
                "medium": feld("medium"),
                "interaktion": feld("interaktion"),
            })
        return level
    return []


def normalisiere_medium(medium: str) -> str:
    """Bildet Freitext aus der Tabelle („ANIMATION + BILD (Hero)") auf die
    Gate-Auswahl (FILM/ANIMATION/BILD) ab. Ohne Treffer: bereinigter Rohwert."""
    m = medium.upper()
    for kandidat in MEDIEN:
        if kandidat in m:
            return kandidat
    return medium.strip().upper()
