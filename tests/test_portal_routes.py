"""Portal-Routen. Der Schwerpunkt liegt auf der Zugriffskontrolle."""

import json
import re

from tests.conftest import _anmelden

ALLES_RICHTIG = {"f0": "0", "f1": "1", "f2": "2", "f3": "0"}
ALLES_FALSCH = {"f0": "1", "f1": "0", "f2": "0", "f3": "1"}


def test_ohne_anmeldung_fuehrt_alles_zum_login(portal_umgebung):
    c = portal_umgebung
    for weg in ("/portal/kurse", f"/portal/kurs/{c.anna['teilnahme']}",
                f"/portal/kurs/{c.anna['teilnahme']}/pruefung",
                f"/portal/kurs/{c.anna['teilnahme']}/zertifikat"):
        antwort = c.get(weg, follow_redirects=False)
        assert antwort.status_code == 302, weg
        assert antwort.headers["location"] == "/portal"


def test_login_seite_ist_ohne_anmeldung_erreichbar(portal_umgebung):
    antwort = portal_umgebung.get("/portal")
    assert antwort.status_code == 200
    assert 'name="passwort"' in antwort.text


def test_falsches_passwort_setzt_kein_cookie(portal_umgebung):
    antwort = _anmelden(portal_umgebung, "anna@example.org", "falsch")
    assert antwort.status_code == 200
    assert "sitzung" not in antwort.cookies
    assert "E-Mail oder Passwort" in antwort.text


def test_unbekannte_adresse_bekommt_dieselbe_meldung(portal_umgebung):
    # Sonst ist die Login-Maske ein Kundenverzeichnis.
    falsch = _anmelden(portal_umgebung, "anna@example.org", "falsch").text
    unbekannt = _anmelden(portal_umgebung, "niemand@example.org", "x").text
    assert "E-Mail oder Passwort" in falsch
    assert "E-Mail oder Passwort" in unbekannt


def test_richtiges_passwort_meldet_an(portal_umgebung):
    c = portal_umgebung
    antwort = _anmelden(c, c.anna["email"], c.anna["passwort"])
    assert antwort.status_code == 302
    assert antwort.headers["location"] == "/portal/kurse"
    keks = antwort.headers["set-cookie"]
    assert "HttpOnly" in keks
    assert "SameSite=Lax" in keks


def test_kursliste_zeigt_nur_die_eigenen_kurse(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    text = c.get("/portal/kurse").text
    assert "KI-Pflichtschulung" in text
    assert f'/portal/kurs/{c.anna["teilnahme"]}' in text
    assert f'/portal/kurs/{c.bodo["teilnahme"]}' not in text


def test_fremder_kurs_ist_404_nicht_403(portal_umgebung):
    # 403 würde bestätigen, dass es die Teilnahme gibt.
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    assert c.get(f"/portal/kurs/{c.bodo['teilnahme']}").status_code == 404
    assert c.get(f"/portal/kurs/{c.bodo['teilnahme']}/pruefung").status_code == 404
    assert c.get(f"/portal/kurs/{c.bodo['teilnahme']}/datei").status_code == 404


def test_abgelaufenes_fenster_ist_403(portal_umgebung):
    from datetime import datetime, timedelta, timezone

    from app import db

    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    conn = db.verbinden()
    conn.execute("UPDATE teilnahme SET gueltig_bis = ? WHERE id = ?",
                 ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                  c.anna["teilnahme"]))
    conn.close()

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}")
    assert antwort.status_code == 403
    assert "abgelaufen" in antwort.json()["detail"].lower()


def test_abmelden_entwertet_die_sitzung_serverseitig(portal_umgebung):
    c = portal_umgebung
    antwort = _anmelden(c, c.anna["email"], c.anna["passwort"])
    token = antwort.cookies["sitzung"]

    c.get("/portal/abmelden", follow_redirects=False)
    # Auch mit dem alten Token von Hand: die Sitzung ist weg.
    c.cookies.set("sitzung", token)
    assert c.get("/portal/kurse", follow_redirects=False).status_code == 302


