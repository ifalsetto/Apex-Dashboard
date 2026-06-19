from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


GENERIC_DEFAULTS = {
    "source_machine": "Local PC",
    "connection": "",
    "isp": "",
    "router_model": "",
    "modem_fiber_box": "",
    "adapter_name": "",
    "adapter_description": "",
    "adapter_status": "",
    "link_speed": "",
    "default_gateway": "",
    "dns_servers": "",
    "ipv4_address": "",
    "mac_address": "",
    "gateway_ping_ms": "",
    "internet_ping_ms": "",
    "packet_loss_pct": "",
    "download_mbps": "",
    "upload_mbps": "",
}


def _read_toml_secret_path() -> Optional[str]:
    """
    Reads an optional local-only settings path from .streamlit/secrets.toml.
    This file should never be committed.
    """
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        return None

    try:
        import tomllib
        data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
        value = data.get("APEX_NETWORK_SETTINGS_PATH")
        return str(value) if value else None
    except Exception:
        return None


def _configured_settings_paths() -> list[str]:
    paths: list[str] = []

    env_path = os.environ.get("APEX_NETWORK_SETTINGS_PATH")
    if env_path:
        paths.append(env_path)

    secret_path = _read_toml_secret_path()
    if secret_path:
        paths.append(secret_path)

    paths.extend([
        "data/network/network_settings.json",
        "data/network/local_network_settings.json",
        "data/network/imported_network_settings.json",
    ])

    return paths


def _load_json(path: str | Path) -> Optional[Dict[str, Any]]:
    try:
        p = Path(path)
        if p.exists() and p.is_file():
            with p.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                data["_import_source"] = str(p)
                return data
    except Exception:
        return None
    return None


def _run_powershell_json(script: str) -> Optional[Dict[str, Any]]:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=12,
        )

        if completed.returncode != 0:
            return None

        raw = completed.stdout.strip()
        if not raw:
            return None

        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _collect_local_windows_adapter() -> Optional[Dict[str, Any]]:
    ps = r'''
$adapter = Get-NetAdapter |
Where-Object {
    $_.Status -eq "Up" -and
    $_.HardwareInterface -eq $true -and
    $_.InterfaceDescription -notmatch "Virtual|VPN|Loopback|Hyper-V|VMware|VirtualBox|Tailscale"
} |
Select-Object -First 1

if (-not $adapter) {
    throw "No active network adapter found."
}

$ip = Get-NetIPConfiguration -InterfaceAlias $adapter.Name
$dns = Get-DnsClientServerAddress -InterfaceAlias $adapter.Name -AddressFamily IPv4 -ErrorAction SilentlyContinue
$gateway = $ip.IPv4DefaultGateway.NextHop

$result = [ordered]@{
    source_machine = $env:COMPUTERNAME
    exported_at = (Get-Date).ToString("o")
    connection = $adapter.Name
    adapter_name = $adapter.Name
    adapter_description = $adapter.InterfaceDescription
    adapter_status = $adapter.Status
    link_speed = $adapter.LinkSpeed
    default_gateway = $gateway
    dns_servers = ($dns.ServerAddresses -join " / ")
    ipv4_address = $ip.IPv4Address.IPAddress
    mac_address = $adapter.MacAddress
    router_model = ""
    modem_fiber_box = ""
    isp = ""
    gateway_ping_ms = ""
    internet_ping_ms = ""
    packet_loss_pct = ""
    download_mbps = ""
    upload_mbps = ""
}

$result | ConvertTo-Json -Depth 5
'''
    return _run_powershell_json(ps)


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(GENERIC_DEFAULTS)
    merged.update({k: v for k, v in data.items() if v is not None})

    dns = merged.get("dns_servers")
    if isinstance(dns, list):
        merged["dns_servers"] = " / ".join(str(x) for x in dns)

    merged["sourceMachine"] = merged.get("source_machine", "")
    merged["routerModel"] = merged.get("router_model", "")
    merged["modemFiberBox"] = merged.get("modem_fiber_box", "")
    merged["adapterName"] = merged.get("adapter_name", "")
    merged["adapterDescription"] = merged.get("adapter_description", "")
    merged["adapterStatus"] = merged.get("adapter_status", "")
    merged["linkSpeed"] = merged.get("link_speed", "")
    merged["defaultGateway"] = merged.get("default_gateway", "")
    merged["dnsServers"] = merged.get("dns_servers", "")
    merged["ipv4Address"] = merged.get("ipv4_address", "")
    merged["macAddress"] = merged.get("mac_address", "")
    merged["gatewayPingMs"] = merged.get("gateway_ping_ms", "")
    merged["internetPingMs"] = merged.get("internet_ping_ms", "")
    merged["packetLossPct"] = merged.get("packet_loss_pct", "")
    merged["downloadMbps"] = merged.get("download_mbps", "")
    merged["uploadMbps"] = merged.get("upload_mbps", "")

    return merged


def _redact(data: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(data)
    for key in ("ipv4_address", "ipv4Address", "mac_address", "macAddress"):
        if key in redacted:
            redacted[key] = "Redacted"
    return redacted


def collect_local_network_settings(redact_local_ids: bool = True) -> Dict[str, Any]:
    searched = []

    for path in _configured_settings_paths():
        searched.append(path)
        data = _load_json(path)
        if data:
            normalized = _normalize(data)
            if redact_local_ids:
                normalized = _redact(normalized)
            return {
                "ok": True,
                "data": normalized,
                "source": path,
                "mode": "configured_json_import",
                "searched": searched,
            }

    local = _collect_local_windows_adapter()
    if local:
        normalized = _normalize(local)
        if redact_local_ids:
            normalized = _redact(normalized)
        return {
            "ok": True,
            "data": normalized,
            "source": "local_windows_adapter",
            "mode": "local_windows_adapter",
            "searched": searched,
        }

    fallback = _normalize({})
    if redact_local_ids:
        fallback = _redact(fallback)

    return {
        "ok": True,
        "data": fallback,
        "source": "generic_empty_fallback",
        "mode": "generic_empty_fallback",
        "warning": "No configured network settings file or local adapter data was available.",
        "searched": searched,
    }


def apply_network_settings_to_profile(profile: Dict[str, Any], imported_network: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(profile, dict):
        profile = {}

    imported = _normalize(imported_network)
    network = profile.setdefault("network", {})

    network["importedSettings"] = imported

    for key, value in imported.items():
        network[key] = value

    return profile
