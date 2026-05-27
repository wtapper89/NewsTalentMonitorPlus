from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MicSnapshot:
    id: str
    shure_name: str
    receiver_name: str
    channel_label: str
    battery_percent: int
    signal_strength: int
    audio_level: int
    assigned_to: str = ""
    is_online: bool = True
    errors: list[str] = field(default_factory=list)
    last_seen: str = field(default_factory=utc_now_iso)
    source: str = "mock"
    connection_state: str = "ok"

    @property
    def display_name(self) -> str:
        return self.shure_name or self.id

    @property
    def health(self) -> str:
        if not self.is_online:
            return "offline"
        if self.errors or self.battery_percent <= 20 or self.signal_strength <= 25:
            return "warning"
        return "ok"

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["display_name"] = self.display_name
        payload["health"] = self.health
        return payload

