"""Apex Optimizer Dashboard - Refactored main application."""
import json
import os
import csv
import hashlib
import datetime as dt
import platform
import subprocess
import re
import time
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from streamlit_autorefresh import st_autorefresh
import streamlit as st
from apex_api_status import render_api_status_panel

# Import refactored modules
from apex_config import config, Config
from apex_logging import setup_logging
from apex_utils import (
    now_iso,
    deep_copy,
    safe_load_json,
    safe_save_json,
    slug,
    profile_hash,
    bytes_human,
    safe_metric_comparison,
    validate_refresh_hz,
    validate_fps_target,
)
from apex_validation import validate_profile_structure, safe_int, safe_float
from apex_types import Profile, MonitorState, PerformanceLog

# Setup logging
logger = setup_logging(config.DAILY_TEMP_DIR)
logger.info("Apex Dashboard started")

# Ensure directories exist
config.ensure_directories()

# -------------------- App Identity --------------------
APP_TITLE = config.APP_TITLE
APP_VERSION = config.APP_VERSION
REPO_URL = config.REPO_URL
BUG_URL = f"{REPO_URL}/issues/new?template=bug_report.yml"
FEATURE_URL = f"{REPO_URL}/issues/new?template=feature_request.yml"

# Path variables for backward compatibility
BASE_DIR = str(config.BASE_DIR)
SNAP_DIR = str(config.SNAP_DIR)
SCAN_DIR = str(config.SCAN_DIR)
EXPORT_DIR = str(config.EXPORT_DIR)
PROFILES_DIR = str(config.PROFILES_DIR)
TEMPBIN_DIR = str(config.TEMPBIN_DIR)
DAILY_TEMP_DIR = str(config.DAILY_TEMP_DIR)
TRASHBIN_DIR = str(config.TRASHBIN_DIR)
TRASH_TODAY_DIR = str(config.TRASH_TODAY_DIR)
STORAGE_DIR = str(config.STORAGE_DIR)
STORAGE_MAP_JSON = str(config.STORAGE_MAP_JSON)
STORAGE_MAP_CSV = str(config.STORAGE_MAP_CSV)
INDEX_PATH = str(config.INDEX_PATH)
AUTOSAVE_PATH = str(config.AUTOSAVE_PATH)

# -------------------- Defaults (PUBLIC-SAFE) --------------------
DEFAULT_PROFILE: Profile = {
    "meta": {
        "profileName": "Apex - Competitive (Generic)",
        "lastUpdatedISO": dt.datetime.now().isoformat(timespec="seconds"),
        "monitor": "Unknown / User provided",
        "gpu": "Unknown / User provided",
        "os": platform.system(),
        "notes": "Public-safe defaults. Tune per user + log sessions.",
    },
    "targets": {"refreshHz": 240, "fpsTarget": 237, "latencyGoalMs": 10},
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
        {"key": "-dev", "enabled": True, "note": "Skip some startup behavior (patch dependent)"},
        {"key": "+fps_max 0", "enabled": True, "note": "Uncap engine FPS (cap elsewhere if desired)"},
        {"key": "+lobby_max_fps 0", "enabled": True, "note": "Uncap lobby/menu FPS"},
        {"key": "-no_render_on_input_thread", "enabled": True, "note": "Threading behavior (system/patch dependent)"},
        {"key": "+m_rawinput 1", "enabled": True, "note": "Raw mouse input"},
        {"key": "-refresh 240", "enabled": False, "note": "Force refresh at launch (only if needed)"},
        {"key": "+mat_no_stretching 1", "enabled": True, "note": "Prevent stretching on aspect changes"},
        {"key": "+clip_mouse_to_letterbox 0", "enabled": True, "note": "Cursor behavior with letterbox"},
    ],
    "hdrSetup": {
        "windows": [
            "Settings → System → Display → Use HDR = ON",
            "Auto HDR = ON (tune per-title via Win+G if available)",
            "SDR brightness (in HDR) start ≈ 35–40% for desktop readability",
            "Run Windows HDR Calibration and save the profile",
        ],
        "nvidia": [
            "NVIDIA Control Panel → Change Resolution: RGB, Full, 10 bpc (if available)",
            "G-SYNC ON; V-Sync OFF globally; in-game V-Sync OFF",
            "Avoid heavy filters; prioritize clarity",
        ],
        "monitor": [
            "Use DisplayPort when possible",
            "DSC = ON/Auto if required for high Hz + HDR bandwidth",
            "OLED care features = ON",
            "Disable extra dynamic contrast; keep tone mapping consistent",
        ],
        "apexBehavior": [
            "Apex has no native HDR toggle; Windows HDR/Auto HDR affects tone mapping",
            "Use Win+G HDR intensity until shadows separate without gray haze",
        ],
    },
    "presets": {
        "HDR ON (Auto HDR) – Competitive": {
            "Windows": {"HDR": "ON", "Auto HDR": "ON", "SDR brightness in HDR": "35–40%"},
            "NVIDIA": {"RTX HDR": "OFF", "RGB Range": "Full", "10 bpc": "If available", "G-SYNC": "ON", "V-Sync Global": "OFF"},
            "Apex": {"Fullscreen": "Yes", "V-Sync": "OFF", "Reflex": "ON+Boost", "AA": "OFF", "AO": "OFF", "Shadows": "LOW/OFF"},
        },
        "HDR OFF (SDR) – Competitive": {
            "Windows": {"HDR": "OFF", "Auto HDR": "OFF"},
            "NVIDIA": {"RTX HDR": "OFF", "RGB Range": "Full", "G-SYNC": "ON", "V-Sync Global": "OFF"},
            "Apex": {"Fullscreen": "Yes", "V-Sync": "OFF", "Reflex": "ON+Boost", "AA": "OFF", "AO": "OFF", "Shadows": "LOW/OFF"},
        },
    },
    "performanceLogs": [],
    "network": {
        "connection": "Ethernet",
        "dns": "Auto",
        "router_model": "",
        "modem_model": "",
        "mtu": "",
        "qos_enabled": "",
        "bufferbloat_grade": "",
        "isp": "",
        "notes": "",
        "tests": {
            "speedtest_down_mbps": "",
            "speedtest_up_mbps": "",
            "speedtest_ping_ms": "",
            "jitter_ms": "",
            "packet_loss_pct": "",
        },
    },
    "privacy": {
        "sanitize_exports": True,
        "redact_user_paths": True,
        "redact_machine_name": True,
    },
}

