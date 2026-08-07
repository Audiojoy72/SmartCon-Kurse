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
