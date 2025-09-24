"""Launcher GUI for automating the op-jetson-adapters stack.

This module provides a small Tkinter based GUI that automates the setup of the
project on both Windows (through WSL) and native Linux.  The launcher mirrors
the manual steps described in ``instructions.txt`` while adding quality of life
features such as sensor selection and structured logging.  The GUI offers a
single **Start** button and a panel of checkboxes that allow the operator to
choose which sensors should be active before the autopilot stack is started.

Usage
-----

Run ``python app.py`` from the repository root on either Windows (with WSL
installed) or Linux.  When running from Windows the script automatically shells
into WSL for all heavy lifting.  When **Start** is pressed the launcher will:

1. Validate that the ``op-jetson-adapters`` directory exists.
2. Ensure that a Python virtual environment is present and all dependencies are
   installed.
3. Generate a temporary sensor configuration based on the selected checkboxes
   (without modifying the original ``config/sensors.yaml`` file).
4. Run ``tools/run_all.sh`` inside the adapters directory.

The log pane at the bottom of the window surfaces command output and status
messages.  A **Stop** button becomes available once the autopilot process is
running so that it can be shut down gracefully.
"""

from __future__ import annotations

import queue
import shlex
import subprocess
import threading
import time
import tkinter as tk
from collections.abc import Iterable
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

import platform

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - dependency available via requirements.txt
    raise SystemExit(
        "PyYAML is required to run the launcher. Install the project "
        "dependencies first."
    ) from exc


