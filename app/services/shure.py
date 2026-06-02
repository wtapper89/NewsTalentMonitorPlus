from __future__ import annotations

import asyncio
import logging
import re
import socket
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.models import LOW_BATTERY_PERCENT, MicSnapshot
from app.store import MappingStore


logger = logging.getLogger("anchor_mics.qlxd")


def clamp(value: Any, minimum: int = 0, maximum: int = 100, fallback: int = 0) -> int:
    try:
        coerced = int(round(float(value)))
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, coerced))


def deep_get(payload: Any, dotted_path: str | None, default: Any = None) -> Any:
    if not dotted_path:
        return default

    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return default
            current = current[index]
            continue
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return default
    return current if current is not None else default


def render_template(payload: Any, values: dict[str, str]) -> Any:
    if isinstance(payload, str):
        return payload.format(**values)
    if isinstance(payload, list):
        return [render_template(item, values) for item in payload]
    if isinstance(payload, dict):
        return {key: render_template(value, values) for key, value in payload.items()}
    return payload


def normalize_errors(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str):
        return [raw_value] if raw_value.strip() else []
    return [str(raw_value)]


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def build_endpoint_url(
    mic_config: dict,
    url_key: str,
    path_key: str,
    default_connection: dict | None = None,
) -> str:
    direct_url = str(mic_config.get(url_key, "") or "").strip()
    if direct_url:
        return direct_url

    default_connection = default_connection or {}
    device_ip = str(mic_config.get("device_ip", "") or "").strip()
    endpoint_path = str(mic_config.get(path_key, "") or "").strip()
    if not device_ip or not endpoint_path:
        return ""

    scheme = str(mic_config.get("scheme") or default_connection.get("scheme") or "https").strip()
    port = mic_config.get("port") or default_connection.get("port")
    normalized_path = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
    if port:
        return f"{scheme}://{device_ip}:{int(port)}{normalized_path}"
    return f"{scheme}://{device_ip}{normalized_path}"


def endpoint_host(url: str) -> str:
    if not url:
        return ""
    return urlsplit(url).hostname or ""


def qlxd_name(value: str) -> str:
    sanitized = (value or "").strip()[:8]
    return sanitized.ljust(8)


def qlxd_percent(raw_value: str, maximum: int) -> int:
    try:
        raw = int(raw_value)
    except (TypeError, ValueError):
        return 0
    if raw < 0:
        return 0
    return clamp((raw / maximum) * 100, 0, 100, fallback=0)


def qlxd_audio_percent(raw_value: str) -> int:
    try:
        raw = int(raw_value)
    except (TypeError, ValueError):
        return 0
    return clamp(raw * 2, 0, 100, fallback=0)


def extract_qlxd_frames(buffer: str) -> tuple[list[str], str]:
    frames: list[str] = []
    while True:
        start = buffer.find("<")
        end = buffer.find(">", start + 1)
        if start == -1 or end == -1:
            break
        frames.append(buffer[start + 1 : end].strip())
        buffer = buffer[end + 1 :]
    return frames, buffer


def micboard_battery_percent(raw_value: Any) -> int:
    try:
        raw = int(raw_value)
    except (TypeError, ValueError):
        return 0
    if raw < 0 or raw >= 250:
        return 0
    if raw <= 5:
        return clamp((raw / 5) * 100, 0, 100, fallback=0)
    return clamp(raw, 0, 100, fallback=0)


def micboard_level_percent(raw_value: Any, maximum: int = 13) -> int:
    try:
        raw = int(raw_value)
    except (TypeError, ValueError):
        return 0
    if raw < 0 or raw >= 250:
        return 0
    if raw <= maximum:
        return clamp((raw / maximum) * 100, 0, 100, fallback=0)
    return clamp(raw, 0, 100, fallback=0)


def humanize_status(status: Any) -> str:
    normalized = str(status or "").strip()
    if not normalized:
        return ""
    return normalized.replace("_", " ").title()


QLXD_RECONNECT_DELAY_SECONDS = 2.0
QLXD_READ_TIMEOUT_SECONDS = 0.5
QLXD_SAMPLE_TIMEOUT_SECONDS = 5.0
QLXD_QUERY_INTERVAL_SECONDS = 0.5
QLXD_BATTERY_STALE_SECONDS = 30 * 60
QLXD_AUDIO_PEAK_SECONDS = 10.0
QLXD_METER_RATE_MS = 100


