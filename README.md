# OP Pilot Launcher

This repository contains a Tkinter-based launcher that prepares the
`op-jetson-adapters` stack on Windows (via WSL) or native Linux.  The GUI lets
you choose which sensors to enable, prepares the Python environments, and then
starts the autopilot services with a single click.

## Quick start

1. Ensure Python 3.9+ is installed on your machine.  On Windows you can install
   it from the [Microsoft Store](https://apps.microsoft.com/store/detail/python-39/9P7QFQMJRFP7) or python.org.
2. Double-click `run_launcher.py` (or execute `python run_launcher.py` from a
   terminal).
3. The helper script creates a lightweight `.launcher-venv`, installs the GUI
   dependency (PyYAML), and then opens the launcher window.

From the launcher:

* Pick the sensors you want to run by toggling the checkboxes.
* Press **Start**.  The app will set up WSL (if on Windows), create the
  `op-jetson-adapters/.venv` environment, install its requirements, normalise
  script permissions, and finally call `tools/run_all.sh`.
* Watch the status updates and logs in the lower pane.  Press **Stop** at any
  time to terminate the adapters gracefully.

The launcher never edits your existing `config/sensors.yaml`; it writes the
temporary selection to `config/launcher_selected.yaml` and passes it through via
the `SENSORS_CONFIG` environment variable.

## Tips

* If you already maintain your own virtual environment for the adapters, the
  launcher will reuse it—just keep it in `op-jetson-adapters/.venv`.
* On Windows the tool automatically invokes `wsl.exe` so you do not have to open
  a Ubuntu terminal manually.
* You can still run the original manual workflow described in
  `instructions.txt`; the launcher simply automates those steps.

## Stopping everything

Use the **Stop** button or close the window.  If a process remains running in
the background, you can run the following from WSL to clean up:

```bash
pkill -f adapters.common.hub || true
pkill -f adapters.sensor_manager || true
```
