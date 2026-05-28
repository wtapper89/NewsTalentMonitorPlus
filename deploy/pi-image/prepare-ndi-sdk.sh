#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${ANCHOR_MICS_IMAGE_BUILD_DIR:-${REPO_ROOT}/.pi-image-build}"
SDK_DIR="${BUILD_DIR}/ndi"
DEFAULT_SDK="${HOME}/Downloads/Install_NDI_SDK_v6_Linux.tar.gz"
SOURCE_SDK="${1:-${NDI_SDK_TARBALL:-${DEFAULT_SDK}}}"
DEST_SDK="${SDK_DIR}/Install_NDI_SDK_v6_Linux.tar.gz"

if [ ! -f "${SOURCE_SDK}" ]; then
  echo "NDI SDK archive was not found: ${SOURCE_SDK}" >&2
  echo "Pass the archive path explicitly, or place it at: ${DEFAULT_SDK}" >&2
  exit 1
fi

if ! tar -tf "${SOURCE_SDK}" | grep -q 'Install_NDI_SDK.*_Linux\.sh'; then
  echo "The archive does not look like the NDI Linux SDK installer tarball: ${SOURCE_SDK}" >&2
  exit 1
fi

mkdir -p "${SDK_DIR}"
cp "${SOURCE_SDK}" "${DEST_SDK}"

echo "NDI SDK cached for image builds:"
echo "${DEST_SDK}"
