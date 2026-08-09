"""Die öffentlichen Anmelderouten. Schwerpunkt: was Fremde auslösen können."""

from datetime import date, timedelta

import pytest

from app import anmeldung, anmeldung_routes, config, db, kurse

FORMULAR = {"name": "Anna Beispiel", "email": "anna@example.org",
            "firma": "Beispiel GmbH", "nachricht": "Bitte um Rechnung."}


@pytest.fixture
def anmeldeclient(client, tmp_path, monkeypatch):
    """TestClient mit eigener Datenbank, einem Kurs — und ohne echten Versand."""
    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()
    # Die Bremse ist Modulzustand: ohne Rücksetzen färbt ein Test den nächsten.
    monkeypatch.setattr(anmeldung_routes, "_ZUGRIFFE", {})

    gesendet = []
    monkeypatch.setattr(anmeldung_routes.mail, "konfiguriert", lambda: True)
    monkeypatch.setattr(anmeldung_routes.mail, "senden",
                        lambda an, betreff, text: gesendet.append(an))

    kid = kurse.anlegen("ki-pflicht", "KI-Pflichtschulung", plaetze=2,
                        preis_cent=14900, format="E-Learning, 80–90 Min",
                        schulung_slug="ki-pflicht")
    sid = kurse.serie_anlegen(kid, wochentag=2, uhrzeit="09:00")
    kurse.termine_erzeugen(sid, bis=date.today() + timedelta(days=60))

    # Zweiter Kurs ohne jeden Termin: das terminlose E-Learning. Hier ist eine
    # Anmeldung ohne termin_id zulässig — die Tests zur Bremse laufen darüber,
    # damit sie nicht an der Platzzahl des ersten Kurses hängen.
    kurse.anlegen("elearning", "E-Learning jederzeit", plaetze=100,
                  preis_cent=9900, format="E-Learning",
                  schulung_slug="elearning")

    client.kurs = kid
    client.termin = kurse.termine(kid)[0]["id"]
    client.gesendet = gesendet
    return client


def _absenden(c, **felder):
    daten = {**FORMULAR, "termin_id": str(c.termin), **felder}
    return c.post("/anmeldung/ki-pflicht", data=daten)


def _absenden_terminlos(c, **felder):
    """Anmeldung zum terminlosen Kurs — ohne termin_id, und das ist erlaubt."""
    return c.post("/anmeldung/elearning", data={**FORMULAR, **felder})


def test_kursliste_ist_ohne_anmeldung_erreichbar(anmeldeclient):
    antwort = anmeldeclient.get("/anmeldung")
    assert antwort.status_code == 200
    assert "KI-Pflichtschulung" in antwort.text


def test_nur_aktive_kurse_erscheinen(anmeldeclient):
    kurse.aendern(anmeldeclient.kurs, aktiv=False)
    text = anmeldeclient.get("/anmeldung").text
    assert "KI-Pflichtschulung" not in text
    assert anmeldeclient.get("/anmeldung/ki-pflicht").status_code == 404


def test_unbekannter_kurs_ist_404(anmeldeclient):
    assert anmeldeclient.get("/anmeldung/gibts-nicht").status_code == 404


def test_kursseite_nennt_keine_platzzahlen(anmeldeclient):
    text = anmeldeclient.get("/anmeldung/ki-pflicht").text.lower()
    for verboten in ("plätze", "plaetze", "belegt", "frei "):
        assert verboten not in text


def test_anmelden_legt_an_und_dankt(anmeldeclient):
    antwort = _absenden(anmeldeclient)
    assert antwort.status_code == 200
    assert "Rechnung" in antwort.text
    eintraege = anmeldung.liste()
    assert len(eintraege) == 1
    assert eintraege[0]["email"] == "anna@example.org"
    assert eintraege[0]["termin_id"] == anmeldeclient.termin


def test_anmelden_verschickt_eine_bestaetigung(anmeldeclient):
    _absenden(anmeldeclient)
    assert anmeldeclient.gesendet == ["anna@example.org"]


def test_versand_fehler_verliert_die_anmeldung_nicht(anmeldeclient, monkeypatch):
    """Ein klemmendes Postfach kostet einen Anruf, keinen Kunden."""
    def kaputt(*a, **kw):
        raise anmeldung_routes.mail.MailFehler("Postfach antwortet nicht")

    monkeypatch.setattr(anmeldung_routes.mail, "senden", kaputt)
    antwort = _absenden(anmeldeclient)
    assert antwort.status_code == 200
    assert len(anmeldung.liste()) == 1


def test_fehlerhafte_eingabe_zeigt_die_seite_mit_den_werten(anmeldeclient):
    antwort = _absenden(anmeldeclient, email="keine-mail")
    assert antwort.status_code == 400
    assert 'value="Anna Beispiel"' in antwort.text
    assert anmeldung.liste() == []


