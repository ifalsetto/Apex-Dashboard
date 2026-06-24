from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


CANDIDATE_KEYS = {
    "msbetweenpresents",
    "msbetweendisplaychange",
    "frametimes",
    "frame_times",
    "frametime",
}


@dataclass
class CaptureMetrics:
    captured_at: str
    test_name: str

    avg_fps: float
    fps_1_low: float
    fps_01_low: float

    avg_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float

    stutter8_pct: float
    stutter10_pct: float


def _find_key_recursively(obj: Any, key_pred) -> List[List[float]]:
    found: List[List[float]] = []

    def walk(x: Any):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(k, str) and key_pred(k):
                    if isinstance(v, list) and v and all(isinstance(n, (int, float)) for n in v):
                        found.append([float(n) for n in v])
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return found


def _find_plausible_numeric_arrays(obj: Any, min_len: int = 300) -> List[List[float]]:
    arrays: List[List[float]] = []

    def walk(x: Any):
        if isinstance(x, list):
            if len(x) >= min_len and all(isinstance(n, (int, float)) for n in x):
                arr = [float(n) for n in x]
                # plausibility: typical frame times are within (0, 200)
                med = float(np.median(arr))
                if 0.1 < med < 50.0:
                    arrays.append(arr)
            else:
                for v in x:
                    walk(v)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)

    walk(obj)
    return arrays


def _load_json(path: Path) -> Any:
    if path.suffix.lower() == ".gz" or path.name.lower().endswith(".json.gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            return json.load(f)
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return json.load(f)


def _extract_frametimes_from_csv(path: Path) -> Optional[np.ndarray]:
    df = pd.read_csv(path)
    # Common PresentMon/CapFrameX columns
    candidates = [
        "MsBetweenPresents",
        "msBetweenPresents",
        "MsBetweenDisplayChange",
        "MsBetweenPresentsAvg",
    ]
    for c in candidates:
        if c in df.columns:
            arr = df[c].to_numpy(dtype=float)
            return arr

    # Heuristic: any numeric column with plausible median
    for c in df.columns:
        try:
            arr = df[c].to_numpy(dtype=float)
        except Exception:
            continue
        if len(arr) < 300:
            continue
        med = float(np.nanmedian(arr))
        if 0.1 < med < 50.0:
            return arr

    return None


def _extract_frametimes_from_json(path: Path) -> Optional[np.ndarray]:
    obj = _load_json(path)

    # First: known keys
    def pred(k: str) -> bool:
        return k.lower() in CANDIDATE_KEYS

    candidates = _find_key_recursively(obj, pred)
    if candidates:
        best = max(candidates, key=len)
        return np.asarray(best, dtype=float)

    # Second: plausible arrays
    arrays = _find_plausible_numeric_arrays(obj, min_len=300)
    if arrays:
        best = max(arrays, key=len)
        return np.asarray(best, dtype=float)

    return None


def compute_metrics_from_frametimes(ft_ms: np.ndarray) -> Tuple[float, float, float, float, float, float, float, float, float]:
    # Clean
    ft = np.asarray(ft_ms, dtype=float)
    ft = ft[np.isfinite(ft)]
    ft = ft[(ft > 0.0) & (ft < 1000.0)]
    if ft.size < 300:
        raise ValueError(f"Not enough valid frame time samples: {ft.size}")

    avg_ms = float(np.mean(ft))
    avg_fps = float(1000.0 / avg_ms)

    sorted_ft = np.sort(ft)
    n = sorted_ft.size

    n1 = max(1, int(round(n * 0.01)))
    n01 = max(1, int(round(n * 0.001)))

    worst_1 = sorted_ft[-n1:]
    worst_01 = sorted_ft[-n01:]

    fps_1_low = float(1000.0 / float(np.mean(worst_1)))
    fps_01_low = float(1000.0 / float(np.mean(worst_01)))

    p95_ms = float(np.percentile(ft, 95))
    p99_ms = float(np.percentile(ft, 99))
    max_ms = float(np.max(ft))

    stutter8_pct = float(np.mean(ft > 8.0) * 100.0)
    stutter10_pct = float(np.mean(ft > 10.0) * 100.0)

    return (
        avg_fps,
        fps_1_low,
        fps_01_low,
        avg_ms,
        p95_ms,
        p99_ms,
        max_ms,
        stutter8_pct,
        stutter10_pct,
    )


def import_capture(path: Path) -> CaptureMetrics:
    test_name = path.stem
    if test_name.lower().endswith(".json"):
        test_name = Path(test_name).stem

    captured_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")

    ft: Optional[np.ndarray] = None
    lower = path.name.lower()
    if lower.endswith(".csv"):
        ft = _extract_frametimes_from_csv(path)
    elif lower.endswith(".json") or lower.endswith(".json.gz"):
        ft = _extract_frametimes_from_json(path)

    if ft is None:
        raise ValueError(f"Could not extract frame times from: {path.name}")

    (
        avg_fps,
        fps_1_low,
        fps_01_low,
        avg_ms,
        p95_ms,
        p99_ms,
        max_ms,
        stutter8_pct,
        stutter10_pct,
    ) = compute_metrics_from_frametimes(ft)

    return CaptureMetrics(
        captured_at=captured_at,
        test_name=test_name,
        avg_fps=avg_fps,
        fps_1_low=fps_1_low,
        fps_01_low=fps_01_low,
        avg_ms=avg_ms,
        p95_ms=p95_ms,
        p99_ms=p99_ms,
        max_ms=max_ms,
        stutter8_pct=stutter8_pct,
        stutter10_pct=stutter10_pct,
    )
