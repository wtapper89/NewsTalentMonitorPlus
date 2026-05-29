# Windows Setup Guide

This guide is for getting News Talent Monitor+ running from a Windows PC without installing Ubuntu or building the image yourself.

The normal setup path is:

1. Download Raspberry Pi Imager.
2. Download the prepared News Talent Monitor+ Pi image.
3. Flash the image with Raspberry Pi Imager.
4. Copy the NDI SDK archive onto the flashed boot drive if you need NDI preview.
5. Boot the Pi.
6. Open the config page and finish setup.
7. Optionally start the Windows photo server.

## What You Need

- Windows 10 or Windows 11 PC
- Raspberry Pi Imager
- Prepared News Talent Monitor+ `.img.xz` image
- 32 GB or larger microSD card or USB boot drive
- Raspberry Pi 5 recommended
- NDI SDK Linux archive if you want native NDI preview
- Optional: Python on Windows if you want to host talent photos from the PC

Downloads:

- Raspberry Pi Imager: https://www.raspberrypi.com/software/
- NDI SDK: https://ndi.video/for-developers/ndi-sdk/download/
- Python for Windows: https://www.python.org/downloads/windows/

## Step 1: Download Raspberry Pi Imager

1. Go to:

```text
https://www.raspberrypi.com/software/
```

2. Download `Raspberry Pi Imager` for Windows.
3. Run the installer.
4. Open Raspberry Pi Imager once it is installed.

## Step 2: Download The News Talent Monitor+ Pi Image

Download the latest prepared `.img.xz` image from the project release or from the person maintaining your station build.

The file should look similar to:

```text
news-talent-monitor-pi.img.xz
```

or:

```text
image_YYYY-MM-DD-anchor-mics-pi.img.xz
```

Save it somewhere easy to find, such as:

```text
Downloads
```

Do not unzip the `.img.xz` file. Raspberry Pi Imager can use it directly.

## Step 3: Flash The Image With Raspberry Pi Imager

1. Insert the microSD card or USB boot drive into the Windows PC.
2. Open Raspberry Pi Imager.
3. Choose `Raspberry Pi Device`.
4. Choose your Raspberry Pi model.
5. Choose `Operating System`.
6. Choose `Use custom`.
7. Pick the News Talent Monitor+ `.img.xz` file.
8. Choose the SD card or USB drive.
9. Click `Next` or `Write`.
10. Wait for the write and verify process to finish.

When Imager finishes, Windows may show a small drive named `bootfs` or `boot`. Leave it plugged in for the NDI step below.

## Step 4: Add The NDI SDK To The Boot Drive

Native NDI preview needs the NDI runtime. The project does not include the NDI SDK because it is licensed separately by NDI.

If you do not need NDI preview, skip this step.

1. Go to:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

2. Download the Linux SDK archive.
3. The file should be named:

```text
Install_NDI_SDK_v6_Linux.tar.gz
```

4. Open the flashed Pi boot drive in File Explorer. It is usually named `bootfs` or `boot`.
5. Create this folder on that boot drive:

```text
NewsTalentMonitor
```

6. Copy the SDK archive into that folder:

```text
NewsTalentMonitor\Install_NDI_SDK_v6_Linux.tar.gz
```

7. In the same `NewsTalentMonitor` folder, create a text file named:

```text
ACCEPT_NDI_SDK_LICENSE.txt
```

8. Put this text inside that file:

```text
I have reviewed and accept the NDI SDK license for this local installation.
```

This marker is required so the Pi does not install the NDI runtime unless someone intentionally accepts the NDI SDK license.

## Step 5: Boot The Pi

1. Safely eject the SD card or USB drive from Windows.
2. Put it into the Raspberry Pi.
3. Connect HDMI to the camera-front monitor or setup monitor.
4. Connect the Pi to the production network.
5. Power on the Pi.

On first boot, the Pi checks the boot drive for:

```text
NewsTalentMonitor\Install_NDI_SDK_v6_Linux.tar.gz
NewsTalentMonitor\ACCEPT_NDI_SDK_LICENSE.txt
```

