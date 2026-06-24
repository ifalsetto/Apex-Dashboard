"""Utility functions for Apex Dashboard."""
import json
import hashlib
import datetime as dt
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("apex_dashboard")


def now_iso() -> str:
    """Get current ISO timestamp."""
    return dt.datetime.now().isoformat(timespec="seconds")


def deep_copy(x: Any) -> Any:
    """Deep copy using JSON serialization."""
    try:
        return json.loads(json.dumps(x))
    except Exception as e:
        logger.error(f"Deep copy failed: {e}")
        return x


def safe_load_json(path: Path | str) -> Optional[Dict[str, Any]]:
    """Safely load JSON file with error handling.

    Args:
        path: Path to JSON file.

    Returns:
        Parsed JSON dict, or None on error.
    """
    path = Path(path)
    try:
        if not path.exists():
            logger.debug(f"JSON file not found: {path}")
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"Corrupted JSON in {path}: {e}")
        return None
    except PermissionError as e:
        logger.error(f"Permission denied reading {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading {path}: {e}")
        return None


def safe_save_json(path: Path | str, data: Any) -> bool:
    """Safely save JSON file using atomic write.

    Args:
        path: Path to JSON file.
        data: Data to serialize.

    Returns:
        True if successful, False otherwise.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)  # Atomic move
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        return False


def slug(s: str, max_len: int = 60) -> str:
    """Convert string to safe filename slug.

    Args:
        s: Input string.
        max_len: Maximum slug length.

    Returns:
        URL-safe slug.
    """
    s = (s or "").strip()
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        elif ch.isspace():
            out.append("_")
    name = "".join(out)
    # Collapse multiple underscores
    while "__" in name:
        name = name.replace("__", "_")
    return name[:max_len] if name else "profile"


def profile_hash(profile: Dict[str, Any]) -> str:
    """Generate content hash of profile (excluding lastUpdatedISO).

    Args:
        profile: Profile dictionary.

    Returns:
        SHA256 hex digest (first 12 chars).
    """
    try:
        p = deep_copy(profile)
        if "meta" in p and "lastUpdatedISO" in p["meta"]:
            p["meta"]["lastUpdatedISO"] = "LOCKED"
        s = json.dumps(p, sort_keys=True).encode("utf-8")
        return hashlib.sha256(s).hexdigest()[:12]
    except Exception as e:
        logger.error(f"Failed to hash profile: {e}")
        return "unknown"


def bytes_human(n: int) -> str:
    """Convert bytes to human-readable format.

    Args:
        n: Number of bytes.

    Returns:
        Human-readable string (e.g., "1.23 GB").
    """
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"


def safe_metric_comparison(
    label: str,
    current: Any,
    average: Optional[float],
    fmt: str = ".1f",
) -> Optional[str]:
    """Safely compare two numeric values.

    Args:
        label: Metric label.
        current: Current value.
        average: Average to compare against.
        fmt: Format specifier (e.g., '.1f').

    Returns:
        Formatted comparison string, or None if comparison fails.
    """
    try:
        if current in (None, "") or average is None:
            return None
        cur_f = float(current)
        delta = cur_f - average
        return f"{label}: {cur_f:{fmt}} vs {average:{fmt}} ({delta:+{fmt}})"
    except (ValueError, TypeError):
        return None


def validate_refresh_hz(hz: int) -> int:
    """Validate monitor refresh rate.

    Args:
        hz: Refresh rate in Hz.

    Returns:
        Clamped refresh rate (30-360 Hz).
    """
    return max(30, min(360, hz))


def validate_fps_target(fps: int, refresh_hz: int) -> int:
    """Validate FPS target.

    Args:
        fps: Target FPS.
        refresh_hz: Monitor refresh rate.

    Returns:
        Clamped FPS (max: refresh_hz - 1).
    """
    return min(fps, refresh_hz - 1) if refresh_hz > 30 else fps
