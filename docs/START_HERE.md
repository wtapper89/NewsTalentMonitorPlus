# Start Here

This is the simplest from-scratch setup path for News Talent Monitor+.

There are two separate jobs:

1. **Create the Pi image**  
   This makes the custom `.img.xz` file with News Talent Monitor+ and the NDI SDK runtime inside it.

2. **Flash the Pi image**  
   This uses Raspberry Pi Imager to put that `.img.xz` file onto a microSD card or USB drive.

Raspberry Pi Imager does not create the custom image. It only writes an already-created image to the card.

If you are the person making the master image for everyone else, do **Part 1**.

If someone already gave you the `.img.xz` file, skip to **Part 2**.

## What You Need To Download

Download these first:

- Docker Desktop: https://www.docker.com/products/docker-desktop/
- Raspberry Pi Imager: https://www.raspberrypi.com/software/
- NDI SDK: https://ndi.video/for-developers/ndi-sdk/download/

You also need:

- Raspberry Pi 5 recommended
- 32 GB or larger microSD card or USB boot drive
- A computer with enough free disk space for the image build
- The News Talent Monitor+ project folder

## Part 1: Create The Pi Image With NDI Built In

Do this part on the computer that will create the master image.

For the simplest build, use a Mac or Linux computer with Docker Desktop. Windows computers should normally use Raspberry Pi Imager with a finished `.img.xz` file instead of building the image.

### Step 1: Install Docker Desktop

1. Download Docker Desktop:

```text
https://www.docker.com/products/docker-desktop/
```

2. Install it.
3. Open Docker Desktop.
4. Wait until Docker says it is running.

Keep Docker Desktop open during the image build.

### Step 2: Download The NDI SDK

1. Go to:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

2. Download the **Linux** SDK.
3. The file should be named:

```text
Install_NDI_SDK_v6_Linux.tar.gz
```

4. Put that exact file in your Downloads folder.

On Mac, that usually means:

```text
~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

Do not unzip it.

### Step 3: Run The Image Builder

Open the News Talent Monitor+ project folder.

On Mac:

1. Double-click:

```text
make-pi-image.command
```

2. If macOS asks whether to allow it, choose allow/open.
3. When asked to accept the NDI SDK license for this build, type:

```text
y
```

4. Wait for the build to finish.

The first build can take a long time. That is normal.

### Step 4: Find The Finished Image

When the build finishes, it tells you where the image is.

Look in:

```text
.pi-image-build/pi-gen/deploy
```

Use the newest file ending in:

```text
.img.xz
```

That is the finished Raspberry Pi image.

## Part 2: Flash The Image With Raspberry Pi Imager

Do this part on any computer with Raspberry Pi Imager and an SD card reader.

### Step 1: Install Raspberry Pi Imager

Download it here:

```text
https://www.raspberrypi.com/software/
```

Install it and open it.

### Step 2: Choose The Custom Image

1. Insert the microSD card or USB boot drive.
2. In Raspberry Pi Imager, choose your Raspberry Pi model.
3. Choose `Operating System`.
4. Choose `Use custom`.
5. Pick the `.img.xz` file from:

```text
.pi-image-build/pi-gen/deploy
```

6. Choose the SD card or USB drive.
7. Click `Write`.
8. Wait for Imager to finish writing and verifying.

When it finishes, eject the card or drive.

## Part 3: Boot The Pi

1. Put the card or USB drive into the Raspberry Pi.
2. Connect HDMI to the monitor.
3. Connect the Pi to the production network.
4. Power on the Pi.

The Pi should open News Talent Monitor+ automatically.

Default login:

```text
Username: cci
Password: anchor
```

Config page:

```text
http://<pi-ip-address>:8010/config
```

Display page:

```text
http://<pi-ip-address>:8010/display
```

## Part 4: Basic App Setup

Open the config page:

```text
http://<pi-ip-address>:8010/config
```

Then use the tabs:

### Display

1. Set `Preview mode` to `ndi`.
2. Click `Scan`.
3. Pick your vMix NDI output.
4. Save.

### Companion

1. Set `Enable Companion polling` to `true`.
2. Enter the Companion computer address, for example:

```text
http://10.0.0.50:8000
```

3. Enter your PGM variable in `PGM / Now source variable`.
4. Enter your PVW variable in `PVW / Next source variable`.
5. Save.

Examples:

```text
vmix:mix_1_program_full_title
vmix:mix_1_preview_full_title
```

### Mics

For each mic:

1. Enter the Shure receiver IP address.
2. Leave `Scheme` as `tcp`.
3. Leave `Port` as `2202`.
4. Enter a Companion assignment variable if you want names to come from Companion.
5. Save.

### Photos

If you want talent photos:

1. Host a photo folder from Windows using the batch files in:

```text
tools/windows-photo-server
```

2. Enter that folder URL in `HTTP folder URL`.
3. Save.

## Windows Photo Server

Put photos in:

```text
tools\windows-photo-server
```

Name them without spaces:

```text
JohnSmith.png
JaneDoe.jpg
```

To test manually, double-click:

```text
Start Anchor Photo Server.bat
```

To make it start in the background when Windows logs in, double-click:

```text
Install Anchor Photo Server.bat
```

Use this URL in the app:

```text
http://<windows-computer-ip>:8090/
```

## Important NDI License Note

The project does not include the NDI SDK. You download it yourself from NDI.

When you type `y` during the image build, you are confirming that you accept the NDI SDK license for embedding the runtime into that local Pi image.

NDI SDK:

```text
https://ndi.video/for-developers/ndi-sdk/download/
```

NDI licensing information:

```text
https://docs.ndi.video/all/developing-with-ndi/sdk/licensing
```

## If Something Does Not Work

### Docker is not running

Open Docker Desktop and wait until it says it is running. Then run `make-pi-image.command` again.

### The builder cannot find the NDI SDK

Make sure this file exists:

```text
~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz
```

### The Pi boots but NDI is blank

Open:

```text
http://<pi-ip-address>:8010/config
```

Then go to `Display`, click `Scan`, choose the NDI source, and save.

### You do not know the Pi IP address

Open Terminal on the Pi and run:

```bash
hostname -I
```