@dataclass
class QlxdChannelState:
    channel: int
    name: str = ""
    battery: int = 255
    previous_battery: int = 255
    battery_seen_at: float = 0.0
    last_sample_at: float = 0.0
    rf_level: int = 0
    audio_level: int = 0
    peak_at: float = 0.0
    antenna: str = ""
    frequency: str = ""
    runtime: str = ""
    tx_type: str = ""
    encryption_warning: str = ""
    tx_offset: int | None = None
    raw: dict[str, str] = field(default_factory=dict)

    def apply_frame(self, frame: str) -> None:
        now = time.monotonic()
        sample_match = re.match(r"^SAMPLE\s+(\d+)\s+ALL\s+(\S+)\s+(\d{1,3})\s+(\d{1,3})$", frame)
        if sample_match and int(sample_match.group(1)) == self.channel:
            self.antenna = sample_match.group(2)
            self.rf_level = qlxd_percent(sample_match.group(3), 115)
            self.audio_level = qlxd_audio_percent(sample_match.group(4))
            self.last_sample_at = now
            if self.audio_level >= 80:
                self.peak_at = now
            return

        brace_match = re.match(r"^(?:REP|REPLY|REPORT)\s+(\d+)\s+([A-Z_]+)\s+\{(.*)\}$", frame)
        if brace_match and int(brace_match.group(1)) == self.channel:
            self._apply_report(brace_match.group(2), brace_match.group(3).strip(), now)
            return

        plain_match = re.match(r"^(?:REP|REPLY|REPORT)\s+(\d+)\s+([A-Z_]+)\s+(.+)$", frame)
        if plain_match and int(plain_match.group(1)) == self.channel:
            self._apply_report(plain_match.group(2), plain_match.group(3).strip(), now)

    def _apply_report(self, key: str, value: str, now: float) -> None:
        self.raw[key] = value
        if key == "CHAN_NAME":
            self.name = value.replace("_", " ").strip()
            return
        if key == "BATT_BARS":
            if value == "U":
                self.battery = 255
            else:
                try:
                    self.battery = int(value)
                except ValueError:
                    self.battery = 255
            if 1 <= self.battery <= 5:
                self.previous_battery = self.battery
                self.battery_seen_at = now
            return
        if key == "BATT_RUN_TIME":
            self.runtime = value
            return
        if key == "TX_TYPE":
            self.tx_type = value
            return
        if key == "ENCRYPTION_WARNING":
            self.encryption_warning = value.upper()
            return
        if key == "FREQUENCY":
            normalized = value.strip()
            if normalized.isdigit() and len(normalized) > 3:
                self.frequency = f"{normalized[:-3]}.{normalized[-3:]}"
            else:
                self.frequency = normalized
            return
        if key == "TX_OFFSET":
            try:
                self.tx_offset = int(value)
            except ValueError:
                self.tx_offset = None

    def battery_percent(self) -> int:
        if 1 <= self.battery <= 5:
            return clamp((self.battery / 5) * 100, 0, 100, fallback=0)
        if 1 <= self.previous_battery <= 5:
            return clamp((self.previous_battery / 5) * 100, 0, 100, fallback=0)
        return 0

    def battery_alert(self, now: float) -> str:
        if self.battery_seen_at and (now - self.battery_seen_at) <= QLXD_BATTERY_STALE_SECONDS:
            level = self.battery if self.battery != 255 else self.previous_battery
            percent = clamp((level / 5) * 100, 0, 100, fallback=0) if 0 <= level <= 5 else 0
            if percent <= LOW_BATTERY_PERCENT:
                return "Low battery"
            return ""
        return ""

    def has_recent_battery(self, now: float) -> bool:
        return bool(self.battery_seen_at and (now - self.battery_seen_at) <= QLXD_BATTERY_STALE_SECONDS)

    def has_current_battery(self) -> bool:
        return 1 <= self.battery <= 5

    def has_recent_audio_peak(self, now: float) -> bool:
        return self.peak_at > 0 and (now - self.peak_at) <= QLXD_AUDIO_PEAK_SECONDS


