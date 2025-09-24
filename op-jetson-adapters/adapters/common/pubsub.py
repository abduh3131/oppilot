"""ZeroMQ helper utilities for the adapter processes."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

import zmq


@dataclass
class ZMQEndpoints:
    """Connection details used by :class:`Bus`."""

    pub: str = "tcp://127.0.0.1:5557"
    sub: str = "tcp://127.0.0.1:5557"


class Bus:
    """Small wrapper around a shared ZeroMQ context."""

    def __init__(self, endpoints: ZMQEndpoints | None = None) -> None:
        self.ctx = zmq.Context.instance()
        self.endpoints = endpoints or ZMQEndpoints()

    # ---------------------------------------------------------------------
    def publisher(self) -> zmq.Socket:
        sock = self.ctx.socket(zmq.PUB)
        sock.bind(self.endpoints.pub)
        return sock

    def subscriber(self, topics: Iterable[bytes] = (b"",)) -> zmq.Socket:
        sock = self.ctx.socket(zmq.SUB)
        sock.connect(self.endpoints.sub)
        for topic in topics:
            sock.setsockopt(zmq.SUBSCRIBE, topic)
        return sock


def pub_json(sock: zmq.Socket, topic: bytes, obj: dict) -> None:
    """Publish a JSON payload on the provided socket."""

    sock.send_multipart([topic, json.dumps(obj).encode("utf-8")])

