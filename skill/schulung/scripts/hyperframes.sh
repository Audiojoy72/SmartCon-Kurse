#!/usr/bin/env bash
# Ruft die HyperFrames-CLI mit einer Node-22-Laufzeit auf, ohne die Shell-Umgebung
# umzustellen. Grund: `nvm use` scheitert, wenn npm einen eigenen `prefix` gesetzt hat
# (z. B. ~/.npm-global fuer global installierte Pakete) — und den anzufassen wuerde
# eine vorhandene andere Node-Installation beschaedigen.
#
#   ./hyperframes.sh lint
#   ./hyperframes.sh check
#   ./hyperframes.sh render --quality high --output final.mp4
#   ./hyperframes.sh --pfad          # nur das bin-Verzeichnis ausgeben (fuer preflight)
set -euo pipefail

# Hoechste vorhandene Node-Version >= 22 finden: nvm-Versionen und System-Node.
# Jeder Kandidat wird als "<major> <bin-verzeichnis>" gesammelt, damit `sort -V`
# numerisch nach Version sortiert und nicht alphabetisch nach Pfad.
node22_bin() {
  local kandidat major kandidaten=""

  for kandidat in "$HOME/.nvm/versions/node"/v*/bin; do
    [ -x "$kandidat/node" ] || continue
    major=$("$kandidat/node" -v | sed 's/^v\([0-9]*\).*/\1/')
    if [ "$major" -ge 22 ]; then
      kandidaten="$kandidaten$major $kandidat"$'\n'
    fi
  done

  if command -v node >/dev/null 2>&1; then
    major=$(node -v | sed 's/^v\([0-9]*\).*/\1/')
    if [ "$major" -ge 22 ]; then
      kandidaten="$kandidaten$major $(dirname "$(command -v node)")"$'\n'
    fi
  fi

  # Ohne Treffer nichts ausgeben, aber sauber zurueckkehren — sonst reisst `set -e`
  # das Skript ab, bevor die Fehlermeldung unten erscheint.
  printf '%s' "$kandidaten" | grep -v '^$' | sort -V | tail -1 | cut -d' ' -f2-
  return 0
}

BIN=$(node22_bin)

if [ -z "$BIN" ]; then
  echo "Keine Node-Laufzeit >= 22 gefunden — HyperFrames braucht sie." >&2
  echo "Abhilfe:  export NVM_DIR=\"\$HOME/.nvm\"; . \"\$NVM_DIR/nvm.sh\"; nvm install 22" >&2
  exit 1
fi

if [ "${1:-}" = "--pfad" ]; then
  echo "$BIN"
  exit 0
fi

# PATH nur fuer diesen Aufruf voranstellen — die aufrufende Shell bleibt unberuehrt.
PATH="$BIN:$PATH" exec npx hyperframes "$@"
