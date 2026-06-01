#!/bin/bash
set -euo pipefail

PRODUCT_NAME="News Talent Monitor+"
INSTALL_ROOT="${HOME}/Applications/NewsTalentMonitorPlus"
SOURCE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_PYTHON="${INSTALL_ROOT}/.venv/bin/python"
APP_SUPPORT="${HOME}/Library/Application Support/NewsTalentMonitorPlus"
LOG_DIR="${HOME}/Library/Logs/NewsTalentMonitorPlus"
LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${LAUNCH_AGENT_DIR}/com.newstalentmonitor.plus.plist"

section() {
  printf '\n== %s ==\n' "$1"
}

echo "${PRODUCT_NAME} macOS installer"
echo "This installs the app for the current Mac user."

section "Checking Python"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found."
  echo "Install Python 3 from https://www.python.org/downloads/macos/ and run this installer again."
  read -r -p "Press Enter to close..."
  exit 1
fi
python3 --version

section "Installing app files"
mkdir -p "${INSTALL_ROOT}"
rsync -a --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".pi-image-build" \
  --exclude "__pycache__" \
  --exclude ".DS_Store" \
  "${SOURCE_ROOT}/" "${INSTALL_ROOT}/"

section "Creating Python environment"
cd "${INSTALL_ROOT}"
python3 -m venv .venv
"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PYTHON}" -m pip install -r requirements.txt

section "Preparing app data"
mkdir -p "${APP_SUPPORT}" "${LOG_DIR}" "${TMPDIR:-/tmp}/NewsTalentMonitorPlus/ndi"

section "Installing login startup"
mkdir -p "${LAUNCH_AGENT_DIR}"
cat > "${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.newstalentmonitor.plus</string>
  <key>ProgramArguments</key>
  <array>
    <string>${INSTALL_ROOT}/installers/macos/start-server.command</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/launchd.err.log</string>
</dict>
</plist>
PLIST

chmod +x "${INSTALL_ROOT}/installers/macos/"*.command
launchctl unload "${PLIST_PATH}" >/dev/null 2>&1 || true
launchctl load "${PLIST_PATH}"

section "Checking NDI runtime"
set +e
"${VENV_PYTHON}" tools/ndi/check_ndi_runtime.py
NDI_STATUS=$?
set -e

if [ "${NDI_STATUS}" -ne 0 ]; then
  echo
  echo "NDI is not ready yet."
  echo "Install the official NDI runtime or SDK from:"
  echo "https://ndi.video/for-developers/ndi-sdk/download/"
  echo "Then restart News Talent Monitor+."
fi

section "Starting app"
"${INSTALL_ROOT}/installers/macos/start-server.command"

echo
echo "Installed to: ${INSTALL_ROOT}"
echo "Display: http://127.0.0.1:8010/display"
echo "Config:  http://127.0.0.1:8010/config"
echo
read -r -p "Press Enter to close..."
