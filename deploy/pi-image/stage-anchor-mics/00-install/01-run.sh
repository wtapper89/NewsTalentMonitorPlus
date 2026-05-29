#!/bin/bash
set -e

install -d "${ROOTFS_DIR}/opt/anchor-mics"
tar -xzf files/anchor-mics.tgz -C "${ROOTFS_DIR}/opt/anchor-mics"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${ROOTFS_DIR}/opt/anchor-mics/IMAGE_BUILD_TIME"

install -m 0755 files/start-kiosk.sh "${ROOTFS_DIR}/opt/anchor-mics/deploy/raspberry-pi/start-kiosk.sh"
install -m 0755 files/install-ndi-from-boot.sh "${ROOTFS_DIR}/opt/anchor-mics/deploy/raspberry-pi/install-ndi-from-boot.sh"
install -Dm 0644 files/anchor-mics.service "${ROOTFS_DIR}/etc/systemd/system/anchor-mics.service"
install -Dm 0644 files/anchor-mics-kiosk.service "${ROOTFS_DIR}/etc/systemd/system/anchor-mics-kiosk.service"
install -Dm 0644 files/news-talent-monitor-ndi-install.service "${ROOTFS_DIR}/etc/systemd/system/news-talent-monitor-ndi-install.service"

if [ -f files/ndi-sdk.tar.gz ]; then
  install -d "${ROOTFS_DIR}/tmp/ndi-installer" "${ROOTFS_DIR}/tmp/ndi-sdk"
  tar -xzf files/ndi-sdk.tar.gz -C "${ROOTFS_DIR}/tmp/ndi-installer"
  NDI_INSTALLER="$(find "${ROOTFS_DIR}/tmp/ndi-installer" -type f -name 'Install_NDI_SDK*_Linux.sh' | head -n 1 || true)"
  if [ -z "${NDI_INSTALLER}" ]; then
    echo "NDI SDK archive was provided, but no Linux installer script was found." >&2
    exit 1
  fi

  (
    cd "${ROOTFS_DIR}/tmp/ndi-sdk"
    printf 'Y\n' | sh "${NDI_INSTALLER}"
  )

  NDI_LIB="$(find "${ROOTFS_DIR}/tmp/ndi-sdk" -type f \( -path '*/lib/aarch64-rpi4-linux-gnu/libndi.so.*.*.*' -o -path '*/lib/aarch64-linux-gnu/libndi.so.*.*.*' -o -path '*/lib/arm-rpi4-linux-gnueabihf/libndi.so.*.*.*' -o -path '*/lib/arm-linux-gnueabihf/libndi.so.*.*.*' -o -name 'libndi.so.*.*.*' \) | sort | head -n 1 || true)"
  if [ -n "${NDI_LIB}" ]; then
    install -Dm 0755 "${NDI_LIB}" "${ROOTFS_DIR}/usr/local/lib/$(basename "${NDI_LIB}")"
    ln -sf "/usr/local/lib/$(basename "${NDI_LIB}")" "${ROOTFS_DIR}/usr/local/lib/libndi.so"
  else
    echo "NDI SDK archive was provided, but no libndi.so file was found." >&2
    exit 1
  fi
fi

on_chroot <<'EOF'
set -e
cd /opt/anchor-mics
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
chown -R cci:cci /opt/anchor-mics
ldconfig
systemctl enable anchor-mics.service
systemctl enable anchor-mics-kiosk.service
systemctl enable news-talent-monitor-ndi-install.service
EOF

rm -rf "${ROOTFS_DIR}/tmp/ndi-installer" "${ROOTFS_DIR}/tmp/ndi-sdk"
