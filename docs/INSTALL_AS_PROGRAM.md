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

Current install path:

1. Install Python 3 from:

```text
https://www.python.org/downloads/windows/
```

2. Open:

```text
installers/windows
```

3. Double-click:

```text
Install News Talent Monitor.bat
```

The installer:

- Copies the app to `%LOCALAPPDATA%\NewsTalentMonitorPlus`.
- Creates the Python virtual environment.
- Installs Python dependencies.
- Creates desktop shortcuts for Display and Config.
- Creates a Windows startup task so the app starts at login.
- Checks for the NDI runtime.

The app remains a source-based install for now. A future release can wrap this same flow in an Inno Setup, WiX, or MSIX installer.

## macOS Install Direction

Current install path:

1. Install Python 3 from:

```text
https://www.python.org/downloads/macos/
```

2. Open:

```text
installers/macos
```

3. Double-click:

```text
Install News Talent Monitor.command
```

The installer:

- Copies the app to `~/Applications/NewsTalentMonitorPlus`.
- Creates the Python virtual environment.
- Installs Python dependencies.
- Creates a LaunchAgent so the app starts at login.
- Checks for the NDI runtime.

The app remains a source-based install for now. A future release can wrap this same flow in a signed `.pkg` or `.app` bundle.

## NDI Runtime Check

A cross-platform check script is available:

```bash
python tools/ndi/check_ndi_runtime.py
```

Exit codes:

- `0`: runtime found and loadable
- `1`: runtime missing
- `2`: runtime file found but could not be loaded

## Build Shareable Installer Zips

From the repo root on macOS or Linux:

```bash
tools/build_installer_archives.sh 0.1.0
```

That creates:

```text
dist/NewsTalentMonitorPlus-0.1.0-windows.zip
dist/NewsTalentMonitorPlus-0.1.0-macos.zip
```

Those zip files contain the app source, the matching installer scripts, and the docs. They intentionally exclude git history, virtual environments, image-builder cache files, and generated build output.
