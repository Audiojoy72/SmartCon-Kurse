"""Preflight-Ampel. Läuft ohne echte Binaries — geprüft wird die Logik."""

from app import config, preflight


def test_jeder_check_hat_die_pflichtfelder():
    checks = preflight.run_all(config.DEFAULTS)
    assert checks, "run_all darf nie eine leere Liste liefern"
    for c in checks:
        assert set(("id", "name", "status", "detail")) <= set(c)
        assert c["status"] in ("ok", "warn", "fail")


def test_check_ids_sind_eindeutig():
    ids = [c["id"] for c in preflight.run_all(config.DEFAULTS)]
    assert len(ids) == len(set(ids))


def test_design_check_meldet_fehlenden_pfad(tmp_path):
    cfg = {**config.DEFAULTS, "default_design_md": str(tmp_path / "gibt-es-nicht.md")}
    check = _finde(preflight.run_all(cfg), "design")
    assert check["status"] != "ok"
    assert "nicht gefunden" in check["detail"]


def test_design_check_ok_bei_vorhandener_datei(tmp_path):
    datei = tmp_path / "design.md"
    datei.write_text("akzent: \"#c9a84c\"")
    cfg = {**config.DEFAULTS, "default_design_md": str(datei)}
    assert _finde(preflight.run_all(cfg), "design")["status"] == "ok"


def test_ohne_hinterlegten_pfad_gibt_es_keinen_design_check():
    cfg = {**config.DEFAULTS, "default_design_md": ""}
    assert _finde(preflight.run_all(cfg), "design") is None


def _finde(checks, check_id):
    return next((c for c in checks if c["id"] == check_id), None)
