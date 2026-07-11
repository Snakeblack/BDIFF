"""Integration tests: real `run.py` invocation against a minimal,
dependency-free fixture project (copied into a tmp_path), exercising
actual `venv.create` + `pip install -e .` + subprocess relaunch — no
mocking. Slower than the unit suite by design; isolated here per the
existing `tests/integration/` convention (see `test_extraction_live.py`).
"""

import shutil
import subprocess
import sys
from pathlib import Path

_RUN_PY = Path(__file__).resolve().parents[2] / "run.py"
_READY_MARKER_NAME = ".schema_comparator_ready"


def _make_fixture_project(tmp_path: Path) -> Path:
    """A minimal, dependency-free `schema_comparator` package: just enough
    for `pip install -e .` and `python -m schema_comparator.cli` to work
    quickly, without pulling in this repo's real (heavier) dependencies."""
    project_dir = tmp_path / "fixture-project"
    (project_dir / "src" / "schema_comparator").mkdir(parents=True)
    (project_dir / "pyproject.toml").write_text(
        """\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "fixture-project"
version = "0.0.1"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]
""",
        encoding="utf-8",
    )
    (project_dir / "src" / "schema_comparator" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (project_dir / "src" / "schema_comparator" / "cli.py").write_text(
        """\
def main(argv=None):
    print("fixture-cli-ran")


if __name__ == "__main__":
    main()
""",
        encoding="utf-8",
    )
    shutil.copy(_RUN_PY, project_dir / "run.py")
    return project_dir


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def test_first_run_creates_working_venv_with_marker(tmp_path) -> None:
    project_dir = _make_fixture_project(tmp_path)

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "fixture-cli-ran" in result.stdout
    venv_dir = project_dir / ".venv"
    assert _venv_python(venv_dir).exists()
    assert (venv_dir / _READY_MARKER_NAME).exists()


def test_second_run_does_not_reprovision(tmp_path) -> None:
    project_dir = _make_fixture_project(tmp_path)
    subprocess.run(
        [sys.executable, "run.py"], cwd=project_dir, capture_output=True, text=True
    )
    marker = project_dir / ".venv" / _READY_MARKER_NAME
    mtime_before = marker.stat().st_mtime

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "fixture-cli-ran" in result.stdout
    assert marker.stat().st_mtime == mtime_before


def test_deleting_venv_triggers_reprovisioning(tmp_path) -> None:
    project_dir = _make_fixture_project(tmp_path)
    subprocess.run(
        [sys.executable, "run.py"], cwd=project_dir, capture_output=True, text=True
    )
    shutil.rmtree(project_dir / ".venv")

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "fixture-cli-ran" in result.stdout
    venv_dir = project_dir / ".venv"
    assert _venv_python(venv_dir).exists()
    assert (venv_dir / _READY_MARKER_NAME).exists()
