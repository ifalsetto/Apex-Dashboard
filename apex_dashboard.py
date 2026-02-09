import json
import os
import csv
import hashlib
import datetime as dt
import platform
import subprocess
import re
import time
from typing import Dict, Any, Tuple, List, Optional

import streamlit as st

APP_VERSION = "v0.1.0-beta"
REPO_ISSUES_URL = "https://github.com/ifalsetto/Apex-Dashboard/issues/new"
APP_TITLE = "Apex Optimizer Dashboard"
APEX_PROCESS_NAMES = ["r5apex", "r5apex.exe"]  # common Apex executable name

# -------------------- Paths (Your Layout) --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SNAP_DIR = os.path.join(BASE_DIR, "Snapshots")
SCAN_DIR = os.path.join(BASE_DIR, "Scans")
EXPORT_DIR = os.path.join(BASE_DIR, "Exports")
PROFILES_DIR = os.path.join(BASE_DIR, "Profiles")

# TempBin: safe-to-delete artifacts created by the app during the day
TEMPBIN_DIR = os.path.join(BASE_DIR, "TempBin")
TODAY_STR = dt.date.today().strftime("%Y-%m-%d")
DAILY_TEMP_DIR = os.path.join(TEMPBIN_DIR, TODAY_STR)

# Trash Bin: "office cleanup" staging area (move-to-bin first, delete only when you confirm)
TRASHBIN_DIR = os.path.join(BASE_DIR, "_TRASH_BIN")
TRASH_TODAY_DIR = os.path.join(TRASHBIN_DIR, TODAY_STR)

# Storage Map outputs
STORAGE_DIR = os.path.join(BASE_DIR, "StorageMap")
STORAGE_MAP_JSON = os.path.join(STORAGE_DIR, "storage_map.json")
STORAGE_MAP_CSV = os.path.join(STORAGE_DIR, "storage_map_view.csv")

INDEX_PATH = os.path.join(BASE_DIR, "profile_index.json")
AUTOSAVE_PATH = os.path.join(BASE_DIR, "profile_autosave.json")

for p in [SNAP_DIR, SCAN_DIR, EXPORT_DIR, PROFILES_DIR, DAILY_TEMP_DIR, TRASH_TODAY_DIR, STORAGE_DIR]:
    os.makedirs(p, exist_ok=True)

# -------------------- Defaults --------------------
DEFAULT_PROFILE: Dict[str, Any] = {
    "meta": {
        "profileName": "Apex - Competitive",
        "lastUpdatedISO": dt.datetime.now().isoformat(timespec="seconds"),
        "monitor": "ASUS ROG XG27AQDMG OLED 240Hz",
        "gpu": "RTX 5070 Ti",
        "os": "Windows 11",
        "notes": "OLED + 240Hz. Focus: clarity + low latency + repeatable presets.",
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
        {"key": "-dev", "enabled": True, "note": "Skip more startup animations (varies by patch)"},
        {"key": "+fps_max 0", "enabled": True, "note": "Uncap FPS (cap elsewhere if desired)"},
        {"key": "+lobby_max_fps 0", "enabled": True, "note": "Uncap lobby/menu FPS"},
        {"key": "-no_render_on_input_thread", "enabled": True, "note": "Threading behavior (system/patch dependent)"},
        {"key": "+m_rawinput 1", "enabled": True, "note": "Raw mouse input"},
        {"key": "-refresh 240", "enabled": False, "note": "Force 240Hz at launch (only if needed)"},
        {"key": "+mat_no_stretching 1", "enabled": True, "note": "Prevent stretching on aspect changes"},
        {"key": "+clip_mouse_to_letterbox 0", "enabled": True, "note": "Cursor behavior with letterbox"},
    ],
    "hdrSetup": {
        "windows": [
            "Settings → System → Display → Use HDR = ON",
            "Auto HDR = ON (tune per-title via Win+G)",
            "SDR brightness (in HDR) ≈ 35–40% for desktop readability",
            "Run Windows HDR Calibration and save profile",
        ],
        "nvidia": [
            "NVIDIA Control Panel → Change Resolution: RGB, Full, 10 bpc (if available)",
            "G-SYNC ON; V-Sync OFF globally; in-game V-Sync OFF",
            "Avoid heavy filters; prioritize clarity",
        ],
        "monitor": [
            "Use DisplayPort",
            "DSC = ON/Auto (needed for 240Hz + HDR bandwidth)",
            "OLED care features = ON",
            "Disable extra dynamic contrast modes; keep tone mapping consistent",
        ],
        "apexBehavior": [
            "Apex has no native HDR toggle; Windows HDR/Auto HDR affects tone mapping",
            "Use Win+G → HDR intensity until no gray fog but shadows still separate",
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

# -------------------- Libraries (short; extend later) --------------------
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
             "negatives": ["Can behave differently after updates."], "sop": ["Enable -dev.", "Launch twice to verify."], "scop": {"affects": ["Startup"], "risk_level": "Low–Medium", "rollback": ["Disable flag"], "verify": ["No weird boot"]}},
    "+fps_max 0": {"title": "+fps_max 0", "what_it_does": "Uncaps in-engine FPS cap (0 = uncapped).", "interactions": ["Still cap below refresh (237 @ 240Hz)."], "pros": ["Lets you cap elsewhere."],
                   "cons": ["More heat/power if uncapped."], "negatives": ["VRR ceiling issues if no cap."], "sop": ["Enable +fps_max 0.", "Cap to 237 using ONE method.", "Test+log."],
                   "scop": {"affects": ["FPS behavior", "thermals"], "risk_level": "Medium", "rollback": ["Disable or set fixed cap"], "verify": ["Stable cap"]}},
}

# -------------------- Helpers --------------------
def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")

def deep_copy(x):
    return json.loads(json.dumps(x))

def safe_load_json(path: str):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None

def safe_save_json(path: str, data: Any):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

def slug(s: str) -> str:
    s = (s or "").strip()
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        elif ch.isspace():
            out.append("_")
    name = "".join(out)
    while "__" in name:
        name = name.replace("__", "_")
    return (name[:60] if name else "profile")

def profile_hash(profile: Dict[str, Any]) -> str:
    p = deep_copy(profile)
    if "meta" in p and "lastUpdatedISO" in p["meta"]:
        p["meta"]["lastUpdatedISO"] = "LOCKED"
    s = json.dumps(p, sort_keys=True).encode("utf-8")
    return hashlib.sha256(s).hexdigest()

def load_index() -> Dict[str, Any]:
    idx = safe_load_json(INDEX_PATH)
    if isinstance(idx, dict) and "hash_to_file" in idx:
        return idx
    return {"hash_to_file": {}, "createdISO": now_iso(), "updatedISO": now_iso()}

def save_index(idx: Dict[str, Any]):
    idx["updatedISO"] = now_iso()
    safe_save_json(INDEX_PATH, idx)

def save_unique_json(folder: str, obj: Dict[str, Any], reason: str, prefix: str) -> Tuple[bool, str]:
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

def build_launch_string(launch_options: List[Dict[str, Any]]) -> str:
    return " ".join([x["key"].strip() for x in launch_options if x.get("enabled")])

def bump_updated(profile: Dict[str, Any]) -> Dict[str, Any]:
    profile.setdefault("meta", {})
    profile["meta"]["lastUpdatedISO"] = now_iso()
    return profile

def logs_to_csv_bytes(logs: List[Dict[str, Any]]) -> bytes:
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
    if not toggles.get("hdrWindowsOn"):
        return "HDR OFF (SDR)"
    if toggles.get("rtxHdrOn"):
        return "RTX HDR"
    if toggles.get("autoHdrOn"):
        return "HDR ON (Auto HDR)"
    return "HDR ON (no converter)"

def settings_signature(profile: Dict[str, Any]) -> str:
    p = {
        "targets": profile.get("targets", {}),
        "toggles": profile.get("toggles", {}),
        "launch": build_launch_string(profile.get("launchOptions", [])),
    }
    s = json.dumps(p, sort_keys=True).encode("utf-8")
    return hashlib.sha256(s).hexdigest()[:12]

# -------------------- Windows helpers (PowerShell) --------------------
def ps_run(cmd: str) -> str:
    if not is_windows():
        return ""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            text=True,
            errors="ignore"
        )
        return out.strip()
    except Exception:
        return ""

