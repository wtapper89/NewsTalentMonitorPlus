from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_FIELDS = {
    "shure_name": "name",
    "battery_percent": "battery.percent",
    "signal_strength": "rf.signalPercent",
    "audio_level": "audio.level",
    "is_online": "status.online",
    "errors": "errors",
}

DEFAULT_DISPLAY = {
    "show_title_mode": "manual",
    "manual_show_title": "TVC NEWS",
    "preview_mode": "placeholder",
    "preview_url": "",
    "preview_source_name": "",
    "preview_poster_url": "",
    "font_family": "Gotham, Montserrat, Arial, sans-serif",
    "now_panel_enabled": True,
    "now_panel_label": "Now",
    "now_panel_border_color": "#1cff00",
    "next_panel_enabled": True,
    "next_panel_label": "Next",
    "next_panel_border_color": "#fff200",
    "status_sign_enabled": True,
    "status_sign_custom_text": "",
}

DEFAULT_COMPANION = {
    "enabled": False,
    "base_url": "http://127.0.0.1:8000",
    "connection_label": "Cuez",
    "variable_name": "",
    "on_air_source_variable_name": "",
    "next_source_variable_name": "",
    "status_sign_variable_name": "",
}

DEFAULT_ANCHOR_PHOTOS = {
    "enabled": False,
    "base_url": "",
    "share_path": "",
    "username": "",
    "password": "",
    "domain": "",
    "timeout_seconds": 4,
}


def default_mic_entry(index: int, name: str, receiver: str, channel: str) -> dict:
    return {
        "id": f"mic-{index}",
        "default_name": name,
        "receiver_name": receiver,
        "channel_label": channel,
        "micboard_slot": 0,
        "receiver_channel": 1,
        "device_ip": "",
        "scheme": "tcp",
        "port": 2202,
        "telemetry_path": f"/api/receivers/{receiver.lower().replace(' ', '-')}/channels/{channel.lower()}",
        "telemetry_method": "GET",
        "rename_path": f"/api/receivers/{receiver.lower().replace(' ', '-')}/channels/{channel.lower()}/name",
        "rename_method": "PUT",
        "rename_body": {"name": "{name}"},
        "fields": deepcopy(DEFAULT_FIELDS),
        "assignment_variable_name": "",
    }


DEFAULT_MAPPING = {
    "auth": {
        "type": "none",
        "token_url": "",
        "grant_type": "client_credentials",
        "client_id": "",
        "client_secret": "",
    },
    "default_headers": {
        "Accept": "application/json",
    },
    "micboard": {
        "data_url": "http://127.0.0.1:8058/data.json",
    },
    "display": deepcopy(DEFAULT_DISPLAY),
    "companion": deepcopy(DEFAULT_COMPANION),
    "anchor_photos": deepcopy(DEFAULT_ANCHOR_PHOTOS),
    "default_connection": {
        "scheme": "tcp",
        "port": 2202,
    },
    "mics": [
        default_mic_entry(1, "HANDHELD 1", "Rack A", "A1"),
        default_mic_entry(2, "HANDHELD 2", "Rack A", "A2"),
        default_mic_entry(3, "LAV 1", "Rack A", "A3"),
        default_mic_entry(4, "LAV 2", "Rack A", "A4"),
        default_mic_entry(5, "HEADSET 1", "Rack B", "B1"),
        default_mic_entry(6, "HEADSET 2", "Rack B", "B2"),
        default_mic_entry(7, "INTERVIEW 1", "Rack B", "B3"),
        default_mic_entry(8, "INTERVIEW 2", "Rack B", "B4"),
    ],
}


def _path_from_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or ""
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return path


def _port_from_url(url: str) -> int | None:
    parsed = urlsplit(url)
    if parsed.port:
        return parsed.port
    if parsed.scheme == "https":
        return 443
    if parsed.scheme == "http":
        return 80
    return None


