# Windows Photo Server

Use this only if you want News Talent Monitor+ to show talent headshots from a Windows computer.

For the full first-time setup, start with:

```text
docs/START_HERE.md
```

## What This Does

The Pi can load photos from a normal web address like:

```text
http://10.0.0.50:8090/JohnSmith.png
```

That is easier than Windows file sharing. The included batch files start a simple HTTP server for one folder of photos.

## Step 1: Put Photos In The Folder

Open this folder:

```text
tools\windows-photo-server
```

Put square photos in that folder.

Use filenames without spaces:

```text
JohnSmith.png
JaneDoe.jpg
SportyBallman.jpeg
```

If the display name is `John Smith`, the app looks for:

```text
JohnSmith.png
JohnSmith.jpg
JohnSmith.jpeg
```

## Step 2: Test It Manually

Double-click:

```text
Start Anchor Photo Server.bat
```

A black command window opens. Leave it open while testing.

From another computer, try:

```text
http://<windows-computer-ip>:8090/
```

If you see the folder listing or can open a photo, it is working.

## Step 3: Add It To News Talent Monitor+

Open the Pi config page:

```text
http://<pi-ip-address>:8010/config
```

Go to:

```text
Photos
```

Set:

```text
Enable photos = true
HTTP folder URL = http://<windows-computer-ip>:8090/
```

Save.

## Step 4: Make It Start Automatically

Double-click:

```text
Install Anchor Photo Server.bat
```

This creates a Windows Scheduled Task that starts the photo server when that Windows user logs in.

It runs in the background with no black command window.

If Windows blocks it, right-click the file and choose:

```text
Run as administrator
```

## Stop Auto-Start Later

Double-click:

```text
Uninstall Anchor Photo Server.bat
```

## If It Does Not Work

- Make sure Python is installed on Windows.
- Make sure Windows Firewall allows Python on the production network.
- Use the Windows computer IP address instead of the computer name.
- Try opening one photo directly, such as:

```text
http://<windows-computer-ip>:8090/JohnSmith.png
```
