from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


DEFAULT_DESTINATION = Path("data/network/network_history.jsonl")

LOCAL_FALLBACK_SOURCES = [
    "data/network/import_network_history.jsonl",
    "data/network/imported_network_history.jsonl",
    "data/network/gamingdesktop_network_history.jsonl",
    "data/network/network_history.jsonl",
]


def _read_toml_history_path() -> Optional[str]:
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        return None

    try:
        import tomllib
        data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
        value = data.get("APEX_NETWORK_HISTORY_PATH")
        return str(value) if value else None
    except Exception:
        return None


def _configured_sources(source_path: str | Path | None = None) -> list[str | Path]:
    sources: list[str | Path] = []

    if source_path:
        sources.append(source_path)

    env_path = os.environ.get("APEX_NETWORK_HISTORY_PATH")
    if env_path:
        sources.append(env_path)

    secret_path = _read_toml_history_path()
    if secret_path:
        sources.append(secret_path)

    sources.extend(LOCAL_FALLBACK_SOURCES)
    return sources


def _safe_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(str(value))


def _first_existing(paths: Iterable[str | Path]) -> Optional[Path]:
    for raw in paths:
        path = _safe_path(raw)
        try:
            if path.exists() and path.is_file():
                return path
        except OSError:
            continue
    return None


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except Exception:
        return str(a).lower() == str(b).lower()


def _validate_jsonl(path: Path) -> tuple[int, int]:
    records = 0
    bad_lines = 0

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue

            try:
                json.loads(line)
                records += 1
            except json.JSONDecodeError:
                bad_lines += 1

    return records, bad_lines


def import_local_network_history(
    source_path: str | Path | None = None,
    destination_path: str | Path | None = None,
    copy_aliases: bool = True,
    *_args: Any,
    **_kwargs: Any,
) -> Dict[str, Any]:
    """
    Neutral JSONL network-history importer.

    Public app code does not contain user-specific hostnames, IPs, MACs,
    router models, or local paths. Users can provide their own source path via:
      - function source_path
      - APEX_NETWORK_HISTORY_PATH environment variable
      - .streamlit/secrets.toml key APEX_NETWORK_HISTORY_PATH
      - local data/network/*.jsonl fallback files
    """

    destination = _safe_path(destination_path or DEFAULT_DESTINATION)
    destination.parent.mkdir(parents=True, exist_ok=True)

    sources = _configured_sources(source_path)
    source = _first_existing(sources)

    if source is None:
        return {
            "ok": False,
            "success": False,
            "error": "No network history JSONL file found.",
            "searched": [str(p) for p in sources],
            "destination": str(destination),
        }

    try:
        records, bad_lines = _validate_jsonl(source)

        if records <= 0:
            return {
                "ok": False,
                "success": False,
                "error": f"Network history file has no valid JSONL records: {source}",
                "source": str(source),
                "destination": str(destination),
                "records": records,
                "bad_lines": bad_lines,
            }

        if not _same_file(source, destination):
            shutil.copy2(source, destination)

        aliases = []
        if copy_aliases:
            for alias_name in (
                "imported_network_history.jsonl",
                "latest_network_history.jsonl",
            ):
                alias = destination.parent / alias_name
                if not _same_file(destination, alias):
                    shutil.copy2(destination, alias)
                    aliases.append(str(alias))

        return {
            "ok": True,
            "success": True,
            "message": "Network history imported.",
            "source": str(source),
            "destination": str(destination),
            "aliases": aliases,
            "records": records,
            "bad_lines": bad_lines,
            "imported": records,
            "count": records,
        }

    except Exception as exc:
        return {
            "ok": False,
            "success": False,
            "error": f"Local network import failed: {exc}",
            "source": str(source),
            "destination": str(destination),
        }


def import_network_history(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return import_local_network_history(*args, **kwargs)


def run_local_network_import(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return import_local_network_history(*args, **kwargs)


def import_from_network_share(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return import_local_network_history(*args, **kwargs)