If both files are present, it installs the NDI runtime automatically. The log is on the Pi at:

```text
/var/log/news-talent-monitor-ndi-install.log
```

Default image values:

- Hostname: `anchor-mics`
- User: `cci`
- Password: `anchor`
- Display page on the Pi: `http://127.0.0.1:8010/display`
- Config page from another computer: `http://<pi-ip-address>:8010/config`

Change the Pi password after setup if the unit will stay on a production network.

## Step 6: Open The Config Page

From the Windows PC, open a browser and go to:

```text
http://<pi-ip-address>:8010/config
```

If you do not know the Pi IP address, check your router/DHCP server, or open Terminal on the Pi and run:

```bash
hostname -I
```

## Step 7: Configure The Display

Use the config tabs:

- `Display`: choose `Preview mode = ndi`, click `Scan`, pick the vMix NDI source, and save.
- `Companion`: enter the Companion URL and the PGM/PVW variables.
- `Photos`: enter the photo folder URL if using headshots.
- `Receivers`: leave QLX-D defaults unless you know you need something else.
- `Mics`: enter each Shure receiver IP and assignment variable.

Click `Save configuration`.

## Optional: Host Talent Photos From Windows

This is the easiest way to show anchor/talent pictures without dealing with Windows file sharing.

### Prepare The Photo Folder

1. Open:

```text
tools\windows-photo-server
```

2. Put the talent photos in that folder.
3. Use square pictures if possible.
4. Name files with no spaces.

Examples:

```text
JohnSmith.png
JaneDoe.jpg
SportyBallman.jpeg
```

If the mic assignment says `John Smith`, the app looks for `JohnSmith.png`, `JohnSmith.jpg`, or `JohnSmith.jpeg`.

### Start The Photo Server Manually

Double-click:

```text
Start Anchor Photo Server.bat
```

Leave the black command window open. The photos will be served at:

```text
http://<windows-computer-name>:8090/
```

or:

```text
http://<windows-computer-ip>:8090/
```

Enter that URL in Config -> Photos -> `HTTP folder URL`.

### Make The Photo Server Start Automatically

Double-click:

```text
Install Anchor Photo Server.bat
```

What it does:

- Creates a Windows Scheduled Task.
- Starts the server when that Windows user logs in.
- Runs the server in the background with no command window.
- Uses port `8090`.

If Windows blocks it, right-click the file and choose `Run as administrator`.

To remove the startup task later, double-click:

```text
Uninstall Anchor Photo Server.bat
```

## Common Problems

### The Pi display opens but NDI is blank

Open:

```text
http://<pi-ip-address>:8010/config
```

Then:

1. Go to `Display`.
2. Click `Scan`.
3. Pick the vMix NDI source.
4. Save.

Also confirm the Pi and vMix computer are on the same network.

### The NDI source still does not work

Confirm the SDK files were copied before the Pi first booted:

```text
NewsTalentMonitor\Install_NDI_SDK_v6_Linux.tar.gz
NewsTalentMonitor\ACCEPT_NDI_SDK_LICENSE.txt
```

On the Pi, check:

```bash
ls -l /usr/local/lib/libndi.so
cat /var/log/news-talent-monitor-ndi-install.log
```

### Photos do not show

Try opening the photo folder URL in a browser:

```text
http://<windows-computer-ip>:8090/JohnSmith.png
```

If that does not load, check Windows Firewall or make sure the photo server is running.

### The Pi config page will not open

Find the Pi IP address from your router, DHCP server, or by opening Terminal on the Pi and running:

```bash
hostname -I
```

Then open:

```text
http://<that-ip-address>:8010/config
```

## Advanced: Building The Image Yourself

Most users should not build the Pi image. They should use the prepared `.img.xz` with Raspberry Pi Imager.

If you are maintaining the project and need to build a new image, use a Mac or Linux machine with Docker and follow:

```text
deploy/pi-image/README.md
```
