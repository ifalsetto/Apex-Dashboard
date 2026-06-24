from __future__ import annotations

from apexops import db

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from .utils import load_config, now_iso


def project_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def cfg_path() -> Path:
    return project_dir() / "config.yaml"


def load_cfg():
    return load_config(cfg_path())


def con_from_cfg(cfg):
    con = db.connect(cfg.db_path)
    db.init_db(con)
    return con


def read_table(con, sql: str, params=()):
    return pd.read_sql_query(sql, con, params=params)


def pretty_settings(settings_json: str) -> Dict[str, Any]:
    try:
        return json.loads(settings_json) if settings_json else {}
    except Exception:
        return {}


st.set_page_config(page_title="ApexOps", layout="wide")

cfg = load_cfg()
con = con_from_cfg(cfg)

st.title("ApexOps – Apex performance + settings snapshots")

page = st.sidebar.selectbox(
    "Page",
    [
        "Status",
        "Captures",
        "Compare",
        "Match Log",
        "Edit Notes",
        "Export",
    ],
)


if page == "Status":
    st.subheader("Live config")
    st.code(cfg_path().read_text(encoding="utf-8", errors="ignore"), language="yaml")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("CapFrameX captures folder", str(cfg.capframex_dir))
    with c2:
        st.metric("Apex local config folder", str(cfg.apex_local_dir))
    with c3:
        st.metric("DB", str(cfg.db_path))

    runs = read_table(con, "SELECT * FROM runs ORDER BY start_at DESC LIMIT 25")
    st.subheader("Recent Apex runs")
    st.dataframe(runs, width="stretch")

    caps = read_table(con, "SELECT * FROM captures ORDER BY imported_at DESC LIMIT 50")
    st.subheader("Recent captures")
    st.dataframe(
        caps[[
            "imported_at",
            "test_name",
            "avg_fps",
            "fps_1_low",
            "fps_01_low",
            "win_hz",
            "profile_name",
            "display_mode",
            "capture_path",
        ]],
        width="stretch",
    )


elif page == "Captures":
    st.subheader("Filter + inspect captures")

    caps = read_table(con, "SELECT * FROM captures ORDER BY imported_at DESC")
    if caps.empty:
        st.info("No captures yet. Run the collector and record a CapFrameX capture.")
        st.stop()

    # Filters
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        profile = st.selectbox("Profile", ["(all)"] + sorted(caps["profile_name"].dropna().unique().tolist()))
    with f2:
        display = st.selectbox("Display mode", ["(all)"] + sorted(caps["display_mode"].dropna().unique().tolist()))
    with f3:
        hz = st.selectbox("Windows Hz", ["(all)"] + sorted([int(x) for x in caps["win_hz"].dropna().unique().tolist()]))
    with f4:
        name_search = st.text_input("Test name contains")

    filt = caps.copy()
    if profile != "(all)":
        filt = filt[filt["profile_name"] == profile]
    if display != "(all)":
        filt = filt[filt["display_mode"] == display]
    if hz != "(all)":
        filt = filt[filt["win_hz"] == hz]
    if name_search:
        filt = filt[filt["test_name"].str.contains(name_search, case=False, na=False)]

    st.write(f"Rows: {len(filt)}")

    show_cols = [
        "imported_at",
        "test_name",
        "avg_fps",
        "fps_1_low",
        "fps_01_low",
        "avg_ms",
        "p99_ms",
        "max_ms",
        "stutter8_pct",
        "win_hz",
        "notes",
    ]

    st.dataframe(filt[show_cols], width="stretch")

    # Charts
    st.subheader("Trends")
    chart_df = filt.sort_values("imported_at")
    st.line_chart(chart_df.set_index("imported_at")["avg_fps"], height=220)
    st.line_chart(chart_df.set_index("imported_at")["fps_1_low"], height=220)

    st.subheader("Inspect a capture")
    selected = st.selectbox(
        "Capture",
        chart_df["id"].tolist(),
        format_func=lambda cid: f"{cid} | {chart_df.loc[chart_df['id']==cid,'test_name'].iloc[0]} | {chart_df.loc[chart_df['id']==cid,'imported_at'].iloc[0]}",
    )
    row = chart_df[chart_df["id"] == selected].iloc[0].to_dict()

    c1, c2 = st.columns(2)
    with c1:
        st.json(pretty_settings(row.get("settings_json", "")))
    with c2:
        st.json({
            "videoconfig": pretty_settings(row.get("apex_video_json", "")),
            "settings_cfg": pretty_settings(row.get("apex_cfg_json", "")),
        })


