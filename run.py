"""Stdlib-only zero-setup launcher: provisions `.venv` on demand (creating
it and installing this project into it) and relaunches the CLI inside
that virtual environment, forwarding all arguments and the exit code.

No third-party imports here — this script must run with any bare
Python 3.11+ interpreter, before the project (or anything it depends on)
is installed anywhere.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

_VENV_DIR_NAME = ".venv"
_READY_MARKER_NAME = ".schema_comparator_ready"


def resolve_venv_dir(repo_root: Path) -> Path:
    return repo_root / _VENV_DIR_NAME


def resolve_venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def is_venv_ready(venv_dir: Path) -> bool:
    return (
        resolve_venv_python(venv_dir).exists()
        and (venv_dir / _READY_MARKER_NAME).exists()
    )


def build_pip_install_argv(venv_python: Path, repo_root: Path) -> list[str]:
    return [str(venv_python), "-m", "pip", "install", "-e", str(repo_root)]


def build_relaunch_argv(venv_python: Path, cli_args: list[str]) -> list[str]:
    return [str(venv_python), "-m", "schema_comparator.cli", *cli_args]


def _run_checked(argv: list[str], *, step_name: str) -> None:
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {step_name} failed:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode or 1)


def _provision(repo_root: Path, venv_dir: Path) -> None:
    venv.create(venv_dir, with_pip=True)
    venv_python = resolve_venv_python(venv_dir)
    _run_checked(
        build_pip_install_argv(venv_python, repo_root),
        step_name="pip install -e .",
    )
    (venv_dir / _READY_MARKER_NAME).write_text("ok\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    cli_args = sys.argv[1:] if argv is None else argv
    repo_root = Path(__file__).resolve().parent
    venv_dir = resolve_venv_dir(repo_root)

    if not is_venv_ready(venv_dir):
        _provision(repo_root, venv_dir)

    venv_python = resolve_venv_python(venv_dir)
    completed = subprocess.run(build_relaunch_argv(venv_python, cli_args))
    sys.exit(completed.returncode)


if __name__ == "__main__":
    main()
