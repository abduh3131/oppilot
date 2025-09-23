import argparse, sys, time, json
from adapters.common.pubsub import Bus, pub_json


# Modes: mock file reader today; serial later


def parse_args():
ap = argparse.ArgumentParser()
ap.add_argument("--source_file", default="./config/mock_nmea.txt")
ap.add_argument("--baud", type=int, default=9600)
ap.add_argument("--topic", default=b"gps.raw", type=lambda s: s.encode())
ap.add_argument("--rate_hz", type=float, default=5.0)
return ap.parse_args()


# Very light NMEA parsing (just pull lat/lon from GPRMC/GPGGA)


def extract_fix(nmea_line: str):
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


def dm_to_deg(dm, hemi):
if not dm:
return None
# ddmm.mmmm -> dd + mm/60
dd = float(dm[:2]) if len(dm) >= 4 else 0.0
mm = float(dm[2:]) if len(dm) > 2 else 0.0
deg = dd + mm/60.0
if hemi in ("S","W"):
deg = -deg
return deg


lat = dm_to_deg(lat_raw, lat_ns)
lon = dm_to_deg(lon_raw, lon_ew)
if lat is None or lon is None:
return None
return {"lat": lat, "lon": lon}
except Exception:
return None




def main():
args = parse_args()
bus = Bus()
pub = bus.publisher()


# mock file tail loop
with open(args.source_file, "r") as f:
lines = f.readlines()


idx = 0
period = 1.0 / args.rate_hz
while True:
line = lines[idx % len(lines)].strip()
idx += 1
fix = extract_fix(line)
if fix:
msg = {"type": "gps_fix", "fix": fix, "ts": time.time()}
pub_json(pub, args.topic, msg)
time.sleep(period)


if __name__ == "__main__":
main()