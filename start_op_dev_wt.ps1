# start_op_dev_wt.ps1
# Opens TWO panes in Windows Terminal (wt): left runs your daemons, right shows live bus messages.

# ----- EDIT THESE IF NEEDED -----
$Distro   = "Ubuntu-24.04"   # output of: wsl -l -q
$WIN_PATH = "C:\Users\Abduh\Downloads\astratest\op-jetson-adapters"
$WSL_PATH = "/mnt/c/Users/Abduh/Downloads/astratest/op-jetson-adapters"
# --------------------------------

# Create sniffer script on Windows if missing
$snifferPy = @'
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
'@
$snifferPath = Join-Path $WIN_PATH "tools\sniffer.py"
if (-not (Test-Path (Split-Path $snifferPath))) {
  New-Item -ItemType Directory -Force -Path (Split-Path $snifferPath) | Out-Null
}
$snifferPy | Set-Content -Path $snifferPath -NoNewline

# Commands to run INSIDE WSL bash
$daemonCmd  = "cd '$WSL_PATH'; python3 -m venv .venv || true; source .venv/bin/activate; " +
              "python -m pip install -U pip; pip install -r requirements.txt numpy pillow; " +
              "./tools/run_all.sh"
$snifferCmd = "cd '$WSL_PATH'; source .venv/bin/activate; python tools/sniffer.py"

# Ensure Windows Terminal exists
if (-not (Get-Command wt.exe -ErrorAction SilentlyContinue)) {
  Write-Error "Windows Terminal (wt.exe) not found. Install it from Microsoft Store, or run two Ubuntu windows manually."
  exit 1
}

# Open 2 panes: left (daemons), right (sniffer)
# Note: we explicitly call wsl -d $Distro bash -lc "<cmd>" so the right env runs.
$wtArgs = @(
  "new-tab", "-p", $Distro, "--title", "OP Daemons", "--",
  "wsl.exe", "-d", $Distro, "bash", "-lc", $daemonCmd,
  ";",
  "split-pane", "-H", "-p", $Distro, "--title", "OP Sniffer", "--",
  "wsl.exe", "-d", $Distro, "bash", "-lc", $snifferCmd
)

Start-Process wt.exe -ArgumentList $wtArgs -WorkingDirectory $WIN_PATH
