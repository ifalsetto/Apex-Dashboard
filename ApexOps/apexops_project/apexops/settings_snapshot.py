from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .utils import now_iso, try_get_gpu_driver_info, try_get_primary_display_mode


KV_RE = re.compile(r'^\s*"?([^"\s]+)"?\s+"?([^"\n\r]+)"?\s*$')


def parse_source_kv_file(path: Path) -> Dict[str, str]:
    """Parses Source-style cfg: key "value" or "key" "value"."""
    out: Dict[str, str] = {}
    if not path.exists():
        return out

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        m = KV_RE.match(line)
        if not m:
            continue
        k = m.group(1).strip()
        v = m.group(2).strip()
        out[k] = v

    return out


def snapshot_apex_configs(apex_local_dir: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Returns (videoconfig, settings_cfg) dicts."""
    videoconfig = parse_source_kv_file(apex_local_dir / "videoconfig.txt")
    settings_cfg = parse_source_kv_file(apex_local_dir / "settings.cfg")
    return videoconfig, settings_cfg


def snapshot_system(profile: Dict[str, Any]) -> Dict[str, Any]:
    """All best-effort; safe to store as JSON."""
    disp = try_get_primary_display_mode()
    gpu = try_get_gpu_driver_info()

    return {
        "captured_at": now_iso(),
        "profile": profile,
        "display": disp,
        "gpu": gpu,
    }
