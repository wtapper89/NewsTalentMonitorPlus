from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger("anchor_mics.ndi")


NDI_RECV_FRAME_TYPE_NONE = 0
NDI_RECV_FRAME_TYPE_VIDEO = 1
NDI_RECV_FRAME_TYPE_AUDIO = 2
NDI_RECV_FRAME_TYPE_METADATA = 3
NDI_RECV_COLOR_FORMAT_BGRX_BGRA = 0
NDI_RECV_BANDWIDTH_LOWEST = 0
NDI_RECV_BANDWIDTH_HIGHEST = 100
NDI_PREVIEW_MAX_WIDTH = 960
NDI_PREVIEW_FPS = 30.0
NDI_PREVIEW_JPEG_QUALITY = 64
NDI_CAPTURE_TIMEOUT_MS = 1000
NDI_MAX_DRAIN_FRAMES = 120
NDI_STALE_RECONNECT_SECONDS = 10.0
NDI_MAX_RAW_FRAME_BYTES = 48 * 1024 * 1024


def fourcc(value: str) -> int:
    encoded = value.encode("ascii")
    return encoded[0] | (encoded[1] << 8) | (encoded[2] << 16) | (encoded[3] << 24)


FOURCC_BGRX = fourcc("BGRX")
FOURCC_BGRA = fourcc("BGRA")


class NDIlibSource(ctypes.Structure):
    _fields_ = [
        ("p_ndi_name", ctypes.c_char_p),
        ("p_url_address", ctypes.c_char_p),
    ]


class NDIlibRecvCreateV3(ctypes.Structure):
    _fields_ = [
        ("source_to_connect_to", NDIlibSource),
        ("color_format", ctypes.c_int),
        ("bandwidth", ctypes.c_int),
        ("allow_video_fields", ctypes.c_bool),
    ]


class NDIlibFindCreateV2(ctypes.Structure):
    _fields_ = [
        ("show_local_sources", ctypes.c_bool),
        ("p_groups", ctypes.c_char_p),
        ("p_extra_ips", ctypes.c_char_p),
    ]


class NDIlibVideoFrameV2(ctypes.Structure):
    _fields_ = [
        ("xres", ctypes.c_int),
        ("yres", ctypes.c_int),
        ("FourCC", ctypes.c_int),
        ("frame_rate_N", ctypes.c_int),
        ("frame_rate_D", ctypes.c_int),
        ("picture_aspect_ratio", ctypes.c_float),
        ("frame_format_type", ctypes.c_int),
        ("timecode", ctypes.c_longlong),
        ("p_data", ctypes.POINTER(ctypes.c_ubyte)),
        ("line_stride_in_bytes", ctypes.c_int),
        ("p_metadata", ctypes.c_char_p),
        ("timestamp", ctypes.c_longlong),
    ]


class NDIlibAudioFrameV3(ctypes.Structure):
    _fields_ = [
        ("sample_rate", ctypes.c_int),
        ("no_channels", ctypes.c_int),
        ("no_samples", ctypes.c_int),
        ("timecode", ctypes.c_longlong),
        ("p_data", ctypes.c_void_p),
        ("channel_stride_in_bytes", ctypes.c_int),
        ("p_metadata", ctypes.c_char_p),
        ("timestamp", ctypes.c_longlong),
    ]


class NDIlibMetadataFrame(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_int),
        ("timecode", ctypes.c_longlong),
        ("p_data", ctypes.c_char_p),
    ]


@dataclass
class NDIFrame:
    jpeg: bytes
    source_name: str
    width: int
    height: int
    captured_at: float


class NDIUnavailableError(RuntimeError):
    pass


