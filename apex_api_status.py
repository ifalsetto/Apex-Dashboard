from __future__ import annotations

import os
from typing import Optional, Tuple

import requests
import streamlit as st


TRACKER_SEARCH_URL = "https://public-api.tracker.gg/v2/apex/standard/search"


def _safe_secret(name: str) -> Optional[str]:
    """Read a secret without displaying it. Streamlit secrets first, env fallback second."""
    value = None

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    if not value:
        value = os.getenv(name)

    if value is None:
        return None

    value = str(value).strip()
    return value or None


def _present_label(value: Optional[str]) -> str:
    return "Found" if value else "Missing"


def _test_tracker_auth(platform: str = "origin", query: str = "ifalsetto") -> Tuple[str, str]:
    api_key = _safe_secret("TRACKER_API_KEY")

    if not api_key:
        return "Missing", "TRACKER_API_KEY is not configured."

    try:
        response = requests.get(
            TRACKER_SEARCH_URL,
            headers={
                "TRN-Api-Key": api_key,
                "Accept": "application/json",
            },
            params={
                "platform": platform,
                "query": query,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        return "Network Error", f"{type(exc).__name__}: {exc}"

    body_preview = response.text[:300].replace("\n", " ").strip()

    if response.status_code == 200:
        return "Valid", "Tracker API accepted the key."

    if response.status_code == 401:
        return "Invalid", "Tracker rejected the key: 401 Invalid authentication credentials."

    if response.status_code == 403:
        return "Forbidden", "Tracker rejected access: 403. Key may need approval or permission."

    if response.status_code == 404:
        return "Accepted / Not Found", "Auth likely worked, but the player/platform was not found."

    if response.status_code == 429:
        return "Rate Limited", "Tracker returned 429. Wait and retry later."

    return f"HTTP {response.status_code}", body_preview or "No response body."


def render_api_status_panel() -> None:
    """Render a safe API status card. Never prints secret values."""
    openai_key = _safe_secret("OPENAI_API_KEY")
    tracker_key = _safe_secret("TRACKER_API_KEY")

    if "tracker_auth_status" not in st.session_state:
        st.session_state.tracker_auth_status = "Not tested"

    if "tracker_auth_detail" not in st.session_state:
        st.session_state.tracker_auth_detail = "Click the test button to verify Tracker auth."

    with st.expander("API Status / Safe Debug", expanded=False):
        st.caption("Checks whether API keys are configured without displaying secret values.")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("OpenAI Key", _present_label(openai_key))
        col2.metric("Tracker Key", _present_label(tracker_key))
        col3.metric("Tracker Auth", st.session_state.tracker_auth_status)
        col4.metric("Fallback Data", "Ready")

        st.divider()

        test_col, info_col = st.columns([1, 2])

        with test_col:
            test_clicked = st.button(
                "Test Tracker Auth",
                key="test_tracker_auth_button",
                help="Sends a safe Tracker search request without displaying your API key.",
            )

        with info_col:
            st.write(st.session_state.tracker_auth_detail)

        if test_clicked:
            with st.status("Testing Tracker auth...", expanded=True) as status_box:
                status, detail = _test_tracker_auth()
                st.session_state.tracker_auth_status = status
                st.session_state.tracker_auth_detail = detail

                if status == "Valid":
                    status_box.update(label="Tracker auth valid", state="complete")
                    st.success(detail)
                    st.toast("Tracker auth valid.", icon="?")
                elif status in {"Invalid", "Forbidden", "Missing"}:
                    status_box.update(label=f"Tracker auth: {status}", state="error")
                    st.warning(detail)
                else:
                    status_box.update(label=f"Tracker auth: {status}", state="complete")
                    st.info(detail)

        with st.expander("Expected secret names"):
            st.code(
                'OPENAI_API_KEY = "your-openai-key"\n'
                'TRACKER_API_KEY = "your-tracker-key"',
                language="toml",
            )
