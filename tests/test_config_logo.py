"""Haus-Logo: liegt neben der config.json, nicht im Repo."""

import pytest

from app import config, preflight

PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)


@pytest.fixture
def logo_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGO_PFAD", tmp_path / "config-logo.png")
    return config.LOGO_PFAD


@pytest.fixture
def kein_host_toolchain(monkeypatch):
    """run_all() prüft nebenbei claude/kimi/ffmpeg/higgsfield/node auf dem
    Host — für einen Logo-Check unnötig und macht den Test vom lokalen
    Toolchain-Stand abhängig (Subprozesse bis zu preflight.TIMEOUT=20s je
    Aufruf). shutil.which auf None zu setzen lässt _check_binary() vor jedem
    Subprozess-Aufruf abbrechen."""
    monkeypatch.setattr(preflight.shutil, "which", lambda name: None)


def test_ohne_datei_kein_logo(logo_tmp):
    assert config.standard_logo() is None


def test_speichern_und_lesen(logo_tmp):
    config.logo_speichern(PNG)
    assert config.standard_logo() == PNG


def test_loeschen_ist_auch_ohne_datei_harmlos(logo_tmp):
    config.logo_loeschen()
    config.logo_speichern(PNG)
    config.logo_loeschen()
    assert config.standard_logo() is None


def test_kein_png_wird_abgewiesen(logo_tmp):
    with pytest.raises(ValueError):
        config.logo_speichern(b"das ist kein PNG")


def test_preflight_meldet_fehlendes_logo(logo_tmp, kein_host_toolchain):
    check = _finde(preflight.run_all(config.DEFAULTS), "logo")
    assert check["status"] == "warn"


def test_preflight_ok_mit_logo(logo_tmp, kein_host_toolchain):
    config.logo_speichern(PNG)
    assert _finde(preflight.run_all(config.DEFAULTS), "logo")["status"] == "ok"


def _finde(checks, check_id):
    return next((c for c in checks if c["id"] == check_id), None)
