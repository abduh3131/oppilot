import argparse, time
import numpy as np
import zmq
from adapters.common.pubsub import Bus, pub_json


# Publish synthetic frames to validate throughput and bus


def parse_args():
ap = argparse.ArgumentParser()
ap.add_argument("--width", type=int, default=1280)
ap.add_argument("--height", type=int, default=720)
ap.add_argument("--fps", type=int, default=20)
ap.add_argument("--pattern", choices=["gradient","noise","bars"], default="gradient")
ap.add_argument("--topic", default=b"camera.front", type=lambda s: s.encode())
return ap.parse_args()




def make_frame(w, h, t, pattern):
if pattern == "noise":
img = (np.random.rand(h, w, 3) * 255).astype(np.uint8)
elif pattern == "bars":
img = np.zeros((h, w, 3), dtype=np.uint8)
bar_w = max(1, w // 10)
for i in range(10):
img[:, i*bar_w:(i+1)*bar_w, :] = (i*25) % 255
else: # gradient
x = np.linspace(0, 255, w, dtype=np.uint8)
y = np.linspace(0, 255, h, dtype=np.uint8)
xv, yv = np.meshgrid(x, y)
img = np.stack([xv, yv, ((xv.astype(int)+yv.astype(int))%256).astype(np.uint8)], axis=-1)
return img




def main():
args = parse_args()
bus = Bus()
pub = bus.publisher()
period = 1.0 / max(1, args.fps)
t = 0
while True:
frame = make_frame(args.width, args.height, t, args.pattern)
# Send lightweight header + raw bytes (keep it simple for now)
payload = {
"type": "rgb8",
"w": args.width,
"h": args.height,
"ts": time.time(),
}
pub_json(pub, args.topic, payload)
# then the bytes (separate multipart so subscribers can decide)
pub.send_multipart([args.topic + b".bytes", frame.tobytes()])
t += 1
time.sleep(period)


if __name__ == "__main__":
main()