class LauncherApp:
    """Interactive Tk based launcher.

    The class owns the GUI components and encapsulates all orchestration logic
    (environment preparation, configuration handling and process management).
    """

    GENERATED_CONFIG = "launcher_selected.yaml"

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("OP Pilot Launcher")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.repo_path = Path(__file__).resolve().parent
        self.adapters_path = self.repo_path / "op-jetson-adapters"
        self.config_path = self.adapters_path / "config" / "sensors.yaml"
        self.generated_config_path = (
            self.adapters_path / "config" / self.GENERATED_CONFIG
        )

        if not self.adapters_path.exists():
            raise SystemExit(
                "op-jetson-adapters directory not found. Please run the launcher "
                "from the repository root."
            )

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.sensor_widgets: Dict[str, List[tuple[tk.BooleanVar, dict]]] = {}
        self.running_process: Optional[subprocess.Popen[str]] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.output_thread: Optional[threading.Thread] = None
        self.running = False

        self._build_ui()
        self._load_sensors()
        self.root.after(150, self._drain_log_queue)

    # ------------------------------------------------------------------ UI ---
    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        intro = ttk.Label(
            main,
            text=(
                "Select the sensors to enable and press Start. The launcher will "
                "prepare the WSL/Linux environment and run the adapters stack."
            ),
            wraplength=520,
            justify="left",
        )
        intro.pack(fill="x", pady=(0, 10))

        sensors_frame = ttk.LabelFrame(main, text="Sensors")
        sensors_frame.pack(fill="x", expand=False)
        self.sensor_container = sensors_frame

        controls = ttk.Frame(main)
        controls.pack(fill="x", pady=10)

        self.start_button = ttk.Button(controls, text="Start", command=self.on_start)
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(
            controls, text="Stop", state="disabled", command=self.on_stop
        )
        self.stop_button.pack(side="left", padx=(10, 0))

        self.status_var = tk.StringVar(value="Idle")
        status = ttk.Label(controls, textvariable=self.status_var)
        status.pack(side="right")

        log_frame = ttk.LabelFrame(main, text="Log")
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame,
            height=18,
            state="disabled",
            wrap="word",
            background="#111",
            foreground="#DDD",
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _load_sensors(self) -> None:
        data = self._read_yaml(self.config_path)
        if not isinstance(data, dict):
            raise SystemExit(
                "Unexpected sensors.yaml structure. Expected a mapping of categories."
            )

        for child in self.sensor_container.winfo_children():
            child.destroy()

        for category, entries in data.items():
            frame = ttk.LabelFrame(
                self.sensor_container, text=category.replace("_", " ").title()
            )
            frame.pack(fill="x", expand=True, padx=8, pady=6)

            self.sensor_widgets[category] = []
            if not isinstance(entries, Iterable):
                continue
            for sensor in entries:
                if not isinstance(sensor, dict):
                    continue
                name = sensor.get("name", "unnamed")
                var = tk.BooleanVar(value=True)
                chk = ttk.Checkbutton(frame, text=name, variable=var)
                chk.pack(anchor="w", padx=4, pady=2)
                self.sensor_widgets[category].append((var, sensor))

    # ----------------------------------------------------------- UI helpers ---
    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}\n")

    def _drain_log_queue(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.root.after(150, self._drain_log_queue)

    def set_running(self, value: bool) -> None:
        self.running = value
        self.start_button.configure(state="disabled" if value else "normal")
        self.stop_button.configure(state="normal" if value else "disabled")
        self.status_var.set("Running" if value else "Idle")

    # ------------------------------------------------------------ sensors ---
    def _collect_selected_sensors(self) -> Dict[str, List[dict]]:
        selected: Dict[str, List[dict]] = {}
        for category, entries in self.sensor_widgets.items():
            group: List[dict] = []
            for var, sensor in entries:
                if var.get():
                    group.append(sensor)
            selected[category] = group
        return selected

    def _write_generated_config(self, config: Dict[str, List[dict]]) -> None:
        yaml_text = yaml.safe_dump(config, sort_keys=False)
        self.generated_config_path.write_text(yaml_text)
        self.log(
            f"Wrote sensor selection to {self.generated_config_path.relative_to(self.repo_path)}"
        )

    # ------------------------------------------------------- env helpers ---
    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    def _ensure_wsl(self) -> None:
        if not self.is_windows:
            return
        try:
            result = subprocess.run(
                ["wsl", "--version"], capture_output=True, text=True, check=False
            )
        except FileNotFoundError as exc:  # pragma: no cover - Windows only
            raise RuntimeError(
                "WSL is not available. Install it from Windows Features or the "
                "Microsoft Store."
            ) from exc

        if result.returncode != 0:
            fallback = subprocess.run(
                ["wsl", "-l", "-q"], capture_output=True, text=True, check=False
            )
            if fallback.returncode != 0:
                raise RuntimeError(
                    "Unable to query WSL status. Ensure WSL is installed and "
                    "initialised."
                )

    def _run_shell(self, command: str) -> subprocess.CompletedProcess[str]:
        self.log(f"$ {command}")
        if self.is_windows:
            proc = subprocess.run(
                ["wsl", "bash", "-lc", command],
                capture_output=True,
                text=True,
            )
        else:
            proc = subprocess.run(
                ["bash", "-lc", command], capture_output=True, text=True
            )

        if proc.stdout:
            for line in proc.stdout.splitlines():
                self.log(line)
        if proc.stderr:
            for line in proc.stderr.splitlines():
                self.log(line)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Command failed ({proc.returncode}): {command}"
            )
        return proc

    def _to_wsl_path(self, path: Path) -> str:
        if not self.is_windows:
            return str(path)
        proc = subprocess.run(
            ["wsl", "wslpath", str(path)], capture_output=True, text=True, check=True
        )
        return proc.stdout.strip()

    def ensure_environment(self) -> None:
        self._ensure_wsl()
        adapters_wsl = self._to_wsl_path(self.adapters_path)
        quoted = shlex.quote(adapters_wsl)
        base = f"cd {quoted}"
        commands = [
            f"{base} && python3 -m venv .venv 2>/dev/null || true",
            f"{base} && source .venv/bin/activate && python -m pip install -U pip",
            (
                f"{base} && source .venv/bin/activate && "
                "pip install -r requirements.txt numpy pillow"
            ),
            (
                f"{base} && if command -v dos2unix >/dev/null 2>&1; then "
                "dos2unix adapters/*.py adapters/common/*.py tools/run_all.sh || true; fi"
            ),
            f"{base} && chmod +x tools/run_all.sh",
        ]

        for cmd in commands:
            self._run_shell(cmd)

    # ------------------------------------------------------- launch logic ---
    def launch(self) -> None:
        self.set_running(True)
        try:
            selected = self._collect_selected_sensors()
            self._write_generated_config(selected)
            self.ensure_environment()
            self._start_process()
        except Exception as exc:  # pragma: no cover - depends on environment
            self.log(f"ERROR: {exc}")
            self.root.after(0, lambda: self.set_running(False))
            messagebox.showerror("Launcher", str(exc))

    def _start_process(self) -> None:
        adapters_wsl = self._to_wsl_path(self.adapters_path)
        quoted = shlex.quote(adapters_wsl)
        env_prefix = (
            f"SENSORS_CONFIG=./config/{self.GENERATED_CONFIG} "
            f"PYTHONUNBUFFERED=1"
        )
        cmd = (
            f"cd {quoted} && source .venv/bin/activate && {env_prefix} ./tools/run_all.sh"
        )

        if self.is_windows:
            popen_cmd = ["wsl", "bash", "-lc", cmd]
        else:
            popen_cmd = ["bash", "-lc", cmd]

        self.log("Starting adapters stack...")
        self.running_process = subprocess.Popen(
            popen_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        self.output_thread = threading.Thread(
            target=self._stream_process_output, daemon=True
        )
        self.output_thread.start()

        self.monitor_thread = threading.Thread(
            target=self._monitor_process, daemon=True
        )
        self.monitor_thread.start()

    def _stream_process_output(self) -> None:
        assert self.running_process and self.running_process.stdout
        for line in self.running_process.stdout:
            self.log(line.rstrip())

    def _monitor_process(self) -> None:
        assert self.running_process is not None
        code = self.running_process.wait()
        self.root.after(0, lambda: self._on_process_exit(code))

    def _on_process_exit(self, code: int) -> None:
        self.log(f"Process exited with code {code}")
        self.running_process = None
        self.set_running(False)

    # ------------------------------------------------------------ events ---
    def on_start(self) -> None:
        if self.running:
            return
        threading.Thread(target=self.launch, daemon=True).start()

    def on_stop(self) -> None:
        if not self.running_process:
            return
        self.log("Stopping adapters stack…")
        self.running_process.terminate()
        try:
            self.running_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.log("Force killing process")
            self.running_process.kill()
        finally:
            self.running_process = None
            self.set_running(False)

    def on_close(self) -> None:
        if self.running_process is not None:
            self.on_stop()
        self.root.destroy()

    # ----------------------------------------------------------- utilities ---
    @staticmethod
    def _read_yaml(path: Path) -> dict:
        try:
            return yaml.safe_load(path.read_text()) or {}
        except FileNotFoundError as exc:
            raise SystemExit(f"Missing configuration file: {path}") from exc


def main() -> None:
    app = LauncherApp()
    app.root.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
