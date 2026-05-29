# Pi Image Builder

Most people should use:

```text
docs/START_HERE.md
```

This folder is for the image builder used by `make-pi-image.command`.

## Simple Build Steps

1. Install and open Docker Desktop.
2. Download the Linux NDI SDK archive.
3. Put it here:

```text
~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

4. From the repo root, run:

```bash
./make-pi-image.command
```

5. Type `y` when asked to confirm the NDI SDK license.
6. Wait for the build to finish.

The finished image will be in:

```text
.pi-image-build/pi-gen/deploy/
```

Use the newest `.img.xz` file with Raspberry Pi Imager.

## What The Builder Does

- Downloads Raspberry Pi OS build files through pi-gen.
- Copies News Talent Monitor+ into `/opt/anchor-mics`.
- Installs Python dependencies.
- Installs the NDI runtime from the SDK archive.
- Enables the app and kiosk services.
- Produces a flashable `.img.xz`.

## Default Image Values

- Hostname: `anchor-mics`
- User: `cci`
- Password: `anchor`
- App URL on the Pi: `http://127.0.0.1:8010/display`
- Config page from another computer: `http://<pi-ip>:8010/config`

Change the password after first boot if the Pi will stay on a production network.

## NDI License Note

The repo does not include the NDI SDK. You provide the SDK archive yourself.

When you type `y` during the build, you are confirming that you accept the NDI SDK license for embedding the runtime into the image you are creating.
