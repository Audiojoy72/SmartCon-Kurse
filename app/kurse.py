"""Kurse, Terminserien und Termine.

Ein Kurs ist das Angebot, eine Serie die Regel („mittwochs, 14-tägig"), ein
Termin die einzelne Durchführung. Termine werden aus der Serie erzeugt und
halten die Platzzahl fest, die zum Zeitpunkt der Erzeugung galt — sonst
würde eine spätere Änderung am Kurs bereits ausgeschriebene Termine
rückwirkend überbuchen.
"""

import re
import sqlite3
from datetime import date, datetime, timedelta

from . import db

STATUS = ("offen", "geschlossen", "abgesagt")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# HH:MM, und zwar mit Bereich: "25:70" passt zwar auf \d\d:\d\d, aber nicht hier.
_UHRZEIT_RE = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")

# Gemeinsames JOIN-Fragment für "belegt" (Anmeldungen ungleich storniert je
# Termin) — von termine() und naechste_offene() genutzt, damit eine
# künftige Änderung der Belegungslogik nur an einer Stelle passiert.
_BELEGT_JOIN = (
    "LEFT JOIN ("
    "  SELECT termin_id, count(*) AS belegt FROM anmeldung "
    "  WHERE status != 'storniert' GROUP BY termin_id"
    ") a ON a.termin_id = t.id "
)

# Welche Felder `anlegen`/`aendern` annehmen. Alles andere wird abgewiesen,
# damit ein Tippfehler nicht stillschweigend ins Leere läuft.
FELDER = ("titel", "beschreibung", "format", "preis_cent", "preis_pauschal",
          "plaetze", "nachweis", "schulung_slug", "aktiv")


class KursFehler(ValueError):
    """Eingabe oder Zustand passt nicht. Die Meldung ist für die Oberfläche."""


def _slug_normalisieren(slug: str) -> str:
    sauber = slug.strip().lower()
    if not _SLUG_RE.match(sauber):
        raise KursFehler(f"„{slug}“ ist kein gültiger Slug")
    return sauber


def anlegen(slug: str, titel: str, **felder) -> int:
    """Legt einen Kurs an und gibt seine id zurück."""
    slug = _slug_normalisieren(slug)
    titel = titel.strip()
    if not titel:
        raise KursFehler("Titel fehlt")

    unbekannt = set(felder) - set(FELDER)
    if unbekannt:
        raise KursFehler(f"Unbekannte Felder: {', '.join(sorted(unbekannt))}")

    spalten = ["slug", "titel"] + list(felder.keys())
    werte = [slug, titel] + list(felder.values())
    platzhalter = ", ".join("?" * len(spalten))

    conn = db.verbinden()
    try:
        cur = conn.execute(
            f"INSERT INTO kurs ({', '.join(spalten)}, angelegt_am) "
            f"VALUES ({platzhalter}, ?)",
            werte + [datetime.now().isoformat(timespec="seconds")])
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise KursFehler(f"„{slug}“ ist bereits angelegt")
    finally:
        conn.close()


def aendern(kurs_id: int, **felder) -> None:
    """Setzt nur die genannten Felder eines Kurses."""
    unbekannt = set(felder) - set(FELDER)
    if unbekannt:
        raise KursFehler(f"Unbekannte Felder: {', '.join(sorted(unbekannt))}")
    if not felder:
        return

    zuweisungen = ", ".join(f"{k} = ?" for k in felder)
    conn = db.verbinden()
    try:
        cur = conn.execute(
            f"UPDATE kurs SET {zuweisungen} WHERE id = ?",
            list(felder.values()) + [kurs_id])
        if cur.rowcount == 0:
            raise KursFehler("Kurs nicht gefunden")
    finally:
        conn.close()


def liste(nur_aktive: bool = False) -> list[dict]:
    """Alle Kurse, optional nur die aktiven."""
    conn = db.verbinden()
    try:
        sql = "SELECT * FROM kurs"
        if nur_aktive:
            sql += " WHERE aktiv = 1"
        sql += " ORDER BY id"
        return [dict(z) for z in conn.execute(sql)]
    finally:
        conn.close()


def kurs(kurs_id: int) -> dict | None:
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM kurs WHERE id = ?", (kurs_id,)).fetchone()
        return dict(zeile) if zeile else None
    finally:
        conn.close()


def kurs_nach_slug(slug: str) -> dict | None:
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM kurs WHERE slug = ?", (slug,)).fetchone()
        return dict(zeile) if zeile else None
    finally:
        conn.close()


def serie_anlegen(kurs_id: int, wochentag: int, uhrzeit: str,
                  dauer_tage: int = 1, rhythmus: int = 1) -> int:
    """Legt die Wiederholungsregel einer Serie an und gibt ihre id zurück.

    Geprüft wird vor dem Schreiben: Die Verbindung ist Autocommit, eine
    angelegte Serie ist also sofort dauerhaft. Ohne Prüfung landete eine
    Serie mit „25:70“ in der Tabelle und erst das nachgelagerte
    `termine_erzeugen()` scheiterte — mit einem ValueError statt KursFehler
    und einer Leiche in der Tabelle.
    """
    if not isinstance(wochentag, int) or isinstance(wochentag, bool) \
            or not 0 <= wochentag <= 6:
        raise KursFehler("Der Wochentag muss eine Zahl von 0 (Montag) bis 6 sein")
    uhrzeit = str(uhrzeit).strip()
    if not _UHRZEIT_RE.match(uhrzeit):
        raise KursFehler(f"„{uhrzeit}“ ist keine gültige Uhrzeit (erwartet HH:MM)")

    conn = db.verbinden()
    try:
        cur = conn.execute(
            "INSERT INTO serie (kurs_id, wochentag, uhrzeit, dauer_tage, "
            "rhythmus) VALUES (?, ?, ?, ?, ?)",
            (kurs_id, wochentag, uhrzeit, dauer_tage, rhythmus))
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise KursFehler("Kurs nicht gefunden")
    finally:
        conn.close()


