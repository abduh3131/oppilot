cd ~/dev/op-jetson-adapters
cat > adapters/sensor_manager.py <<'PY'
import subprocess, yaml, time, os, sys

CFG = "./config/sensors.yaml"

PROCS = []

def launch_camera(cam):
    if cam.get("type") == "mock":
        cmd = [
            "python3","-m","adapters.mock_camera_publisher",
            "--width",  str(cam.get("width", 1280)),
            "--height", str(cam.get("height", 720)),
            "--fps",    str(cam.get("fps", 20)),
            "--pattern", cam.get("pattern", "gradient"),
        ]
        return subprocess.Popen(cmd)
    else:
        print(f"TODO: implement camera type {cam.get('type')}")
        return None

def launch_gps(gps):
    cmd = ["python3","-m","adapters.gpsd_bridge"]
    if gps.get("type") == "mock":
        cmd += ["--source_file", gps.get("source_file","./config/mock_nmea.txt")]
    # serial mode later (e.g., --serial /dev/ttyUSB0)
    return subprocess.Popen(cmd)

def main():
    with open(CFG, "r") as f:
        cfg = yaml.safe_load(f)

    for cam in cfg.get("cameras", []):
        p = launch_camera(cam)
        if p: PROCS.append(p)

    for gps in cfg.get("gps", []):
        p = launch_gps(gps)
        if p: PROCS.append(p)

    try:
        while True:
            alive = [p.poll() is None for p in PROCS]
            if not all(alive):
                print("A process exited; restarting...")
                for p in PROCS:
                    if p.poll() is None:
                        p.terminate()
                time.sleep(1)
                os.execv(sys.executable, [sys.executable, "-m", "adapters.sensor_manager"])
            time.sleep(1)
    except KeyboardInterrupt:
        for p in PROCS:
            if p.poll() is None:
                p.terminate()

if __name__ == "__main__":
    main()
PY
