with open('apex_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: safe_load_json duplicate return
content = content.replace(
    '''def safe_load_json(path: str):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None''',
    '''def safe_load_json(path: str):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {path}: {e}")
    return None'''
)

# Fix 2: null-check for loaded profile
content = content.replace(
    '''if "profile" not in st.session_state:
    loaded = safe_load_json(AUTOSAVE_PATH)
    st.session_state.profile = loaded if loaded else deep_copy(DEFAULT_PROFILE)''',
    '''if "profile" not in st.session_state:
    loaded = safe_load_json(AUTOSAVE_PATH)
    if isinstance(loaded, dict) and "meta" in loaded and "targets" in loaded:
        st.session_state.profile = loaded
    else:
        st.session_state.profile = deep_copy(DEFAULT_PROFILE)'''
)

# Fix 3: ping_sample cross-platform  
old_ping = '''def ping_sample(host: str = "1.1.1.1", count: int = 10) -> Tuple[Optional[int], Optional[float]]:
    try:
        out = subprocess.check_output(["ping", "-n", str(count), host], text=True, errors="ignore")
    except Exception:
        return None, None
    loss = None
    m = re.search(r"Lost = \\d+ \\((\\d+)% loss\\)", out, re.IGNORECASE)
    if m:
        loss = float(m.group(1))
    avg = None
    m2 = re.search(r"Average = (\\d+)ms", out, re.IGNORECASE)
    if m2:
        avg = int(m2.group(1))
    return avg, loss'''

new_ping = '''def ping_sample(host: str = "1.1.1.1", count: int = 10) -> Tuple[Optional[int], Optional[float]]:
    try:
        # Use -n for Windows, -c for Unix-like systems
        ping_cmd = ["ping", "-n" if platform.system() == "Windows" else "-c", str(count), host]
        out = subprocess.check_output(ping_cmd, text=True, errors="ignore")
    except Exception:
        return None, None
    loss = None
    # Windows: "Lost = X (Y% loss)"; Unix: "X% packet loss"
    m = re.search(r"(?:Lost = \\d+ \\((\\d+)% loss\\)|(\\d+)% packet loss)", out, re.IGNORECASE)
    if m:
        loss = float(m.group(1) or m.group(2) or 0)
    avg = None
    # Windows: "Average = Xms"; Unix: "avg = Xms" or similar
    m2 = re.search(r"(?:Average|avg) = ([\\d.]+)ms", out, re.IGNORECASE)
    if m2:
        avg = int(float(m2.group(1)))
    return avg, loss'''
content = content.replace(old_ping, new_ping)

# Fix 4: OCR monitor index
old_ocr = '''def ocr_detect_end_screen_demo() -> Dict[str, Any]:
    import pytesseract
    import mss
    from PIL import Image

    keywords = ["CHAMPION", "SQUAD ELIMINATED", "MATCH SUMMARY", "YOU ARE THE CHAMPION", "ELIMINATED"]
    with mss.mss() as sct:
        mon = sct.monitors[1]'''

new_ocr = '''def ocr_detect_end_screen_demo() -> Dict[str, Any]:
    import pytesseract
    import mss
    from PIL import Image

    keywords = ["CHAMPION", "SQUAD ELIMINATED", "MATCH SUMMARY", "YOU ARE THE CHAMPION", "ELIMINATED"]
    with mss.mss() as sct:
        # Use monitor 1 (primary) if available, else 0
        mon_idx = 1 if len(sct.monitors) > 1 else 0
        mon = sct.monitors[mon_idx]'''
content = content.replace(old_ocr, new_ocr)

# Fix 5: CSV writing - handle empty results
old_csv = '''    with open(STORAGE_MAP_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["label", "path"])'''

new_csv = '''    if not rows:
        rows = [{"label": "", "path": "", "exists": "", "files": "", "size_bytes": "", "size_human": "", "newest_modifiedISO": "", "oldest_modifiedISO": "", "truncated": ""}]
    with open(STORAGE_MAP_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))'''
content = content.replace(old_csv, new_csv)

with open('apex_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Applied 5 critical fixes')