def termine_erzeugen(serie_id: int, bis: date) -> int:
    """Erzeugt Termine aus der Serie bis einschließlich `bis`.

    Wiederholbar: Ein zweiter Aufruf mit demselben `bis` legt dank
    `UNIQUE (kurs_id, beginn)` + `INSERT OR IGNORE` keine Dubletten an.
    """
    conn = db.verbinden()
    try:
        serie = conn.execute(
            "SELECT * FROM serie WHERE id = ?", (serie_id,)).fetchone()
        if serie is None:
            raise KursFehler("Serie nicht gefunden")
        kurs_zeile = conn.execute(
            "SELECT * FROM kurs WHERE id = ?", (serie["kurs_id"],)).fetchone()
        if kurs_zeile is None:
            raise KursFehler("Kurs nicht gefunden")

        stunde, minute = (int(x) for x in serie["uhrzeit"].split(":"))
        heute = date.today()
        tage_bis_wochentag = (serie["wochentag"] - heute.weekday()) % 7
        naechster = heute + timedelta(days=tage_bis_wochentag)

        eingefuegt = 0
        tag = naechster
        schritt = timedelta(weeks=serie["rhythmus"])
        while tag <= bis:
            beginn = datetime.combine(
                tag, datetime.min.time()).replace(hour=stunde, minute=minute)
            ende = (beginn + timedelta(days=serie["dauer_tage"] - 1)
                     + timedelta(hours=4))
            cur = conn.execute(
                "INSERT OR IGNORE INTO termin (kurs_id, serie_id, beginn, "
                "ende, plaetze) VALUES (?, ?, ?, ?, ?)",
                (serie["kurs_id"], serie_id, beginn.isoformat(),
                 ende.isoformat(), kurs_zeile["plaetze"]))
            eingefuegt += cur.rowcount
            tag += schritt
        return eingefuegt
    finally:
        conn.close()


def termine(kurs_id: int | None = None, ab: datetime | None = None) -> list[dict]:
    """Termine mit `belegt` und `frei`, optional nach Kurs/Zeitraum gefiltert."""
    sql = (
        "SELECT t.*, "
        "coalesce(a.belegt, 0) AS belegt, "
        "t.plaetze - coalesce(a.belegt, 0) AS frei "
        "FROM termin t "
        + _BELEGT_JOIN +
        "WHERE 1 = 1"
    )
    parameter = []
    if kurs_id is not None:
        sql += " AND t.kurs_id = ?"
        parameter.append(kurs_id)
    if ab is not None:
        sql += " AND t.beginn >= ?"
        parameter.append(ab.isoformat())
    sql += " ORDER BY t.beginn"

    conn = db.verbinden()
    try:
        return [dict(z) for z in conn.execute(sql, parameter)]
    finally:
        conn.close()


def termin(termin_id: int) -> dict | None:
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM termin WHERE id = ?", (termin_id,)).fetchone()
        return dict(zeile) if zeile else None
    finally:
        conn.close()


def termin_status(termin_id: int, status: str) -> None:
    if status not in STATUS:
        raise KursFehler(f"Unbekannter Status „{status}“")
    conn = db.verbinden()
    try:
        cur = conn.execute(
            "UPDATE termin SET status = ? WHERE id = ?", (status, termin_id))
        if cur.rowcount == 0:
            raise KursFehler("Termin nicht gefunden")
    finally:
        conn.close()


def naechste_offene(kurs_id: int, anzahl: int = 4) -> list[dict]:
    """Die nächsten künftigen, buchbaren Termine — ohne jede Platzzahl.

    Einzige Funktion dieses Moduls, deren Ergebnis an Fremde geht. Vergangene
    sowie geschlossene/abgesagte Termine tauchen hier gar nicht auf; belegte
    Termine erscheinen mit Status „ausgebucht" statt einer Zahl.
    """
    conn = db.verbinden()
    try:
        zeilen = conn.execute(
            "SELECT t.*, coalesce(a.belegt, 0) AS belegt "
            "FROM termin t "
            + _BELEGT_JOIN +
            "WHERE t.kurs_id = ? AND t.status = 'offen' AND t.beginn > ? "
            "ORDER BY t.beginn LIMIT ?",
            (kurs_id, datetime.now().isoformat(), anzahl)).fetchall()

        ergebnis = []
        for z in zeilen:
            status = "ausgebucht" if z["belegt"] >= z["plaetze"] else "offen"
            ergebnis.append({
                "id": z["id"], "beginn": z["beginn"], "ende": z["ende"],
                "status": status,
            })
        return ergebnis
    finally:
        conn.close()
