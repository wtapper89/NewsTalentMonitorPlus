# Windows Setup Guide

This guide is for setting up News Talent Monitor+ from a Windows PC, building the Raspberry Pi image, and hosting talent photos from a Windows folder.

The short version:

1. Install Docker Desktop.
2. Install Ubuntu for Windows.
3. Download the NDI SDK Linux archive.
4. Put the SDK archive in the right folder.
5. Run `make-pi-image-windows.bat`.
6. Flash the image with Raspberry Pi Imager.
7. Start the optional Windows photo server.

## What You Need

- Windows 10 or Windows 11 PC
- Internet connection
- Docker Desktop
- Windows Subsystem for Linux with Ubuntu
- Raspberry Pi Imager
- 32 GB or larger microSD card or USB boot drive
- Raspberry Pi 5 recommended
- The NDI SDK Linux archive if you want NDI preview built into the Pi image

Official downloads:

- Docker Desktop for Windows: https://docs.docker.com/desktop/setup/install/windows-install/
- Raspberry Pi Imager: https://www.raspberrypi.com/downloads/
- NDI SDK: https://ndi.video/for-developers/ndi-sdk/download/

## Step 1: Install Docker Desktop

1. Download Docker Desktop for Windows from Docker:

```text
https://docs.docker.com/desktop/setup/install/windows-install/
```

2. Run the installer.
3. When asked, allow Docker to use WSL 2.
4. Restart the PC if the installer asks.
5. Open Docker Desktop.
6. Wait until Docker says it is running.
7. Open Docker Desktop settings and make sure WSL integration is enabled for Ubuntu.

Leave Docker Desktop open while building the Pi image.

## Step 2: Install Ubuntu For Windows

News Talent Monitor+ builds the Pi image with Linux tools. On Windows, the easiest reliable way is Ubuntu through Windows Subsystem for Linux.

1. Right-click the Windows Start button.
2. Open `Terminal` or `PowerShell`.
3. Run:

```powershell
wsl --install -d Ubuntu
```

4. Restart the PC if Windows asks.
5. Open `Ubuntu` from the Start menu once.
6. Let it finish first-time setup.
7. Create the Ubuntu username and password it asks for.
8. Install the small Linux tools used by the image builder:

```bash
sudo apt update
sudo apt install -y git rsync xz-utils
```

You do not need to use Ubuntu day-to-day. The build batch file uses it for you.

## Step 3: Get The Project Folder

Put the News Talent Monitor+ project folder somewhere easy, for example:

```text
C:\NewsTalentMonitor
```

If you downloaded a ZIP from GitHub:

1. Right-click the ZIP.
2. Choose `Extract All`.
3. Put the extracted folder somewhere easy to find.

If you use Git:

```powershell
git clone https://github.com/wtapper89/AnchorMics.git C:\NewsTalentMonitor
```

The internal repository name may still say `AnchorMics`; the product name is News Talent Monitor+.

## Step 4: Download The NDI SDK

Native NDI preview needs the NDI runtime. The project does not include the NDI SDK because it is licensed separately by NDI.

1. Go to:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

2. Download the Linux SDK archive.
3. The file should be named:

```text
Install_NDI_SDK_v6_Linux.tar.gz
```

4. Put that file in your Windows Downloads folder:

```text
C:\Users\<your-windows-user>\Downloads\Install_NDI_SDK_v6_Linux.tar.gz
```

5. Also copy it into this project folder:

```text
C:\NewsTalentMonitor\.pi-image-build\ndi\Install_NDI_SDK_v6_Linux.tar.gz
```

If the `.pi-image-build` or `ndi` folders do not exist yet, create them.

When the image builder asks whether you accept the NDI SDK license for this build, type `y` only if you have reviewed and accept the NDI license.

## Step 5: Build The Raspberry Pi Image

1. Make sure Docker Desktop is open and running.
2. Open the project folder in File Explorer.
3. Double-click:

```text
make-pi-image-windows.bat
```

4. If Windows asks whether to allow it, choose yes.
5. When the NDI license prompt appears, type:

```text
y
```

6. Wait. The first build can take a long time because it downloads Raspberry Pi OS build files.

When it finishes, the Pi image will be in:

```text
C:\NewsTalentMonitor\.pi-image-build\pi-gen\deploy
```

Use the newest file ending in:

```text
.img.xz
```

## Step 6: Flash The Pi Image

1. Install Raspberry Pi Imager:

```text
https://www.raspberrypi.com/downloads/
```

2. Insert the microSD card or USB boot drive into the PC.
3. Open Raspberry Pi Imager.
4. Choose `Raspberry Pi Device`.
5. Choose your Raspberry Pi model.
6. Choose `Operating System`.
7. Choose `Use custom`.
8. Pick the `.img.xz` file from:

```text
C:\NewsTalentMonitor\.pi-image-build\pi-gen\deploy
```

9. Choose the SD card or USB drive.
10. Click `Next` or `Write`.
11. Wait for the write and verify process.

When it finishes, put the card or drive into the Pi and boot it.

## Step 7: First Boot On The Pi

On first boot, the Pi should start the display automatically.

Default image values:

- Hostname: `anchor-mics`
- User: `cci`
- Password: `anchor`
- Display page: `http://127.0.0.1:8010/display`
- Config page: `http://<pi-ip-address>:8010/config`

Change the Pi password after setup if the unit will stay on a production network.

## Step 8: Configure News Talent Monitor+

From another computer on the same network, open:

```text
http://<pi-ip-address>:8010/config
```

Use the tabs:

- `Display`: choose the NDI source.
- `Companion`: enter Companion URL and PGM/PVW variables.
- `Photos`: enter the photo folder URL.
- `Receivers`: leave QLX-D defaults unless needed.
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

### Docker says it is not running

Open Docker Desktop and wait until it finishes starting. Then run `make-pi-image-windows.bat` again.

### The build says docker was not found inside Ubuntu

Open Docker Desktop settings and enable WSL integration for Ubuntu. Then close and reopen Ubuntu, and run `make-pi-image-windows.bat` again.

### The build says git or rsync was not found

Open Ubuntu and run:

```bash
sudo apt update
sudo apt install -y git rsync xz-utils
```

Then run `make-pi-image-windows.bat` again.

### The build says the NDI SDK was not found

Make sure this file exists:

```text
C:\NewsTalentMonitor\.pi-image-build\ndi\Install_NDI_SDK_v6_Linux.tar.gz
```

The file must be the Linux SDK `.tar.gz`, not the Windows installer.

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