class QlxdReceiverRuntime:
    def __init__(self, host: str, port: int, channels: set[int]) -> None:
        self.host = host
        self.port = port
        self.channels = {int(channel) for channel in channels if int(channel) > 0}
        self.connection_status = "disconnected"
        self.last_error = ""
        self.connected_at = 0.0
        self._last_message_at = 0.0
        self._states = {channel: QlxdChannelState(channel) for channel in self.channels}
        self._task: asyncio.Task | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._stop_requested = False
        self._write_lock: asyncio.Lock | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_requested = False
        logger.info("starting qlxd runtime host=%s port=%s channels=%s", self.host, self.port, sorted(self.channels))
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_requested = True
        logger.info("stopping qlxd runtime host=%s port=%s channels=%s", self.host, self.port, sorted(self.channels))
        await self._close_writer(send_meter_stop=True)
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.connection_status = "disconnected"

    async def update_channels(self, channels: set[int]) -> None:
        normalized = {int(channel) for channel in channels if int(channel) > 0}
        added = normalized - self.channels
        removed = self.channels - normalized
        self.channels = normalized
        for channel in added:
            self._states[channel] = QlxdChannelState(channel)
        for channel in removed:
            self._states.pop(channel, None)

        if self.connection_status == "connected" and (added or removed):
            logger.info(
                "updating qlxd channels host=%s port=%s added=%s removed=%s",
                self.host,
                self.port,
                sorted(added),
                sorted(removed),
            )
            commands = [self._meter_stop_command(channel) for channel in sorted(removed)]
            commands.extend(self._startup_commands(sorted(added)))
            await self._send_commands(commands)

    def state_for_channel(self, channel: int) -> QlxdChannelState | None:
        return self._states.get(int(channel))

    async def rename_channel(self, channel: int, new_name: str) -> None:
        if self.connection_status != "connected" or self._writer is None:
            raise ConnectionError(f"Receiver {self.host} is not connected")
        normalized_name = qlxd_name(new_name)
        logger.info(
            "renaming qlxd channel host=%s port=%s channel=%s name=%s",
            self.host,
            self.port,
            channel,
            normalized_name.strip(),
        )
        await self._send_commands(
            [
                f"< SET {int(channel)} CHAN_NAME {{{normalized_name}}} >",
                f"< GET {int(channel)} CHAN_NAME >",
            ]
        )
        state = self._states.setdefault(int(channel), QlxdChannelState(int(channel)))
        state.name = normalized_name.strip()

    async def _run(self) -> None:
        buffer = ""
        while not self._stop_requested:
            try:
                self.connection_status = "connecting"
                logger.info("connecting qlxd receiver host=%s port=%s", self.host, self.port)
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=2.0,
                )
                self.connection_status = "connected"
                self.last_error = ""
                self.connected_at = time.monotonic()
                self._last_message_at = self.connected_at
                logger.info("connected qlxd receiver host=%s port=%s", self.host, self.port)
                buffer = ""
                await self._send_commands(self._startup_commands())
                next_query_at = time.monotonic() + QLXD_QUERY_INTERVAL_SECONDS

                while not self._stop_requested:
                    now = time.monotonic()
                    if now >= next_query_at:
                        await self._send_commands(self._query_commands())
                        next_query_at = now + QLXD_QUERY_INTERVAL_SECONDS

                    try:
                        chunk = await asyncio.wait_for(
                            self._reader.read(4096),
                            timeout=QLXD_READ_TIMEOUT_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        if (time.monotonic() - self._last_message_at) > QLXD_SAMPLE_TIMEOUT_SECONDS:
                            raise TimeoutError("Receiver sample timeout")
                        continue

                    if not chunk:
                        raise ConnectionError("Receiver closed socket")

                    buffer += chunk.decode("ascii", errors="ignore")
                    frames, buffer = extract_qlxd_frames(buffer)
                    if not frames:
                        continue
                    self._last_message_at = time.monotonic()
                    for frame in frames:
                        self._apply_frame(frame)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = str(exc)
                self.connection_status = "disconnected"
                logger.warning(
                    "qlxd receiver fault host=%s port=%s error=%s",
                    self.host,
                    self.port,
                    exc,
                )
                await self._close_writer(send_meter_stop=False)
                if not self._stop_requested:
                    await asyncio.sleep(QLXD_RECONNECT_DELAY_SECONDS)

    def _apply_frame(self, frame: str) -> None:
        parts = frame.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return
        channel = int(parts[1])
        if channel not in self.channels:
            return
        state = self._states.setdefault(channel, QlxdChannelState(channel))
        previous = (
            state.name,
            state.battery,
            state.rf_level,
            state.audio_level,
            state.encryption_warning,
            state.last_sample_at,
        )
        state.apply_frame(frame)
        logger.debug(
            "qlxd frame host=%s port=%s channel=%s frame=%s",
            self.host,
            self.port,
            channel,
            frame,
        )
        if state.name != previous[0]:
            logger.info(
                "qlxd channel name host=%s port=%s channel=%s name=%s",
                self.host,
                self.port,
                channel,
                state.name,
            )
        if state.battery != previous[1]:
            logger.info(
                "qlxd battery host=%s port=%s channel=%s bars=%s percent=%s",
                self.host,
                self.port,
                channel,
                state.battery,
                state.battery_percent(),
            )
        if (state.rf_level, state.audio_level) != (previous[2], previous[3]):
            logger.debug(
                "qlxd metering host=%s port=%s channel=%s rf=%s audio=%s antenna=%s",
                self.host,
                self.port,
                channel,
                state.rf_level,
                state.audio_level,
                state.antenna,
            )
        if state.encryption_warning != previous[4]:
            logger.warning(
                "qlxd encryption host=%s port=%s channel=%s warning=%s",
                self.host,
                self.port,
                channel,
                state.encryption_warning,
            )

    def _startup_commands(self, channels: list[int] | None = None) -> list[str]:
        target_channels = channels if channels is not None else sorted(self.channels)
        commands: list[str] = []
        for channel in target_channels:
            commands.extend(
                [
                    f"< SET {channel} METER_RATE {QLXD_METER_RATE_MS:05d} >",
                    f"< GET {channel} ALL >",
                    f"< GET {channel} ENCRYPTION_WARNING >",
                    f"< GET {channel} BATT_RUN_TIME >",
                    f"< GET {channel} TX_TYPE >",
                ]
            )
        return commands

    def _query_commands(self) -> list[str]:
        commands: list[str] = []
        for channel in sorted(self.channels):
            commands.extend(
                [
                    f"< GET {channel} CHAN_NAME >",
                    f"< GET {channel} BATT_BARS >",
                    f"< GET {channel} ENCRYPTION_WARNING >",
                ]
            )
        return commands

    def _meter_stop_command(self, channel: int) -> str:
        return f"< SET {channel} METER_RATE 00000 >"

    async def _send_commands(self, commands: list[str]) -> None:
        if not commands or self._writer is None:
            return
        async with self._write_lock_for():
            if self._writer is None:
                return
            for command in commands:
                logger.debug("qlxd command host=%s port=%s command=%s", self.host, self.port, command)
                self._writer.write(f"{command}\r\n".encode("ascii"))
            await self._writer.drain()

    async def _close_writer(self, send_meter_stop: bool) -> None:
        writer = self._writer
        self._writer = None
        self._reader = None
        if writer is None:
            return

        try:
            if send_meter_stop:
                async with self._write_lock_for():
                    for channel in sorted(self.channels):
                        writer.write(f"{self._meter_stop_command(channel)}\r\n".encode("ascii"))
                    await writer.drain()
        except Exception:
            pass

        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    def _write_lock_for(self) -> asyncio.Lock:
        if self._write_lock is None:
            self._write_lock = asyncio.Lock()
        return self._write_lock

    def diagnostics(self) -> dict[str, Any]:
        now = time.monotonic()
        return {
            "host": self.host,
            "port": self.port,
            "connection_status": self.connection_status,
            "last_error": self.last_error,
            "connected_for_seconds": round(max(0.0, now - self.connected_at), 3) if self.connected_at else 0.0,
            "seconds_since_last_message": round(max(0.0, now - self._last_message_at), 3) if self._last_message_at else None,
            "channels": [
                {
                    "channel": channel,
                    "name": state.name,
                    "battery_bars": state.battery,
                    "battery_percent": state.battery_percent(),
                    "battery_alert": state.battery_alert(now),
                    "rf_level": state.rf_level,
                    "audio_level": state.audio_level,
                    "antenna": state.antenna,
                    "encryption_warning": state.encryption_warning,
                    "tx_type": state.tx_type,
                    "frequency": state.frequency,
                    "seconds_since_sample": round(max(0.0, now - state.last_sample_at), 3) if state.last_sample_at else None,
                    "raw": state.raw,
                }
                for channel, state in sorted(self._states.items())
            ],
        }


class ShureAdapter(ABC):
    @abstractmethod
    async def refresh(self) -> list[MicSnapshot]:
        raise NotImplementedError

    @abstractmethod
    async def rename_mic(self, mic_id: str, new_name: str) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        return None


class MockShureAdapter(ShureAdapter):
    def __init__(self) -> None:
        self._tick = 0
        self._mics = [
            {
                "id": "mic-1",
                "shure_name": "HANDHELD 1",
                "receiver_name": "Rack A",
                "channel_label": "A1",
                "battery_percent": 91,
                "signal_strength": 82,
                "audio_level": 44,
            },
            {
                "id": "mic-2",
                "shure_name": "HANDHELD 2",
                "receiver_name": "Rack A",
                "channel_label": "A2",
                "battery_percent": 78,
                "signal_strength": 75,
                "audio_level": 38,
            },
            {
                "id": "mic-3",
                "shure_name": "LAV 1",
                "receiver_name": "Rack A",
                "channel_label": "A3",
                "battery_percent": 56,
                "signal_strength": 65,
                "audio_level": 22,
            },
            {
                "id": "mic-4",
                "shure_name": "LAV 2",
                "receiver_name": "Rack A",
                "channel_label": "A4",
                "battery_percent": 33,
                "signal_strength": 49,
                "audio_level": 54,
            },
            {
                "id": "mic-5",
                "shure_name": "HEADSET 1",
                "receiver_name": "Rack B",
                "channel_label": "B1",
                "battery_percent": 71,
                "signal_strength": 86,
                "audio_level": 48,
            },
            {
                "id": "mic-6",
                "shure_name": "HEADSET 2",
                "receiver_name": "Rack B",
                "channel_label": "B2",
                "battery_percent": 64,
                "signal_strength": 57,
                "audio_level": 61,
            },
            {
                "id": "mic-7",
                "shure_name": "INTERVIEW 1",
                "receiver_name": "Rack B",
                "channel_label": "B3",
                "battery_percent": 18,
                "signal_strength": 31,
                "audio_level": 25,
            },
            {
                "id": "mic-8",
                "shure_name": "INTERVIEW 2",
                "receiver_name": "Rack B",
                "channel_label": "B4",
                "battery_percent": 88,
                "signal_strength": 91,
                "audio_level": 34,
            },
        ]

    async def refresh(self) -> list[MicSnapshot]:
        self._tick += 1
        snapshots: list[MicSnapshot] = []

        for index, mic in enumerate(self._mics):
            battery_drop = 1 if self._tick % (index + 3) == 0 else 0
            mic["battery_percent"] = max(8, mic["battery_percent"] - battery_drop)
            signal_delta = ((self._tick * (index + 2)) % 9) - 4
            mic["signal_strength"] = clamp(mic["signal_strength"] + signal_delta, 18, 100, fallback=60)
            mic["audio_level"] = clamp((self._tick * 11 + index * 17) % 100, 0, 100, fallback=30)

            is_online = not (index == 7 and self._tick % 14 == 0)
            errors = []
            if mic["battery_percent"] <= LOW_BATTERY_PERCENT:
                errors.append("Low battery")
            if mic["signal_strength"] <= 28:
                errors.append("RF drop risk")
            if index == 5 and self._tick % 6 == 0:
                errors.append("Audio clip warning")
            if not is_online:
                errors = ["Receiver not responding"]

            snapshots.append(
                MicSnapshot(
                    id=mic["id"],
                    shure_name=mic["shure_name"],
                    receiver_name=mic["receiver_name"],
                    channel_label=mic["channel_label"],
                    battery_percent=mic["battery_percent"],
                    signal_strength=mic["signal_strength"],
                    audio_level=mic["audio_level"],
                    is_online=is_online,
                    errors=errors,
                )
            )

        return snapshots

    async def rename_mic(self, mic_id: str, new_name: str) -> None:
        for mic in self._mics:
            if mic["id"] == mic_id:
                mic["shure_name"] = new_name.strip()
                return
        raise KeyError(f"Unknown microphone: {mic_id}")


class MicboardAdapter(ShureAdapter):
    def __init__(self, mapping_store: MappingStore, client: httpx.AsyncClient | None = None) -> None:
        self.mapping_store = mapping_store
        self._client = client or httpx.AsyncClient(timeout=5.0)
        self._owns_client = client is None
        self._resolved_host_cache: dict[str, tuple[float, set[str]]] = {}

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def refresh(self) -> list[MicSnapshot]:
        mapping = self.mapping_store.load()
        micboard_config = mapping.get("micboard", {})
        configured_mics = mapping.get("mics", [])
        data_url = str(micboard_config.get("data_url", "") or "").strip()

        if not data_url:
            if not configured_mics:
                raise ValueError("No Micboard data URL configured")
            return [
                self._offline_snapshot(mic_config, "No Micboard data URL configured")
                for mic_config in configured_mics
            ]

        try:
            response = await self._client.get(data_url)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            if configured_mics:
                return [
                    self._offline_snapshot(mic_config, f"Fetch failed: {exc}")
                    for mic_config in configured_mics
                ]
            raise

        entries = self._extract_entries(payload)
        if configured_mics:
            return await self._snapshots_for_configured_mics(configured_mics, entries)
        return self._snapshots_for_discovered_entries(entries)

    async def rename_mic(self, mic_id: str, new_name: str) -> None:
        return None

    def _extract_entries(self, payload: Any) -> list[dict[str, Any]]:
        receivers = payload.get("receivers", []) if isinstance(payload, dict) else payload
        if isinstance(receivers, dict):
            receiver_list = list(receivers.values())
        elif isinstance(receivers, list):
            receiver_list = receivers
        else:
            receiver_list = []

        entries: list[dict[str, Any]] = []
        for receiver in receiver_list:
            if not isinstance(receiver, dict):
                continue
            for tx in receiver.get("tx", []) or []:
                if not isinstance(tx, dict):
                    continue
                entries.append({"receiver": receiver, "tx": tx})
        return entries

    async def _snapshots_for_configured_mics(
        self,
        configured_mics: list[dict[str, Any]],
        entries: list[dict[str, Any]],
    ) -> list[MicSnapshot]:
        used_indexes: set[int] = set()
        snapshots: list[MicSnapshot] = []

        for mic_config in configured_mics:
            match_index = await self._find_match_index(mic_config, entries, used_indexes)
            if match_index is None:
                snapshots.append(
                    self._offline_snapshot(
                        mic_config,
                        "No Micboard receiver matched this entry",
                    )
                )
                continue
            used_indexes.add(match_index)
            snapshots.append(self._snapshot_from_entry(mic_config, entries[match_index]))
        return snapshots

    def _snapshots_for_discovered_entries(self, entries: list[dict[str, Any]]) -> list[MicSnapshot]:
        snapshots: list[MicSnapshot] = []
        for index, entry in enumerate(entries, start=1):
            receiver = entry["receiver"]
            tx = entry["tx"]
            receiver_ip = str(receiver.get("ip", "") or "").strip()
            channel = int(tx.get("channel") or tx.get("slot") or index)
            mic_config = {
                "id": f"micboard-{receiver_ip or 'receiver'}-{channel}",
                "default_name": str(tx.get("name_raw") or tx.get("name") or f"MIC {index}"),
                "receiver_name": str((receiver.get("raw") or {}).get("DEVICE_ID", receiver_ip)),
                "channel_label": str(tx.get("slot") or tx.get("channel") or index),
            }
            snapshots.append(self._snapshot_from_entry(mic_config, entry))
        return snapshots

    async def _find_match_index(
        self,
        mic_config: dict[str, Any],
        entries: list[dict[str, Any]],
        used_indexes: set[int],
    ) -> int | None:
        device_keys = await self._device_keys(str(mic_config.get("device_ip", "") or ""))
        micboard_slot = int(mic_config.get("micboard_slot") or 0)
        receiver_channel = int(mic_config.get("receiver_channel") or 0)
        unique_channel = receiver_channel > 0 and sum(
            1
            for entry in entries
            if int(entry["tx"].get("channel") or 0) == receiver_channel
        ) == 1

        candidates: list[tuple[int, int]] = []
        for index, entry in enumerate(entries):
            if index in used_indexes:
                continue

            receiver = entry["receiver"]
            tx = entry["tx"]
            receiver_ip = str(receiver.get("ip", "") or "").strip().lower()
            tx_channel = int(tx.get("channel") or 0)
            tx_slot = int(tx.get("slot") or 0)

            score = 0
            if device_keys:
                if receiver_ip in device_keys:
                    score += 100
                else:
                    continue

            if micboard_slot > 0:
                if tx_slot == micboard_slot:
                    score += 30
                else:
                    continue

            if receiver_channel > 0:
                if tx_channel == receiver_channel:
                    score += 15 if (device_keys or micboard_slot or unique_channel) else 1
                elif device_keys or micboard_slot or unique_channel:
                    continue

            candidates.append((score, index))

        if candidates:
            candidates.sort(key=lambda item: (-item[0], item[1]))
            best_score, best_index = candidates[0]
            if best_score > 0 or not (device_keys or micboard_slot or receiver_channel):
                return best_index

        if not (device_keys or micboard_slot or receiver_channel):
            for index in range(len(entries)):
                if index not in used_indexes:
                    return index

        return None

    async def _device_keys(self, device_value: str) -> set[str]:
        normalized = device_value.strip().lower()
        if not normalized:
            return set()

        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", normalized):
            return {normalized}

        cached = self._resolved_host_cache.get(normalized)
        now = time.monotonic()
        if cached and cached[0] > now:
            return set(cached[1])

        resolved = {normalized}
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                normalized,
                None,
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
            )
            for info in infos:
                sockaddr = info[4]
                if sockaddr:
                    resolved.add(str(sockaddr[0]).lower())
        except socket.gaierror:
            pass

        self._resolved_host_cache[normalized] = (now + 300, set(resolved))
        return resolved

    def _offline_snapshot(self, mic_config: dict[str, Any], error_message: str) -> MicSnapshot:
        return MicSnapshot(
            id=mic_config["id"],
            shure_name=str(mic_config.get("default_name", mic_config["id"])),
            receiver_name=str(mic_config.get("receiver_name", "")),
            channel_label=str(mic_config.get("channel_label", "")),
            battery_percent=0,
            signal_strength=0,
            audio_level=0,
            is_online=False,
            errors=[error_message],
            source="micboard",
            connection_state="error",
        )

    def _snapshot_from_entry(self, mic_config: dict[str, Any], entry: dict[str, Any]) -> MicSnapshot:
        receiver = entry["receiver"]
        tx = entry["tx"]
        receiver_raw = receiver.get("raw") or {}
        tx_raw = tx.get("raw") or {}
        receiver_status = str(receiver.get("status", "") or "").strip().upper()
        tx_status = str(tx.get("status", "") or "").strip().upper()
        battery_percent = micboard_battery_percent(tx.get("battery"))
        errors: list[str] = []

        if receiver_status and receiver_status != "CONNECTED":
            errors.append("Receiver disconnected")

        status_messages = {
            "TX_COM_ERROR": "Transmitter unavailable",
            "RX_COM_ERROR": "Receiver communication error",
            "AUDIO_PEAK": "Audio peak",
        }
        if tx_status == "CRITICAL":
            if battery_percent <= LOW_BATTERY_PERCENT:
                errors.append("Low battery")
        elif tx_status == "REPLACE":
            if battery_percent <= LOW_BATTERY_PERCENT:
                errors.append("Low battery")
        elif tx_status and tx_status not in {"CONNECTED", "OK", "NORMAL"}:
            errors.append(status_messages.get(tx_status, humanize_status(tx_status)))

        encryption_status = str(tx_raw.get("ENCRYPTION_STATUS", "") or "").strip().upper()
        if encryption_status and encryption_status not in {"OK", "ON", "OFF"}:
            errors.append(f"Encryption {humanize_status(encryption_status)}")

        if battery_percent and battery_percent <= LOW_BATTERY_PERCENT:
            errors.append("Low battery")

        is_online = receiver_status == "CONNECTED" and tx_status not in {"TX_COM_ERROR", "RX_COM_ERROR"}
        connection_state = "ok"
        if not is_online:
            connection_state = "error"
        elif errors:
            connection_state = "warning"

        return MicSnapshot(
            id=mic_config["id"],
            shure_name=str(
                tx.get("name_raw")
                or tx.get("name")
                or mic_config.get("default_name", mic_config["id"])
            ),
            receiver_name=str(
                mic_config.get("receiver_name")
                or receiver_raw.get("DEVICE_ID")
                or receiver.get("ip", "")
            ),
            channel_label=str(
                mic_config.get("channel_label")
                or tx.get("channel")
                or tx.get("slot")
                or ""
            ),
            battery_percent=battery_percent,
            signal_strength=micboard_level_percent(tx.get("rf_level")),
            audio_level=micboard_level_percent(tx.get("audio_level")),
            is_online=is_online,
            errors=dedupe_preserve_order(errors),
            source="micboard",
            connection_state=connection_state,
        )


