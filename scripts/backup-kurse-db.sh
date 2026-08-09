#!/usr/bin/env bash
# Taegliche Sicherung von data/kurse.db (Teilnehmer, Zugaenge, Anmeldungen,
# Pruefungsergebnisse). Ein `rm -rf data/` ist sonst das Ende der Kundenliste.
#
# `.backup` statt `cp`: Es laeuft konsistent, auch waehrend die App schreibt.
# Aufbewahrung 30 Tage; die Sicherungen liegen neben der Datenbank und sind
# per .gitignore vom Repo ausgeschlossen.
set -euo pipefail

PROJEKT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="$PROJEKT/data/kurse.db"
ZIEL="$PROJEKT/data/backups"
TAGE=30

[ -f "$DB" ] || { echo "keine Datenbank unter $DB"; exit 0; }
mkdir -p "$ZIEL"

DATEI="$ZIEL/kurse-$(date +%F-%H%M).db"
sqlite3 "$DB" ".backup '$DATEI'"

# Nur pruefen, ob die Kopie lesbar ist — eine kaputte Sicherung faellt sonst
# erst auf, wenn man sie braucht.
sqlite3 "$DATEI" "PRAGMA integrity_check;" | grep -q '^ok$' || {
  echo "Sicherung $DATEI ist nicht in Ordnung"; exit 1; }

find "$ZIEL" -name 'kurse-*.db' -type f -mtime +$TAGE -delete
echo "$(date -Iseconds) gesichert: $DATEI ($(du -h "$DATEI" | cut -f1))"
