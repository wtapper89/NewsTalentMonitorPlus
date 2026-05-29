#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${ANCHOR_MICS_IMAGE_BUILD_DIR:-${SCRIPT_DIR}/.pi-image-build}"
CACHED_SDK="${BUILD_DIR}/ndi/Install_NDI_SDK_v6_Linux.tar.gz"
DOWNLOADS_SDK="${HOME}/Downloads/Install_NDI_SDK_v6_Linux.tar.gz"

cd "${SCRIPT_DIR}"

echo "News Talent Monitor+ Raspberry Pi image builder"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not on PATH."
  echo "Install Docker Desktop, open it once, then run this command again."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed, but Docker Desktop is not running."
  echo
  echo "Open Docker Desktop and wait until it says the engine is running, then run:"
  echo "${SCRIPT_DIR}/make-pi-image.command"
  exit 1
fi

if [ ! -f "${CACHED_SDK}" ]; then
  if [ -f "${NDI_SDK_TARBALL:-}" ]; then
    ./deploy/pi-image/prepare-ndi-sdk.sh "${NDI_SDK_TARBALL}"
  elif [ -f "${DOWNLOADS_SDK}" ]; then
    ./deploy/pi-image/prepare-ndi-sdk.sh "${DOWNLOADS_SDK}"
  else
    echo "NDI SDK archive not found."
    echo "Expected: ${DOWNLOADS_SDK}"
    echo
    read -r -p "Build the Pi image without embedded NDI runtime? [y/N] " build_without_ndi
    case "${build_without_ndi}" in
      y|Y|yes|YES) ;;
      *) echo "Stopped."; exit 1 ;;
    esac
  fi
fi

if [ -f "${CACHED_SDK}" ]; then
  if [ "${ACCEPT_NDI_SDK_LICENSE:-0}" != "1" ]; then
    echo "The NDI SDK will be embedded from:"
    echo "${CACHED_SDK}"
    echo
    read -r -p "Type y to confirm you accept the NDI SDK license for this build: " accept_ndi
    if [ "${accept_ndi}" != "y" ] && [ "${accept_ndi}" != "Y" ]; then
      echo "Stopped."
      exit 1
    fi
    export ACCEPT_NDI_SDK_LICENSE=1
  fi
  export NDI_SDK_TARBALL="${CACHED_SDK}"
fi

./deploy/pi-image/build-image.sh

echo
echo "Done. Flash the newest .img.xz from:"
echo "${BUILD_DIR}/pi-gen/deploy"
