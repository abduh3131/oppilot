"""Quick subscriber to inspect the ZeroMQ mock sensor bus."""
from __future__ import annotations

import json

import zmq

from adapters.common.pubsub import Bus


def main() -> None:
    bus = Bus()
    sub = bus.subscriber(topics=(b"gps.raw", b"camera.front", b"camera.front.bytes"))
    print("listening… (Ctrl+C to stop)")
    while True:
        parts = sub.recv_multipart()
        topic = parts[0].decode()
        if topic.endswith(".bytes"):
            print(topic, "bytes=", len(parts[1]))
        else:
            print(topic, json.loads(parts[1]))


if __name__ == "__main__":
    main()
