#!/bin/bash
set -euo pipefail

INSTALL_ROOT="${HOME}/Applications/NewsTalentMonitorPlus"
APP_SUPPORT="${HOME}/Library/Application Support/NewsTalentMonitorPlus"
PLIST_PATH="${HOME}/Library/LaunchAgents/com.newstalentmonitor.plus.plist"

if [ -x "${INSTALL_ROOT}/installers/macos/stop-server.command" ]; then
  "${INSTALL_ROOT}/installers/macos/stop-server.command" || true
fi

launchctl unload "${PLIST_PATH}" >/dev/null 2>&1 || true
rm -f "${PLIST_PATH}"
rm -rf "${INSTALL_ROOT}"

echo "News Talent Monitor+ app files were removed."
echo "User data remains here so settings are not accidentally lost:"
echo "${APP_SUPPORT}"
echo
echo "Delete that folder manually if you want to remove settings and logs too."
read -r -p "Press Enter to close..."