# -------------------- Libraries --------------------
SETTING_LIBRARY = {
    "windows_hdr": {
        "title": "Windows HDR (Use HDR)",
        "what_it_does": "Switches Windows output pipeline from SDR to HDR (PQ). Changes tone mapping and luminance handling.",
        "interactions": ["Auto HDR requires Windows HDR ON.", "RTX HDR requires Windows HDR ON."],
        "pros": ["Enables HDR pipeline", "Potentially better highlight detail/depth on OLED"],
        "cons": ["Can look washed if not calibrated", "Desktop may appear different vs SDR"],
        "negatives": ["Gray fog/raised blacks if calibration/intensity is wrong"],
        "sop": [
            "Settings → System → Display → select monitor",
            "Use HDR = ON (or OFF for SDR baseline)",
            "HDR settings: SDR brightness (in HDR) start 35–40%",
            "Run Windows HDR Calibration",
        ],
        "scop": {"affects": ["Desktop tone mapping", "Game tone mapping"], "risk_level": "Medium", "rollback": ["HDR OFF"], "verify": ["No gray haze in shadows"]},
    },
}

LAUNCH_OPTION_LIBRARY = {
    "-novid": {"title": "-novid", "what_it_does": "Skips intro videos.", "interactions": ["None."], "pros": ["Faster boot."], "cons": ["None."], "negatives": ["None."],
              "sop": ["Enable -novid.", "Launch once to verify."], "scop": {"affects": ["Startup"], "risk_level": "Low", "rollback": ["Disable flag"], "verify": ["Launch normal"]}},
    "-dev": {"title": "-dev", "what_it_does": "Skips some startup behavior (varies).", "interactions": ["Pairs with -novid."], "pros": ["Often faster startup."], "cons": ["Patch dependent."],
             "negatives": ["Can behave differently after updates."], "sop": ["Enable -dev.", "Launch twice to verify."], "scop": {"affects": ["Startup"], "risk_level": "Low–Medium", "rollback": ["Disable flag"], "verify": ["Launch normal"]}},
    "+fps_max 0": {"title": "+fps_max 0", "what_it_does": "Uncaps in-engine FPS cap (0 = uncapped).", "interactions": ["Still cap below refresh (237 @ 240Hz)."], "pros": ["Lets you cap elsewhere."],
                   "cons": ["More heat/power if uncapped."], "negatives": ["VRR ceiling issues if no cap."], "sop": ["Enable +fps_max 0.", "Cap to 237 using ONE method.", "Test+log."],
                   "scop": {"affects": ["FPS behavior", "thermals"], "risk_level": "Medium", "rollback": ["Disable or set fixed cap"], "verify": ["Stable cap"]}},
}

# -------------------- Friendly UI Labels --------------------
UI = {
    "tabs": {
        "apex": "Setup",
        "match": "Auto Match Log",
        "hdr": "HDR Guide",
        "presets": "Presets",
        "perf": "Match History",
        "net": "Network",
        "scan": "Import & Autofill",
        "storage": "Storage Audit",
        "trash": "Safe Cleanup",
        "ocr": "OCR (Optional)",
        "presentmon": "FPS Import (Optional)",
        "library": "Help Library",
    },
    "buttons": {
        "snapshot": "Save Snapshot",
        "reset": "Reset Profile",
        "export": "Export Profile",
    },
    "labels": {
        "profile_name": "Profile name",
        "notes": "Notes (auto-written after matches)",
        "refresh": "Monitor refresh rate (Hz)",
        "fps_target": "FPS cap target",
        "latency": "Latency goal (ms)",
        "launch": "Steam launch options",
    },
}


# -------------------- Helper Functions --------------------
def load_index() -> Dict[str, Any]:
    """Load profile index with fallback to defaults."""
    idx = safe_load_json(INDEX_PATH)
    if isinstance(idx, dict) and "hash_to_file" in idx:
        return idx
    return {"hash_to_file": {}, "createdISO": now_iso(), "updatedISO": now_iso()}


def save_index(idx: Dict[str, Any]) -> None:
    """Save profile index."""
    idx["updatedISO"] = now_iso()
    safe_save_json(INDEX_PATH, idx)


def save_unique_json(folder: str, obj: Dict[str, Any], reason: str, prefix: str) -> Tuple[bool, str]:
    """Save JSON file with duplicate detection based on hash."""
    try:
        idx = load_index()
        h = profile_hash(obj) if isinstance(obj, dict) else hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()
        if h in idx["hash_to_file"]:
            return False, idx["hash_to_file"][h]

        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = slug(obj.get("meta", {}).get("profileName", "profile")) if isinstance(obj, dict) else "object"
        r = slug(reason) if reason else "snapshot"
        filename = f"{prefix}_{name}_{ts}_{r}.json"
        path = os.path.join(folder, filename)

        safe_save_json(path, obj)
        idx["hash_to_file"][h] = path
        save_index(idx)
        return True, path
    except Exception as e:
        logger.error(f"Failed to save unique JSON: {e}")
        return False, ""


def build_launch_string(launch_options: List[Dict[str, Any]]) -> str:
    """Build launch option string from enabled options."""
    try:
        return " ".join([x["key"].strip() for x in launch_options if x.get("enabled")])
    except Exception as e:
        logger.error(f"Failed to build launch string: {e}")
        return ""


def bump_updated(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Update profile's lastUpdatedISO timestamp."""
    profile.setdefault("meta", {})
    profile["meta"]["lastUpdatedISO"] = now_iso()
    return profile


def logs_to_csv_bytes(logs: List[Dict[str, Any]]) -> bytes:
    """Convert performance logs to CSV bytes."""
    fieldnames = [
        "createdISO",
        "match_startISO", "match_endISO", "duration_s",
        "mode", "map", "hdr_mode",
        "avg_fps", "one_percent_low",
        "ping_ms", "packet_loss_pct",
        "cpu_avg_pct", "cpu_peak_pct",
        "input_feel_1_10",
        "settings_signature",
        "compare_to_similar",
        "notes"
    ]
    from io import StringIO
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in logs:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue().encode("utf-8")


def hdr_method_label(toggles: Dict[str, Any]) -> str:
    """Determine HDR method label from toggles."""
    if not toggles.get("hdrWindowsOn"):
        return "HDR OFF (SDR)"
    if toggles.get("rtxHdrOn"):
        return "RTX HDR"
    if toggles.get("autoHdrOn"):
        return "HDR ON (Auto HDR)"
    return "HDR ON"


def settings_signature(profile: Dict[str, Any]) -> str:
    """Generate settings signature hash."""
    p = {
        "targets": profile.get("targets", {}),
        "toggles": profile.get("toggles", {}),
        "launch": build_launch_string(profile.get("launchOptions", [])),
    }
    s = json.dumps(p, sort_keys=True).encode("utf-8")
    return hashlib.sha256(s).hexdigest()[:12]


# -------------------- Windows helpers (PowerShell) --------------------
def ps_run(cmd: str) -> str:
    """Run PowerShell command safely."""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            text=True,
            errors="ignore",
            timeout=5,
        )
        return out.strip()
    except subprocess.TimeoutExpired:
        logger.warning("PowerShell command timed out")
        return ""
    except Exception as e:
        logger.error(f"PowerShell error: {e}")
        return ""


