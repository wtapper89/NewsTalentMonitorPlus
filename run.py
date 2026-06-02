from __future__ import annotations

import os
import sys
import threading

from app.config import load_config


if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def run_server() -> int:
    import uvicorn

    config = load_config()
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        timeout_graceful_shutdown=2,
    )
    return 0


def run_tray() -> int:
    from app.windows_tray import WindowsTrayApp

    config = load_config()
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    WindowsTrayApp(config.host, config.port).run()
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--ndi-worker":
        from app.services.ndi_worker import main as worker_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        return worker_main()

    if len(sys.argv) > 1 and sys.argv[1] == "--check-ndi":
        from tools.ndi.check_ndi_runtime import main as check_ndi_main

        return check_ndi_main()

    if len(sys.argv) > 1 and sys.argv[1] == "--tray":
        return run_tray()

    return run_server()


if __name__ == "__main__":
    raise SystemExit(main())
