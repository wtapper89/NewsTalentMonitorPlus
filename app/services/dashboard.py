from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.models import MicSnapshot
from app.services.photos import AnchorPhotoResolver
from app.store import DEFAULT_ANCHOR_PHOTOS, DEFAULT_COMPANION, DEFAULT_DISPLAY, MappingStore
from app.store import StateStore


TELEMETRY_HISTORY_WINDOW_SECONDS = 60.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DashboardService:
    def __init__(
        self,
        adapter,
        store: StateStore,
        source: str,
        refresh_interval_seconds: int,
        mapping_store: MappingStore | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.source = source
        self.refresh_interval_seconds = refresh_interval_seconds
        self.mapping_store = mapping_store
        self._lock = asyncio.Lock()
        self._telemetry_history: dict[str, dict[str, deque[tuple[float, int]]]] = {}
        self._client = client
        self._owns_client = client is None
        self._photo_resolver = AnchorPhotoResolver()
        self._display_context = self._default_display_context()
        self._state = self._build_state([], "starting", "Connecting to source")

    async def close(self) -> None:
        await self.adapter.close()
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def get_state(self) -> dict:
        if not self._state["mics"] and self._state["connection_status"] == "starting":
            await self.refresh()
        return deepcopy(self._state)

    async def refresh(self) -> dict:
        async with self._lock:
            try:
                mics = await self.adapter.refresh()
                mapping = self.mapping_store.load() if self.mapping_store is not None else {}
                companion = {**DEFAULT_COMPANION, **(mapping.get("companion") or {})}
                mic_configs = {str(mic.get("id") or ""): mic for mic in mapping.get("mics", [])}
                for mic in mics:
                    mic.assigned_to = self.store.get_assignment(mic.id)
                    try:
                        companion_assignment = await self._resolve_companion_assignment(
                            companion,
                            str((mic_configs.get(mic.id) or {}).get("assignment_variable_name") or ""),
                        )
                        if companion_assignment:
                            mic.assigned_to = companion_assignment
                    except Exception as exc:
                        mic.errors.append(f"Companion assignment unavailable: {exc}")
                    if self.source == "micboard":
                        override_name = self.store.get_name_override(mic.id)
                        if override_name:
                            mic.shure_name = override_name
                self._display_context = await self._resolve_display_context()
                self._record_history(mics)
                self._state = self._build_state(mics, "ok", "Live data connected")
            except Exception as exc:
                if self._state["mics"]:
                    self._state["connection_status"] = "warning"
                    self._state["connection_message"] = f"Using cached data: {exc}"
                    self._state["last_refresh"] = utc_now_iso()
                else:
                    self._state = self._build_state([], "error", str(exc))
            return deepcopy(self._state)

    async def rename_mic(self, mic_id: str, new_name: str) -> dict:
        if self.source == "micboard":
            self.store.set_name_override(mic_id, new_name)
            return await self.refresh()
        await self.adapter.rename_mic(mic_id, new_name)
        return await self.refresh()

    async def update_assignment(self, mic_id: str, assigned_to: str) -> dict:
        self.store.set_assignment(mic_id, assigned_to)
        return await self.refresh()

    async def companion_state(self) -> dict:
        state = await self.get_state()
        variables = self._build_companion_variables(state)
        return {
            "updated_at": state["last_refresh"],
            "connection_status": state["connection_status"],
            "summary": state["summary"],
            "mic_count": len(state["mics"]),
            "display": state["display"],
            "mics": [
                {
                    "index": index,
                    "id": mic["id"],
                    "name": mic["display_name"],
                    "assignee": mic["assigned_to"],
                    "battery_percent": mic["battery_percent"],
                    "signal_strength": mic["signal_strength"],
                    "audio_level": mic["audio_level"],
                    "is_online": mic["is_online"],
                    "errors": mic["errors"],
                    "health": mic["health"],
                }
                for index, mic in enumerate(state["mics"], start=1)
            ],
            "variables": variables,
        }

    def _build_state(self, mics: list[MicSnapshot], connection_status: str, connection_message: str) -> dict:
        photo_config = DEFAULT_ANCHOR_PHOTOS
        if self.mapping_store is not None:
            mapping = self.mapping_store.load()
            photo_config = {**DEFAULT_ANCHOR_PHOTOS, **(mapping.get("anchor_photos") or {})}

        mic_payload = []
        for mic in mics:
            payload = mic.to_dict()
            payload["history"] = self._history_payload_for(mic.id)
            payload["anchor_photo_url"] = self._photo_resolver.photo_url_for(mic.assigned_to, photo_config)
            payload["anchor_photo_urls"] = self._photo_resolver.photo_urls_for(mic.assigned_to, photo_config)
            mic_payload.append(payload)
        summary = {
            "total": len(mic_payload),
            "assigned": sum(1 for mic in mic_payload if mic["assigned_to"]),
            "offline": sum(1 for mic in mic_payload if not mic["is_online"]),
            "low_battery": sum(1 for mic in mic_payload if mic["battery_percent"] <= 25),
            "with_errors": sum(1 for mic in mic_payload if mic["errors"]),
        }
        alerts = []
        for mic in mic_payload:
            if mic["errors"]:
                alerts.append(
                    {
                        "id": mic["id"],
                        "title": mic["display_name"],
                        "detail": ", ".join(mic["errors"]),
                    }
                )

        return {
            "source": self.source,
            "connection_status": connection_status,
            "connection_message": connection_message,
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "telemetry_window_seconds": int(TELEMETRY_HISTORY_WINDOW_SECONDS),
            "last_refresh": utc_now_iso(),
            "display": deepcopy(self._display_context),
            "summary": summary,
            "alerts": alerts[:8],
            "mics": mic_payload,
        }

    def _build_companion_variables(self, state: dict) -> dict[str, str]:
        variables = {
            "summary_total": str(state["summary"]["total"]),
            "summary_assigned": str(state["summary"]["assigned"]),
            "summary_offline": str(state["summary"]["offline"]),
            "summary_low_battery": str(state["summary"]["low_battery"]),
            "summary_with_errors": str(state["summary"]["with_errors"]),
            "summary_updated_at": state["last_refresh"],
            "summary_connection_status": state["connection_status"],
        }
        for index, mic in enumerate(state["mics"], start=1):
            prefix = f"mic_{index}"
            variables[f"{prefix}_id"] = mic["id"]
            variables[f"{prefix}_name"] = mic["display_name"]
            variables[f"{prefix}_assignee"] = mic["assigned_to"]
            variables[f"{prefix}_battery"] = str(mic["battery_percent"])
            variables[f"{prefix}_signal"] = str(mic["signal_strength"])
            variables[f"{prefix}_audio"] = str(mic["audio_level"])
            variables[f"{prefix}_status"] = mic["health"]
            variables[f"{prefix}_errors"] = ", ".join(mic["errors"])
            variables[f"{prefix}_receiver"] = mic["receiver_name"]
            variables[f"{prefix}_channel"] = mic["channel_label"]
        return variables

    def _record_history(self, mics: list[MicSnapshot], captured_at: float | None = None) -> None:
        captured_at = captured_at or time.time()
        cutoff = captured_at - TELEMETRY_HISTORY_WINDOW_SECONDS
        active_ids = {mic.id for mic in mics}

        for stale_id in list(self._telemetry_history):
            if stale_id not in active_ids:
                self._telemetry_history.pop(stale_id, None)

        for mic in mics:
            history = self._telemetry_history.setdefault(
                mic.id,
                {
                    "signal_strength": deque(),
                    "audio_level": deque(),
                },
            )
            history["signal_strength"].append((captured_at, int(mic.signal_strength)))
            history["audio_level"].append((captured_at, int(mic.audio_level)))
            self._trim_series(history["signal_strength"], cutoff)
            self._trim_series(history["audio_level"], cutoff)

    def _history_payload_for(self, mic_id: str) -> dict:
        history = self._telemetry_history.get(mic_id)
        if not history:
            return {
                "window_seconds": int(TELEMETRY_HISTORY_WINDOW_SECONDS),
                "signal_strength": [],
                "audio_level": [],
            }
        return {
            "window_seconds": int(TELEMETRY_HISTORY_WINDOW_SECONDS),
            "signal_strength": self._serialize_series(history["signal_strength"]),
            "audio_level": self._serialize_series(history["audio_level"]),
        }

    @staticmethod
    def _trim_series(series: deque[tuple[float, int]], cutoff: float) -> None:
        while series and series[0][0] < cutoff:
            series.popleft()

    @staticmethod
    def _serialize_series(series: deque[tuple[float, int]]) -> list[dict[str, int]]:
        return [
            {
                "timestamp_ms": int(timestamp * 1000),
                "value": value,
            }
            for timestamp, value in series
        ]

    def _default_display_context(self) -> dict:
        return {
            "show_title": DEFAULT_DISPLAY["manual_show_title"],
            "show_title_source": "manual",
            "show_title_error": "",
            "show_title_mode": DEFAULT_DISPLAY["show_title_mode"],
            "manual_show_title": DEFAULT_DISPLAY["manual_show_title"],
            "preview_mode": DEFAULT_DISPLAY["preview_mode"],
            "preview_url": DEFAULT_DISPLAY["preview_url"],
            "preview_source_name": DEFAULT_DISPLAY["preview_source_name"],
            "preview_poster_url": DEFAULT_DISPLAY["preview_poster_url"],
            "font_family": DEFAULT_DISPLAY["font_family"],
            "companion_enabled": DEFAULT_COMPANION["enabled"],
            "companion_base_url": DEFAULT_COMPANION["base_url"],
            "companion_connection_label": DEFAULT_COMPANION["connection_label"],
            "companion_variable_name": DEFAULT_COMPANION["variable_name"],
            "on_air_source_name": "",
            "on_air_source_variable_name": DEFAULT_COMPANION["on_air_source_variable_name"],
            "anchor_photos_enabled": DEFAULT_ANCHOR_PHOTOS["enabled"],
            "anchor_photos_base_url": DEFAULT_ANCHOR_PHOTOS["base_url"],
            "anchor_photos_share_path": DEFAULT_ANCHOR_PHOTOS["share_path"],
        }

    async def _resolve_display_context(self) -> dict:
        if self.mapping_store is None:
            return deepcopy(self._display_context)

        mapping = self.mapping_store.load()
        display = {**DEFAULT_DISPLAY, **(mapping.get("display") or {})}
        companion = {**DEFAULT_COMPANION, **(mapping.get("companion") or {})}

        manual_title = str(display.get("manual_show_title") or DEFAULT_DISPLAY["manual_show_title"]).strip()
        show_title = manual_title
        show_title_source = "manual"
        show_title_error = ""
        on_air_source_name = ""
        on_air_source_error = ""

        if (
            str(display.get("show_title_mode") or "manual").lower() == "companion"
            and companion.get("enabled")
            and str(companion.get("base_url") or "").strip()
            and str(companion.get("connection_label") or "").strip()
            and str(companion.get("variable_name") or "").strip()
        ):
            try:
                title_connection_label, title_variable_name = self._companion_lookup_parts(
                    companion,
                    str(companion["variable_name"]),
                )
                show_title = await self._fetch_companion_variable(
                    str(companion["base_url"]),
                    title_connection_label,
                    title_variable_name,
                )
                if show_title:
                    show_title_source = "companion"
                else:
                    show_title = manual_title
                    show_title_error = "Companion variable is empty"
            except Exception as exc:
                show_title = str(self._display_context.get("show_title") or manual_title)
                show_title_source = str(self._display_context.get("show_title_source") or "manual")
                show_title_error = str(exc)

        if (
            companion.get("enabled")
            and str(companion.get("base_url") or "").strip()
            and str(companion.get("connection_label") or "").strip()
            and str(companion.get("on_air_source_variable_name") or "").strip()
        ):
            try:
                on_air_connection_label, on_air_variable_name = self._companion_lookup_parts(
                    companion,
                    str(companion["on_air_source_variable_name"]),
                )
                on_air_source_name = await self._fetch_companion_variable(
                    str(companion["base_url"]),
                    on_air_connection_label,
                    on_air_variable_name,
                )
            except Exception as exc:
                on_air_source_name = str(self._display_context.get("on_air_source_name") or "")
                on_air_source_error = str(exc)

        return {
            "show_title": show_title or manual_title,
            "show_title_source": show_title_source,
            "show_title_error": show_title_error,
            "show_title_mode": str(display.get("show_title_mode") or "manual"),
            "manual_show_title": manual_title,
            "preview_mode": str(display.get("preview_mode") or "placeholder"),
            "preview_url": str(display.get("preview_url") or ""),
            "preview_source_name": str(display.get("preview_source_name") or ""),
            "preview_poster_url": str(display.get("preview_poster_url") or ""),
            "font_family": str(display.get("font_family") or DEFAULT_DISPLAY["font_family"]),
            "companion_enabled": bool(companion.get("enabled")),
            "companion_base_url": str(companion.get("base_url") or DEFAULT_COMPANION["base_url"]),
            "companion_connection_label": str(companion.get("connection_label") or DEFAULT_COMPANION["connection_label"]),
            "companion_variable_name": str(companion.get("variable_name") or ""),
            "on_air_source_name": on_air_source_name,
            "on_air_source_error": on_air_source_error,
            "on_air_source_variable_name": str(companion.get("on_air_source_variable_name") or ""),
            "anchor_photos_enabled": bool((mapping.get("anchor_photos") or {}).get("enabled")),
            "anchor_photos_base_url": str((mapping.get("anchor_photos") or {}).get("base_url") or ""),
            "anchor_photos_share_path": str((mapping.get("anchor_photos") or {}).get("share_path") or ""),
        }

    async def _resolve_companion_assignment(self, companion: dict, variable_name: str) -> str:
        if (
            not companion.get("enabled")
            or not str(companion.get("base_url") or "").strip()
            or not str(companion.get("connection_label") or "").strip()
            or not variable_name.strip()
        ):
            return ""
        connection_label, resolved_variable_name = self._companion_lookup_parts(companion, variable_name)
        return await self._fetch_companion_variable(
            str(companion["base_url"]),
            connection_label,
            resolved_variable_name,
        )

    @staticmethod
    def _companion_lookup_parts(companion: dict, variable_name: str) -> tuple[str, str]:
        raw_variable = variable_name.strip()
        wrapped = re.fullmatch(r"\$\(([^:()]+):([^()]+)\)", raw_variable)
        if wrapped:
            return wrapped.group(1).strip(), wrapped.group(2).strip()
        prefixed = re.fullmatch(r"([^:()]+):(.+)", raw_variable)
        if prefixed:
            return prefixed.group(1).strip(), prefixed.group(2).strip()
        return str(companion.get("connection_label") or "").strip(), raw_variable

    async def _fetch_companion_variable(self, base_url: str, connection_label: str, variable_name: str) -> str:
        url = (
            f"{base_url.rstrip('/')}/api/variable/"
            f"{quote(connection_label, safe='')}/{quote(variable_name, safe='')}/value"
        )
        response = await self._http_client().get(url)
        response.raise_for_status()

        raw_text = response.text.strip()
        if not raw_text:
            return ""

        try:
            parsed = response.json()
        except json.JSONDecodeError:
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                parsed = raw_text

        if parsed is None:
            return ""
        if isinstance(parsed, (dict, list)):
            return json.dumps(parsed)
        return str(parsed).strip()

    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=2.0)
        return self._client
