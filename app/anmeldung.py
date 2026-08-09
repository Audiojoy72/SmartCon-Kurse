"""Anmeldungen entgegennehmen und zu Teilnehmern weiterverarbeiten.

Eine Anmeldung entsteht öffentlich (Fremde tragen sich zu einem Kurs/Termin
ein) und wird intern in der Verwaltung weiterbearbeitet: Status setzen, und
nach Zahlungseingang zu einem Teilnehmer mit Portalzugang machen.
"""

import sqlite3
from datetime import datetime, timezone

from . import db, teilnehmer

STATUS = ("neu", "bestaetigt", "bezahlt", "storniert")
# Serverseitige Deckel. Die maxlength-Attribute im Formular sind Bequemlichkeit,
# keine Grenze — ein direkter POST kennt sie nicht.
MAX_NAME = 120
MAX_FIRMA = 120
MAX_NACHRICHT = 2000


class AnmeldungFehler(ValueError):
    """Eingabe oder Zustand passt nicht. Die Meldung ist für die Oberfläche."""


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _email_normalisieren(email: str) -> str:
    if not isinstance(email, str):
        raise AnmeldungFehler("E-Mail fehlt")
    sauber = email.strip().lower()
    if not sauber:
        raise AnmeldungFehler("E-Mail fehlt")
    if "@" not in sauber or sauber.startswith("@") or sauber.endswith("@"):
        raise AnmeldungFehler("Das ist keine gültige E-Mail-Adresse")
    return sauber


def _hat_buchbaren_termin(conn, kurs_id: int) -> bool:
    """Ob der Kurs mindestens einen künftigen, offenen Termin mit Platz hat.

    Dieselbe Auswahl, die `kurse.naechste_offene()` der Kursseite als
    Auswahlliste zeigt — nur als Ja/Nein und ohne Begrenzung auf die
    nächsten vier. Läuft auf der Verbindung des Aufrufers, damit die
    Prüfung im selben `BEGIN IMMEDIATE` liegt wie das Schreiben.
    """
    zeile = conn.execute(
        "SELECT 1 FROM termin t "
        "LEFT JOIN ("
        "  SELECT termin_id, count(*) AS belegt FROM anmeldung "
        "  WHERE status != 'storniert' GROUP BY termin_id"
        ") a ON a.termin_id = t.id "
        "WHERE t.kurs_id = ? AND t.status = 'offen' AND t.beginn > ? "
        "AND coalesce(a.belegt, 0) < t.plaetze LIMIT 1",
        (kurs_id, datetime.now().isoformat())).fetchone()
    return zeile is not None


def annehmen(kurs_id: int, termin_id: int | None, name: str, email: str,
            firma: str = "", nachricht: str = "") -> int:
    """Nimmt eine Anmeldung entgegen und gibt ihre id zurück.

    Die Platzprüfung läuft in `BEGIN IMMEDIATE`: Ohne den Schreib-Lock könnten
    zwei gleichzeitige Anmeldungen beide den letzten Platz sehen und beide
    schreiben.
    """
    name = name.strip()
    if not name:
        raise AnmeldungFehler("Name fehlt")
    if len(name) > MAX_NAME:
        raise AnmeldungFehler("Der Name ist zu lang")
    firma = firma.strip()
    if len(firma) > MAX_FIRMA:
        raise AnmeldungFehler("Der Firmenname ist zu lang")
    email = _email_normalisieren(email)
    if len(nachricht) > MAX_NACHRICHT:
        raise AnmeldungFehler("Die Nachricht ist zu lang")

    conn = db.verbinden()
    try:
        conn.execute("BEGIN IMMEDIATE")
        kurs_zeile = conn.execute(
            "SELECT * FROM kurs WHERE id = ?", (kurs_id,)).fetchone()
        if kurs_zeile is None:
            raise AnmeldungFehler("Kurs nicht gefunden")

        if termin_id is None:
            # Sonst wäre die Platzprüfung mit einem leeren Formularfeld zu
            # umgehen: Ohne Termin gäbe es nichts zu prüfen. Die Terminwahl
            # ist Pflicht, sobald es überhaupt etwas zu wählen gibt — genau
            # dann zeigt die Kursseite auch die Auswahlliste. Gibt es keinen
            # buchbaren Termin (terminloses E-Learning, alles vergeben oder
            # vorbei), bleibt die terminlose Anmeldung zulässig.
            if _hat_buchbaren_termin(conn, kurs_id):
                raise AnmeldungFehler("Bitte einen Termin auswählen.")
        else:
            termin_zeile = conn.execute(
                "SELECT * FROM termin WHERE id = ?", (termin_id,)).fetchone()
            if termin_zeile is None:
                raise AnmeldungFehler("Termin nicht gefunden")
            if termin_zeile["kurs_id"] != kurs_id:
                raise AnmeldungFehler("Der Termin gehört nicht zu diesem Kurs")
            if termin_zeile["status"] != "offen":
                raise AnmeldungFehler("Dieser Termin nimmt keine Anmeldungen an")

            belegt = conn.execute(
                "SELECT count(*) AS n FROM anmeldung "
                "WHERE termin_id = ? AND status != 'storniert'",
                (termin_id,)).fetchone()["n"]
            if belegt >= termin_zeile["plaetze"]:
                raise AnmeldungFehler("Dieser Termin ist ausgebucht")

        cur = conn.execute(
            "INSERT INTO anmeldung (termin_id, kurs_id, name, email, firma, "
            "nachricht, angelegt_am) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (termin_id, kurs_id, name, email, firma, nachricht,
             _jetzt()))
        conn.execute("COMMIT")
        return cur.lastrowid
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def eintrag(anmeldung_id: int) -> dict | None:
    conn = db.verbinden()
    try:
        zeile = conn.execute(
            "SELECT * FROM anmeldung WHERE id = ?", (anmeldung_id,)).fetchone()
        return dict(zeile) if zeile else None
    finally:
        conn.close()


