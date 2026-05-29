# News Talent Monitor+

Wouldn't it be better if the monitor on the front of your camera showed more than just return video?

News Talent Monitor+ turns a Raspberry Pi into a front-of-camera talent monitor for newsrooms, control rooms, and studio production teams. It shows the return/program video, the current PGM source, the upcoming PVW source, talent or anchor mic assignments, headshots, and Shure wireless mic status in one screen.

The goal is simple: give talent and operators more context using hardware you probably already have.

## Typical Setup

- Raspberry Pi connected to a camera-front monitor, set monitor, or control-room display
- vMix providing an NDI return/program feed
- Bitfocus Companion providing vMix variables
- Shure QLX-D receivers on the same network
- Optional talent headshots served from a simple HTTP folder

## What The Display Shows

- Large return video from an NDI source
- Green `Now` box for the current PGM source
- Yellow `Next` box for the current PVW source
- Mic assignment tiles for anchors, hosts, reporters, or guests
- Optional headshot beside each assigned person
- Battery, RF, audio level, and online/offline state for each mic
- Hamburger button for quick access to setup

## Daily Use

1. Power on the Raspberry Pi.
2. Wait for the fullscreen monitor page to open.
3. Confirm the large video preview is showing the expected vMix NDI output.
4. Confirm `Now` and `Next` match your vMix PGM/PVW sources.
5. Check the mic boxes:
   - Green means the mic is online and healthy.
   - Yellow means something needs attention.
   - Red means the mic or transmitter is unavailable.
6. Tap the hamburger button in the upper-right corner to open setup.

## First Setup

For a step-by-step Windows PC setup, including Docker Desktop, the NDI SDK location, building the Pi image, flashing the image, and running the Windows photo server, start here:

```text
docs/WINDOWS_SETUP.md
```

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

Use this tab for the large return video.

- `Preview mode`: choose `ndi` for vMix or another NDI source.
- `NDI source name`: click `Scan`, then choose the source you want displayed.
- `Preview URL`: leave blank when using NDI.
- `Font family`: leave the default unless you installed a specific font on the Pi.

Save after choosing the NDI source.

### Companion Tab

Use this tab when Companion should provide rundown/source names and mic assignments.

- `Enable Companion polling`: set to `true`.
- `Companion base URL`: enter the Companion computer URL, such as `http://10.0.0.50:8000`.
- `Default connection label`: enter the Companion connection label used for variables, such as `vmix` or `custom`.
- `PGM / Now source variable`: vMix or Companion variable shown in the green `Now` box.
- `PVW / Next source variable`: vMix or Companion variable shown in the yellow `Next` box.

Variable examples:

```text
vmix:mix_1_program_full_title
vmix:mix_1_preview_full_title
$(vmix:mix_1_program_full_title)
```

For talent names, each mic row has a `Companion assignment variable`. If that variable returns `John Smith`, the display uses `John Smith` instead of `Mic 1`.

### Photos Tab

Use this tab for square headshots beside talent names.

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

If the mic assignment is `John Smith`, News Talent Monitor+ looks for files like `JohnSmith.png`, `JohnSmith.jpg`, and `JohnSmith.jpeg`.

### Receivers Tab

For normal Shure QLX-D polling:

- `Default scheme`: `tcp`
- `Default port`: `2202`
- `Auth type`: `none`

The token fields are only for a custom Shure System API setup. Most users can leave them blank.

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
3. Confirm `Now` and `Next` match vMix/Companion.
4. Turn one mic transmitter on and off to confirm the tile changes.
5. Change a Companion mic assignment and confirm the display updates.

## Troubleshooting

### The preview is red or blank

- Open Config -> Display.
- Click `Scan` and choose the NDI source again.
- Make sure the Pi and vMix computer are on the same production network.
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

News Talent Monitor+ only marks a mic as low battery at `10%` or below. If a receiver reports another warning status, update to the latest build and restart the Pi service.

## Building a Custom Pi Image

If you want a flashable image with the app already installed, use:

```bash
./make-pi-image.command
```

Docker Desktop must be open first. If you have the NDI SDK Linux archive in Downloads, the builder can embed the NDI runtime after you confirm the SDK license.

More details are in:

```text
docs/WINDOWS_SETUP.md
deploy/pi-image/README.md
deploy/raspberry-pi/README.md
```

## Legal And Licensing Notes

News Talent Monitor+ does not include the NDI SDK or NDI runtime in this source repository.

Native NDI preview support dynamically loads `libndi.so` from an NDI SDK/runtime installation. If you use the custom Pi image builder to embed the NDI runtime, you must provide the NDI SDK archive yourself and explicitly confirm that you accept the NDI SDK license. The NDI documentation says SDK use is governed by the SDK License Agreement, and distribution of NDI runtime files must comply with that agreement and its third-party rights requirements.

Useful NDI references:

- NDI SDK licensing: https://docs.ndi.video/all/developing-with-ndi/sdk/licensing
- NDI software distribution: https://docs.ndi.video/all/developing-with-ndi/sdk/software-distribution
- NDI SDK download: https://ndi.video/for-developers/ndi-sdk/download/

Product names and trademarks belong to their respective owners. This project is not affiliated with, endorsed by, or sponsored by NDI, vMix, Bitfocus Companion, Shure, Raspberry Pi, or any related company.

See `LICENSE` and `THIRD_PARTY_NOTICES.md` for project license and attribution details.

## Credits

- Micboard by Karl Swanson: https://github.com/karlcswanson/micboard
  - Micboard influenced the QLX-D monitoring direction and is credited for its public documentation around monitoring network-enabled Shure devices.
- Raspberry Pi pi-gen: https://github.com/RPi-Distro/pi-gen
  - Used by the custom image build flow.
- Bitfocus Companion: https://bitfocus.io/companion
  - Used as the variable/control integration target.
- FastAPI: https://fastapi.tiangolo.com/
  - Used for the local web app and API.
- NDI SDK documentation: https://docs.ndi.video/
  - Used for NDI runtime integration guidance.

## Developer Notes

The repository and service names still use `anchor-mics` internally in a few places for compatibility with existing installs and systemd services. The user-facing product name is News Talent Monitor+.

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
