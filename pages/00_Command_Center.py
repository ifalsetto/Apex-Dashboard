"""FalseTech Apex Command Center home page."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from apex_config import config
from apex_process_monitor import get_apex_process_status, verify_supported_process_names
from apex_utils import safe_load_json, bytes_human
from apex_validation import safe_int


st.set_page_config(page_title="FalseTech Apex Command Center", layout="wide")

THEME_CSS_PATH = Path(config.BASE_DIR) / "assets" / "falsetech_theme.css"
if THEME_CSS_PATH.exists():
    st.markdown(f"<style>{THEME_CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def get_profile() -> Dict[str, Any]:
    loaded = safe_load_json(config.AUTOSAVE_PATH)
    return loaded if isinstance(loaded, dict) else {}


def latest_session(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not logs:
        return {}
    return sorted(logs, key=lambda row: str(row.get("createdISO", "")), reverse=True)[0]


def folder_status(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"Area": path.name, "Ready": False, "Files": 0, "Size": "0 B"}

    total = 0
    files = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                files += 1
                total += item.stat().st_size
    except Exception:
        pass

    return {"Area": path.name, "Ready": True, "Files": files, "Size": bytes_human(total)}


profile = get_profile()
meta = profile.get("meta", {}) if isinstance(profile, dict) else {}
targets = profile.get("targets", {}) if isinstance(profile, dict) else {}
network = profile.get("network", {}) if isinstance(profile, dict) else {}
logs = profile.get("performanceLogs", []) if isinstance(profile.get("performanceLogs", []), list) else []
last = latest_session(logs)
status = get_apex_process_status()
process_verification = verify_supported_process_names()

st.title("FalseTech Apex Command Center")
st.caption("Player home base, live process status, session summary, and quick access to optimizer tools.")

hero_left, hero_right = st.columns([2, 1])

with hero_left:
    st.markdown("### Player Profile")
    profile_cols = st.columns(4)
    profile_cols[0].metric("Profile", str(meta.get("profileName", "Apex Player")))
    profile_cols[1].metric("GPU", str(meta.get("gpu", "Unknown"))[:28])
    profile_cols[2].metric("Monitor", str(meta.get("monitor", "Unknown"))[:28])
    profile_cols[3].metric("Target FPS", str(targets.get("fpsTarget", "—")))
    st.write(str(meta.get("notes", "Use the Setup page to tune this profile.")))

with hero_right:
    st.markdown("### Live Status")
    st.metric("Apex Process", "Running" if status.running else "Closed")
    st.metric("Linked", "Yes" if status.running else "No")
    st.metric("Process", status.process_name or "Waiting")
    if status.error:
        st.caption(f"Detector note: {status.error}")

st.divider()

status_cols = st.columns(4)
status_cols[0].metric("Detection", "Process-only")
status_cols[1].metric("CPU Sample", f"{status.cpu_pct:.2f}%")
status_cols[2].metric("PID", status.pid if status.pid else "—")
status_cols[3].metric("Refresh Target", f"{safe_int(targets.get('refreshHz', 240), 240)} Hz")

st.subheader("Last Session")
if last:
    session_cols = st.columns(5)
    session_cols[0].metric("Created", str(last.get("createdISO", "—")))
    session_cols[1].metric("Mode", str(last.get("mode", "—")))
    session_cols[2].metric("Duration", str(last.get("duration_s", "—")))
    session_cols[3].metric("CPU Avg", str(last.get("cpu_avg_pct", "—")))
    session_cols[4].metric("CPU Peak", str(last.get("cpu_peak_pct", "—")))
    if last.get("notes"):
        st.caption(str(last.get("notes")))
else:
    st.info("No session logs yet. Open the main dashboard and use Auto Match Log / Live Apex Monitor.")

st.subheader("Quick Actions")
quick_cols = st.columns(4)
quick_cols[0].link_button("Open Main Dashboard", "./", width="stretch")
quick_cols[1].link_button("GitHub Repo", config.REPO_URL, width="stretch")
quick_cols[2].link_button("Report Bug", f"{config.REPO_URL}/issues/new?template=bug_report.yml", width="stretch")
quick_cols[3].link_button("Request Feature", f"{config.REPO_URL}/issues/new?template=feature_request.yml", width="stretch")

st.subheader("Command Center Map")
map_rows = [
    {"Area": "Setup", "Purpose": "Profile, monitor, GPU, launch options, DxDiag import"},
    {"Area": "Live Monitor", "Purpose": "Process-only Apex detection and session logging"},
    {"Area": "Tracker", "Purpose": "Player lookup and stats fallback"},
    {"Area": "Network", "Purpose": "Local adapter, DNS, gateway, latency notes"},
    {"Area": "Match History", "Purpose": "Session logs and CSV export"},
    {"Area": "System Lab", "Purpose": "Storage audit, imports, safety checks, local diagnostics"},
]
st.dataframe(map_rows, hide_index=True, width="stretch")

st.subheader("System Health Summary")
health_cols = st.columns(4)
health_cols[0].metric("OpenAI Key", "Set" if bool(st.secrets.get("OPENAI_API_KEY", "")) else "Missing")
health_cols[1].metric("Tracker Key", "Set" if bool(st.secrets.get("TRACKER_API_KEY", "")) else "Missing")
health_cols[2].metric("Logs", len(logs))
health_cols[3].metric("Network", str(network.get("connection", "Unknown")))

storage_rows = [
    folder_status(config.PROFILES_DIR),
    folder_status(config.SNAP_DIR),
    folder_status(config.EXPORT_DIR),
    folder_status(config.STORAGE_DIR),
]
st.dataframe(storage_rows, hide_index=True, width="stretch")

with st.expander("Process detection verification", expanded=False):
    st.write("The detector treats these Apex process names as valid:")
    st.json(process_verification)

with st.expander("System Lab direction", expanded=False):
    st.write("The optimizer tools remain available in the main dashboard. This page is the command layer for player identity, live status, quick navigation, and session summaries.")
    st.write("Next build targets: squad room, legend lab, weapon lab, creator lane, and richer Tracker-driven player cards.")