class QlxdAdapter(ShureAdapter):
    def __init__(self, mapping_store: MappingStore) -> None:
        self.mapping_store = mapping_store
        self._receivers: dict[tuple[str, int], QlxdReceiverRuntime] = {}
        self._sync_lock: asyncio.Lock | None = None

    async def close(self) -> None:
        for key, runtime in list(self._receivers.items()):
            await runtime.stop()
            self._receivers.pop(key, None)

    async def refresh(self) -> list[MicSnapshot]:
        mapping = self.mapping_store.load()
        await self._sync_receivers(mapping)
        default_connection = mapping.get("default_connection", {})
        return [
            self._snapshot_for_mic(mic_config, default_connection)
            for mic_config in mapping.get("mics", [])
        ]

    async def rename_mic(self, mic_id: str, new_name: str) -> None:
        mapping = self.mapping_store.load()
        await self._sync_receivers(mapping)
        mic_config = next((item for item in mapping.get("mics", []) if item["id"] == mic_id), None)
        if not mic_config:
            raise KeyError(f"Unknown microphone: {mic_id}")
        host = str(mic_config.get("device_ip", "") or "").strip()
        if not host:
            raise ValueError(f"No QLX-D receiver host configured for {mic_id}")
        port = int(mic_config.get("port") or mapping.get("default_connection", {}).get("port") or 2202)
        channel = int(mic_config.get("receiver_channel") or 1)
        runtime = self._receivers.get((host, port))
        if runtime is None:
            raise ConnectionError(f"Receiver {host}:{port} is not connected")
        await runtime.rename_channel(channel, new_name)

    async def _sync_receivers(self, mapping: dict) -> None:
        desired: dict[tuple[str, int], set[int]] = {}
        default_connection = mapping.get("default_connection", {})
        for mic_config in mapping.get("mics", []):
            host = str(mic_config.get("device_ip", "") or "").strip()
            if not host:
                continue
            port = int(mic_config.get("port") or default_connection.get("port") or 2202)
            channel = int(mic_config.get("receiver_channel") or 1)
            desired.setdefault((host, port), set()).add(channel)

        async with self._sync_lock_for():
            existing_keys = set(self._receivers)
            for key, channels in desired.items():
                runtime = self._receivers.get(key)
                if runtime is None:
                    runtime = QlxdReceiverRuntime(key[0], key[1], channels)
                    self._receivers[key] = runtime
                    await runtime.start()
                else:
                    await runtime.update_channels(channels)
                    await runtime.start()

            for key in existing_keys - set(desired):
                runtime = self._receivers.pop(key)
                await runtime.stop()

    def _snapshot_for_mic(self, mic_config: dict[str, Any], default_connection: dict) -> MicSnapshot:
        host = str(mic_config.get("device_ip", "") or "").strip()
        if not host:
            return self._offline_snapshot(mic_config, "No QLX-D receiver host configured")

        port = int(mic_config.get("port") or default_connection.get("port") or 2202)
        channel = int(mic_config.get("receiver_channel") or 1)
        runtime = self._receivers.get((host, port))
        if runtime is None:
            return self._offline_snapshot(mic_config, "Receiver runtime not initialized")

        state = runtime.state_for_channel(channel)
        if state is None:
            return self._offline_snapshot(mic_config, f"Receiver channel {channel} is not configured")

        now = time.monotonic()
        errors: list[str] = []
        is_online = runtime.connection_status == "connected"

        if runtime.connection_status != "connected":
            errors.append(runtime.last_error or "Receiver disconnected")
        elif not state.last_sample_at:
            is_online = False
            errors.append("Waiting for receiver data")
        elif (now - state.last_sample_at) > QLXD_SAMPLE_TIMEOUT_SECONDS:
            is_online = False
            errors.append("Receiver sample timeout")

        battery_percent = state.battery_percent()
        if is_online and not state.has_current_battery():
            is_online = False
            errors.append("Transmitter off or battery unavailable")

        battery_alert = state.battery_alert(now)
        if battery_alert:
            errors.append(battery_alert)
        if state.has_recent_audio_peak(now):
            errors.append("Audio peak")
        if state.encryption_warning == "ON":
            errors.append("Encryption mismatch")

        connection_state = "ok"
        if not is_online:
            connection_state = "error"
        elif errors:
            connection_state = "warning"

        return MicSnapshot(
            id=mic_config["id"],
            shure_name=str(state.name or mic_config.get("default_name", mic_config["id"])).strip(),
            receiver_name=str(mic_config.get("receiver_name", "")),
            channel_label=str(mic_config.get("channel_label", "")),
            battery_percent=battery_percent,
            signal_strength=state.rf_level,
            audio_level=state.audio_level,
            is_online=is_online,
            errors=dedupe_preserve_order(errors),
            source="qlxd",
            connection_state=connection_state,
        )

    def _offline_snapshot(self, mic_config: dict[str, Any], error_message: str) -> MicSnapshot:
        return MicSnapshot(
            id=mic_config["id"],
            shure_name=str(mic_config.get("default_name", mic_config["id"])),
            receiver_name=str(mic_config.get("receiver_name", "")),
            channel_label=str(mic_config.get("channel_label", "")),
            battery_percent=0,
            signal_strength=0,
            audio_level=0,
            is_online=False,
            errors=[error_message],
            source="qlxd",
            connection_state="error",
        )

    def diagnostics(self) -> dict[str, Any]:
        return {
            "source": "qlxd",
            "receivers": [
                runtime.diagnostics()
                for _, runtime in sorted(self._receivers.items(), key=lambda item: item[0])
            ],
        }

    def _sync_lock_for(self) -> asyncio.Lock:
        if self._sync_lock is None:
            self._sync_lock = asyncio.Lock()
        return self._sync_lock


