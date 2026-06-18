from pathlib import Path
import runpy
import streamlit as st

st.caption("Live Tracker AI Coach beta page")

legacy_page = Path(__file__).with_name("9_FalseTech_AI_Coach.py")

if legacy_page.exists():
    runpy.run_path(str(legacy_page), run_name="__main__")
else:
    st.error("Legacy AI coach page was not found.")
