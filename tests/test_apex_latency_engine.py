"""Basic regression tests for the latency source analyzer."""
from apex_latency_engine import NetworkSample, SettingsProfile, analyze_latency, network_queue_ms, visibility_score


def test_network_queue_ms_detects_loaded_ping_delta():
    sample = NetworkSample(idle_ping_ms=30, loaded_ping_ms=75)
    assert network_queue_ms(sample) == 45


def test_simulated_lower_gpu_load_can_reduce_total_estimate():
    current = SettingsProfile(name="Current", fps_target=180, gpu_load_pct=96, cpu_load_pct=50)
    simulated = SettingsProfile(name="Simulated", fps_target=180, gpu_load_pct=82, cpu_load_pct=45)
    network = NetworkSample(idle_ping_ms=30, loaded_ping_ms=35, jitter_ms=2, packet_loss_pct=0)
    report = analyze_latency(current, simulated, network)
    assert report.simulated_total_ms < report.current_total_ms


def test_visibility_score_is_bounded():
    profile = SettingsProfile(name="Test", gpu_load_pct=100, shadows_low=True, effects_low=True)
    assert 0 <= visibility_score(profile) <= 100
