"""Configuration module for Apex Dashboard."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import datetime as dt
import platform
import json


@dataclass
class Config:
    """Centralized application configuration."""

    # App Identity
    APP_TITLE: str = "Apex Optimizer Dashboard"
    APP_VERSION: str = "v0.1.1-beta"
    REPO_URL: str = "https://github.com/ifalsetto/Apex-Dashboard"
    BUG_URL: str = field(default_factory=lambda: f"{Config.REPO_URL}/issues/new?template=bug_report.yml")
    FEATURE_URL: str = field(default_factory=lambda: f"{Config.REPO_URL}/issues/new?template=feature_request.yml")

    # Process names
    APEX_PROCESS_NAMES: list = field(default_factory=lambda: ["r5apex", "r5apex.exe"])

    # Base directory
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)

    # Auto-derived paths
    @property
    def SNAP_DIR(self) -> Path:
        return self.BASE_DIR / "Snapshots"

    @property
    def SCAN_DIR(self) -> Path:
        return self.BASE_DIR / "Scans"

    @property
    def EXPORT_DIR(self) -> Path:
        return self.BASE_DIR / "Exports"

    @property
    def PROFILES_DIR(self) -> Path:
        return self.BASE_DIR / "Profiles"

    @property
    def TEMPBIN_DIR(self) -> Path:
        return self.BASE_DIR / "TempBin"

    @property
    def TODAY_STR(self) -> str:
        return dt.date.today().strftime("%Y-%m-%d")

    @property
    def DAILY_TEMP_DIR(self) -> Path:
        return self.TEMPBIN_DIR / self.TODAY_STR

    @property
    def TRASHBIN_DIR(self) -> Path:
        return self.BASE_DIR / "_TRASH_BIN"

    @property
    def TRASH_TODAY_DIR(self) -> Path:
        return self.TRASHBIN_DIR / self.TODAY_STR

    @property
    def STORAGE_DIR(self) -> Path:
        return self.BASE_DIR / "StorageMap"

    @property
    def STORAGE_MAP_JSON(self) -> Path:
        return self.STORAGE_DIR / "storage_map.json"

    @property
    def STORAGE_MAP_CSV(self) -> Path:
        return self.STORAGE_DIR / "storage_map_view.csv"

    @property
    def INDEX_PATH(self) -> Path:
        return self.BASE_DIR / "profile_index.json"

    @property
    def AUTOSAVE_PATH(self) -> Path:
        return self.BASE_DIR / "profile_autosave.json"

    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        for path in [
            self.SNAP_DIR,
            self.SCAN_DIR,
            self.EXPORT_DIR,
            self.PROFILES_DIR,
            self.DAILY_TEMP_DIR,
            self.TRASH_TODAY_DIR,
            self.STORAGE_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)


# Global instance
config = Config()
