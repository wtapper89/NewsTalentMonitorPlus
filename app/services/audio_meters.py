from __future__ import annotations

import asyncio
import math
import socket
import struct
from copy import deepcopy
from xml.etree import ElementTree

import httpx

from app.store import DEFAULT_AUDIO_METERS


VMIX_BUSES = {"master", "busA", "busB", "busC", "busD", "busE", "busF", "busG"}
WING_METER_TYPES = {
    "channel": 0xA0,
    "aux": 0xA1,
    "bus": 0xA2,
    "main": 0xA3,
    "matrix": 0xA4,
    "dca": 0xA5,
}


def db_to_percent(db: float, floor_db: float = -60.0) -> float:
    if not math.isfinite(db):
        return 0.0
    return round(max(0.0, min(100.0, ((db - floor_db) / -floor_db) * 100.0)), 1)


def vmix_amplitude_to_percent(amplitude: float) -> float:
    if amplitude <= 0:
        return 0.0
    return db_to_percent(20.0 * math.log10(amplitude))


def parse_vmix_levels(xml_text: str, target: str) -> tuple[float, float]:
    root = ElementTree.fromstring(xml_text)
    target = str(target or "master").strip()
    bus_target = next((bus for bus in VMIX_BUSES if bus.lower() == target.lower()), None)
    if bus_target:
        node = root.find(f"./audio/{bus_target}")
    else:
        node = next(
            (
                item
                for item in root.findall("./inputs/input")
                if target.lower()
                in {
                    str(item.get("number") or "").lower(),
                    str(item.get("key") or "").lower(),
                    str(item.get("title") or "").lower(),
                }
            ),
            None,
        )
    if node is None:
        raise ValueError(f"vMix meter target '{target}' was not found")
    left = float(node.get("meterF1") or 0)
    right = float(node.get("meterF2") or left)
    return vmix_amplitude_to_percent(left), vmix_amplitude_to_percent(right)


def parse_wing_meter_packet(packet: bytes, report_id: int) -> tuple[float, float]:
    if len(packet) < 12:
        raise ValueError("WING returned an incomplete meter packet")
    if struct.unpack(">I", packet[:4])[0] != report_id:
        raise ValueError("WING returned a meter packet for another request")
    values = struct.unpack(f">{(len(packet) - 4) // 2}h", packet[4 : len(packet) - ((len(packet) - 4) % 2)])
    if len(values) < 4:
        raise ValueError("WING meter packet did not include stereo output levels")
    return db_to_percent(values[2] / 256.0), db_to_percent(values[3] / 256.0)


class AudioMeterService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def refresh(self, raw_config: dict | None) -> list[dict]:
        config = deepcopy(DEFAULT_AUDIO_METERS)
        config.update(raw_config or {})
        results = await asyncio.gather(
            *(self._read_meter(config.get(side) or {}, side) for side in ("left", "right")),
        )
        return list(results)

    async def _read_meter(self, config: dict, position: str) -> dict:
        source = str(config.get("source") or "off").strip().lower()
        result = {
            "position": position,
            "enabled": source != "off",
            "source": source,
            "label": str(config.get("label") or position.title()),
            "left": 0.0,
            "right": 0.0,
            "online": False,
            "error": "",
        }
        if source == "off":
            return result
        try:
            if source == "vmix":
                left, right = await self._read_vmix(config)
            elif source == "wing":
                left, right = await asyncio.to_thread(self._read_wing, config)
            else:
                raise ValueError(f"Unsupported meter source: {source}")
            result.update({"left": left, "right": right, "online": True})
        except Exception as exc:
            result["error"] = str(exc)
        return result

    async def _read_vmix(self, config: dict) -> tuple[float, float]:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=0.4)
        host = str(config.get("host") or "127.0.0.1").strip()
        port = int(config.get("port") or 8088)
        response = await self._client.get(f"http://{host}:{port}/api/")
        response.raise_for_status()
        return parse_vmix_levels(response.text, str(config.get("target") or "master"))

    @staticmethod
    def _read_wing(config: dict) -> tuple[float, float]:
        host = str(config.get("host") or "127.0.0.1").strip()
        port = int(config.get("port") or 2222)
        meter_group = str(config.get("meter_group") or "main").strip().lower()
        meter_type = WING_METER_TYPES.get(meter_group)
        if meter_type is None:
            raise ValueError(f"Unsupported WING meter group: {meter_group}")
        meter_index = max(1, int(config.get("meter_index") or 1))
        report_id = 0x4E544D50

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind(("0.0.0.0", 0))
            udp_socket.settimeout(0.4)
            local_port = int(udp_socket.getsockname()[1])
            request = (
                b"\xdf\xd3"
                + b"\xd3"
                + struct.pack(">H", local_port)
                + b"\xd4"
                + struct.pack(">I", report_id)
                + bytes((0xDC, meter_type, meter_index - 1, 0xDE))
            )
            with socket.create_connection((host, port), timeout=0.4) as tcp_socket:
                tcp_socket.sendall(request)
                packet, _ = udp_socket.recvfrom(4096)
        return parse_wing_meter_packet(packet, report_id)
