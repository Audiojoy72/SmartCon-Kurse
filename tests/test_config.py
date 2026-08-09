"""Speichern und Ausliefern der Konfiguration.

Wichtig ist hier vor allem, was NICHT passieren darf: Zugangsdaten verlieren
oder Zugangsdaten herausgeben.
"""

import json

import pytest

from app import config


@pytest.fixture
def config_tmp(tmp_path, monkeypatch):
    """Leitet die config.json auf eine temporäre Datei um."""
    pfad = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_PATH", pfad)
    return pfad


def test_speichern_behaelt_felder_die_das_formular_nicht_kennt(config_tmp):
    """Das Einstellungsformular kennt keine SMTP-Felder — sie dürfen bleiben."""
    config_tmp.write_text(json.dumps({
        "smtp_host": "mail.example.org", "smtp_user": "post@example.org",
        "smtp_passwort": "geheim", "smtp_von": "post@example.org",
        "portal_url": "https://portal.example.org",
    }), encoding="utf-8")

    config.save({"backend": "kimi", "whisper_command": "whisper"})

    danach = json.loads(config_tmp.read_text(encoding="utf-8"))
    assert danach["backend"] == "kimi"
    assert danach["smtp_host"] == "mail.example.org"
    assert danach["smtp_user"] == "post@example.org"
    assert danach["smtp_passwort"] == "geheim"
    assert danach["smtp_von"] == "post@example.org"
    assert danach["portal_url"] == "https://portal.example.org"


def test_speichern_setzt_genannte_felder_auch_auf_leer(config_tmp):
    """„Behalten" gilt nur für fehlende Schlüssel, nicht für leere Werte."""
    config_tmp.write_text(json.dumps({"whisper_api_url": "https://alt/v1"}),
                          encoding="utf-8")
    config.save({"whisper_api_url": ""})
    assert json.loads(config_tmp.read_text(encoding="utf-8"))["whisper_api_url"] == ""


def test_geheimnisse_gehen_maskiert_hinaus(config_tmp):
    gesetzt = {"whisper_api_key": "sk-echt", "cf_access_client_secret": "cf-echt",
               "smtp_passwort": "geheim", "cf_access_client_id": "id-ist-oeffentlich"}
    sichtbar = config.maskiert({**config.DEFAULTS, **gesetzt})
    for feld in config.GEHEIME_FELDER:
        assert sichtbar[feld] == config.MASKE
    assert sichtbar["cf_access_client_id"] == "id-ist-oeffentlich"


def test_leere_geheimnisse_bleiben_leer(config_tmp):
    """Sonst sähe ein nie gesetzter Schlüssel aus, als wäre er hinterlegt."""
    assert config.maskiert(dict(config.DEFAULTS))["whisper_api_key"] == ""


def test_zurueckgeschickte_maske_ueberschreibt_nichts(config_tmp):
    config_tmp.write_text(json.dumps({
        "whisper_api_key": "sk-echt", "cf_access_client_secret": "cf-echt",
        "smtp_passwort": "geheim"}), encoding="utf-8")

    clean = config.save({"whisper_api_key": config.MASKE,
                         "cf_access_client_secret": config.MASKE,
                         "smtp_passwort": config.MASKE})

    assert clean["whisper_api_key"] == "sk-echt"
    assert clean["cf_access_client_secret"] == "cf-echt"
    assert clean["smtp_passwort"] == "geheim"
    danach = json.loads(config_tmp.read_text(encoding="utf-8"))
    assert danach["whisper_api_key"] == "sk-echt"


def test_ein_neues_geheimnis_wird_gespeichert(config_tmp):
    config_tmp.write_text(json.dumps({"whisper_api_key": "sk-alt"}),
                          encoding="utf-8")
    config.save({"whisper_api_key": "sk-neu"})
    assert json.loads(config_tmp.read_text(encoding="utf-8"))["whisper_api_key"] \
        == "sk-neu"


def test_die_config_route_nennt_kein_geheimnis(client, monkeypatch):
    """GET /api/config ging bisher im Klartext heraus."""
    monkeypatch.setattr(config, "load", lambda: {
        **config.DEFAULTS, "whisper_api_key": "sk-echt",
        "cf_access_client_secret": "cf-echt", "smtp_passwort": "geheim"})
    antwort = client.get("/api/config").json()
    assert "sk-echt" not in json.dumps(antwort)
    assert "cf-echt" not in json.dumps(antwort)
    assert "geheim" not in json.dumps(antwort)
    assert antwort["whisper_api_key"] == config.MASKE
