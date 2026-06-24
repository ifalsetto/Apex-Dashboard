"""Process-only local Apex Legends monitor helpers.

This module is intentionally read-only and local-first.
It only checks the local process list for Apex Legends process names.

Safety boundaries:
- No memory reading.
- No input automation.
- No game-file modification.
- No anti-cheat interaction.
- No credential collection.
"""
from __future__ import annotations

import os
import platform
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, Optional

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - psutil may be absent in some environments
    psutil = None

try:
    from apex_config import config
except Exception:  # pragma: no cover
    config = None


DEFAULT_PROCESS_NAMES = {
    "r5apex",
    "r5apex.exe",
    "r5apex_dx12",
    "r5apex_dx12.exe",
}

DEFAULT_PROCESS_PREFIXES = ("r5apex",)


@dataclass
class ApexProcessStatus:
    """Normalized Apex process status returned to Streamlit UI."""

    running: bool
    process_name: str = ""
    pid: Optional[int] = None
    cpu_pct: float = 0.0
    detection_mode: str = "process-only"
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _configured_names() -> set[str]:
    names = set(DEFAULT_PROCESS_NAMES)
    if config is not None:
        for item in getattr(config, "APEX_PROCESS_NAMES", []) or []:
            names.add(str(item).lower())
    return names


def _configured_prefixes() -> tuple[str, ...]:
    prefixes = set(DEFAULT_PROCESS_PREFIXES)
    if config is not None:
        for item in getattr(config, "APEX_PROCESS_PREFIXES", []) or []:
            prefixes.add(str(item).lower().replace(".exe", ""))
    return tuple(sorted(prefixes))


def _normalize_process_name(name: str) -> str:
    return str(name or "").strip().lower()


def is_apex_process_name(name: str) -> bool:
    """Return True when a process name belongs to Apex Legends."""
    raw = _normalize_process_name(name)
    normalized = raw.replace(".exe", "")
    names = {_normalize_process_name(item) for item in _configured_names()}
    names_without_exe = {item.replace(".exe", "") for item in names}

    if raw in names or normalized in names_without_exe:
        return True

    return any(normalized.startswith(prefix) for prefix in _configured_prefixes())


def find_apex_process_psutil() -> ApexProcessStatus:
    """Find Apex using psutil when available."""
    if psutil is None:
        return ApexProcessStatus(running=False, error="psutil unavailable")

    try:
        for proc in psutil.process_iter(["pid", "name"]):
            name = proc.info.get("name") or ""
            if is_apex_process_name(name):
                cpu_pct = 0.0
                try:
                    proc.cpu_percent(interval=None)
                    time.sleep(0.15)
                    raw_cpu = float(proc.cpu_percent(interval=None))
                    cpu_pct = max(0.0, min(100.0, raw_cpu / max(1, os.cpu_count() or 1)))
                except Exception:
                    cpu_pct = 0.0

                return ApexProcessStatus(
                    running=True,
                    process_name=str(name),
                    pid=int(proc.info.get("pid") or 0),
                    cpu_pct=round(cpu_pct, 2),
                )
    except Exception as exc:
        return ApexProcessStatus(running=False, error=f"psutil failed: {exc}")

    return ApexProcessStatus(running=False)


def find_apex_process_powershell() -> ApexProcessStatus:
    """Find Apex using a read-only PowerShell fallback on Windows."""
    if platform.system().lower() != "windows":
        return ApexProcessStatus(running=False, error="PowerShell fallback is Windows-only")

    script = r"""
try {
    $p = Get-Process | Where-Object { $_.ProcessName -like 'r5apex*' } | Select-Object -First 1
    if ($p) {
        [PSCustomObject]@{
            Running = $true
            ProcessName = $p.ProcessName
            Pid = $p.Id
            Cpu = $p.CPU
        } | ConvertTo-Json -Compress
    } else {
        [PSCustomObject]@{
            Running = $false
            ProcessName = ''
            Pid = $null
            Cpu = 0
        } | ConvertTo-Json -Compress
    }
} catch {
    [PSCustomObject]@{
        Running = $false
        ProcessName = ''
        Pid = $null
        Cpu = 0
        Error = $_.Exception.Message
    } | ConvertTo-Json -Compress
}
"""

    try:
        import json

        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode != 0:
            return ApexProcessStatus(running=False, error=completed.stderr.strip())

        data = json.loads(completed.stdout.strip() or "{}")
        return ApexProcessStatus(
            running=bool(data.get("Running")),
            process_name=str(data.get("ProcessName") or ""),
            pid=data.get("Pid"),
            cpu_pct=0.0,
            error=str(data.get("Error") or ""),
        )
    except Exception as exc:
        return ApexProcessStatus(running=False, error=f"PowerShell fallback failed: {exc}")


def get_apex_process_status() -> ApexProcessStatus:
    """Return Apex process status using psutil first and PowerShell fallback second."""
    status = find_apex_process_psutil()
    if status.running:
        return status

    fallback = find_apex_process_powershell()
    if fallback.running:
        return fallback

    if status.error and not fallback.error:
        return status
    if fallback.error and not status.error:
        return fallback
    if status.error and fallback.error:
        return ApexProcessStatus(running=False, error=f"{status.error}; {fallback.error}")

    return ApexProcessStatus(running=False)


def verify_supported_process_names(names: Optional[Iterable[str]] = None) -> Dict[str, bool]:
    """Verify which known Apex process names match the detector."""
    test_names = list(names or ["r5apex", "r5apex.exe", "r5apex_dx12", "r5apex_dx12.exe"])
    return {name: is_apex_process_name(name) for name in test_names}
