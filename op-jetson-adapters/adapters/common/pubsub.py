from dataclasses import dataclass
import json
import zmq


@dataclass
class ZMQEndpoints:
pub: str = "tcp://127.0.0.1:5557"
sub: str = "tcp://127.0.0.1:5557"


class Bus:
def __init__(self, endpoints: ZMQEndpoints = ZMQEndpoints()):
self.ctx = zmq.Context.instance()
self.endpoints = endpoints


def publisher(self):
s = self.ctx.socket(zmq.PUB)
s.bind(self.endpoints.pub)
return s


def subscriber(self, topics=(b"",)):
s = self.ctx.socket(zmq.SUB)
s.connect(self.endpoints.sub)
for t in topics:
s.setsockopt(zmq.SUBSCRIBE, t)
return s


# helpers


def pub_json(sock, topic: bytes, obj: dict):
sock.send_multipart([topic, json.dumps(obj).encode("utf-8")])