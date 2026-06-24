"""Type definitions for Apex Dashboard."""
from typing import TypedDict, Optional, List, Any, Dict


class MetaInfo(TypedDict, total=False):
    """Profile metadata."""

    profileName: str
    lastUpdatedISO: str
    monitor: str
    gpu: str
    os: str
    notes: str


class TargetsConfig(TypedDict, total=False):
    """FPS and latency targets."""

    refreshHz: int
    fpsTarget: int
    latencyGoalMs: int


class TogglesConfig(TypedDict, total=False):
    """Boolean feature toggles."""

    hdrWindowsOn: bool
    autoHdrOn: bool
    rtxHdrOn: bool
    gsyncOn: bool
    vsyncInGameOff: bool
    reflexBoostOn: bool


class LaunchOption(TypedDict, total=False):
    """Single launch option."""

    key: str
    enabled: bool
    note: str


class NetworkConfig(TypedDict, total=False):
    """Network settings."""

    connection: str
    dns: str
    router_model: str
    modem_model: str
    mtu: str
    qos_enabled: str
    bufferbloat_grade: str
    isp: str
    notes: str
    tests: Dict[str, Any]


class PrivacyConfig(TypedDict, total=False):
    """Privacy settings."""

    sanitize_exports: bool
    redact_user_paths: bool
    redact_machine_name: bool


class Profile(TypedDict, total=False):
    """Complete user profile."""

    meta: MetaInfo
    targets: TargetsConfig
    toggles: TogglesConfig
    launchOptions: List[LaunchOption]
    hdrSetup: Dict[str, Any]
    presets: Dict[str, Any]
    performanceLogs: List[Dict[str, Any]]
    network: NetworkConfig
    privacy: PrivacyConfig


class PerformanceLog(TypedDict, total=False):
    """Match performance log entry."""

    createdISO: str
    match_startISO: str
    match_endISO: str
    duration_s: int
    mode: str
    map: str
    hdr_mode: str
    avg_fps: float
    one_percent_low: float
    ping_ms: Optional[int]
    packet_loss_pct: Optional[float]
    cpu_avg_pct: float
    cpu_peak_pct: float
    input_feel_1_10: str
    settings_signature: str
    compare_to_similar: str
    notes: str


class MonitorState(TypedDict, total=False):
    """Monitor/auto-logger state."""

    enabled: bool
    poll_seconds: int
    start_streak_needed: int
    end_streak_needed: int
    in_match: bool
    match_startISO: str
    match_endISO: str
    cpu_samples: List[float]
    cpu_peak: float
    last_tickISO: str
    apex_running: bool
    apex_foreground: bool
    fg_title: str
    fg_process: str
    fg_streak: int
    bg_streak: int