def status_setzen(anmeldung_id: int, status: str) -> None:
    if status not in STATUS:
        raise AnmeldungFehler(f"Unbekannter Status „{status}“")
    conn = db.verbinden()
    try:
        cur = conn.execute(
            "UPDATE anmeldung SET status = ? WHERE id = ?",
            (status, anmeldung_id))
        if cur.rowcount == 0:
            raise AnmeldungFehler("Anmeldung nicht gefunden")
    finally:
        conn.close()


def liste(status: str | None = None) -> list[dict]:
    """Alle Anmeldungen, neueste zuerst, mit `kurs_titel`, `beginn` und
    `termin_status`.

    `termin_status` muss mit: Sonst sieht die Verwaltung einer Anmeldung
    nicht an, dass ihr Termin abgesagt wurde, und schaltet den Zugang guten
    Gewissens frei.
    """
    sql = (
        "SELECT anmeldung.*, kurs.titel AS kurs_titel, termin.beginn AS beginn, "
        "termin.status AS termin_status "
        "FROM anmeldung "
        "LEFT JOIN kurs ON kurs.id = anmeldung.kurs_id "
        "LEFT JOIN termin ON termin.id = anmeldung.termin_id"
    )
    parameter = []
    if status is not None:
        sql += " WHERE anmeldung.status = ?"
        parameter.append(status)
    sql += " ORDER BY anmeldung.angelegt_am DESC, anmeldung.id DESC"

    conn = db.verbinden()
    try:
        return [dict(z) for z in conn.execute(sql, parameter)]
    finally:
        conn.close()


def zu_teilnehmer(anmeldung_id: int) -> tuple[int, str]:
    """Macht aus einer bezahlten Anmeldung einen Teilnehmer mit Portalzugang.

    Legt in einer Transaktion den Teilnehmer an (oder nimmt den vorhandenen
    mit dieser E-Mail), ordnet ihm die Teilnahme des Kurses zu und verknüpft
    die Anmeldung. `teilnehmer.freischalten()` läuft danach, außerhalb dieser
    Transaktion — es hat seine eigene Absicherung.
    """
    conn = db.verbinden()
    try:
        conn.execute("BEGIN IMMEDIATE")
        anmeldung_zeile = conn.execute(
            "SELECT * FROM anmeldung WHERE id = ?", (anmeldung_id,)).fetchone()
        if anmeldung_zeile is None:
            raise AnmeldungFehler("Anmeldung nicht gefunden")
        if anmeldung_zeile["teilnehmer_id"] is not None:
            raise AnmeldungFehler("Diese Anmeldung ist bereits verknüpft")
        if anmeldung_zeile["status"] != "bezahlt":
            raise AnmeldungFehler("Die Anmeldung ist noch nicht bezahlt")

        kurs_zeile = conn.execute(
            "SELECT * FROM kurs WHERE id = ?",
            (anmeldung_zeile["kurs_id"],)).fetchone()
        if kurs_zeile is None or not kurs_zeile["schulung_slug"]:
            raise AnmeldungFehler("Diesem Kurs fehlt die Schulung")

        teilnehmer_zeile = conn.execute(
            "SELECT id FROM teilnehmer WHERE email = ?",
            (anmeldung_zeile["email"],)).fetchone()
        if teilnehmer_zeile is not None:
            teilnehmer_id = teilnehmer_zeile["id"]
        else:
            # Spiegelt teilnehmer.anlegen() (dort UNIQUE auf email — hier
            # per SELECT vorher ausgeschlossen, damit alles in dieser
            # Transaktion bleibt statt über eine zweite Verbindung zu laufen).
            cur = conn.execute(
                "INSERT INTO teilnehmer (email, name, firma, angelegt_am) "
                "VALUES (?, ?, ?, ?)",
                (anmeldung_zeile["email"], anmeldung_zeile["name"],
                 anmeldung_zeile["firma"], _jetzt()))
            teilnehmer_id = cur.lastrowid

        # Spiegelt teilnehmer.teilnahme_anlegen(): FOREIGN KEY ist hier
        # unerreichbar (teilnehmer_id kommt gerade aus dieser Transaktion),
        # nur die UNIQUE(teilnehmer_id, slug)-Verletzung ist erwartbar und
        # kein Fehler — alles andere soll durchschlagen statt zu verschwinden.
        try:
            conn.execute(
                "INSERT INTO teilnahme (teilnehmer_id, slug, titel, nachweis) "
                "VALUES (?, ?, ?, ?)",
                (teilnehmer_id, kurs_zeile["schulung_slug"], kurs_zeile["titel"],
                 kurs_zeile["nachweis"]))
        except sqlite3.IntegrityError as e:
            if "UNIQUE" not in str(e):
                raise
            # Diese Schulung ist dem Teilnehmer bereits zugeordnet.

        conn.execute(
            "UPDATE anmeldung SET teilnehmer_id = ? WHERE id = ?",
            (teilnehmer_id, anmeldung_id))
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

    passwort = teilnehmer.freischalten(teilnehmer_id)
    return teilnehmer_id, passwort
