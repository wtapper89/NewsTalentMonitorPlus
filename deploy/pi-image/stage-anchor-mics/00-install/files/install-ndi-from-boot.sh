#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/news-talent-monitor-ndi-install.log"
BOOT_DIR="/boot/firmware"
SDK_NAME="Install_NDI_SDK_v6_Linux.tar.gz"
SDK_CANDIDATES=(
  "${BOOT_DIR}/NewsTalentMonitor/${SDK_NAME}"
  "${BOOT_DIR}/${SDK_NAME}"
)
ACCEPT_CANDIDATES=(
  "${BOOT_DIR}/NewsTalentMonitor/ACCEPT_NDI_SDK_LICENSE.txt"
  "${BOOT_DIR}/ACCEPT_NDI_SDK_LICENSE.txt"
)

exec >>"${LOG_FILE}" 2>&1

echo "[$(date -Is)] Checking for NDI SDK runtime install."

if [ -e /usr/local/lib/libndi.so ]; then
  echo "NDI runtime already installed."
  exit 0
fi

SDK_ARCHIVE=""
for candidate in "${SDK_CANDIDATES[@]}"; do
  if [ -f "${candidate}" ]; then
    SDK_ARCHIVE="${candidate}"
    break
  fi
done

if [ -z "${SDK_ARCHIVE}" ]; then
  echo "No NDI SDK archive found on boot partition."
  exit 0
fi

ACCEPT_FILE=""
for candidate in "${ACCEPT_CANDIDATES[@]}"; do
  if [ -f "${candidate}" ]; then
    ACCEPT_FILE="${candidate}"
    break
  fi
done

if [ -z "${ACCEPT_FILE}" ]; then
  echo "NDI SDK archive found, but ACCEPT_NDI_SDK_LICENSE.txt is missing."
  echo "Not installing NDI runtime."
  exit 0
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

mkdir -p "${WORK_DIR}/installer" "${WORK_DIR}/sdk"
tar -xzf "${SDK_ARCHIVE}" -C "${WORK_DIR}/installer"

NDI_INSTALLER="$(find "${WORK_DIR}/installer" -type f -name 'Install_NDI_SDK*_Linux.sh' | head -n 1 || true)"
if [ -z "${NDI_INSTALLER}" ]; then
  echo "NDI SDK archive did not contain the Linux installer script."
  exit 1
fi

(
  cd "${WORK_DIR}/sdk"
  printf 'Y\n' | sh "${NDI_INSTALLER}"
)

NDI_LIB="$(find "${WORK_DIR}/sdk" -type f \( -path '*/lib/aarch64-rpi4-linux-gnu/libndi.so.*.*.*' -o -path '*/lib/aarch64-linux-gnu/libndi.so.*.*.*' -o -path '*/lib/arm-rpi4-linux-gnueabihf/libndi.so.*.*.*' -o -path '*/lib/arm-linux-gnueabihf/libndi.so.*.*.*' -o -name 'libndi.so.*.*.*' \) | sort | head -n 1 || true)"
if [ -z "${NDI_LIB}" ]; then
  echo "NDI SDK installer completed, but libndi.so was not found."
  exit 1
fi

install -Dm 0755 "${NDI_LIB}" "/usr/local/lib/$(basename "${NDI_LIB}")"
ln -sf "/usr/local/lib/$(basename "${NDI_LIB}")" /usr/local/lib/libndi.so
ldconfig

echo "NDI runtime installed from ${SDK_ARCHIVE}."