def apex_process_running() -> bool:
    """Check if Apex process is running."""
    check = r"""
$names = @('r5apex','r5apex.exe')
$found = $false
foreach ($n in $names) {
  try { if (Get-Process -Name $n -ErrorAction Stop) { $found = $true } } catch {}
}
if ($found) { '1' } else { '0' }
"""
    return ps_run(check) == "1"


def get_foreground_window_info() -> Dict[str, str]:
    """Get foreground window title and process name."""
    script = r"""
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class Win32 {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@
$h = [Win32]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 1024
[void][Win32]::GetWindowText($h, $sb, $sb.Capacity)
$title = $sb.ToString()
$pid = 0
[void][Win32]::GetWindowThreadProcessId($h, [ref]$pid)
$pname = ''
try { $pname = (Get-Process -Id $pid -ErrorAction Stop).ProcessName } catch {}
@{ title=$title; process=$pname } | ConvertTo-Json -Compress
"""
    raw = ps_run(script)
    try:
        d = json.loads(raw) if raw else {}
        return {"title": d.get("title", ""), "process": d.get("process", "")}
    except json.JSONDecodeError:
        logger.warning("Failed to parse foreground window info")
        return {"title": "", "process": ""}


def get_apex_cpu_pct_sample(window_s: float = 0.5) -> float:
    """Sample Apex process CPU usage."""
    script1 = r"""
try { $p = Get-Process -Name r5apex -ErrorAction Stop; "{0}" -f $p.CPU } catch { "" }
"""
    a = ps_run(script1)
    time.sleep(max(0.2, window_s))
    b = ps_run(script1)
    try:
        if not a or not b:
            return 0.0
        cpu_a = float(a)
        cpu_b = float(b)
        delta_cpu_s = max(0.0, cpu_b - cpu_a)
        cores = os.cpu_count() or 1
        pct = (delta_cpu_s / window_s) * 100.0 / cores
        return max(0.0, min(100.0, pct))
    except (ValueError, TypeError):
        logger.debug("Failed to compute CPU percentage")
        return 0.0


def ping_sample(host: str = "1.1.1.1", count: int = 10) -> Tuple[Optional[int], Optional[float]]:
    """Sample ping statistics."""
    try:
        out = subprocess.check_output(["ping", "-n", str(count), host], text=True, errors="ignore", timeout=15)
    except subprocess.TimeoutExpired:
        logger.warning(f"Ping to {host} timed out")
        return None, None
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        return None, None
    
    loss = None
    m = re.search(r"Lost = \d+ \((\d+)% loss\)", out, re.IGNORECASE)
    if m:
        try:
            loss = float(m.group(1))
        except ValueError:
            pass
    
    avg = None
    m2 = re.search(r"Average = (\d+)ms", out, re.IGNORECASE)
    if m2:
        try:
            avg = int(m2.group(1))
        except ValueError:
            pass
    
    return avg, loss


# -------------------- Match Monitor (heuristic) --------------------
def monitor_tick(state: MonitorState) -> MonitorState:
    """Update match monitor state."""
    tick_ts = now_iso()
    fg = get_foreground_window_info()
    apex_running = apex_process_running()
    apex_foreground = apex_running and (fg.get("process", "").lower() == "r5apex")

    state.setdefault("fg_streak", 0)
    state.setdefault("bg_streak", 0)
    state.setdefault("in_match", False)
    state.setdefault("match_startISO", "")
    state.setdefault("match_endISO", "")
    state.setdefault("cpu_samples", [])
    state.setdefault("cpu_peak", 0.0)

    cpu_pct = 0.0
    if apex_running:
        cpu_pct = get_apex_cpu_pct_sample(0.35)
        state["cpu_samples"].append(cpu_pct)
        state["cpu_peak"] = max(state.get("cpu_peak", 0.0), cpu_pct)

    if apex_foreground:
        state["fg_streak"] += 1
        state["bg_streak"] = 0
    else:
        state["bg_streak"] += 1
        state["fg_streak"] = 0

    START_STREAK = safe_int(state.get("start_streak_needed"), 3)
    END_STREAK = safe_int(state.get("end_streak_needed"), 6)

    if (not state["in_match"]) and apex_foreground and state["fg_streak"] >= START_STREAK:
        state["in_match"] = True
        state["match_startISO"] = tick_ts
        state["match_endISO"] = ""
        state["cpu_samples"] = []
        state["cpu_peak"] = 0.0

    if state["in_match"]:
        if (not apex_running) or (not apex_foreground and state["bg_streak"] >= END_STREAK):
            state["in_match"] = False
            state["match_endISO"] = tick_ts

    state["last_tickISO"] = tick_ts
    state["apex_running"] = apex_running
    state["apex_foreground"] = apex_foreground
    state["fg_title"] = fg.get("title", "")
    state["fg_process"] = fg.get("process", "")
    return state


def compute_cpu_stats(samples: List[float]) -> Tuple[float, float]:
    """Compute CPU average and peak from samples."""
    if not samples:
        return 0.0, 0.0
    avg = sum(samples) / len(samples)
    peak = max(samples)
    return round(avg, 2), round(peak, 2)


def find_similar_entries(logs: List[Dict[str, Any]], sig: str, hdr_mode: str) -> List[Dict[str, Any]]:
    """Find logs with matching settings signature and HDR mode."""
    return [x for x in logs if x.get("settings_signature") == sig and x.get("hdr_mode") == hdr_mode]


def compare_vs_similar(similar: List[Dict[str, Any]], current: Dict[str, Any]) -> str:
    """Compare current metrics against similar sessions."""
    if not similar:
        return "No prior similar sessions found."

    def mean_of(key: str) -> Optional[float]:
        """Safely compute mean of key across similar entries."""
        vals = []
        for s in similar:
            v = s.get(key)
            try:
                if v is None or v == "":
                    continue
                vals.append(float(v))
            except (ValueError, TypeError):
                continue
        return sum(vals) / len(vals) if vals else None

    cur_cpu = safe_float(current.get("cpu_avg_pct", 0), 0.0)
    avg_cpu = mean_of("cpu_avg_pct")

    parts = []
    if avg_cpu is not None:
        parts.append(f"CPU avg: {cur_cpu:.2f}% vs {avg_cpu:.2f}% ({cur_cpu-avg_cpu:+.2f})")

    # Use extracted utility for other metrics
    for metric_name, current_val, avg_val in [
        ("Ping", current.get("ping_ms"), mean_of("ping_ms")),
        ("Loss", current.get("packet_loss_pct"), mean_of("packet_loss_pct")),
        ("Avg FPS", current.get("avg_fps"), mean_of("avg_fps")),
        ("1% Low", current.get("one_percent_low"), mean_of("one_percent_low")),
    ]:
        comparison = safe_metric_comparison(metric_name, current_val, avg_val)
        if comparison:
            parts.append(comparison)

    return " | ".join(parts) if parts else "Similar sessions exist, but not enough comparable numeric fields logged yet."


