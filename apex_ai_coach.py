"""Local-first AI coach utilities for Apex Dashboard."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from openai import OpenAI

from apex_utils import now_iso, safe_save_json

logger = logging.getLogger("apex_dashboard")


def get_openai_api_key() -> Optional[str]:
    try:
        secret = st.secrets.get("OPENAI_API_KEY")
        if secret:
            return str(secret).strip()
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "").strip() or None


def build_local_fallback_report(profile: Dict[str, Any], tracker_profile: Optional[Dict[str, Any]], latest_match: Optional[Dict[str, Any]], performance_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    suggestions: List[str] = []
    targets = profile.get("targets", {})
    toggles = profile.get("toggles", {})
    refresh = targets.get("refreshHz", "—")
    fps_target = targets.get("fpsTarget", "—")

    if isinstance(refresh, int) and isinstance(fps_target, int) and refresh >= 120 and fps_target >= refresh:
        suggestions.append(f"Cap FPS slightly below refresh (for example {max(30, refresh - 3)} at {refresh}Hz) to improve frametime consistency.")
    if not toggles.get("vsyncInGameOff", True):
        suggestions.append("Turn in-game V-Sync off for competitive play to lower latency.")
    if not toggles.get("reflexBoostOn", True):
        suggestions.append("Enable NVIDIA Reflex + Boost if supported to help reduce latency spikes.")

    if latest_match:
        avg_fps = latest_match.get("avg_fps")
        low_1 = latest_match.get("one_percent_low")
        if avg_fps not in (None, "") and low_1 not in (None, ""):
            try:
                if float(low_1) < float(avg_fps) * 0.7:
                    suggestions.append("Your 1% low FPS is much lower than your average FPS. Focus on background task cleanup and stable graphics settings.")
            except Exception:
                pass
        ping = latest_match.get("ping_ms")
        if ping not in (None, ""):
            try:
                if float(ping) > 60:
                    suggestions.append("Ping is elevated. Test a wired connection, less congested times, or router QoS if available.")
            except Exception:
                pass

    if tracker_profile and tracker_profile.get("ok"):
        rank = tracker_profile.get("rank", "Unranked")
        suggestions.append(f"Tracker rank snapshot: {rank}. Use ranked sessions to compare changes consistently.")

    if performance_stats and performance_stats.get("apex_running"):
        suggestions.append("Apex is currently running. Capture a few more sessions before making major changes so recommendations stay evidence-based.")

    if not suggestions:
        suggestions.append("No urgent issues detected from the available data. Keep logging matches to improve future coaching recommendations.")

    return {
        "ok": True,
        "source": "local_fallback",
        "createdISO": now_iso(),
        "summary": "Local coaching report generated without OpenAI.",
        "suggestions": suggestions[:6],
    }


def generate_ai_coach_report(profile: Dict[str, Any], tracker_profile: Optional[Dict[str, Any]], latest_match: Optional[Dict[str, Any]], performance_stats: Optional[Dict[str, Any]] = None, export_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    api_key = get_openai_api_key()
    fallback = build_local_fallback_report(profile, tracker_profile, latest_match, performance_stats)
    report = fallback

    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            payload = {
                "profile": profile,
                "tracker_profile": tracker_profile if tracker_profile and tracker_profile.get("ok") else None,
                "latest_match": latest_match,
                "performance_stats": performance_stats,
            }
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": "You are an Apex Legends performance coach. Only use provided data. If data is missing, say so plainly. Give concise practical recommendations in bullets.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
            )
            text = getattr(response, "output_text", "").strip()
            if text:
                report = {
                    "ok": True,
                    "source": "openai",
                    "createdISO": now_iso(),
                    "summary": text,
                    "suggestions": [],
                }
        except Exception as exc:
            logger.warning("OpenAI coach unavailable, using fallback report: %s", exc)
            report = fallback

    if export_dir:
        try:
            export_path = Path(export_dir)
            export_path.mkdir(parents=True, exist_ok=True)
            filename = export_path / f"apex_ai_coach_{now_iso().replace(':', '-')}".replace('T', '_')
            safe_save_json(f"{filename}.json", report)
        except Exception as exc:
            logger.warning("Failed to save AI coach report: %s", exc)

    return report
