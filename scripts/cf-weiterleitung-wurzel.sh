#!/usr/bin/env bash
# Legt die Cloudflare-Weiterleitung an: kurse.smartcon-ai.de/ -> /anmeldung
#
# Warum das nicht der Tunnel macht: Der Tunnel routet bewusst nur
# /anmeldung* und /portal*, damit die Werkstatt von aussen nicht erreichbar
# ist. Die Wurzel liefert deshalb 404. Diese Regel greift eine Ebene davor,
# bei Cloudflare selbst, und laesst die Schutzregel unangetastet.
#
# Braucht einen API-Token mit "Zone -> Dynamic Redirect -> Edit" auf der Zone
# smartcon-ai.de, abgelegt in ~/.cloudflared/smartcon-ai-api-token (chmod 600).
# Zwei Stolpersteine, beide einmal erlebt:
#  - Der Token aus cert.pem reicht nicht, der darf nur DNS.
#  - "Zone WAF -> Edit" ist die falsche Gruppe. Damit gehen Firewall-Regeln,
#    aber nicht Redirect Rules; die API antwortet dann schlicht
#    "request is not authorized". Womit ein Token darf, laesst sich pruefen:
#    die erlaubte Phase meldet "could not find entrypoint ruleset", die
#    verbotene "request is not authorized".
#
# Die Bedingung prueft den Pfad exakt auf "/". Ohne das wuerde die Regel auch
# /anmeldung umleiten und eine Endlosschleife bauen.
set -euo pipefail

# Zwei Wege, je nachdem was hinterlegt ist:
#  1. Global API Key — zwei Zeilen (Mailadresse, Schluessel), kann alles
#  2. eingeschraenkter Token — eine Zeile, braucht "Dynamic Redirect -> Edit"
GLOBAL_DATEI="$HOME/.cloudflared/smartcon-ai-global-key"
TOKEN_DATEI="$HOME/.cloudflared/smartcon-ai-api-token"
ZONE=6ef4c1d94d813010cb8f6682e962d963   # smartcon-ai.de
HOST=kurse.smartcon-ai.de
ZIEL="https://kurse.smartcon-ai.de/anmeldung"

if [ -s "$GLOBAL_DATEI" ]; then
  MAIL=$(sed -n 1p "$GLOBAL_DATEI" | tr -d '[:space:]')
  KEY=$(sed -n 2p "$GLOBAL_DATEI" | tr -d '[:space:]')
  api() { curl -s -H "X-Auth-Email: $MAIL" -H "X-Auth-Key: $KEY" \
               -H "Content-Type: application/json" "$@"; }
elif [ -s "$TOKEN_DATEI" ]; then
  TOKEN=$(tr -d '[:space:]' < "$TOKEN_DATEI")
  api() { curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$@"; }
else
  echo "Weder $GLOBAL_DATEI noch $TOKEN_DATEI gefuellt"; exit 1
fi

echo "Pruefe den Token …"
api "https://api.cloudflare.com/client/v4/zones/$ZONE/rulesets/phases/http_request_dynamic_redirect/entrypoint" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
if not d.get('success'):
    print('Token darf keine Redirect Rules:', d.get('errors'))
    print('Fehlt vermutlich die Berechtigung Zone -> Dynamic Redirect -> Edit.')
    raise SystemExit(1)
print('  OK, bestehende Regeln:', len(d['result'].get('rules', [])))"

echo "Setze die Weiterleitung …"
api -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE/rulesets/phases/http_request_dynamic_redirect/entrypoint" \
  --data @- <<JSON | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('  angelegt:' if d.get('success') else '  fehlgeschlagen:',
      d['result']['rules'][0]['description'] if d.get('success') else d.get('errors'))"
{
  "rules": [{
    "action": "redirect",
    "description": "kurse: Wurzel auf die Anmeldung",
    "expression": "(http.host eq \"$HOST\" and http.request.uri.path eq \"/\")",
    "action_parameters": {
      "from_value": {
        "status_code": 301,
        "target_url": { "value": "$ZIEL" },
        "preserve_query_string": false
      }
    }
  }]
}
JSON

echo "Gegenprobe:"
for p in / /anmeldung /portal; do
  printf "  %-12s HTTP %s\n" "$p" \
    "$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "https://$HOST$p")"
done
echo "Erwartet: / -> 301, /anmeldung -> 200, /portal -> 200"
