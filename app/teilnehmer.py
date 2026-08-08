"""Teilnehmer, ihre Teilnahmen und der Zugang zum Portal.

Ein Teilnehmer entsteht in der Verwaltung, bekommt eine oder mehrere
Teilnahmen zugeordnet und wird dann freigeschaltet. Erst dabei entsteht ein
Passwort — vorher ist `passwort_hash` leer, und ein Login-Versuch scheitert.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

from . import db, zugang

SITZUNG_STUNDEN = 24

# Fester Dummy-Hash für Login-Versuche mit unbekannter E-Mail: `anmelden()`
# lässt scrypt auch dann laufen, damit die Antwortzeit nicht verrät, ob die
# Adresse existiert. Einmal beim Modulimport erzeugt (nicht als Konstante im
# Quelltext, nicht neu pro Aufruf — beides würde entweder ein festes Timing-
# Ziel bieten oder die Kosten jedes Logins verdoppeln).
_DUMMY_PASSWORT_HASH = zugang.passwort_hashen(zugang.passwort_erzeugen())


class TeilnehmerFehler(ValueError):
    """Eingabe oder Zustand passt nicht. Die Meldung ist für die Oberfläche."""


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _iso(zeitpunkt: datetime) -> str:
    return zeitpunkt.isoformat(timespec="seconds")


def _email_normalisieren(email: str) -> str:
    if not isinstance(email, str):
        raise TeilnehmerFehler("E-Mail fehlt")
    sauber = email.strip().lower()
    if not sauber:
        raise TeilnehmerFehler("E-Mail fehlt")
    if "@" not in sauber or sauber.startswith("@") or sauber.endswith("@"):
        raise TeilnehmerFehler("Das ist keine gültige E-Mail-Adresse")
    return sauber


def anlegen(email: str, name: str, firma: str = "") -> int:
    """Legt einen Teilnehmer ohne Zugang an und gibt seine id zurück."""
    email = _email_normalisieren(email)
    name = name.strip()
    if not name:
        raise TeilnehmerFehler("Name fehlt")

    conn = db.verbinden()
    try:
        cur = conn.execute(
            "INSERT INTO teilnehmer (email, name, firma, angelegt_am) "
            "VALUES (?, ?, ?, ?)",
            (email, name, firma.strip(), _iso(_jetzt())))
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise TeilnehmerFehler(f"„{email}“ ist bereits angelegt")
    finally:
        conn.close()


def teilnahme_anlegen(teilnehmer_id: int, slug: str, titel: str,
                      nachweis: str) -> int:
    """Ordnet einem Teilnehmer eine Schulung zu. Noch ohne Freischaltung."""
    conn = db.verbinden()
    try:
        cur = conn.execute(
            "INSERT INTO teilnahme (teilnehmer_id, slug, titel, nachweis) "
            "VALUES (?, ?, ?, ?)",
            (teilnehmer_id, slug, titel, nachweis))
        return cur.lastrowid
    except sqlite3.IntegrityError as e:
        if "FOREIGN KEY" in str(e):
            raise TeilnehmerFehler("Teilnehmer nicht gefunden")
        raise TeilnehmerFehler("Diese Schulung ist dem Teilnehmer bereits zugeordnet")
    finally:
        conn.close()


def liste() -> list[dict]:
    """Alle Teilnehmer mit ihren Teilnahmen, neueste zuerst."""
    conn = db.verbinden()
    try:
        eintraege = []
        for t in conn.execute(
                "SELECT * FROM teilnehmer ORDER BY angelegt_am DESC"):
            teilnahmen = [dict(z) for z in conn.execute(
                "SELECT * FROM teilnahme WHERE teilnehmer_id = ? ORDER BY id",
                (t["id"],))]
            for tn in teilnahmen:
                tn["offen"] = teilnahme_offen(tn)
            eintraege.append({
                "id": t["id"], "email": t["email"], "name": t["name"],
                "firma": t["firma"], "angelegt_am": t["angelegt_am"],
                "hat_zugang": bool(t["passwort_hash"]),
                "teilnahmen": teilnahmen,
            })
        return eintraege
    finally:
        conn.close()


def freischalten(teilnehmer_id: int, tage: int = 30) -> str:
    """Erzeugt ein Passwort, öffnet alle Teilnahmen und gibt den Klartext zurück.

    Der Klartext wird nirgends gespeichert. Wer ihn verliert, bekommt ein
    neues Passwort — dasselbe kann niemand wiederherstellen.

    db.verbinden() öffnet im Autocommit-Modus (isolation_level=None); ein
    `with conn:` würde hier keine Transaktion aufspannen. Beide Schreib-
    vorgänge (Passwort setzen, Zugangsfenster öffnen) laufen deshalb in
    einer expliziten BEGIN/COMMIT-Klammer — schlägt der zweite fehl, macht
    das ROLLBACK auch den ersten wieder rückgängig.
    """
    passwort = zugang.passwort_erzeugen()
    bis = _iso(_jetzt() + timedelta(days=tage))

    conn = db.verbinden()
    try:
        conn.execute("BEGIN")
        cur = conn.execute(
            "UPDATE teilnehmer SET passwort_hash = ? WHERE id = ?",
            (zugang.passwort_hashen(passwort), teilnehmer_id))
        if cur.rowcount == 0:
            raise TeilnehmerFehler("Teilnehmer nicht gefunden")
        conn.execute(
            "UPDATE teilnahme SET gueltig_bis = ?, freigeschaltet_am = ? "
            "WHERE teilnehmer_id = ?",
            (bis, _iso(_jetzt()), teilnehmer_id))
        conn.execute("COMMIT")
        return passwort
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def verlaengern(teilnahme_id: int, tage: int = 30) -> None:
    """Schiebt das Zugangsfenster einer Teilnahme nach hinten."""
    conn = db.verbinden()
    try:
        cur = conn.execute(
            "UPDATE teilnahme SET gueltig_bis = ? WHERE id = ?",
            (_iso(_jetzt() + timedelta(days=tage)), teilnahme_id))
        if cur.rowcount == 0:
            raise TeilnehmerFehler("Teilnahme nicht gefunden")
    finally:
        conn.close()


def teilnahme_offen(teilnahme: dict) -> bool:
    """True, solange das Zugangsfenster läuft. Ohne Freischaltung: False."""
    bis = teilnahme.get("gueltig_bis")
    if not bis:
        return False
    try:
        return datetime.fromisoformat(bis) > _jetzt()
    except ValueError:
        return False


def anmelden(email: str, passwort: str) -> str | None:
    """Prüft die Zugangsdaten und legt eine Sitzung an. None = abgelehnt.

    Warum keine Unterscheidung zwischen „unbekannt" und „falsches Passwort":
    Die Antwort verrät sonst, welche Adressen Kunde sind — nicht nur über
    den Rückgabewert, sondern auch über die Zeit: scrypt läuft deshalb in
    jedem Fall, auch wenn die E-Mail nicht existiert oder der Teilnehmer
    noch gar nicht freigeschaltet ist (`passwort_hash == ""` — das ist der
    Normalzustand zwischen `anlegen()` und `freischalten()`, kein Randfall).
    """
    try:
        email = _email_normalisieren(email)
    except TeilnehmerFehler:
        return None

    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT id, passwort_hash FROM teilnehmer WHERE email = ?",
            (email,)).fetchone()
        hash_ = (zeile["passwort_hash"] if zeile is not None else "") or _DUMMY_PASSWORT_HASH
        richtig = zugang.passwort_pruefen(passwort, hash_)
        if zeile is None or not richtig:
            return None

        klartext, gehasht = zugang.token_erzeugen()
        conn.execute(
            "INSERT INTO sitzung (token_hash, teilnehmer_id, gueltig_bis) "
            "VALUES (?, ?, ?)",
            (gehasht, zeile["id"],
             _iso(_jetzt() + timedelta(hours=SITZUNG_STUNDEN))))
        return klartext
    finally:
        conn.close()


def sitzung_pruefen(token: str) -> dict | None:
    """Der Teilnehmer zu einem Sitzungstoken, oder None."""
    if not isinstance(token, str) or not token:
        return None
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT t.id, t.email, t.name, t.firma, s.gueltig_bis "
            "FROM sitzung s JOIN teilnehmer t ON t.id = s.teilnehmer_id "
            "WHERE s.token_hash = ?",
            (zugang.token_hashen(token),)).fetchone()
        if zeile is None:
            return None
        try:
            if datetime.fromisoformat(zeile["gueltig_bis"]) <= _jetzt():
                return None
        except ValueError:
            return None
        return {"id": zeile["id"], "email": zeile["email"],
                "name": zeile["name"], "firma": zeile["firma"]}
    finally:
        conn.close()


def abmelden(token: str) -> None:
    """Entwertet eine Sitzung. Ein unbekanntes Token ist kein Fehler."""
    if not isinstance(token, str) or not token:
        return
    conn = db.verbinden()
    try:
        conn.execute("DELETE FROM sitzung WHERE token_hash = ?",
                     (zugang.token_hashen(token),))
    finally:
        conn.close()


def teilnahmen_von(teilnehmer_id: int) -> list[dict]:
    """Die Teilnahmen eines Teilnehmers, mit `offen` je Eintrag."""
    conn = db.verbinden()
    try:
        teilnahmen = [dict(z) for z in conn.execute(
            "SELECT * FROM teilnahme WHERE teilnehmer_id = ? ORDER BY id",
            (teilnehmer_id,))]
        for tn in teilnahmen:
            tn["offen"] = teilnahme_offen(tn)
        return teilnahmen
    finally:
        conn.close()


def teilnahme(teilnahme_id: int, teilnehmer_id: int) -> dict | None:
    """Eine Teilnahme — aber nur, wenn sie diesem Teilnehmer gehört.

    Der Teilnehmer-Bezug ist Teil der Abfrage, nicht eine Prüfung danach:
    So kann keine Route ihn vergessen.
    """
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM teilnahme WHERE id = ? AND teilnehmer_id = ?",
            (teilnahme_id, teilnehmer_id)).fetchone()
        if zeile is None:
            return None
        eintrag = dict(zeile)
        eintrag["offen"] = teilnahme_offen(eintrag)
        return eintrag
    finally:
        conn.close()