elif page == "Compare":
    st.subheader("Compare two captures")

    caps = read_table(con, "SELECT id, imported_at, test_name, avg_fps, fps_1_low, fps_01_low, avg_ms, p99_ms, max_ms, stutter8_pct, win_hz, notes FROM captures ORDER BY imported_at DESC")
    if len(caps) < 2:
        st.info("Need at least 2 captures.")
        st.stop()

    def label(cid: str) -> str:
        r = caps[caps["id"] == cid].iloc[0]
        return f"{r['imported_at']} | {r['test_name']} | avg {r['avg_fps']:.1f} | 1% {r['fps_1_low']:.1f} | hz {r['win_hz']}"

    a, b = st.columns(2)
    with a:
        left = st.selectbox("Left", caps["id"].tolist(), format_func=label, key="cmp_left")
    with b:
        right = st.selectbox("Right", caps["id"].tolist(), format_func=label, index=1, key="cmp_right")

    left_row = caps[caps["id"] == left].iloc[0]
    right_row = caps[caps["id"] == right].iloc[0]

    metrics = ["avg_fps", "fps_1_low", "fps_01_low", "avg_ms", "p99_ms", "max_ms", "stutter8_pct", "win_hz"]
    comp = pd.DataFrame({
        "metric": metrics,
        "left": [left_row[m] for m in metrics],
        "right": [right_row[m] for m in metrics],
    })
    comp["delta (right-left)"] = comp["right"] - comp["left"]

    st.dataframe(comp, width="stretch")


elif page == "Match Log":
    st.subheader("Manual match logging (free, fast)")

    caps = read_table(con, "SELECT id, imported_at, test_name FROM captures ORDER BY imported_at DESC LIMIT 50")
    runs = read_table(con, "SELECT id, start_at FROM runs ORDER BY start_at DESC LIMIT 50")

    with st.form("match_form"):
        played_at = st.text_input("Played at (ISO)", value=now_iso())
        mode = st.text_input("Mode (Ranked/Pubs/Mixtape)", value="Ranked")
        map_name = st.text_input("Map", value="")
        ping_ms = st.number_input("Ping (ms)", min_value=0, max_value=999, value=0)
        kills = st.number_input("Kills", min_value=0, max_value=99, value=0)
        assists = st.number_input("Assists", min_value=0, max_value=99, value=0)
        damage = st.number_input("Damage", min_value=0, max_value=99999, value=0)
        placement = st.number_input("Placement", min_value=0, max_value=99, value=0)
        notes = st.text_area("Notes")

        run_id = st.selectbox("Link to run (optional)", [""] + runs["id"].tolist(), format_func=lambda x: x if x else "(none)")
        cap_id = st.selectbox("Link to capture (optional)", [""] + caps["id"].tolist(), format_func=lambda x: x if x else "(none)")

        submitted = st.form_submit_button("Save match")

    if submitted:
        row = {
            "id": str(uuid.uuid4()),
            "played_at": played_at,
            "mode": mode,
            "map": map_name,
            "ping_ms": int(ping_ms),
            "kills": int(kills),
            "assists": int(assists),
            "damage": int(damage),
            "placement": int(placement),
            "notes": notes,
            "run_id": run_id or None,
            "capture_id": cap_id or None,
            "settings_json": "",  # reserved
        }
        db.insert_match(con, row)
        st.success("Saved.")

    st.subheader("Recent matches")
    matches = read_table(con, "SELECT * FROM match_logs ORDER BY played_at DESC LIMIT 200")
    st.dataframe(matches, width="stretch")


elif page == "Edit Notes":
    st.subheader("Add notes to a capture")

    caps = read_table(con, "SELECT id, imported_at, test_name, notes FROM captures ORDER BY imported_at DESC")
    if caps.empty:
        st.info("No captures.")
        st.stop()

    def label(cid: str) -> str:
        r = caps[caps["id"] == cid].iloc[0]
        return f"{r['imported_at']} | {r['test_name']}"

    cap_id = st.selectbox("Capture", caps["id"].tolist(), format_func=label)
    current = caps[caps["id"] == cap_id].iloc[0]

    new_notes = st.text_area("Notes", value=current.get("notes") or "", height=120)
    if st.button("Save notes"):
        db.update_capture_notes(con, cap_id, new_notes)
        st.success("Updated.")


elif page == "Export":
    st.subheader("Export to CSV")

    caps = read_table(con, "SELECT * FROM captures ORDER BY imported_at DESC")
    matches = read_table(con, "SELECT * FROM match_logs ORDER BY played_at DESC")

    st.download_button(
        "Download captures.csv",
        data=caps.to_csv(index=False).encode("utf-8"),
        file_name="captures.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download matches.csv",
        data=matches.to_csv(index=False).encode("utf-8"),
        file_name="matches.csv",
        mime="text/csv",
    )

    st.info("Tip: drop these into Google Sheets for sharing/backup.")
