# Anchor Mics

Anchor Mics is a local control-room dashboard and fullscreen display for Shure microphone assignments and telemetry, with a Companion module alongside it so live mic data can appear on Companion buttons and feedbacks.

## What is in this repo

- A Python `FastAPI` app that serves a control-room dashboard and JSON APIs.
- A Raspberry Pi friendly fullscreen display page at `/display`.
- A mock Shure adapter so the interface works immediately without hardware.
- A Micboard adapter that reads Micboard’s `data.json` feed and maps it onto your board layout.
- A configurable `SystemAPI` adapter that polls URLs you map from your Shure deployment.
- A Companion module folder that reads the dashboard state and exposes per-mic variables and status feedbacks.

## Run this on your Mac

```bash
cd /path/to/AnchorMics
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Then open:

- Dashboard: [http://127.0.0.1:8010](http://127.0.0.1:8010)
- Fullscreen display: [http://127.0.0.1:8010/display](http://127.0.0.1:8010/display)
- Config page: [http://127.0.0.1:8010/config](http://127.0.0.1:8010/config)

If you stop and restart later:

```bash
cd /path/to/AnchorMics
. .venv/bin/activate
python run.py
```

## Configuration

Environment variables:

- `ANCHOR_MICS_SOURCE`: `mock`, `micboard`, `qlxd`, or `system_api`
  - default: `qlxd`
- `ANCHOR_MICS_HOST`: bind host for the dashboard app
- `ANCHOR_MICS_PORT`: bind port for the dashboard app
- `ANCHOR_MICS_RELOAD`: set to `1` if you want uvicorn auto-reload while developing
- `ANCHOR_MICS_REFRESH_SECONDS`: backend polling interval
- `ANCHOR_MICS_DATA_FILE`: JSON file for assignment storage
- `ANCHOR_MICS_MAPPING_FILE`: JSON mapping file for live Shure endpoints

The config GUI now also stores:

- Display settings for the Pi fullscreen layout
- Companion variable lookup for the show title
- Preview source settings for the large center window, including native NDI mode

### Recommended QLX-D hookup: integrated receiver polling

Anchor Mics now includes the QLX-D receiver polling internally, so you only need to run this app.

1. Start the app.
2. Open [http://127.0.0.1:8010/config](http://127.0.0.1:8010/config).
3. Enter the IP or hostname for each QLX-D receiver row.
4. Leave `Receiver channel` at `1` for a single-channel QLX-D receiver unless you know a different channel index is required.
5. Save the config page.
6. Restart the app in QLX-D live mode:

```bash
export ANCHOR_MICS_SOURCE=qlxd
. .venv/bin/activate
python run.py
```

The integrated QLX-D adapter reads:

- channel name
- battery level
- RF level
- audio level
- receiver / transmitter error states

Renaming in `qlxd` mode is sent directly to the receiver channel.

Legacy note

If you previously started the app with `ANCHOR_MICS_SOURCE=micboard`, that value is now treated as an alias for integrated `qlxd` mode so existing launch commands still work.

## Companion integration

The Companion module lives in [`companion-module-anchor-mics`](companion-module-anchor-mics).

It polls `/api/companion/state` from the Python app and exposes:

- Summary variables like `summary_total` and `summary_low_battery`
- Per-mic variables like `mic_1_name`, `mic_1_assignee`, `mic_1_battery`, and `mic_1_errors`
- Feedbacks for low battery and active mic errors

The module follows Bitfocus Companion’s official module structure: `src/main.js`, `companion/manifest.json`, and `companion/HELP.md`.

The FastAPI app can also read a module variable directly from Companion for the fullscreen display title. Configure this on `/config` using:

- `Companion base URL`
- `Connection label`
- `Variable name`

The fetch path uses Companion’s HTTP remote control API for module variables.

## Fullscreen display

The new fullscreen page is at [http://127.0.0.1:8010/display](http://127.0.0.1:8010/display).

It is designed for a 1080p HDMI output on a Raspberry Pi and includes:

- large clock
- show title from manual config or Companion
- large preview area
- bottom mic status tiles for all configured Shure mics

Important preview note:

- Use `Preview mode = ndi` and set `NDI source name` to receive a native NDI source through the local NDI bridge.
- The app exposes the bridge as an MJPEG feed at `/api/ndi/preview.mjpg` for Chromium.
- The repo does not include the NDI SDK runtime because it is proprietary. Install the NDI runtime on the Pi or include it in the custom image build with `NDI_SDK_TARBALL`.
- The default font stack starts with `Gotham`, but you must have a licensed Gotham font installed on the Pi for Chromium to actually render it. Otherwise it will fall back to the rest of the stack.

NDI diagnostics:

- `/api/ndi/status` shows bridge state, last error, and frame dimensions.
- `/api/ndi/sources` scans for available NDI sources.

## Raspberry Pi boot setup

Systemd and kiosk launcher templates are in [`deploy/raspberry-pi`](deploy/raspberry-pi/README.md).

They provide:

- `anchor-mics.service` for the Python app
- `anchor-mics-kiosk.service` for Chromium kiosk on boot
- `start-kiosk.sh` for opening `/display` on the Pi HDMI output

## Custom Pi image

A Docker/pi-gen image build is in [`deploy/pi-image`](deploy/pi-image/README.md).

Open Docker Desktop first and wait until the engine is running.

Build the image with:

```bash
./make-pi-image.command
```

That wrapper auto-detects the NDI SDK archive at `~/Downloads/Install_NDI_SDK_v6_Linux.tar.gz`, caches it under `.pi-image-build/ndi/`, asks for license confirmation, and embeds the runtime into the image.

If the SDK archive is somewhere else:

```bash
./deploy/pi-image/prepare-ndi-sdk.sh /path/to/Install_NDI_SDK_v6_Linux.tar.gz
./make-pi-image.command
```

The resulting `.img.xz` in `.pi-image-build/pi-gen/deploy/` can be flashed with Raspberry Pi Imager using `Use custom`.

## Testing

Run the unit tests with:

```bash
python3 -m unittest discover -s tests
```

## Notes

- This repo ships in `mock` mode by default because the workspace does not have direct access to your Shure hardware.
- The config page writes to [`config/system_api_mapping.example.json`](config/system_api_mapping.example.json) unless you point `ANCHOR_MICS_MAPPING_FILE` somewhere else.
- The Companion module is included but not packaged here because this machine does not currently have Node/Yarn installed.
- Official references used while shaping this MVP:
  - Shure System API Server documentation: [shure.stoplight.io/docs/shure-system-api-server-specification](https://shure.stoplight.io/docs/shure-system-api-server-specification/c30bd45807650-shure-system-api-server)
  - Micboard QLX-D firmware note: [github.com/karlcswanson/micboard/blob/master/docs/qlxd.md](https://github.com/karlcswanson/micboard/blob/master/docs/qlxd.md)
  - Companion module development guide: [companion.free/for-developers/module-development/home](https://companion.free/for-developers/module-development/home)
  - Companion variables guide: [companion.free/for-developers/module-development/connection-basics/variables](https://companion.free/for-developers/module-development/connection-basics/variables)
