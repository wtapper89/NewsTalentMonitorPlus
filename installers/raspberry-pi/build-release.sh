#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-dev}"
OUTPUT_DIR="${ROOT}/dist"
STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT

mkdir -p "${OUTPUT_DIR}" "${STAGE}/NewsTalentMonitorPlus"
rsync -a \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '.installer-build' \
  --exclude '.pi-image-build' \
  --exclude 'build' \
  --exclude 'dist' \
  --exclude '__pycache__' \
  "${ROOT}/" "${STAGE}/NewsTalentMonitorPlus/"

chmod +x \
  "${STAGE}/NewsTalentMonitorPlus/install-pi.sh" \
  "${STAGE}/NewsTalentMonitorPlus/installers/raspberry-pi/"*.sh
tar -C "${STAGE}" -czf "${OUTPUT_DIR}/NewsTalentMonitorPlus-RaspberryPi-${VERSION}.tar.gz" NewsTalentMonitorPlus

echo "Created ${OUTPUT_DIR}/NewsTalentMonitorPlus-RaspberryPi-${VERSION}.tar.gz"
