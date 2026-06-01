#!/bin/bash
set -euo pipefail

APP_SUPPORT="${HOME}/Library/Application Support/NewsTalentMonitorPlus"
PID_PATH="${APP_SUPPORT}/server.pid"

if [ ! -f "${PID_PATH}" ]; then
  echo "News Talent Monitor+ is not running."
  exit 0
fi

PID="$(cat "${PID_PATH}" 2>/dev/null || true)"
if [ -n "${PID}" ] && kill -0 "${PID}" >/dev/null 2>&1; then
  kill "${PID}" || true
  echo "Stopped News Talent Monitor+."
fi

rm -f "${PID_PATH}"