class NDIlib:
    def __init__(self) -> None:
        self.lib = self._load_library()
        self._configure_signatures()
        if not self.lib.NDIlib_initialize():
            raise NDIUnavailableError("NDI runtime failed to initialize")

    def _load_library(self):
        candidates: list[str] = []
        env_path = os.getenv("ANCHOR_MICS_NDI_LIBRARY", "").strip()
        if env_path:
            candidates.append(env_path)

        found = ctypes.util.find_library("ndi")
        if found:
            candidates.append(found)

        system = platform.system().lower()
        if system == "windows":
            candidates.extend(
                [
                    r"C:\Program Files\NDI\NDI 6 Runtime\v6\Processing.NDI.Lib.x64.dll",
                    r"C:\Program Files\NDI\NDI 5 Runtime\v5\Processing.NDI.Lib.x64.dll",
                    r"C:\Program Files\NDI\NDI 5 Tools\Runtime\Processing.NDI.Lib.x64.dll",
                ]
            )
        elif system == "darwin":
            candidates.extend(
                [
                    "/usr/local/lib/libndi.dylib",
                    "/Library/NDI SDK for Apple/lib/macOS/libndi.dylib",
                ]
            )
        else:
            candidates.extend(
                [
                    "/usr/local/lib/libndi.so",
                    "/usr/local/lib/libndi.so.6",
                    "/usr/lib/libndi.so",
                    "/usr/lib/aarch64-linux-gnu/libndi.so",
                    "/usr/lib/arm-linux-gnueabihf/libndi.so",
                ]
            )

        errors: list[str] = []
        for candidate in candidates:
            try:
                return ctypes.CDLL(candidate)
            except OSError as exc:
                errors.append(f"{candidate}: {exc}")

        raise NDIUnavailableError("NDI runtime library was not found. Set ANCHOR_MICS_NDI_LIBRARY or install the NDI SDK runtime.")

    def _configure_signatures(self) -> None:
        lib = self.lib
        lib.NDIlib_initialize.restype = ctypes.c_bool
        lib.NDIlib_destroy.restype = None

        lib.NDIlib_find_create_v2.argtypes = [ctypes.POINTER(NDIlibFindCreateV2)]
        lib.NDIlib_find_create_v2.restype = ctypes.c_void_p
        lib.NDIlib_find_destroy.argtypes = [ctypes.c_void_p]
        lib.NDIlib_find_destroy.restype = None
        lib.NDIlib_find_wait_for_sources.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        lib.NDIlib_find_wait_for_sources.restype = ctypes.c_bool
        lib.NDIlib_find_get_current_sources.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        lib.NDIlib_find_get_current_sources.restype = ctypes.POINTER(NDIlibSource)

        lib.NDIlib_recv_create_v3.argtypes = [ctypes.POINTER(NDIlibRecvCreateV3)]
        lib.NDIlib_recv_create_v3.restype = ctypes.c_void_p
        lib.NDIlib_recv_destroy.argtypes = [ctypes.c_void_p]
        lib.NDIlib_recv_destroy.restype = None
        lib.NDIlib_recv_connect.argtypes = [ctypes.c_void_p, ctypes.POINTER(NDIlibSource)]
        lib.NDIlib_recv_connect.restype = None
        lib.NDIlib_recv_capture_v3.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(NDIlibVideoFrameV2),
            ctypes.POINTER(NDIlibAudioFrameV3),
            ctypes.POINTER(NDIlibMetadataFrame),
            ctypes.c_uint32,
        ]
        lib.NDIlib_recv_capture_v3.restype = ctypes.c_int
        lib.NDIlib_recv_free_video_v2.argtypes = [ctypes.c_void_p, ctypes.POINTER(NDIlibVideoFrameV2)]
        lib.NDIlib_recv_free_video_v2.restype = None
        lib.NDIlib_recv_free_audio_v3.argtypes = [ctypes.c_void_p, ctypes.POINTER(NDIlibAudioFrameV3)]
        lib.NDIlib_recv_free_audio_v3.restype = None
        lib.NDIlib_recv_free_metadata.argtypes = [ctypes.c_void_p, ctypes.POINTER(NDIlibMetadataFrame)]
        lib.NDIlib_recv_free_metadata.restype = None

    def destroy(self) -> None:
        self.lib.NDIlib_destroy()


