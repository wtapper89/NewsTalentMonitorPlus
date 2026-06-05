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
- They want the fastest command-line install.
- They do not want to build a custom Pi image.

Steps:

1. Download the Linux NDI SDK:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

2. Put this file in the Pi user's Downloads folder:

```text
~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

3. Open Terminal on the Pi.
4. Paste:

```bash
curl -fsSL https://raw.githubusercontent.com/wtapper89/NewsTalentMonitorPlus/main/install-pi.sh | bash
```

If `curl` is not available:

```bash
wget -qO- https://raw.githubusercontent.com/wtapper89/NewsTalentMonitorPlus/main/install-pi.sh | bash
```

The installer:

- Downloads the current source from GitHub.
- Installs system packages with `apt`.
- Copies the app to `/opt/news-talent-monitor`.
- Creates a Python virtual environment.
- Installs Python dependencies.
- Installs the NDI runtime from the SDK archive if the user accepts the NDI license prompt.
- Installs systemd services.
- Opens the configured kiosk page at boot.

## Raspberry Pi OS Desktop Install

If someone already downloaded or copied this project folder to the Pi, they can use the desktop installer instead.

1. Open:

```text
installers/raspberry-pi
```

2. Double-click:

```text
Install News Talent Monitor.desktop
```

3. Follow the prompts.

## Windows Install Direction

Current install path:

1. Download:

```text
NewsTalentMonitorPlus-Setup.exe
```

2. Double-click it.
3. Let it start News Talent Monitor+ and open the config page.

The installer:

- Installs the packaged `NewsTalentMonitor.exe`.
- Creates desktop shortcuts for Display and Config.
- Adds News Talent Monitor+ to the current user's Windows Startup folder.
- Checks for the NDI runtime.

Users do not need to run PowerShell scripts.

To build the installer from source on Windows, install Python 3 and Inno Setup 6, then run:

```text
installers\windows\Build Windows Installer.bat
```

That creates:

```text
dist\windows-installer\NewsTalentMonitorPlus-Setup.exe
```

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

## Build Shareable macOS Zip

From the repo root on macOS or Linux:

```bash
tools/build_installer_archives.sh 0.1.0
```

That creates:

```text
dist/NewsTalentMonitorPlus-0.1.0-macos.zip
```

The macOS zip contains the app source, the macOS installer scripts, and the docs. It intentionally excludes git history, virtual environments, image-builder cache files, and generated build output.

Windows releases should use the `.exe` installer created by:

```text
installers\windows\Build Windows Installer.bat
```