class SystemApiAdapter(ShureAdapter):
    def __init__(self, mapping_store: MappingStore) -> None:
        self.mapping_store = mapping_store
        self._client = httpx.AsyncClient(timeout=5.0)
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_signature: tuple[str, str, str] | None = None

    async def close(self) -> None:
        await self._client.aclose()

    async def refresh(self) -> list[MicSnapshot]:
        mapping = self.mapping_store.load()
        snapshots: list[MicSnapshot] = []
        default_headers = await self._build_headers(mapping, mapping.get("default_headers"))
        default_connection = mapping.get("default_connection", {})

        for mic_config in mapping.get("mics", []):
            headers = await self._build_headers(mapping, mic_config.get("headers"), default_headers)
            telemetry_url = build_endpoint_url(
                mic_config,
                "telemetry_url",
                "telemetry_path",
                default_connection,
            )
            if not telemetry_url:
                snapshots.append(
                    MicSnapshot(
                        id=mic_config["id"],
                        shure_name=str(mic_config.get("default_name", mic_config["id"])),
                        receiver_name=str(mic_config.get("receiver_name", "")),
                        channel_label=str(mic_config.get("channel_label", "")),
                        battery_percent=0,
                        signal_strength=0,
                        audio_level=0,
                        is_online=False,
                        errors=["No telemetry URL or IP configured"],
                        source="system_api",
                        connection_state="error",
                    )
                )
                continue

            try:
                response = await self._client.request(
                    mic_config.get("telemetry_method", "GET").upper(),
                    telemetry_url,
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                fields = mic_config.get("fields", {})
                snapshots.append(
                    MicSnapshot(
                        id=mic_config["id"],
                        shure_name=str(
                            deep_get(
                                payload,
                                fields.get("shure_name"),
                                mic_config.get("default_name", mic_config["id"]),
                            )
                        ),
                        receiver_name=str(mic_config.get("receiver_name", "")),
                        channel_label=str(mic_config.get("channel_label", "")),
                        battery_percent=clamp(
                            deep_get(payload, fields.get("battery_percent"), 0),
                            fallback=0,
                        ),
                        signal_strength=clamp(
                            deep_get(payload, fields.get("signal_strength"), 0),
                            fallback=0,
                        ),
                        audio_level=clamp(
                            deep_get(payload, fields.get("audio_level"), 0),
                            fallback=0,
                        ),
                        is_online=bool(deep_get(payload, fields.get("is_online"), True)),
                        errors=normalize_errors(deep_get(payload, fields.get("errors"), [])),
                        source="system_api",
                    )
                )
            except Exception as exc:
                snapshots.append(
                    MicSnapshot(
                        id=mic_config["id"],
                        shure_name=str(mic_config.get("default_name", mic_config["id"])),
                        receiver_name=str(mic_config.get("receiver_name", "")),
                        channel_label=str(mic_config.get("channel_label", "")),
                        battery_percent=0,
                        signal_strength=0,
                        audio_level=0,
                        is_online=False,
                        errors=[f"Fetch failed: {exc}"],
                        source="system_api",
                        connection_state="error",
                    )
                )

        return snapshots

    async def rename_mic(self, mic_id: str, new_name: str) -> None:
        mapping = self.mapping_store.load()
        mic_config = next((item for item in mapping.get("mics", []) if item["id"] == mic_id), None)
        if not mic_config:
            raise KeyError(f"Unknown microphone: {mic_id}")
        rename_url = build_endpoint_url(
            mic_config,
            "rename_url",
            "rename_path",
            mapping.get("default_connection", {}),
        )
        if not rename_url:
            raise ValueError(f"No rename_url configured for {mic_id}")

        headers = await self._build_headers(
            mapping,
            mic_config.get("headers"),
            await self._build_headers(mapping, mapping.get("default_headers")),
        )
        payload = render_template(
            mic_config.get("rename_body", {"name": "{name}"}),
            {"name": new_name.strip()},
        )
        response = await self._client.request(
            mic_config.get("rename_method", "PUT").upper(),
            rename_url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

    async def _build_headers(
        self,
        mapping: dict,
        extra_headers: dict[str, str] | None,
        base_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if base_headers:
            headers.update(base_headers)
        auth_header = await self._get_auth_header(mapping)
        if auth_header:
            headers["Authorization"] = auth_header
        if extra_headers:
            headers.update({str(key): str(value) for key, value in extra_headers.items()})
        return headers

    async def _get_auth_header(self, mapping: dict) -> str | None:
        auth = mapping.get("auth", {})
        if not auth:
            return None
        auth_type = str(auth.get("type", "") or "").strip().lower()
        if auth_type in {"", "none", "disabled"}:
            return None
        if auth_type != "bearer":
            return auth.get("header")
        token = await self._get_access_token(mapping)
        return f"Bearer {token}"

    async def _get_access_token(self, mapping: dict) -> str:
        auth = mapping.get("auth", {})
        token_url = str(auth.get("token_url", "") or "").strip()
        if not token_url:
            # Allow unauthenticated deployments to omit OAuth entirely.
            raise ValueError("Authentication is set to bearer, but auth.token_url is blank")

        signature = (
            token_url,
            str(auth.get("client_id", "")),
            str(auth.get("username", "")),
        )
        if signature != self._token_signature:
            self._token = None
            self._token_expires_at = 0.0
            self._token_signature = signature

        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        form = {
            "grant_type": auth.get("grant_type", "client_credentials"),
            "client_id": auth.get("client_id", ""),
            "client_secret": auth.get("client_secret", ""),
        }
        if auth.get("scope"):
            form["scope"] = auth["scope"]
        if auth.get("username"):
            form["username"] = auth["username"]
        if auth.get("password"):
            form["password"] = auth["password"]

        response = await self._client.post(token_url, data=form)
        response.raise_for_status()
        payload = response.json()
        self._token = str(payload["access_token"])
        self._token_expires_at = time.monotonic() + int(payload.get("expires_in", 300)) - 30
        return self._token
