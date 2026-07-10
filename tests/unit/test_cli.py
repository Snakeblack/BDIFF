"""Unit tests for cli.main: argparse wiring and write_reports dispatch."""

from unittest.mock import MagicMock, patch

from schema_comparator.cli import main
from schema_comparator.config.models import ConnectionProfile


def _profiles():
    return [
        ConnectionProfile(name="a", connection_string="DSN=a"),
        ConnectionProfile(name="b", connection_string="DSN=b"),
    ]


def test_cli_main_invokes_write_reports_after_compare_snapshots() -> None:
    fake_result = MagicMock(name="ComparisonResult")
    with (
        patch("schema_comparator.cli.load_profiles", return_value=_profiles()) as m_load,
        patch("schema_comparator.cli.extract_schema", side_effect=lambda p: p) as m_extract,
        patch(
            "schema_comparator.cli.compare_snapshots", return_value=fake_result
        ) as m_compare,
        patch("schema_comparator.cli.write_reports") as m_write,
    ):
        main(["--config", "config.local.yaml"])

    m_load.assert_called_once_with("config.local.yaml")
    assert m_extract.call_count == 2
    m_compare.assert_called_once()
    m_write.assert_called_once_with(fake_result)


def test_cli_main_filters_profiles_when_profiles_flag_given() -> None:
    fake_result = MagicMock(name="ComparisonResult")
    with (
        patch("schema_comparator.cli.load_profiles", return_value=_profiles()),
        patch("schema_comparator.cli.extract_schema", side_effect=lambda p: p) as m_extract,
        patch("schema_comparator.cli.compare_snapshots", return_value=fake_result),
        patch("schema_comparator.cli.write_reports"),
    ):
        main(["--config", "config.local.yaml", "--profiles", "a"])

    assert m_extract.call_count == 1
    assert m_extract.call_args[0][0].name == "a"
