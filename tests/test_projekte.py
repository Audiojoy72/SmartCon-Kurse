"""Projektordner: Slugs, Dateinamen, Anlegen, Löschen."""

import json

from app import projekte

BRIEF = {
    "thema": "Cyber Resilience Act",
    "lernziele": "Pflichten kennen",
    "zielgruppe": "KMU",
    "sprache": "Deutsch",
    "dauer": "60 Minuten",
    "stil": "kostenlos",
    "ki_medien": False,
}


def test_slugify_wandelt_umlaute_und_sonderzeichen():
    assert projekte.slugify("Über Größe & Maß") == "ueber-groesse-mass"
    assert projekte.slugify("  Mehrere   Wörter  ") == "mehrere-woerter"
    assert projekte.slugify("!!!") == "projekt"


def test_gueltig_weist_pfadtricks_ab():
    assert projekte._gueltig("kurs-1")
    assert not projekte._gueltig("../etc")
    assert not projekte._gueltig("/absolut")
    assert not projekte._gueltig("Gross")


def test_dateiname_entfernt_pfadanteile_und_prozentkodierung():
    assert projekte._dateiname("../../etc/passwd") == "passwd"
    assert projekte._dateiname("T%C3%9CV%20Vortrag.pptx") == "TÜV Vortrag.pptx"
    # unquote macht aus %2F einen Schrägstrich — der zweite basename fängt das ab.
    assert projekte._dateiname("a%2F..%2Fb.md") == "b.md"


def test_create_legt_ordner_und_dateien_an(projekte_tmp):
    slug = projekte.create(BRIEF, design_md=b"# CI", material=[("q.md", b"Quelle")])
    d = projekte_tmp / slug
    assert slug == "cyber-resilience-act"
    assert json.loads((d / "brief.json").read_text())["thema"] == BRIEF["thema"]
    assert (d / "design.md").read_bytes() == b"# CI"
    assert (d / "material" / "q.md").read_bytes() == b"Quelle"
    assert projekte.load_status(slug)["phase"] == projekte.PHASE_BRIEFING


def test_create_vergibt_bei_gleichem_thema_einen_freien_slug(projekte_tmp):
    erst = projekte.create(BRIEF)
    zweit = projekte.create(BRIEF)
    assert erst == "cyber-resilience-act"
    assert zweit == "cyber-resilience-act-2"


def test_material_ohne_namen_wird_verworfen(projekte_tmp):
    slug = projekte.create(BRIEF, material=[("", b"x"), ("gut.md", b"y")])
    namen = [p.name for p in (projekte_tmp / slug / "material").iterdir()]
    assert namen == ["gut.md"]


def test_projekt_dir_liefert_nur_gueltige_vorhandene_ordner(projekte_tmp):
    slug = projekte.create(BRIEF)
    assert projekte.projekt_dir(slug) == projekte_tmp / slug
    assert projekte.projekt_dir("gibt-es-nicht") is None
    assert projekte.projekt_dir("../etc") is None


def test_loeschen_entfernt_den_ordner(projekte_tmp):
    slug = projekte.create(BRIEF)
    assert projekte.loeschen(slug) is True
    assert not (projekte_tmp / slug).exists()
    assert projekte.loeschen(slug) is False


def test_liste_ignoriert_lose_dateien(projekte_tmp):
    # projects/aisc-design.md liegt dort bewusst als Standard-CI und ist kein Projekt.
    projekte.create(BRIEF)
    (projekte_tmp / "aisc-design.md").write_text("# CI")
    assert [p["slug"] for p in projekte.liste()] == ["cyber-resilience-act"]


def test_set_phase_schreibt_zeitstempel_und_fehler(projekte_tmp):
    slug = projekte.create(BRIEF)
    projekte.set_phase(slug, projekte.PHASE_FEHLER, fehler="kaputt")
    status = projekte.load_status(slug)
    assert status["phase"] == projekte.PHASE_FEHLER
    assert status["letzter_fehler"] == "kaputt"
    assert status["geaendert_am"] >= status["erstellt_am"]
