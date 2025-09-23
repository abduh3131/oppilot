# start_op_dev.ps1
# Runs your dev stack in TWO WSL windows: daemons + sniffer

# --- edit only if your path changes ---
$WIN_PATH = "C:\Users\Abduh\Downloads\astratest\op-jetson-adapters"
$WSL_PATH = "/mnt/c/Users/Abduh/Downloads/astratest/op-jetson-adapters"
# --------------------------------------

# sanity checks
if (-not (Test-Path $WIN_PATH)) {
  Write-Error "Path not found: $WIN_PATH"
  exit 1
}
# make sure the sniffer file exists on Windows side
$snifferPy = @'
import zmq, json, numpy as np
ctx=zmq.Context.instance(); s=ctx.socket(zmq.SUB)
s.connect("tcp://127.0.0.1:5557")
for t in (b"gps.raw", b"camera.front", b"camera.front.bytes"):
    s.setsockopt(zmq.SUBSCRIBE, t)
print("listening…  (Ctrl+C to stop)")
while True:
    parts = s.recv_multipart()
    topic = parts[0].decode()
    if topic.endswith(".bytes"):
        print(topic, "bytes=", len(parts[1]))
    else:
        print(topic, json.loads(parts[1]))
'@
$snifferPath = Join-Path $WIN_PATH "tools\sniffer.py"
if (-not (Test-Path (Split-Path $snifferPath))) {
  New-Item -ItemType Directory -Force -Path (Split-Path $snifferPath) | Out-Null
}
$snifferPy | Set-Content -Path $snifferPath -NoNewline

# commands to run inside WSL
$daemonCmd = "cd '$WSL_PATH'; python3 -m venv .venv || true; " +
             "source .venv/bin/activate; " +
             "python -m pip install -U pip; " +
             "pip install -r requirements.txt numpy pillow; " +
             "command -v dos2unix >/dev/null 2>&1 && dos2unix tools/sniffer.py || true; " +
             "./tools/run_all.sh"

$snifferCmd = "cd '$WSL_PATH'; source .venv/bin/activate; python tools/sniffer.py"

# open two WSL terminals
Start-Process wsl.exe -ArgumentList @("bash","-lc",$daemonCmd) -WorkingDirectory $WIN_PATH -WindowStyle Normal
Start-Process wsl.exe -ArgumentList @("bash","-lc",$snifferCmd) -WorkingDirectory $WIN_PATH -WindowStyle Normal
