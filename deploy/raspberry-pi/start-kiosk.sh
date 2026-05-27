#!/bin/bash
set -eu

APP_URL="${ANCHOR_MICS_KIOSK_URL:-http://127.0.0.1:8010/display}"

xset -dpms || true
xset s off || true
xset s noblank || true
unclutter -idle 0.2 -root >/dev/null 2>&1 &

if command -v chromium-browser >/dev/null 2>&1; then
  BROWSER_BIN="chromium-browser"
elif command -v chromium >/dev/null 2>&1; then
  BROWSER_BIN="chromium"
else
  echo "Chromium was not found on this Raspberry Pi." >&2
  exit 1
fi

exec "$BROWSER_BIN" \
  --kiosk \
  --incognito \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --check-for-update-interval=31536000 \
  "$APP_URL"
