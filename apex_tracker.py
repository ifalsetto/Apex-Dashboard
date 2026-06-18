"""Tracker.gg integration for Apex Dashboard."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, Optional

import requests
import streamlit as st

logger = logging.getLogger("apex_dashboard")

TRACKER_PROFILE_URL = "https://public-api.tracker.gg/v2/apex/standard/profile/{platform}/{player}"
VALID_PLATFORMS = {"origin", "psn", "xbl"}


def normalize_platform(platform: str | None) -> str:
    value = str(platform or "origin").strip().lower()
    return value if value in VALID_PLATFORMS else "origin"


def get_tracker_api_key() -> Optional[str]:
    try:
        secret = st.secrets.get("TRACKER_API_KEY")
        if secret:
            return str(secret).strip()
    except Exception:
        pass

    return os.getenv("TRACKER_API_KEY", "").strip() or None


def _unwrap_stat_value(value: Any, fallback: Any = "—") -> Any:
    if isinstance(value, dict):
        if value.get("displayValue") not in (None, ""):
            return value["displayValue"]
        if value.get("value") not in (None, ""):
            return value["value"]
    elif value not in (None, ""):
        return value
    return fallback


def _read_stat(stats: Dict[str, Any], keys: Iterable[str], fallback: Any = "—") -> Any:
    for key in keys:
        if key in stats:
            return _unwrap_stat_value(stats.get(key), fallback)
    return fallback


def _read_rank(stats: Dict[str, Any]) -> str:
    rank_score = stats.get("rankScore") or stats.get("rank") or stats.get("rankedScore")
    if isinstance(rank_score, dict):
        metadata = rank_score.get("metadata") or {}
        if metadata.get("rankName"):
            return str(metadata["rankName"])
        display_value = rank_score.get("displayValue")
        if display_value not in (None, ""):
            return str(display_value)
        value = rank_score.get("value")
        if value not in (None, ""):
            return str(value)
    return "Unranked"


def _pick_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    root = payload.get("data") or payload
    candidates = []
    if isinstance(root, dict):
        for key in ("profile", "player"):
            if isinstance(root.get(key), dict):
                candidates.append(root[key])
        for key in ("data", "results", "players", "profiles"):
            value = root.get(key)
            if isinstance(value, list) and value:
                candidates.append(value[0])
    elif isinstance(root, list) and root:
        candidates.append(root[0])
    if isinstance(root, dict):
        candidates.append(root)

    for item in candidates:
        if isinstance(item, dict):
            return item
    return {}


def _get_segments(payload: Dict[str, Any], profile: Dict[str, Any]) -> list[Dict[str, Any]]:
    root = payload.get("data") or payload
    for value in (
        profile.get("segments"),
        (profile.get("data") or {}).get("segments") if isinstance(profile.get("data"), dict) else None,
        root.get("segments") if isinstance(root, dict) else None,
        (root.get("data") or {}).get("segments") if isinstance(root, dict) and isinstance(root.get("data"), dict) else None,
    ):
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def normalize_tracker_profile(payload: Dict[str, Any], *, query: str, platform: str) -> Dict[str, Any]:
    root = payload.get("data") or payload
    profile = _pick_profile(payload)
    segments = _get_segments(payload, profile)

    overview_segment = next((segment for segment in segments if segment.get("type") == "overview"), None)
    if not overview_segment:
        overview_segment = next(
            (segment for segment in segments if str((segment.get("metadata") or {}).get("name", "")).lower() == "overview"),
            None,
        )
    overview_segment = overview_segment or (segments[0] if segments else {})
    legend_segment = next((segment for segment in segments if segment.get("type") == "legend"), None)
    if not legend_segment:
        legend_segment = next((segment for segment in segments if (segment.get("metadata") or {}).get("legendName")), None)

    stats = overview_segment.get("stats") or profile.get("stats") or (root.get("stats") if isinstance(root, dict) else {}) or {}
    platform_info = profile.get("platformInfo") or (root.get("platformInfo") if isinstance(root, dict) else {}) or {}
    user_info = profile.get("userInfo") or (root.get("userInfo") if isinstance(root, dict) else {}) or {}

    player_name = (
        platform_info.get("platformUserHandle")
        or platform_info.get("platformUserIdentifier")
        or profile.get("platformUserHandle")
        or profile.get("platformUserIdentifier")
        or profile.get("name")
        or profile.get("username")
        or query
    )
    avatar_url = (
        user_info.get("avatarUrl")
        or user_info.get("imageUrl")
        or profile.get("avatarUrl")
        or profile.get("imageUrl")
        or platform_info.get("avatarUrl")
        or ""
    )
    current_legend = (
        (legend_segment or {}).get("metadata", {}).get("legendName")
        or (legend_segment or {}).get("metadata", {}).get("name")
        or "—"
    )

    return {
        "ok": True,
        "source": "tracker",
        "player_name": player_name,
        "platform": normalize_platform(platform),
        "avatar_url": avatar_url,
        "level": _read_stat(stats, ["level"]),
        "rank": _read_rank(stats),
        "kills": _read_stat(stats, ["kills"]),
        "damage": _read_stat(stats, ["damage"]),
        "wins": _read_stat(stats, ["wins", "seasonWins"]),
        "kd": _read_stat(stats, ["kd", "kdr", "killDeathRatio"]),
        "matches": _read_stat(stats, ["matchesPlayed", "gamesPlayed", "matches"]),
        "current_legend": current_legend,
        "raw": payload,
    }


def tracker_fallback_profile(*, query: str = "Apex Player", platform: str = "origin", error: str = "") -> Dict[str, Any]:
    return {
        "ok": False,
        "source": "fallback",
        "player_name": query or "Apex Player",
        "platform": normalize_platform(platform),
        "avatar_url": "",
        "level": "—",
        "rank": "Unranked",
        "kills": "—",
        "damage": "—",
        "wins": "—",
        "kd": "—",
        "matches": "—",
        "current_legend": "—",
        "error": error,
        "raw": {},
    }


def fetch_tracker_profile(query: str, platform: str) -> Dict[str, Any]:
    clean_query = str(query or "").strip()
    clean_platform = normalize_platform(platform)
    if not clean_query:
        return tracker_fallback_profile(query=clean_query, platform=clean_platform, error="Player name is required.")

    api_key = get_tracker_api_key()
    if not api_key:
        msg = "Tracker API key not configured. Using fallback data."
        logger.info(msg)
        return tracker_fallback_profile(query=clean_query, platform=clean_platform, error=msg)

    try:
        response = requests.get(
            TRACKER_PROFILE_URL.format(platform=clean_platform, player=clean_query),
            headers={"TRN-Api-Key": api_key, "Accept": "application/json"},
            timeout=15,
        )
        if response.status_code >= 400:
            msg = f"Tracker API request failed: {response.status_code} {response.text[:200]}"
            logger.warning(msg)
            return tracker_fallback_profile(query=clean_query, platform=clean_platform, error=msg)

        payload = response.json()
        normalized = normalize_tracker_profile(payload, query=clean_query, platform=clean_platform)
        logger.info("Tracker profile loaded for %s on %s", clean_query, clean_platform)
        return normalized
    except requests.RequestException as exc:
        msg = f"Tracker request error: {exc}"
        logger.warning(msg)
        return tracker_fallback_profile(query=clean_query, platform=clean_platform, error=msg)
    except Exception as exc:
        msg = f"Tracker normalization error: {exc}"
        logger.exception(msg)
        return tracker_fallback_profile(query=clean_query, platform=clean_platform, error=msg)
