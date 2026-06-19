import argparse
import json
import re
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class NetworkSample:
    timestamp: str
    target: str
    packets_sent: int
    packets_received: int
    packet_loss_pct: float
    avg_ping_ms: float | None
    min_ping_ms: float | None
    max_ping_ms: float | None
    jitter_ms: float | None
    latency_variance_ms: float | None
    score: int
    rating: str
    flags: list[str]


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_ping_times(text):
    values = []
    for match in re.finditer(r"time[=<]\s*([0-9]+(?:\.[0-9]+)?)\s*ms", text, re.IGNORECASE):
        values.append(float(match.group(1)))
    if re.search(r"time<\s*1\s*ms", text, re.IGNORECASE):
        values.append(0.5)
    return values


def parse_packets(text, expected_count, received_from_times):
    match = re.search(
        r"Sent\s*=\s*(\d+).*?Received\s*=\s*(\d+).*?Lost\s*=\s*(\d+).*?\((\d+(?:\.\d+)?)%\s*loss\)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if match:
        sent = int(match.group(1))
        received = int(match.group(2))
        loss = float(match.group(4))
        return sent, received, loss

    sent = expected_count
    received = received_from_times
    loss = ((sent - received) / sent) * 100 if sent else 100
    return sent, received, round(loss, 2)


def calc_jitter(times):
    if len(times) < 2:
        return None
    diffs = [abs(times[i] - times[i - 1]) for i in range(1, len(times))]
    return round(sum(diffs) / len(diffs), 2)


def score_network(avg_ping, jitter, loss, variance):
    flags = []

    if avg_ping is None:
        ping_score = 0
        flags.append("NO_PING_RESPONSE")
    elif avg_ping <= 30:
        ping_score = 40
    elif avg_ping <= 50:
        ping_score = 36
    elif avg_ping <= 70:
        ping_score = 30
    elif avg_ping <= 100:
        ping_score = 22
    else:
        ping_score = 10
        flags.append("HIGH_PING")

    if jitter is None:
        jitter_score = 0 if avg_ping is None else 20
    elif jitter < 5:
        jitter_score = 25
    elif jitter <= 10:
        jitter_score = 21
    elif jitter <= 20:
        jitter_score = 14
        flags.append("JITTER_WARNING")
    else:
        jitter_score = 5
        flags.append("BAD_JITTER")

    if loss <= 0:
        loss_score = 25
    elif loss <= 1:
        loss_score = 20
    elif loss <= 3:
        loss_score = 12
        flags.append("PACKET_LOSS_NOTICEABLE")
    else:
        loss_score = 3
        flags.append("BAD_PACKET_LOSS")

    if variance is None:
        variance_score = 0 if avg_ping is None else 7
    elif variance < 10:
        variance_score = 10
    elif variance <= 20:
        variance_score = 7
    elif variance <= 40:
        variance_score = 4
        flags.append("LATENCY_SWING")
    else:
        variance_score = 1
        flags.append("SEVERE_LATENCY_SWING")

    total = max(0, min(100, ping_score + jitter_score + loss_score + variance_score))

    if total >= 96:
        rating = "Elite"
    elif total >= 85:
        rating = "Excellent"
    elif total >= 70:
        rating = "Good"
    elif total >= 50:
        rating = "Fair"
    else:
        rating = "Poor"

    if loss > 1 or (jitter is not None and jitter > 15):
        flags.append("APEX_NETWORK_INSTABILITY")

    return int(total), rating, sorted(set(flags))


def sample_target(target, count):
    cmd = ["ping", "-n", str(count), "-w", "1000", target]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=count + 10)
        output = result.stdout + "\n" + result.stderr
    except Exception as exc:
        output = str(exc)

    times = parse_ping_times(output)
    sent, received, loss = parse_packets(output, count, len(times))

    avg_ping = round(statistics.mean(times), 2) if times else None
    min_ping = round(min(times), 2) if times else None
    max_ping = round(max(times), 2) if times else None
    jitter = calc_jitter(times)
    variance = round(max(times) - min(times), 2) if times else None

    score, rating, flags = score_network(avg_ping, jitter, loss, variance)

    return NetworkSample(
        timestamp=now_utc(),
        target=target,
        packets_sent=sent,
        packets_received=received,
        packet_loss_pct=round(loss, 2),
        avg_ping_ms=avg_ping,
        min_ping_ms=min_ping,
        max_ping_ms=max_ping,
        jitter_ms=jitter,
        latency_variance_ms=variance,
        score=score,
        rating=rating,
        flags=flags,
    )


def append_history(path, sample):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(sample)) + "\n")


def main():
    parser = argparse.ArgumentParser(description="FalseTech Apex Network Monitor")
    parser.add_argument("--target", action="append", default=None)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--out", default="data/network/network_history.jsonl")
    args = parser.parse_args()

    targets = args.target or ["1.1.1.1", "8.8.8.8"]
    out = Path(args.out)

    while True:
        for target in targets:
            sample = sample_target(target, args.count)
            append_history(out, sample)
            print(json.dumps(asdict(sample), indent=2))

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