def apex_process_running() -> bool:
    if not is_windows():
        return False
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
    except Exception:
        return {"title": "", "process": ""}

def get_apex_cpu_pct_sample(window_s: float = 0.5) -> float:
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
    except Exception:
        return 0.0
        
def is_windows() -> bool:
    return platform.system().lower().startswith("win")

def ping_sample(host: str = "1.1.1.1", count: int = 10) -> Tuple[Optional[int], Optional[float]]:
    try:
        if is_windows():
            cmd = ["ping", "-n", str(count), host]
        else:
            cmd = ["ping", "-c", str(count), host]

        out = subprocess.check_output(cmd, text=True, errors="ignore")
    except Exception:
        return None, None

    loss = None
    # Windows: Lost = X (Y% loss)
    m = re.search(r"Lost = \d+ \((\d+)% loss\)", out, re.IGNORECASE)
    if m:
        loss = float(m.group(1))

    # Linux/mac: X% packet loss
    if loss is None:
        m = re.search(r"(\d+(?:\.\d+)?)%\s*packet loss", out, re.IGNORECASE)
        if m:
            loss = float(m.group(1))

    avg = None
    # Windows: Average = 12ms
    m2 = re.search(r"Average = (\d+)ms", out, re.IGNORECASE)
    if m2:
        avg = int(m2.group(1))

    # Linux/mac: rtt min/avg/max/mdev = 10.0/12.0/...
    if avg is None:
        m3 = re.search(r"=\s*[\d\.]+/([\d\.]+)/", out)
        if m3:
            avg = int(float(m3.group(1)))

    return avg, loss

# -------------------- Match Monitor (heuristic) --------------------
def monitor_tick(state: Dict[str, Any]) -> Dict[str, Any]:
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

    START_STREAK = int(state.get("start_streak_needed", 3))
    END_STREAK = int(state.get("end_streak_needed", 6))

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
    if not samples:
        return 0.0, 0.0
    avg = sum(samples) / len(samples)
    peak = max(samples)
    return round(avg, 2), round(peak, 2)

def find_similar_entries(logs: List[Dict[str, Any]], sig: str, hdr_mode: str) -> List[Dict[str, Any]]:
    return [x for x in logs if x.get("settings_signature") == sig and x.get("hdr_mode") == hdr_mode]

def compare_vs_similar(similar: List[Dict[str, Any]], current: Dict[str, Any]) -> str:
    if not similar:
        return "No prior similar sessions found."

    def mean_of(key: str) -> Optional[float]:
        vals = []
        for s in similar:
            v = s.get(key, None)
            try:
                if v is None or v == "":
                    continue
                vals.append(float(v))
            except Exception:
                continue
        if not vals:
            return None
        return sum(vals) / len(vals)

    cur_cpu = float(current.get("cpu_avg_pct", 0) or 0)
    cur_ping = current.get("ping_ms", None)
    cur_loss = current.get("packet_loss_pct", None)
    cur_fps = current.get("avg_fps", None)
    cur_1l = current.get("one_percent_low", None)

    avg_cpu = mean_of("cpu_avg_pct")
    avg_ping = mean_of("ping_ms")
    avg_loss = mean_of("packet_loss_pct")
    avg_fps = mean_of("avg_fps")
    avg_1l = mean_of("one_percent_low")

    parts = []
    if avg_cpu is not None:
        parts.append(f"CPU avg: {cur_cpu:.2f}% vs {avg_cpu:.2f}% ({cur_cpu-avg_cpu:+.2f})")
    if (cur_ping not in (None, "")) and (avg_ping is not None):
        parts.append(f"Ping: {int(cur_ping)}ms vs {avg_ping:.1f}ms ({int(cur_ping)-avg_ping:+.1f})")
    if (cur_loss not in (None, "")) and (avg_loss is not None):
        try:
            cur_loss_f = float(cur_loss)
            parts.append(f"Loss: {cur_loss_f:.1f}% vs {avg_loss:.1f}% ({cur_loss_f-avg_loss:+.1f})")
        except Exception:
            pass
    if (cur_fps not in (None, "")) and (avg_fps is not None):
        try:
            cur_fps_f = float(cur_fps)
            parts.append(f"Avg FPS: {cur_fps_f:.1f} vs {avg_fps:.1f} ({cur_fps_f-avg_fps:+.1f})")
        except Exception:
            pass
    if (cur_1l not in (None, "")) and (avg_1l is not None):
        try:
            cur_1l_f = float(cur_1l)
            parts.append(f"1% Low: {cur_1l_f:.1f} vs {avg_1l:.1f} ({cur_1l_f-avg_1l:+.1f})")
        except Exception:
            pass

    return " | ".join(parts) if parts else "Similar sessions exist, but not enough comparable numeric fields logged yet."

