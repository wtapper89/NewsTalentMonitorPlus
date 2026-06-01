from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path


def candidate_paths() -> list[Path]:
    env_path = os.getenv("ANCHOR_MICS_NDI_LIBRARY", "").strip()
    system = platform.system().lower()
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))
    if system == "windows":
        candidates.extend(
            [
                Path(r"C:\Program Files\NDI\NDI 6 Runtime\v6\Processing.NDI.Lib.x64.dll"),
                Path(r"C:\Program Files\NDI\NDI 5 Runtime\v5\Processing.NDI.Lib.x64.dll"),
                Path(r"C:\Program Files\NDI\NDI 5 Tools\Runtime\Processing.NDI.Lib.x64.dll"),
            ]
        )
    elif system == "darwin":
        candidates.extend(
            [
                Path("/usr/local/lib/libndi.dylib"),
                Path("/Library/NDI SDK for Apple/lib/macOS/libndi.dylib"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/local/lib/libndi.so"),
                Path("/usr/lib/libndi.so"),
                Path("/usr/lib/aarch64-linux-gnu/libndi.so"),
                Path("/usr/lib/arm-linux-gnueabihf/libndi.so"),
            ]
        )
    return candidates


def main() -> int:
    for path in candidate_paths():
        if not path.exists():
            continue
        try:
            ctypes.CDLL(str(path))
        except OSError as exc:
            print(f"FOUND_BUT_COULD_NOT_LOAD={path}")
            print(f"ERROR={exc}")
            return 2
        print(f"FOUND={path}")
        return 0

    print("MISSING")
    print("Download/install the NDI runtime or SDK from:")
    print("https://ndi.video/for-developers/ndi-sdk/download/")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
