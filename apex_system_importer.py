"""Privacy-safe DxDiag/System Report importer for Apex Dashboard.

Cloud-safe design:
- User uploads a DxDiag .txt file.
- Parser extracts allowed fields only.
- Raw report is not saved by default.
- User previews and selects what to import.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Iterable


LOCAL_DXDIAG_HELPER_PS1 = r"""# FalseTech Apex Dashboard - DxDiag helper
# Creates a local DxDiag report on your Desktop.
# Review the file before uploading it to the dashboard.

$Output = Join-Path $env:USERPROFILE "Desktop\dxdiag_apex.txt"

Write-Host "Creating DxDiag report..."
dxdiag /t $Output

Write-Host ""
Write-Host "Done:"
Write-Host $Output
Write-Host ""
Write-Host "Upload dxdiag_apex.txt into the Apex Dashboard Import System Report panel."
"""


LABELS = {
    "operating_system": ["Operating System"],
    "system_manufacturer": ["System Manufacturer"],
    "system_model": ["System Model"],
    "bios": ["BIOS"],
    "processor": ["Processor"],
    "memory": ["Memory"],
    "directx_version": ["DirectX Version"],
    "gpu_name": ["Card name", "Card Name"],
    "gpu_manufacturer": ["Manufacturer"],
    "display_memory": ["Display Memory"],
    "dedicated_memory": ["Dedicated Memory"],
    "shared_memory": ["Shared Memory"],
    "current_mode": ["Current Mode"],
    "monitor_name": ["Monitor Name", "Monitor Model", "Monitor Id"],
    "driver_version": ["Driver Version"],
    "driver_date": ["Driver Date/Size"],
}


FIELD_LABELS = {
    "operating_system": "Operating System",
    "system_manufacturer": "System Manufacturer",
    "system_model": "System Model",
    "bios": "BIOS",
    "processor": "CPU",
    "memory": "RAM",
    "directx_version": "DirectX Version",
    "gpu_name": "GPU",
    "gpu_manufacturer": "GPU Manufacturer",
    "display_memory": "Display Memory",
    "dedicated_memory": "Dedicated GPU Memory",
    "shared_memory": "Shared GPU Memory",
    "current_mode": "Current Display Mode",
    "resolution": "Resolution",
    "refresh_hz": "Refresh Rate",
    "monitor_name": "Monitor",
    "driver_version": "GPU Driver Version",
    "driver_date": "GPU Driver Date",
}


DESTINATIONS = {
    "operating_system": "profile.meta.os",
    "gpu_name": "profile.meta.gpu",
    "monitor_name": "profile.meta.monitor",
    "refresh_hz": "profile.targets.refreshHz",
    "processor": "profile.systemReport.cpu",
    "memory": "profile.systemReport.memory",
    "directx_version": "profile.systemReport.directxVersion",
    "system_manufacturer": "profile.systemReport.systemManufacturer",
    "system_model": "profile.systemReport.systemModel",
    "bios": "profile.systemReport.bios",
    "gpu_manufacturer": "profile.systemReport.gpuManufacturer",
    "display_memory": "profile.systemReport.displayMemory",
    "dedicated_memory": "profile.systemReport.dedicatedMemory",
    "shared_memory": "profile.systemReport.sharedMemory",
    "current_mode": "profile.systemReport.displayMode",
    "resolution": "profile.systemReport.resolution",
    "driver_version": "profile.systemReport.gpuDriverVersion",
    "driver_date": "profile.systemReport.gpuDriverDate",
}


RECOMMENDED_IMPORTS = {
    "operating_system",
    "processor",
    "memory",
    "directx_version",
    "gpu_name",
    "monitor_name",
    "current_mode",
    "resolution",
    "refresh_hz",
    "driver_version",
    "driver_date",
}


ORDER = [
    "operating_system",
    "system_manufacturer",
    "system_model",
    "bios",
    "processor",
    "memory",
    "directx_version",
    "gpu_name",
    "gpu_manufacturer",
    "display_memory",
    "dedicated_memory",
    "shared_memory",
    "current_mode",
    "resolution",
    "refresh_hz",
    "monitor_name",
    "driver_version",
    "driver_date",
]


SENSITIVE_KEYWORDS = {
    "machine name",
    "machine",
    "computer name",
    "user name",
    "registered owner",
    "page file",
    "windows dir",
    "system directory",
}


def normalize_lines(text: str) -> List[str]:
    """Normalize DxDiag text into clean non-empty lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in text.split("\n") if line.strip()]


