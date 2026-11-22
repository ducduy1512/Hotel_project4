"""Launch the Hotel HTML5 interface and FastAPI backend from PyCharm."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

PROJECT_DIR = Path(__file__).resolve().parent


def main() -> None:
    # Make imports and relative .env/static paths independent of PyCharm's
    # configured working directory.
    os.chdir(PROJECT_DIR)
    project_path = str(PROJECT_DIR)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    host = os.getenv("HOTEL_HOST", "127.0.0.1")
    port = int(os.getenv("HOTEL_PORT", "8000"))

    print("=" * 60)
    print("HOTEL MANAGEMENT SYSTEM")
    print("=" * 60)
    print("PROJECT:", PROJECT_DIR)
    print("PYTHON:", sys.executable)
    print("API:", PROJECT_DIR / "api" / "main.py")
    print("FRONTEND:", PROJECT_DIR / "frontend")
    print("=" * 60)
    print(f"Starting Hotel Server at http://{host}:{port}/")

    # PROJECT_DIR is already in sys.path and is the current working directory.
    config = uvicorn.Config(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=True,
    )
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
