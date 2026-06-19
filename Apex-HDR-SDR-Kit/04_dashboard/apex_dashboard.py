import json
import datetime as dt
from dataclasses import dataclass, asdict
import streamlit as st

APP_TITLE = "Apex Optimizer Dashboard"

DEFAULT_PROFILE = {
    "meta": {
        "profileName": "Apex - Competitive",
        "lastUpdatedISO": dt.datetime.now().isoformat(timespec="seconds"),
        "monitor": "ASUS ROG XG27AQDMG OLED 240Hz",
        "gpu": "RTX 5070 Ti",
        "os": "Windows 11",
        "notes": "OLED + 240Hz. Focus: clarity + low latency + repeatable presets.",
    },
    "targets": {
        "refreshHz": 240,
        "fpsTarget": 237,
        "latencyGoalMs": 10,
    },
    "toggles": {
        "hdrWindowsOn": True,
        "autoHdrOn": True,
        "rtxHdrOn": False,
        "gsyncOn": True,
        "vsyncInGameOff": True,
        "reflexBoostOn": True,
    },
    "launchOptions": [
        {"key": "-novid", "enabled": True, "note": "Skip intro videos"},
        {"key": "-dev", "enabled": True, "note": "Skip more startup animations"},
        {"key": "+fps_max 0", "enabled": True, "note": "Uncap FPS (cap via Reflex/RTSS if desired)"},
        {"key": "+lobby_max_fps 0", "enabled": True, "note": "Uncap lobby/menu FPS"},
        {"key": "-no_render_on_input_thread", "enabled": True, "note": "Threading stability on some rigs"},
        {"key": "+m_rawinput 1", "enabled": True, "note": "Raw mouse input"},
        {"key": "-refresh 240", "enabled": False, "note": "Force 240Hz at launch (only if needed)"},
        {"key": "+mat_no_stretching 1", "enabled": True, "note": "Prevent stretching"},
        {"key": "+clip_mouse_to_letterbox 0", "enabled": True, "note": "Cursor behavior with letterbox"},
    ],
    "hdrSetup": {
        "windows": [
            "Settings → System → Display → Use HDR = ON",
            "Auto HDR = ON (tune per-title via Win+G)",
            "SDR brightness (in HDR) = ~35–40% for desktop readability",
            "Run Windows HDR Calibration and save profile",
        ],
        "nvidia": [
            "NVIDIA Control Panel → Change Resolution: RGB, Full, 10 bpc (if available)",
            "G-SYNC ON; V-Sync OFF globally (game V-Sync OFF)",
            "Avoid heavy filters; clarity > cosmetics",
        ],
        "monitor": [
            "Use DisplayPort",
            "DSC = ON/Auto (for 240Hz + 10-bit HDR headroom)",
            "OLED care features = ON",
            "Disable extra dynamic contrast modes; keep consistent tone mapping",
        ],
        "apexBehavior": [
            "Apex has no native HDR toggle; Windows HDR/Auto HDR affects tone mapping",
            "Use Win+G → HDR intensity to avoid gray fog while keeping shadow detail",
        ],
    },
    "presets": {
        "hdr_on_comp": {
            "name": "HDR ON – Competitive (Auto HDR)",
            "windows": {"HDR": "ON", "Auto HDR": "ON", "SDR Brightness (HDR mode)": "35–40%"},
            "nvidia": {"RTX HDR": "OFF", "RGB Range": "Full", "G-SYNC": "ON", "V-Sync Global": "OFF"},
            "apex": {
                "Display Mode": "Fullscreen (preferred)",
                "V-Sync": "OFF",
                "NVIDIA Reflex": "ON + Boost",
                "Adaptive Resolution": "OFF",
                "Anti-Aliasing": "OFF",
                "Ambient Occlusion": "OFF",
                "Shadows": "LOW/OFF",
                "Volumetric": "OFF",
                "Effects": "LOW",
                "Ragdolls": "LOW",
                "Color Blind": "Deuteranopia (mild) if it helps target pop",
            },
        },
        "hdr_off_comp": {
            "name": "HDR OFF – Competitive (SDR Baseline)",
            "windows": {"HDR": "OFF", "Auto HDR": "OFF", "SDR Brightness (HDR mode)": "N/A"},
            "nvidia": {"RTX HDR": "OFF", "RGB Range": "Full", "G-SYNC": "ON", "V-Sync Global": "OFF"},
            "apex": {
                "Display Mode": "Fullscreen",
                "V-Sync": "OFF",
                "NVIDIA Reflex": "ON + Boost",
                "Adaptive Resolution": "OFF",
                "Anti-Aliasing": "OFF",
                "Ambient Occlusion": "OFF",
                "Shadows": "LOW/OFF",
                "Volumetric": "OFF",
                "Effects": "LOW",
                "Ragdolls": "LOW",
                "Color Blind": "Optional",
            },
        },
    },
    "futureModules": [
        "OBS / Capture Setup",
        "Sensitivity Tracking",
        "Loadouts / TTK Tools",
        "Patch Notes Highlights",
    ],
}

def now_iso():
    return dt.datetime.now().isoformat(timespec="seconds")

def build_launch_string(launch_options):
    return " ".join([x["key"].strip() for x in launch_options if x.get("enabled")])

def bump_updated(profile):
    profile["meta"]["lastUpdatedISO"] = now_iso()
    return profile

