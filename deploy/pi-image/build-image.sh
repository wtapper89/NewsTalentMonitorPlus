#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${ANCHOR_MICS_IMAGE_BUILD_DIR:-${REPO_ROOT}/.pi-image-build}"
PI_GEN_DIR="${BUILD_DIR}/pi-gen"
STAGE_NAME="stage-anchor-mics"
STAGE_DIR="${PI_GEN_DIR}/${STAGE_NAME}"
APP_ARCHIVE="${STAGE_DIR}/00-install/files/anchor-mics.tgz"

mkdir -p "${BUILD_DIR}"

if [ ! -d "${PI_GEN_DIR}/.git" ]; then
  git clone --depth 1 https://github.com/RPi-Distro/pi-gen.git "${PI_GEN_DIR}"
fi

rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}/00-install/files"

rsync -a "${SCRIPT_DIR}/${STAGE_NAME}/" "${STAGE_DIR}/"
tar \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".pi-image-build" \
  --exclude "__pycache__" \
  --exclude "data/anchor-mics.log" \
  -czf "${APP_ARCHIVE}" \
  -C "${REPO_ROOT}" .

if [ -n "${NDI_SDK_TARBALL:-}" ]; then
  if [ "${ACCEPT_NDI_SDK_LICENSE:-0}" != "1" ]; then
    echo "Set ACCEPT_NDI_SDK_LICENSE=1 to confirm you accept the NDI SDK license before bundling it into the image." >&2
    exit 1
  fi
  cp "${NDI_SDK_TARBALL}" "${STAGE_DIR}/00-install/files/ndi-sdk.tar.gz"
fi

cat > "${PI_GEN_DIR}/config" <<'EOF'
IMG_NAME='anchor-mics-pi'
RELEASE='bookworm'
ARCH='arm64'
DEPLOY_COMPRESSION='xz'
ENABLE_SSH=1
LOCALE_DEFAULT='en_US.UTF-8'
TARGET_HOSTNAME='anchor-mics'
FIRST_USER_NAME='pi'
FIRST_USER_PASS='anchor'
STAGE_LIST='stage0 stage1 stage2 stage3 stage4 stage-anchor-mics'
EOF

cd "${PI_GEN_DIR}"
./build-docker.sh

echo
echo "Image build complete. Look in ${PI_GEN_DIR}/deploy for anchor-mics-pi*.img.xz"
