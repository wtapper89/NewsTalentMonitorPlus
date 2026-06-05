#!/bin/bash
set -euo pipefail

APP_NAME="News Talent Monitor+"
INSTALL_DIR="${NEWS_TALENT_MONITOR_INSTALL_DIR:-/opt/news-talent-monitor}"
SERVICE_NAME="${NEWS_TALENT_MONITOR_SERVICE_NAME:-news-talent-monitor}"
SOURCE_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-dir)
      if [ -z "${2:-}" ]; then
        echo "--source-dir requires a path"
        exit 1
      fi
      SOURCE_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: sudo bash installers/raspberry-pi/install.sh [--source-dir /path/to/source]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [ -z "${SOURCE_DIR}" ]; then
  SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
CURRENT_DIR="$(cd "${SOURCE_DIR}" && pwd)"

detect_install_user() {
  if [ -n "${NEWS_TALENT_MONITOR_INSTALL_USER:-}" ]; then
    printf '%s\n' "${NEWS_TALENT_MONITOR_INSTALL_USER}"
    return
  fi
  if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    printf '%s\n' "${SUDO_USER}"
    return
  fi

  local login_user
  login_user="$(logname 2>/dev/null || true)"
  if [ -n "${login_user}" ] && [ "${login_user}" != "root" ]; then
    printf '%s\n' "${login_user}"
    return
  fi

  printf '%s\n' "pi"
}

home_for_user() {
  local user_name="$1"
  local home_dir
  home_dir="$(getent passwd "${user_name}" 2>/dev/null | cut -d: -f6 || true)"
  if [ -n "${home_dir}" ]; then
    printf '%s\n' "${home_dir}"
  else
    printf '/home/%s\n' "${user_name}"
  fi
}

echo "${APP_NAME} installer for Raspberry Pi OS"
echo

if [ "$(id -u)" -ne 0 ]; then
  echo "This installer needs administrator permission."
  echo "Run it again with:"
  echo "sudo $0"
  exit 1
fi

INSTALL_USER="$(detect_install_user)"
if ! id "${INSTALL_USER}" >/dev/null 2>&1; then
  echo "Could not find the Raspberry Pi desktop user '${INSTALL_USER}'."
  echo "Run again with:"
  echo "sudo env NEWS_TALENT_MONITOR_INSTALL_USER=<your-pi-user> bash $0"
  exit 1
fi
INSTALL_GROUP="$(id -gn "${INSTALL_USER}")"
INSTALL_HOME="${NEWS_TALENT_MONITOR_USER_HOME:-$(home_for_user "${INSTALL_USER}")}"
SDK_ARCHIVE="${NEWS_TALENT_MONITOR_NDI_SDK:-${INSTALL_HOME}/Downloads/Install_NDI_SDK_v6_Linux.tar.gz}"

echo "Installing for Pi user: ${INSTALL_USER}"
echo "Install folder: ${INSTALL_DIR}"
echo

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
  --exclude "config/system_api_mapping.example.json" \
  --exclude "data/state.json" \
  --exclude "data/*.log" \
  --exclude "__pycache__" \
  "${CURRENT_DIR}/" "${INSTALL_DIR}/"
install -d -o "${INSTALL_USER}" -g "${INSTALL_GROUP}" "${INSTALL_DIR}/data"

echo "Installing Python dependencies..."
python3 -m venv "${INSTALL_DIR}/.venv"
"${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${INSTALL_DIR}/.venv/bin/python" -m pip install -r "${INSTALL_DIR}/requirements.txt"
chown -R "${INSTALL_USER}:${INSTALL_GROUP}" "${INSTALL_DIR}"

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
User=${INSTALL_USER}
Group=${INSTALL_GROUP}
WorkingDirectory=${INSTALL_DIR}
Environment=ANCHOR_MICS_SOURCE=qlxd
Environment=ANCHOR_MICS_HOST=0.0.0.0
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
User=${INSTALL_USER}
Environment=DISPLAY=:0
Environment=XAUTHORITY=${INSTALL_HOME}/.Xauthority
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