def _normalize_mic_entry(raw_entry: dict, default_connection: dict) -> dict:
    entry = deepcopy(raw_entry)
    telemetry_url = str(entry.get("telemetry_url", "") or "")
    rename_url = str(entry.get("rename_url", "") or "")

    if telemetry_url and not entry.get("device_ip"):
        parsed = urlsplit(telemetry_url)
        entry["device_ip"] = parsed.hostname or ""
        entry["scheme"] = entry.get("scheme") or parsed.scheme or default_connection.get("scheme", "https")
        entry["port"] = entry.get("port") or _port_from_url(telemetry_url) or default_connection.get("port", 443)
        entry["telemetry_path"] = entry.get("telemetry_path") or _path_from_url(telemetry_url)

    if rename_url:
        parsed = urlsplit(rename_url)
        if not entry.get("device_ip"):
            entry["device_ip"] = parsed.hostname or ""
        entry["scheme"] = entry.get("scheme") or parsed.scheme or default_connection.get("scheme", "https")
        entry["port"] = entry.get("port") or _port_from_url(rename_url) or default_connection.get("port", 443)
        entry["rename_path"] = entry.get("rename_path") or _path_from_url(rename_url)

    entry["scheme"] = str(entry.get("scheme") or default_connection.get("scheme", "https"))
    entry["port"] = int(entry.get("port") or default_connection.get("port", 443))
    entry["device_ip"] = str(entry.get("device_ip", "") or "")
    entry["micboard_slot"] = int(entry.get("micboard_slot") or 0)
    entry["receiver_channel"] = int(entry.get("receiver_channel") or 1)
    entry["telemetry_path"] = str(entry.get("telemetry_path", "") or "")
    entry["rename_path"] = str(entry.get("rename_path", "") or "")
    entry["telemetry_method"] = str(entry.get("telemetry_method", "GET") or "GET").upper()
    entry["rename_method"] = str(entry.get("rename_method", "PUT") or "PUT").upper()
    entry["rename_body"] = entry.get("rename_body") or {"name": "{name}"}
    entry["fields"] = {**DEFAULT_FIELDS, **(entry.get("fields") or {})}
    entry["assignment_variable_name"] = str(entry.get("assignment_variable_name") or "").strip()
    entry["telemetry_url"] = telemetry_url
    entry["rename_url"] = rename_url
    return entry


def _normalize_display(raw_display: dict | None) -> dict:
    display = {**DEFAULT_DISPLAY, **(raw_display or {})}
    display["show_title_mode"] = str(display.get("show_title_mode") or "manual").strip().lower() or "manual"
    if display["show_title_mode"] not in {"manual", "companion"}:
        display["show_title_mode"] = "manual"
    display["manual_show_title"] = str(display.get("manual_show_title") or DEFAULT_DISPLAY["manual_show_title"]).strip()
    display["preview_mode"] = str(display.get("preview_mode") or "placeholder").strip().lower() or "placeholder"
    if display["preview_mode"] not in {"placeholder", "iframe", "image", "video", "ndi"}:
        display["preview_mode"] = "placeholder"
    display["preview_url"] = str(display.get("preview_url") or "").strip()
    display["preview_source_name"] = str(display.get("preview_source_name") or "").strip()
    display["preview_poster_url"] = str(display.get("preview_poster_url") or "").strip()
    display["font_family"] = str(display.get("font_family") or DEFAULT_DISPLAY["font_family"]).strip()
    display["now_panel_enabled"] = _normalize_bool(
        display.get("now_panel_enabled"),
        DEFAULT_DISPLAY["now_panel_enabled"],
    )
    display["now_panel_label"] = str(display.get("now_panel_label") or DEFAULT_DISPLAY["now_panel_label"]).strip()
    display["now_panel_border_color"] = _normalize_hex_color(
        display.get("now_panel_border_color"),
        DEFAULT_DISPLAY["now_panel_border_color"],
    )
    display["next_panel_enabled"] = _normalize_bool(
        display.get("next_panel_enabled"),
        DEFAULT_DISPLAY["next_panel_enabled"],
    )
    display["next_panel_label"] = str(display.get("next_panel_label") or DEFAULT_DISPLAY["next_panel_label"]).strip()
    display["next_panel_border_color"] = _normalize_hex_color(
        display.get("next_panel_border_color"),
        DEFAULT_DISPLAY["next_panel_border_color"],
    )
    display["status_sign_enabled"] = _normalize_bool(
        display.get("status_sign_enabled"),
        DEFAULT_DISPLAY["status_sign_enabled"],
    )
    display["status_sign_custom_text"] = str(display.get("status_sign_custom_text") or "").strip()
    return display


