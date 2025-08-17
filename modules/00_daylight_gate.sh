#!/bin/bash
set -euo pipefail

LAT="49.454N"
LON="11.078E"

# Zeiten für zivile Dämmerung holen (Format: HH:MM,HH:MM)
OUT=$(sunwait list civil "$LAT" "$LON")
DAWN=$(echo "$OUT" | cut -d',' -f1)
DUSK=$(echo "$OUT" | cut -d',' -f2)
NOW=$(date +%H:%M)

echo "DAWN=$DAWN DUSK=$DUSK NOW=$NOW"

if [[ "$NOW" > "$DAWN" && "$NOW" < "$DUSK" ]]; then
  exit 0   # Tag -> Bild aufnehmen
else
  echo "Night window – skip capture." >&2
  exit 3   # Nacht -> kein Bild
fi

