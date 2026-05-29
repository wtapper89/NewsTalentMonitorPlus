# Anchor Mics

Anchor Mics is a Raspberry Pi display for church production teams. It shows a large program preview, the current and next rundown source, and the status of each wireless mic so a volunteer can quickly see who is assigned, which mics are on, and whether any battery or receiver problem needs attention.

The normal setup is:

- A Raspberry Pi connected to the booth monitor or confidence display
- Shure QLX-D receivers on the same network
- Bitfocus Companion for names and rundown variables
- vMix or another NDI source for the large preview window
- Optional anchor or pastor headshots served from a simple web folder

## Daily Use

1. Power on the Raspberry Pi.
2. Wait for the fullscreen display to open.
3. Confirm the large preview is showing the expected vMix or NDI output.
4. Confirm the green `Now` box and yellow `Next` box show the right rundown items.
5. Check the mic boxes at the bottom:
   - Green means the mic is online and healthy.
   - Yellow means something needs attention.
   - Red means the mic or transmitter is unavailable.
6. Tap the hamburger button in the upper-right corner to open the config page.

## First Setup

Open the config page from the Pi:

```text
http://anchor-mics.local:8010/config
```

If that does not work, use the Pi IP address:

```text
http://<pi-ip-address>:8010/config
```

The config page is organized into tabs.

### Display Tab

Use this tab for the large video preview.

- `Preview mode`: choose `ndi` for vMix or another NDI source.
- `NDI source name`: click `Scan`, then choose the source you want displayed.
- `Preview URL`: leave blank when using NDI.
- `Font family`: leave the default unless you installed a specific font on the Pi.

Save after choosing the NDI source.

### Companion Tab

Use this tab when Companion should provide names for the top rundown boxes and mic assignments.

- `Enable Companion polling`: set to `true`.
- `Companion base URL`: enter the Companion computer URL, such as `http://10.0.0.50:8000`.
- `Default connection label`: enter the Companion connection label used for variables, such as `vmix` or `custom`.
- `PGM / Now source variable`: variable shown in the green `Now` box.
- `PVW / Next source variable`: variable shown in the yellow `Next` box.

Variable examples:

```text
vmix:mix_1_program_full_title
vmix:mix_1_preview_full_title
$(vmix:mix_1_program_full_title)
```

For mic names, each mic row has a `Companion assignment variable`. If that variable returns `John Smith`, the display uses `John Smith` instead of `Mic 1`.

### Photos Tab

Use this tab for square headshots beside anchor names.

Recommended method:

1. Put photos in a folder on the vMix or Companion computer.
2. Name files without spaces, such as:

```text
JohnSmith.png
JaneDoe.jpg
```

3. Start a simple web server for that folder.
4. Enter the folder URL in `HTTP folder URL`, such as:

```text
http://10.0.0.50:8090/
```

If the mic assignment is `John Smith`, Anchor Mics looks for files like `JohnSmith.png`, `JohnSmith.jpg`, and `JohnSmith.jpeg`.

### Receivers Tab

For normal Shure QLX-D polling:

- `Default scheme`: `tcp`
- `Default port`: `2202`
- `Auth type`: `none`

The token fields are only for a custom Shure System API setup. Most churches can leave them blank.

### Mics Tab

Add one row for each mic you want on the display.

Important fields:

- `Display label`: fallback name when no Companion assignment is available.
- `Assigned to`: manual fallback person name.
- `Companion assignment variable`: variable that returns the assigned person.
- `Receiver label`: friendly label, such as `Rack A`.
- `Channel`: friendly channel label, such as `MIC 1`.
- `Device IP / host`: the Shure receiver IP address or hostname.
- `Receiver channel`: usually `1` for a single-channel QLX-D receiver.
- `Scheme`: `tcp`
- `Port`: `2202`

Save when finished.

## Photo Server on Windows

If you want an easy public photo folder on Windows, open Command Prompt in the photo folder and run:

```bat
python -m http.server 8090
```

Then enter this in the Photos tab:

```text
http://<windows-computer-ip>:8090/
```

To start it automatically with Windows, use the batch file in:

```text
tools/windows-photo-server/
```

## Testing

After saving config:

1. Open the fullscreen display:

```text
http://<pi-ip-address>:8010/display
```

2. Confirm the NDI preview is moving.
3. Confirm Now and Next match Companion or vMix.
4. Turn one mic transmitter on and off to confirm the tile changes.
5. Change a Companion mic assignment and confirm the display updates.

## Troubleshooting

### The preview is red or blank

- Open Config -> Display.
- Click `Scan` and choose the NDI source again.
- Make sure the Pi and vMix computer are on the same network.
- Check NDI status from:

```text
http://<pi-ip-address>:8010/api/ndi/status
```

### Now or Next is blank

- Open Config -> Companion.
- Confirm Companion polling is enabled.
- Confirm the Companion base URL is reachable from the Pi.
- Confirm the PGM and PVW variable names are correct.
- If using a prefixed variable, use a form like `vmix:variable_name`.

### Photos do not show

- Open the photo URL in a browser from another computer.
- Confirm file names remove spaces from the displayed name.
- Confirm photos are `.png`, `.jpg`, or `.jpeg`.
- Use HTTP hosting before trying a Windows share.

### Battery warning appears too early

Anchor Mics only marks a mic as low battery at `10%` or below. If a receiver reports another warning status, update to the latest build and restart the Pi service.

## Building a Custom Pi Image

If you want a flashable image with the app already installed, use:

```bash
./make-pi-image.command
```

Docker Desktop must be open first. If you have the NDI SDK Linux archive in Downloads, the builder can embed the NDI runtime after you confirm the SDK license.

More details are in:

```text
deploy/pi-image/README.md
deploy/raspberry-pi/README.md
```

## Developer Notes

Run locally:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Useful pages:

```text
http://127.0.0.1:8010/dashboard
http://127.0.0.1:8010/display
http://127.0.0.1:8010/config
```

Run tests:

```bash
python3 -m unittest discover -s tests
```
