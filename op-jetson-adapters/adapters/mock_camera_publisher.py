"""Synthetic camera publisher for quick testing."""

from __future__ import annotations

import argparse
import time

import numpy as np

from adapters.common.pubsub import Bus, pub_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument(
        "--pattern", choices=["gradient", "noise", "bars"], default="gradient"
    )
    parser.add_argument(
        "--topic", default=b"camera.front", type=lambda value: value.encode()
    )
    return parser.parse_args()


def make_frame(width: int, height: int, t: int, pattern: str) -> np.ndarray:
    if pattern == "noise":
        frame = (np.random.rand(height, width, 3) * 255).astype(np.uint8)
    elif pattern == "bars":
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        bar_width = max(1, width // 10)
        for i in range(10):
            frame[:, i * bar_width : (i + 1) * bar_width, :] = (i * 25) % 255
    else:  # gradient
        x = np.linspace(0, 255, width, dtype=np.uint8)
        y = np.linspace(0, 255, height, dtype=np.uint8)
        xv, yv = np.meshgrid(x, y)
        frame = np.stack(
            [xv, yv, ((xv.astype(int) + yv.astype(int)) % 256).astype(np.uint8)],
            axis=-1,
        )
    return frame


def main() -> None:
    args = parse_args()
    bus = Bus()
    pub = bus.publisher()
    period = 1.0 / max(1, args.fps)
    counter = 0

    while True:
        frame = make_frame(args.width, args.height, counter, args.pattern)
        payload = {
            "type": "rgb8",
            "w": args.width,
            "h": args.height,
            "ts": time.time(),
        }
        pub_json(pub, args.topic, payload)
        pub.send_multipart([args.topic + b".bytes", frame.tobytes()])
        counter += 1
        time.sleep(period)


if __name__ == "__main__":  # pragma: no cover - exercised manually
    main()

