from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import quote


PHOTO_EXTENSIONS = (".png", ".jpg", ".jpeg")


def normalized_anchor_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", name or "")


def parse_unc_path(path: str) -> tuple[str, str]:
    cleaned = str(path or "").strip().replace("/", "\\")
    if cleaned.startswith("\\\\"):
        cleaned = cleaned[2:]
    parts = [part for part in cleaned.split("\\") if part]
    if len(parts) < 2:
        return "", ""
    service = f"//{parts[0]}/{parts[1]}"
    remote_dir = "/".join(parts[2:])
    return service, remote_dir


class AnchorPhotoResolver:
    def __init__(self, cache_dir: Path | str = "/tmp/anchor-mics-anchor-photos") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._seen: dict[str, tuple[float, Path | None]] = {}

    def photo_url_for(self, name: str, config: dict) -> str:
        if not self._enabled(config) or not str(name or "").strip():
            return ""
        path = self.photo_path_for(name, config)
        if not path:
            return ""
        return f"/api/anchor-photos/{quote(name, safe='')}"

    def photo_path_for(self, name: str, config: dict) -> Path | None:
        if not self._enabled(config):
            return None

        key = self._cache_key(name, config)
        now = time.time()
        cached = self._seen.get(key)
        if cached and cached[0] > now:
            return cached[1]

        path = self._fetch_photo(name, config)
        ttl = 300.0 if path else 30.0
        self._seen[key] = (now + ttl, path)
        return path

    def _fetch_photo(self, name: str, config: dict) -> Path | None:
        stem = normalized_anchor_filename(name)
        if not stem:
            return None

        service, remote_dir = parse_unc_path(str(config.get("share_path") or ""))
        if not service:
            return None

        username = str(config.get("username") or "")
        password = str(config.get("password") or "")
        domain = str(config.get("domain") or "")
        timeout_seconds = float(config.get("timeout_seconds") or 4.0)

        for extension in PHOTO_EXTENSIONS:
            remote_name = f"{stem}{extension}"
            remote_path = "/".join(part for part in (remote_dir, remote_name) if part)
            local_path = self.cache_dir / f"{hashlib.sha1((service + remote_path).encode('utf-8')).hexdigest()}{extension}"
            if self._smb_get(service, remote_path, local_path, username, password, domain, timeout_seconds):
                return local_path
        return None

    def _smb_get(
        self,
        service: str,
        remote_path: str,
        local_path: Path,
        username: str,
        password: str,
        domain: str,
        timeout_seconds: float,
    ) -> bool:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as credentials:
            credentials.write(f"username = {username}\n")
            credentials.write(f"password = {password}\n")
            if domain:
                credentials.write(f"domain = {domain}\n")
            credentials_path = credentials.name

        temp_path = local_path.with_suffix(local_path.suffix + ".tmp")
        try:
            command = [
                "smbclient",
                service,
                "-A",
                credentials_path,
                "-m",
                "SMB3",
                "-c",
                f'get "{remote_path}" "{temp_path}"',
            ]
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout_seconds,
                check=False,
            )
            if result.returncode != 0 or not temp_path.exists():
                return False
            os.replace(temp_path, local_path)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
        finally:
            try:
                Path(credentials_path).unlink()
            except FileNotFoundError:
                pass
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

    def _cache_key(self, name: str, config: dict) -> str:
        identity = "|".join(
            [
                normalized_anchor_filename(name).lower(),
                str(config.get("share_path") or ""),
                str(config.get("username") or ""),
                str(config.get("domain") or ""),
            ]
        )
        return hashlib.sha1(identity.encode("utf-8")).hexdigest()

    @staticmethod
    def _enabled(config: dict) -> bool:
        return bool(config.get("enabled")) and bool(str(config.get("share_path") or "").strip())
