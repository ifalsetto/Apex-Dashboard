from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import psutil

from . import db
from .capframex_import import import_capture
from .settings_snapshot import snapshot_apex_configs, snapshot_system
from .utils import ResolvedConfig, json_dumps, load_config, now_iso, stable_file_ready


APEX_PROCESS_NAMES = {"r5apex.exe", "r5apex_dx12.exe"}


def is_apex_running() -> bool:
    for p in psutil.process_iter(attrs=["name"]):
        name = (p.info.get("name") or "").lower()
        if name in APEX_PROCESS_NAMES:
            return True
    return False


def iter_capture_files(cfg: ResolvedConfig):
    if not cfg.capframex_dir.exists():
        return []
    exts = cfg.capture_extensions
    files = []
    for p in cfg.capframex_dir.glob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if any(name.endswith(ext) for ext in exts):
            files.append(p)
    return sorted(files, key=lambda x: x.stat().st_mtime)


def start_run(con, cfg: ResolvedConfig) -> str:
    run_id = str(uuid.uuid4())
    snap = snapshot_system(cfg.profile)

    disp = snap.get("display", {})
    gpu = snap.get("gpu", {})

    row = {
        "id": run_id,
        "start_at": snap.get("captured_at") or now_iso(),
        "profile_name": cfg.profile.get("profile_name") or cfg.profile.get("profile_name"),
        "display_mode": cfg.profile.get("display_mode"),
        "win_width": disp.get("width"),
        "win_height": disp.get("height"),
        "win_hz": disp.get("hz"),
        "gpu_name": gpu.get("name"),
        "gpu_driver": gpu.get("driver_version"),
        "settings_json": json_dumps(snap),
    }
    db.insert_run(con, row)
    print(f"[ApexOps] Run started: {run_id} (hz={disp.get('hz')})")
    return run_id


def import_one_capture(con, cfg: ResolvedConfig, path: Path, run_id: Optional[str]) -> None:
    metrics = import_capture(path)
    snap = snapshot_system(cfg.profile)
    videoconfig, settings_cfg = snapshot_apex_configs(cfg.apex_local_dir)

    disp = snap.get("display", {})
    gpu = snap.get("gpu", {})

    capture_id = str(uuid.uuid4())

    row = {
        "id": capture_id,
        "captured_at": metrics.captured_at,
        "imported_at": now_iso(),
        "test_name": metrics.test_name,
        "capture_path": str(path),
        "run_id": run_id,

        "profile_name": cfg.profile.get("profile_name"),
        "display_mode": cfg.profile.get("display_mode"),
        "monitor_target_hz": cfg.profile.get("monitor_target_hz"),

        "win_width": disp.get("width"),
        "win_height": disp.get("height"),
        "win_hz": disp.get("hz"),

        "gpu_name": gpu.get("name"),
        "gpu_driver": gpu.get("driver_version"),

        "avg_fps": metrics.avg_fps,
        "fps_1_low": metrics.fps_1_low,
        "fps_01_low": metrics.fps_01_low,

        "avg_ms": metrics.avg_ms,
        "p95_ms": metrics.p95_ms,
        "p99_ms": metrics.p99_ms,
        "max_ms": metrics.max_ms,

        "stutter8_pct": metrics.stutter8_pct,
        "stutter10_pct": metrics.stutter10_pct,

        "settings_json": json_dumps(snap),
        "apex_video_json": json_dumps(videoconfig),
        "apex_cfg_json": json_dumps(settings_cfg),

        "notes": cfg.profile.get("notes_default", ""),
    }

    db.insert_capture(con, row)

    print(
        "[ApexOps] Imported capture:"
        f" {metrics.test_name} | avg_fps={metrics.avg_fps:.1f}"
        f" 1%={metrics.fps_1_low:.1f} 0.1%={metrics.fps_01_low:.1f}"
        f" | win_hz={disp.get('hz')} | file={path.name}"
    )


def main() -> int:
    project_dir = Path(__file__).resolve().parent.parent
    cfg_path = project_dir / "config.yaml"

    cfg = load_config(cfg_path)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)

    con = db.connect(cfg.db_path)
    db.init_db(con)

    print(f"[ApexOps] Collector running. Watching: {cfg.capframex_dir}")
    print(f"[ApexOps] DB: {cfg.db_path}")

    last_running = False
    current_run_id: Optional[str] = None

    while True:
        # Reload config live (so you can edit config.yaml without restarting)
        try:
            cfg = load_config(cfg_path)
        except Exception as e:
            print(f"[ApexOps] config.yaml error: {e}")

        # Ensure dirs
        cfg.data_dir.mkdir(parents=True, exist_ok=True)

        # Track Apex process
        if cfg.track_apex_process:
            running = is_apex_running()
            if running and not last_running:
                current_run_id = start_run(con, cfg)
            elif (not running) and last_running:
                if current_run_id:
                    db.end_run(con, current_run_id, now_iso())
                    print(f"[ApexOps] Run ended: {current_run_id}")
                current_run_id = None
            last_running = running

        # Import new capture files
        for p in iter_capture_files(cfg):
            if not stable_file_ready(p, min_age_sec=2.0):
                continue
            if db.capture_exists(con, str(p)):
                continue
            try:
                import_one_capture(con, cfg, p, current_run_id)
            except Exception as e:
                print(f"[ApexOps] Failed import {p.name}: {e}")

        time.sleep(max(1, int(cfg.scan_interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