def test_lerneinheit_wird_ausgeliefert(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/datei")
    assert antwort.status_code == 200
    assert "Lerneinheit" in antwort.text
    assert "private" in antwort.headers.get("cache-control", "")


def test_lerneinheit_traegt_eine_csp_die_netzwerkzugriff_verbietet(portal_umgebung):
    """Critical 1: same-origin iframe darf nicht die Werkstatt-API erreichen.

    `connect-src 'none'` ist die tragende Direktive — sie unterbindet
    fetch/XHR/WebSocket aus der agent-generierten Lerneinheit heraus, ohne
    `sandbox` zu setzen (das würde `allow-same-origin` und damit
    localStorage kosten).
    """
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/datei")
    csp = antwort.headers.get("content-security-policy", "")
    assert "connect-src 'none'" in csp
    assert "form-action 'none'" in csp
    assert "frame-ancestors 'self'" in csp
    # Ohne das würde style-src auf default-src zurückfallen (kein
    # unsafe-inline dort) und den <style>-Block der Lerneinheit komplett
    # blocken — im Browser gegen eine echte Schulung nachgewiesen.
    assert "style-src 'unsafe-inline'" in csp


def test_pruefungsseite_enthaelt_keine_loesung(portal_umgebung, projekte_tmp):
    """Die wichtigste Zusicherung des Portals.

    Ein reiner Wortfilter ("richtig" not in seite) würde eine Implementierung
    durchlassen, die die richtige Option z. B. mit `class="k"` markiert oder
    die Optionen so sortiert, dass Index 0 immer stimmt. Deshalb wird hier
    strukturell geprüft: alle Options-Labels einer Frage müssen bis auf Text
    und value identisch aufgebaut sein, und die Reihenfolge muss der aus
    pruefung.json entsprechen — dann lässt sich der richtige Index aus dem
    Markup nicht rekonstruieren.
    """
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    seite = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung").text

    daten = json.loads((projekte_tmp / "kurs" / "pruefung.json").read_text())
    for frage in daten["fragen"]:
        assert frage["hinweis"] not in seite
    # Die Fragen und Optionen sind da — nur eben ohne Auszeichnung.
    assert "Frage eins?" in seite

    # Strukturelle Prüfung: Für jede Frage ein Label je Option, in der
    # Reihenfolge der Quelldatei, ohne irgendeine Option auszuzeichnen.
    label_re = re.compile(
        r'<label class="option">'
        r'<input type="radio" name="f(\d+)" value="(\d+)" required> '
        r'<span>([^<]*)</span></label>')
    treffer = label_re.findall(seite)
    assert treffer, "keine Options-Labels gefunden"

    by_frage: dict[int, list[tuple[int, str]]] = {}
    for fnr, wert, text in treffer:
        by_frage.setdefault(int(fnr), []).append((int(wert), text))

    assert len(by_frage) == len(daten["fragen"])
    for nr, frage in enumerate(daten["fragen"]):
        gefunden = by_frage[nr]
        # Gleiche Anzahl, aufsteigende values, Text und Reihenfolge wie im
        # Quell-JSON — keine Umsortierung, kein bevorzugtes Markup für die
        # richtige Option.
        assert [w for w, _ in gefunden] == list(range(len(frage["optionen"])))
        assert [t for _, t in gefunden] == frage["optionen"]
    # Jedes Label folgt exakt demselben Muster (ein einziger Regex mit fixer
    # Struktur hat oben schon alle Treffer erfasst) — es gibt also keine
    # Variante mit zusätzlicher Klasse, zusätzlichem Attribut o. Ä. für genau
    # eine Option.
    assert seite.count('<label class="option">') == len(treffer)


def test_pruefung_bestehen_und_zertifikat(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")

    ergebnis = c.post(f"/portal/kurs/{c.anna['teilnahme']}/pruefung",
                      data=ALLES_RICHTIG)
    assert ergebnis.status_code == 200
    assert "100" in ergebnis.text
    assert "zertifikat" in ergebnis.text.lower()

    nachweis = c.get(f"/portal/kurs/{c.anna['teilnahme']}/zertifikat")
    assert nachweis.status_code == 200
    assert "Anna Beispiel" in nachweis.text
    assert "AI-SmartCon-Zertifikat" in nachweis.text


def test_zertifikat_vor_dem_bestehen_ist_404(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    assert c.get(f"/portal/kurs/{c.anna['teilnahme']}/zertifikat").status_code == 404


def test_der_vierte_versuch_wird_abgewiesen(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    for _ in range(3):
        c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
        c.post(f"/portal/kurs/{c.anna['teilnahme']}/pruefung", data=ALLES_FALSCH)

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert antwort.status_code == 409
    assert "aufgebraucht" in antwort.json()["detail"].lower()


def test_nach_bestehen_keine_weitere_pruefung(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    c.post(f"/portal/kurs/{c.anna['teilnahme']}/pruefung", data=ALLES_RICHTIG)

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert antwort.status_code == 409
    assert "bestanden" in antwort.json()["detail"].lower()


def test_neuladen_der_pruefung_verbraucht_keinen_versuch(portal_umgebung):
    from app import versuche

    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    for _ in range(3):
        c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert versuche.zaehlen(c.anna["teilnahme"]) == 1


def test_fremde_pruefung_kann_nicht_abgegeben_werden(portal_umgebung):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    antwort = c.post(f"/portal/kurs/{c.bodo['teilnahme']}/pruefung",
                     data=ALLES_RICHTIG)
    assert antwort.status_code == 404


def test_pruefung_ohne_projektordner_ist_404(portal_umgebung, projekte_tmp):
    """Der Projektordner kann verschwunden sein (`DELETE /api/projekte/…`
    kennt keinen Papierkorb) — die Teilnahme in der Datenbank bleibt.
    """
    import shutil

    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    shutil.rmtree(projekte_tmp / "kurs")

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert antwort.status_code == 404


def test_pruefung_mit_kaputter_datei_ist_409(portal_umgebung, projekte_tmp):
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    (projekte_tmp / "kurs" / "pruefung.json").write_text("kein json", encoding="utf-8")

    antwort = c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert antwort.status_code == 409
    assert "nicht zur Verfügung" in antwort.json()["detail"]


def test_pruefung_mit_kaputter_datei_verbraucht_keinen_versuch(
        portal_umgebung, projekte_tmp):
    from app import versuche

    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    (projekte_tmp / "kurs" / "pruefung.json").write_text("kein json", encoding="utf-8")

    c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    assert versuche.zaehlen(c.anna["teilnahme"]) == 0


def test_pruefung_abgeben_mit_kaputter_datei_ist_409(portal_umgebung, projekte_tmp):
    """Die Datei kann zwischen Start und Abgabe der Prüfung kaputt gehen."""
    c = portal_umgebung
    _anmelden(c, c.anna["email"], c.anna["passwort"])
    c.get(f"/portal/kurs/{c.anna['teilnahme']}/pruefung")
    (projekte_tmp / "kurs" / "pruefung.json").write_text("kein json", encoding="utf-8")

    antwort = c.post(f"/portal/kurs/{c.anna['teilnahme']}/pruefung",
                     data=ALLES_RICHTIG)
    assert antwort.status_code == 409
    assert "nicht zur Verfügung" in antwort.json()["detail"]


def test_secure_cookie_ist_im_produktions_default_an(portal_umgebung, monkeypatch):
    """Regressionsschutz: Der `client`-Fixture-Test läuft mit abgeschaltetem
    `portal_secure_cookie` (httpx sendet Secure-Cookies nicht über http
    zurück). Damit ein umgekippter Produktions-Default nicht unbemerkt
    bliebe, prüft dieser Test mit dem echten `config.DEFAULTS` direkt gegen
    den gesetzten `Set-Cookie`-Header.
    """
    from app import config

    c = portal_umgebung
    monkeypatch.setattr(config, "load", lambda: dict(config.DEFAULTS))
    antwort = _anmelden(c, c.anna["email"], c.anna["passwort"])
    assert "Secure" in antwort.headers["set-cookie"]
