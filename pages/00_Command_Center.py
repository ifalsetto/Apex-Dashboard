"""Apex Command Center home page.

This Streamlit page is the entry point into the Apex system. It displays the
player profile card, live Apex process status, last session summary, quick
actions, latency/source analyzer entry points, system lab map, safety rails,
heartbeats, Cell/Brain/Agent status, and system health.

Everything on this page is read-only and local-first. It never attempts to read
process memory, automate input, modify game files, manipulate packets, or
interact with anti-cheat systems.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from apex_config import config
from apex_guardrails import agent_table, build_cell_snapshot, build_heartbeat, guardrail_table
from apex_process_monitor import get_apex_process_status, verify_supported_process_names
from apex_utils import safe_load_json, bytes_human
from apex_validation import safe_int


st.set_page_config(page_title="Apex Command Center", layout="wide")

THEME_CSS_PATH = Path(config.BASE_DIR) / "assets" / "falsetech_theme.css"
if THEME_CSS_PATH.exists():
    st.markdown(f"<style>{THEME_CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def get_profile() -> Dict[str, Any]:
    """Load the autosaved profile if present; otherwise return an empty dict."""
    loaded = safe_load_json(config.AUTOSAVE_PATH)
    return loaded if isinstance(loaded, dict) else {}


def latest_session(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the most recent performance log from a list of session logs."""
    if not logs:
        return {}
    return sorted(logs, key=lambda row: str(row.get("createdISO", "")), reverse=True)[0]


def folder_status(path: Path) -> Dict[str, Any]:
    """Summarize readiness, file count and total size for a given folder."""
    if not path.exists():
        return {"Area": path.name, "Ready": False, "Files": 0, "Size": "0 B"}

    total = 0
    files = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                files += 1
                total += item.stat().st_size
    except Exception as exc:
        return {"Area": path.name, "Ready": False, "Files": files, "Size": bytes_human(total), "Note": str(exc)[:80]}

    return {"Area": path.name, "Ready": True, "Files": files, "Size": bytes_human(total)}


def metric_text(value: Any, fallback: str = "—", limit: int = 30) -> str:
    """Return safe metric text for Streamlit metric cards."""
    text = str(value if value not in (None, "") else fallback)
    return text[:limit]


# Load profile and derive commonly used sections.
profile: Dict[str, Any] = get_profile()
meta: Dict[str, Any] = profile.get("meta", {}) if isinstance(profile, dict) else {}
targets: Dict[str, Any] = profile.get("targets", {}) if isinstance(profile, dict) else {}
network: Dict[str, Any] = profile.get("network", {}) if isinstance(profile, dict) else {}
logs: List[Dict[str, Any]] = profile.get("performanceLogs", []) if isinstance(profile.get("performanceLogs", []), list) else []
last: Dict[str, Any] = latest_session(logs)
status = get_apex_process_status()
process_verification = verify_supported_process_names()
heartbeat = build_heartbeat()
cell = build_cell_snapshot({"profile": profile, "process": status.to_dict(), "latency": "linked-page"})

# Page header and description
st.title("Apex Command Center")
st.caption(
    "Player home base, live process status, session summary, latency/source analyzer, safety rails, and quick access to optimizer tools."
)

# Hero section: profile card and live status
hero_left, hero_right = st.columns([2, 1])

with hero_left:
    st.markdown("### Player Profile")
    profile_cols = st.columns(4)
    profile_cols[0].metric("Profile", metric_text(meta.get("profileName"), "Apex Player"))
    profile_cols[1].metric("GPU", metric_text(meta.get("gpu"), "Unknown", 28))
    profile_cols[2].metric("Monitor", metric_text(meta.get("monitor"), "Unknown", 28))
    profile_cols[3].metric("Target FPS", metric_text(targets.get("fpsTarget")))
    st.write(str(meta.get("notes", "Use the Setup page to tune this profile.")))

with hero_right:
    st.markdown("### Live Status")
    st.metric("Apex Process", "Running" if status.running else "Closed")
    st.metric("Linked", "Yes" if status.running else "No")
    st.metric("Process", status.process_name or "Waiting")
    if status.error:
        st.caption(f"Detector note: {status.error}")

# Divider and basic runtime stats
st.divider()

status_cols = st.columns(4)
status_cols[0].metric("Detection", "Process-only")
status_cols[1].metric("CPU Sample", f"{status.cpu_pct:.2f}%")
status_cols[2].metric("PID", status.pid if status.pid else "—")
status_cols[3].metric("Refresh Target", f"{safe_int(targets.get('refreshHz', 240), 240)} Hz")

# Latency/source analyzer summary
st.subheader("Latency Source Analyzer")
latency_cols = st.columns(4)
latency_cols[0].metric("Mode", "Display-only")
latency_cols[1].metric("Machine Delay", "Frame/Input")
latency_cols[2].metric("Network Delay", "Ping/Jitter/Loss")
latency_cols[3].metric("Router Queue", "QoS/SQM Advice")
st.info(
    "Use the Latency Source Analyzer to compare current settings against a simulated profile and generate a safe live overlay feed. "
    "It explains whether delay is likely from the PC, frame pacing, network, packet loss, or router queueing."
)

