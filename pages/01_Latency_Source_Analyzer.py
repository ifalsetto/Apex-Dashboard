"""Latency Source Analyzer and Live Settings Impact page.

This page is a safe display/simulation layer. It does not modify Apex, read game
memory, automate input, or control the network. Router/QoS items are advisory
unless the user configures them outside the game with proper admin permission.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from apex_config import config
from apex_guardrails import agent_table, build_cell_snapshot, build_heartbeat, guardrail_table
from apex_latency_engine import (
    NetworkSample,
    SettingsProfile,
    analyze_latency,
    build_overlay_payload,
    overlay_payload_json,
)


st.set_page_config(page_title="Latency Source Analyzer", layout="wide")

THEME_CSS_PATH = Path(config.BASE_DIR) / "assets" / "falsetech_theme.css"
if THEME_CSS_PATH.exists():
    st.markdown(f"<style>{THEME_CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

st.title("Latency Source Analyzer")
st.caption(
    "Compare current settings against a simulated profile, then show likely machine/network latency sources and safe live-coaching overlay data."
)

st.warning(
    "Safety mode: display-only. No game memory reads, no input automation, no packet manipulation, no anti-cheat interaction, and no game-file changes."
)

# -------------------- Inputs --------------------
st.subheader("1. Current vs Simulated Settings")
current_col, simulated_col = st.columns(2)

with current_col:
    st.markdown("#### Current Settings")
    current_fps = st.number_input("Current FPS cap / average", min_value=30, max_value=500, value=180, step=1)
    current_refresh = st.number_input("Current refresh Hz", min_value=60, max_value=500, value=240, step=1)
    current_gpu = st.slider("Current GPU load %", 0, 100, 88)
    current_cpu = st.slider("Current CPU load %", 0, 100, 45)
    current_reflex = st.toggle("Current NVIDIA Reflex / low latency enabled", value=True)
    current_vsync = st.toggle("Current V-Sync enabled", value=False)
    current_gsync = st.toggle("Current G-SYNC / VRR enabled", value=False)
    current_shadows = st.toggle("Current low/off shadows", value=True)
    current_effects = st.toggle("Current low effects", value=True)
    current_audio = st.toggle("Current clarity audio profile", value=True)

with simulated_col:
    st.markdown("#### Simulated Settings")
    sim_fps = st.number_input("Simulated FPS cap / average", min_value=30, max_value=500, value=190, step=1)
    sim_refresh = st.number_input("Simulated refresh Hz", min_value=60, max_value=500, value=240, step=1)
    sim_gpu = st.slider("Simulated GPU load %", 0, 100, 82)
    sim_cpu = st.slider("Simulated CPU load %", 0, 100, 42)
    sim_reflex = st.toggle("Simulated NVIDIA Reflex / low latency enabled", value=True)
    sim_vsync = st.toggle("Simulated V-Sync enabled", value=False)
    sim_gsync = st.toggle("Simulated G-SYNC / VRR enabled", value=False)
    sim_shadows = st.toggle("Simulated low/off shadows", value=True)
    sim_effects = st.toggle("Simulated low effects", value=True)
    sim_audio = st.toggle("Simulated clarity audio profile", value=True)

st.subheader("2. Network Sample")
net_cols = st.columns(6)
idle_ping = net_cols[0].number_input("Idle ping ms", min_value=0.0, max_value=1000.0, value=35.0, step=1.0)
loaded_ping = net_cols[1].number_input("Loaded ping ms", min_value=0.0, max_value=1500.0, value=48.0, step=1.0)
jitter = net_cols[2].number_input("Jitter ms", min_value=0.0, max_value=500.0, value=4.0, step=1.0)
packet_loss = net_cols[3].number_input("Packet loss %", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
qos_enabled = net_cols[4].toggle("Router QoS/SQM enabled", value=False)
connection_type = net_cols[5].selectbox("Connection", ["Ethernet", "Wi-Fi", "Unknown"], index=0)

current = SettingsProfile(
    name="Current",
    fps_target=float(current_fps),
    refresh_hz=float(current_refresh),
    gpu_load_pct=float(current_gpu),
    cpu_load_pct=float(current_cpu),
    reflex_on=bool(current_reflex),
    vsync_on=bool(current_vsync),
    gsync_on=bool(current_gsync),
    shadows_low=bool(current_shadows),
    effects_low=bool(current_effects),
    audio_clarity_profile=bool(current_audio),
)
simulated = SettingsProfile(
    name="Simulated",
    fps_target=float(sim_fps),
    refresh_hz=float(sim_refresh),
    gpu_load_pct=float(sim_gpu),
    cpu_load_pct=float(sim_cpu),
    reflex_on=bool(sim_reflex),
    vsync_on=bool(sim_vsync),
    gsync_on=bool(sim_gsync),
    shadows_low=bool(sim_shadows),
    effects_low=bool(sim_effects),
    audio_clarity_profile=bool(sim_audio),
)
network = NetworkSample(
    idle_ping_ms=float(idle_ping),
    loaded_ping_ms=float(loaded_ping),
    jitter_ms=float(jitter),
    packet_loss_pct=float(packet_loss),
    qos_enabled=bool(qos_enabled),
    connection_type=str(connection_type),
)

report = analyze_latency(current, simulated, network)
payload = build_overlay_payload(report, current, simulated, network)

# -------------------- Output --------------------
st.subheader("3. Result")
result_cols = st.columns(5)
result_cols[0].metric("Current total estimate", f"{report.current_total_ms:.2f} ms")
result_cols[1].metric("Simulated total estimate", f"{report.simulated_total_ms:.2f} ms")
result_cols[2].metric("Delta", f"{report.delta_ms:+.2f} ms")
result_cols[3].metric("Primary source", report.primary_source)
result_cols[4].metric("Risk", report.risk_level.upper())

st.markdown("#### Component Breakdown")
st.dataframe(report.component_rows, hide_index=True, width="stretch")

rec_col, coach_col = st.columns(2)
with rec_col:
    st.markdown("#### Recommendations")
    for item in report.recommendations:
        st.write(f"- {item}")

with coach_col:
    st.markdown("#### Live Coaching Prompts")
    for item in report.coaching_prompts:
        st.write(f"- {item}")

st.subheader("4. Safe Overlay Feed")
st.caption("Use this as a display-only JSON feed for a browser/second-monitor overlay. It does not control Apex or the network.")
st.json(payload)
st.download_button(
    "Download overlay feed JSON",
    data=overlay_payload_json(report, current, simulated, network),
    file_name="apex live settings impact overlay.json",
    mime="application/json",
    width="stretch",
)

st.subheader("5. Heartbeat / Cell / Brain")
health_cols = st.columns(4)
heartbeat = build_heartbeat()
cell = build_cell_snapshot({"latency": report.to_dict(), "profile": current.name, "process": "display-only"})
health_cols[0].metric("Safe Mode", "ON" if heartbeat.get("safe_mode") else "OFF")
health_cols[1].metric("Active Agents", heartbeat.get("active_agents", 0))
health_cols[2].metric("Cell Context", "OK" if cell.get("context_ok") else "Needs Input")
health_cols[3].metric("Blocked Capabilities", heartbeat.get("blocked_capabilities", 0))

with st.expander("Brain agents", expanded=False):
    st.dataframe(agent_table(), hide_index=True, width="stretch")

with st.expander("Safety rails and guardrails", expanded=False):
    st.dataframe(guardrail_table(), hide_index=True, width="stretch")
    for note in report.safety_notes:
        st.caption(note)
