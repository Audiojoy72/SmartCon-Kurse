"""Abschlussprüfung: Schema-Validierung und HTML-Ausgabe.

Der Agent liefert pruefung.json. Diese Datei prüft, was ankam, bevor daraus
ein Nachweis wird — ein Zeiger auf eine nicht vorhandene Option macht eine
Frage unlösbar, und das fällt sonst erst dem Teilnehmer auf.
"""

import html as _html
import json
from pathlib import Path

MIN_OPTIONEN = 3
MAX_OPTIONEN = 5

# Name der gerenderten Prüfungsseite. Weder Stoffquelle noch Ergebnis-Datei:
# eine Prüfung ist nicht der Stoff, den sie abfragt, und kein Nachweis der
# Schulung — sie darf also weder in stoffquelle() noch in der Ergebnis-Liste
# auftauchen.
HTML_DATEINAME = "pruefung.html"


class PruefungFehler(ValueError):
    """Die Datei ist nicht verwendbar. Die Meldung nennt die Fundstelle."""


def laden(pfad: Path) -> dict:
    """Liest und validiert pruefung.json."""
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError as e:
        raise PruefungFehler(f"{pfad.name} nicht lesbar: {e}") from e
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as e:
        raise PruefungFehler(
            f"{pfad.name} ist kein gültiges JSON ({e.msg}, Zeile {e.lineno}). "
            "Häufigste Ursache: Der Agent hat Code-Zäune (```json) mitgeschrieben."
        ) from e
    pruefe(daten)
    return daten


def pruefe(daten: dict) -> None:
    """Wirft PruefungFehler, wenn die Struktur unbrauchbar ist."""
    if not isinstance(daten, dict):
        raise PruefungFehler("Die Datei muss ein JSON-Objekt enthalten")
    titel = daten.get("titel")
    if not isinstance(titel, str) or not titel.strip():
        raise PruefungFehler("„titel“ fehlt oder ist leer")

    grenze = daten.get("bestehensgrenze")
    if not isinstance(grenze, int) or isinstance(grenze, bool) \
            or not 1 <= grenze <= 100:
        raise PruefungFehler(
            "„bestehensgrenze“ muss eine ganze Zahl zwischen 1 und 100 sein")

    fragen = daten.get("fragen")
    if not isinstance(fragen, list) or not fragen:
        raise PruefungFehler("„fragen“ fehlt oder ist leer")

    for nr, frage in enumerate(fragen, start=1):
        _pruefe_frage(nr, frage)


def _pruefe_frage(nr: int, frage) -> None:
    if not isinstance(frage, dict):
        raise PruefungFehler(f"Frage {nr}: kein Objekt")
    frage_text = frage.get("frage")
    if not isinstance(frage_text, str) or not frage_text.strip():
        raise PruefungFehler(f"Frage {nr}: Fragetext fehlt")

    optionen = frage.get("optionen")
    if not isinstance(optionen, list) or not MIN_OPTIONEN <= len(optionen) <= MAX_OPTIONEN:
        raise PruefungFehler(
            f"Frage {nr}: „optionen“ braucht {MIN_OPTIONEN} bis {MAX_OPTIONEN} Einträge")
    if any(not isinstance(o, str) or not o.strip() for o in optionen):
        raise PruefungFehler(f"Frage {nr}: leere Antwortoption")

    richtig = frage.get("richtig")
    if not isinstance(richtig, int) or isinstance(richtig, bool) \
            or not 0 <= richtig < len(optionen):
        raise PruefungFehler(
            f"Frage {nr}: „richtig“ muss auf eine vorhandene Option zeigen "
            f"(0 bis {len(optionen) - 1})")


# AI-SmartCon-CI. Eine design.md im Projekt kann sie überschreiben.
FARBEN = {
    "hintergrund": "#060611",
    "panel": "#1a1a22",
    "akzent": "#c9a84c",
    "akzent_hell": "#e0c274",
    "text": "#f6f1e8",
    "text_sekundaer": "#d8cdb4",
}


def als_html(daten: dict, design: dict | None = None) -> str:
    """Eine offline lauffähige Prüfungsseite. Kein Server, keine Fremdquellen.

    Die Lösungen stehen im Skript, nicht im Fragebogen — sonst genügt ein
    Blick in den Quelltext des sichtbaren Teils.
    """
    pruefe(daten)
    farben = {**FARBEN, **(design or {})}

    fragen_html = []
    for nr, frage in enumerate(daten["fragen"], start=1):
        optionen = "\n".join(
            f'          <label class="option">'
            f'<input type="radio" name="f{nr}" value="{i}"> '
            f'<span>{_html.escape(str(o))}</span></label>'
            for i, o in enumerate(frage["optionen"]))
        thema = _html.escape(str(frage.get("thema", "")))
        fragen_html.append(f"""      <li class="frage" id="frage-{nr}">
        <p class="thema">{thema}</p>
        <p class="text">{_html.escape(str(frage["frage"]))}</p>
        <div class="optionen">
{optionen}
        </div>
        <p class="rueckmeldung" hidden></p>
      </li>""")

    # Nur das, was die Auswertung braucht.
    # "hinweis" ist Agenten-Freitext und ungeprüft (siehe _pruefe_frage) — ein
    # "</script>" darin würde den Script-Block vorzeitig beenden, bevor JS ihn
    # als String liest, und alle Lösungen im Klartext offenlegen. json.dumps
    # escaped "/" nicht, deshalb hier explizit: "<\/script>" bleibt in einem
    # JS-String ein normales Zeichen, der HTML-Tokenizer sieht kein Tag-Ende.
    loesungen = json.dumps(
        [{"richtig": f["richtig"], "hinweis": str(f.get("hinweis", ""))}
         for f in daten["fragen"]], ensure_ascii=False
    ).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(str(daten["titel"]))}</title>