# -------------------- Auto Notes + Suggestions --------------------
def make_suggestions(profile: Dict[str, Any]) -> List[str]:
    suggestions: List[str] = []
    t = profile.get("toggles", {})
    targets = profile.get("targets", {})
    fps_target = int(targets.get("fpsTarget", 0) or 0)
    refresh = int(targets.get("refreshHz", 0) or 0)

    if refresh >= 120 and fps_target >= refresh:
        suggestions.append("Cap FPS to 2–3 below refresh (e.g., 237 for 240Hz) for VRR/Reflex consistency.")

    if t.get("autoHdrOn") and t.get("rtxHdrOn"):
        suggestions.append("Disable one: Auto HDR OR RTX HDR. Stacking can reduce clarity (double tone-map).")

    if not t.get("vsyncInGameOff"):
        suggestions.append("Turn in-game V-Sync OFF to reduce input latency (competitive baseline).")

    if not t.get("reflexBoostOn"):
        suggestions.append("Enable Reflex + Boost to reduce latency and stabilize pacing.")

    return suggestions[:6]

def auto_write_notes(profile: Dict[str, Any], last_entry: Dict[str, Any], compare_text: str, suggestions: List[str]) -> str:
    t = profile.get("toggles", {})
    targets = profile.get("targets", {})
    launch = build_launch_string(profile.get("launchOptions", []))
    hdr_label = hdr_method_label(t)

    lines = []
    lines.append("=== CURRENT COMP SETUP ===")
    lines.append(f"Refresh/FPS cap: {int(targets.get('refreshHz',0))}Hz / {int(targets.get('fpsTarget',0))} FPS")
    lines.append(f"VRR: {'ON' if t.get('gsyncOn') else 'OFF'} | V-Sync (in-game): {'OFF' if t.get('vsyncInGameOff') else 'ON'} | Reflex: {'ON+Boost' if t.get('reflexBoostOn') else 'OFF'}")
    lines.append(f"HDR path: {hdr_label}")
    lines.append(f"Launch: {launch if launch else '(none)'}")
    lines.append("")
    lines.append("=== LAST MATCH AUTO-LOG ===")
    lines.append(
        f"{last_entry.get('match_startISO','')} → {last_entry.get('match_endISO','')} "
        f"({last_entry.get('duration_s','')}s) | CPU avg {last_entry.get('cpu_avg_pct','')}% peak {last_entry.get('cpu_peak_pct','')}% | "
        f"Ping {last_entry.get('ping_ms','')}ms | Loss {last_entry.get('packet_loss_pct','')}% | "
        f"AvgFPS {last_entry.get('avg_fps','')} | 1%Low {last_entry.get('one_percent_low','')}"
    )
    lines.append(f"Compare: {compare_text}")
    if last_entry.get("notes"):
        lines.append(f"Session note: {last_entry.get('notes')}")
    lines.append("")
    lines.append("=== NEXT SUGGESTIONS ===")
    if suggestions:
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")
    else:
        lines.append("No changes suggested. Keep baseline and log more matches.")
    return "\n".join(lines)

# -------------------- Trash Bin (move-first; delete only on confirm) --------------------
def list_files_recursive(root: str) -> List[str]:
    out = []
    for base, _, files in os.walk(root):
        for f in files:
            out.append(os.path.join(base, f))
    return out

def safe_move_to_trash(path: str) -> Tuple[bool, str]:
    """
    Moves a file into today's trash folder. Never deletes here.
    """
    try:
        if not os.path.exists(path) or not os.path.isfile(path):
            return False, "Not a file."
        os.makedirs(TRASH_TODAY_DIR, exist_ok=True)
        name = os.path.basename(path)
        dst = os.path.join(TRASH_TODAY_DIR, name)
        # Avoid overwriting
        if os.path.exists(dst):
            stem, ext = os.path.splitext(name)
            dst = os.path.join(TRASH_TODAY_DIR, f"{stem}_{dt.datetime.now().strftime('%H%M%S')}{ext}")
        os.replace(path, dst)
        return True, dst
    except Exception as e:
        return False, str(e)

def safe_empty_trash_today() -> Tuple[int, int]:
    """
    Deletes ONLY files inside today's trash folder.
    """
    files_deleted = 0
    dirs_deleted = 0
    if not os.path.abspath(TRASH_TODAY_DIR).startswith(os.path.abspath(TRASHBIN_DIR)):
        return 0, 0
    if not os.path.exists(TRASH_TODAY_DIR):
        return 0, 0

    for p in list_files_recursive(TRASH_TODAY_DIR):
        try:
            os.remove(p)
            files_deleted += 1
        except Exception:
            pass

    for base, dirs, _ in os.walk(TRASH_TODAY_DIR, topdown=False):
        for d in dirs:
            dp = os.path.join(base, d)
            try:
                os.rmdir(dp)
                dirs_deleted += 1
            except Exception:
                pass
    try:
        os.rmdir(TRASH_TODAY_DIR)
        dirs_deleted += 1
    except Exception:
        pass
    os.makedirs(TRASH_TODAY_DIR, exist_ok=True)
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
    """
    Returns counts/sizes for a directory without reading file contents.
    """
    total_files = 0
    total_bytes = 0
    type_counts: Dict[str, int] = {}
    newest_iso = ""
    oldest_iso = ""
    truncated = False

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
            except Exception:
                pass
        if truncated:
            break

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

