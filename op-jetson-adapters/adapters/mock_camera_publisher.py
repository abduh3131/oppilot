"""Synthetic camera publisher for feeding OpenPilot replays."""
from __future__ import annotations

import argparse
import time

import numpy as np

from adapters.common.pubsub import Bus, pub_json


# CLI ------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--pattern", choices=["gradient", "noise", "bars"], default="gradient")
    parser.add_argument("--topic", default=b"camera.front", type=lambda s: s.encode())
    return parser.parse_args()


# Frame generation -----------------------------------------------------------

def make_frame(width: int, height: int, t: int, pattern: str) -> np.ndarray:
    if pattern == "noise":
        return (np.random.rand(height, width, 3) * 255).astype(np.uint8)
    if pattern == "bars":
        img = np.zeros((height, width, 3), dtype=np.uint8)
        bar_width = max(1, width // 10)
        for i in range(10):
            img[:, i * bar_width : (i + 1) * bar_width, :] = (i * 25) % 255
        return img

    # Default to gradient pattern
    x = np.linspace(0, 255, width, dtype=np.uint8)
    y = np.linspace(0, 255, height, dtype=np.uint8)
    xv, yv = np.meshgrid(x, y)
    return np.stack([xv, yv, ((xv.astype(int) + yv.astype(int) + t) % 256).astype(np.uint8)], axis=-1)


# Main -----------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    bus = Bus()
    publisher = bus.publisher()
    period = 1.0 / max(1, args.fps)

    frame_idx = 0
    while True:
        frame = make_frame(args.width, args.height, frame_idx, args.pattern)
        payload = {
            "type": "rgb8",
            "w": args.width,
            "h": args.height,
            "ts": time.time(),
        }
        pub_json(publisher, args.topic, payload)
        publisher.send_multipart([args.topic + b".bytes", frame.tobytes()])
        frame_idx += 1
        time.sleep(period)


if __name__ == "__main__":
    main()
