"""Input validation for Apex Dashboard."""
from typing import Any, Optional
import logging

logger = logging.getLogger("apex_dashboard")


def validate_profile_structure(profile: Any) -> bool:
    """Validate profile has required structure.

    Args:
        profile: Profile to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(profile, dict):
        return False

    required_keys = {"meta", "targets", "toggles", "launchOptions"}
    return required_keys.issubset(profile.keys())


def safe_int(value: Any, default: int = 0, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Safely convert value to int with bounds.

    Args:
        value: Value to convert.
        default: Default if conversion fails.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        Converted integer.
    """
    try:
        result = int(value or default)
        if min_val is not None:
            result = max(result, min_val)
        if max_val is not None:
            result = min(result, max_val)
        return result
    except (ValueError, TypeError):
        logger.debug(f"Failed to convert {value} to int, using default {default}")
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float.

    Args:
        value: Value to convert.
        default: Default if conversion fails.

    Returns:
        Converted float.
    """
    try:
        return float(value or default)
    except (ValueError, TypeError):
        logger.debug(f"Failed to convert {value} to float, using default {default}")
        return default
