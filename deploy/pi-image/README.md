# Custom Raspberry Pi Image

This folder builds a flashable Raspberry Pi OS image with Anchor Mics installed and configured to boot directly to the HDMI display page.

The output is an `.img.xz` file that can be written with Raspberry Pi Imager using `Choose OS` -> `Use custom`.

## Requirements

- Docker
- Git
- `rsync`
- Enough disk space for a Raspberry Pi OS image build
- Optional: NDI SDK Linux archive containing `libndi.so`

## Build

From the repo root:

```bash
./deploy/pi-image/build-image.sh
```

With the NDI runtime included:

```bash
ACCEPT_NDI_SDK_LICENSE=1 NDI_SDK_TARBALL=/path/to/Install_NDI_SDK_v6_Linux.tar.gz ./deploy/pi-image/build-image.sh
```

For the SDK archive currently on this Mac:

```bash
ACCEPT_NDI_SDK_LICENSE=1 NDI_SDK_TARBALL=/Users/wtapper/Downloads/Install_NDI_SDK_v6_Linux.tar.gz ./deploy/pi-image/build-image.sh
```

The image lands under:

```bash
.pi-image-build/pi-gen/deploy/
```

## Default Image Behavior

- Hostname: `anchor-mics`
- User: `pi`
- Password: `anchor`
- App URL: `http://127.0.0.1:8010/display`
- Config GUI: `http://<pi-ip>:8010/config`

Change the password after first boot.

## NDI Notes

The app uses the NDI SDK runtime dynamically through `libndi.so`. The repo does not include the SDK runtime because it is proprietary.

If you build without `NDI_SDK_TARBALL`, the image still boots and runs the app, but the NDI preview endpoint will report that the NDI runtime is missing until you install it on the Pi.
