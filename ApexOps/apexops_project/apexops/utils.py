from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping (dict). Got: {type(data)}")
    return data


def expand_path(value: str, ctx: Optional[Dict[str, Any]] = None) -> str:
    """Expand env vars + {placeholders} + ~ in a Windows-friendly way."""
    if value is None:
        return ""
    s = str(value)
    s = os.path.expandvars(s)
    s = os.path.expanduser(s)
    if ctx:
        try:
            s = s.format_map(ctx)
        except Exception:
            # If formatting fails, keep original string.
            pass
    return s


def ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class ResolvedConfig:
    raw: Dict[str, Any]
    config_path: Path

    capframex_dir: Path
    apex_local_dir: Path
    data_dir: Path
    db_path: Path

    scan_interval_sec: int
    track_apex_process: bool
    capture_extensions: Tuple[str, ...]

    profile: Dict[str, Any]


def load_config(config_path: Path) -> ResolvedConfig:
    raw = read_yaml(config_path)

    paths = raw.get("paths", {})
    if not isinstance(paths, dict):
        raise ValueError("config.yaml: paths must be a mapping")

    # Resolve data_dir first because db_path may reference it.
    data_dir = expand_path(paths.get("data_dir", "./data"))
    ctx = {"data_dir": data_dir}

    capframex_dir = expand_path(paths.get("capframex_captures_dir", ""), ctx)
    apex_local_dir = expand_path(paths.get("apex_local_config_dir", ""), ctx)
    db_path = expand_path(paths.get("db_path", "{data_dir}\\apexops.db"), ctx)

    collector = raw.get("collector", {})
    if not isinstance(collector, dict):
        collector = {}

    scan_interval = int(collector.get("scan_interval_sec", 5))
    track_proc = bool(collector.get("track_apex_process", True))

    exts = collector.get("capture_extensions", [".json", ".json.gz", ".csv"])
    if not isinstance(exts, list):
        exts = [".json", ".json.gz", ".csv"]
    exts_tuple = tuple(str(e).lower() for e in exts)

    profile = raw.get("profile", {})
    if not isinstance(profile, dict):
        profile = {}

    return ResolvedConfig(
        raw=raw,
        config_path=config_path,
        capframex_dir=Path(capframex_dir),
        apex_local_dir=Path(apex_local_dir),
        data_dir=Path(data_dir),
        db_path=Path(db_path),
        scan_interval_sec=scan_interval,
        track_apex_process=track_proc,
        capture_extensions=exts_tuple,
        profile=profile,
    )


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def try_get_primary_display_mode() -> Dict[str, Any]:
    """Windows-only: returns {width,height,hz}."""
    if os.name != "nt":
        return {"width": None, "height": None, "hz": None, "source": "non-windows"}

    try:
        import ctypes
        from ctypes import wintypes

        ENUM_CURRENT_SETTINGS = -1

        class DEVMODEW(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", wintypes.WCHAR * 32),
                ("dmSpecVersion", wintypes.WORD),
                ("dmDriverVersion", wintypes.WORD),
                ("dmSize", wintypes.WORD),
                ("dmDriverExtra", wintypes.WORD),
                ("dmFields", wintypes.DWORD),
                ("dmOrientation", wintypes.SHORT),
                ("dmPaperSize", wintypes.SHORT),
                ("dmPaperLength", wintypes.SHORT),
                ("dmPaperWidth", wintypes.SHORT),
                ("dmScale", wintypes.SHORT),
                ("dmCopies", wintypes.SHORT),
                ("dmDefaultSource", wintypes.SHORT),
                ("dmPrintQuality", wintypes.SHORT),
                ("dmColor", wintypes.SHORT),
                ("dmDuplex", wintypes.SHORT),
                ("dmYResolution", wintypes.SHORT),
                ("dmTTOption", wintypes.SHORT),
                ("dmCollate", wintypes.SHORT),
                ("dmFormName", wintypes.WCHAR * 32),
                ("dmLogPixels", wintypes.WORD),
                ("dmBitsPerPel", wintypes.DWORD),
                ("dmPelsWidth", wintypes.DWORD),
                ("dmPelsHeight", wintypes.DWORD),
                ("dmDisplayFlags", wintypes.DWORD),
                ("dmDisplayFrequency", wintypes.DWORD),
                ("dmICMMethod", wintypes.DWORD),
                ("dmICMIntent", wintypes.DWORD),
                ("dmMediaType", wintypes.DWORD),
                ("dmDitherType", wintypes.DWORD),
                ("dmReserved1", wintypes.DWORD),
                ("dmReserved2", wintypes.DWORD),
                ("dmPanningWidth", wintypes.DWORD),
                ("dmPanningHeight", wintypes.DWORD),
            ]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        EnumDisplaySettingsW = user32.EnumDisplaySettingsW
        EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW)]
        EnumDisplaySettingsW.restype = wintypes.BOOL

        devmode = DEVMODEW()
        devmode.dmSize = ctypes.sizeof(DEVMODEW)

        ok = EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode))
        if not ok:
            return {"width": None, "height": None, "hz": None, "source": "EnumDisplaySettings failed"}

        return {
            "width": int(devmode.dmPelsWidth),
            "height": int(devmode.dmPelsHeight),
            "hz": int(devmode.dmDisplayFrequency),
            "source": "EnumDisplaySettingsW",
        }
    except Exception as e:
        return {"width": None, "height": None, "hz": None, "source": f"error: {e}"}


def try_get_gpu_driver_info() -> Dict[str, Any]:
    """Best-effort GPU + driver version using PowerShell CIM. Windows-only."""
    if os.name != "nt":
        return {"name": None, "driver_version": None, "driver_date": None, "source": "non-windows"}

    ps = (
        "Get-CimInstance Win32_VideoController "
        "| Select-Object Name, DriverVersion, DriverDate "
        "| ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return {"name": None, "driver_version": None, "driver_date": None, "source": "powershell failed"}

        data = json.loads(out.stdout)
        items = data if isinstance(data, list) else [data]

        # Prefer NVIDIA
        nvidia = None
        for it in items:
            name = str(it.get("Name", ""))
            if "nvidia" in name.lower():
                nvidia = it
                break
        it = nvidia or (items[0] if items else {})

        return {
            "name": it.get("Name"),
            "driver_version": it.get("DriverVersion"),
            "driver_date": it.get("DriverDate"),
            "source": "Win32_VideoController",
        }
    except Exception as e:
        return {"name": None, "driver_version": None, "driver_date": None, "source": f"error: {e}"}


def human_bool(v: Any) -> str:
    return "on" if bool(v) else "off"


def stable_file_ready(path: Path, min_age_sec: float = 2.0) -> bool:
    """Avoid importing while the file is still being written."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return False

    age = time.time() - stat.st_mtime
    return age >= min_age_sec and stat.st_size > 0
