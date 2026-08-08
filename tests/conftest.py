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
    monkeypatch.setattr(config, "load", lambda: dict(config.DEFAULTS))

    c = TestClient(main.app)
    c.gestartet = gestartet
    return c