def _normalize_hex_color(value: object, fallback: str) -> str:
    candidate = str(value or "").strip()
    if len(candidate) == 7 and candidate.startswith("#"):
        try:
            int(candidate[1:], 16)
            return candidate.lower()
        except ValueError:
            pass
    return fallback


def _normalize_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return bool(value)


def _normalize_companion(raw_companion: dict | None) -> dict:
    companion = {**DEFAULT_COMPANION, **(raw_companion or {})}
    companion["enabled"] = bool(companion.get("enabled"))
    companion["base_url"] = str(companion.get("base_url") or DEFAULT_COMPANION["base_url"]).strip().rstrip("/")
    companion["connection_label"] = str(companion.get("connection_label") or DEFAULT_COMPANION["connection_label"]).strip()
    companion["variable_name"] = str(companion.get("variable_name") or "").strip()
    companion["on_air_source_variable_name"] = str(companion.get("on_air_source_variable_name") or "").strip()
    companion["next_source_variable_name"] = str(companion.get("next_source_variable_name") or "").strip()
    companion["status_sign_variable_name"] = str(companion.get("status_sign_variable_name") or "").strip()
    return companion


def _normalize_anchor_photos(raw_anchor_photos: dict | None) -> dict:
    anchor_photos = {**DEFAULT_ANCHOR_PHOTOS, **(raw_anchor_photos or {})}
    anchor_photos["enabled"] = bool(anchor_photos.get("enabled"))
    anchor_photos["base_url"] = str(anchor_photos.get("base_url") or "").strip().rstrip("/")
    anchor_photos["share_path"] = str(anchor_photos.get("share_path") or "").strip()
    anchor_photos["username"] = str(anchor_photos.get("username") or "").strip()
    anchor_photos["password"] = str(anchor_photos.get("password") or "")
    anchor_photos["domain"] = str(anchor_photos.get("domain") or "").strip()
    anchor_photos["timeout_seconds"] = int(anchor_photos.get("timeout_seconds") or 4)
    return anchor_photos


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"assignments": {}}, indent=2), encoding="utf-8")
        self._state = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"assignments": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def get_assignment(self, mic_id: str) -> str:
        return str(self._state.get("assignments", {}).get(mic_id, "") or "")

    def set_assignment(self, mic_id: str, assigned_to: str) -> None:
        assignments = self._state.setdefault("assignments", {})
        if assigned_to.strip():
            assignments[mic_id] = assigned_to.strip()
        else:
            assignments.pop(mic_id, None)
        self._save()

    def get_name_override(self, mic_id: str) -> str:
        return str(self._state.get("name_overrides", {}).get(mic_id, "") or "")

    def set_name_override(self, mic_id: str, name: str) -> None:
        overrides = self._state.setdefault("name_overrides", {})
        if name.strip():
            overrides[mic_id] = name.strip()
        else:
            overrides.pop(mic_id, None)
        self._save()


class MappingStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(DEFAULT_MAPPING)

    def load(self) -> dict:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = deepcopy(DEFAULT_MAPPING)
        return self._normalize(raw)

    def save(self, mapping: dict) -> dict:
        normalized = self._normalize(mapping)
        self.path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
        return normalized

    def _normalize(self, raw: dict) -> dict:
        mapping = deepcopy(DEFAULT_MAPPING)
        mapping["auth"].update(raw.get("auth", {}))
        mapping["default_headers"].update(raw.get("default_headers", {}))
        mapping["micboard"].update(raw.get("micboard", {}))
        mapping["display"] = _normalize_display(raw.get("display"))
        mapping["companion"] = _normalize_companion(raw.get("companion"))
        mapping["anchor_photos"] = _normalize_anchor_photos(raw.get("anchor_photos"))
        mapping["default_connection"].update(raw.get("default_connection", {}))

        if "mics" in raw:
            mapping["mics"] = [
                _normalize_mic_entry(item, mapping["default_connection"])
                for item in raw.get("mics", [])
            ]
        else:
            mapping["mics"] = [
                _normalize_mic_entry(item, mapping["default_connection"])
                for item in mapping["mics"]
            ]
        return mapping
