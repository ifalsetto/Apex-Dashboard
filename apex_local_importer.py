
# One-click local Windows import helpers for Apex Dashboard.
# Local-first only:
# - Works when Streamlit runs on the user's Windows PC.
# - Does not collect the user's PC info from Streamlit Cloud.
# - Uses read-only Windows commands.

from __future__ import annotations

import json
import platform
import re
import subprocess
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict


def is_windows_local() -> bool:
    return platform.system().lower() == "windows"


def _run_powershell_json(script: str, timeout: int = 20) -> Dict[str, Any]:
    if not is_windows_local():
        return {
            "ok": False,
            "error": "One-click local import only works when the dashboard is running locally on Windows.",
            "data": {},
        }

    shells = ["powershell", "pwsh"]
    last_error = ""

    for shell in shells:
        try:
            completed = subprocess.run(
                [
                    shell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if completed.returncode != 0:
                last_error = completed.stderr.strip() or completed.stdout.strip()
                continue

            output = completed.stdout.strip()
            if not output:
                last_error = "PowerShell returned no output."
                continue

            return {
                "ok": True,
                "error": "",
                "data": json.loads(output),
            }

        except Exception as exc:
            last_error = str(exc)

    return {
        "ok": False,
        "error": last_error or "PowerShell could not run.",
        "data": {},
    }


def _redact_mac(value: str) -> str:
    if not value:
        return value
    return "<redacted-mac>"


def _redact_ipv4(value: str) -> str:
    if not value:
        return value

    value = str(value)
    value = re.sub(r"\b10\.\d+\.\d+\.\d+\b", "10.x.x.x", value)
    value = re.sub(r"\b192\.168\.\d+\.\d+\b", "192.168.x.x", value)
    value = re.sub(r"\b172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+\b", "172.x.x.x", value)
    return value


def collect_local_setup_settings() -> Dict[str, Any]:
    script = r'''
$ErrorActionPreference = "SilentlyContinue"

$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs = Get-CimInstance Win32_ComputerSystem
$gpu = Get-CimInstance Win32_VideoController |
    Sort-Object AdapterRAM -Descending |
    Select-Object -First 1

$ramGb = $null
if ($cs.TotalPhysicalMemory) {
    $ramGb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
}

$resolution = ""
if ($gpu.CurrentHorizontalResolution -and $gpu.CurrentVerticalResolution) {
    $resolution = "$($gpu.CurrentHorizontalResolution)x$($gpu.CurrentVerticalResolution)"
}

[PSCustomObject]@{
    OperatingSystem = $os.Caption
    OSVersion = $os.Version
    CPU = $cpu.Name
    RAMGB = $ramGb
    GPU = $gpu.Name
    VideoMode = $gpu.VideoModeDescription
    Resolution = $resolution
    RefreshHz = $gpu.CurrentRefreshRate
    GPUDriverVersion = $gpu.DriverVersion
    GPUDriverDate = $gpu.DriverDate
    ImportedAt = (Get-Date).ToString("s")
} | ConvertTo-Json -Compress -Depth 4
'''

    result = _run_powershell_json(script)
    if not result["ok"]:
        return result

    return {
        "ok": True,
        "error": "",
        "data": result.get("data", {}) or {},
    }


def collect_local_network_settings(redact_local_ids: bool = True) -> Dict[str, Any]:
    script = r'''
$ErrorActionPreference = "SilentlyContinue"

$cfg = Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -ne $null } |
    Select-Object -First 1

if ($null -eq $cfg) {
    $cfg = Get-NetIPConfiguration | Select-Object -First 1
}

$adapter = $null
$dns = $null
$gateway = ""

if ($cfg) {
    $adapter = Get-NetAdapter -InterfaceIndex $cfg.InterfaceIndex
    $dns = Get-DnsClientServerAddress -InterfaceIndex $cfg.InterfaceIndex -AddressFamily IPv4

    if ($cfg.IPv4DefaultGateway) {
        $gateway = ($cfg.IPv4DefaultGateway | Select-Object -First 1).NextHop
    }
}

$pingAvg = $null
if ($gateway) {
    $ping = Test-Connection -ComputerName $gateway -Count 2 -ErrorAction SilentlyContinue
    if ($ping) {
        $pingAvg = [math]::Round(($ping | Measure-Object ResponseTime -Average).Average, 1)
    }
}

$ipv4 = ""
if ($cfg.IPv4Address) {
    $ipv4 = ($cfg.IPv4Address.IPAddress -join ", ")
}

$dnsServers = ""
if ($dns.ServerAddresses) {
    $dnsServers = ($dns.ServerAddresses -join ", ")
}

[PSCustomObject]@{
    InterfaceAlias = $cfg.InterfaceAlias
    InterfaceDescription = $adapter.InterfaceDescription
    Status = $adapter.Status
    LinkSpeed = $adapter.LinkSpeed
    MacAddress = $adapter.MacAddress
    IPv4Address = $ipv4
    DefaultGateway = $gateway
    DnsServers = $dnsServers
    GatewayPingMs = $pingAvg
    ImportedAt = (Get-Date).ToString("s")
} | ConvertTo-Json -Compress -Depth 4
'''

    result = _run_powershell_json(script)
    if not result["ok"]:
        return result

    data = result.get("data", {}) or {}

    if redact_local_ids:
        data["MacAddress"] = _redact_mac(str(data.get("MacAddress", "")))
        data["IPv4Address"] = _redact_ipv4(str(data.get("IPv4Address", "")))

    return {
        "ok": True,
        "error": "",
        "data": data,
    }


def _infer_connection_type(data: Dict[str, Any]) -> str:
    label = f'{data.get("InterfaceAlias", "")} {data.get("InterfaceDescription", "")}'.lower()

    if any(token in label for token in ["wi-fi", "wifi", "wireless", "wlan"]):
        return "Wi-Fi"

    if any(token in label for token in ["ethernet", "realtek", "intel", "gbe", "lan"]):
        return "Ethernet"

    return "Unknown"


def apply_setup_settings_to_profile(profile: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(profile)

    meta = updated.setdefault("meta", {})
    targets = updated.setdefault("targets", {})
    report = updated.setdefault("systemReport", {})

    if data.get("OperatingSystem"):
        meta["os"] = data["OperatingSystem"]

    if data.get("GPU"):
        meta["gpu"] = data["GPU"]

    if data.get("VideoMode"):
        meta["monitor"] = data["VideoMode"]

    if data.get("RefreshHz"):
        try:
            targets["refreshHz"] = int(data["RefreshHz"])
        except Exception:
            report["refreshHz"] = data["RefreshHz"]

    report["operatingSystem"] = data.get("OperatingSystem", "")
    report["osVersion"] = data.get("OSVersion", "")
    report["cpu"] = data.get("CPU", "")
    report["ramGB"] = data.get("RAMGB", "")
    report["gpu"] = data.get("GPU", "")
    report["videoMode"] = data.get("VideoMode", "")
    report["resolution"] = data.get("Resolution", "")
    report["refreshHz"] = data.get("RefreshHz", "")
    report["gpuDriverVersion"] = data.get("GPUDriverVersion", "")
    report["gpuDriverDate"] = data.get("GPUDriverDate", "")
    report["setupImportedAt"] = data.get("ImportedAt", datetime.now().isoformat(timespec="seconds"))

    return updated


def apply_network_settings_to_profile(profile: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(profile)

    network = updated.setdefault("network", {})
    tests = network.setdefault("tests", {})

    network["connection"] = _infer_connection_type(data)
    network["adapter_name"] = data.get("InterfaceAlias", "")
    network["adapter_description"] = data.get("InterfaceDescription", "")
    network["adapter_status"] = data.get("Status", "")
    network["link_speed"] = data.get("LinkSpeed", "")
    network["mac_address"] = data.get("MacAddress", "")
    network["ipv4_address"] = data.get("IPv4Address", "")
    network["default_gateway"] = data.get("DefaultGateway", "")
    network["dns"] = data.get("DnsServers", "")
    network["importedSettings"] = data
    network["networkImportedAt"] = data.get("ImportedAt", datetime.now().isoformat(timespec="seconds"))

    if data.get("GatewayPingMs") is not None:
        tests["gateway_ping_ms"] = data.get("GatewayPingMs")

    existing_notes = str(network.get("notes", "")).strip()
    import_note = f'Imported local network settings at {network["networkImportedAt"]}.'

    if import_note not in existing_notes:
        network["notes"] = f"{existing_notes}\n{import_note}".strip()

    return updated
