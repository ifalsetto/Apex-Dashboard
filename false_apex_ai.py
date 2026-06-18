from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
PROFILE_AUTOSAVE_FILE = "profile_autosave.json"
AI_REPORTS_DIR = "AI_Coach_Reports"


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def find_repo_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "apex_dashboard.py").exists():
            return candidate
    return current


def safe_load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else None
    except Exception:
        return None
    return None


def safe_save_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_dashboard_profile(repo_root: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
    root = repo_root or find_repo_root()
    path = root / PROFILE_AUTOSAVE_FILE
    return safe_load_json(path) or {}, path


def build_launch_string(launch_options: List[Dict[str, Any]]) -> str:
    return " ".join(
        str(item.get("key", "")).strip()
        for item in launch_options
        if isinstance(item, dict) and item.get("enabled")
    ).strip()


def settings_signature(profile: Mapping[str, Any]) -> str:
    payload = {
        "targets": profile.get("targets", {}),
        "toggles": profile.get("toggles", {}),
        "launch": build_launch_string(profile.get("launchOptions", [])),
    }
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def hdr_method_label(toggles: Mapping[str, Any]) -> str:
    if not toggles.get("hdrWindowsOn"):
        return "HDR OFF (SDR)"
    if toggles.get("rtxHdrOn"):
        return "RTX HDR"
    if toggles.get("autoHdrOn"):
        return "HDR ON (Auto HDR)"
    return "HDR ON"


def make_baseline_suggestions(profile: Mapping[str, Any]) -> List[str]:
    suggestions: List[str] = []
    toggles = profile.get("toggles", {}) if isinstance(profile.get("toggles", {}), dict) else {}
    targets = profile.get("targets", {}) if isinstance(profile.get("targets", {}), dict) else {}

    try:
        refresh = int(targets.get("refreshHz", 0) or 0)
        fps_target = int(targets.get("fpsTarget", 0) or 0)
    except Exception:
        refresh = 0
        fps_target = 0

    if refresh >= 120 and fps_target >= refresh:
        suggestions.append("Cap FPS 2-3 below refresh rate for VRR/Reflex consistency.")
    if toggles.get("autoHdrOn") and toggles.get("rtxHdrOn"):
        suggestions.append("Use Auto HDR or RTX HDR, not both, to avoid stacked tone mapping.")
    if not toggles.get("vsyncInGameOff", True):
        suggestions.append("Turn in-game V-Sync OFF for competitive latency baseline.")
    if not toggles.get("reflexBoostOn", True):
        suggestions.append("Enable NVIDIA Reflex + Boost for latency consistency.")

    return suggestions


def latest_performance_log(profile: Mapping[str, Any]) -> Dict[str, Any]:
    logs = profile.get("performanceLogs", [])
    if isinstance(logs, list) and logs:
        latest = logs[-1]
        return latest if isinstance(latest, dict) else {}
    return {}


def enabled_launch_options(profile: Mapping[str, Any]) -> List[Dict[str, Any]]:
    launch_options = profile.get("launchOptions", [])
    if not isinstance(launch_options, list):
        return []

    return [
        {
            "key": str(item.get("key", "")),
            "note": str(item.get("note", "")),
        }
        for item in launch_options
        if isinstance(item, dict) and item.get("enabled")
    ]


def build_apex_coach_context(profile: Mapping[str, Any], user_goal: str) -> Dict[str, Any]:
    toggles = profile.get("toggles", {}) if isinstance(profile.get("toggles", {}), dict) else {}
    targets = profile.get("targets", {}) if isinstance(profile.get("targets", {}), dict) else {}
    network = profile.get("network", {}) if isinstance(profile.get("network", {}), dict) else {}
    meta = profile.get("meta", {}) if isinstance(profile.get("meta", {}), dict) else {}

    return {
        "goal": user_goal.strip(),
        "profile": {
            "name": meta.get("profileName", "Unknown"),
            "lastUpdatedISO": meta.get("lastUpdatedISO", ""),
            "notes": meta.get("notes", ""),
        },
        "targets": targets,
        "toggles": toggles,
        "hdrMode": hdr_method_label(toggles),
        "enabledLaunchOptions": enabled_launch_options(profile),
        "launchString": build_launch_string(profile.get("launchOptions", [])),
        "network": network,
        "latestPerformanceLog": latest_performance_log(profile),
        "baselineSuggestions": make_baseline_suggestions(profile),
        "settingsSignature": settings_signature(profile),
    }


def get_openai_api_key(streamlit_secrets: Optional[Mapping[str, Any]] = None) -> str:
    if streamlit_secrets:
        try:
            value = streamlit_secrets.get("OPENAI_API_KEY", "")
            if value:
                return str(value).strip()
        except Exception:
            pass
    return os.environ.get("OPENAI_API_KEY", "").strip()


def generate_apex_ai_coach_report(
    profile: Mapping[str, Any],
    user_goal: str,
    model: str = OPENAI_MODEL_DEFAULT,
    streamlit_secrets: Optional[Mapping[str, Any]] = None,
) -> Tuple[bool, str]:
    if OpenAI is None:
        return False, "OpenAI package is not installed. Run `pip install -r requirements.txt`."

    api_key = get_openai_api_key(streamlit_secrets)
    if not api_key:
        return False, "Missing OPENAI_API_KEY. Add it to `.streamlit/secrets.toml` or your environment variables."

    context = build_apex_coach_context(profile, user_goal)

    system_prompt = """
You are the FalseTech Apex Performance Coach.

Rules:
- Focus on competitive Apex Legends improvement.
- Prioritize latency consistency, FPS stability, visibility, audio discipline, rotations, fight timing, and ranked decision-making.
- Give direct, practical recommendations.
- Do not recommend cheats, recoil scripts, macros, exploits, or anything that violates game rules.
- Do not recommend disabling critical Windows security, audio, input, networking, or anti-cheat services.
- If data is missing, say exactly what should be tracked next.
- Keep the output structured, direct, and useful.

Output format:
1. Current Read
2. Biggest Bottleneck
3. Settings / System Fixes
4. Gameplay Focus
5. Ranked Rules
6. Next Session Checklist
7. Data To Track Next
""".strip()

    user_prompt = f"""
User goal:
{user_goal.strip()}

Dashboard context JSON:
{json.dumps(context, indent=2, ensure_ascii=False, default=str)}
""".strip()

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.25,
        )
        report = response.choices[0].message.content or ""
        report = report.strip()
        if not report:
            return False, "OpenAI returned an empty report."
        return True, report
    except Exception as exc:
        return False, f"OpenAI coach failed: {exc}"


def append_report_to_profile(
    profile: Dict[str, Any],
    *,
    user_goal: str,
    report: str,
    model: str,
) -> Dict[str, Any]:
    profile.setdefault("aiCoachReports", [])
    if not isinstance(profile["aiCoachReports"], list):
        profile["aiCoachReports"] = []

    profile["aiCoachReports"].append(
        {
            "createdISO": now_iso(),
            "goal": user_goal,
            "report": report,
            "model": model,
            "settingsSignature": settings_signature(profile),
        }
    )
    profile.setdefault("meta", {})
    if isinstance(profile["meta"], dict):
        profile["meta"]["lastUpdatedISO"] = now_iso()
    return profile


def save_report_markdown(repo_root: Path, report: str) -> Path:
    day = dt.date.today().isoformat()
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = repo_root / AI_REPORTS_DIR / day
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"apex_ai_coach_{timestamp}.md"
    output_path.write_text(report + "\n", encoding="utf-8")
    return output_path