# ---------- Streamlit App ----------
st.set_page_config(page_title=APP_TITLE, layout="wide")

if "profile" not in st.session_state:
    st.session_state.profile = json.loads(json.dumps(DEFAULT_PROFILE))

profile = st.session_state.profile

st.title(APP_TITLE)
st.caption(
    f"Profile: **{profile['meta']['profileName']}** • "
    f"Monitor: **{profile['meta']['monitor']}** • GPU: **{profile['meta']['gpu']}** • "
    f"Updated: **{profile['meta']['lastUpdatedISO']}**"
)

# Top actions
colA, colB, colC, colD = st.columns([2, 1, 1, 1])
with colA:
    profile["meta"]["profileName"] = st.text_input("Profile name", profile["meta"]["profileName"])
with colB:
    if st.button("Reset to Default", use_container_width=True):
        st.session_state.profile = json.loads(json.dumps(DEFAULT_PROFILE))
        st.rerun()
with colC:
    exported = json.dumps(profile, indent=2)
    st.download_button(
        "Export JSON",
        data=exported,
        file_name=f"apex_profile_{profile['meta']['profileName'].replace(' ', '_').lower()}.json",
        mime="application/json",
        use_container_width=True,
    )
with colD:
    uploaded = st.file_uploader("Import JSON", type=["json"], label_visibility="collapsed")
    if uploaded:
        try:
            st.session_state.profile = json.loads(uploaded.read().decode("utf-8"))
            st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")

st.divider()

# Performance Targets
st.subheader("Performance Targets")
t1, t2, t3 = st.columns(3)
with t1:
    profile["targets"]["refreshHz"] = st.number_input("Refresh (Hz)", min_value=60, max_value=360, value=profile["targets"]["refreshHz"], step=1)
with t2:
    profile["targets"]["fpsTarget"] = st.number_input("FPS Target", min_value=60, max_value=600, value=profile["targets"]["fpsTarget"], step=1)
with t3:
    profile["targets"]["latencyGoalMs"] = st.number_input("Latency Goal (ms)", min_value=1, max_value=100, value=profile["targets"]["latencyGoalMs"], step=1)

st.divider()

# Toggles
st.subheader("System Toggles")
g1, g2, g3 = st.columns(3)
with g1:
    profile["toggles"]["hdrWindowsOn"] = st.toggle("Windows HDR", profile["toggles"]["hdrWindowsOn"])
    profile["toggles"]["autoHdrOn"] = st.toggle("Auto HDR", profile["toggles"]["autoHdrOn"])
with g2:
    profile["toggles"]["rtxHdrOn"] = st.toggle("RTX HDR", profile["toggles"]["rtxHdrOn"])
    profile["toggles"]["gsyncOn"] = st.toggle("G-SYNC / VRR", profile["toggles"]["gsyncOn"])
with g3:
    profile["toggles"]["vsyncInGameOff"] = st.toggle("In-game V-Sync OFF", profile["toggles"]["vsyncInGameOff"])
    profile["toggles"]["reflexBoostOn"] = st.toggle("Reflex (+Boost)", profile["toggles"]["reflexBoostOn"])

st.divider()

# Launch Options
st.subheader("Steam Launch Options")
left, right = st.columns([2, 1])
with left:
    for i, opt in enumerate(profile["launchOptions"]):
        c1, c2, c3 = st.columns([1, 2, 3])
        with c1:
            profile["launchOptions"][i]["enabled"] = st.checkbox(opt["key"], opt["enabled"], key=f"lo_{i}")
        with c2:
            st.code(opt["key"], language="text")
        with c3:
            st.caption(opt.get("note", ""))

launch_string = build_launch_string(profile["launchOptions"])
with right:
    st.caption("Current launch string")
    st.code(launch_string if launch_string else "(none)", language="text")
    st.download_button("Download launch.txt", data=launch_string, file_name="apex_launch_options.txt", use_container_width=True)

st.divider()

# HDR Setup Checklist
st.subheader("HDR Setup Checklist")
w, n, m = st.columns(3)
with w:
    st.markdown("### Windows")
    for x in profile["hdrSetup"]["windows"]:
        st.write(f"- {x}")
with n:
    st.markdown("### NVIDIA")
    for x in profile["hdrSetup"]["nvidia"]:
        st.write(f"- {x}")
with m:
    st.markdown("### Monitor")
    for x in profile["hdrSetup"]["monitor"]:
        st.write(f"- {x}")
st.markdown("### Apex Behavior")
for x in profile["hdrSetup"]["apexBehavior"]:
    st.write(f"- {x}")

st.divider()

# Presets
st.subheader("Competitive Presets")
preset_keys = list(profile["presets"].keys())
preset_labels = [profile["presets"][k]["name"] for k in preset_keys]

sel = st.radio("Choose preset", options=preset_keys, format_func=lambda k: profile["presets"][k]["name"], horizontal=True)

p = profile["presets"][sel]
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### Windows")
    st.json(p["windows"])
with c2:
    st.markdown("### NVIDIA")
    st.json(p["nvidia"])
with c3:
    st.markdown("### Apex")
    st.json(p["apex"])

st.divider()

# Future modules
with st.expander("Future Modules (Reserved)"):
    for x in profile["futureModules"]:
        st.write(f"- {x}")

# Finalize
st.session_state.profile = bump_updated(profile)
