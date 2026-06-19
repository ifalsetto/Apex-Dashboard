from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  start_at TEXT NOT NULL,
  end_at TEXT,
  profile_name TEXT,
  display_mode TEXT,
  win_width INTEGER,
  win_height INTEGER,
  win_hz INTEGER,
  gpu_name TEXT,
  gpu_driver TEXT,
  settings_json TEXT
);

CREATE TABLE IF NOT EXISTS captures (
  id TEXT PRIMARY KEY,
  captured_at TEXT,
  imported_at TEXT NOT NULL,
  test_name TEXT,
  capture_path TEXT NOT NULL UNIQUE,
  run_id TEXT,

  profile_name TEXT,
  display_mode TEXT,
  monitor_target_hz INTEGER,

  win_width INTEGER,
  win_height INTEGER,
  win_hz INTEGER,

  gpu_name TEXT,
  gpu_driver TEXT,

  avg_fps REAL,
  fps_1_low REAL,
  fps_01_low REAL,

  avg_ms REAL,
  p95_ms REAL,
  p99_ms REAL,
  max_ms REAL,

  stutter8_pct REAL,
  stutter10_pct REAL,

  settings_json TEXT,
  apex_video_json TEXT,
  apex_cfg_json TEXT,

  notes TEXT,

  FOREIGN KEY(run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS match_logs (
  id TEXT PRIMARY KEY,
  played_at TEXT NOT NULL,
  mode TEXT,
  map TEXT,
  ping_ms INTEGER,
  kills INTEGER,
  assists INTEGER,
  damage INTEGER,
  placement INTEGER,
  notes TEXT,
  run_id TEXT,
  capture_id TEXT,
  settings_json TEXT,

  FOREIGN KEY(run_id) REFERENCES runs(id),
  FOREIGN KEY(capture_id) REFERENCES captures(id)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def capture_exists(con: sqlite3.Connection, capture_path: str) -> bool:
    cur = con.execute("SELECT 1 FROM captures WHERE capture_path = ? LIMIT 1", (capture_path,))
    return cur.fetchone() is not None


def insert_run(con: sqlite3.Connection, row: Dict[str, Any]) -> None:
    cols = ",".join(row.keys())
    qs = ",".join(["?"] * len(row))
    con.execute(f"INSERT INTO runs ({cols}) VALUES ({qs})", tuple(row.values()))
    con.commit()


def end_run(con: sqlite3.Connection, run_id: str, end_at: str) -> None:
    con.execute("UPDATE runs SET end_at=? WHERE id=?", (end_at, run_id))
    con.commit()


def insert_capture(con: sqlite3.Connection, row: Dict[str, Any]) -> None:
    cols = ",".join(row.keys())
    qs = ",".join(["?"] * len(row))
    con.execute(f"INSERT INTO captures ({cols}) VALUES ({qs})", tuple(row.values()))
    con.commit()


def update_capture_notes(con: sqlite3.Connection, capture_id: str, notes: str) -> None:
    con.execute("UPDATE captures SET notes=? WHERE id=?", (notes, capture_id))
    con.commit()


def insert_match(con: sqlite3.Connection, row: Dict[str, Any]) -> None:
    cols = ",".join(row.keys())
    qs = ",".join(["?"] * len(row))
    con.execute(f"INSERT INTO match_logs ({cols}) VALUES ({qs})", tuple(row.values()))
    con.commit()
