#!/bin/bash
set -euo pipefail

INSTALL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_PYTHON="${INSTALL_ROOT}/.venv/bin/python"
APP_SUPPORT="${HOME}/Library/Application Support/NewsTalentMonitorPlus"
LOG_DIR="${HOME}/Library/Logs/NewsTalentMonitorPlus"
FRAME_DIR="${TMPDIR:-/tmp}/NewsTalentMonitorPlus/ndi"
PID_PATH="${APP_SUPPORT}/server.pid"

mkdir -p "${APP_SUPPORT}" "${LOG_DIR}" "${FRAME_DIR}"

if [ -f "${PID_PATH}" ]; then
  EXISTING_PID="$(cat "${PID_PATH}" 2>/dev/null || true)"
  if [ -n "${EXISTING_PID}" ] && kill -0 "${EXISTING_PID}" >/dev/null 2>&1; then
    echo "News Talent Monitor+ is already running on process ${EXISTING_PID}."
    exit 0
  fi
fi

export ANCHOR_MICS_HOST="127.0.0.1"
export ANCHOR_MICS_PORT="8010"
export ANCHOR_MICS_DATA_FILE="${APP_SUPPORT}/state.json"
export ANCHOR_MICS_LOG_FILE="${LOG_DIR}/news-talent-monitor.log"
export ANCHOR_MICS_NDI_WORK_DIR="${FRAME_DIR}"

cd "${INSTALL_ROOT}"
nohup "${VENV_PYTHON}" run.py >> "${LOG_DIR}/server.out.log" 2>> "${LOG_DIR}/server.err.log" &
echo "$!" > "${PID_PATH}"
echo "Started News Talent Monitor+ on process $!."
