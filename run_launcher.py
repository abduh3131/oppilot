"""Bootstrapper script for the OP Pilot launcher.

Running this module ensures a lightweight virtual environment exists for the
Tkinter launcher, installs its Python dependency (PyYAML) if required, and then
invokes :mod:`app` from inside that environment.  It provides a single entry
point that works on both Windows and Linux without any manual setup.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_PATH = ROOT / ".launcher-venv"


def ensure_virtualenv() -> Path:
    """Create the launcher specific virtual environment if it is missing."""

    if VENV_PATH.exists():
        return VENV_PATH

    print("[launcher] creating virtual environment…")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_PATH)])
    return VENV_PATH


def python_in_venv() -> Path:
    """Return the Python executable inside the launcher venv."""

    if os.name == "nt":
        return VENV_PATH / "Scripts" / "python.exe"
    return VENV_PATH / "bin" / "python"


def ensure_dependencies(python_exe: Path) -> None:
    """Install or update the launcher's Python dependencies."""

    print("[launcher] ensuring PyYAML is available…")
    subprocess.check_call([
        str(python_exe),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "pyyaml",
    ])


def start_launcher(python_exe: Path) -> None:
    """Execute the Tkinter launcher inside the virtual environment."""

    print("[launcher] starting GUI…")
    subprocess.check_call([str(python_exe), str(ROOT / "app.py")])


def main() -> None:
    ensure_virtualenv()
    python_exe = python_in_venv()
    ensure_dependencies(python_exe)
    start_launcher(python_exe)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