class NDIReceiver:
    def __init__(
        self,
        ndi: NDIlib,
        source_name: str,
        jpeg_quality: int = NDI_PREVIEW_JPEG_QUALITY,
        max_width: int = NDI_PREVIEW_MAX_WIDTH,
    ) -> None:
        self.ndi = ndi
        self.source_name = source_name
        self.jpeg_quality = max(1, min(95, int(jpeg_quality)))
        self.max_width = max(240, int(max_width))
        self.recv_instance: ctypes.c_void_p | None = None

    def connect(self, timeout_ms: int = 5000) -> None:
        source = self._find_source(timeout_ms)
        recv_create = NDIlibRecvCreateV3(
            source_to_connect_to=source,
            color_format=NDI_RECV_COLOR_FORMAT_BGRX_BGRA,
            bandwidth=NDI_RECV_BANDWIDTH_HIGHEST,
            allow_video_fields=True,
        )
        self.recv_instance = self.ndi.lib.NDIlib_recv_create_v3(ctypes.byref(recv_create))
        if not self.recv_instance:
            raise NDIUnavailableError(f"Failed to create NDI receiver for {self.source_name}")
        self.ndi.lib.NDIlib_recv_connect(self.recv_instance, ctypes.byref(source))

    def close(self) -> None:
        if self.recv_instance:
            self.ndi.lib.NDIlib_recv_destroy(self.recv_instance)
            self.recv_instance = None

    def capture_jpeg(self, timeout_ms: int = 1000) -> tuple[NDIFrame | None, str]:
        if not self.recv_instance:
            raise NDIUnavailableError("NDI receiver is not connected")

        latest_video: NDIlibVideoFrameV2 | None = None
        try:
            for index in range(NDI_MAX_DRAIN_FRAMES):
                frame_type, video, audio, metadata = self._capture_raw(timeout_ms if index == 0 else 0)
                if frame_type == NDI_RECV_FRAME_TYPE_VIDEO:
                    if latest_video is not None:
                        self.ndi.lib.NDIlib_recv_free_video_v2(self.recv_instance, ctypes.byref(latest_video))
                    latest_video = video
                    continue
                self._free_non_video_frame(frame_type, audio, metadata)
                if latest_video is not None or frame_type == NDI_RECV_FRAME_TYPE_NONE:
                    break

            if latest_video is None:
                return None, ""
            return self._video_to_jpeg(latest_video), ""
        except NDIUnavailableError as exc:
            return None, str(exc)
        finally:
            if latest_video is not None:
                self.ndi.lib.NDIlib_recv_free_video_v2(self.recv_instance, ctypes.byref(latest_video))

    def _capture_raw(
        self,
        timeout_ms: int,
    ) -> tuple[int, NDIlibVideoFrameV2, NDIlibAudioFrameV3, NDIlibMetadataFrame]:
        video = NDIlibVideoFrameV2()
        audio = NDIlibAudioFrameV3()
        metadata = NDIlibMetadataFrame()
        frame_type = self.ndi.lib.NDIlib_recv_capture_v3(
            self.recv_instance,
            ctypes.byref(video),
            ctypes.byref(audio),
            ctypes.byref(metadata),
            timeout_ms,
        )
        return frame_type, video, audio, metadata

    def _free_non_video_frame(
        self,
        frame_type: int,
        audio: NDIlibAudioFrameV3,
        metadata: NDIlibMetadataFrame,
    ) -> None:
        if not self.recv_instance:
            return
        if frame_type == NDI_RECV_FRAME_TYPE_AUDIO:
            self.ndi.lib.NDIlib_recv_free_audio_v3(self.recv_instance, ctypes.byref(audio))
        elif frame_type == NDI_RECV_FRAME_TYPE_METADATA:
            self.ndi.lib.NDIlib_recv_free_metadata(self.recv_instance, ctypes.byref(metadata))

    def _find_source(self, timeout_ms: int) -> NDIlibSource:
        sources = discover_ndi_sources(self.ndi, timeout_ms=timeout_ms)
        exact_match = next((source for source in sources if source["name"] == self.source_name), None)
        loose_match = next((source for source in sources if self.source_name.lower() in source["name"].lower()), None)
        selected = exact_match or loose_match
        if not selected:
            available = ", ".join(source["name"] for source in sources) or "none found"
            raise NDIUnavailableError(f"NDI source not found: {self.source_name}. Available sources: {available}")
        return NDIlibSource(
            p_ndi_name=selected["name"].encode("utf-8"),
            p_url_address=selected["url"].encode("utf-8") if selected["url"] else None,
        )

    def _video_to_jpeg(self, video: NDIlibVideoFrameV2) -> NDIFrame:
        if video.FourCC not in {FOURCC_BGRX, FOURCC_BGRA}:
            format_name = "".join(chr((video.FourCC >> shift) & 0xFF) for shift in (0, 8, 16, 24))
            raise NDIUnavailableError(f"Unsupported NDI pixel format {format_name} FourCC={video.FourCC}")
        if video.xres <= 0 or video.yres <= 0 or not video.p_data:
            raise NDIUnavailableError("NDI returned an empty video frame")

        from io import BytesIO

        from PIL import Image

        raw_size = video.line_stride_in_bytes * video.yres
        if raw_size > NDI_MAX_RAW_FRAME_BYTES:
            raise NDIUnavailableError(
                f"NDI frame is too large for Pi preview: {video.xres}x{video.yres}, {raw_size} bytes"
            )
        raw = ctypes.string_at(video.p_data, raw_size)
        image = Image.frombytes(
            "RGB",
            (video.xres, video.yres),
            raw,
            "raw",
            "BGRX",
            video.line_stride_in_bytes,
            1,
        )
        if image.width > self.max_width:
            target_height = max(1, round(image.height * (self.max_width / image.width)))
            image = image.resize((self.max_width, target_height), Image.Resampling.BILINEAR)
        output = BytesIO()
        image.save(output, format="JPEG", quality=self.jpeg_quality, optimize=False)
        return NDIFrame(
            jpeg=output.getvalue(),
            source_name=self.source_name,
            width=video.xres,
            height=video.yres,
            captured_at=time.time(),
        )


