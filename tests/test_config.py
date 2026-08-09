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
