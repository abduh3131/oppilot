"""Entry point that launches the configured sensor processes."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List

import yaml


CFG_ENV = "SENSORS_CONFIG"
DEFAULT_CFG = Path("./config/sensors.yaml")


def _load_config() -> Dict[str, List[dict]]:
    cfg_path = Path(os.environ.get(CFG_ENV, DEFAULT_CFG))
    if not cfg_path.exists():
        raise SystemExit(f"Sensors configuration file not found: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit("Sensors configuration must be a mapping of categories")
    return {key: list(value or []) for key, value in data.items()}


def _launch_camera(cam_cfg: dict) -> subprocess.Popen[bytes] | None:
    cam_type = cam_cfg.get("type")
    if cam_type == "mock":
        cmd = [
            "python3",
            "-m",
            "adapters.mock_camera_publisher",
            "--width",
            str(cam_cfg.get("width", 1280)),
            "--height",
            str(cam_cfg.get("height", 720)),
            "--fps",
            str(cam_cfg.get("fps", 20)),
            "--pattern",
            cam_cfg.get("pattern", "gradient"),
        ]
        topic = cam_cfg.get("topic")
        if topic:
            cmd += ["--topic", topic]
        return subprocess.Popen(cmd)

    print(f"Unsupported camera type: {cam_type}")
    return None


def _launch_gps(gps_cfg: dict) -> subprocess.Popen[bytes] | None:
    cmd = ["python3", "-m", "adapters.gpsd_bridge"]
    gps_type = gps_cfg.get("type")
    if gps_type == "mock":
        cmd += ["--source_file", gps_cfg.get("source_file", "./config/mock_nmea.txt")]
    serial = gps_cfg.get("serial")
    if serial:
        cmd += ["--serial", serial]
    topic = gps_cfg.get("topic")
    if topic:
        cmd += ["--topic", topic]
    return subprocess.Popen(cmd)


def _launch_all(config: Dict[str, Iterable[dict]]) -> List[subprocess.Popen[bytes]]:
    processes: List[subprocess.Popen[bytes]] = []
    for cam in config.get("cameras", []):
        proc = _launch_camera(cam)
        if proc:
            processes.append(proc)
    for gps in config.get("gps", []):
        proc = _launch_gps(gps)
        if proc:
            processes.append(proc)
    for lidar in config.get("lidar", []):
        print(f"Lidar support not implemented yet: {lidar}")
    return processes


def _wait_forever(processes: List[subprocess.Popen[bytes]]) -> None:
    try:
        while True:
            alive = [proc.poll() is None for proc in processes]
            if not all(alive):
                print("A process exited; shutting down remaining sensors...")
                for proc in processes:
                    if proc.poll() is None:
                        proc.terminate()
                time.sleep(1)
                sys.exit(1)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping sensors...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()


def main() -> None:
    config = _load_config()
    procs = _launch_all(config)
    if not procs:
        print("No sensors enabled. Nothing to do.")
        return
    _wait_forever(procs)


if __name__ == "__main__":  # pragma: no cover - entry point for the launcher
    main()

