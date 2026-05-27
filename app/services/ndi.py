from __future__ import annotations

import ctypes
import ctypes.util
import logging
import os
import platform
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger("anchor_mics.ndi")


NDI_RECV_FRAME_TYPE_NONE = 0
NDI_RECV_FRAME_TYPE_VIDEO = 2
NDI_RECV_COLOR_FORMAT_BGRX_BGRA = 1
NDI_RECV_BANDWIDTH_HIGHEST = 100


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
        if system == "darwin":
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
    def __init__(self, ndi: NDIlib, source_name: str, jpeg_quality: int = 70) -> None:
        self.ndi = ndi
        self.source_name = source_name
        self.jpeg_quality = max(1, min(95, int(jpeg_quality)))
        self.recv_instance: ctypes.c_void_p | None = None

    def connect(self, timeout_ms: int = 5000) -> None:
        source = self._find_source(timeout_ms)
        recv_create = NDIlibRecvCreateV3(
            source_to_connect_to=source,
            color_format=NDI_RECV_COLOR_FORMAT_BGRX_BGRA,
            bandwidth=NDI_RECV_BANDWIDTH_HIGHEST,
            allow_video_fields=False,
        )
        self.recv_instance = self.ndi.lib.NDIlib_recv_create_v3(ctypes.byref(recv_create))
        if not self.recv_instance:
            raise NDIUnavailableError(f"Failed to create NDI receiver for {self.source_name}")
        self.ndi.lib.NDIlib_recv_connect(self.recv_instance, ctypes.byref(source))

    def close(self) -> None:
        if self.recv_instance:
            self.ndi.lib.NDIlib_recv_destroy(self.recv_instance)
            self.recv_instance = None

    def capture_jpeg(self, timeout_ms: int = 1000) -> NDIFrame | None:
        if not self.recv_instance:
            raise NDIUnavailableError("NDI receiver is not connected")

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

        try:
            if frame_type == NDI_RECV_FRAME_TYPE_VIDEO:
                return self._video_to_jpeg(video)
            return None
        finally:
            if frame_type == NDI_RECV_FRAME_TYPE_VIDEO:
                self.ndi.lib.NDIlib_recv_free_video_v2(self.recv_instance, ctypes.byref(video))
            elif frame_type == 3:
                self.ndi.lib.NDIlib_recv_free_audio_v3(self.recv_instance, ctypes.byref(audio))
            elif frame_type == 4:
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
            raise NDIUnavailableError(f"Unsupported NDI pixel format FourCC={video.FourCC}")
        if video.xres <= 0 or video.yres <= 0 or not video.p_data:
            raise NDIUnavailableError("NDI returned an empty video frame")

        from io import BytesIO

        from PIL import Image

        raw_size = video.line_stride_in_bytes * video.yres
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
        output = BytesIO()
        image.save(output, format="JPEG", quality=self.jpeg_quality, optimize=True)
        return NDIFrame(
            jpeg=output.getvalue(),
            source_name=self.source_name,
            width=video.xres,
            height=video.yres,
            captured_at=time.time(),
        )


class NDIBridge:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: NDIFrame | None = None
        self._source_name = ""
        self._last_error = ""
        self._connection_status = "idle"
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def configure(self, display: dict[str, Any]) -> None:
        if str(display.get("preview_mode") or "").lower() != "ndi":
            self.stop()
            return

        source_name = str(display.get("preview_source_name") or "").strip()
        if not source_name:
            self.stop()
            with self._lock:
                self._connection_status = "error"
                self._last_error = "No NDI source name configured"
            return

        with self._lock:
            current_source = self._source_name
            running = self._thread is not None and self._thread.is_alive()
        if running and current_source == source_name:
            return

        self.stop()
        self._stop_event.clear()
        with self._lock:
            self._source_name = source_name
            self._connection_status = "starting"
            self._last_error = ""
            self._frame = None
        self._thread = threading.Thread(target=self._run, args=(source_name,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        thread = self._thread
        if thread and thread.is_alive():
            self._stop_event.set()
            thread.join(timeout=2.0)
        self._thread = None
        self._stop_event.clear()
        with self._lock:
            if self._connection_status != "error":
                self._connection_status = "idle"

    def latest_frame(self) -> NDIFrame | None:
        with self._lock:
            return self._frame

    def status(self) -> dict[str, Any]:
        with self._lock:
            frame = self._frame
            return {
                "source_name": self._source_name,
                "connection_status": self._connection_status,
                "last_error": self._last_error,
                "has_frame": frame is not None,
                "frame_width": frame.width if frame else 0,
                "frame_height": frame.height if frame else 0,
                "seconds_since_frame": round(time.time() - frame.captured_at, 3) if frame else None,
            }

    def discover_sources(self, timeout_ms: int = 2000) -> list[dict[str, str]]:
        ndi = NDIlib()
        try:
            return discover_ndi_sources(ndi, timeout_ms=timeout_ms)
        finally:
            ndi.destroy()

    def _run(self, source_name: str) -> None:
        ndi: NDIlib | None = None
        receiver: NDIReceiver | None = None
        try:
            ndi = NDIlib()
            receiver = NDIReceiver(ndi, source_name)
            receiver.connect()
            with self._lock:
                self._connection_status = "connected"
                self._last_error = ""
            logger.info("connected ndi receiver source=%s", source_name)

            while not self._stop_event.is_set():
                frame = receiver.capture_jpeg(timeout_ms=1000)
                if frame is None:
                    continue
                with self._lock:
                    self._frame = frame
                    self._connection_status = "connected"
                    self._last_error = ""
        except Exception as exc:
            logger.warning("ndi receiver fault source=%s error=%s", source_name, exc)
            with self._lock:
                self._connection_status = "error"
                self._last_error = str(exc)
        finally:
            if receiver:
                receiver.close()
            if ndi:
                ndi.destroy()


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
