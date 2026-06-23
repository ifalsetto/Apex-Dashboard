"""Safety rails, scope rules, heartbeats, and Cell/Brain/Agent helpers.

This module is intentionally local-first and read-only. It provides shared
operational language for the dashboard without adding any game interaction.
"""
from __future__ import annotations

import datetime as dt
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping


APP_SCOPE = {
    "mission": "Help players understand setup, latency sources, sessions, and improvement focus without unsafe game interaction.",
    "mode": "local-first, read-only, user-controlled",
    "data_boundary": "Windows/system metrics, user-entered settings, benchmark history, manual notes, exported reports.",
}

ALLOWED_CAPABILITIES = [
    "process-only Apex detection",
    "system metric display",
    "manual session logging",
    "settings impact simulation",
    "latency source analysis",
    "coaching reminders",
    "local export/import",
    "router QoS recommendation notes",
]

BLOCKED_CAPABILITIES = [
    "game memory reading",
    "anti-cheat interaction",
    "input automation",
    "aim/recoil assistance",
    "packet manipulation",
    "game-file modification",
    "credential collection",
    "hidden background control",
    "unapproved network control",
]

BRAIN_AGENTS = [
    {
        "name": "Scope Brain",
        "job": "Keeps the app inside local-first, read-only, player-improvement boundaries.",
        "status": "active",
    },
    {
        "name": "Latency Analyst",
        "job": "Separates machine delay, network delay, jitter, packet loss, and queueing risk.",
        "status": "active",
    },
    {
        "name": "Settings Simulator",
        "job": "Compares current settings against a simulated profile and predicts likely impact.",
        "status": "active",
    },
    {
        "name": "Live Coach",
        "job": "Shows non-invasive reminders based on user-selected state and training focus.",
        "status": "active",
    },
    {
        "name": "Safety Gate",
        "job": "Blocks unsafe capabilities and marks risky ideas before they become features.",
        "status": "active",
    },
]


@dataclass(frozen=True)
class GuardrailResult:
    """Result returned when a requested capability is checked."""

    capability: str
    allowed: bool
    risk_level: str
    reason: str
    replacement: str = ""


@dataclass(frozen=True)
class Heartbeat:
    """Lightweight runtime heartbeat for the command center."""

    timestamp_utc: str
    os: str
    python_version: str
    safe_mode: bool
    active_agents: int
    blocked_capabilities: int


@dataclass(frozen=True)
class CellSnapshot:
    """FalseTech Cell style self-check snapshot."""

    cell_name: str
    scope_ok: bool
    heartbeat_ok: bool
    safety_ok: bool
    context_ok: bool
    next_action: str


def normalize_text(value: Any) -> str:
    """Normalize user/system strings for capability checks."""
    return str(value or "").strip().lower()


def evaluate_capability_request(capability: str) -> GuardrailResult:
    """Allow safe dashboard work and block unsafe game/network interaction."""
    text = normalize_text(capability)

    for blocked in BLOCKED_CAPABILITIES:
        if normalize_text(blocked) in text:
            return GuardrailResult(
                capability=capability,
                allowed=False,
                risk_level="blocked",
                reason=f"Blocked because it matches unsafe capability: {blocked}.",
                replacement="Use local metrics, manual inputs, settings simulation, or router/admin-approved recommendations instead.",
            )

    risky_terms = ["overlay", "priority", "qos", "traffic", "latency", "coach", "settings"]
    if any(term in text for term in risky_terms):
        return GuardrailResult(
            capability=capability,
            allowed=True,
            risk_level="review",
            reason="Allowed only when external, visible, user-controlled, and non-invasive.",
            replacement="Keep the feature read-only unless the user explicitly configures router/system settings outside the game.",
        )

    return GuardrailResult(
        capability=capability,
        allowed=True,
        risk_level="low",
        reason="Safe dashboard capability.",
    )


def build_heartbeat() -> Dict[str, Any]:
    """Return a serializable dashboard heartbeat."""
    heartbeat = Heartbeat(
        timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        os=platform.system() or "Unknown",
        python_version=platform.python_version(),
        safe_mode=True,
        active_agents=len([agent for agent in BRAIN_AGENTS if agent.get("status") == "active"]),
        blocked_capabilities=len(BLOCKED_CAPABILITIES),
    )
    return asdict(heartbeat)


def build_cell_snapshot(context: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Return a compact self-check snapshot for the dashboard."""
    context = dict(context or {})
    missing = [key for key in ("profile", "process", "latency") if key not in context]
    snapshot = CellSnapshot(
        cell_name="Apex Command Cell",
        scope_ok=True,
        heartbeat_ok=True,
        safety_ok=True,
        context_ok=not bool(missing),
        next_action="Open Latency Source Analyzer" if missing else "Run session, compare settings, save notes",
    )
    return asdict(snapshot)


def guardrail_table() -> List[Dict[str, str]]:
    """Return rows suitable for Streamlit display."""
    rows: List[Dict[str, str]] = []
    for item in ALLOWED_CAPABILITIES:
        rows.append({"Capability": item, "Status": "Allowed", "Rule": "Read-only / user-controlled"})
    for item in BLOCKED_CAPABILITIES:
        rows.append({"Capability": item, "Status": "Blocked", "Rule": "Unsafe or unfair advantage risk"})
    return rows


def agent_table() -> List[Dict[str, str]]:
    """Return active agent rows for UI display."""
    return [dict(agent) for agent in BRAIN_AGENTS]


def safe_path_status(path: str | Path) -> Dict[str, Any]:
    """Check a path without creating, deleting, or modifying anything."""
    p = Path(path)
    try:
        exists = p.exists()
        return {
            "path": str(p),
            "exists": exists,
            "is_dir": p.is_dir() if exists else False,
            "is_file": p.is_file() if exists else False,
            "safe": True,
        }
    except Exception as exc:  # pragma: no cover - defensive UI helper
        return {"path": str(p), "exists": False, "is_dir": False, "is_file": False, "safe": False, "error": str(exc)}
