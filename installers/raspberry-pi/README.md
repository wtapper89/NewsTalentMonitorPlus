# Raspberry Pi OS Installer

Use this when you already have Raspberry Pi OS with Desktop installed and want to install News Talent Monitor+ like a program.

## Simple Steps

1. Download the Linux NDI SDK from:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

2. Put this file in Downloads:

```text
~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

3. Open this folder on the Pi:

```text
installers/raspberry-pi
```

4. Double-click:

```text
Install News Talent Monitor.desktop
```

5. Follow the prompts.

## What Gets Installed

- App folder: `/opt/news-talent-monitor`
- Main service: `news-talent-monitor.service`
- Kiosk service: `news-talent-monitor-kiosk.service`
- NDI runtime: `/usr/local/lib/libndi.so`, if the SDK archive is present and accepted

## After Install

Open:

```text
http://127.0.0.1:8010/config
```

or from another computer:

```text
http://<pi-ip-address>:8010/config
```
