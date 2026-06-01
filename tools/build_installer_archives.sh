#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/.installer-build"
VERSION="${1:-dev}"

mkdir -p "${DIST_DIR}"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/NewsTalentMonitorPlus"

rsync -a --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".pi-image-build" \
  --exclude ".installer-build" \
  --exclude "dist" \
  --exclude "__pycache__" \
  --exclude ".DS_Store" \
  "${ROOT_DIR}/" "${BUILD_DIR}/NewsTalentMonitorPlus/"

(
  cd "${BUILD_DIR}"
  zip -qr "${DIST_DIR}/NewsTalentMonitorPlus-${VERSION}-macos.zip" NewsTalentMonitorPlus \
    -x "NewsTalentMonitorPlus/installers/windows/*" \
    -x "NewsTalentMonitorPlus/installers/raspberry-pi/*" \
    -x "NewsTalentMonitorPlus/deploy/pi-image/*"
)

rm -rf "${BUILD_DIR}"

echo "Created:"
echo "${DIST_DIR}/NewsTalentMonitorPlus-${VERSION}-macos.zip"
