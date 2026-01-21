from __future__ import annotations

import uvicorn

from .config import Settings


def main() -> int:
    settings = Settings()
    uvicorn.run(
        "auth_service.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