# -------------------- Auto Notes + Suggestions --------------------
def make_suggestions(profile: Dict[str, Any]) -> List[str]:
    """Generate performance suggestions based on profile."""
    suggestions: List[str] = []
    t = profile.get("toggles", {})
    targets = profile.get("targets", {})
    fps_target = safe_int(targets.get("fpsTarget"), 0)
    refresh = safe_int(targets.get("refreshHz"), 0)

    if refresh >= 120 and fps_target >= refresh:
        suggestions.append("Cap FPS to 2–3 below refresh (e.g., 237 for 240Hz) for VRR/Reflex consistency.")

    if t.get("autoHdrOn") and t.get("rtxHdrOn"):
        suggestions.append("Disable one: Auto HDR OR RTX HDR. Stacking can reduce clarity (double tone-map).")

    if not t.get("vsyncInGameOff"):
        suggestions.append("Turn in-game V-Sync OFF to reduce input latency (competitive baseline).")

    if not t.get("reflexBoostOn"):
        suggestions.append("Enable Reflex + Boost to reduce latency and stabilize pacing.")

    return suggestions[:6]


# Note template
AUTO_NOTES_TEMPLATE = """=== CURRENT SETUP ===
Version: {version}
Refresh/FPS cap: {refresh}Hz / {fps} FPS
VRR: {vrr} | In-game V-Sync: {vsync} | Reflex: {reflex}
HDR mode: {hdr_label}
Launch: {launch}

=== LAST MATCH (AUTO) ===
{match_start} → {match_end} ({duration}s) | CPU avg {cpu_avg}% peak {cpu_peak}% | Ping {ping}ms | Loss {loss}% | AvgFPS {avg_fps} | 1%Low {one_percent_low}
Compared to similar: {compare_text}
{session_notes}

=== NEXT STEPS ===
{suggestions}"""


def auto_write_notes(profile: Dict[str, Any], last_entry: Dict[str, Any], compare_text: str, suggestions: List[str]) -> str:
    """Generate auto notes for match."""
    try:
        t = profile.get("toggles", {})
        targets = profile.get("targets", {})
        launch = build_launch_string(profile.get("launchOptions", []))
        hdr_label = hdr_method_label(t)

        session_notes_line = f"Session note: {last_entry.get('notes')}" if last_entry.get("notes") else ""
        
        suggestions_text = "\n".join([f"{i}. {s}" for i, s in enumerate(suggestions, 1)]) if suggestions else "No changes suggested. Keep baseline and log more matches."

        return AUTO_NOTES_TEMPLATE.format(
            version=APP_VERSION,
            refresh=safe_int(targets.get("refreshHz"), 0),
            fps=safe_int(targets.get("fpsTarget"), 0),
            vrr="ON" if t.get("gsyncOn") else "OFF",
            vsync="OFF" if t.get("vsyncInGameOff") else "ON",
            reflex="ON+Boost" if t.get("reflexBoostOn") else "OFF",
            hdr_label=hdr_label,
            launch=launch if launch else "(none)",
            match_start=last_entry.get("match_startISO", ""),
            match_end=last_entry.get("match_endISO", ""),
            duration=last_entry.get("duration_s", ""),
            cpu_avg=last_entry.get("cpu_avg_pct", ""),
            cpu_peak=last_entry.get("cpu_peak_pct", ""),
            ping=last_entry.get("ping_ms", ""),
            loss=last_entry.get("packet_loss_pct", ""),
            avg_fps=last_entry.get("avg_fps", ""),
            one_percent_low=last_entry.get("one_percent_low", ""),
            compare_text=compare_text,
            session_notes=session_notes_line,
            suggestions=suggestions_text,
        )
    except Exception as e:
        logger.error(f"Failed to auto-write notes: {e}")
        return "Error generating notes."


# -------------------- Trash Bin (move-first; delete only on confirm) --------------------
def list_files_recursive(root: str) -> List[str]:
    """Recursively list all files in directory."""
    out = []
    try:
        for base, _, files in os.walk(root):
            for f in files:
                out.append(os.path.join(base, f))
    except Exception as e:
        logger.error(f"Failed to list files in {root}: {e}")
    return out


def safe_move_to_trash(path: str) -> Tuple[bool, str]:
    """Safely move file to trash."""
    try:
        if not os.path.exists(path) or not os.path.isfile(path):
            return False, "Not a file."
        os.makedirs(TRASH_TODAY_DIR, exist_ok=True)
        name = os.path.basename(path)
        dst = os.path.join(TRASH_TODAY_DIR, name)
        if os.path.exists(dst):
            stem, ext = os.path.splitext(name)
            dst = os.path.join(TRASH_TODAY_DIR, f"{stem}_{dt.datetime.now().strftime('%H%M%S')}{ext}")
        os.replace(path, dst)
        return True, dst
    except Exception as e:
        logger.error(f"Failed to move file to trash: {e}")
        return False, str(e)


