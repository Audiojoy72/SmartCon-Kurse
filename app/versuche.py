"""Prüfungsversuche eines Teilnehmers.

Die Auswertung passiert hier, auf dem Server. Die richtigen Antworten stehen
in `projects/<slug>/pruefung.json` und verlassen den Server nicht — eine
Prüfung, deren Lösungen im Browser liegen, taugt nicht als Nachweis.
"""

from datetime import datetime, timezone

from . import db, projekte, pruefung

MAX_VERSUCHE = 3


class VersuchFehler(ValueError):
    """Der Versuch ist nicht zulässig. Die Meldung ist für die Oberfläche."""


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def zaehlen(teilnahme_id: int) -> int:
    conn = db.verbinden()
    try:
        return conn.execute(
            "SELECT count(*) AS n FROM versuch WHERE teilnahme_id = ?",
            (teilnahme_id,)).fetchone()["n"]
    finally:
        conn.close()


def bestanden(teilnahme_id: int) -> dict | None:
    """Der bestandene Versuch, falls es einen gibt."""
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM versuch WHERE teilnahme_id = ? AND bestanden = 1 "
            "ORDER BY beendet_am LIMIT 1", (teilnahme_id,)).fetchone()
        return dict(zeile) if zeile else None
    finally:
        conn.close()


def liste(teilnahme_id: int) -> list[dict]:
    conn = db.verbinden()
    try:
        return [dict(z) for z in conn.execute(
            "SELECT * FROM versuch WHERE teilnahme_id = ? ORDER BY id",
            (teilnahme_id,))]
    finally:
        conn.close()


def _offener(conn, teilnahme_id: int):
    return conn.execute(
        "SELECT * FROM versuch WHERE teilnahme_id = ? AND beendet_am IS NULL "
        "ORDER BY id LIMIT 1", (teilnahme_id,)).fetchone()


def starten(teilnahme_id: int) -> int:
    """Beginnt einen Versuch — oder gibt den offenen zurück.

    Ein Neuladen der Prüfungsseite darf keinen Versuch verbrauchen, deshalb
    zählt ein bereits offener Versuch weiter statt einen zweiten anzulegen.
    """
    if bestanden(teilnahme_id):
        raise VersuchFehler("Diese Prüfung ist bereits bestanden")

    conn = db.verbinden()
    try:
        offen = _offener(conn, teilnahme_id)
        if offen:
            return offen["id"]
        anzahl = conn.execute(
            "SELECT count(*) AS n FROM versuch WHERE teilnahme_id = ?",
            (teilnahme_id,)).fetchone()["n"]
        if anzahl >= MAX_VERSUCHE:
            raise VersuchFehler(
                f"Alle {MAX_VERSUCHE} Versuche sind aufgebraucht")
        cur = conn.execute(
            "INSERT INTO versuch (teilnahme_id, begonnen_am) VALUES (?, ?)",
            (teilnahme_id, _jetzt()))
        return cur.lastrowid
    finally:
        conn.close()


def auswerten(versuch_id: int, slug: str, antworten: dict) -> dict:
    """Wertet die Antworten gegen pruefung.json aus und schließt den Versuch.

    `antworten` bildet den Fragenindex als String auf die gewählte Option ab —
    so kommt es aus einem Formular. Fehlende, unbekannte oder unsinnige Werte
    zählen als falsch; ein Formular ohne Antwort darf nicht abstürzen.
    """
    d = projekte.projekt_dir(slug)
    if d is None:
        raise VersuchFehler(f"Schulung „{slug}“ nicht gefunden")
    daten = pruefung.laden(d / "pruefung.json")
    fragen = daten["fragen"]

    conn = db.verbinden()
    try:
        zeile = conn.execute("SELECT * FROM versuch WHERE id = ?",
                             (versuch_id,)).fetchone()
        if zeile is None:
            raise VersuchFehler("Versuch nicht gefunden")
        if zeile["beendet_am"] is not None:
            raise VersuchFehler("Dieser Versuch ist bereits abgeschlossen")

        rueckmeldung = []
        treffer = 0
        for nr, frage in enumerate(fragen):
            gewaehlt = antworten.get(str(nr))
            try:
                gewaehlt = int(gewaehlt)
            except (TypeError, ValueError):
                gewaehlt = None
            korrekt = gewaehlt == frage["richtig"]
            if korrekt:
                treffer += 1
            rueckmeldung.append({
                "frage": frage["frage"],
                "gewaehlt": gewaehlt,
                "richtig": frage["richtig"],
                "korrekt": korrekt,
                "hinweis": str(frage.get("hinweis", "")),
            })

        prozent = round(treffer / len(fragen) * 100)
        geschafft = prozent >= daten["bestehensgrenze"]
        conn.execute(
            "UPDATE versuch SET beendet_am = ?, prozent = ?, bestanden = ? "
            "WHERE id = ?",
            (_jetzt(), prozent, 1 if geschafft else 0, versuch_id))

        return {"prozent": prozent, "bestanden": geschafft, "treffer": treffer,
                "gesamt": len(fragen), "grenze": daten["bestehensgrenze"],
                "rueckmeldung": rueckmeldung}
    finally:
        conn.close()
