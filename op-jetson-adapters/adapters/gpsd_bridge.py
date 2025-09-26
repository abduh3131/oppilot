"""Mock GPS bridge that replays an NMEA log."""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Optional

from adapters.common.pubsub import Bus, pub_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_file", default="./config/mock_nmea.txt")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--topic", default=b"gps.raw", type=lambda s: s.encode())
    parser.add_argument("--rate_hz", type=float, default=5.0)
    return parser.parse_args()


def extract_fix(nmea_line: str) -> Optional[dict]:
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

        def dm_to_deg(dm: str, hemi: str) -> Optional[float]:
            if not dm:
                return None
            # ddmm.mmmm -> dd + mm/60
            deg = float(dm[:2]) if len(dm) >= 4 else 0.0
            minutes = float(dm[2:]) if len(dm) > 2 else 0.0
            value = deg + minutes / 60.0
            if hemi in ("S", "W"):
                value = -value
            return value

        lat = dm_to_deg(lat_raw, lat_ns)
        lon = dm_to_deg(lon_raw, lon_ew)
        if lat is None or lon is None:
            return None
        return {"lat": lat, "lon": lon}
    except Exception:
        return None


def main() -> None:
    args = parse_args()
    bus = Bus()
    publisher = bus.publisher()

    lines = Path(args.source_file).read_text().strip().splitlines()
    if not lines:
        raise SystemExit(f"No NMEA sentences found in {args.source_file}")

    idx = 0
    period = 1.0 / max(0.1, args.rate_hz)
    while True:
        line = lines[idx % len(lines)].strip()
        idx += 1
        fix = extract_fix(line)
        if fix:
            msg = {"type": "gps_fix", "fix": fix, "ts": time.time()}
            pub_json(publisher, args.topic, msg)
        time.sleep(period)


if __name__ == "__main__":
    main()
