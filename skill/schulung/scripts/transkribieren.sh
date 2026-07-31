#!/usr/bin/env bash
# Transkribiert eine Audiodatei und gibt JSON mit Wort-Zeitstempeln plus abgeleiteten
# Satz-Beats aus (Choreografie-Grundlage fuer HyperFrames und HTML-Szenen, siehe
# SKILL.md, Phase 4).
#
#   ./transkribieren.sh vo_fast.mp3            > vo.json     # Sprache: de
#   ./transkribieren.sh vo_fast.mp3 en         > vo.json
#
# Zwei Wege:
#   1. Default: lokales whisper (pip install openai-whisper) mit
#      --output_format json --word_timestamps True. Laeuft notfalls auf CPU, dann
#      deutlich langsamer. Modell per WHISPER_MODEL waehlbar (Default: large-v3).
#   2. Optional Remote: WHISPER_REMOTE_CMD enthaelt ein Kommando, das die Audiodatei
#      auf stdin bekommt und verbose_json mit Wort-Zeitstempeln auf stdout liefert —
#      z. B. ein ssh-Aufruf auf einen eigenen GPU-Server mit einer Whisper-kompatiblen
#      API. Beispiel:
#        WHISPER_REMOTE_CMD='ssh gpu-server "curl -sS -m 300 http://localhost:8000/v1/audio/transcriptions -F file=@- -F model=large-v3 -F response_format=verbose_json -F \"timestamp_granularities[]=word\""'
#
# Die Ausgabe enthaelt WORT-Zeitstempel. Segment-Granularitaet reicht nicht: ein
# 35-Sekunden-Text kommt als ein bis zwei Segmente zurueck, damit laesst sich nichts
# choreografieren. Aus den Wortzeiten werden die Beats abgeleitet, indem an
# Satzzeichen geschnitten wird.
set -euo pipefail

AUDIO="${1:?Aufruf: transkribieren.sh <audiodatei> [sprachcode]}"
SPRACHE="${2:-de}"
MODELL="${WHISPER_MODEL:-large-v3}"

[ -f "$AUDIO" ] || { echo "Datei nicht gefunden: $AUDIO" >&2; exit 1; }

if [ -n "${WHISPER_REMOTE_CMD:-}" ]; then
  # Remote-Weg: das konfigurierte Kommando bekommt die Datei per stdin.
  eval "$WHISPER_REMOTE_CMD" < "$AUDIO" | python3 -c '
import json, sys
roh = sys.stdin.read()
try:
    d = json.loads(roh)
except json.JSONDecodeError:
    sys.exit("Keine JSON-Antwort vom Remote-Kommando:\n" + roh[:400])
if "error" in d:
    sys.exit("Die Transkriptions-API meldet einen Fehler: " + json.dumps(d["error"], ensure_ascii=False))
woerter = d.get("words") or []
if not woerter:
    for seg in d.get("segments", []):
        woerter.extend(seg.get("words") or [])
if not woerter:
    sys.exit("Antwort ohne Wortzeiten — Audio still oder Sprachcode falsch?")
# Beats = Satzgrenzen. Genau daran haengen die Einblendungen.
beats, start = [], woerter[0]["start"]
for w in woerter:
    if w["word"].strip().endswith((".", ":", "?", "!")):
        beats.append({"start": round(start, 2), "end": round(w["end"], 2)})
        start = w["end"]
out = {"text": d.get("text", ""), "words": woerter, "beats": beats}
print(json.dumps(out, ensure_ascii=False, indent=2))
print("%d Woerter, %d Saetze, %.1f s" % (len(woerter), len(beats), woerter[-1]["end"]), file=sys.stderr)
'
else
  # Lokaler Default: whisper-CLI. Schreibt <basisname>.json ins Output-Verzeichnis.
  command -v whisper >/dev/null 2>&1 || {
    echo "whisper nicht gefunden — Abhilfe: pip install openai-whisper" >&2
    echo "oder WHISPER_REMOTE_CMD auf einen Remote-Dienst setzen (siehe Skriptkopf)." >&2
    exit 1
  }
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' EXIT
  whisper "$AUDIO" --model "$MODELL" --language "$SPRACHE" \
    --output_format json --word_timestamps True --verbose False \
    --output_dir "$TMP" >/dev/null
  python3 - "$TMP/$(basename "${AUDIO%.*}").json" <<'PYEOF'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    d = json.load(f)
woerter = []
for seg in d.get("segments", []):
    woerter.extend(seg.get("words") or [])
if not woerter:
    sys.exit("whisper lieferte keine Wortzeiten — Audio still oder Sprachcode falsch?")
# Beats = Satzgrenzen. Genau daran haengen die Einblendungen.
beats, start = [], woerter[0]["start"]
for w in woerter:
    if w["word"].strip().endswith((".", ":", "?", "!")):
        beats.append({"start": round(start, 2), "end": round(w["end"], 2)})
        start = w["end"]
out = {"text": d.get("text", ""), "words": woerter, "beats": beats}
print(json.dumps(out, ensure_ascii=False, indent=2))
print("%d Woerter, %d Saetze, %.1f s" % (len(woerter), len(beats), woerter[-1]["end"]), file=sys.stderr)
PYEOF
fi
