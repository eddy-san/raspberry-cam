#!/bin/bash
set -euo pipefail

# Verzeichnis relativ zum Skript
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_DIR="${SCRIPT_DIR}/../jpg/current"

# --- 0) Daylight-Gate aufrufen ---
GATE_OUT=$("$SCRIPT_DIR/00_daylight_gate.sh" 2>&1)
rc=$?
echo "$GATE_OUT" >&2   # Debug nach STDERR

if [ $rc -eq 3 ]; then
  echo "Night window – skip capture." >&2
  exit 3
elif [ $rc -ne 0 ]; then
  echo "Daylight-Gate Fehler (exit $rc)" >&2
  exit $rc
fi

# --- 1) Aufnahme nur wenn Tag ---
mkdir -p "$CURRENT_DIR"
rm -f "$CURRENT_DIR"/*

# Zeitstempel + CPU-Temp
STAMP="$(date +'%Y-%m-%d %H:%M')"
CPU_TEMP="$([ -x /usr/bin/vcgencmd ] && /usr/bin/vcgencmd measure_temp | sed 's/temp=//;s/\..*$/°C/;s/\..*°C/°C/' || echo 'n/a')"
OVERLAY_TEXT="$STAMP - RaspberryCam - CPU: $CPU_TEMP"

# Dateiname
TS="$(date +"%Y%m%d_%H%M%S")"
OUT_IMG="$CURRENT_DIR/IMG_4903_${TS}.jpg"
LIVE_IMG="$CURRENT_DIR/IMG_4903.jpg"

# Bild aufnehmen
fswebcam --flip v --flip h --skip 10 -r 1920x1080 --no-banner \
  --input 0 --jpeg 95 --palette MJPEG "$OUT_IMG"

# Maße
W=$(identify -format "%w" "$OUT_IMG")
H=$(identify -format "%h" "$OUT_IMG")

# Leicht + stark blurren
convert "$OUT_IMG" -blur 0x2 "$CURRENT_DIR/lightly.png"
convert "$OUT_IMG" -blur 0x25 "$CURRENT_DIR/fully.png"

# Maske erstellen
convert -size "${W}x${H}" gradient: -define gradient:angle=90 -negate -evaluate pow 0.5 "$CURRENT_DIR/mask.png"

# Blur kombinieren
convert "$CURRENT_DIR/lightly.png" "$CURRENT_DIR/fully.png" "$CURRENT_DIR/mask.png" \
  -compose over -composite "$OUT_IMG"

# Text einfügen
convert "$OUT_IMG" \
  -gravity southeast -pointsize 20 -fill white \
  -annotate +75+90 "$OVERLAY_TEXT" "$OUT_IMG"

# Live-Bild erzeugen
cp "$OUT_IMG" "$LIVE_IMG"

# Aufräumen
rm -f "$CURRENT_DIR/lightly.png" "$CURRENT_DIR/fully.png" "$CURRENT_DIR/mask.png"

# Nur bei Erfolg den Pfad ausgeben
echo "$OUT_IMG"

