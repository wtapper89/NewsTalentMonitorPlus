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
  --exclude '.DS_Store' \
  "${ROOT}/" "${STAGE}/NewsTalentMonitorPlus/"

chmod +x "${STAGE}/NewsTalentMonitorPlus/installers/macos/"*.command
(
  cd "${STAGE}"
  zip -qry "${OUTPUT_DIR}/NewsTalentMonitorPlus-macOS-${VERSION}.zip" NewsTalentMonitorPlus
)

echo "Created ${OUTPUT_DIR}/NewsTalentMonitorPlus-macOS-${VERSION}.zip"
