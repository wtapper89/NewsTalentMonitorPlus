#!/bin/bash
set -euo pipefail

APP_NAME="News Talent Monitor+"
INSTALL_DIR="/opt/news-talent-monitor"
SERVICE_NAME="news-talent-monitor"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SDK_ARCHIVE="${HOME}/Downloads/Install_NDI_SDK_v6_Linux.tar.gz"

echo "${APP_NAME} installer for Raspberry Pi OS"
echo

if [ "$(id -u)" -ne 0 ]; then
  echo "This installer needs administrator permission."
  echo "Run it again with:"
  echo "sudo $0"
  exit 1
fi

echo "Installing system packages..."
apt-get update
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip \
  x11-xserver-utils \
  unclutter \
  curl ca-certificates \
  rsync

if ! apt-get install -y --no-install-recommends chromium-browser; then
  apt-get install -y --no-install-recommends chromium
fi

echo "Copying app to ${INSTALL_DIR}..."
install -d "${INSTALL_DIR}"
rsync -a \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".pi-image-build" \
  --exclude "__pycache__" \
  "${CURRENT_DIR}/" "${INSTALL_DIR}/"

echo "Installing Python dependencies..."
python3 -m venv "${INSTALL_DIR}/.venv"
"${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${INSTALL_DIR}/.venv/bin/python" -m pip install -r "${INSTALL_DIR}/requirements.txt"

echo "Installing NDI runtime if SDK archive is present..."
if [ -f "${SDK_ARCHIVE}" ]; then
  /bin/bash "${INSTALL_DIR}/installers/raspberry-pi/install_ndi_from_sdk.sh" "${SDK_ARCHIVE}"
else
  echo "NDI SDK archive was not found at ${SDK_ARCHIVE}."
  echo "NDI preview will stay unavailable until the NDI runtime is installed."
fi

echo "Installing services..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=News Talent Monitor+ service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}
Environment=ANCHOR_MICS_SOURCE=qlxd
Environment=ANCHOR_MICS_HOST=127.0.0.1
Environment=ANCHOR_MICS_PORT=8010
ExecStart=${INSTALL_DIR}/.venv/bin/python ${INSTALL_DIR}/run.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

install -m 0755 "${INSTALL_DIR}/deploy/raspberry-pi/start-kiosk.sh" "${INSTALL_DIR}/deploy/raspberry-pi/start-kiosk.sh"
cat > "/etc/systemd/system/${SERVICE_NAME}-kiosk.service" <<EOF
[Unit]
Description=News Talent Monitor+ Chromium kiosk
After=${SERVICE_NAME}.service graphical.target
Wants=${SERVICE_NAME}.service

[Service]
Type=simple
User=${SUDO_USER:-pi}
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/${SUDO_USER:-pi}/.Xauthority
ExecStart=${INSTALL_DIR}/deploy/raspberry-pi/start-kiosk.sh
Restart=always
RestartSec=2

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl enable "${SERVICE_NAME}-kiosk.service"
systemctl restart "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}-kiosk.service" || true

echo
echo "Install complete."
echo "Config page: http://127.0.0.1:8010/config"
echo "Display page: http://127.0.0.1:8010/display"
