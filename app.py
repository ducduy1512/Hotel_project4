"""Launch the Hotel HTML5 interface and its existing FastAPI backend."""
from __future__ import annotations

import os
from pathlib import Path
import threading
import time
import webbrowser

import uvicorn


def open_browser() -> None:
    time.sleep(1.2)
    webbrowser.open(os.getenv("HOTEL_APP_URL", "http://127.0.0.1:8000/"))


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    host = os.getenv("HOTEL_HOST", "127.0.0.1")
    port = int(os.getenv("HOTEL_PORT", "8000"))
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("api.main:app", host=host, port=port, reload=False)
