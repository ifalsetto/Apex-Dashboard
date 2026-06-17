from pathlib import Path
import re
import shutil
import datetime as dt

ROOT = Path.cwd()
TARGET = ROOT / "apex_dashboard.py"

if not TARGET.exists():
    raise SystemExit("ERROR: apex_dashboard.py not found. Run this script from the Apex-Dashboard repo root.")

text = TARGET.read_text(encoding="utf-8")
original = text

backup_dir = ROOT / ".fix_backups"
backup_dir.mkdir(exist_ok=True)
backup = backup_dir / f"apex_dashboard_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.py.bak"
shutil.copy2(TARGET, backup)

# 1) Make streamlit_autorefresh optional.
old_import = "from streamlit_autorefresh import st_autorefresh"
new_import = '''try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
    AUTOREFRESH_IMPORT_ERROR = ""
except Exception as exc:
    st_autorefresh = None
    AUTOREFRESH_AVAILABLE = False
    AUTOREFRESH_IMPORT_ERROR = str(exc)'''

if old_import in text and "AUTOREFRESH_AVAILABLE" not in text:
    text = text.replace(old_import, new_import, 1)

# 2) Add safe helper before Match Monitor section.
helper_marker = "# -------------------- Match Monitor (heuristic) --------------------"
helper_code = '''

def safe_poll_seconds(value, default: int = 3) -> int:
    """Return a safe Streamlit auto-refresh interval in seconds."""
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        seconds = default
    return max(1, min(60, seconds))


def safe_match_autorefresh(monitor_state: Dict[str, Any]) -> None:
    """Run match-monitor autorefresh without crashing the dashboard."""
    poll_seconds = safe_poll_seconds(monitor_state.get("poll_seconds", 3))

    if not AUTOREFRESH_AVAILABLE or st_autorefresh is None:
        st.warning("Auto-refresh is unavailable. Monitoring will update when the page reruns.")
        if AUTOREFRESH_IMPORT_ERROR:
            logger.warning(f"Auto-refresh import failed: {AUTOREFRESH_IMPORT_ERROR}")
        return

    try:
        st_autorefresh(interval=poll_seconds * 1000, key="autorefresh_match")
    except AttributeError as exc:
        logger.warning(f"Auto-refresh AttributeError: {exc}")
        st.warning("Auto-refresh failed. Monitoring will update when the page reruns.")
    except Exception as exc:
        logger.warning(f"Auto-refresh failed: {exc}")
        st.warning("Auto-refresh failed. Monitoring will update when the page reruns.")

'''

if "def safe_match_autorefresh(" not in text:
    if helper_marker not in text:
        raise SystemExit(f"ERROR: Could not find marker: {helper_marker}")
    text = text.replace(helper_marker, helper_code + helper_marker, 1)

# 3) Replace the crashing direct autorefresh call.
patterns = [
    r'st_autorefresh\(\s*interval\s*=\s*int\(s\["poll_seconds"\]\)\s*\*\s*1000\s*,\s*key\s*=\s*"autorefresh_match"\s*\)',
    r"st_autorefresh\(\s*interval\s*=\s*int\(s\['poll_seconds'\]\)\s*\*\s*1000\s*,\s*key\s*=\s*'autorefresh_match'\s*\)",
]

replaced = False
for pat in patterns:
    text, count = re.subn(pat, "safe_match_autorefresh(s)", text, count=1, flags=re.MULTILINE)
    if count:
        replaced = True
        break

if not replaced and "safe_match_autorefresh(s)" not in text:
    raise SystemExit("ERROR: Could not find the direct st_autorefresh(...) call to replace.")

if text == original:
    print("No changes needed. The autorefresh fix may already be applied.")
else:
    TARGET.write_text(text, encoding="utf-8")
    print("Applied autorefresh crash fix.")
    print(f"Backup saved to: {backup}")
    print("Next commands:")
    print("  python -m py_compile apex_dashboard.py")
    print("  streamlit run apex_dashboard.py")
