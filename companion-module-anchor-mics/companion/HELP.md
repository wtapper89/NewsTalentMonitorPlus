# News Talent Monitor+ Companion Module

This module connects Companion to the local News Talent Monitor+ backend.

## Configuration

- `Dashboard Host`: Hostname or IP address where the Python app is running.
- `Dashboard Port`: Port exposed by the Python app. The default in this repo is `8010`.
- `Use HTTPS`: Enable only if you reverse-proxy the app behind TLS.
- `Poll Interval`: How often Companion should refresh values from the dashboard API.

## Variables

Summary variables:

- `summary_total`
- `summary_assigned`
- `summary_offline`
- `summary_low_battery`
- `summary_with_errors`
- `summary_connection_status`
- `summary_updated_at`

Per-mic variables are exposed as `mic_1_name`, `mic_1_assignee`, `mic_1_battery`, `mic_1_signal`, `mic_1_audio`, `mic_1_status`, and `mic_1_errors`, with the index continuing for every mic returned by the backend.

## Feedbacks

- `Mic low battery`: Turns on when the selected mic index falls under the configured threshold.
- `Mic has error`: Turns on when the selected mic index reports any error or is offline.

## Usage

1. Run the Python dashboard app from this repo.
2. Place this module in your Companion module development folder.
3. Install dependencies with Yarn on a machine that has Node 22.
4. Add the module in Companion and point it at the dashboard host and port.
