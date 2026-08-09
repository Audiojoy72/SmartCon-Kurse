"""Passwörter und Sitzungstoken. Alles aus der Standardbibliothek."""

from app import zugang


def test_erzeugtes_passwort_hat_die_gewuenschte_laenge():
    assert len(zugang.passwort_erzeugen()) == 12
    assert len(zugang.passwort_erzeugen(20)) == 20


def test_passwort_meidet_verwechselbare_zeichen():
    # Wird am Telefon vorgelesen und abgetippt: I, l, 1, O und 0 fehlen.
    zeichen = set("".join(zugang.passwort_erzeugen(40) for _ in range(20)))
    assert not (zeichen & set("Il1O0"))


def test_zwei_passwoerter_sind_verschieden():
    assert zugang.passwort_erzeugen() != zugang.passwort_erzeugen()


def test_hash_enthaelt_die_parameter():
    h = zugang.passwort_hashen("geheim")
    assert h.startswith("scrypt$")
    assert len(h.split("$")) == 6


def test_gleiches_passwort_ergibt_verschiedene_hashes():
    # Salz je Hash — sonst verrät ein Hash, dass zwei Konten dasselbe nutzen.
    assert zugang.passwort_hashen("geheim") != zugang.passwort_hashen("geheim")


def test_richtiges_passwort_wird_erkannt():
    h = zugang.passwort_hashen("geheim")
    assert zugang.passwort_pruefen("geheim", h) is True


def test_falsches_passwort_wird_abgewiesen():
    h = zugang.passwort_hashen("geheim")
    assert zugang.passwort_pruefen("falsch", h) is False
    assert zugang.passwort_pruefen("", h) is False


def test_leerer_hash_ergibt_false_statt_fehler():
    # Ein Teilnehmer ohne Freischaltung hat noch keinen Hash. Ein Login-Versuch
    # darf daran nicht mit einem Serverfehler enden.
    assert zugang.passwort_pruefen("egal", "") is False
    assert zugang.passwort_pruefen("egal", "kaputt") is False
    assert zugang.passwort_pruefen("egal", "scrypt$nicht$zahlen$x$y$z") is False


def test_none_passwort_ergibt_false_statt_fehler():
    # Regression: None aus fehlendem Formfeld oder Datenbank darf nicht zu
    # AttributeError führen.
    h = zugang.passwort_hashen("geheim")
    assert zugang.passwort_pruefen(None, h) is False  # type: ignore


def test_none_hash_ergibt_false_statt_fehler():
    # Regression: None aus fehlender Datenbankfreischaltung darf nicht zu
    # AttributeError führen.
    assert zugang.passwort_pruefen("egal", None) is False  # type: ignore


def test_owasp_scrypt_parameter_verifizieren():
    # Ein mit den aktuellen OWASP-Parametern erstellter Hash muss
    # verifizierbar sein. Regressiontest für maxmem-Fehler.
    h = zugang.passwort_hashen("test-passwort")
    assert h.startswith("scrypt$131072$8$1$")  # N=2**17, R=8, P=1
    assert zugang.passwort_pruefen("test-passwort", h) is True
    assert zugang.passwort_pruefen("falsch", h) is False


def test_token_klartext_und_hash_gehoeren_zusammen():
    klartext, gehasht = zugang.token_erzeugen()
    assert zugang.token_hashen(klartext) == gehasht
    assert klartext != gehasht


def test_token_ist_lang_genug():
    klartext, _ = zugang.token_erzeugen()
    assert len(klartext) >= 32


def test_token_hash_ist_deterministisch():
    # Anders als beim Passwort: der Hash ist der Datenbankschlüssel.
    assert zugang.token_hashen("abc") == zugang.token_hashen("abc")
