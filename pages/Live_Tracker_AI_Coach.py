"""Streamlit page for live Tracker.gg lookup, AI coach, and safe psutil monitor."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import psutil
import streamlit as st

from apex_ai_coach import generate_ai_coach_report
from apex_config import config
from apex_tracker import fetch_tracker_profile, tracker_fallback_profile
from apex_utils import safe_load_json

logger = logging.getLogger("apex_dashboard")
APEX_PROCESS_NAMES = {"r5apex", "r5apex.exe"}


def find_apex_process() -> Optional[psutil.Process]:
    for proc in psutil.process_iter(["name"]):
        try:
            if (proc.info.get("name") or "").lower() in APEX_PROCESS_NAMES:
                return proc
        except (psutil.Error, OSError):
            continue
    return None


def read_apex_monitor_snapshot() -> Dict[str, Any]:
    proc = find_apex_process()
    if not proc:
        return {
            "apex_running": False,
            "process_name": "",
            "pid": "",
            "cpu_pct": 0.0,
            "memory_mb": 0.0,
        }

    try:
        return {
            "apex_running": True,
            "process_name": proc.name(),
            "pid": proc.pid,
            "cpu_pct": round(proc.cpu_percent(interval=0.15), 2),
            "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 2),
        }
    except (psutil.Error, OSError) as exc:
        logger.warning("Failed to read Apex process snapshot: %s", exc)
        return {
            "apex_running": True,
            "process_name": "r5apex",
            "pid": "unknown",
            "cpu_pct": 0.0,
            "memory_mb": 0.0,
        }


def get_latest_match(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    logs = profile.get("performanceLogs", [])
    if isinstance(logs, list) and logs:
        return logs[-1]
    return None


def render_tracker_profile(profile: Dict[str, Any]) -> None:
    left, right = st.columns([1, 2])

    with left:
        st.subheader("Profile Card")
        if profile.get("avatar_url"):
            st.image(profile["avatar_url"], width=120)
        st.markdown(f"**Player:** {profile.get('player_name', 'Apex Player')}")
        st.markdown(f"**Platform:** {profile.get('platform', 'pc').upper()}")
        st.markdown(f"**Rank:** {profile.get('rank', 'Unranked')}")
        st.markdown(f"**Level:** {profile.get('level', '—')}")
        st.markdown(f"**Legend:** {profile.get('current_legend', '—')}")

    with right:
        st.subheader("Overview Strip")
        stats = [
            ("Kills", profile.get("kills", "—")),
            ("Damage", profile.get("damage", "—")),
            ("Wins", profile.get("wins", "—")),
            ("K/D", profile.get("kd", "—")),
            ("Matches", profile.get("matches", "—")),
            ("Source", profile.get("source", "fallback")),
        ]
        cols = st.columns(3)
        for index, (label, value) in enumerate(stats):
            with cols[index % 3]:
                st.metric(label, value)


def main() -> None:
    st.set_page_config(page_title="Apex Live Tracker + Coach", layout="wide")
    st.title("Apex Live Tracker + Coach")
    st.caption("Streamlit-native Tracker.gg lookup, local-first AI coach, and safe psutil monitor.")

    if "tracker_profile" not in st.session_state:
        st.session_state.tracker_profile = tracker_fallback_profile(
            query="Apex Player",
            platform="pc",
            error="No live search yet.",
        )
    if "tracker_last_error" not in st.session_state:
        st.session_state.tracker_last_error = ""
    if "ai_coach_report" not in st.session_state:
        st.session_state.ai_coach_report = None

    profile = st.session_state.get("profile")
    if not isinstance(profile, dict):
        profile = safe_load_json(config.AUTOSAVE_PATH) or {}

    with st.sidebar:
        st.subheader("Search Player")
        query = st.text_input("Player name", value="", placeholder="Example: NotFalsetto")
        platform = st.selectbox("Platform", ["pc", "psn", "xbl"], index=0)
        if st.button("Search Tracker.gg", width="stretch"):
            result = fetch_tracker_profile(query, platform)
            if result.get("ok"):
                st.session_state.tracker_profile = result
                st.session_state.tracker_last_error = ""
            else:
                st.session_state.tracker_last_error = result.get("error", "Tracker search failed.")
                logger.warning(
                    "Tracker search failed. Keeping fallback data visible: %s",
                    st.session_state.tracker_last_error,
                )
        if st.session_state.tracker_last_error:
            st.warning(st.session_state.tracker_last_error)

    render_tracker_profile(st.session_state.tracker_profile)

    st.markdown("---")
    monitor = read_apex_monitor_snapshot()
    monitor_col, coach_col = st.columns([1, 2])

    with monitor_col:
        st.subheader("Safe Monitor")
        st.metric("Apex running", "Yes" if monitor["apex_running"] else "No")
        st.metric("CPU %", monitor["cpu_pct"])
        st.metric("Memory MB", monitor["memory_mb"])
        st.caption("Uses psutil process metadata only. No memory reads, injection, macros, or anti-cheat bypass behavior.")

    with coach_col:
        st.subheader("AI Coach Beta")
        if st.button("Generate coach report", width="stretch"):
            st.session_state.ai_coach_report = generate_ai_coach_report(
                profile=profile,
                tracker_profile=st.session_state.tracker_profile,
                latest_match=get_latest_match(profile),
                performance_stats=monitor,
                export_dir=Path(config.EXPORT_DIR) / "reports",
            )

        report = st.session_state.ai_coach_report
        if report:
            st.caption(f"Source: {report.get('source', 'unknown')} • Created: {report.get('createdISO', '—')}")
            if report.get("summary"):
                st.write(report["summary"])
            for item in report.get("suggestions", []) or []:
                st.markdown(f"- {item}")
        else:
            st.info("Generate a report after searching a player or logging a match. If OpenAI is unavailable, a local fallback report is generated.")


if __name__ == "__main__":
    main()
