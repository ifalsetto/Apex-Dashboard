import copy
import re
import streamlit as st
import sys


def apply_patches(target_globals):
    """
    Apply performance patches to selected global functions from apex_dashboard.
    """
    original_deep_copy = target_globals.get("deep_copy")
    original_slug = target_globals.get("slug")
    original_logs_to_csv_bytes = target_globals.get("logs_to_csv_bytes")
    original_ping_sample = target_globals.get("ping_sample")

    def deep_copy_patch(x):
        try:
            return copy.deepcopy(x)
        except Exception:
            if original_deep_copy:
                return original_deep_copy(x)
            return x

    def slug_patch(s: str) -> str:
        s = (s or "").strip()
        out = []
        for ch in s:
            if ch.isalnum() or ch in ("-", "_"):
                out.append(ch)
            elif ch.isspace():
                out.append("_")
        name = "".join(out)
        name = re.sub(r"_+", "_", name)
        return (name[:60] if name else "profile")

    @st.cache_data(show_spinner=False)
    def logs_to_csv_bytes_patch(logs):
        if original_logs_to_csv_bytes:
            return original_logs_to_csv_bytes(logs)
        return b""

    def ping_sample_patch(host: str = "1.1.1.1", count: int = 10):
        if original_ping_sample:
            return original_ping_sample(host, min(count, 3))
        return None, None

    if original_deep_copy:
        target_globals["deep_copy"] = deep_copy_patch
    if original_slug:
        target_globals["slug"] = slug_patch
    if original_logs_to_csv_bytes:
        target_globals["logs_to_csv_bytes"] = logs_to_csv_bytes_patch
    if original_ping_sample:
        target_globals["ping_sample"] = ping_sample_patch


def _auto_patch():
    mod = sys.modules.get("apex_dashboard")
    if mod:
        apply_patches(mod.__dict__)


_auto_patch()
