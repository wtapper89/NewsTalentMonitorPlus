# Raspberry Pi Kiosk

This folder contains a simple boot-to-HDMI setup for running the fullscreen Anchor Mics display on a Raspberry Pi.

## What it does

- Starts the FastAPI app at boot with `systemd`
- Opens Chromium in kiosk mode to `http://127.0.0.1:8010/display`
- Keeps both services restarted if they exit

## Assumptions

- Raspberry Pi OS with desktop and Chromium installed
- Project copied to `/opt/anchor-mics`
- Python virtual environment created at `/opt/anchor-mics/.venv`
- `pi` is the desktop user

## Install steps

1. Copy the project to the Pi, for example to `/opt/anchor-mics`
2. Create the venv and install dependencies
3. Copy the service files:

```bash
sudo cp /opt/anchor-mics/deploy/raspberry-pi/anchor-mics.service /etc/systemd/system/
sudo cp /opt/anchor-mics/deploy/raspberry-pi/anchor-mics-kiosk.service /etc/systemd/system/
sudo chmod +x /opt/anchor-mics/deploy/raspberry-pi/start-kiosk.sh
```

4. Reload and enable them:

```bash
sudo systemctl daemon-reload
sudo systemctl enable anchor-mics.service
sudo systemctl enable anchor-mics-kiosk.service
sudo systemctl start anchor-mics.service
sudo systemctl start anchor-mics-kiosk.service
```

## Notes

- The kiosk page is `/display`
- The config GUI remains at `http://<pi-ip>:8010/config`
- For native NDI, install the NDI runtime on the Pi, set `Preview mode` to `ndi`, and set `NDI source name` on the config page.
- The display page reads the NDI bridge through `/api/ndi/preview.mjpg`.
- A custom flashable image build is available in `deploy/pi-image`.
