# Windows Installer EXE

The recommended Windows install is a normal `.exe` installer:

```text
NewsTalentMonitorPlus-Setup.exe
```

It does not include the NDI SDK or NDI runtime. The installer checks for NDI and points the user to the official NDI download if it is missing.

## Install

1. Download `NewsTalentMonitorPlus-Setup.exe`.
2. Double-click it.
3. Leave `Create desktop shortcuts` checked unless you do not want shortcuts.
4. At the end, leave these checked:
   - `Check NDI runtime now`
   - `Start News Talent Monitor+ now`
   - `Open the config page`

Users do not need to run PowerShell scripts.

The installer:

- Installs the packaged `NewsTalentMonitor.exe` app.
- Creates desktop shortcuts for Display and Config.
- Adds News Talent Monitor+ to the current user's Windows Startup folder.
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

To remove the app:

1. Open Windows Settings.
2. Go to `Apps`.
3. Uninstall `News Talent Monitor+`.

## Build The Installer From Source

Use this only if you are creating a release installer.

Install these on the Windows build computer:

- Python 3: `https://www.python.org/downloads/windows/`
- Inno Setup 6: `https://jrsoftware.org/isdl.php`

Then double-click:

```text
Build Windows Installer.bat
```

The builder creates:

```text
dist\windows-installer\NewsTalentMonitorPlus-Setup.exe
```

The Windows user path is the installer EXE. This folder does not include a PowerShell installer.