<style>
  :root {{
    --bg: {farben["hintergrund"]};
    --panel: {farben["panel"]};
    --akzent: {farben["akzent"]};
    --akzent-hell: {farben["akzent_hell"]};
    --text: {farben["text"]};
    --text2: {farben["text_sekundaer"]};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 16px;
    background: var(--bg); color: var(--text);
    font-family: Inter, system-ui, sans-serif; line-height: 1.5;
    overflow-wrap: break-word;
  }}
  main {{ max-width: 760px; margin: 0 auto; }}
  h1 {{ font-size: 28px; line-height: 1.2; margin: 0 0 8px; }}
  .kopf {{ border-bottom: 3px solid var(--akzent); padding-bottom: 16px; margin-bottom: 24px; }}
  .muted {{ color: var(--text2); font-size: 14px; }}
  ol {{ list-style: none; padding: 0; margin: 0; }}
  .frage {{
    background: var(--panel); border: 1px solid var(--akzent);
    border-radius: 14px; padding: 20px; margin-bottom: 16px;
  }}
  .thema {{
    color: var(--akzent); font-size: 11px; letter-spacing: .14em;
    text-transform: uppercase; margin: 0 0 8px;
  }}
  .text {{ font-weight: 600; margin: 0 0 12px; }}
  .optionen {{ display: flex; flex-direction: column; gap: 8px; }}
  .option {{
    display: flex; gap: 10px; align-items: flex-start;
    padding: 10px 12px; border-radius: 10px;
    background: rgba(255,255,255,.04); cursor: pointer;
  }}
  .option span {{ min-width: 0; }}
  .option[hidden] {{ display: none; }}
  .rueckmeldung {{ margin: 12px 0 0; font-size: 14px; color: var(--text2); }}
  .rueckmeldung[hidden] {{ display: none; }}
  .korrekt {{ border-color: #4ade80; }}
  .falsch {{ border-color: #f87171; }}
  .zeile {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
  button {{
    background: var(--akzent); color: #1a1a22; border: 0;
    border-radius: 10px; padding: 13px 22px; font-size: 15px;
    font-weight: 600; cursor: pointer;
  }}
  button:hover {{ background: var(--akzent-hell); }}
  #ergebnis {{
    margin-top: 24px; padding: 20px; border-radius: 14px;
    background: var(--panel); border: 1px solid var(--akzent);
  }}
  #ergebnis[hidden] {{ display: none; }}
  #ergebnis .note {{ font-size: 34px; font-weight: 700; color: var(--akzent); }}
</style>
</head>
<body>
<main>
  <div class="kopf">
    <h1>{_html.escape(str(daten["titel"]))}</h1>
    <p class="muted">{len(daten["fragen"])} Fragen · bestanden ab
      {daten["bestehensgrenze"]} % · je Frage zählt genau eine Antwort.</p>
  </div>

  <form id="pruefung">
    <ol>
{chr(10).join(fragen_html)}
    </ol>
    <div class="zeile">
      <button type="submit">Auswerten</button>
      <span id="hinweis" class="muted"></span>
    </div>
  </form>

  <div id="ergebnis" hidden>
    <p class="note" id="note"></p>
    <p id="urteil"></p>
    <div class="zeile"><button type="button" id="nochmal">Noch einmal</button></div>
  </div>
</main>
<script>
const LOESUNGEN = {loesungen};
const GRENZE = {daten["bestehensgrenze"]};
const form = document.getElementById('pruefung');

form.addEventListener('submit', (e) => {{
  e.preventDefault();
  const offen = LOESUNGEN.findIndex((_, i) => !form[`f${{i + 1}}`].value);
  if (offen !== -1) {{
    document.getElementById('hinweis').textContent =
      `Frage ${{offen + 1}} ist noch offen.`;
    document.getElementById(`frage-${{offen + 1}}`).scrollIntoView({{block: 'center'}});
    return;
  }}
  document.getElementById('hinweis').textContent = '';

  let treffer = 0;
  LOESUNGEN.forEach((loesung, i) => {{
    const gewaehlt = Number(form[`f${{i + 1}}`].value);
    const kasten = document.getElementById(`frage-${{i + 1}}`);
    const rueck = kasten.querySelector('.rueckmeldung');
    const ok = gewaehlt === loesung.richtig;
    if (ok) treffer++;
    kasten.classList.remove('korrekt', 'falsch');
    kasten.classList.add(ok ? 'korrekt' : 'falsch');
    rueck.textContent = (ok ? 'Richtig. ' : 'Nicht richtig. ') + loesung.hinweis;
    rueck.hidden = false;
  }});

  const prozent = Math.round((treffer / LOESUNGEN.length) * 100);
  document.getElementById('note').textContent = `${{prozent}} %`;
  document.getElementById('urteil').textContent = prozent >= GRENZE
    ? `Bestanden — ${{treffer}} von ${{LOESUNGEN.length}} Fragen richtig.`
    : `Nicht bestanden — ${{treffer}} von ${{LOESUNGEN.length}} richtig, nötig sind ${{GRENZE}} %.`;
  document.getElementById('ergebnis').hidden = false;
  document.getElementById('ergebnis').scrollIntoView({{behavior: 'smooth'}});
}});

document.getElementById('nochmal').addEventListener('click', () => {{
  form.reset();
  document.querySelectorAll('.frage').forEach((k) => {{
    k.classList.remove('korrekt', 'falsch');
    k.querySelector('.rueckmeldung').hidden = true;
  }});
  document.getElementById('ergebnis').hidden = true;
  window.scrollTo({{top: 0, behavior: 'smooth'}});
}});
</script>
</body>
</html>
"""
