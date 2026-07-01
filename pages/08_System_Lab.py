import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# ------------------------------------------------------------
# Page Config
# ------------------------------------------------------------

st.set_page_config(
    page_title="System Lab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Optional Project Imports
# ------------------------------------------------------------

CONFIG_AVAILABLE = False
UTILS_AVAILABLE = False
IMPORTER_AVAILABLE = False
PSUTIL_AVAILABLE = False

config = None
safe_load_json = None
safe_save_json = None
collect_local_network_settings = None
apply_network_settings_to_profile = None

try:
    from apex_config import config as imported_config

    config = imported_config
    CONFIG_AVAILABLE = True
except Exception:
    CONFIG_AVAILABLE = False

try:
    from apex_utils import safe_load_json as imported_safe_load_json
    from apex_utils import safe_save_json as imported_safe_save_json

    safe_load_json = imported_safe_load_json
    safe_save_json = imported_safe_save_json
    UTILS_AVAILABLE = True
except Exception:
    UTILS_AVAILABLE = False

try:
    from apex_local_importer import (
        collect_local_network_settings as imported_collect_local_network_settings,
        apply_network_settings_to_profile as imported_apply_network_settings_to_profile,
    )

    collect_local_network_settings = imported_collect_local_network_settings
    apply_network_settings_to_profile = imported_apply_network_settings_to_profile
    IMPORTER_AVAILABLE = True
except Exception as exc:
    IMPORTER_AVAILABLE = False
    IMPORTER_IMPORT_ERROR = str(exc)

try:
    import psutil

    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False


# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------

st.markdown(
    """
<style>
:root {
    --ft-bg: #0E1117;
    --ft-panel: #16191F;
    --ft-panel-2: #1E222B;
    --ft-border: #2D333B;
    --ft-text: #E6EDF3;
    --ft-muted: #8B949E;
    --ft-green: #00FF9D;
    --ft-blue: #58A6FF;
    --ft-purple: #A371F7;
    --ft-yellow: #F2CC60;
    --ft-red: #FF6B6B;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(88, 166, 255, 0.10), transparent 32%),
        radial-gradient(circle at top right, rgba(163, 113, 247, 0.12), transparent 30%),
        var(--ft-bg);
    color: var(--ft-text);
}

[data-testid="stHeader"] {
    background: rgba(14, 17, 23, 0.70);
}

.block-container {
    padding-top: 1.2rem;
    max-width: 1500px;
}

.ft-hero {
    background: linear-gradient(135deg, rgba(22,25,31,0.96), rgba(30,34,43,0.88));
    border: 1px solid rgba(88,166,255,0.22);
    border-radius: 22px;
    padding: 24px;
    margin-bottom: 18px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.28);
}

.ft-title {
    font-size: 38px;
    font-weight: 900;
    letter-spacing: -0.8px;
    margin: 0;
}

.ft-subtitle {
    color: var(--ft-muted);
    font-size: 14px;
    margin-top: 6px;
}

.ft-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border-radius: 999px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 800;
    border: 1px solid rgba(0,255,157,0.35);
    color: var(--ft-green);
    background: rgba(0,255,157,0.08);
}

.ft-card {
    background: linear-gradient(180deg, rgba(22,25,31,0.96), rgba(14,17,23,0.96));
    border: 1px solid var(--ft-border);
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 16px 32px rgba(0,0,0,0.18);
}

.ft-card h3 {
    margin-top: 0;
    font-size: 15px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--ft-muted);
}

.ft-good { color: var(--ft-green); font-weight: 800; }
.ft-warn { color: var(--ft-yellow); font-weight: 800; }
.ft-bad { color: var(--ft-red); font-weight: 800; }
.ft-blue { color: var(--ft-blue); font-weight: 800; }
.ft-muted { color: var(--ft-muted); }

.ft-code {
    background: rgba(0,0,0,0.35);
    border: 1px solid rgba(88,166,255,0.22);
    border-radius: 14px;
    padding: 14px;
    font-family: Consolas, monospace;
    color: #D6E8FF;
    overflow-x: auto;
}

div[data-testid="stMetric"] {
    background: rgba(22,25,31,0.88);
    border: 1px solid var(--ft-border);
    padding: 16px;
    border-radius: 16px;
}

div[data-testid="stMetricValue"] {
    color: var(--ft-green);
    font-weight: 900;
}

.stButton > button {
    border-radius: 12px;
    border: 1px solid rgba(88,166,255,0.35);
    background: linear-gradient(135deg, #1F6FEB, #8957E5);
    color: white;
    font-weight: 800;
}

.stButton > button:hover {
    border-color: rgba(255,255,255,0.75);
    filter: brightness(1.08);
}

.stAlert {
    border-radius: 14px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

ROOT_DIR = Path.cwd()
DEFAULT_PROFILE_PATH = ROOT_DIR / "profile_autosave.json"


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_path(value: Any) -> Optional[Path]:
    if not value:
        return None

    try:
        return Path(str(value)).expanduser()
    except Exception:
        return None


def get_config_path_candidates() -> List[Path]:
    candidates: List[Path] = []

    if CONFIG_AVAILABLE and config is not None:
        possible_attrs = [
            "PROFILE_AUTOSAVE_PATH",
            "PROFILE_PATH",
            "PROFILE_FILE",
            "profile_autosave_path",
            "profile_path",
            "profile_file",
            "autosave_profile_path",
        ]

        for attr in possible_attrs:
            if hasattr(config, attr):
                candidate = normalize_path(getattr(config, attr))
                if candidate:
                    candidates.append(candidate)

    candidates.extend(
        [
            ROOT_DIR / "profile_autosave.json",
            ROOT_DIR / "Profiles" / "profile_autosave.json",
            ROOT_DIR / "Profiles" / "apex_competitive_profile.json",
            ROOT_DIR / "data" / "profile_autosave.json",
        ]
    )

    # Remove duplicates while preserving order.
    unique: List[Path] = []
    seen = set()
    for path in candidates:
        resolved = str(path)
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)

    return unique


def resolve_profile_path() -> Path:
    for path in get_config_path_candidates():
        if path.exists():
            return path

    return DEFAULT_PROFILE_PATH


PROFILE_PATH = resolve_profile_path()


def raw_load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if default is None:
        default = {}

    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

        return default
    except Exception:
        return default


def raw_save_json(path: Path, data: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

        return True, f"Saved {path}"
    except Exception as exc:
        return False, str(exc)


def load_profile(path: Path) -> Dict[str, Any]:
    if UTILS_AVAILABLE and safe_load_json is not None:
        try:
            result = safe_load_json(path, {})
            if isinstance(result, dict):
                return result
        except TypeError:
            try:
                result = safe_load_json(str(path), {})
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
        except Exception:
            pass

    return raw_load_json(path, default={})


def save_profile(path: Path, profile: Dict[str, Any]) -> Tuple[bool, str]:
    # Use raw JSON save intentionally because project safe_save_json signature
    # may vary across versions. This page should not crash over helper mismatch.
    return raw_save_json(path, profile)


def process_names() -> List[str]:
    if not PSUTIL_AVAILABLE:
        return []

    names: List[str] = []

    try:
        for proc in psutil.process_iter(["name"]):
            name = proc.info.get("name")
            if name:
                names.append(name.lower())
    except Exception:
        return names

    return names


def is_process_running(match_terms: List[str]) -> bool:
    names = process_names()

    for name in names:
        for term in match_terms:
            if term.lower() in name:
                return True

    return False


def get_system_snapshot() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "timestamp": now_stamp(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cwd": str(ROOT_DIR),
        "profile_path": str(PROFILE_PATH),
        "config_available": CONFIG_AVAILABLE,
        "utils_available": UTILS_AVAILABLE,
        "importer_available": IMPORTER_AVAILABLE,
        "psutil_available": PSUTIL_AVAILABLE,
    }

    if PSUTIL_AVAILABLE:
        try:
            snapshot["cpu_percent"] = psutil.cpu_percent(interval=0.2)
            snapshot["memory_percent"] = psutil.virtual_memory().percent
            snapshot["disk_c_percent"] = psutil.disk_usage("C:\\").percent
            snapshot["steam_running"] = is_process_running(["steam.exe", "steamservice.exe", "steamwebhelper.exe"])
            snapshot["apex_running"] = is_process_running(["r5apex.exe", "r5apex_dx12.exe"])
        except Exception as exc:
            snapshot["psutil_error"] = str(exc)
    else:
        snapshot["steam_running"] = False
        snapshot["apex_running"] = False

    return snapshot


def run_command(command: List[str], timeout: int = 10) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }


def get_dns_cache_status() -> Dict[str, Any]:
    # Read-only diagnostic. Does not flush or change DNS.
    return run_command(["ipconfig", "/displaydns"], timeout=8)


def safe_collect_network() -> Tuple[bool, Dict[str, Any], str]:
    if not IMPORTER_AVAILABLE or collect_local_network_settings is None:
        message = "apex_local_importer network collector is unavailable."
        if "IMPORTER_IMPORT_ERROR" in globals():
            message += f" Import error: {IMPORTER_IMPORT_ERROR}"
        return False, {}, message

    try:
        imported_network = collect_local_network_settings(redact_local_ids=True)

        if not isinstance(imported_network, dict):
            return False, {}, "Network collector returned non-dict data."

        return True, imported_network, "Network settings collected successfully."
    except TypeError:
        try:
            imported_network = collect_local_network_settings()

            if not isinstance(imported_network, dict):
                return False, {}, "Network collector returned non-dict data."

            return True, imported_network, "Network settings collected successfully."
        except Exception as exc:
            return False, {}, str(exc)
    except Exception as exc:
        return False, {}, str(exc)


def safe_apply_network(profile: Dict[str, Any], imported_network: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
    if not IMPORTER_AVAILABLE or apply_network_settings_to_profile is None:
        return False, profile, "apex_local_importer network applier is unavailable."

    try:
        updated = apply_network_settings_to_profile(profile, imported_network)

        if not isinstance(updated, dict):
            return False, profile, "Network applier returned non-dict profile."

        return True, updated, "Network settings applied to profile."
    except Exception as exc:
        return False, profile, str(exc)


def ensure_profile_shape(profile: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(profile, dict):
        profile = {}

    profile.setdefault("metadata", {})
    profile.setdefault("system_lab", {})
    profile.setdefault("launch_options", {})
    profile.setdefault("local_system", {})

    profile["metadata"].setdefault("app", "Apex Dashboard")
    profile["metadata"].setdefault("last_opened_by", "08_System_Lab.py")
    profile["metadata"]["last_touched"] = now_stamp()

    profile["launch_options"].setdefault("steam_flags", ["-novid", "+fps_max 237"])
    profile["launch_options"].setdefault("fps_cap", 237)
    profile["launch_options"].setdefault("refresh_rate_hz", 240)
    profile["launch_options"].setdefault("profile_name", "Apex - Competitive")

    return profile


def update_launch_profile(
    profile: Dict[str, Any],
    profile_name: str,
    refresh_rate_hz: int,
    fps_cap: int,
    enabled_flags: List[str],
) -> Dict[str, Any]:
    profile = ensure_profile_shape(profile)

    profile["launch_options"]["profile_name"] = profile_name
    profile["launch_options"]["refresh_rate_hz"] = refresh_rate_hz
    profile["launch_options"]["fps_cap"] = fps_cap
    profile["launch_options"]["steam_flags"] = enabled_flags
    profile["metadata"]["last_touched"] = now_stamp()

    return profile


def flag_status(flag: str) -> Tuple[str, str]:
    safe_defaults = {
        "-novid": ("Recommended", "Skips intro video. Safe."),
        "+fps_max 237": ("Recommended", "Good cap for 240Hz display with low latency margin."),
        "+fps_max 240": ("Test Only", "Matches monitor, but 237 often leaves better frame pacing margin."),
        "+fps_max 225": ("Fallback", "Good if 237/240 is not stable."),
        "+fps_max 180": ("Fallback", "Stable fallback if frametime spikes happen."),
    }

    avoid_defaults = {
        "+fps_max 0": ("Avoid Default", "Uncapped FPS can increase heat, power, and frametime variance."),
        "-dev": ("Avoid Default", "Do not use as a normal competitive default unless testing."),
        "+m_rawinput 1": ("Obsolete / Verify", "Apex uses raw input behavior internally; do not rely on this as a magic fix."),
    }

    if flag in safe_defaults:
        return safe_defaults[flag]

    if flag in avoid_defaults:
        return avoid_defaults[flag]

    return "Unknown", "Only use if you have tested it and logged the result."


# ------------------------------------------------------------
# Session State
# ------------------------------------------------------------

if "profile" not in st.session_state:
    st.session_state.profile = ensure_profile_shape(load_profile(PROFILE_PATH))

if "imported_network" not in st.session_state:
    st.session_state.imported_network = {}

if "last_collect_status" not in st.session_state:
    st.session_state.last_collect_status = None

if "last_save_status" not in st.session_state:
    st.session_state.last_save_status = None


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

snapshot = get_system_snapshot()

steam_status = bool(snapshot.get("steam_running"))
apex_status = bool(snapshot.get("apex_running"))

status_text = "READY"
status_class = "ft-good"

if not IMPORTER_AVAILABLE:
    status_text = "IMPORTER LIMITED"
    status_class = "ft-warn"

st.markdown(
    f"""
<div class="ft-hero">
    <div style="display:flex; align-items:center; justify-content:space-between; gap:18px;">
        <div>
            <h1 class="ft-title">System Lab</h1>
            <div class="ft-subtitle">
                Local diagnostics • Steam profile control • network import • safe profile writer
            </div>
        </div>
        <div class="ft-pill">
            <span class="{status_class}">{status_text}</span>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Top Metrics
# ------------------------------------------------------------

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Steam", "Running" if steam_status else "Not Running")

with m2:
    st.metric("Apex", "Live" if apex_status else "Waiting")

with m3:
    cpu_value = snapshot.get("cpu_percent", "N/A")
    st.metric("CPU Load", f"{cpu_value}%" if isinstance(cpu_value, (int, float)) else cpu_value)

with m4:
    memory_value = snapshot.get("memory_percent", "N/A")
    st.metric("Memory", f"{memory_value}%" if isinstance(memory_value, (int, float)) else memory_value)


# ------------------------------------------------------------
# Warnings
# ------------------------------------------------------------

if not IMPORTER_AVAILABLE:
    st.warning(
        "Network importer is limited or unavailable. This page will still run, but the import/apply buttons may be disabled."
    )

    if "IMPORTER_IMPORT_ERROR" in globals():
        st.code(IMPORTER_IMPORT_ERROR, language="text")

if not PROFILE_PATH.exists():
    st.info(
        f"No profile file exists yet at `{PROFILE_PATH}`. Saving from this page will create it."
    )


# ------------------------------------------------------------
# Tabs
# ------------------------------------------------------------

tab_dashboard, tab_network, tab_launch, tab_profile, tab_tools = st.tabs(
    [
        "Dashboard",
        "Network Import",
        "Launch Configuration",
        "Profile JSON",
        "Tools",
    ]
)


# ------------------------------------------------------------
# Dashboard Tab
# ------------------------------------------------------------

with tab_dashboard:
    left, right = st.columns([1, 1])

    with left:
        st.markdown(
            """
<div class="ft-card">
    <h3>Local System</h3>
    <p><span class="ft-muted">This is read-only status. It does not modify Windows, Steam, Apex, DNS, registry, drivers, services, or firewall rules.</span></p>
</div>
""",
            unsafe_allow_html=True,
        )

        st.json(snapshot)

    with right:
        profile = ensure_profile_shape(st.session_state.profile)
        launch = profile.get("launch_options", {})

        st.markdown(
            """
<div class="ft-card">
    <h3>Current Profile Summary</h3>
</div>
""",
            unsafe_allow_html=True,
        )

        st.metric("Profile", launch.get("profile_name", "Apex - Competitive"))
        st.metric("Refresh Rate", f"{launch.get('refresh_rate_hz', 240)} Hz")
        st.metric("FPS Cap", launch.get("fps_cap", 237))
        st.write("Steam Flags:")
        st.code(" ".join(launch.get("steam_flags", ["-novid", "+fps_max 237"])), language="text")


# ------------------------------------------------------------
# Network Import Tab
# ------------------------------------------------------------

with tab_network:
    st.subheader("Network Import")

    st.write(
        "Collect local network settings, review them, then apply them to your profile JSON. "
        "This does not change router settings or Windows network configuration."
    )

    c1, c2, c3 = st.columns([1, 1, 2])

    with c1:
        collect_clicked = st.button(
            "Collect Network Settings",
            disabled=not IMPORTER_AVAILABLE,
            use_container_width=True,
        )

    with c2:
        apply_clicked = st.button(
            "Apply To Profile",
            disabled=not IMPORTER_AVAILABLE,
            use_container_width=True,
        )

    if collect_clicked:
        ok, imported_network, message = safe_collect_network()
        st.session_state.last_collect_status = (ok, message)

        if ok:
            st.session_state.imported_network = imported_network
            st.success(message)
        else:
            st.error(message)

    if apply_clicked:
        if not st.session_state.imported_network:
            st.warning("Collect network settings first before applying.")
        else:
            ok, updated_profile, message = safe_apply_network(
                st.session_state.profile,
                st.session_state.imported_network,
            )

            if ok:
                updated_profile = ensure_profile_shape(updated_profile)
                updated_profile["local_system"]["last_network_import"] = now_stamp()
                st.session_state.profile = updated_profile

                saved, save_message = save_profile(PROFILE_PATH, updated_profile)
                st.session_state.last_save_status = (saved, save_message)

                if saved:
                    st.success(f"{message} {save_message}")
                else:
                    st.error(f"{message} But save failed: {save_message}")
            else:
                st.error(message)

    if st.session_state.last_collect_status:
        ok, message = st.session_state.last_collect_status
        if ok:
            st.success(message)
        else:
            st.error(message)

    if st.session_state.imported_network:
        st.markdown("### Imported Network Data")
        st.json(st.session_state.imported_network)
    else:
        st.info("No network data collected yet.")


# ------------------------------------------------------------
# Launch Configuration Tab
# ------------------------------------------------------------

with tab_launch:
    st.subheader("Steam Launch Configuration")

    profile = ensure_profile_shape(st.session_state.profile)
    launch = profile.get("launch_options", {})

    default_profile_name = str(launch.get("profile_name", "Apex - Competitive"))
    default_refresh = int(launch.get("refresh_rate_hz", 240))
    default_fps_cap = int(launch.get("fps_cap", 237))
    current_flags = launch.get("steam_flags", ["-novid", "+fps_max 237"])

    left, right = st.columns([1, 1])

    with left:
        profile_name = st.text_input("Profile Name", default_profile_name)
        refresh_rate_hz = st.slider("Monitor Refresh Rate", 60, 360, default_refresh, step=5)
        fps_cap = st.number_input("FPS Cap", min_value=0, max_value=500, value=default_fps_cap, step=1)

        st.info(
            "For your 240Hz OLED, start with 237 FPS. Test 240, 225, and 180 only if frame pacing feels off."
        )

    with right:
        st.write("Recommended / Test Flags")

        available_flags = [
            "-novid",
            "+fps_max 237",
            "+fps_max 240",
            "+fps_max 225",
            "+fps_max 180",
            "+fps_max 0",
            "-dev",
            "+m_rawinput 1",
        ]

        enabled_flags: List[str] = []

        for flag in available_flags:
            default_enabled = flag in current_flags

            # Enforce safer default if no existing flags are present.
            if not current_flags and flag in ["-novid", "+fps_max 237"]:
                default_enabled = True

            checked = st.checkbox(flag, value=default_enabled, key=f"flag_{flag}")

            label, note = flag_status(flag)
            st.caption(f"{label}: {note}")

            if checked:
                enabled_flags.append(flag)

    save_launch_clicked = st.button("Save Launch Profile", use_container_width=True)

    if save_launch_clicked:
        updated_profile = update_launch_profile(
            st.session_state.profile,
            profile_name=profile_name,
            refresh_rate_hz=refresh_rate_hz,
            fps_cap=fps_cap,
            enabled_flags=enabled_flags,
        )

        st.session_state.profile = updated_profile
        saved, message = save_profile(PROFILE_PATH, updated_profile)

        if saved:
            st.success(message)
        else:
            st.error(message)

    st.markdown("### Steam Launch Options Output")

    steam_output = " ".join(enabled_flags) if enabled_flags else "-novid +fps_max 237"

    st.markdown(
        f"""
<div class="ft-code">{steam_output}</div>
""",
        unsafe_allow_html=True,
    )

    if "+fps_max 0" in enabled_flags:
        st.warning(
            "`+fps_max 0` is enabled. I would not use uncapped FPS as your default for competitive stability."
        )

    if "-dev" in enabled_flags:
        st.warning(
            "`-dev` is enabled. Do not use this as your normal competitive default unless you are testing something specific."
        )


# ------------------------------------------------------------
# Profile JSON Tab
# ------------------------------------------------------------

with tab_profile:
    st.subheader("Profile JSON")

    st.write(f"Resolved profile path:")

    st.code(str(PROFILE_PATH), language="text")

    reload_col, save_col = st.columns([1, 1])

    with reload_col:
        if st.button("Reload Profile From Disk", use_container_width=True):
            st.session_state.profile = ensure_profile_shape(load_profile(PROFILE_PATH))
            st.success("Profile reloaded.")

    with save_col:
        if st.button("Save Current Profile To Disk", use_container_width=True):
            saved, message = save_profile(PROFILE_PATH, ensure_profile_shape(st.session_state.profile))
            if saved:
                st.success(message)
            else:
                st.error(message)

    st.json(ensure_profile_shape(st.session_state.profile))


# ------------------------------------------------------------
# Tools Tab
# ------------------------------------------------------------

with tab_tools:
    st.subheader("Read-Only Tools")

    st.write(
        "These tools are diagnostic only. No delete, registry, driver, firewall, service, adapter, DNS-change, or BIOS operations are performed."
    )

    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("Refresh System Snapshot", use_container_width=True):
            st.rerun()

    with c2:
        if st.button("Check DNS Cache Availability", use_container_width=True):
            dns_result = get_dns_cache_status()
            st.session_state.dns_result = dns_result

    if "dns_result" in st.session_state:
        result = st.session_state.dns_result

        if result.get("ok"):
            st.success("DNS cache command ran successfully.")
        else:
            st.warning("DNS cache command failed or timed out.")

        with st.expander("DNS Command Output", expanded=False):
            st.code(result.get("stdout", ""), language="text")
            if result.get("stderr"):
                st.code(result.get("stderr", ""), language="text")

    st.markdown("### Launch Command")

    st.code(
        "cd C:\\FalseTech\\Projects\\Apex-Dashboard\n"
        ".\\.venv\\Scripts\\activate\n"
        "streamlit run apex_dashboard.py",
        language="powershell",
    )

    st.markdown("### Safety Notes")

    st.markdown(
        """
1. This page does not modify Windows services.
2. This page does not modify registry keys.
3. This page does not touch Easy Anti-Cheat.
4. This page does not read or inject Apex memory.
5. This page does not change DNS, IP, adapter, firewall, or router settings.
6. Profile changes only write to the local JSON profile file.
"""
    )