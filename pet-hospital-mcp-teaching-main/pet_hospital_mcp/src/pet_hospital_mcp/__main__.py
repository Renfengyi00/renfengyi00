from __future__ import annotations

import uvicorn

from pet_hospital_mcp.config import load_settings
from pet_hospital_mcp.logging_config import configure_logging
from pet_hospital_mcp.server import create_app


def main() -> None:
    configure_logging()
    settings = load_settings()
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
