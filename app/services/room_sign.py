from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import httpx

from app.store import DEFAULT_ROOM_SIGN, MappingStore


@dataclass(frozen=True)
class RoomEvent:
    title: str
    starts_at: datetime
    ends_at: datetime
    location: str = ""
    event_id: str = ""
    room_id: str = ""

    def to_dict(self, tz: ZoneInfo) -> dict[str, str]:
        starts_at = self.starts_at.astimezone(tz)
        ends_at = self.ends_at.astimezone(tz)
        start_time = starts_at.strftime("%I:%M %p").lstrip("0")
        end_time = ends_at.strftime("%I:%M %p").lstrip("0")
        return {
            "title": self.title,
            "location": self.location,
            "event_id": self.event_id,
            "room_id": self.room_id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "date_label": f"{starts_at.strftime('%A, %B')} {starts_at.day}",
            "time_label": f"{start_time} - {end_time}",
        }


class RoomSignService:
    def __init__(
        self,
        mapping_store: MappingStore,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.mapping_store = mapping_store
        self._client = client
        self._owns_client = client is None
        self._cache_key = ""
        self._cache_until = 0.0
        self._cached_events: list[RoomEvent] = []
        self._cached_error = ""

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def state(self, status_display: dict[str, Any]) -> dict[str, Any]:
        config = self._config()
        tz = self._timezone(config)
        now = datetime.now(tz)
        events, schedule_error = await self._events(config, now, tz)
        current_event = self._current_event(events, now)
        upcoming_events = self._upcoming_events(events, now, int(config["max_events"]))

        status_text = str(status_display.get("status_sign_text") or "").strip()
        status_mode = str(status_display.get("status_sign_mode") or "empty").strip() or "empty"
        is_status_active = bool(status_text) and status_mode != "empty"

        return {
            "enabled": bool(config["enabled"]),
            "room_name": str(config["room_name"]),
            "room_id": str(config["room_id"]),
            "timezone": str(config["timezone"]),
            "is_status_active": is_status_active,
            "status_text": status_text,
            "status_mode": status_mode,
            "status_error": str(status_display.get("status_sign_error") or ""),
            "current_event": current_event.to_dict(tz) if current_event else None,
            "upcoming_events": [event.to_dict(tz) for event in upcoming_events],
            "schedule_error": schedule_error,
            "last_refresh": datetime.now(tz).isoformat(),
        }

    def _config(self) -> dict:
        mapping = self.mapping_store.load()
        return {**DEFAULT_ROOM_SIGN, **(mapping.get("room_sign") or {})}

    @staticmethod
    def _timezone(config: dict) -> ZoneInfo:
        try:
            return ZoneInfo(str(config.get("timezone") or DEFAULT_ROOM_SIGN["timezone"]))
        except Exception:
            return ZoneInfo(DEFAULT_ROOM_SIGN["timezone"])

    async def _events(self, config: dict, now: datetime, tz: ZoneInfo) -> tuple[list[RoomEvent], str]:
        if not config.get("enabled"):
            return [], ""

        url = self._feed_url(config, now)
        if not url:
            return [], "Room sign schedule is enabled, but no 25Live feed URL or calendar web name is configured."

        cache_key = json.dumps(
            {
                "url": url,
                "room_id": config.get("room_id"),
                "room_name": config.get("room_name"),
                "tz": str(tz),
            },
            sort_keys=True,
        )
        now_monotonic = time.monotonic()
        if cache_key == self._cache_key and now_monotonic < self._cache_until:
            return list(self._cached_events), self._cached_error

        try:
            response = await self._http_client().get(url)
            response.raise_for_status()
            events = self._parse_events(
                response.text,
                response.headers.get("content-type", ""),
                tz,
                str(config.get("room_id") or ""),
                str(config.get("room_name") or ""),
            )
            error = ""
        except Exception as exc:
            events = list(self._cached_events)
            error = f"Using cached schedule: {exc}" if events else str(exc)

        self._cache_key = cache_key
        self._cache_until = now_monotonic + int(config.get("refresh_seconds") or 60)
        self._cached_events = list(events)
        self._cached_error = error
        return events, error

    def _feed_url(self, config: dict, now: datetime) -> str:
        feed_url = str(config.get("feed_url") or "").strip()
        calendar_web_name = str(config.get("calendar_web_name") or "").strip()
        if not feed_url and calendar_web_name:
            feed_url = f"https://25livepub.collegenet.com/calendars/{calendar_web_name}.json"
        if not feed_url:
            return ""

        lookahead_days = int(config.get("lookahead_days") or 7)
        startdate = now.strftime("%Y%m%d")
        enddate = (now + timedelta(days=lookahead_days)).strftime("%Y%m%d")
        replacements = {
            "room_id": str(config.get("room_id") or ""),
            "startdate": startdate,
            "enddate": enddate,
            "days": str(lookahead_days),
        }
        for key, value in replacements.items():
            feed_url = feed_url.replace(f"{{{key}}}", value)

        if "{" not in feed_url and "}" not in feed_url:
            parsed = urlsplit(feed_url)
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            if str(config.get("room_id") or "").strip():
                query["space_id"] = str(config.get("room_id") or "").strip()
            if parsed.path.endswith("rm_reservations.xml"):
                query.setdefault("start_dt", "-1")
                query.setdefault("end_dt", f"+{lookahead_days}")
                for key in ("start_dt", "end_dt"):
                    value = str(query.get(key) or "")
                    if value.startswith(" ") and value.strip():
                        query[key] = f"+{value.strip()}"
            else:
                query.setdefault("startdate", startdate)
                query.setdefault("days", str(lookahead_days))
                query.setdefault("previousweeks", "0")
            query.setdefault("html", "0")
            feed_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

        return feed_url

    def _parse_events(self, text: str, content_type: str, tz: ZoneInfo, room_id: str, room_name: str) -> list[RoomEvent]:
        stripped = text.strip()
        if "xml" in content_type or stripped.startswith("<?xml") or "space_reservations" in stripped[:300]:
            events = self._parse_25live_xml(stripped, tz)
        elif "text/calendar" in content_type or stripped.startswith("BEGIN:VCALENDAR"):
            events = self._parse_ics(stripped, tz)
        else:
            events = self._parse_json(stripped, tz)
        filtered = [event for event in events if self._event_matches_room(event, room_id, room_name)]
        return sorted(filtered, key=lambda event: event.starts_at)

    def _parse_json(self, text: str, tz: ZoneInfo) -> list[RoomEvent]:
        payload = json.loads(text)
        raw_events = self._event_items(payload)
        events = []
        for item in raw_events:
            if not isinstance(item, dict):
                continue
            event = self._event_from_mapping(item, tz)
            if event is not None:
                events.append(event)
        return events

    def _event_items(self, payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        for key in ("events", "items", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = self._event_items(value)
                if nested:
                    return nested
        return []

    def _event_from_mapping(self, item: dict, tz: ZoneInfo) -> RoomEvent | None:
        title = self._first_string(item, ("title", "name", "event_name", "eventName", "summary", "description"))
        starts_at = self._parse_datetime(
            self._first_value(
                item,
                (
                    "start",
                    "starts_at",
                    "start_at",
                    "startDateTime",
                    "start_datetime",
                    "dtstart",
                    "eventStart",
                    "event_start",
                    "dateTime",
                ),
            ),
            tz,
        )
        ends_at = self._parse_datetime(
            self._first_value(
                item,
                (
                    "end",
                    "ends_at",
                    "end_at",
                    "endDateTime",
                    "end_datetime",
                    "dtend",
                    "eventEnd",
                    "event_end",
                ),
            ),
            tz,
        )
        if not title or starts_at is None:
            return None
        if ends_at is None or ends_at <= starts_at:
            ends_at = starts_at + timedelta(hours=1)
        return RoomEvent(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            location=self._first_string(item, ("location", "locationName", "spaceName", "room", "space")),
            event_id=self._first_string(item, ("id", "event_id", "eventId", "uid")),
            room_id=self._first_string(item, ("space_id", "spaceId", "room_id", "roomId")),
        )

    def _parse_25live_xml(self, text: str, tz: ZoneInfo) -> list[RoomEvent]:
        root = ET.fromstring(text)
        events: list[RoomEvent] = []
        for reservation in root.iter():
            if self._local_name(reservation.tag) != "space_reservation":
                continue
            event = self._event_from_25live_reservation(reservation, tz)
            if event is not None:
                events.append(event)
        return events

    def _event_from_25live_reservation(self, reservation: ET.Element, tz: ZoneInfo) -> RoomEvent | None:
        event_el = self._child(reservation, "event")
        space_el = self._child(reservation, "spaces")
        if event_el is None:
            return None

        state_name = self._child_text(event_el, "state_name").lower()
        if state_name in {"cancelled", "canceled", "denied"}:
            return None

        title = self._child_text(event_el, "event_title") or self._child_text(event_el, "event_name")
        starts_at = self._parse_datetime(
            self._child_text(reservation, "reservation_start_dt") or self._child_text(event_el, "event_start_dt"),
            tz,
        )
        ends_at = self._parse_datetime(
            self._child_text(reservation, "reservation_end_dt") or self._child_text(event_el, "event_end_dt"),
            tz,
        )
        if not title or starts_at is None:
            return None
        if ends_at is None or ends_at <= starts_at:
            ends_at = starts_at + timedelta(hours=1)

        return RoomEvent(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            location=self._child_text(space_el, "space_name") if space_el is not None else "",
            event_id=self._child_text(event_el, "event_id") or self._child_text(reservation, "reservation_id"),
            room_id=self._child_text(space_el, "space_id") if space_el is not None else "",
        )

    def _parse_ics(self, text: str, tz: ZoneInfo) -> list[RoomEvent]:
        lines = self._unfold_ics_lines(text)
        events: list[RoomEvent] = []
        current: dict[str, str] | None = None
        for raw_line in lines:
            line = raw_line.strip()
            if line == "BEGIN:VEVENT":
                current = {}
                continue
            if line == "END:VEVENT":
                if current is not None:
                    event = self._event_from_ics(current, tz)
                    if event is not None:
                        events.append(event)
                current = None
                continue
            if current is None or ":" not in line:
                continue
            name, value = line.split(":", 1)
            key = name.split(";", 1)[0].upper()
            current[key] = self._unescape_ics(value)
        return events

    @staticmethod
    def _unfold_ics_lines(text: str) -> list[str]:
        lines: list[str] = []
        for raw_line in text.replace("\r\n", "\n").split("\n"):
            if raw_line.startswith((" ", "\t")) and lines:
                lines[-1] += raw_line[1:]
            else:
                lines.append(raw_line)
        return lines

    @staticmethod
    def _unescape_ics(value: str) -> str:
        return (
            value.replace("\\n", " ")
            .replace("\\N", " ")
            .replace("\\,", ",")
            .replace("\\;", ";")
            .replace("\\\\", "\\")
            .strip()
        )

    def _event_from_ics(self, item: dict[str, str], tz: ZoneInfo) -> RoomEvent | None:
        title = str(item.get("SUMMARY") or "").strip()
        starts_at = self._parse_datetime(item.get("DTSTART"), tz)
        ends_at = self._parse_datetime(item.get("DTEND"), tz)
        if not title or starts_at is None:
            return None
        if ends_at is None or ends_at <= starts_at:
            ends_at = starts_at + timedelta(hours=1)
        return RoomEvent(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            location=str(item.get("LOCATION") or "").strip(),
            event_id=str(item.get("UID") or "").strip(),
        )

    @classmethod
    def _child(cls, element: ET.Element | None, local_name: str) -> ET.Element | None:
        if element is None:
            return None
        for child in element:
            if cls._local_name(child.tag) == local_name:
                return child
        return None

    @classmethod
    def _child_text(cls, element: ET.Element | None, local_name: str) -> str:
        child = cls._child(element, local_name)
        if child is None or child.text is None:
            return ""
        return child.text.strip()

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag.split(":", 1)[-1]

    @staticmethod
    def _parse_datetime(value: Any, tz: ZoneInfo) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=tz)
        raw = str(value).strip()
        if not raw:
            return None

        if re.fullmatch(r"\d{8}", raw):
            parsed_date = datetime.strptime(raw, "%Y%m%d").date()
            return datetime.combine(parsed_date, dt_time.min, tzinfo=tz)
        if re.fullmatch(r"\d{8}T\d{6}Z", raw):
            return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        if re.fullmatch(r"\d{8}T\d{6}", raw):
            return datetime.strptime(raw, "%Y%m%dT%H%M%S").replace(tzinfo=tz)

        try:
            if raw.endswith("Z"):
                raw = f"{raw[:-1]}+00:00"
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=tz)
            return parsed.astimezone(tz)
        except ValueError:
            pass

        for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=tz)
            except ValueError:
                continue

        try:
            parsed = parsedate_to_datetime(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=tz)
            return parsed.astimezone(tz)
        except (TypeError, ValueError):
            return None

    def _event_matches_room(self, event: RoomEvent, room_id: str, room_name: str) -> bool:
        room_id = room_id.strip().lower()
        room_name = room_name.strip().lower()
        haystack = " ".join([event.location, event.event_id, event.room_id]).lower()
        if room_id and room_id in haystack:
            return True
        if room_name and room_name in haystack:
            return True
        return not room_id

    @staticmethod
    def _first_value(item: dict, keys: tuple[str, ...]) -> Any:
        for key in keys:
            if key in item and item[key] not in (None, ""):
                return item[key]
        for value in item.values():
            if isinstance(value, dict):
                nested = RoomSignService._first_value(value, keys)
                if nested not in (None, ""):
                    return nested
        return None

    @staticmethod
    def _first_string(item: dict, keys: tuple[str, ...]) -> str:
        value = RoomSignService._first_value(item, keys)
        if isinstance(value, dict):
            return str(value.get("name") or value.get("title") or value.get("summary") or "").strip()
        if isinstance(value, list):
            return ", ".join(str(part) for part in value if part).strip()
        return str(value or "").strip()

    @staticmethod
    def _current_event(events: list[RoomEvent], now: datetime) -> RoomEvent | None:
        for event in events:
            if event.starts_at <= now < event.ends_at:
                return event
        return None

    @staticmethod
    def _upcoming_events(events: list[RoomEvent], now: datetime, limit: int) -> list[RoomEvent]:
        return [event for event in events if event.starts_at > now][:limit]

    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=8.0)
        return self._client