def bytes_human(n: int) -> str:
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"

def write_storage_map(results: List[Dict[str, Any]]):
    os.makedirs(STORAGE_DIR, exist_ok=True)
    doc = {
        "createdISO": now_iso(),
        "scope": "User-approved safe scan (no file contents).",
        "results": results,
    }
    safe_save_json(STORAGE_MAP_JSON, doc)

    # Flat CSV view
    rows = []
    for r in results:
        rows.append({
            "label": r.get("label",""),
            "path": r.get("path",""),
            "exists": r.get("exists",""),
            "files": r.get("total_files",""),
            "size_bytes": r.get("total_bytes",""),
            "size_human": bytes_human(int(r.get("total_bytes",0) or 0)),
            "newest_modifiedISO": r.get("newest_modifiedISO",""),
            "oldest_modifiedISO": r.get("oldest_modifiedISO",""),
            "truncated": r.get("truncated",""),
        })
    with open(STORAGE_MAP_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["label","path"])
        w.writeheader()
        for row in rows:
            w.writerow(row)

# -------------------- OCR Detector (optional / safe-off) --------------------
def ocr_available() -> Tuple[bool, str]:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
        import mss  # noqa: F401
        return True, "OK"
    except Exception as e:
        return False, str(e)

def ocr_detect_end_screen_demo() -> Dict[str, Any]:
    """
    Safe demo: captures a full monitor image via mss and runs OCR.
    This is OFF by default and only runs when user clicks.
    """
    import pytesseract
    import mss
    from PIL import Image

    keywords = ["CHAMPION", "SQUAD ELIMINATED", "MATCH SUMMARY", "YOU ARE THE CHAMPION", "ELIMINATED"]
    with mss.mss() as sct:
        mon = sct.monitors[1]  # primary
        img = sct.grab(mon)
        im = Image.frombytes("RGB", img.size, img.rgb)

    text = pytesseract.image_to_string(im)
    upper = (text or "").upper()
    hits = [k for k in keywords if k in upper]
    return {"hits": hits, "text_preview": upper[:600]}

# -------------------- PresentMon CSV import (safe) --------------------
def parse_presentmon_csv(file_bytes: bytes) -> Dict[str, Any]:
    """
    Accepts a PresentMon CSV and computes Avg FPS and 1% low FPS if possible.
    PresentMon formats vary; we handle common columns:
      - "MsBetweenPresents" (frame time ms)
      - or "FPS" per-row
    """
    text = file_bytes.decode("utf-8-sig", errors="ignore")
    lines = text.splitlines()
    if len(lines) < 2:
        return {"ok": False, "error": "CSV too short."}

    reader = csv.DictReader(lines)
    fps_samples: List[float] = []
    ft_ms: List[float] = []

    for row in reader:
        # Common: MsBetweenPresents
        if "MsBetweenPresents" in row and row["MsBetweenPresents"]:
            try:
                ft_ms.append(float(row["MsBetweenPresents"]))
            except Exception:
                pass
        # Alternate: FPS
        if "FPS" in row and row["FPS"]:
            try:
                fps_samples.append(float(row["FPS"]))
            except Exception:
                pass

    # Derive FPS from frame times if needed
    if not fps_samples and ft_ms:
        for ms in ft_ms:
            if ms > 0:
                fps_samples.append(1000.0 / ms)

    if not fps_samples:
        return {"ok": False, "error": "No usable FPS data found in CSV (expected FPS or MsBetweenPresents)."}
    fps_samples.sort()

    avg_fps = sum(fps_samples) / len(fps_samples)
    # 1% low = 1st percentile of FPS samples
    idx = max(0, int(len(fps_samples) * 0.01) - 1)
    one_percent_low = fps_samples[idx]

    return {
        "ok": True,
        "samples": len(fps_samples),
        "avg_fps": round(avg_fps, 2),
        "one_percent_low": round(one_percent_low, 2),
    }

# -------------------- Streamlit Setup --------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")

with st.sidebar:
    st.markdown(f"### {APP_TITLE}")
    st.caption(f"Version: {APP_VERSION}")
    st.markdown(f"[Report a bug]({REPO_ISSUES_URL})")
    st.caption("Include: steps + expected vs actual + screenshot if possible.")


if "profile" not in st.session_state:
    loaded = safe_load_json(AUTOSAVE_PATH)
    st.session_state.profile = loaded if loaded else deep_copy(DEFAULT_PROFILE)

if "monitor_state" not in st.session_state:
    st.session_state.monitor_state = {
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
    }

if "scan_plan" not in st.session_state:
    st.session_state.scan_plan = deep_copy(SAFE_SCAN_PRESETS)

if "storage_map" not in st.session_state:
    st.session_state.storage_map = safe_load_json(STORAGE_MAP_JSON) or {}

profile: Dict[str, Any] = st.session_state.profile

# -------------------- Header --------------------
st.title(APP_TITLE)
st.caption(
    f"Profile: {profile['meta']['profileName']} • Monitor: {profile['meta']['monitor']} • "
    f"GPU: {profile['meta']['gpu']} • Updated: {profile['meta']['lastUpdatedISO']}"
)

h1, h2, h3, h4, h5 = st.columns([2, 1, 1, 1, 1])

with h1:
    profile["meta"]["profileName"] = st.text_input("Profile name", profile["meta"]["profileName"])

with h2:
    if st.button("Snapshot NOW (dedup)", use_container_width=True):
        saved, path = save_unique_json(SNAP_DIR, profile, "manual", "SNAP")
        st.success(f"Snapshot saved: {path}") if saved else st.info(f"Duplicate already exists: {path}")

with h3:
    if st.button("Reset (snapshot first)", use_container_width=True):
        save_unique_json(SNAP_DIR, profile, "before_reset", "SNAP")
        st.session_state.profile = deep_copy(DEFAULT_PROFILE)
        safe_save_json(AUTOSAVE_PATH, st.session_state.profile)
        st.rerun()

