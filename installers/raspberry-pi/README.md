# Raspberry Pi OS Installer

Use this when you already have Raspberry Pi OS with Desktop installed and want to install News Talent Monitor+ like a program.

## One-Line Install

On the Raspberry Pi, open Terminal and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/wtapper89/NewsTalentMonitorPlus/main/install-pi.sh | bash
```

If `curl` is not available, use:

```bash
wget -qO- https://raw.githubusercontent.com/wtapper89/NewsTalentMonitorPlus/main/install-pi.sh | bash
```

The installer will:

- Download the current News Talent Monitor+ source from GitHub.
- Install the needed Raspberry Pi OS packages with `apt`.
- Install the app to `/opt/news-talent-monitor`.
- Create the Python environment.
- Install and enable the background service.
- Install and enable the fullscreen Chromium kiosk service.
- Install the NDI runtime if the NDI SDK archive is in Downloads and you accept the NDI license prompt.

## NDI SDK Step

1. Download the Linux NDI SDK from:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

2. Put this file in Downloads:

```text
~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

Do this before running the one-line install if you want native NDI preview right away.

News Talent Monitor+ does not bundle the NDI SDK or NDI runtime. The installer only extracts the runtime from the SDK archive after you confirm that you accept the NDI SDK license.

## Desktop Install Option

If you already copied this project folder to the Pi, you can also open this folder:

```text
installers/raspberry-pi
```

Then double-click:

```text
Install News Talent Monitor.desktop
```

Follow the prompts.

## What Gets Installed

- App folder: `/opt/news-talent-monitor`
- Main service: `news-talent-monitor.service`
- Kiosk service: `news-talent-monitor-kiosk.service`
- NDI runtime: `/usr/local/lib/libndi.so`, if the SDK archive is present and accepted
- Web UI: `http://<pi-ip-address>:8010/config`
- Local UI: `http://127.0.0.1:8010/config`

## After Install

Open:

```text
http://127.0.0.1:8010/config
```

or from another computer:

```text
http://<pi-ip-address>:8010/config
```