def safe_empty_trash_today() -> Tuple[int, int]:
    """Safely empty trash (today only)."""
    files_deleted = 0
    dirs_deleted = 0
    try:
        if not os.path.abspath(TRASH_TODAY_DIR).startswith(os.path.abspath(TRASHBIN_DIR)):
            return 0, 0
        if not os.path.exists(TRASH_TODAY_DIR):
            return 0, 0

        for p in list_files_recursive(TRASH_TODAY_DIR):
            try:
                os.remove(p)
                files_deleted += 1
            except Exception as e:
                logger.debug(f"Failed to delete {p}: {e}")

        for base, dirs, _ in os.walk(TRASH_TODAY_DIR, topdown=False):
            for d in dirs:
                dp = os.path.join(base, d)
                try:
                    os.rmdir(dp)
                    dirs_deleted += 1
                except Exception as e:
                    logger.debug(f"Failed to remove directory {dp}: {e}")
        
        try:
            os.rmdir(TRASH_TODAY_DIR)
            dirs_deleted += 1
        except Exception:
            pass
        
        os.makedirs(TRASH_TODAY_DIR, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to empty trash: {e}")
    
    return files_deleted, dirs_deleted


# -------------------- Storage Map (safe scoped scan) --------------------
SAFE_SCAN_PRESETS = [
    {"label": "Apex Dashboard (this folder only)", "path": BASE_DIR, "enabled": True},
    {"label": "Apex Dashboard\\Profiles", "path": PROFILES_DIR, "enabled": True},
    {"label": "Apex Dashboard\\Snapshots", "path": SNAP_DIR, "enabled": True},
    {"label": "Apex Dashboard\\Scans", "path": SCAN_DIR, "enabled": True},
    {"label": "Apex Dashboard\\TempBin", "path": TEMPBIN_DIR, "enabled": True},
    {"label": "Apex Dashboard\\_TRASH_BIN", "path": TRASHBIN_DIR, "enabled": True},
]


def dir_stats(root: str, max_files: int = 25000) -> Dict[str, Any]:
    """Compute directory statistics."""
    total_files = 0
    total_bytes = 0
    type_counts: Dict[str, int] = {}
    newest_iso = ""
    oldest_iso = ""
    truncated = False

    try:
        for base, _, files in os.walk(root):
            for f in files:
                total_files += 1
                if total_files > max_files:
                    truncated = True
                    break
                fp = os.path.join(base, f)
                try:
                    stt = os.stat(fp)
                    total_bytes += int(stt.st_size)
                    ext = os.path.splitext(f)[1].lower() or "(noext)"
                    type_counts[ext] = type_counts.get(ext, 0) + 1
                    m = dt.datetime.fromtimestamp(stt.st_mtime).isoformat(timespec="seconds")
                    if not newest_iso or m > newest_iso:
                        newest_iso = m
                        if not oldest_iso or m < oldest_iso:
                            oldest_iso = m
                except Exception as e:
                    logger.debug(f"Failed to stat {fp}: {e}")
            if truncated:
                break
    except Exception as e:
        logger.error(f"Failed to scan directory {root}: {e}")

    return {
        "path": root,
        "exists": os.path.exists(root),
        "total_files": total_files,
        "total_bytes": total_bytes,
        "newest_modifiedISO": newest_iso,
        "oldest_modifiedISO": oldest_iso,
        "type_counts": type_counts,
        "truncated": truncated,
        "max_files": max_files,
    }


def write_storage_map(results: List[Dict[str, Any]]) -> None:
    """Write storage audit results to JSON and CSV."""
    try:
        os.makedirs(STORAGE_DIR, exist_ok=True)
        doc = {
            "createdISO": now_iso(),
            "scope": "User-approved safe scan (no file contents).",
            "results": results,
        }
        safe_save_json(STORAGE_MAP_JSON, doc)

        rows = []
        for r in results:
            rows.append({
                "label": r.get("label", ""),
                "path": r.get("path", ""),
                "exists": r.get("exists", ""),
                "files": r.get("total_files", ""),
                "size_bytes": r.get("total_bytes", ""),
                "size_human": bytes_human(int(r.get("total_bytes", 0) or 0)),
                "newest_modifiedISO": r.get("newest_modifiedISO", ""),
                "oldest_modifiedISO": r.get("oldest_modifiedISO", ""),
                "truncated": r.get("truncated", ""),
            })
        with open(STORAGE_MAP_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["label", "path"])
            w.writeheader()
            for row in rows:
                w.writerow(row)
    except Exception as e:
        logger.error(f"Failed to write storage map: {e}")


# -------------------- OCR Detector (optional / safe-off) --------------------
def ocr_available() -> Tuple[bool, str]:
    """Check if OCR dependencies are available."""
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
        import mss  # noqa: F401
        return True, "OK"
    except ImportError as e:
        return False, str(e)


def ocr_detect_end_screen_demo() -> Dict[str, Any]:
    """Demo OCR detection on current screen."""
    try:
        import pytesseract
        import mss
        from PIL import Image

        keywords = ["CHAMPION", "SQUAD ELIMINATED", "MATCH SUMMARY", "YOU ARE THE CHAMPION", "ELIMINATED"]
        with mss.mss() as sct:
            mon = sct.monitors[1]
            img = sct.grab(mon)
            im = Image.frombytes("RGB", img.size, img.rgb)

        text = pytesseract.image_to_string(im)
        upper = (text or "").upper()
        hits = [k for k in keywords if k in upper]
        return {"hits": hits, "text_preview": upper[:600]}
    except Exception as e:
        logger.error(f"OCR detection failed: {e}")
        return {"hits": [], "text_preview": f"Error: {e}"}


# -------------------- PresentMon CSV import (safe) --------------------
def parse_presentmon_csv(file_bytes: bytes) -> Dict[str, Any]:
    """Parse PresentMon FPS CSV."""
    try:
        text = file_bytes.decode("utf-8-sig", errors="ignore")
        lines = text.splitlines()
        if len(lines) < 2:
            return {"ok": False, "error": "CSV too short."}

        reader = csv.DictReader(lines)
        fps_samples: List[float] = []
        ft_ms: List[float] = []

        for row in reader:
            if "MsBetweenPresents" in row and row["MsBetweenPresents"]:
                try:
                    ft_ms.append(float(row["MsBetweenPresents"]))
                except ValueError:
                    pass
            if "FPS" in row and row["FPS"]:
                try:
                    fps_samples.append(float(row["FPS"]))
                except ValueError:
                    pass

        if not fps_samples and ft_ms:
            for ms in ft_ms:
                if ms > 0:
                    fps_samples.append(1000.0 / ms)

        if not fps_samples:
            return {"ok": False, "error": "No usable FPS data found in CSV (expected FPS or MsBetweenPresents)."}

        fps_samples.sort()
        avg_fps = sum(fps_samples) / len(fps_samples)
        idx = max(0, int(len(fps_samples) * 0.01) - 1)
        one_percent_low = fps_samples[idx]

        return {
            "ok": True,
            "samples": len(fps_samples),
            "avg_fps": round(avg_fps, 2),
            "one_percent_low": round(one_percent_low, 2),
        }
    except Exception as e:
        logger.error(f"Failed to parse PresentMon CSV: {e}")
        return {"ok": False, "error": str(e)}



# -------------------- System Health --------------------
def runtime_secret_available(name: str) -> bool:
    """Check whether a runtime secret/env var exists without exposing the value."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = os.environ.get(name, "")
    return bool(str(value).strip())


def bool_status(value: bool) -> str:
    """Readable status label."""
    return "Ready" if value else "Missing"


def render_system_health_panel(profile: Dict[str, Any]) -> None:
    """Render a compact system health panel in the sidebar."""
    with st.expander("System Health", expanded=True):
        st.caption("Live app status, secrets, storage, and profile state.")

        app_col, version_col = st.columns(2)
        app_col.metric("App", "Live")
        version_col.metric("Version", APP_VERSION)

        secret_col_a, secret_col_b = st.columns(2)
        openai_ready = runtime_secret_available("OPENAI_API_KEY")
        tracker_ready = runtime_secret_available("TRACKER_API_KEY")

        secret_col_a.metric("OpenAI", bool_status(openai_ready))
        secret_col_b.metric("Tracker", bool_status(tracker_ready))

        profile_meta = profile.get("meta", {}) if isinstance(profile, dict) else {}
        profile_logs = profile.get("performanceLogs", []) if isinstance(profile, dict) else []

        st.write("**Profile**")
        st.caption(f"Name: {profile_meta.get('profileName', 'Unknown')}")
        st.caption(f"Updated: {profile_meta.get('lastUpdatedISO', 'Unknown')}")
        st.caption(f"Match logs: {len(profile_logs) if isinstance(profile_logs, list) else 0}")

        storage_rows = []
        for label, folder in [
            ("Autosave", Path(AUTOSAVE_PATH).parent),
            ("Snapshots", Path(SNAP_DIR)),
            ("Exports", Path(EXPORT_DIR)),
            ("Profiles", Path(PROFILES_DIR)),
            ("Storage", Path(STORAGE_DIR)),
        ]:
            storage_rows.append({
                "Area": label,
                "Ready": folder.exists(),
            })

        st.write("**Storage**")
        st.dataframe(storage_rows, use_container_width=True, hide_index=True)

        if not openai_ready:
            st.warning("OPENAI_API_KEY missing in Streamlit Secrets.")
        if not tracker_ready:
            st.warning("TRACKER_API_KEY missing or blank in Streamlit Secrets.")
        st.link_button("Open GitHub Repo", REPO_URL, use_container_width=True)


# ============== STREAMLIT UI ==============
st.set_page_config(page_title=APP_TITLE, layout="wide")

# FALSETECH_THEME_START
THEME_CSS_PATH = Path(BASE_DIR) / "assets" / "falsetech_theme.css"
if THEME_CSS_PATH.exists():
    st.markdown(f"<style>{THEME_CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
# FALSETECH_THEME_END


with st.sidebar:
    st.markdown(
        '<div class="ft-brand-pill"><span class="ft-brand-dot"></span>FalseTech Apex</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### Apex Dashboard")
    st.caption(f"Version: {APP_VERSION}")
    st.markdown("---")
    st.markdown("**Official Links**")
    st.link_button("GitHub Repo", REPO_URL, use_container_width=True)
    st.link_button("Report a bug", BUG_URL, use_container_width=True)
    st.link_button("Request a feature", FEATURE_URL, use_container_width=True)

st.info("Beta: reproduce once → click Report a bug → paste steps + screenshot.", icon="🧪")

# ============== Session State Initialization ==============
if "profile" not in st.session_state:
    loaded = safe_load_json(AUTOSAVE_PATH)
    st.session_state.profile = loaded if loaded and validate_profile_structure(loaded) else deep_copy(DEFAULT_PROFILE)

if "monitor_state" not in st.session_state:
    st.session_state.monitor_state: MonitorState = {
        "enabled": False,
        "poll_seconds": 3,
        "start_streak_needed": 3,
        "end_streak_needed": 6,
        "in_match": False,
        "match_startISO": "",
        "match_endISO": "",
        "cpu_samples": [],
        "cpu_peak": 0.0,
        "last_tickISO": "",
        "apex_running": False,
        "apex_foreground": False,
        "fg_title": "",
        "fg_process": "",
        "fg_streak": 0,
        "bg_streak": 0,
    }

if "scan_plan" not in st.session_state:
    st.session_state.scan_plan = deep_copy(SAFE_SCAN_PRESETS)

if "storage_map" not in st.session_state:
    st.session_state.storage_map = safe_load_json(STORAGE_MAP_JSON) or {}

profile: Profile = st.session_state.profile

with st.sidebar:
    render_system_health_panel(profile)

# ============== Header ==============
st.title(APP_TITLE)
# APEX_API_STATUS_PANEL_START
try:
    render_api_status_panel()
except Exception as exc:
    st.warning(f"API status panel unavailable: {exc}")
# APEX_API_STATUS_PANEL_END
st.caption(
    f"v{APP_VERSION} • Profile: {profile['meta']['profileName']} • "
    f"Updated: {profile['meta']['lastUpdatedISO']}"
)


# ============== Dashboard Body ==============

profile.setdefault("meta", {})
profile.setdefault("targets", {})
profile.setdefault("toggles", {})
profile.setdefault("launchOptions", [])
profile.setdefault("performanceLogs", [])
profile.setdefault("network", {})
profile.setdefault("hdrSetup", DEFAULT_PROFILE.get("hdrSetup", {}))
profile.setdefault("presets", DEFAULT_PROFILE.get("presets", {}))

top_a, top_b, top_c, top_d = st.columns(4)
top_a.metric("Refresh Target", f"{profile['targets'].get('refreshHz', '?')} Hz")
top_b.metric("FPS Target", profile["targets"].get("fpsTarget", "?"))
top_c.metric("Latency Goal", f"{profile['targets'].get('latencyGoalMs', '?')} ms")
top_d.metric("HDR Mode", hdr_method_label(profile.get("toggles", {})))

tabs = st.tabs([
    UI["tabs"]["apex"],
    "Tracker",
    UI["tabs"]["hdr"],
    UI["tabs"]["presets"],
    UI["tabs"]["match"],
    UI["tabs"]["perf"],
    UI["tabs"]["net"],
    UI["tabs"]["storage"],
    UI["tabs"]["library"],
])

with tabs[0]:
    st.subheader("Competitive Setup")

    left, right = st.columns([1, 1])

    with left:
        profile["meta"]["profileName"] = st.text_input(
            UI["labels"]["profile_name"],
            value=str(profile["meta"].get("profileName", "")),
        )
        profile["meta"]["monitor"] = st.text_input(
            "Monitor",
            value=str(profile["meta"].get("monitor", "")),
        )
        profile["meta"]["gpu"] = st.text_input(
            "GPU",
            value=str(profile["meta"].get("gpu", "")),
        )
        profile["meta"]["notes"] = st.text_area(
            UI["labels"]["notes"],
            value=str(profile["meta"].get("notes", "")),
            height=110,
        )

    with right:
        refresh = st.number_input(
            UI["labels"]["refresh"],
            min_value=30,
            max_value=360,
            value=safe_int(profile["targets"].get("refreshHz", 240), 240, 30, 360),
            step=1,
        )
        profile["targets"]["refreshHz"] = validate_refresh_hz(int(refresh))

        fps_target = st.number_input(
            UI["labels"]["fps_target"],
            min_value=30,
            max_value=500,
            value=safe_int(profile["targets"].get("fpsTarget", 237), 237, 30, 500),
            step=1,
        )
        profile["targets"]["fpsTarget"] = validate_fps_target(int(fps_target), int(refresh))

        latency_goal = st.number_input(
            UI["labels"]["latency"],
            min_value=1,
            max_value=100,
            value=safe_int(profile["targets"].get("latencyGoalMs", 10), 10, 1, 100),
            step=1,
        )
        profile["targets"]["latencyGoalMs"] = int(latency_goal)

    st.divider()
    st.subheader(UI["labels"]["launch"])

    for i, opt in enumerate(profile.get("launchOptions", [])):
        if not isinstance(opt, dict):
            continue
        cols = st.columns([1, 2, 4])
        with cols[0]:
            opt["enabled"] = st.checkbox("On", value=bool(opt.get("enabled")), key=f"launch_enabled_{i}")
        with cols[1]:
            opt["key"] = st.text_input("Flag", value=str(opt.get("key", "")), key=f"launch_key_{i}")
        with cols[2]:
            opt["note"] = st.text_input("Note", value=str(opt.get("note", "")), key=f"launch_note_{i}")

    st.code(build_launch_string(profile.get("launchOptions", [])), language="text")

    if st.button("Add launch option"):
        profile["launchOptions"].append({"key": "", "enabled": False, "note": ""})
        st.rerun()

    st.divider()
    st.subheader("Import System Report")
    st.caption("Upload a DxDiag .txt report to import safe system, display, GPU, and driver information.")

    try:
        from apex_system_importer import (
            LOCAL_DXDIAG_HELPER_PS1,
            apply_system_report_to_profile,
            build_import_rows,
            parse_dxdiag_text,
        )
    except Exception as exc:
        st.error(f"System report importer unavailable: {exc}")
    else:
        with st.expander("How to create a DxDiag report", expanded=False):
            st.write("Run this on your Windows gaming PC, then upload the created text file here.")
            st.code('dxdiag /t "$env:USERPROFILE\\Desktop\\dxdiag_apex.txt"', language="powershell")
            st.download_button(
                "Download local DxDiag helper script",
                data=LOCAL_DXDIAG_HELPER_PS1.encode("utf-8"),
                file_name="generate_dxdiag_apex.ps1",
                mime="text/plain",
                use_container_width=True,
            )

        uploaded_dxdiag = st.file_uploader(
            "Upload DxDiag report (.txt)",
            type=["txt"],
            key="dxdiag_report_upload",
        )

        if uploaded_dxdiag is not None:
            raw_dxdiag = uploaded_dxdiag.getvalue().decode("utf-8", errors="replace")
            parsed_dxdiag = parse_dxdiag_text(raw_dxdiag)
            import_rows = build_import_rows(parsed_dxdiag)

            if not import_rows:
                st.warning("No supported DxDiag fields were found. Make sure you uploaded the full DxDiag text report.")
            else:
                st.success(f"Found {len(import_rows)} supported fields.")
                st.dataframe(
                    [
                        {
                            "Field": row["Field"],
                            "Value": row["Value"],
                            "Destination": row["Destination"],
                            "Recommended": row["Recommended"],
                        }
                        for row in import_rows
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                with st.form("apply_dxdiag_import"):
                    st.write("Choose what to import into your profile.")

                    selected_import_keys = []
                    for row in import_rows:
                        selected = st.checkbox(
                            f'{row["Field"]} ? {row["Destination"]}',
                            value=bool(row["Recommended"]),
                            key=f'dxdiag_import_{row["key"]}',
                        )
                        if selected:
                            selected_import_keys.append(row["key"])

                    apply_import = st.form_submit_button("Apply selected system info")

                if apply_import:
                    if not selected_import_keys:
                        st.warning("No fields selected.")
                    else:
                        st.session_state.profile = apply_system_report_to_profile(
                            profile,
                            parsed_dxdiag,
                            selected_import_keys,
                        )
                        st.success(f"Imported {len(selected_import_keys)} fields into profile.")
                        st.toast("System report imported.")
                        st.rerun()

                with st.expander("Parsed safe fields", expanded=False):
                    st.json(parsed_dxdiag)


with tabs[1]:
    st.subheader("Tracker.gg Player Lookup")

    try:
        from apex_tracker import fetch_tracker_profile
    except Exception as exc:
        fetch_tracker_profile = None
        st.error(f"Tracker module unavailable: {exc}")

    tracker_cols = st.columns([1, 2, 1])
    with tracker_cols[0]:
        tracker_platform = st.selectbox("Platform", ["origin", "xbl", "psn"], index=0)
    with tracker_cols[1]:
        tracker_player = st.text_input("Player handle", value=st.session_state.get("tracker_player", "ifalsetto"))
    with tracker_cols[2]:
        st.write("")
        st.write("")
        search_tracker = st.button("Search Tracker", use_container_width=True)

    if search_tracker and fetch_tracker_profile:
        st.session_state.tracker_player = tracker_player
        with st.spinner("Fetching Tracker profile..."):
            st.session_state.tracker_profile = fetch_tracker_profile(tracker_player, tracker_platform)

    tracker_profile = st.session_state.get("tracker_profile")
    if tracker_profile:
        if tracker_profile.get("source") == "fallback":
            st.warning(tracker_profile.get("error", "Tracker fallback data is active."))
        else:
            st.success("Tracker profile loaded.")

        stat_cols = st.columns(6)
        stat_cols[0].metric("Player", tracker_profile.get("player_name", "?"))
        stat_cols[1].metric("Level", tracker_profile.get("level", "?"))
        stat_cols[2].metric("Rank", tracker_profile.get("rank", "?"))
        stat_cols[3].metric("Kills", tracker_profile.get("kills", "?"))
        stat_cols[4].metric("Wins", tracker_profile.get("wins", "?"))
        stat_cols[5].metric("K/D", tracker_profile.get("kd", "?"))

        st.metric("Current Legend", tracker_profile.get("current_legend", "?"))

        with st.expander("Raw Tracker payload", expanded=False):
            st.json(tracker_profile.get("raw", {}))
    else:
        st.info("Search a player to load Tracker stats. If the API key is missing/invalid, fallback mode stays active.")

with tabs[2]:
    st.subheader("HDR / Display Guide")

    toggles = profile.setdefault("toggles", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        toggles["hdrWindowsOn"] = st.checkbox("Windows HDR", value=bool(toggles.get("hdrWindowsOn", True)))
        toggles["autoHdrOn"] = st.checkbox("Auto HDR", value=bool(toggles.get("autoHdrOn", True)))
    with col2:
        toggles["rtxHdrOn"] = st.checkbox("RTX HDR", value=bool(toggles.get("rtxHdrOn", False)))
        toggles["gsyncOn"] = st.checkbox("G-SYNC", value=bool(toggles.get("gsyncOn", True)))
    with col3:
        toggles["vsyncInGameOff"] = st.checkbox("In-game V-Sync OFF", value=bool(toggles.get("vsyncInGameOff", True)))
        toggles["reflexBoostOn"] = st.checkbox("NVIDIA Reflex + Boost", value=bool(toggles.get("reflexBoostOn", True)))

    hdr_setup = profile.get("hdrSetup", {})
    for section, steps in hdr_setup.items():
        with st.expander(str(section).title(), expanded=False):
            if isinstance(steps, list):
                for step in steps:
                    st.write(f"- {step}")
            else:
                st.write(steps)

with tabs[3]:
    st.subheader("Presets")

    presets = profile.get("presets", {})
    if presets:
        selected_preset = st.selectbox("Preset", list(presets.keys()))
        st.json(presets.get(selected_preset, {}))
    else:
        st.info("No presets found.")

with tabs[4]:
    st.subheader("Auto Match Log")

    with st.form("manual_match_log"):
        match_cols = st.columns(4)
        mode = match_cols[0].text_input("Mode", value="Ranked")
        map_name = match_cols[1].text_input("Map", value="")
        avg_fps = match_cols[2].number_input("Avg FPS", min_value=0, max_value=500, value=0)
        ping_ms = match_cols[3].number_input("Ping ms", min_value=0, max_value=500, value=0)

        notes = st.text_area("Match notes", height=90)
        submitted = st.form_submit_button("Add Match Log")

    if submitted:
        profile.setdefault("performanceLogs", []).append({
            "createdISO": now_iso(),
            "mode": mode,
            "map": map_name,
            "avg_fps": avg_fps,
            "ping_ms": ping_ms,
            "notes": notes,
            "settings_signature": profile_hash(profile),
        })
        st.success("Match log added.")
        st.toast("Match log added.")

with tabs[5]:
    st.subheader("Match History / Performance Logs")

    logs = profile.get("performanceLogs", [])
    if logs:
        st.dataframe(logs, use_container_width=True)
        st.download_button(
            "Download logs CSV",
            data=logs_to_csv_bytes(logs),
            file_name="apex_performance_logs.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No performance logs yet.")

with tabs[6]:
    st.subheader("Network")

    network = profile.setdefault("network", {})
    left, right = st.columns(2)

    with left:
        network["connection"] = st.text_input("Connection", value=str(network.get("connection", "Ethernet")))
        network["isp"] = st.text_input("ISP", value=str(network.get("isp", "")))
        network["router_model"] = st.text_input("Router model", value=str(network.get("router_model", "")))
        network["modem_model"] = st.text_input("Modem / fiber box", value=str(network.get("modem_model", "")))

    with right:
        tests = network.setdefault("tests", {})
        tests["speedtest_down_mbps"] = st.text_input("Download Mbps", value=str(tests.get("speedtest_down_mbps", "")))
        tests["speedtest_up_mbps"] = st.text_input("Upload Mbps", value=str(tests.get("speedtest_up_mbps", "")))
        tests["speedtest_ping_ms"] = st.text_input("Ping ms", value=str(tests.get("speedtest_ping_ms", "")))
        tests["packet_loss_pct"] = st.text_input("Packet loss %", value=str(tests.get("packet_loss_pct", "")))

    network["notes"] = st.text_area("Network notes", value=str(network.get("notes", "")), height=100)

with tabs[7]:
    st.subheader("Storage Audit")

    storage_targets = [
        ("Snapshots", SNAP_DIR),
        ("Scans", SCAN_DIR),
        ("Exports", EXPORT_DIR),
        ("Profiles", PROFILES_DIR),
        ("TempBin", TEMPBIN_DIR),
        ("Trash", TRASHBIN_DIR),
        ("StorageMap", STORAGE_DIR),
    ]

    rows = []
    for label, folder in storage_targets:
        path_obj = Path(folder)
        total_bytes = 0
        file_count = 0

        if path_obj.exists():
            for item in path_obj.rglob("*"):
                try:
                    if item.is_file():
                        file_count += 1
                        total_bytes += item.stat().st_size
                except Exception:
                    pass

        rows.append({
            "Label": label,
            "Path": str(path_obj),
            "Exists": path_obj.exists(),
            "Files": file_count,
            "Size": bytes_human(total_bytes),
        })

    st.dataframe(rows, use_container_width=True)

with tabs[8]:
    st.subheader("Help Library")

    library_type = st.radio("Library", ["Settings", "Launch Options"], horizontal=True)

    if library_type == "Settings":
        keys = list(SETTING_LIBRARY.keys())
        if keys:
            selected = st.selectbox("Setting", keys)
            st.json(SETTING_LIBRARY[selected])
        else:
            st.info("No setting library entries yet.")
    else:
        keys = list(LAUNCH_OPTION_LIBRARY.keys())
        if keys:
            selected = st.selectbox("Launch option", keys)
            st.json(LAUNCH_OPTION_LIBRARY[selected])
        else:
            st.info("No launch option library entries yet.")

st.divider()

action_cols = st.columns(4)

with action_cols[0]:
    if st.button(UI["buttons"]["snapshot"], use_container_width=True):
        ok, path = save_unique_json(SNAP_DIR, profile, "manual_snapshot", "snapshot")
        if ok:
            st.success(f"Snapshot saved: {path}")
            st.toast("Snapshot saved.")
        else:
            st.info(f"Duplicate snapshot skipped: {path}")

with action_cols[1]:
    st.download_button(
        UI["buttons"]["export"],
        data=json.dumps(profile, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name=f"{slug(profile['meta'].get('profileName', 'apex_profile'))}.json",
        mime="application/json",
        use_container_width=True,
    )

with action_cols[2]:
    if st.button(UI["buttons"]["reset"], use_container_width=True):
        st.session_state.profile = deep_copy(DEFAULT_PROFILE)
        st.warning("Profile reset to defaults.")
        st.rerun()

with action_cols[3]:
    if st.button("Save Now", use_container_width=True):
        safe_save_json(AUTOSAVE_PATH, profile)
        st.success("Profile autosaved.")
        st.toast("Profile autosaved.")


# ============== Autosave ==============
profile = bump_updated(profile)
st.session_state.profile = profile
safe_save_json(AUTOSAVE_PATH, st.session_state.profile)

logger.info("Session saved successfully")
