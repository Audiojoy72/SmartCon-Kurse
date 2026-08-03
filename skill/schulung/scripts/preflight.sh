#!/usr/bin/env bash
# Prueft VOR der Produktion, ob alles bereitsteht. Zweck: nicht mitten in einer
# Credit-Produktion an einem fehlenden ffmpeg scheitern.
#
#   ./preflight.sh              # alles pruefen
#   ./preflight.sh --kostenlos  # Kostenlos-Modus (Preset kostenlos):
#                               # Higgsfield/ffmpeg/Node/Whisper sind "nicht noetig"
#   SCHULUNG_KOSTENLOS=1 ./preflight.sh   # dasselbe per Umgebungsvariable
#
# Rueckgabe: 0 = produktionsbereit, 1 = etwas Notwendiges fehlt.
set -uo pipefail

KOSTENLOS=0
for a in "$@"; do
  [ "$a" = "--kostenlos" ] && KOSTENLOS=1
done
[ "${SCHULUNG_KOSTENLOS:-}" = "1" ] && KOSTENLOS=1

FEHLER=0
WARNUNG=0
ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; }
warn() { printf '  \033[33mwarn\033[0m  %s\n' "$1"; WARNUNG=$((WARNUNG+1)); }
fail() { printf '  \033[31mfehlt\033[0m %s\n' "$1"; FEHLER=$((FEHLER+1)); }
skip() { printf '  \033[34mnicht noetig\033[0m %s\n' "$1"; }

echo "Preflight — interaktive Lerneinheit"
if [ "$KOSTENLOS" = "1" ]; then
  echo "Modus: KOSTENLOS (Preset kostenlos — keine Medienproduktion, 0 Credits)"
fi
echo

echo "Medien-Werkzeuge"
if [ "$KOSTENLOS" = "1" ]; then
  skip "ffmpeg (kein Muxing, kein Tempo — es gibt keine Medien)"
else
  if command -v ffmpeg >/dev/null 2>&1; then
    ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')"
  else
    fail "ffmpeg — ohne das kein Muxing, kein Tempo, kein Concat"
  fi
fi

if [ "$KOSTENLOS" = "1" ]; then
  skip "node >= 22 (keine HyperFrames-Renders — Szenen laufen als HTML)"
else
  N22=$(bash "$(dirname "$0")/hyperframes.sh" --pfad 2>/dev/null || true)
  if [ -n "$N22" ]; then
    ok "node $("$N22/node" -v) fuer HyperFrames ($N22)"
  else
    fail "keine Node-Laufzeit >= 22 — HyperFrames braucht sie. Abhilfe: nvm install 22"
  fi
fi

echo
echo "Transkription (Beat-Timestamps)"
if [ "$KOSTENLOS" = "1" ]; then
  skip "whisper/WHISPER_REMOTE_CMD (kein Voiceover — nichts zu transkribieren)"
elif [ -n "${WHISPER_REMOTE_CMD:-}" ]; then
  ok "Remote-Transkription konfiguriert (WHISPER_REMOTE_CMD gesetzt)"
elif command -v whisper >/dev/null 2>&1; then
  ok "lokales whisper vorhanden (Default; CPU-tauglich, GPU deutlich schneller)"
else
  fail "weder WHISPER_REMOTE_CMD gesetzt noch lokales whisper — Abhilfe: pip install openai-whisper"
fi

echo
echo "Higgsfield (Video, Bild, Voiceover)"
if [ "$KOSTENLOS" = "1" ]; then
  skip "higgsfield-CLI, Auth, Guthaben, Workspace (0 Credits — kein Higgsfield noetig)"
elif ! command -v higgsfield >/dev/null 2>&1; then
  fail "higgsfield-CLI nicht gefunden: npm i -g @higgsfield/cli, dann higgsfield auth login"
else
  STATUS=$(timeout 30 higgsfield account status 2>&1 || true)
  case "$STATUS" in
    *"No workspace selected"*)
      fail "kein Workspace gesetzt: higgsfield workspace list, dann higgsfield workspace set <id>" ;;
    *credits*)
      ok "CLI angemeldet — $STATUS"
      # Guthaben herausziehen und gegen die guenstigste sinnvolle Produktion halten:
      # eine Kompakt-Lektion mit einem einzigen 10-s-Film liegt bei rund 110 Credits.
      # Guthaben kann Nachkommastellen haben ("1082.5 credits") — Ganzzahlteil nehmen.
      CREDITS=$(printf '%s' "$STATUS" | grep -o '[0-9][0-9.]* credits' | head -1 | cut -d. -f1)
      if [ -n "$CREDITS" ] && [ "$CREDITS" -lt 110 ]; then
        warn "$CREDITS Credits — unter dem Richtwert fuer die kleinste Schulung (~110)."
        warn "  Vor der Produktion mit dem User klaeren: aufladen, Filme durch"
        warn "  HyperFrames-Animationen ersetzen (die kosten nichts) — oder Preset statisch."
      fi ;;
    *)
      warn "CLI-Status unklar: $STATUS" ;;
  esac
fi

echo
echo "Stil"
SKILL_MD="$(dirname "$0")/../SKILL.md"
if [ -f "$SKILL_MD" ]; then
  ok "Skill-Anleitung gefunden: $SKILL_MD"
else
  fail "SKILL.md fehlt neben dem Skript ($SKILL_MD) — Installation unvollstaendig"
fi
if [ -n "${DESIGN_MD:-}" ] && [ -f "$DESIGN_MD" ]; then
  ok "design.md gefunden: $DESIGN_MD (uebersteuert das Preset)"
  if grep -q '^logo:' "$DESIGN_MD"; then
    LOGO=$(sed -n 's/^logo: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$DESIGN_MD" | head -1)
    if [ -n "$LOGO" ] && [ -f "$LOGO" ]; then
      ok "Logo-Datei gefunden: $LOGO"
    else
      warn "design.md nennt ein Logo ($LOGO), die Datei fehlt — im Curriculum als offene Position fuehren"
    fi
  fi
else
  ok "keine design.md gesetzt (DESIGN_MD) — es gilt das gewaehlte Preset, Default: cinematic"
fi

echo
if [ "$FEHLER" -gt 0 ]; then
  echo "Nicht produktionsbereit: $FEHLER fehlend, $WARNUNG Warnung(en)."
  echo "Teil 1 (Curriculum) geht trotzdem — der kostet nichts und braucht keins dieser Werkzeuge."
  exit 1
fi
echo "Produktionsbereit ($WARNUNG Warnung(en))."
