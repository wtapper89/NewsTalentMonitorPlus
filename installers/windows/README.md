# Windows Installer

This folder contains a simple per-user Windows installer for News Talent Monitor+.

It does not include the NDI SDK or NDI runtime. The installer checks for NDI and points the user to the official NDI download if it is missing.

## Install

1. Install Python 3 from:

```text
https://www.python.org/downloads/windows/
```

2. Open this folder.
3. Double-click:

```text
Install News Talent Monitor.bat
```

The installer:

- Copies the app to `%LOCALAPPDATA%\NewsTalentMonitorPlus`.
- Creates a Python virtual environment.
- Installs Python dependencies.
- Creates a Windows startup task so the app starts when the user logs in.
- Creates desktop shortcuts for Display and Config.
- Checks whether the NDI runtime is installed.

## NDI

News Talent Monitor+ needs the official NDI runtime or SDK for native NDI video.

Download it from:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

Then restart News Talent Monitor+.

## URLs

Display:

```text
http://127.0.0.1:8010/display
```

Config:

```text
http://127.0.0.1:8010/config
```

## Stop Or Uninstall

Use the desktop shortcut named `Stop News Talent Monitor+` to stop the app.

To remove the app, double-click:

```text
Uninstall News Talent Monitor.bat
```

The uninstaller leaves user settings in `%APPDATA%\NewsTalentMonitorPlus` so they are not accidentally lost.
