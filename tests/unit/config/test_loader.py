"""Unit tests for schema_comparator.config.loader.load_profiles.

Grows across phases 3-6 of the connection-profile-config change:
- Phase 3: happy path + explicit-path contract
- Phase 4: missing-file / malformed-YAML fail-fast
- Phase 5: trim + duplicate-key + validation pipeline
- Phase 6: cross-cutting guardrails (secret leakage, no-fallback, network)
"""

import pathlib

import pytest

from schema_comparator.config.errors import (
    ConfigFileNotFoundError,
    ConfigParseError,
    ProfileValidationError,
)
from schema_comparator.config.loader import load_profiles
from schema_comparator.config.models import ConnectionProfile


def _write_yaml(tmp_path: pathlib.Path, content: str, filename: str = "config.local.yaml") -> pathlib.Path:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


# --- Phase 3: happy path + explicit-path contract ---------------------------


def test_two_entry_file_returns_two_profiles(tmp_path: pathlib.Path) -> None:
    content = """
databases:
  poliza-service: "Driver={ODBC Driver 18 for SQL Server};Server=srv1;Database=PolizaDB;UID=u;PWD=p;"
  siniestro-service: "Driver={ODBC Driver 18 for SQL Server};Server=srv2;Database=SiniestroDB;Trusted_Connection=yes;"
"""
    config_path = _write_yaml(tmp_path, content)

    profiles = load_profiles(config_path)

    assert len(profiles) == 2
    by_name = {p.name: p for p in profiles}
    assert by_name["poliza-service"].connection_string == (
        "Driver={ODBC Driver 18 for SQL Server};Server=srv1;Database=PolizaDB;UID=u;PWD=p;"
    )
    assert by_name["siniestro-service"].connection_string == (
        "Driver={ODBC Driver 18 for SQL Server};Server=srv2;Database=SiniestroDB;Trusted_Connection=yes;"
    )
    assert all(isinstance(p, ConnectionProfile) for p in profiles)


@pytest.mark.parametrize("count", [1, 3, 20])
def test_arbitrary_number_of_profiles_load(tmp_path: pathlib.Path, count: int) -> None:
    lines = [f'  service-{i}: "Driver=X;Server=srv{i};Database=Db{i};UID=u;PWD=p;"' for i in range(count)]
    content = "databases:\n" + "\n".join(lines) + "\n"
    config_path = _write_yaml(tmp_path, content)

    profiles = load_profiles(config_path)

    assert len(profiles) == count


def test_load_profiles_with_no_args_raises_type_error() -> None:
    with pytest.raises(TypeError):
        load_profiles()  # type: ignore[call-arg]


def test_load_profiles_from_arbitrary_named_file_and_location(tmp_path: pathlib.Path) -> None:
    nested_dir = tmp_path / "nested" / "dir"
    nested_dir.mkdir(parents=True)
    content = 'databases:\n  only-service: "Driver=X;Server=srv;Database=Db;UID=u;PWD=p;"\n'
    config_path = _write_yaml(nested_dir, content, filename="my-weird-name.yml")

    profiles = load_profiles(config_path)

    assert len(profiles) == 1
    assert profiles[0].name == "only-service"


# --- Phase 4: missing-file / malformed-YAML fail-fast ------------------------


def test_missing_file_raises_config_file_not_found_error(tmp_path: pathlib.Path) -> None:
    missing_path = tmp_path / "does-not-exist.yaml"

    with pytest.raises(ConfigFileNotFoundError) as exc_info:
        load_profiles(missing_path)

    assert "config.example.yaml" in str(exc_info.value)


def test_malformed_yaml_raises_config_parse_error(tmp_path: pathlib.Path) -> None:
    # Unterminated flow mapping -> a YAML syntax error.
    content = "databases: [unterminated"
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ConfigParseError) as exc_info:
        load_profiles(config_path)

    message = str(exc_info.value)
    assert "YAMLError" not in message
    assert "ScannerError" not in message
    assert "ParserError" not in message
    assert "unterminated" not in message.lower()


def test_non_mapping_top_level_raises_config_parse_error(tmp_path: pathlib.Path) -> None:
    content = "- just\n- a\n- list\n"
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ConfigParseError):
        load_profiles(config_path)


def test_missing_databases_key_raises_config_parse_error(tmp_path: pathlib.Path) -> None:
    content = "not_databases:\n  a: b\n"
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ConfigParseError):
        load_profiles(config_path)


def test_databases_not_a_mapping_raises_config_parse_error(tmp_path: pathlib.Path) -> None:
    content = "databases:\n  - a\n  - b\n"
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ConfigParseError):
        load_profiles(config_path)


# --- Phase 5: trim, duplicate-key, and validation pipeline -------------------


def test_leading_and_trailing_whitespace_is_trimmed(tmp_path: pathlib.Path) -> None:
    content = 'databases:\n  "  poliza-service  ": "  Driver=X;PWD=y;  "\n'
    config_path = _write_yaml(tmp_path, content)

    profiles = load_profiles(config_path)

    assert len(profiles) == 1
    assert profiles[0].name == "poliza-service"
    assert profiles[0].connection_string == "Driver=X;PWD=y;"


def test_exact_duplicate_yaml_key_raises_profile_validation_error(tmp_path: pathlib.Path) -> None:
    content = (
        "databases:\n"
        '  poliza-service: "Driver=X;PWD=first;"\n'
        '  poliza-service: "Driver=X;PWD=second;"\n'
    )
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ProfileValidationError):
        load_profiles(config_path)


def test_case_insensitive_duplicate_name_raises_profile_validation_error(
    tmp_path: pathlib.Path,
) -> None:
    content = (
        "databases:\n"
        '  Poliza-Service: "Driver=X;PWD=first;"\n'
        '  poliza-service: "Driver=X;PWD=second;"\n'
    )
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ProfileValidationError):
        load_profiles(config_path)


def test_blank_name_raises_profile_validation_error(tmp_path: pathlib.Path) -> None:
    content = 'databases:\n  "   ": "Driver=X;PWD=y;"\n'
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ProfileValidationError) as exc_info:
        load_profiles(config_path)

    assert "PWD" not in str(exc_info.value)


def test_blank_connection_string_raises_profile_validation_error(tmp_path: pathlib.Path) -> None:
    content = 'databases:\n  poliza-service: "   "\n'
    config_path = _write_yaml(tmp_path, content)

    with pytest.raises(ProfileValidationError) as exc_info:
        load_profiles(config_path)

    assert "poliza-service" in str(exc_info.value)
