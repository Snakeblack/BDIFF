"""Unit tests for run.py's pure path/readiness/argv-building helpers.

No real venv creation or subprocess execution here — see
tests/integration/test_run_launcher_bootstrap.py for real-venv coverage.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import run as run_launcher


def test_resolve_venv_dir_is_repo_root_slash_venv(tmp_path) -> None:
    assert run_launcher.resolve_venv_dir(tmp_path) == tmp_path / ".venv"


def test_resolve_venv_python_windows_path(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(os, "name", "nt")
    venv_dir = tmp_path / ".venv"

    assert run_launcher.resolve_venv_python(venv_dir) == venv_dir / "Scripts" / "python.exe"


def test_resolve_venv_python_posix_path(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(os, "name", "posix")
    venv_dir = tmp_path / ".venv"

    assert run_launcher.resolve_venv_python(venv_dir) == venv_dir / "bin" / "python"


def _make_ready_venv(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(os, "name", "nt")
    venv_dir = tmp_path / ".venv"
    interpreter = run_launcher.resolve_venv_python(venv_dir)
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("", encoding="utf-8")
    (venv_dir / run_launcher._READY_MARKER_NAME).write_text("ok\n", encoding="utf-8")
    return venv_dir


def test_is_venv_ready_false_when_interpreter_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(os, "name", "nt")
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / run_launcher._READY_MARKER_NAME).write_text("ok\n", encoding="utf-8")

    assert run_launcher.is_venv_ready(venv_dir) is False


def test_is_venv_ready_false_when_marker_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(os, "name", "nt")
    venv_dir = tmp_path / ".venv"
    interpreter = run_launcher.resolve_venv_python(venv_dir)
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("", encoding="utf-8")

    assert run_launcher.is_venv_ready(venv_dir) is False


def test_is_venv_ready_true_when_both_present(tmp_path, monkeypatch) -> None:
    venv_dir = _make_ready_venv(tmp_path, monkeypatch)

    assert run_launcher.is_venv_ready(venv_dir) is True


def test_build_pip_install_argv_shape(tmp_path) -> None:
    venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    repo_root = tmp_path

    argv = run_launcher.build_pip_install_argv(venv_python, repo_root)

    assert argv == [str(venv_python), "-m", "pip", "install", "-e", str(repo_root)]


def test_build_relaunch_argv_forwards_cli_args_unmodified(tmp_path) -> None:
    venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    cli_args = ["--config", "config.local.yaml", "--tui", "--exclude-tables", "LOG", "QRTZ"]

    argv = run_launcher.build_relaunch_argv(venv_python, cli_args)

    assert argv == [
        str(venv_python),
        "-m",
        "schema_comparator.cli",
        "--config",
        "config.local.yaml",
        "--tui",
        "--exclude-tables",
        "LOG",
        "QRTZ",
    ]


def test_main_skips_provisioning_when_venv_ready(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(run_launcher, "resolve_venv_dir", lambda repo_root: tmp_path / ".venv")
    monkeypatch.setattr(run_launcher, "is_venv_ready", lambda venv_dir: True)
    monkeypatch.setattr(run_launcher.Path, "resolve", lambda self: tmp_path / "run.py")

    venv_create_calls = []
    monkeypatch.setattr(
        run_launcher, "venv", type("_M", (), {"create": lambda *a, **k: venv_create_calls.append((a, k))})
    )

    run_calls = []

    def _fake_run(argv, **kwargs):
        run_calls.append(argv)
        return type("_R", (), {"returncode": 0})()

    monkeypatch.setattr(run_launcher.subprocess, "run", _fake_run)

    with monkeypatch.context() as m:
        m.setattr(sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
        try:
            run_launcher.main(["--config", "config.local.yaml"])
        except SystemExit:
            pass

    assert venv_create_calls == []
    assert len(run_calls) == 1
    assert "pip" not in run_calls[0]


def test_main_provisions_when_venv_not_ready(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(run_launcher, "resolve_venv_dir", lambda repo_root: tmp_path / ".venv")
    monkeypatch.setattr(run_launcher, "is_venv_ready", lambda venv_dir: False)
    monkeypatch.setattr(run_launcher.Path, "resolve", lambda self: tmp_path / "run.py")

    calls = []

    def _fake_create(path, with_pip=True):
        calls.append(("venv.create", path))
        Path(path).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        run_launcher, "venv", type("_M", (), {"create": staticmethod(_fake_create)})
    )

    def _fake_run(argv, **kwargs):
        calls.append(("subprocess.run", argv))
        return type("_R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(run_launcher.subprocess, "run", _fake_run)

    with monkeypatch.context() as m:
        m.setattr(sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
        try:
            run_launcher.main(["--config", "config.local.yaml"])
        except SystemExit:
            pass

    assert calls[0][0] == "venv.create"
    kinds = [c[0] for c in calls]
    assert kinds.count("subprocess.run") == 2  # pip install, then relaunch
    marker = tmp_path / ".venv" / run_launcher._READY_MARKER_NAME
    assert marker.exists()


def test_main_exits_with_child_returncode(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(run_launcher, "resolve_venv_dir", lambda repo_root: tmp_path / ".venv")
    monkeypatch.setattr(run_launcher, "is_venv_ready", lambda venv_dir: True)
    monkeypatch.setattr(run_launcher.Path, "resolve", lambda self: tmp_path / "run.py")
    monkeypatch.setattr(
        run_launcher.subprocess,
        "run",
        lambda argv, **kwargs: type("_R", (), {"returncode": 7})(),
    )

    exit_codes = []
    monkeypatch.setattr(sys, "exit", lambda code=0: exit_codes.append(code))

    run_launcher.main(["--config", "config.local.yaml"])

    assert exit_codes == [7]


def test_provision_failure_reports_error_and_skips_marker(tmp_path, monkeypatch, capsys) -> None:
    venv_dir = tmp_path / ".venv"

    def _fake_create(path, with_pip=True):
        Path(path).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        run_launcher, "venv", type("_M", (), {"create": staticmethod(_fake_create)})
    )
    monkeypatch.setattr(
        run_launcher.subprocess,
        "run",
        lambda argv, **kwargs: type(
            "_R", (), {"returncode": 1, "stdout": "", "stderr": "network unreachable"}
        )(),
    )

    with monkeypatch.context() as m:
        m.setattr(sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
        try:
            run_launcher._provision(tmp_path, venv_dir)
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError("expected SystemExit")

    captured = capsys.readouterr()
    assert "pip install -e ." in captured.err
    assert "network unreachable" in captured.err
    assert not (venv_dir / run_launcher._READY_MARKER_NAME).exists()
