# Smooth, low-delay NDI monitoring on Raspberry Pi

The full-resolution NDI stream can exceed a Pi's real-time decoding and JPEG
conversion budget. For motion-first monitoring, request the source's preview
stream and allow up to 60 frames per second. Actual resolution and frame rate
depend on the source; vMix on the tested installation supplies 640×360 at 59.94 fps.
This is softer than the full-resolution stream.

Create `/etc/systemd/system/anchor-mics.service.d/ndi-performance.conf`:

```ini
[Service]
Environment=ANCHOR_MICS_NDI_BANDWIDTH=lowest
Environment=ANCHOR_MICS_NDI_FPS=60
```

Then run `sudo systemctl daemon-reload` and
`sudo systemctl restart anchor-mics.service`.
The drop-in survives application updates. Use `highest` and `30` to restore the
default full-resolution receive mode and 30 fps output limit.

The worker paces before capturing, drains queued frames, and immediately publishes
the newest converted frame. The browser's MJPEG endpoint sends only the newest
available frame rather than maintaining an application frame queue.

NDI status includes `actual_fps`, `source_fps`, `capture_ms`, and `encode_ms`.
These measure local throughput and processing, not camera-to-screen latency.
Measure total delay by showing a running timecode at the source and comparing it
with the physical monitor in the same camera image.
