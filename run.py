from __future__ import annotations

import sys

from app.config import load_config


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--ndi-worker":
        from app.services.ndi_worker import main as worker_main

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        return worker_main()

    if len(sys.argv) > 1 and sys.argv[1] == "--check-ndi":
        from tools.ndi.check_ndi_runtime import main as check_ndi_main

        return check_ndi_main()

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


if __name__ == "__main__":
    raise SystemExit(main())
