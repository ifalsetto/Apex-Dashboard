import os
from pathlib import Path

APP_DATA_DIR = Path(os.getenv("APP_DATA_DIR", "/data")).expanduser().resolve()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

EXPORTS_DIR = APP_DATA_DIR / "exports"
LOGS_DIR = APP_DATA_DIR / "logs"
UPLOADS_DIR = APP_DATA_DIR / "uploads"

for directory in (EXPORTS_DIR, LOGS_DIR, UPLOADS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
