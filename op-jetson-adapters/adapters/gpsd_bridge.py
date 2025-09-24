"""Mock GPS bridge that replays NMEA sentences over ZeroMQ."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from adapters.common.pubsub import Bus, pub_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_file", default="./config/mock_nmea.txt")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--serial", default="")
    parser.add_argument("--topic", default=b"gps.raw", type=lambda value: value.encode())
    parser.add_argument("--rate_hz", type=float, default=5.0)
    return parser.parse_args()


def dm_to_deg(dm: str, hemi: str) -> float | None:
    if not dm:
        return None
    try:
        raw = float(dm)
    except ValueError:
        return None

    degrees = int(raw // 100)
    minutes = raw - degrees * 100
    value = degrees + minutes / 60.0
    if hemi in {"S", "W"}:
        value = -value
    return value


def extract_fix(nmea_line: str) -> dict | None:
    try:
        if nmea_line.startswith("$GPRMC"):
            parts = nmea_line.split(",")
            lat_raw, lat_ns = parts[3], parts[4]
            lon_raw, lon_ew = parts[5], parts[6]
        elif nmea_line.startswith("$GPGGA"):
            parts = nmea_line.split(",")
            lat_raw, lat_ns = parts[2], parts[3]
            lon_raw, lon_ew = parts[4], parts[5]
        else:
            return None

        lat = dm_to_deg(lat_raw, lat_ns)
        lon = dm_to_deg(lon_raw, lon_ew)
        if lat is None or lon is None:
            return None
        return {"lat": lat, "lon": lon}
    except (IndexError, ValueError):
        return None


def main() -> None:
    args = parse_args()
    bus = Bus()
    publisher = bus.publisher()

    source = Path(args.source_file)
    if not source.exists():
        raise SystemExit(f"NMEA source file not found: {source}")

    lines = source.read_text().splitlines()
    if not lines:
        raise SystemExit("NMEA source file is empty")

    period = 1.0 / max(0.01, args.rate_hz)
    index = 0

    while True:
        line = lines[index % len(lines)].strip()
        index += 1
        fix = extract_fix(line)
        if fix:
            payload = {"type": "gps_fix", "fix": fix, "ts": time.time()}
            pub_json(publisher, args.topic, payload)
        time.sleep(period)


if __name__ == "__main__":  # pragma: no cover - exercised manually
    main()

