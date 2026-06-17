from __future__ import annotations

from pathlib import Path

import streamlit as st

from false_apex_ai import (
    OPENAI_MODEL_DEFAULT,
    append_report_to_profile,
    build_apex_coach_context,
    find_repo_root,
    generate_apex_ai_coach_report,
    get_openai_api_key,
    load_dashboard_profile,
    safe_save_json,
    save_report_markdown,
)

st.set_page_config(
    page_title="FalseTech Apex AI Coach",
    page_icon="🎯",
    layout="wide",
)

REPO_ROOT = find_repo_root(Path(__file__).resolve())
CSS_PATH = REPO_ROOT / "assets" / "false_apex_ai_coach.css"

if CSS_PATH.exists():
    st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <section class="ft-ai-hero" aria-labelledby="ft-ai-title">
      <p class="ft-ai-eyebrow">FalseTech Apex System</p>
      <h1 class="ft-ai-title" id="ft-ai-title">Apex AI Coach</h1>
      <p class="ft-ai-lede">
        Convert your dashboard settings, launch options, network notes, and match logs into a focused ranked improvement plan.
      </p>
    </section>
    """,
    unsafe_allow_html=True,
)

profile, profile_path = load_dashboard_profile(REPO_ROOT)

left, center, right = st.columns(3)
with left:
    st.metric("Profile Source", profile_path.name if profile_path.exists() else "Not found")
with center:
    targets = profile.get("targets", {}) if isinstance(profile.get("targets", {}), dict) else {}
    st.metric("FPS Target", targets.get("fpsTarget", "—"))
with right:
    logs = profile.get("performanceLogs", [])
    st.metric("Logged Sessions", len(logs) if isinstance(logs, list) else 0)

if not profile:
    st.warning("No saved profile found yet. Run the main dashboard once, save/autosave your profile, then return here.")

with st.expander("OpenAI setup status", expanded=False):
    api_key_present = bool(get_openai_api_key(st.secrets))
    if api_key_present:
        st.success("OPENAI_API_KEY detected.")
    else:
        st.warning("OPENAI_API_KEY is missing.")
        st.write("Create `.streamlit/secrets.toml` locally or add the secret in Streamlit Cloud.")
        st.code('OPENAI_API_KEY = "your_key_here"', language="toml")

st.subheader("Coach Input")

default_goal = (
    "Help me improve in ranked Apex. Focus on consistency, decision-making, "
    "rotations, FPS/latency stability, and what I should practice next."
)

goal = st.text_area(
    "What should the coach focus on?",
    value=default_goal,
    height=120,
    help="Examples: solo queue, Ash, Conduit, Vantage, end-game rotations, 1v1s, audio, or FPS stability.",
)

model = st.text_input(
    "OpenAI model",
    value=OPENAI_MODEL_DEFAULT,
    help="Override with OPENAI_MODEL in your environment when needed.",
)

context = build_apex_coach_context(profile, goal)

with st.expander("Preview data sent to the AI coach", expanded=False):
    st.json(context)

if st.button("Generate AI Coach Report", type="primary", use_container_width=True):
    selected_model = model.strip() or OPENAI_MODEL_DEFAULT

    with st.spinner("Analyzing Apex dashboard data..."):
        success, report = generate_apex_ai_coach_report(
            profile=profile,
            user_goal=goal,
            model=selected_model,
            streamlit_secrets=st.secrets,
        )

    if not success:
        st.error(report)
    else:
        st.success("AI coach report generated.")
        st.markdown("## AI Coach Report")
        st.markdown(report)

        updated_profile = append_report_to_profile(
            profile,
            user_goal=goal,
            report=report,
            model=selected_model,
        )
        safe_save_json(profile_path, updated_profile)
        report_path = save_report_markdown(REPO_ROOT, report)

        st.info(f"Saved report: `{report_path.relative_to(REPO_ROOT)}`")
        st.download_button(
            "Download Report",
            data=report.encode("utf-8"),
            file_name=report_path.name,
            mime="text/markdown",
            use_container_width=True,
        )

st.subheader("Recommended Next Data To Log")
st.markdown(
    """
1. Legend played.
2. Map.
3. Drop POI.
4. First fight result.
5. Damage before first knock.
6. Death reason: rotate, heal, ego swing, third party, bad comm, bad timing.
7. Average FPS and 1% low.
8. Ping, jitter, packet loss.
"""
)
