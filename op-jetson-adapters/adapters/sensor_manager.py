"""Launch and supervise the mock sensor publishers."""
from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import yaml

CFG = Path(__file__).resolve().parents[1] / "config" / "sensors.yaml"
PROCS: List[subprocess.Popen[bytes]] = []


def launch_camera(cam: dict) -> subprocess.Popen[bytes] | None:
    if cam.get("type") == "mock":
        cmd = [
            sys.executable,
            "-m",
            "adapters.mock_camera_publisher",
            "--width",
            str(cam.get("width", 1280)),
            "--height",
            str(cam.get("height", 720)),
            "--fps",
            str(cam.get("fps", 20)),
            "--pattern",
            cam.get("pattern", "gradient"),
            "--topic",
            cam.get("topic", "camera.front"),
        ]
        return subprocess.Popen(cmd)

    print(f"TODO: implement camera type {cam.get('type')}")
    return None


def launch_gps(gps: dict) -> subprocess.Popen[bytes] | None:
    cmd = [sys.executable, "-m", "adapters.gpsd_bridge"]
    if gps.get("type") == "mock":
        cmd += ["--source_file", gps.get("source_file", "./config/mock_nmea.txt")]
    if gps.get("topic"):
        cmd += ["--topic", gps["topic"]]
    if gps.get("rate_hz"):
        cmd += ["--rate_hz", str(gps["rate_hz"])]
    return subprocess.Popen(cmd)


def read_config() -> dict:
    with CFG.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    cfg = read_config()

    for cam in cfg.get("cameras", []):
        proc = launch_camera(cam)
        if proc:
            PROCS.append(proc)

    for gps in cfg.get("gps", []):
        proc = launch_gps(gps)
        if proc:
            PROCS.append(proc)

    try:
        while True:
            alive = [proc.poll() is None for proc in PROCS]
            if not all(alive):
                print("A sensor process exited; shutting down...", flush=True)
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in PROCS:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.terminate()


if __name__ == "__main__":
    main()
