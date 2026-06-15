from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlretrieve


DEFAULT_REPO_URL = "https://github.com/wtapper89/NewsTalentMonitorPlus.git"
DEFAULT_TARBALL_URL = "https://github.com/wtapper89/NewsTalentMonitorPlus/archive/refs/heads/main.tar.gz"


class AppUpdater:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.status_file = root_dir / "data" / "update-status.json"
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._restart_task: asyncio.Task[None] | None = None

    def status(self) -> dict:
        if self.status_file.exists():
            try:
                return json.loads(self.status_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "state": "idle",
            "message": "No update has been run yet.",
            "details": [],
            "restart_required": False,
        }

    async def start(self) -> dict:
        async with self._lock:
            if self._task and not self._task.done():
                return self.status()
            self._write_status(
                {
                    "state": "running",
                    "message": "Updating News Talent Monitor+ from GitHub...",
                    "started_at": self._timestamp(),
                    "details": [],
                    "restart_required": False,
                }
            )
            self._task = asyncio.create_task(self._run())
            return self.status()

    async def _run(self) -> None:
        details: list[str] = []
        try:
            method = await self._update_source(details)
            await self._install_dependencies(details)
            self._write_status(
                {
                    "state": "success",
                    "message": "Update complete. The service is restarting now.",
                    "method": method,
                    "started_at": self.status().get("started_at"),
                    "finished_at": self._timestamp(),
                    "details": details,
                    "restart_required": True,
                }
            )
            self._schedule_restart()
        except Exception as exc:
            details.append(str(exc))
            self._write_status(
                {
                    "state": "error",
                    "message": "Update failed.",
                    "started_at": self.status().get("started_at"),
                    "finished_at": self._timestamp(),
                    "details": details,
                    "restart_required": False,
                }
            )

    async def _update_source(self, details: list[str]) -> str:
        if (self.root_dir / ".git").exists() and shutil.which("git"):
            details.append("Using existing git checkout.")
            await self._run_command(["git", "pull", "--ff-only"], details, cwd=self.root_dir)
            return "git"

        details.append("No git checkout found; downloading the latest GitHub archive.")
        await asyncio.to_thread(self._download_and_sync_archive, details)
        return "github-archive"

    async def _install_dependencies(self, details: list[str]) -> None:
        requirements = self.root_dir / "requirements.txt"
        if not requirements.exists():
            details.append("No requirements.txt found; skipped Python dependency install.")
            return
        python = self._venv_python()
        details.append("Installing Python dependencies.")
        await self._run_command(
            [str(python), "-m", "pip", "install", "-r", str(requirements)],
            details,
            cwd=self.root_dir,
        )

    def _download_and_sync_archive(self, details: list[str]) -> None:
        tarball_url = os.getenv("NEWS_TALENT_MONITOR_TARBALL_URL", DEFAULT_TARBALL_URL)
        with tempfile.TemporaryDirectory(prefix="news-talent-monitor-update-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            archive_path = temp_dir / "source.tar.gz"
            source_dir = temp_dir / "source"
            urlretrieve(tarball_url, archive_path)
            source_dir.mkdir()
            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(source_dir)
            extracted_roots = [path for path in source_dir.iterdir() if path.is_dir()]
            if not extracted_roots:
                raise RuntimeError("Downloaded archive did not include a source folder.")
            self._sync_tree(extracted_roots[0], self.root_dir)
        details.append("Copied latest application files from GitHub archive.")

    def _sync_tree(self, source_dir: Path, destination_dir: Path) -> None:
        skip_names = {".git", ".venv", ".pi-image-build", "__pycache__", "data", "config"}
        for source_item in source_dir.iterdir():
            if source_item.name in skip_names:
                continue
            destination_item = destination_dir / source_item.name
            if source_item.is_dir():
                shutil.copytree(
                    source_item,
                    destination_item,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
                )
            else:
                shutil.copy2(source_item, destination_item)

    async def _run_command(self, command: list[str], details: list[str], cwd: Path) -> None:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if output:
            details.extend(line for line in output.splitlines()[-20:] if line.strip())
        if process.returncode:
            raise RuntimeError(f"{command[0]} exited with status {process.returncode}")

    def _schedule_restart(self) -> None:
        if os.getenv("NEWS_TALENT_MONITOR_RESTART_AFTER_UPDATE", "1").strip().lower() in {"0", "false", "no", "off"}:
            return
        if self._restart_task and not self._restart_task.done():
            return
        self._restart_task = asyncio.create_task(self._restart_after_response())

    async def _restart_after_response(self) -> None:
        await asyncio.sleep(3)
        os._exit(0)

    def _venv_python(self) -> Path:
        candidates = [
            self.root_dir / ".venv" / "bin" / "python",
            self.root_dir / ".venv" / "Scripts" / "python.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return Path(sys.executable)

    def _write_status(self, payload: dict) -> None:
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
