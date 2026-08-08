"""Passwörter, Sitzungstoken und ihre Prüfung.

Alles aus der Standardbibliothek. `hashlib.scrypt` ist ein anerkanntes
Verfahren zum Ablegen von Passwörtern (RFC 7914); bcrypt oder argon2 wären
zusätzliche Abhängigkeiten ohne Gewinn für diesen Fall.

Dieses Modul kennt weder Datenbank noch HTTP — dadurch ist es ohne
Vorbereitung testbar.
"""

import hashlib
import hmac
import secrets

# Ohne verwechselbare Zeichen: I, l, 1, O und 0 fehlen bewusst. Das Passwort
# wird am Telefon vorgelesen und von Hand abgetippt.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"

# OWASP empfiehlt n=2**17, r=8, p=1. Auf dieser Maschine braucht das ~211 ms
# pro Hash. Der Wert steht im Hash, ältere Passwörter bleiben also prüfbar,
# wenn er steigt. Das hashlib.scrypt()-Speicherlimit muss explizit gesetzt
# werden; OpenSSLs Default (32 MiB) reicht nicht.
SCRYPT_N = 2**17
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 512 * 1024 * 1024  # 512 MiB für N=2**17, r=8
SALZ_LAENGE = 16
SCHLUESSEL_LAENGE = 32


def passwort_erzeugen(laenge: int = 12) -> str:
    """Ein neues Passwort. 12 Zeichen aus diesem Alphabet sind rund 70 Bit."""
    return "".join(secrets.choice(ALPHABET) for _ in range(laenge))


def passwort_hashen(passwort: str) -> str:
    """Ergibt `scrypt$n$r$p$salz$hash`, Salz und Hash hexadezimal."""
    salz = secrets.token_bytes(SALZ_LAENGE)
    abgeleitet = hashlib.scrypt(
        passwort.encode(), salt=salz, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        dklen=SCHLUESSEL_LAENGE, maxmem=SCRYPT_MAXMEM)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salz.hex()}${abgeleitet.hex()}"


def passwort_pruefen(passwort: str, hinterlegt: str) -> bool:
    """Prüft ein Passwort gegen den hinterlegten Hash.

    Ein leeres oder unlesbares Feld ergibt False statt eines Fehlers: Ein
    Teilnehmer ohne Freischaltung hat noch keinen Hash, und ein Login-Versuch
    darf daran nicht mit einem Serverfehler enden.
    """
    # Typ-Sicherung am Eintritt: Das Vertrauen auf die Signatur beim Aufruf
    # ist in der Praxis nicht genug (None aus Datenbank, fehlende Formfelder).
    if not isinstance(passwort, str) or not isinstance(hinterlegt, str):
        return False

    try:
        kennung, n, r, p, salz_hex, hash_hex = hinterlegt.split("$")
        if kennung != "scrypt":
            return False
        abgeleitet = hashlib.scrypt(
            passwort.encode(), salt=bytes.fromhex(salz_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(hash_hex) // 2,
            maxmem=SCRYPT_MAXMEM)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(abgeleitet.hex(), hash_hex)


def token_erzeugen() -> tuple[str, str]:
    """Ein Sitzungstoken: (Klartext fürs Cookie, Hash für die Datenbank)."""
    klartext = secrets.token_urlsafe(32)
    return klartext, token_hashen(klartext)


def token_hashen(token: str) -> str:
    """Der Datenbankschlüssel eines Tokens.

    Anders als beim Passwort ohne Salz: Der Hash muss ohne Zusatzwissen aus
    dem Cookie berechenbar sein. Das Token ist zufällig und kurzlebig, ein
    Wörterbuchangriff auf einen 256-Bit-Zufallswert ist gegenstandslos.
    """
    return hashlib.sha256(token.encode()).hexdigest()
