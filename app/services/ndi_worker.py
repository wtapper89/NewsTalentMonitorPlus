from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

from app.services.ndi import (
    NDI_CAPTURE_TIMEOUT_MS,
    NDI_PREVIEW_FPS,
    NDI_PREVIEW_MAX_WIDTH,
    NDI_STALE_RECONNECT_SECONDS,
    NDIReceiver,
    NDIlib,
)


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)


def write_bytes(path: Path, payload: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: ndi_worker.py SOURCE_NAME OUTPUT_DIR", file=sys.stderr)
        return 2

    source_name = sys.argv[1]
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_path = output_dir / "current.jpg"
    status_path = output_dir / "status.json"
    stop_path = output_dir / "stop"

    ndi: NDIlib | None = None
    receiver: NDIReceiver | None = None
    last_capture_attempt = 0.0
    fps_window_started_at = time.monotonic()
    fps_window_frames = 0
    actual_fps = 0.0
    try:
        write_json(status_path, {"connection_status": "starting", "source_name": source_name})
        ndi = NDIlib()
        receiver = NDIReceiver(ndi, source_name)
        receiver.connect()
        last_video_at = time.monotonic()
        write_json(
            status_path,
            {
                "connection_status": "connected",
                "source_name": source_name,
                "last_error": "",
                "has_frame": False,
                "frame_width": 0,
                "frame_height": 0,
                "captured_at": None,
                "preview_max_width": NDI_PREVIEW_MAX_WIDTH,
                "preview_fps": NDI_PREVIEW_FPS,
                "actual_fps": actual_fps,
            },
        )

        while not stop_path.exists():
            elapsed = time.monotonic() - last_capture_attempt
            min_interval = 1.0 / NDI_PREVIEW_FPS
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
                continue
            last_capture_attempt = time.monotonic()

            frame, frame_error = receiver.capture_jpeg(timeout_ms=NDI_CAPTURE_TIMEOUT_MS)
            if frame is None:
                if time.monotonic() - last_video_at >= NDI_STALE_RECONNECT_SECONDS:
                    write_json(
                        status_path,
                        {
                            "connection_status": "error",
                            "source_name": source_name,
                            "last_error": f"No NDI video frames for {NDI_STALE_RECONNECT_SECONDS:.1f}s",
                            "has_frame": frame_path.exists(),
                            "preview_max_width": NDI_PREVIEW_MAX_WIDTH,
                            "preview_fps": NDI_PREVIEW_FPS,
                            "actual_fps": actual_fps,
                        },
                    )
                    return 1
                if frame_error:
                    write_json(
                        status_path,
                        {
                            "connection_status": "connected",
                            "source_name": source_name,
                            "last_error": frame_error,
                            "has_frame": frame_path.exists(),
                            "preview_max_width": NDI_PREVIEW_MAX_WIDTH,
                            "preview_fps": NDI_PREVIEW_FPS,
                            "actual_fps": actual_fps,
                        },
                    )
                continue

            last_video_at = time.monotonic()
            fps_window_frames += 1
            fps_elapsed = last_video_at - fps_window_started_at
            if fps_elapsed >= 2.0:
                actual_fps = round(fps_window_frames / fps_elapsed, 1)
                fps_window_started_at = last_video_at
                fps_window_frames = 0
            write_bytes(frame_path, frame.jpeg)
            write_json(
                status_path,
                {
                    "connection_status": "connected",
                    "source_name": source_name,
                    "last_error": "",
                    "has_frame": True,
                    "frame_width": frame.width,
                    "frame_height": frame.height,
                    "captured_at": frame.captured_at,
                    "preview_max_width": NDI_PREVIEW_MAX_WIDTH,
                    "preview_fps": NDI_PREVIEW_FPS,
                    "actual_fps": actual_fps,
                },
            )
    except Exception as exc:
        write_json(
            status_path,
            {
                "connection_status": "error",
                "source_name": source_name,
                "last_error": str(exc),
                "has_frame": frame_path.exists(),
                "preview_max_width": NDI_PREVIEW_MAX_WIDTH,
                "preview_fps": NDI_PREVIEW_FPS,
                "actual_fps": actual_fps,
            },
        )
        return 1
    finally:
        if receiver:
            receiver.close()
        if ndi:
            ndi.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