def test_ausgebucht_zeigt_die_seite_statt_eines_fehlers(anmeldeclient):
    for i in range(2):  # plaetze=2
        _absenden(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org")
    antwort = _absenden(anmeldeclient, name="Zu spät", email="spaet@example.org")
    assert antwort.status_code == 400
    assert "ausgebucht" in antwort.text.lower()


def test_fehlermeldung_nennt_keine_zahlen(anmeldeclient):
    for i in range(2):
        _absenden(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org")
    text = _absenden(anmeldeclient, name="Zu spät", email="spaet@example.org").text
    # Der Kurspreis steht auf der Seite; die Meldung selbst darf nichts zählen.
    meldung = text.split('class="warnung"')[1].split("</p>")[0]
    assert not any(z.isdigit() for z in meldung)


def test_ohne_termin_wird_abgewiesen_wenn_es_offene_gibt(anmeldeclient):
    """Das leere Formularfeld darf die Platzprüfung nicht aushebeln."""
    antwort = _absenden(anmeldeclient, termin_id="")
    assert antwort.status_code == 400
    assert "Termin" in antwort.text
    assert anmeldung.liste() == []


def test_ohne_termin_geht_wenn_alle_termine_vergeben_sind(anmeldeclient):
    """Der Fall, den die Kursseite bewusst anbietet: „trotzdem anmelden"."""
    for t in kurse.termine(anmeldeclient.kurs):
        kurse.termin_status(t["id"], "geschlossen")
    antwort = _absenden(anmeldeclient, termin_id="")
    assert antwort.status_code == 200
    assert anmeldung.liste()[0]["termin_id"] is None


def test_ohne_termin_geht_beim_terminlosen_kurs(anmeldeclient):
    assert _absenden_terminlos(anmeldeclient).status_code == 200


def test_zu_viele_anmeldungen_werden_gebremst(anmeldeclient):
    for i in range(anmeldung_routes.RATE_MAX):
        antwort = _absenden_terminlos(anmeldeclient, name=f"P{i}",
                                      email=f"p{i}@example.org")
        assert antwort.status_code == 200, i
    letzte = _absenden_terminlos(anmeldeclient, name="Zuviel",
                                 email="zuviel@example.org")
    assert letzte.status_code == 429
    assert len(anmeldung.liste()) == anmeldung_routes.RATE_MAX


def test_die_bremse_gilt_je_absender(anmeldeclient, monkeypatch):
    monkeypatch.setattr(anmeldung_routes.config, "load",
                        lambda: {**config.DEFAULTS, "proxy_kopf_vertrauen": True})
    for i in range(anmeldung_routes.RATE_MAX):
        _absenden_terminlos(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org")
    andere = anmeldeclient.post("/anmeldung/elearning", data=FORMULAR,
                                headers={"CF-Connecting-IP": "203.0.113.9"})
    assert andere.status_code == 200


def test_ohne_vertrauen_zaehlt_der_proxy_kopf_nicht(anmeldeclient):
    """Default: `CF-Connecting-IP` darf die Bremse nicht abschalten."""
    for i in range(anmeldung_routes.RATE_MAX):
        _absenden_terminlos(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org")
    andere = anmeldeclient.post("/anmeldung/elearning", data=FORMULAR,
                                headers={"CF-Connecting-IP": "203.0.113.9"})
    assert andere.status_code == 429


def test_die_bremse_zaehlt_nur_erfolgreiche_anmeldungen(anmeldeclient):
    """Wer sich vertippt, soll sich nicht selbst aussperren."""
    for _ in range(anmeldung_routes.RATE_MAX + 3):
        assert _absenden_terminlos(anmeldeclient,
                                   email="keine-mail").status_code == 400
    assert _absenden_terminlos(anmeldeclient).status_code == 200


def test_gebremste_anfrage_verschickt_nichts(anmeldeclient):
    for i in range(anmeldung_routes.RATE_MAX + 3):
        _absenden_terminlos(anmeldeclient, name=f"P{i}", email=f"p{i}@example.org")
    assert len(anmeldeclient.gesendet) == anmeldung_routes.RATE_MAX


def test_der_slug_kann_nicht_aus_dem_bereich_ausbrechen(anmeldeclient):
    """%2f wird im Pfadparameter dekodiert — der Slug darf trotzdem nur ein Slug sein."""
    antwort = anmeldeclient.get("/anmeldung/%2e%2e%2fapi%2fverwaltung%2fteilnehmer")
    assert antwort.status_code == 404
    assert "teilnehmer" not in antwort.text.lower()


def test_der_router_hat_nur_diese_drei_wege(anmeldeclient):
    from app import main
    # fastapi==0.141.1 hält Routen aus include_router() als _IncludedRouter
    # in app.routes vor (kein .path) und löst sie erst bei Bedarf auf — mit
    # derselben Funktion, die FastAPI intern für /openapi.json nutzt.
    from fastapi.routing import iter_route_contexts

    wege = {rc.path for rc in iter_route_contexts(main.app.routes)
            if rc.path and rc.path.startswith("/anmeldung")}
    assert wege == {"/anmeldung", "/anmeldung/{slug}"}
