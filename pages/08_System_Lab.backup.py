"""System Lab page for FalseTech Apex Dashboard.

The System Lab aggregates a set of local‑first collection tools that help a
player import hardware specifications, monitor details, network settings, and
classify running Windows services.  It uses read‑only PowerShell commands
when running on a Windows machine.  Nothing on this page modifies the
system—imports merely update the Streamlit profile JSON on disk so other
parts of the dashboard can read the data.  Services are never disabled
automatically; they are categorized to highlight potential impact on gaming
performance.
"""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import streamlit as st

from apex_config import config
from apex_utils import safe_load_json, safe_save_json
from apex_local_importer import (
    collect_local_setup_settings,
    collect_local_network_settings,
    apply_setup_settings_to_profile,
    apply_network_settings_to_profile,
)
from apex_system_importer import (
    parse_dxdiag_text,
    build_import_rows,
    apply_system_report_to_profile,
)


def classify_service(name: str) -> str:
    """Classify a Windows service name into a category for review.

    The classification logic is intentionally simple: it searches for keywords
    within the service name.  Critical services are required for the OS or
    security, gaming‑related services may impact performance or are part of
    game platforms, and safe‑to‑review services are those that often aren't
    needed during gameplay.  Any service that doesn't match a keyword falls
    into the leave‑alone bucket.
    """
    lower = (name or "").lower()
    critical_keywords = [
        "windows", "microsoft", "defender", "security", "update", "system", "rpc", "event",
        "network", "plugplay", "spooler", "dns", "dhcp",
    ]
    gaming_keywords = [
        "steam", "origin", "ea", "easervice", "eabackground", "epic", "rgb", "nvidia", "amd",
        "asus", "corsair", "razer", "logitech", "msi", "asus", "precision", "gaming", "xbox",
    ]
    review_keywords = [
        "assistant", "support", "telemetry", "help", "update", "assistant", "servicehub",
        "sync", "backup", "browser", "autoupdate", "webhelper", "customer",
    ]
    if any(k in lower for k in critical_keywords):
        return "Critical"
    if any(k in lower for k in gaming_keywords):
        return "Gaming‑related"
    if any(k in lower for k in review_keywords):
        return "Safe‑to‑review"
    return "Leave‑alone"


def collect_windows_services() -> Tuple[str, List[Dict[str, Any]]]:
    """Collect Windows service metadata and classify each entry.

    Returns a tuple of (error message, services list).  The error message is
    empty when services were collected successfully.  On non‑Windows
    platforms the function reports that the collection is unavailable.
    """
    if platform.system().lower() != "windows":
        return (
            "One‑click service analysis only works when running locally on Windows.",
            [],
        )
    # PowerShell script to list services as JSON objects.
    script = (
        "Get-Service | Select-Object Name, Status, DisplayName | ConvertTo-Json -Compress"
    )
    shells = ["powershell", "pwsh"]
    last_error: str = ""
    for shell in shells:
        try:
            completed = subprocess.run(
                [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if completed.returncode != 0 or not completed.stdout.strip():
                last_error = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
                continue
            data = json.loads(completed.stdout.strip())
            services: List[Dict[str, Any]] = []
            # When there is only one service the result is a dict; normalise to list
            if isinstance(data, dict):
                data = [data]
            for item in data:
                name = item.get("Name") or item.get("name") or ""
                display = item.get("DisplayName") or item.get("displayName") or name
                status = item.get("Status") or item.get("status") or ""
                category = classify_service(str(name))
                services.append(
                    {
                        "Service": display,
                        "Name": name,
                        "Status": status,
                        "Category": category,
                    }
                )
            return "", services
        except Exception as exc:
            last_error = str(exc)
    return (last_error or "Failed to collect services via PowerShell.", [])


def save_profile(updated: Dict[str, Any]) -> None:
    """Persist the updated profile to the autosave path safely."""
    safe_save_json(config.AUTOSAVE_PATH, updated)


def main() -> None:
    """Render the System Lab page."""
    st.set_page_config(page_title="System Lab", layout="wide")
    st.title("System Lab")
    st.caption(
        "Import PC specs, display and network info, and analyze Windows services without touching your files."
    )
    # Load current profile from disk
    profile: Dict[str, Any] = safe_load_json(config.AUTOSAVE_PATH) or {}
    # PC specs import
    st.subheader("PC Specs Import")
    st.write(
        "Collects your operating system, CPU, RAM, GPU, video mode, resolution, refresh rate, driver version, and driver date from the local machine."
    )
    if st.button("Import PC specs", key="import_pc", type="primary", help="Runs locally on Windows and saves into your profile"):
        result = collect_local_setup_settings()
        if not result.get("ok"):
            st.error(result.get("error") or "Failed to collect PC settings.")
        else:
            updated = apply_setup_settings_to_profile(profile, result.get("data", {}))
            save_profile(updated)
            st.success("PC specs imported into your dashboard profile.")
            profile = updated  # update local copy so subsequent sections see changes
    # Network import
    st.subheader("Network Import")
    st.write(
        "Collects your active network adapter, IP address (redacted), default gateway, DNS servers and link speed from the local machine."
    )
    if st.button("Import network info", key="import_net", type="primary", help="Runs locally on Windows and saves into your profile"):
        result = collect_local_network_settings(redact_local_ids=True)
        if not result.get("ok"):
            st.error(result.get("error") or "Failed to collect network settings.")
        else:
            updated = apply_network_settings_to_profile(profile, result.get("data", {}))
            save_profile(updated)
            st.success("Network settings imported into your dashboard profile.")
            profile = updated  # update local copy
    # DxDiag / System report import for display and extended system info
    st.subheader("DxDiag / System Report Import")
    st.write(
        "Upload a Windows DxDiag text report to selectively import monitor and extended system details."
    )
    uploaded = st.file_uploader("Upload dxdiag report (.txt)", type=["txt"])
    if uploaded is not None:
        try:
            text = uploaded.read().decode("utf-8", errors="ignore")
        except Exception:
            text = ""
        parsed = parse_dxdiag_text(text)
        rows = build_import_rows(parsed)
        if rows:
            st.dataframe(rows, hide_index=True, width="stretch")
            keys = [row["key"] for row in rows]
            recommended = [row["key"] for row in rows if row.get("Recommended")]
            selected = st.multiselect(
                "Select fields to import", options=keys, default=recommended, key="dxdiag_select"
            )
            if st.button("Apply selected DxDiag fields", key="apply_dxdiag", type="primary"):
                updated = apply_system_report_to_profile(profile, parsed, selected)
                save_profile(updated)
                st.success("Selected fields imported into your profile.")
                profile = updated
        else:
            st.info("No recognisable fields found in the uploaded report.")
    # Windows services analyzer
    st.subheader("Windows Services Analyzer")
    st.write(
        "Classifies running Windows services into categories.  Use this to decide what may be impacting gaming performance.  The dashboard never attempts to stop or modify services on your behalf."
    )
    error_msg, services = collect_windows_services()
    if error_msg:
        st.info(error_msg)
    else:
        st.dataframe(services, hide_index=True, width="stretch")
        st.caption(
            "Services are grouped into Critical, Gaming‑related, Safe‑to‑review, and Leave‑alone categories. Always research a service before disabling it."
        )


if __name__ == "__main__":
    main()