with h4:
    # Privacy-safe export option
    sanitize = bool(profile.get("privacy", {}).get("sanitize_exports", True))

    def sanitized_profile_copy(p: Dict[str, Any]) -> Dict[str, Any]:
        out = deep_copy(p)
        # remove/neutralize anything that looks like user-specific paths
        # (we do not store much, but this keeps it safe for public sharing)
        out.setdefault("meta", {})
        out["meta"]["notes"] = "(notes will be generated per user)"
        # Any future fields that could contain paths/machine info should be stripped here.
        return out

    export_obj = sanitized_profile_copy(profile) if sanitize else profile
    export_name = f"apex_profile_{slug(profile['meta']['profileName']).lower()}.json"
    export_name = ("SANITIZED_" + export_name) if sanitize else export_name

    st.download_button(
        "Export JSON",
        data=json.dumps(export_obj, indent=2),
        file_name=export_name,
        mime="application/json",
        use_container_width=True,
    )

with h5:
    up = st.file_uploader("Import JSON (profile or scan.json)", type=["json"], label_visibility="collapsed")
    if up:
        try:
            raw = up.read()
            text = raw.decode("utf-8-sig", errors="strict")
            data = json.loads(text)

            is_scan = isinstance(data, dict) and ("scan" in data) and ("system" in data)
            is_profile = isinstance(data, dict) and ("meta" in data) and ("targets" in data) and ("toggles" in data)

            if is_scan:
                st.session_state["_scan"] = data
                scan_path = os.path.join(DAILY_TEMP_DIR, f"scan_import_{dt.datetime.now().strftime('%H%M%S')}.json")
                safe_save_json(scan_path, data)
                st.success("Scan imported. Open Scan/Autofill tab to apply it.")
            elif is_profile:
                save_unique_json(SNAP_DIR, profile, "before_import_profile", "SNAP")
                st.session_state.profile = data
                safe_save_json(AUTOSAVE_PATH, st.session_state.profile)
                st.success("Profile imported.")
                st.rerun()
            else:
                st.error("Unknown JSON type. Import a profile JSON or a scan.json bundle.")
        except Exception as e:
            st.error(f"Import failed: {e}")

profile["meta"]["notes"] = st.text_area("Notes (auto-updated after matches)", profile["meta"].get("notes", ""), height=220)
st.divider()

# -------------------- Tabs --------------------
tab_apex, tab_match, tab_hdr, tab_presets, tab_perf, tab_net, tab_scan, tab_storage, tab_trash, tab_ocr, tab_presentmon, tab_library = st.tabs(
    [
        "Apex",
        "Match Monitor",
        "HDR Setup",
        "Presets",
        "Performance Logs",
        "Network",
        "Scan/Autofill",
        "Storage Map",
        "Trash Bin",
        "OCR Detector (optional)",
        "PresentMon Import (optional)",
        "SOP/SCOP + Tutorials",
    ]
)

# -------------------- Apex Tab --------------------
with tab_apex:
    st.subheader("Performance Targets")
    t1, t2, t3 = st.columns(3)
    with t1:
        profile["targets"]["refreshHz"] = st.number_input("Refresh (Hz)", 60, 360, int(profile["targets"]["refreshHz"]), 1)
    with t2:
        profile["targets"]["fpsTarget"] = st.number_input("FPS Target", 60, 600, int(profile["targets"]["fpsTarget"]), 1)
    with t3:
        profile["targets"]["latencyGoalMs"] = st.number_input("Latency Goal (ms)", 1, 100, int(profile["targets"]["latencyGoalMs"]), 1)

    st.subheader("System Toggles")
    g1, g2, g3 = st.columns(3)
    with g1:
        profile["toggles"]["hdrWindowsOn"] = st.toggle("Windows HDR", bool(profile["toggles"]["hdrWindowsOn"]))
        profile["toggles"]["autoHdrOn"] = st.toggle("Auto HDR", bool(profile["toggles"]["autoHdrOn"]))
    with g2:
        profile["toggles"]["rtxHdrOn"] = st.toggle("RTX HDR", bool(profile["toggles"]["rtxHdrOn"]))
        profile["toggles"]["gsyncOn"] = st.toggle("G-SYNC / VRR", bool(profile["toggles"]["gsyncOn"]))
    with g3:
        profile["toggles"]["vsyncInGameOff"] = st.toggle("In-game V-Sync OFF", bool(profile["toggles"]["vsyncInGameOff"]))
        profile["toggles"]["reflexBoostOn"] = st.toggle("Reflex (+Boost)", bool(profile["toggles"]["reflexBoostOn"]))

    st.subheader("Steam Launch Options")
    left, right = st.columns([2, 1])
    with left:
        for i, opt in enumerate(profile["launchOptions"]):
            cols = st.columns([1, 2, 3])
            with cols[0]:
                profile["launchOptions"][i]["enabled"] = st.checkbox(opt["key"], bool(opt["enabled"]), key=f"lo_{i}")
            with cols[1]:
                st.code(opt["key"], language="text")
            with cols[2]:
                st.caption(opt.get("note", ""))

    launch_string = build_launch_string(profile["launchOptions"])
    with right:
        st.caption("Current launch string")
        st.code(launch_string if launch_string else "(none)", language="text")
        st.download_button("Download launch.txt", data=launch_string, file_name="apex_launch_options.txt", use_container_width=True)
        st.info("Safety: avoid -high and random outdated DX flags. Change one thing at a time.")

