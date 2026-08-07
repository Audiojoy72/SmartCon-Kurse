"""Foliensatz → PNG. LibreOffice macht das PDF, pdftoppm die Bilder.

Zwei Schritte statt einem: LibreOffice kann zwar direkt Bilder schreiben,
aber nur die erste Folie je Aufruf. Der Umweg über PDF ist der einzige, der
einen ganzen Satz in einem Durchgang liefert.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

QUELLFORMATE = (".pptx", ".ppt", ".odp", ".pdf")
ZEITLIMIT = 300


class FolienFehler(RuntimeError):
    """Export nicht möglich. Die Meldung nennt den Grund."""


def _soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def werkzeuge_vorhanden() -> bool:
    return bool(_soffice()) and bool(shutil.which("pdftoppm"))


def exportiere(quelle: Path, ziel_dir: Path, dpi: int = 150) -> list[Path]:
    """Rendert jede Folie als folie-NN.png. Leert ziel_dir vorher.

    ziel_dir wird komplett gelöscht und neu angelegt — der Aufrufer muss
    hier einen eigens dafür bestimmten Ordner übergeben (z. B.
    projects/<slug>/folien/), nie einen geteilten oder übergeordneten Pfad.
    """
    if not quelle.is_file():
        raise FolienFehler(f"Quelldatei nicht gefunden: {quelle}")
    if quelle.suffix.lower() not in QUELLFORMATE:
        raise FolienFehler(
            f"Format {quelle.suffix} wird nicht unterstützt "
            f"(möglich: {', '.join(QUELLFORMATE)})")
    if not werkzeuge_vorhanden():
        raise FolienFehler(
            "LibreOffice oder pdftoppm fehlt — im Container sind sie enthalten, "
            "auf dem Host nicht zwingend")

    if ziel_dir.exists():
        shutil.rmtree(ziel_dir)
    ziel_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as tmp:
        pdf = _als_pdf(quelle, Path(tmp))
        _als_pngs(pdf, ziel_dir, dpi)

    return sorted(ziel_dir.glob("folie-*.png"))


def _als_pdf(quelle: Path, arbeit: Path) -> Path:
    if quelle.suffix.lower() == ".pdf":
        return quelle
    # -env:UserInstallation: eigenes Profil, sonst blockieren sich parallele
    # Aufrufe gegenseitig und der zweite endet ohne Ausgabe.
    befehl = [_soffice(), "--headless",
              f"-env:UserInstallation=file://{arbeit / 'profil'}",
              "--convert-to", "pdf", "--outdir", str(arbeit), str(quelle)]
    _laufen_lassen(befehl, "LibreOffice")
    pdf = arbeit / f"{quelle.stem}.pdf"
    if not pdf.is_file():
        raise FolienFehler(
            f"LibreOffice hat kein PDF geschrieben (erwartet: {pdf.name})")
    return pdf


def _als_pngs(pdf: Path, ziel_dir: Path, dpi: int) -> None:
    befehl = ["pdftoppm", "-png", "-r", str(dpi),
              str(pdf), str(ziel_dir / "folie")]
    _laufen_lassen(befehl, "pdftoppm")
    _normalisiere_nummerierung(ziel_dir)


def _normalisiere_nummerierung(ziel_dir: Path) -> None:
    """Macht die pdftoppm-Nummerierung alphabetisch sortierbar.

    pdftoppm polstert die Nummer je nach Gesamtseitenzahl unterschiedlich
    breit (folie-1.png unter 10 Seiten, folie-01.png ab 10, folie-001.png
    ab 100). Ein fest zweistelliges Format würde ab der 100. Folie falsch
    sortieren ("folie-100.png" vor "folie-11.png"), darum richtet sich die
    Breite hier nach der tatsächlichen Foliensahl (mindestens zweistellig).
    """
    dateien = sorted(ziel_dir.glob("folie-*.png"),
                      key=lambda d: int(d.stem.split("-")[-1]))
    breite = max(2, len(str(len(dateien))))
    for datei in dateien:
        nummer = int(datei.stem.split("-")[-1])
        ziel = ziel_dir / f"folie-{nummer:0{breite}d}.png"
        if datei != ziel:
            datei.rename(ziel)


def _laufen_lassen(befehl: list[str], name: str) -> None:
    try:
        ergebnis = subprocess.run(befehl, capture_output=True, text=True,
                                  timeout=ZEITLIMIT)
    except subprocess.TimeoutExpired as e:
        raise FolienFehler(f"{name} hat das Zeitlimit überschritten") from e
    if ergebnis.returncode != 0:
        raise FolienFehler(
            f"{name} fehlgeschlagen: {ergebnis.stderr.strip() or ergebnis.stdout.strip()}")
