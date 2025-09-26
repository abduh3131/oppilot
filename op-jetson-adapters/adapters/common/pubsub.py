"""ZeroMQ pub/sub helpers used by the mock sensor stack."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

import zmq


@dataclass
class ZMQEndpoints:
    """Connection endpoints for the in-process pub/sub bus."""

    pub: str = "tcp://127.0.0.1:5557"
    sub: str = "tcp://127.0.0.1:5557"


class Bus:
    """Tiny wrapper around ZeroMQ for publishing and subscribing."""

    def __init__(self, endpoints: ZMQEndpoints | None = None) -> None:
        self.ctx = zmq.Context.instance()
        self.endpoints = endpoints or ZMQEndpoints()

    def publisher(self) -> zmq.Socket:
        sock = self.ctx.socket(zmq.PUB)
        sock.bind(self.endpoints.pub)
        return sock

    def subscriber(self, topics: Iterable[bytes] | None = None) -> zmq.Socket:
        sock = self.ctx.socket(zmq.SUB)
        sock.connect(self.endpoints.sub)
        for topic in topics or (b"",):
            sock.setsockopt(zmq.SUBSCRIBE, topic)
        return sock


# Helpers --------------------------------------------------------------------

def pub_json(sock: zmq.Socket, topic: bytes, obj: dict) -> None:
    """Publish JSON payloads as multipart messages."""

    sock.send_multipart([topic, json.dumps(obj).encode("utf-8")])
