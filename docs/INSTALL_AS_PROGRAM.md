# Install As A Program

This is the direction for News Talent Monitor+ going forward: install it like an app instead of asking every user to create a custom Raspberry Pi image.

## NDI SDK Answer

Do **not** bundle the NDI SDK archive or NDI runtime inside this repo or inside a general public installer.

The safer install flow is:

1. Check whether the NDI runtime is already installed.
2. If it is missing, show the user where to download the official NDI SDK/runtime.
3. Ask the user to provide the SDK archive or run the official installer.
4. Ask the user to confirm they accept the NDI SDK license.
5. Install or link the runtime after that confirmation.

That is the approach used by the Raspberry Pi OS installer in this repo.

## Raspberry Pi OS GUI Install

Target user:

- Someone has installed Raspberry Pi OS with Desktop.
- They downloaded or copied this project folder to the Pi.
- They want to double-click an installer.

Steps:

1. Download the Linux NDI SDK:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

2. Put this file in the Pi user's Downloads folder:

```text
~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

3. Open the project folder on the Pi.
4. Open:

```text
installers/raspberry-pi
```

5. Double-click:

```text
Install News Talent Monitor.desktop
```

6. Follow the prompts.

The installer:

- Installs system packages.
- Copies the app to `/opt/news-talent-monitor`.
- Creates a Python virtual environment.
- Installs Python dependencies.
- Installs the NDI runtime from the SDK archive if the user accepts the NDI license prompt.
- Installs systemd services.
- Opens the kiosk display at boot.

## Windows Install Direction

Recommended package format:

- Build a Windows installer with a packaged Python app.
- Do not include the NDI SDK.
- During install or first launch, run the NDI runtime check.
- If missing, direct the user to the official NDI runtime/SDK download or run an official redistributable if allowed by the NDI license.

Current repo status:

- Windows photo-server helper batch files exist.
- Full Windows app packaging is not implemented yet.

## macOS Install Direction

Recommended package format:

- Build a `.app` bundle or signed `.pkg`.
- Do not include the NDI SDK.
- During first launch, check common NDI runtime paths.
- If missing, direct the user to install the official NDI runtime/SDK.

Current repo status:

- macOS app packaging is not implemented yet.

## NDI Runtime Check

A cross-platform check script is available:

```bash
python tools/ndi/check_ndi_runtime.py
```

Exit codes:

- `0`: runtime found and loadable
- `1`: runtime missing
- `2`: runtime file found but could not be loaded
