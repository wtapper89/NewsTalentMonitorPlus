from __future__ import annotations

import logging
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any


class RecentLogHandler(logging.Handler):
    def __init__(self, capacity: int = 400) -> None:
        super().__init__()
        self.capacity = capacity
        self._records: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": self.formatter.formatTime(record, self.formatter.datefmt) if self.formatter else "",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        with self._lock:
            self._records.append(entry)

    def snapshot(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._records)[-limit:]


_recent_handler = RecentLogHandler()
_configured = False


def configure_logging(level_name: str, log_file: Path) -> None:
    global _configured

    logger = logging.getLogger("anchor_mics")
    level = getattr(logging, str(level_name or "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    if _configured:
        for handler in logger.handlers:
            handler.setLevel(level)
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    _recent_handler.setLevel(level)
    _recent_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.addHandler(_recent_handler)
    _configured = True


def recent_logs(limit: int = 200) -> list[dict[str, Any]]:
    return _recent_handler.snapshot(limit)
