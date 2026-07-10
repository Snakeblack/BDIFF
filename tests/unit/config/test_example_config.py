"""Tests for the committed config.example.yaml template."""

import pathlib

import yaml

_REAL_LOOKING_MARKERS = ("your-", "your_", "example-")


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def _load_example_config() -> dict:
    path = _repo_root() / "config.example.yaml"
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_example_config_parses_with_databases_mapping() -> None:
    document = _load_example_config()
    assert isinstance(document, dict)
    assert isinstance(document.get("databases"), dict)
    assert len(document["databases"]) >= 1


def test_example_config_values_are_obvious_placeholders() -> None:
    document = _load_example_config()
    for connection_string in document["databases"].values():
        lowered = connection_string.lower()
        assert any(marker in lowered for marker in _REAL_LOOKING_MARKERS), (
            f"Connection string does not look like an obvious placeholder: {connection_string!r}"
        )


def test_example_config_demonstrates_both_auth_modes() -> None:
    document = _load_example_config()
    values = list(document["databases"].values())
    assert any("UID=" in v and "PWD=" in v for v in values), "No SQL-auth placeholder entry found"
    assert any("Trusted_Connection=yes;" in v for v in values), (
        "No Windows-auth placeholder entry found"
    )