# -------------------- Match Monitor Tab --------------------
with tab_match:
    st.subheader("Match Monitor (Auto-detect start/end — safe heuristic)")
    if not is_windows():
    st.warning("Match Monitor is Windows-only (uses PowerShell + foreground window checks). Disabled on Streamlit Cloud.")
    st.stop()
    
    st.caption(
        "Safe mode: no injection, no memory reads. Uses Apex process + foreground window + timing streaks. "
        "End events are approximate."
    )

    ms = st.session_state.monitor_state

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ms["enabled"] = st.toggle("Monitoring enabled", bool(ms.get("enabled", False)))
    with c2:
        ms["poll_seconds"] = st.number_input("Poll interval (sec)", 1, 10, int(ms.get("poll_seconds", 3)), 1)
    with c3:
        ms["start_streak_needed"] = st.number_input("Start streak (ticks)", 1, 10, int(ms.get("start_streak_needed", 3)), 1)
    with c4:
        ms["end_streak_needed"] = st.number_input("End streak (ticks)", 2, 20, int(ms.get("end_streak_needed", 6)), 1)

    if ms["enabled"]:
        st.autorefresh(interval=int(ms["poll_seconds"]) * 1000, key="autorefresh_match")
        ms = monitor_tick(ms)
        st.session_state.monitor_state = ms

        just_ended = (ms.get("match_endISO") and (not ms.get("in_match")))
        if just_ended and ms.get("match_startISO"):
            start_dt = dt.datetime.fromisoformat(ms["match_startISO"])
            end_dt = dt.datetime.fromisoformat(ms["match_endISO"])
            duration_s = int((end_dt - start_dt).total_seconds())
            cpu_avg, cpu_peak = compute_cpu_stats(ms.get("cpu_samples", []))

            ping_ms, loss_pct = ping_sample("1.1.1.1", 10)

            sig = settings_signature(profile)
            hdr_mode = hdr_method_label(profile.get("toggles", {}))

            entry = {
                "createdISO": now_iso(),
                "match_startISO": ms["match_startISO"],
                "match_endISO": ms["match_endISO"],
                "duration_s": duration_s,
                "mode": "",
                "map": "",
                "hdr_mode": hdr_mode,
                "avg_fps": "",
                "one_percent_low": "",
                "ping_ms": ping_ms if ping_ms is not None else "",
                "packet_loss_pct": loss_pct if loss_pct is not None else "",
                "cpu_avg_pct": cpu_avg,
                "cpu_peak_pct": cpu_peak,
                "input_feel_1_10": "",
                "settings_signature": sig,
                "compare_to_similar": "",
                "notes": "",
            }

            logs = profile.get("performanceLogs", [])
            similar = find_similar_entries(logs, sig, hdr_mode)
            compare_text = compare_vs_similar(similar, entry)
            entry["compare_to_similar"] = compare_text

            profile.setdefault("performanceLogs", []).insert(0, entry)
            suggestions = make_suggestions(profile)
            profile["meta"]["notes"] = auto_write_notes(profile, entry, compare_text, suggestions)

            artifact_path = os.path.join(DAILY_TEMP_DIR, f"match_{dt.datetime.now().strftime('%H%M%S')}.json")
            safe_save_json(artifact_path, {"match_entry": entry, "monitor_state": deep_copy(ms)})

            ms["match_startISO"] = ""
            ms["match_endISO"] = ""
            ms["cpu_samples"] = []
            ms["cpu_peak"] = 0.0
            st.session_state.monitor_state = ms

            safe_save_json(AUTOSAVE_PATH, profile)
            st.success("Match ended → auto-logged → compared → Notes updated.")

    st.divider()
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Apex running", "YES" if ms.get("apex_running") else "NO")
    with s2:
        st.metric("Apex foreground", "YES" if ms.get("apex_foreground") else "NO")
    with s3:
        st.metric("In-match state", "YES" if ms.get("in_match") else "NO")
    st.caption(f"Foreground process: {ms.get('fg_process','')}")
    st.caption(f"Foreground title: {ms.get('fg_title','')[:120]}")

# -------------------- HDR Setup Tab --------------------
with tab_hdr:
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

    st.markdown("### Apex behavior")
    for x in profile["hdrSetup"]["apexBehavior"]:
        st.write(f"- {x}")

# -------------------- Presets Tab --------------------
with tab_presets:
    st.subheader("Competitive Presets")
    preset_names = list(profile["presets"].keys())
    choice = st.radio("Choose preset", preset_names, horizontal=True)
    st.json(profile["presets"][choice])

