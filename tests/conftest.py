"""Gemeinsame Fixtures. Kein Test darf den echten projects/-Ordner anfassen."""

import pytest

from app import projekte


@pytest.fixture
def projekte_tmp(tmp_path, monkeypatch):
    """Leitet den Projektordner auf ein temporäres Verzeichnis um.

    monkeypatch statt Zuweisung: Der Wert wird nach jedem Test automatisch
    zurückgesetzt, auch wenn der Test mit einer Ausnahme endet.
    """
    ziel = tmp_path / "projects"
    ziel.mkdir()
    monkeypatch.setattr(projekte, "PROJECTS", ziel)
    return ziel


@pytest.fixture
def client(projekte_tmp, monkeypatch):
    """TestClient mit temporärem Projektordner und ohne echte Agentenläufe."""
    from fastapi.testclient import TestClient

    from app import config, main, runner

    # Kein Test startet je einen echten Agenten: start() wird ersetzt und
    # merkt sich nur, womit es aufgerufen wurde.
    gestartet = []
    monkeypatch.setattr(runner, "start",
                        lambda *a, **kw: gestartet.append((a, kw)))
    monkeypatch.setattr(runner, "laeuft", lambda slug: False)

    # Isoliert von der echten config.json (z. B. lokal gesetztes
    # default_design_md) — Tests, die das brauchen, überschreiben es selbst.
    # portal_secure_cookie aus: Der TestClient spricht http://testserver,
    # und httpx schickt ein `Secure`-Cookie über http nicht zurück — mit dem
    # echten Default bliebe jede Sitzung nach dem Login unsichtbar.
    testkonfig = {**config.DEFAULTS, "portal_secure_cookie": False}
    monkeypatch.setattr(config, "load", lambda: dict(testkonfig))

    c = TestClient(main.app)
    c.gestartet = gestartet
    return c


@pytest.fixture
def portal_umgebung(client, projekte_tmp, tmp_path, monkeypatch):
    """TestClient mit Datenbank, einer fertigen Schulung und zwei Teilnehmern.

    Zwei sind nötig, weil der wichtigste Test ist, dass der eine nicht an die
    Kurse des anderen kommt.
    """
    import json

    from app import db, teilnehmer

    monkeypatch.setattr(db, "DB_PFAD", tmp_path / "kurse.db")
    db.init()

    d = projekte_tmp / "kurs"
    d.mkdir()
    (d / "brief.json").write_text(json.dumps({"thema": "KI-Pflichtschulung"}))
    (d / "status.json").write_text(json.dumps({"phase": "fertig"}))
    (d / "Schulung_KI_2026-08-01.html").write_text(
        "<html><body>Lerneinheit</body></html>", encoding="utf-8")
    (d / "pruefung.json").write_text(json.dumps({
        "titel": "Abschlussprüfung", "bestehensgrenze": 70,
        "fragen": [
            {"frage": "Frage eins?", "optionen": ["a", "b", "c"], "richtig": 0,
             "thema": "Level 1", "hinweis": "Weil a richtig ist."},
            {"frage": "Frage zwei?", "optionen": ["a", "b", "c"], "richtig": 1,
             "thema": "Level 2", "hinweis": "Weil b richtig ist."},
            {"frage": "Frage drei?", "optionen": ["a", "b", "c"], "richtig": 2,
             "thema": "Level 3", "hinweis": "Weil c richtig ist."},
            {"frage": "Frage vier?", "optionen": ["a", "b", "c"], "richtig": 0,
             "thema": "Level 4", "hinweis": "Weil a richtig ist."},
        ]}), encoding="utf-8")

    anna = teilnehmer.anlegen("anna@example.org", "Anna Beispiel", "Beispiel GmbH")
    anna_tn = teilnehmer.teilnahme_anlegen(anna, "kurs", "KI-Pflichtschulung",
                                           "AI-SmartCon-Zertifikat")
    anna_pw = teilnehmer.freischalten(anna)

    bodo = teilnehmer.anlegen("bodo@example.org", "Bodo Beispiel")
    bodo_tn = teilnehmer.teilnahme_anlegen(bodo, "kurs", "KI-Pflichtschulung",
                                           "AI-SmartCon-Zertifikat")
    teilnehmer.freischalten(bodo)

    client.anna = {"id": anna, "teilnahme": anna_tn, "passwort": anna_pw,
                   "email": "anna@example.org"}
    client.bodo = {"id": bodo, "teilnahme": bodo_tn}
    return client


def _anmelden(c, email, passwort):
    """Meldet an und lässt das Cookie im Client. Gibt die Antwort zurück."""
    return c.post("/portal/anmelden",
                  data={"email": email, "passwort": passwort},
                  follow_redirects=False)
