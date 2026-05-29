# Custom Raspberry Pi Image

This folder builds a flashable Raspberry Pi OS image with News Talent Monitor+ installed and configured to boot directly to the HDMI display page.

The output is an `.img.xz` file that can be written with Raspberry Pi Imager using `Choose OS` -> `Use custom`.

## Requirements

- Docker
- Docker Desktop must be open and running before you start the build
- Git
- `rsync`
- Enough disk space for a Raspberry Pi OS image build
- Optional: NDI SDK Linux archive containing `libndi.so`

The builder uses pi-gen's `bookworm-arm64` branch so the image is 64-bit and stays on the stable Raspberry Pi OS Bookworm path for Pi 5.

## Build

From the repo root:

```bash
./make-pi-image.command
```

That command:

- finds `~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz`
- copies it into the untracked build cache at `.pi-image-build/ndi/`
- asks you to confirm the NDI SDK license
- builds the custom Raspberry Pi image with the NDI runtime embedded

If you want to cache the SDK manually first:

```bash
./deploy/pi-image/prepare-ndi-sdk.sh ~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

Then build:

```bash
./make-pi-image.command
```

The lower-level builder still works directly:

```bash
ACCEPT_NDI_SDK_LICENSE=1 NDI_SDK_TARBALL=/path/to/Install_NDI_SDK_v6_Linux.tar.gz ./deploy/pi-image/build-image.sh
```

Or, after the SDK is cached:

```bash
ACCEPT_NDI_SDK_LICENSE=1 ./deploy/pi-image/build-image.sh
```

The image lands under:

```bash
.pi-image-build/pi-gen/deploy/
```

Use the `image_YYYY-MM-DD-anchor-mics-pi.img.xz` file. The builder disables pi-gen's stock stage2/stage4 exports so this image includes `/opt/anchor-mics` and the systemd services.

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
