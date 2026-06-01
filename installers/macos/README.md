# macOS Installer

This folder contains a simple per-user macOS installer for News Talent Monitor+.

It does not include the NDI SDK or NDI runtime. The installer checks for NDI and points the user to the official NDI download if it is missing.

## Install

1. Install Python 3 from:

```text
https://www.python.org/downloads/macos/
```

2. Open this folder in Finder.
3. Double-click:

```text
Install News Talent Monitor.command
```

If macOS blocks the file because it came from the internet, right-click it and choose `Open`.

The installer:

- Copies the app to `~/Applications/NewsTalentMonitorPlus`.
- Creates a Python virtual environment.
- Installs Python dependencies.
- Creates a LaunchAgent so the app starts when the user logs in.
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

After install, the helper commands are in:

```text
~/Applications/NewsTalentMonitorPlus/installers/macos
```

Use:

- `Open Display.command`
- `Open Config.command`
- `stop-server.command`
- `Uninstall News Talent Monitor.command`

The uninstaller leaves user settings in `~/Library/Application Support/NewsTalentMonitorPlus` so they are not accidentally lost.