# -------------------- Performance Logs Tab --------------------
with tab_perf:
    st.subheader("Performance Logs")
    logs = profile.get("performanceLogs", [])

    cA, cB = st.columns([1, 1])
    with cA:
        st.download_button(
            "Export CSV",
            data=logs_to_csv_bytes(logs),
            file_name="apex_match_logs.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with cB:
        st.download_button(
            "Export JSON",
            data=json.dumps(logs, indent=2),
            file_name="apex_match_logs.json",
            mime="application/json",
            use_container_width=True,
        )

    if logs:
        st.dataframe(logs, use_container_width=True, hide_index=True)
    else:
        st.info("No logs yet. Enable Match Monitor and play a match.")

# -------------------- Network Tab --------------------
with tab_net:
    st.subheader("Network")
    net = profile.setdefault("network", deep_copy(DEFAULT_PROFILE["network"]))

    a1, a2, a3 = st.columns(3)
    with a1:
        net["isp"] = st.text_input("ISP", value=net.get("isp", ""))
        net["connection"] = st.selectbox("Connection", ["Ethernet", "Wi-Fi"], index=0 if net.get("connection") == "Ethernet" else 1)
        net["dns"] = st.text_input("DNS (Auto / 1.1.1.1 / 8.8.8.8 etc.)", value=net.get("dns", "Auto"))
    with a2:
        net["router_model"] = st.text_input("Router model", value=net.get("router_model", ""))
        net["modem_model"] = st.text_input("Modem model", value=net.get("modem_model", ""))
        net["mtu"] = st.text_input("MTU (optional)", value=net.get("mtu", ""))
    with a3:
        net["qos_enabled"] = st.text_input("QoS / SQM enabled? (Yes/No/Unknown)", value=net.get("qos_enabled", ""))
        net["bufferbloat_grade"] = st.text_input("Bufferbloat grade (A/B/C/Unknown)", value=net.get("bufferbloat_grade", ""))
        net["notes"] = st.text_area("Network notes", value=net.get("notes", ""), height=90)

    st.divider()
    st.subheader("Quick ping sample")
    if st.button("Ping 1.1.1.1 (10 packets)", use_container_width=True):
        p, l = ping_sample("1.1.1.1", 10)
        st.write(f"Avg ping: {p}ms | Loss: {l}%")

# -------------------- Scan/Autofill Tab --------------------
with tab_scan:
    st.subheader("Scan/Autofill (safe)")
    st.caption("Import scan.json (from your exporter) using Import JSON (top right).")

    scanned = st.session_state.get("_scan")
    if scanned:
        st.json(scanned)
        if st.button("Apply scan → profile fields (safe)", use_container_width=True):
            sysinfo = scanned.get("system", {})
            gpus = sysinfo.get("gpus", [])
            dns = sysinfo.get("dnsServers", [])

            if isinstance(gpus, list) and gpus:
                gpu0 = gpus[0] if isinstance(gpus[0], dict) else {}
                name = gpu0.get("Name")
                rr = gpu0.get("CurrentRefreshRate")
                if name:
                    profile["meta"]["gpu"] = name
                if rr is not None:
                    try:
                        profile["targets"]["refreshHz"] = int(rr)
                    except Exception:
                        pass

            if isinstance(dns, list) and dns:
                profile.setdefault("network", {}).setdefault("dns", "")
                profile["network"]["dns"] = ", ".join([str(x) for x in dns[:3]])

            safe_save_json(AUTOSAVE_PATH, profile)
            st.success("Scan applied to profile (GPU/refresh/DNS).")
            st.rerun()
    else:
        st.info("No scan loaded yet.")

# -------------------- Storage Map Tab --------------------
with tab_storage:
    st.subheader("Storage Map (runs on-demand)")
    st.caption(
        "This does NOT read file contents. It only counts files, totals sizes, file types, and date ranges. "
        "It scans ONLY the locations you approve below."
    )

    st.markdown("### Approved scan locations (edit + toggle)")
    plan = st.session_state.scan_plan

    for i, item in enumerate(plan):
        c1, c2, c3 = st.columns([1, 2, 5])
        with c1:
            plan[i]["enabled"] = st.checkbox("Scan", value=bool(item.get("enabled", True)), key=f"scan_en_{i}")
        with c2:
            plan[i]["label"] = st.text_input("Label", value=item.get("label",""), key=f"scan_label_{i}")
        with c3:
            plan[i]["path"] = st.text_input("Path", value=item.get("path",""), key=f"scan_path_{i}")

    st.session_state.scan_plan = plan

    st.divider()
    st.markdown("### Consent + run")
    consent = st.checkbox("I approve scanning ONLY the enabled paths shown above.", value=False)
    max_files = st.number_input("Safety limit: max files per path", 500, 200000, 25000, 500)

    if consent and st.button("Build / Update Storage Map NOW", type="primary", use_container_width=True):
        results = []
        for it in plan:
            if not it.get("enabled"):
                continue
            path = it.get("path","").strip()
            label = it.get("label","").strip() or path
            if not path:
                continue
            r = dir_stats(path, max_files=int(max_files))
            r["label"] = label
            results.append(r)

        write_storage_map(results)
        st.session_state.storage_map = safe_load_json(STORAGE_MAP_JSON) or {}
        # store the map build artifact in TempBin (safe to trash later)
        safe_save_json(os.path.join(DAILY_TEMP_DIR, f"storage_map_build_{dt.datetime.now().strftime('%H%M%S')}.json"), st.session_state.storage_map)
        st.success("Storage map updated.")

    st.divider()
    st.markdown("### Current Storage Map (latest)")
    current = st.session_state.storage_map or safe_load_json(STORAGE_MAP_JSON) or {}
    if current and "results" in current:
        st.caption(f"Created: {current.get('createdISO','')}")
        flat = []
        for r in current.get("results", []):
            flat.append({
                "label": r.get("label",""),
                "path": r.get("path",""),
                "exists": r.get("exists",""),
                "files": r.get("total_files",""),
                "size": bytes_human(int(r.get("total_bytes",0) or 0)),
                "newest": r.get("newest_modifiedISO",""),
                "oldest": r.get("oldest_modifiedISO",""),
                "truncated": r.get("truncated",""),
            })
        st.dataframe(flat, use_container_width=True, hide_index=True)

        if os.path.exists(STORAGE_MAP_JSON):
            st.download_button("Download storage_map.json", data=open(STORAGE_MAP_JSON, "rb").read(), file_name="storage_map.json", use_container_width=True)
        if os.path.exists(STORAGE_MAP_CSV):
            st.download_button("Download storage_map_view.csv", data=open(STORAGE_MAP_CSV, "rb").read(), file_name="storage_map_view.csv", use_container_width=True)

        with st.expander("File type breakdown"):
            for r in current.get("results", []):
                st.markdown(f"**{r.get('label','')}**")
                tc = r.get("type_counts", {})
                if tc:
                    st.json(tc)
                else:
                    st.write("(none)")
    else:
        st.info("No storage map yet. Approve and run the scan above.")

# -------------------- Trash Bin Tab --------------------
with tab_trash:
    st.subheader("Trash Bin (move-first, delete-last)")
    st.caption(
        "Workflow: (1) Move today’s temp artifacts into Trash Bin, (2) Review, (3) Empty Trash when you decide. "
        "This protects you from accidental deletes."
    )

    st.markdown("### Today’s TempBin")
    st.code(DAILY_TEMP_DIR, language="text")
    temp_files = list_files_recursive(DAILY_TEMP_DIR) if os.path.exists(DAILY_TEMP_DIR) else []
    if temp_files:
        st.write(f"{len(temp_files)} temp files found.")
        st.dataframe([{"temp_file": f.replace(BASE_DIR + os.sep, "")} for f in temp_files], use_container_width=True, hide_index=True)
    else:
        st.info("No temp files today yet.")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Move ALL TempBin files → Trash Bin", use_container_width=True):
            moved = 0
            for f in list(temp_files):
                ok, _dst = safe_move_to_trash(f)
                if ok:
                    moved += 1
            st.success(f"Moved {moved} files to Trash Bin.")

    with colB:
        st.write("")

    st.divider()
    st.markdown("### Today’s Trash Bin")
    st.code(TRASH_TODAY_DIR, language="text")
    trash_files = list_files_recursive(TRASH_TODAY_DIR) if os.path.exists(TRASH_TODAY_DIR) else []
    if trash_files:
        st.write(f"{len(trash_files)} files in trash.")
        st.dataframe([{"trash_file": f.replace(BASE_DIR + os.sep, "")} for f in trash_files], use_container_width=True, hide_index=True)
    else:
        st.info("Trash is empty.")

    st.divider()
    st.markdown("### Empty Trash (deletes files inside today’s Trash Bin only)")
    confirm = st.text_input("Type DELETE to enable emptying Trash", value="")
    if confirm == "DELETE":
        if st.button("EMPTY today’s Trash Bin NOW", type="primary", use_container_width=True):
            files_deleted, dirs_deleted = safe_empty_trash_today()
            st.success(f"Deleted {files_deleted} files; removed {dirs_deleted} directories (Trash Bin only).")
    else:
        st.warning("Deletion locked. Type DELETE exactly.")

# -------------------- OCR Detector Tab (optional) --------------------
with tab_ocr:
    st.subheader("OCR End-Screen Detector (optional)")
    ok, msg = ocr_available()
    if not ok:
        st.error("OCR deps not installed.")
        st.code(
            "pip install pytesseract pillow mss\n"
            "Also install Tesseract OCR:\n"
            "  - Windows: install 'tesseract-ocr' and add it to PATH\n",
            language="text"
        )
        st.caption(f"Missing/issue: {msg}")
    else:
        st.success("OCR dependencies detected.")
        st.caption("This is a safe demo tool (screen capture + OCR). It does not inject into Apex.")
        if st.button("Run OCR scan NOW (1 capture)", use_container_width=True):
            try:
                res = ocr_detect_end_screen_demo()
                st.write("Detected keyword hits:", res.get("hits", []))
                st.text_area("OCR preview (upper)", res.get("text_preview",""), height=220)
                # save artifact to TempBin
                safe_save_json(os.path.join(DAILY_TEMP_DIR, f"ocr_capture_{dt.datetime.now().strftime('%H%M%S')}.json"), res)
            except Exception as e:
                st.error(f"OCR scan failed: {e}")

# -------------------- PresentMon Import Tab (optional) --------------------
with tab_presentmon:
    st.subheader("PresentMon FPS Import (optional)")
    st.caption(
        "This does NOT run PresentMon. It imports a PresentMon CSV you already captured, "
        "computes Avg FPS + 1% Low, and lets you apply it to the latest match log."
    )
    upcsv = st.file_uploader("Upload PresentMon CSV", type=["csv"])
    if upcsv:
        result = parse_presentmon_csv(upcsv.read())
        if result.get("ok"):
            st.success(f"Parsed {result['samples']} samples → Avg FPS {result['avg_fps']} | 1% Low {result['one_percent_low']}")
            if st.button("Apply to latest match entry", use_container_width=True):
                logs = profile.get("performanceLogs", [])
                if not logs:
                    st.error("No match logs exist yet.")
                else:
                    logs[0]["avg_fps"] = result["avg_fps"]
                    logs[0]["one_percent_low"] = result["one_percent_low"]
                    # refresh compare + notes
                    sig = logs[0].get("settings_signature", settings_signature(profile))
                    hdr_mode = logs[0].get("hdr_mode", hdr_method_label(profile.get("toggles", {})))
                    similar = find_similar_entries(logs[1:], sig, hdr_mode)
                    compare_text = compare_vs_similar(similar, logs[0])
                    logs[0]["compare_to_similar"] = compare_text
                    suggestions = make_suggestions(profile)
                    profile["meta"]["notes"] = auto_write_notes(profile, logs[0], compare_text, suggestions)
                    safe_save_json(AUTOSAVE_PATH, profile)
                    safe_save_json(os.path.join(DAILY_TEMP_DIR, f"presentmon_import_{dt.datetime.now().strftime('%H%M%S')}.json"), result)
                    st.success("Applied FPS metrics to latest match entry.")
        else:
            st.error(result.get("error", "Parse failed."))

# -------------------- SOP/SCOP + Tutorials Tab --------------------
with tab_library:
    st.subheader("SOP/SCOP + Tutorials")
    mode = st.radio("Library", ["Settings (Windows/NVIDIA/Apex)", "Steam Launch Options"], horizontal=True)
    query = st.text_input("Search", value="")

    lib = SETTING_LIBRARY if mode == "Settings (Windows/NVIDIA/Apex)" else LAUNCH_OPTION_LIBRARY
    keys = list(lib.keys())
    if query.strip():
        q = query.strip().lower()
        keys = [k for k in keys if q in k.lower() or q in lib[k]["title"].lower()]

    if not keys:
        st.info("No matches.")
    else:
        selected = st.selectbox("Select", keys, format_func=lambda k: lib[k]["title"])
        item = lib[selected]

        st.markdown(f"## {item['title']}")
        st.markdown(f"**What it does:** {item.get('what_it_does','')}")

        st.markdown("### Interactions / Dependencies")
        for x in item.get("interactions", []):
            st.write(f"- {x}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Pros")
            for x in item.get("pros", []):
                st.write(f"- {x}")
            st.markdown("### Cons")
            for x in item.get("cons", []):
                st.write(f"- {x}")
            st.markdown("### Negatives / Pitfalls")
            for x in item.get("negatives", []):
                st.write(f"- {x}")

        with c2:
            st.markdown("### SOP (Step-by-step)")
            for i, step in enumerate(item.get("sop", []), start=1):
                st.write(f"{i}. {step}")

            scop = item.get("scop", {})
            st.markdown("### SCOP (Scope/Impact)")
            st.write(f"**Risk level:** {scop.get('risk_level','Unknown')}")
            if scop.get("affects"):
                st.markdown("**Affects:**")
                for a in scop["affects"]:
                    st.write(f"- {a}")
            if scop.get("verify"):
                st.markdown("**Verify:**")
                for v in scop["verify"]:
                    st.write(f"- {v}")
            if scop.get("rollback"):
                st.markdown("### Rollback")
                for r in scop["rollback"]:
                    st.write(f"- {r}")

# -------------------- Autosave --------------------
profile = bump_updated(profile)
st.session_state.profile = profile
safe_save_json(AUTOSAVE_PATH, st.session_state.profile)
