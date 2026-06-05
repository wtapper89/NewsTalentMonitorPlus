#!/bin/bash
set -euo pipefail

APP_NAME="News Talent Monitor+"
REPO_TARBALL_URL="${NEWS_TALENT_MONITOR_TARBALL_URL:-https://github.com/wtapper89/NewsTalentMonitorPlus/archive/refs/heads/main.tar.gz}"

detect_install_user() {
  if [ -n "${NEWS_TALENT_MONITOR_INSTALL_USER:-}" ]; then
    printf '%s\n' "${NEWS_TALENT_MONITOR_INSTALL_USER}"
    return
  fi
  if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    printf '%s\n' "${SUDO_USER}"
    return
  fi
  if [ "$(id -u)" -ne 0 ] && [ -n "${USER:-}" ]; then
    printf '%s\n' "${USER}"
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

download_to() {
  local url="$1"
  local output_path="$2"

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}" -o "${output_path}"
    return
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -qO "${output_path}" "${url}"
    return
  fi

  echo "curl or wget is required. Installing curl first..."
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update
    apt-get install -y --no-install-recommends curl ca-certificates
  else
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends curl ca-certificates
  fi
  curl -fsSL "${url}" -o "${output_path}"
}

run_with_sudo() {
  local install_user="$1"
  local install_home="$2"
  local installer_path="$3"
  local source_dir="$4"

  if [ "$(id -u)" -eq 0 ]; then
    if [ -r /dev/tty ]; then
      env \
        NEWS_TALENT_MONITOR_INSTALL_USER="${install_user}" \
        NEWS_TALENT_MONITOR_USER_HOME="${install_home}" \
        bash "${installer_path}" --source-dir "${source_dir}" < /dev/tty
    else
      env \
        NEWS_TALENT_MONITOR_INSTALL_USER="${install_user}" \
        NEWS_TALENT_MONITOR_USER_HOME="${install_home}" \
        bash "${installer_path}" --source-dir "${source_dir}"
    fi
    return
  fi

  if [ -r /dev/tty ]; then
    sudo env \
      NEWS_TALENT_MONITOR_INSTALL_USER="${install_user}" \
      NEWS_TALENT_MONITOR_USER_HOME="${install_home}" \
      bash "${installer_path}" --source-dir "${source_dir}" < /dev/tty
  else
    sudo env \
      NEWS_TALENT_MONITOR_INSTALL_USER="${install_user}" \
      NEWS_TALENT_MONITOR_USER_HOME="${install_home}" \
      bash "${installer_path}" --source-dir "${source_dir}"
  fi
}

echo "${APP_NAME} Raspberry Pi command-line installer"
echo

INSTALL_USER="$(detect_install_user)"
if ! id "${INSTALL_USER}" >/dev/null 2>&1; then
  echo "Could not find the Raspberry Pi desktop user '${INSTALL_USER}'."
  echo "Run again with:"
  echo "NEWS_TALENT_MONITOR_INSTALL_USER=<your-pi-user> bash install-pi.sh"
  exit 1
fi

INSTALL_HOME="${NEWS_TALENT_MONITOR_USER_HOME:-$(home_for_user "${INSTALL_USER}")}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

ARCHIVE_PATH="${WORK_DIR}/news-talent-monitor.tar.gz"
SOURCE_DIR="${WORK_DIR}/source"

echo "Downloading installer from GitHub..."
download_to "${REPO_TARBALL_URL}" "${ARCHIVE_PATH}"

mkdir -p "${SOURCE_DIR}"
tar -xzf "${ARCHIVE_PATH}" -C "${SOURCE_DIR}" --strip-components=1

INSTALLER_PATH="${SOURCE_DIR}/installers/raspberry-pi/install.sh"
if [ ! -f "${INSTALLER_PATH}" ]; then
  echo "Downloaded source did not include ${INSTALLER_PATH}."
  exit 1
fi

echo "Installing for Pi user: ${INSTALL_USER}"
echo "Looking for the NDI SDK at: ${INSTALL_HOME}/Downloads/Install_NDI_SDK_v6_Linux.tar.gz"
echo

run_with_sudo "${INSTALL_USER}" "${INSTALL_HOME}" "${INSTALLER_PATH}" "${SOURCE_DIR}"