# Last session summary
st.subheader("Last Session")
if last:
    session_cols = st.columns(5)
    session_cols[0].metric("Created", metric_text(last.get("createdISO"), limit=26))
    session_cols[1].metric("Mode", metric_text(last.get("mode")))
    session_cols[2].metric("Duration", metric_text(last.get("duration_s")))
    session_cols[3].metric("CPU Avg", metric_text(last.get("cpu_avg_pct")))
    session_cols[4].metric("CPU Peak", metric_text(last.get("cpu_peak_pct")))
    if last.get("notes"):
        st.caption(str(last.get("notes")))
else:
    st.info("No session logs yet. Open the main dashboard and use Auto Match Log / Live Apex Monitor.")

# Quick actions for common tasks
st.subheader("Quick Actions")
quick_cols = st.columns(5)
quick_cols[0].link_button("Open Main Dashboard", "./", width="stretch")
quick_cols[1].link_button("Latency Analyzer", "./Latency_Source_Analyzer", width="stretch")
quick_cols[2].link_button("GitHub Repo", config.REPO_URL, width="stretch")
quick_cols[3].link_button(
    "Report Bug",
    f"{config.REPO_URL}/issues/new?template=bug_report.yml",
    width="stretch",
)
quick_cols[4].link_button(
    "Request Feature",
    f"{config.REPO_URL}/issues/new?template=feature_request.yml",
    width="stretch",
)

# System Lab map to orient players to available tools
st.subheader("System Lab Map")
map_rows = [
    {"Area": "Setup", "Purpose": "Profile, monitor, GPU, launch options, DxDiag import"},
    {"Area": "Live Monitor", "Purpose": "Process-only Apex detection and session logging"},
    {"Area": "Latency Source Analyzer", "Purpose": "Machine vs network delay, settings simulation, safe overlay feed"},
    {"Area": "Live Coaching", "Purpose": "Display-only reminders: cover, reset, rotate, group, review"},
    {"Area": "Tracker", "Purpose": "Player lookup and stats fallback"},
    {"Area": "Network", "Purpose": "Adapter, DNS, gateway, jitter, loss, bufferbloat notes"},
    {"Area": "Match History", "Purpose": "Session logs and CSV export"},
    {"Area": "System Lab", "Purpose": "Storage audit, imports, safety checks, local diagnostics"},
]
st.dataframe(map_rows, hide_index=True, width="stretch")

# Navigation links to jump into different areas of the dashboard.
st.subheader("Navigation")
nav_items = [
    ("Setup", "./"),
    ("Live Monitor", "./#live-monitor"),
    ("Latency Analyzer", "./Latency_Source_Analyzer"),
    ("Tracker", "./Live_Tracker_AI_Coach"),
    ("Network", "./#net"),
    ("Match History", "./#perf"),
]
nav_cols = st.columns(len(nav_items))
for idx, (label, url) in enumerate(nav_items):
    nav_cols[idx].link_button(label, url, width="stretch")

# Heartbeat, Cell, Brain, safety rails
st.subheader("Heartbeat / Cell / Brain")
heart_cols = st.columns(4)
heart_cols[0].metric("Safe Mode", "ON" if heartbeat.get("safe_mode") else "OFF")
heart_cols[1].metric("Active Agents", heartbeat.get("active_agents", 0))
heart_cols[2].metric("Cell Context", "OK" if cell.get("context_ok") else "Needs Input")
heart_cols[3].metric("Blocked Capabilities", heartbeat.get("blocked_capabilities", 0))

with st.expander("Active agents", expanded=False):
    st.dataframe(agent_table(), hide_index=True, width="stretch")

with st.expander("Safety rails and guardrails", expanded=False):
    st.dataframe(guardrail_table(), hide_index=True, width="stretch")
    st.caption("Router/QoS controls are recommendation-only unless explicitly configured by the user on owned/admin-approved equipment.")

# System health summary and storage status
st.subheader("System Health Summary")
health_cols = st.columns(4)
health_cols[0].metric(
    "OpenAI Key", "Set" if bool(st.secrets.get("OPENAI_API_KEY", "")) else "Missing"
)
health_cols[1].metric(
    "Tracker Key", "Set" if bool(st.secrets.get("TRACKER_API_KEY", "")) else "Missing"
)
health_cols[2].metric("Logs", len(logs))
health_cols[3].metric("Network", str(network.get("connection", "Unknown")))

# Show storage readiness for important folders
storage_rows = [
    folder_status(config.PROFILES_DIR),
    folder_status(config.SNAP_DIR),
    folder_status(config.EXPORT_DIR),
    folder_status(config.STORAGE_DIR),
]
st.dataframe(storage_rows, hide_index=True, width="stretch")

# Debugging and guidance expanders
with st.expander("Process detection verification", expanded=False):
    st.write("The detector treats these Apex process names as valid:")
    st.json(process_verification)

with st.expander("Build direction", expanded=False):
    st.write(
        "The dashboard now has a safe latency/source analyzer path: current settings vs simulated settings, "
        "machine vs network diagnosis, router queueing notes, and display-only coaching prompts."
    )
    st.write(
        "Next build targets: persistent overlay viewer, session-to-simulation comparison history, squad room, legend lab, weapon lab, and richer Tracker-driven player cards."
    )
