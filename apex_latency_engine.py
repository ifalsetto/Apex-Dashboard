"""Latency source analyzer and live settings impact simulator.

The engine predicts and explains latency sources using only safe inputs:
manual values, OS/system metrics, user-selected settings, and historical logs.
It does not read Apex memory, automate input, modify game files, or interact
with anti-cheat systems.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class SettingsProfile:
    """Current or simulated settings profile."""

    name: str
    fps_target: float = 180.0
    refresh_hz: float = 240.0
    gpu_load_pct: float = 85.0
    cpu_load_pct: float = 45.0
    reflex_on: bool = True
    vsync_on: bool = False
    gsync_on: bool = False
    shadows_low: bool = True
    effects_low: bool = True
    texture_budget: str = "medium"
    audio_clarity_profile: bool = True


@dataclass(frozen=True)
class NetworkSample:
    """Safe network measurements entered by the user or measured externally."""

    idle_ping_ms: float = 35.0
    loaded_ping_ms: float = 45.0
    jitter_ms: float = 3.0
    packet_loss_pct: float = 0.0
    qos_enabled: bool = False
    connection_type: str = "Ethernet"


@dataclass(frozen=True)
class LatencyReport:
    """Serializable report for UI and export."""

    created_utc: str
    current_total_ms: float
    simulated_total_ms: float
    delta_ms: float
    primary_source: str
    risk_level: str
    recommendations: List[str] = field(default_factory=list)
    coaching_prompts: List[str] = field(default_factory=list)
    component_rows: List[Dict[str, Any]] = field(default_factory=list)
    safety_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def safe_float(value: Any, fallback: float = 0.0, minimum: float | None = None, maximum: float | None = None) -> float:
    """Convert values to bounded floats for stable UI calculations."""
    try:
        number = float(value)
    except Exception:
        number = fallback
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def frame_time_ms(fps: float) -> float:
    """Return milliseconds per frame."""
    fps = safe_float(fps, fallback=60.0, minimum=1.0, maximum=1000.0)
    return 1000.0 / fps


def estimate_render_latency_ms(profile: SettingsProfile) -> float:
    """Estimate local render/input latency from common setup indicators."""
    base = frame_time_ms(profile.fps_target)
    queue_penalty = 0.0

    if profile.gpu_load_pct >= 95:
        queue_penalty += base * 1.35
    elif profile.gpu_load_pct >= 90:
        queue_penalty += base * 0.85
    elif profile.gpu_load_pct >= 85:
        queue_penalty += base * 0.45

    if profile.cpu_load_pct >= 90:
        queue_penalty += base * 0.75
    elif profile.cpu_load_pct >= 80:
        queue_penalty += base * 0.35

    if profile.vsync_on:
        queue_penalty += base * 1.5
    if profile.reflex_on:
        queue_penalty -= base * 0.35
    if profile.gsync_on and not profile.vsync_on:
        queue_penalty -= base * 0.1

    return round(max(base, base + queue_penalty), 2)


def visibility_score(profile: SettingsProfile) -> int:
    """Simple 0-100 expected visibility score for settings comparison."""
    score = 65
    if profile.shadows_low:
        score += 10
    if profile.effects_low:
        score += 8
    if profile.texture_budget.lower() in {"medium", "high"}:
        score += 5
    if profile.audio_clarity_profile:
        score += 4
    if profile.gpu_load_pct >= 95:
        score -= 8
    return int(max(0, min(100, score)))


def network_queue_ms(sample: NetworkSample) -> float:
    """Estimate queueing/bufferbloat pressure from loaded vs idle ping."""
    idle = safe_float(sample.idle_ping_ms, 35.0, 0.0, 1000.0)
    loaded = safe_float(sample.loaded_ping_ms, idle, 0.0, 1500.0)
    return round(max(0.0, loaded - idle), 2)


def network_risk(sample: NetworkSample) -> tuple[str, str]:
    """Classify likely network pain source."""
    queue = network_queue_ms(sample)
    jitter = safe_float(sample.jitter_ms, 0.0, 0.0, 500.0)
    loss = safe_float(sample.packet_loss_pct, 0.0, 0.0, 100.0)

    if loss >= 2:
        return "Packet loss", "high"
    if queue >= 60:
        return "Router queueing / bufferbloat", "high"
    if jitter >= 15:
        return "Jitter", "medium"
    if queue >= 30:
        return "Router queueing / bufferbloat", "medium"
    if loss > 0:
        return "Light packet loss", "medium"
    return "Stable network", "low"


def profile_from_mapping(name: str, values: Mapping[str, Any]) -> SettingsProfile:
    """Build a SettingsProfile from untrusted UI/session values."""
    return SettingsProfile(
        name=name,
        fps_target=safe_float(values.get("fps_target", values.get("fpsTarget", 180)), 180, 30, 500),
        refresh_hz=safe_float(values.get("refresh_hz", values.get("refreshHz", 240)), 240, 60, 500),
        gpu_load_pct=safe_float(values.get("gpu_load_pct", 85), 85, 0, 100),
        cpu_load_pct=safe_float(values.get("cpu_load_pct", 45), 45, 0, 100),
        reflex_on=bool(values.get("reflex_on", values.get("reflexBoostOn", True))),
        vsync_on=bool(values.get("vsync_on", False)),
        gsync_on=bool(values.get("gsync_on", values.get("gsyncOn", False))),
        shadows_low=bool(values.get("shadows_low", True)),
        effects_low=bool(values.get("effects_low", True)),
        texture_budget=str(values.get("texture_budget", "medium")),
        audio_clarity_profile=bool(values.get("audio_clarity_profile", True)),
    )


def network_from_mapping(values: Mapping[str, Any]) -> NetworkSample:
    """Build a NetworkSample from untrusted UI/session values."""
    return NetworkSample(
        idle_ping_ms=safe_float(values.get("idle_ping_ms", values.get("speedtest_ping_ms", 35)), 35, 0, 1000),
        loaded_ping_ms=safe_float(values.get("loaded_ping_ms", values.get("loaded_ping", 45)), 45, 0, 1500),
        jitter_ms=safe_float(values.get("jitter_ms", 3), 3, 0, 500),
        packet_loss_pct=safe_float(values.get("packet_loss_pct", 0), 0, 0, 100),
        qos_enabled=bool(values.get("qos_enabled", False)),
        connection_type=str(values.get("connection_type", values.get("connection", "Ethernet"))),
    )


def build_recommendations(current: SettingsProfile, simulated: SettingsProfile, network: NetworkSample) -> List[str]:
    """Return practical recommendations without changing system/game state."""
    recommendations: List[str] = []
    current_render = estimate_render_latency_ms(current)
    simulated_render = estimate_render_latency_ms(simulated)
    queue = network_queue_ms(network)
    net_source, net_level = network_risk(network)

    if simulated_render + 0.5 < current_render:
        recommendations.append("Simulated profile likely improves local render/input delay. Test it for one session and log feel + 1% lows.")
    elif simulated_render > current_render + 0.5:
        recommendations.append("Simulated profile may feel slower. Keep current profile unless visibility gain is worth the delay.")
    else:
        recommendations.append("Latency difference is small. Decide based on stability, visibility, and comfort.")

    if current.gpu_load_pct >= 92:
        recommendations.append("GPU is near saturation. Lower GPU-heavy settings or cap FPS slightly lower to reduce render queue risk.")
    if current.cpu_load_pct >= 85:
        recommendations.append("CPU load is high. Close heavy background apps before ranked sessions.")
    if current.vsync_on:
        recommendations.append("V-Sync is on. For competitive testing, compare against V-Sync off with a stable FPS cap.")
    if queue >= 30 and not network.qos_enabled:
        recommendations.append("Loaded ping is much higher than idle ping. Enable router QoS/SQM if supported or pause uploads/downloads.")
    if net_level == "high":
        recommendations.append(f"Network risk is high: {net_source}. Treat this as a connection/router issue before tuning graphics.")
    if network.connection_type.lower() != "ethernet":
        recommendations.append("Use Ethernet for ranked testing when possible; Wi-Fi can add jitter even when average ping looks fine.")

    return recommendations


def build_coaching_prompts(report_hint: str, current: SettingsProfile, network: NetworkSample) -> List[str]:
    """Return non-invasive live coaching prompts for overlay/second monitor use."""
    prompts = [
        "Stay grouped; do not turn a settings test into solo-chasing.",
        "Play cover before damage. Log if fights feel delayed or smoother.",
    ]
    if current.gpu_load_pct >= 92:
        prompts.append("GPU pressure high: avoid changing aim settings mid-match; finish the test and review.")
    if network_queue_ms(network) >= 30:
        prompts.append("Network queueing risk: avoid ego-challenges when hit-reg or peeks feel delayed.")
    if "Packet" in report_hint:
        prompts.append("Packet loss risk: play safer angles and confirm connection after match.")
    return prompts[:5]


def analyze_latency(current: SettingsProfile, simulated: SettingsProfile, network: NetworkSample) -> LatencyReport:
    """Build a complete latency source report."""
    current_render = estimate_render_latency_ms(current)
    simulated_render = estimate_render_latency_ms(simulated)
    idle_ping = safe_float(network.idle_ping_ms, 35, 0, 1000)
    queue = network_queue_ms(network)
    jitter = safe_float(network.jitter_ms, 3, 0, 500)
    loss = safe_float(network.packet_loss_pct, 0, 0, 100)
    current_total = round(current_render + idle_ping + jitter + queue + (loss * 3.0), 2)
    simulated_total = round(simulated_render + idle_ping + jitter + queue + (loss * 3.0), 2)
    delta = round(simulated_total - current_total, 2)

    network_source, risk = network_risk(network)
    local_delta = simulated_render - current_render
    if risk in {"medium", "high"}:
        primary = network_source
    elif current.gpu_load_pct >= 92 or current.cpu_load_pct >= 85 or current.vsync_on:
        primary = "Local PC render/input pipeline"
    elif abs(local_delta) >= 1.0:
        primary = "Settings profile difference"
    else:
        primary = "No major latency source detected"

    rows = [
        {"Component": "Current render/input estimate", "ms": current_render, "Source": "machine"},
        {"Component": "Simulated render/input estimate", "ms": simulated_render, "Source": "machine"},
        {"Component": "Idle ping", "ms": idle_ping, "Source": "network"},
        {"Component": "Loaded ping queue", "ms": queue, "Source": "router/network"},
        {"Component": "Jitter", "ms": jitter, "Source": "network"},
        {"Component": "Packet loss penalty", "ms": round(loss * 3.0, 2), "Source": "network"},
        {"Component": "Current visibility score", "ms": visibility_score(current), "Source": "score"},
        {"Component": "Simulated visibility score", "ms": visibility_score(simulated), "Source": "score"},
    ]

    safety_notes = [
        "Prediction only: this does not modify Apex, read game memory, automate input, or interact with anti-cheat.",
        "Router priority requires router support and explicit user/admin configuration.",
        "Use second-monitor/browser overlay mode for safest live display behavior.",
    ]

    return LatencyReport(
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        current_total_ms=current_total,
        simulated_total_ms=simulated_total,
        delta_ms=delta,
        primary_source=primary,
        risk_level=risk,
        recommendations=build_recommendations(current, simulated, network),
        coaching_prompts=build_coaching_prompts(network_source, current, network),
        component_rows=rows,
        safety_notes=safety_notes,
    )


def build_overlay_payload(report: LatencyReport, current: SettingsProfile, simulated: SettingsProfile, network: NetworkSample) -> Dict[str, Any]:
    """Build compact data for a safe browser/second-monitor overlay."""
    return {
        "type": "safe-live-settings-impact-overlay",
        "created_utc": report.created_utc,
        "mode": "display-only",
        "current_profile": asdict(current),
        "simulated_profile": asdict(simulated),
        "network_sample": asdict(network),
        "summary": {
            "primary_source": report.primary_source,
            "risk_level": report.risk_level,
            "delta_ms": report.delta_ms,
            "current_total_ms": report.current_total_ms,
            "simulated_total_ms": report.simulated_total_ms,
        },
        "coaching_prompts": report.coaching_prompts,
        "safety": report.safety_notes,
    }


def overlay_payload_json(report: LatencyReport, current: SettingsProfile, simulated: SettingsProfile, network: NetworkSample) -> str:
    """Return pretty JSON for download/export."""
    return json.dumps(build_overlay_payload(report, current, simulated, network), indent=2, sort_keys=True)