class NDIBridge:
    def __init__(self) -> None:
        self._base_dir = Path(os.getenv("ANCHOR_MICS_NDI_WORK_DIR", "/tmp/anchor-mics-ndi"))
        self._source_name = ""
        self._last_error = ""
        self._connection_status = "idle"
        self._process: subprocess.Popen | None = None
        self._worker_dir: Path | None = None
        self._last_frame_mtime = 0.0
        self._last_frame: NDIFrame | None = None

    def configure(self, display: dict[str, Any]) -> None:
        if str(display.get("preview_mode") or "").lower() != "ndi":
            self.stop()
            return

        source_name = str(display.get("preview_source_name") or "").strip()
        if not source_name:
            self.stop()
            self._connection_status = "error"
            self._last_error = "No NDI source name configured"
            return

        if self._process and self._process.poll() is None and self._source_name == source_name:
            return

        self.stop()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        source_hash = hashlib.sha1(source_name.encode("utf-8")).hexdigest()[:12]
        worker_dir = self._base_dir / source_hash
        worker_dir.mkdir(parents=True, exist_ok=True)
        for name in ("stop", "current.jpg", "status.json"):
            try:
                (worker_dir / name).unlink()
            except FileNotFoundError:
                pass

        self._source_name = source_name
        self._connection_status = "starting"
        self._last_error = ""
        self._worker_dir = worker_dir
        self._last_frame = None
        self._last_frame_mtime = 0.0
        if getattr(sys, "frozen", False):
            worker_command = [sys.executable, "--ndi-worker", source_name, str(worker_dir)]
            worker_cwd = str(Path(sys.executable).resolve().parent)
        else:
            worker_command = [sys.executable, "-m", "app.services.ndi_worker", source_name, str(worker_dir)]
            worker_cwd = str(Path(__file__).resolve().parents[2])

        self._process = subprocess.Popen(
            worker_command,
            cwd=worker_cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    def stop(self) -> None:
        process = self._process
        worker_dir = self._worker_dir
        if process and process.poll() is None:
            if worker_dir:
                try:
                    (worker_dir / "stop").write_text("stop", encoding="utf-8")
                except OSError:
                    pass
            try:
                process.terminate()
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        self._process = None
        if self._connection_status != "error":
            self._connection_status = "idle"

    def latest_frame(self) -> NDIFrame | None:
        status = self._read_status()
        process_running = self._process is not None and self._process.poll() is None
        frame_path = self._frame_path()
        if not frame_path:
            return self._last_frame
        try:
            stat = frame_path.stat()
        except FileNotFoundError:
            return self._last_frame
        if stat.st_mtime == self._last_frame_mtime and self._last_frame is not None:
            return self._last_frame
        try:
            jpeg = frame_path.read_bytes()
        except OSError:
            return self._last_frame

        frame = NDIFrame(
            jpeg=jpeg,
            source_name=self._source_name,
            width=int(status.get("frame_width") or 0),
            height=int(status.get("frame_height") or 0),
            captured_at=float(status.get("captured_at") or stat.st_mtime),
        )
        if not process_running and time.time() - frame.captured_at > NDI_STALE_RECONNECT_SECONDS:
            self._last_frame = None
            self._last_frame_mtime = 0.0
            return None
        self._last_frame = frame
        self._last_frame_mtime = stat.st_mtime
        return frame

    def status(self) -> dict[str, Any]:
        status = self._read_status()
        frame = self.latest_frame()
        process_running = self._process is not None and self._process.poll() is None
        exit_code = None if process_running or self._process is None else self._process.returncode
        connection_status = status.get("connection_status") or self._connection_status
        last_error = status.get("last_error") or self._last_error
        if exit_code is not None and connection_status not in {"idle", "error"}:
            connection_status = "error"
            last_error = f"NDI worker exited with status {exit_code}"
        return {
            "source_name": status.get("source_name") or self._source_name,
            "connection_status": connection_status,
            "last_error": last_error,
            "has_frame": frame is not None,
            "frame_width": frame.width if frame else int(status.get("frame_width") or 0),
            "frame_height": frame.height if frame else int(status.get("frame_height") or 0),
            "seconds_since_frame": round(time.time() - frame.captured_at, 3) if frame else None,
            "preview_max_width": NDI_PREVIEW_MAX_WIDTH,
            "preview_fps": NDI_PREVIEW_FPS,
            "actual_fps": status.get("actual_fps"),
            "thread_running": process_running,
            "worker_running": process_running,
            "worker_pid": self._process.pid if process_running and self._process else None,
            "worker_exit_code": exit_code,
        }

    def discover_sources(self, timeout_ms: int = 2000) -> list[dict[str, str]]:
        ndi = NDIlib()
        try:
            return discover_ndi_sources(ndi, timeout_ms=timeout_ms)
        finally:
            ndi.destroy()

    def _frame_path(self) -> Path | None:
        if not self._worker_dir:
            return None
        return self._worker_dir / "current.jpg"

    def _read_status(self) -> dict[str, Any]:
        if not self._worker_dir:
            return {}
        try:
            return json.loads((self._worker_dir / "status.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}


def discover_ndi_sources(ndi: NDIlib, timeout_ms: int = 2000) -> list[dict[str, str]]:
    find_create = NDIlibFindCreateV2(
        show_local_sources=True,
        p_groups=None,
        p_extra_ips=None,
    )
    find_instance = ndi.lib.NDIlib_find_create_v2(ctypes.byref(find_create))
    if not find_instance:
        raise NDIUnavailableError("Failed to create NDI source finder")

    try:
        ndi.lib.NDIlib_find_wait_for_sources(find_instance, timeout_ms)
        source_count = ctypes.c_uint32(0)
        sources_ptr = ndi.lib.NDIlib_find_get_current_sources(find_instance, ctypes.byref(source_count))
        result: list[dict[str, str]] = []
        for index in range(source_count.value):
            source = sources_ptr[index]
            name = source.p_ndi_name.decode("utf-8", errors="replace") if source.p_ndi_name else ""
            url = source.p_url_address.decode("utf-8", errors="replace") if source.p_url_address else ""
            if name:
                result.append({"name": name, "url": url})
        return result
    finally:
        ndi.lib.NDIlib_find_destroy(find_instance)
