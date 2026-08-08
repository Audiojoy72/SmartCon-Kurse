"""Der Arbeitsauftrag entscheidet, ob die Prüfung fair ist."""

from app.prompts import pruefung_prompt


def test_prompt_nennt_stoffquelle_und_zielpfad(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")
    (tmp_path / "curriculum.md").write_text("# Plan")

    p = pruefung_prompt(tmp_path)
    assert "deck.pptx" in p
    assert str(tmp_path / "pruefung.json") in p


def test_prompt_verbietet_fragen_ausserhalb_der_stoffquelle(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")

    p = pruefung_prompt(tmp_path)
    assert "verwirf die Frage" in p
    assert "Kein Vorwissen" in p


def test_curriculum_dient_nur_der_gliederung(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (material / "deck.pptx").write_bytes(b"x")
    (tmp_path / "curriculum.md").write_text("# Plan")

    p = pruefung_prompt(tmp_path)
    assert "nur, um die Gliederung zu kennen" in p


def test_ohne_stoffquelle_wird_der_mangel_benannt(tmp_path):
    (tmp_path / "curriculum.md").write_text("# Plan")
    p = pruefung_prompt(tmp_path)
    assert "ACHTUNG" in p
    assert "Lernplan" in p


def test_bestehensgrenze_steht_im_prompt(tmp_path):
    (tmp_path / "curriculum.md").write_text("# Plan")
    assert "80" in pruefung_prompt(tmp_path, bestehensgrenze=80)


def test_prompt_verlangt_nur_json(tmp_path):
    (tmp_path / "curriculum.md").write_text("# Plan")
    p = pruefung_prompt(tmp_path)
    assert "keine Code-Zäune" in p
