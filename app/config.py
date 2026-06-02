from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


if getattr(sys, "frozen", False):
    ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    reload: bool
    source: str
    refresh_interval_seconds: float
    data_file: Path
    mapping_file: Path
    log_level: str
    log_file: Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    source = os.getenv("ANCHOR_MICS_SOURCE", "qlxd").strip().lower() or "qlxd"
    if source == "micboard":
        source = "qlxd"
    host = os.getenv("ANCHOR_MICS_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("ANCHOR_MICS_PORT", "8010"))
    reload = _as_bool(os.getenv("ANCHOR_MICS_RELOAD"), default=False)
    refresh_interval_seconds = float(os.getenv("ANCHOR_MICS_REFRESH_SECONDS", "0.5"))
    data_file = Path(os.getenv("ANCHOR_MICS_DATA_FILE", ROOT_DIR / "data" / "state.json")).expanduser()
    mapping_file = Path(
        os.getenv(
            "ANCHOR_MICS_MAPPING_FILE",
            ROOT_DIR / "config" / "system_api_mapping.example.json",
        )
    ).expanduser()
    log_level = os.getenv("ANCHOR_MICS_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    log_file = Path(os.getenv("ANCHOR_MICS_LOG_FILE", ROOT_DIR / "data" / "anchor-mics.log")).expanduser()
    return AppConfig(
        host=host,
        port=port,
        reload=reload,
        source=source,
        refresh_interval_seconds=refresh_interval_seconds,
        data_file=data_file,
        mapping_file=mapping_file,
        log_level=log_level,
        log_file=log_file,
    )
