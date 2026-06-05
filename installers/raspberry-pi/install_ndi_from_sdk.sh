#!/bin/bash
set -euo pipefail

SDK_ARCHIVE="${1:-}"

if [ -z "${SDK_ARCHIVE}" ] || [ ! -f "${SDK_ARCHIVE}" ]; then
  echo "NDI SDK archive not found."
  echo "Expected: ${SDK_ARCHIVE:-no path provided}"
  exit 1
fi

echo
echo "The NDI SDK/runtime is licensed by NDI."
echo "Only continue if you have reviewed and accept the NDI SDK license."

accept_ndi="${NEWS_TALENT_MONITOR_ACCEPT_NDI_LICENSE:-}"
if [ -z "${accept_ndi}" ]; then
  if [ -t 0 ]; then
    read -r -p "Type y to install the NDI runtime from this SDK archive: " accept_ndi
  else
    echo "No interactive terminal is available for the NDI license prompt."
    echo "Skipped NDI runtime install."
    exit 0
  fi
fi

if [ "${accept_ndi}" != "y" ] && [ "${accept_ndi}" != "Y" ]; then
  echo "Skipped NDI runtime install."
  exit 0
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

mkdir -p "${WORK_DIR}/installer" "${WORK_DIR}/sdk"
tar -xzf "${SDK_ARCHIVE}" -C "${WORK_DIR}/installer"

NDI_INSTALLER="$(find "${WORK_DIR}/installer" -type f -name 'Install_NDI_SDK*_Linux.sh' | head -n 1 || true)"
if [ -z "${NDI_INSTALLER}" ]; then
  echo "The archive does not contain the Linux NDI SDK installer."
  exit 1
fi

(
  cd "${WORK_DIR}/sdk"
  printf 'Y\n' | sh "${NDI_INSTALLER}"
)

NDI_LIB="$(find "${WORK_DIR}/sdk" -type f \( -path '*/lib/aarch64-rpi4-linux-gnu/libndi.so.*.*.*' -o -path '*/lib/aarch64-linux-gnu/libndi.so.*.*.*' -o -path '*/lib/arm-rpi4-linux-gnueabihf/libndi.so.*.*.*' -o -path '*/lib/arm-linux-gnueabihf/libndi.so.*.*.*' -o -name 'libndi.so.*.*.*' \) | sort | head -n 1 || true)"
if [ -z "${NDI_LIB}" ]; then
  echo "NDI installer completed, but libndi.so was not found."
  exit 1
fi

install -Dm 0755 "${NDI_LIB}" "/usr/local/lib/$(basename "${NDI_LIB}")"
ln -sf "/usr/local/lib/$(basename "${NDI_LIB}")" /usr/local/lib/libndi.so
ldconfig

echo "NDI runtime installed."