def redact_value(value: str) -> str:
    """Redact obvious local paths/account details from extracted values."""
    value = str(value).strip()

    # Redact Windows user paths.
    value = re.sub(
        r"C:\\Users\\[^\\/\s]+",
        r"C:\\Users\\<redacted>",
        value,
        flags=re.IGNORECASE,
    )

    # Redact UNC host/share prefix.
    value = re.sub(
        r"\\\\[^\\/\s]+\\",
        r"\\\\<redacted>\\",
        value,
    )

    return value.strip()


def is_sensitive_label(label: str) -> bool:
    lower = label.lower().strip()
    return any(keyword in lower for keyword in SENSITIVE_KEYWORDS)


def first_labeled_value(lines: Iterable[str], labels: Iterable[str]) -> str:
    """Return the first matching `Label: value` from DxDiag lines."""
    normalized_labels = [label.lower().strip() for label in labels]

    for line in lines:
        if ":" not in line:
            continue

        label, value = line.split(":", 1)
        label_clean = label.lower().strip()

        if is_sensitive_label(label_clean):
            continue

        if label_clean in normalized_labels:
            return redact_value(value)

    return ""


def extract_resolution(current_mode: str) -> str:
    """Extract resolution from a DxDiag Current Mode line."""
    match = re.search(r"(\d{3,5})\s*x\s*(\d{3,5})", current_mode, flags=re.IGNORECASE)
    if not match:
        return ""
    return f"{match.group(1)}x{match.group(2)}"


def extract_refresh_hz(current_mode: str) -> str:
    """Extract refresh rate from a DxDiag Current Mode line."""
    match = re.search(r"(\d{2,3})\s*Hz", current_mode, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1)


def parse_dxdiag_text(text: str) -> Dict[str, str]:
    """Parse allowed DxDiag fields from uploaded text."""
    if not text or not text.strip():
        return {}

    lines = normalize_lines(text)
    parsed: Dict[str, str] = {}

    for key, labels in LABELS.items():
        value = first_labeled_value(lines, labels)
        if value:
            parsed[key] = value

    current_mode = parsed.get("current_mode", "")
    resolution = extract_resolution(current_mode)
    refresh_hz = extract_refresh_hz(current_mode)

    if resolution:
        parsed["resolution"] = resolution
    if refresh_hz:
        parsed["refresh_hz"] = refresh_hz

    return parsed


def build_import_rows(parsed: Dict[str, str]) -> List[Dict[str, Any]]:
    """Build preview rows for Streamlit display."""
    rows: List[Dict[str, Any]] = []

    for key in ORDER:
        value = parsed.get(key, "")
        if not value:
            continue

        rows.append(
            {
                "key": key,
                "Field": FIELD_LABELS.get(key, key),
                "Value": value,
                "Destination": DESTINATIONS.get(key, "profile.systemReport"),
                "Recommended": key in RECOMMENDED_IMPORTS,
            }
        )

    return rows


def apply_system_report_to_profile(
    profile: Dict[str, Any],
    parsed: Dict[str, str],
    selected_keys: Iterable[str],
) -> Dict[str, Any]:
    """Apply selected parsed fields to the dashboard profile."""
    updated = deepcopy(profile)

    meta = updated.setdefault("meta", {})
    targets = updated.setdefault("targets", {})
    report = updated.setdefault("systemReport", {})

    selected = set(selected_keys)

    for key in selected:
        value = parsed.get(key)
        if not value:
            continue

        report[key] = value

        if key == "operating_system":
            meta["os"] = value
        elif key == "gpu_name":
            meta["gpu"] = value
        elif key == "monitor_name":
            meta["monitor"] = value
        elif key == "refresh_hz":
            try:
                targets["refreshHz"] = int(value)
            except ValueError:
                report[key] = value
        elif key == "processor":
            report["cpu"] = value
        elif key == "memory":
            report["memory"] = value
        elif key == "directx_version":
            report["directxVersion"] = value
        elif key == "current_mode":
            report["displayMode"] = value
        elif key == "resolution":
            report["resolution"] = value
        elif key == "driver_version":
            report["gpuDriverVersion"] = value
        elif key == "driver_date":
            report["gpuDriverDate"] = value
        elif key == "system_manufacturer":
            report["systemManufacturer"] = value
        elif key == "system_model":
            report["systemModel"] = value
        elif key == "gpu_manufacturer":
            report["gpuManufacturer"] = value
        elif key == "display_memory":
            report["displayMemory"] = value
        elif key == "dedicated_memory":
            report["dedicatedMemory"] = value
        elif key == "shared_memory":
            report["sharedMemory"] = value
        elif key == "bios":
            report["bios"] = value

    return updated
