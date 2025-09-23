import zmq, json
ctx=zmq.Context.instance(); s=ctx.socket(zmq.SUB)
s.connect("tcp://127.0.0.1:5557")
for t in (b"gps.raw", b"camera.front", b"camera.front.bytes"):
    s.setsockopt(zmq.SUBSCRIBE, t)
print("listening… (Ctrl+C to stop)")
while True:
    parts = s.recv_multipart()
    topic = parts[0].decode()
    if topic.endswith(".bytes"):
        print(topic, "bytes=", len(parts[1]))
    else:
        print(topic, json.loads(parts[1]))