"""Unit tests for tui.actions.run_comparison: a pure, Textual-independent
re-extract/re-compare helper."""

from unittest.mock import MagicMock

import pytest

from schema_comparator.config.models import ConnectionProfile
from schema_comparator.tui.actions import run_comparison


def _profiles() -> list[ConnectionProfile]:
    return [
        ConnectionProfile(name="a", connection_string="DSN=a"),
        ConnectionProfile(name="b", connection_string="DSN=b"),
    ]


def test_run_comparison_calls_extract_filter_compare_in_order(monkeypatch) -> None:
    calls = []
    profiles = _profiles()

    def fake_extract(profile):
        calls.append(("extract", profile))
        return f"snapshot-{profile.name}"

    def fake_filter(snapshot, patterns):
        calls.append(("filter", snapshot, patterns))
        return f"filtered-{snapshot}"

    fake_result = MagicMock(name="ComparisonResult")

    def fake_compare(snapshots):
        calls.append(("compare", snapshots))
        return fake_result

    monkeypatch.setattr("schema_comparator.tui.actions.extract_schema", fake_extract)
    monkeypatch.setattr(
        "schema_comparator.tui.actions.filter_excluded_tables", fake_filter
    )
    monkeypatch.setattr("schema_comparator.tui.actions.compare_snapshots", fake_compare)

    result = run_comparison(profiles, ["LOG"])

    assert result is fake_result
    assert calls == [
        ("extract", profiles[0]),
        ("extract", profiles[1]),
        ("filter", "snapshot-a", ["LOG"]),
        ("filter", "snapshot-b", ["LOG"]),
        ("compare", ["filtered-snapshot-a", "filtered-snapshot-b"]),
    ]


def test_run_comparison_skips_filter_when_no_exclude_patterns(monkeypatch) -> None:
    profiles = _profiles()

    monkeypatch.setattr(
        "schema_comparator.tui.actions.extract_schema",
        lambda profile: f"snapshot-{profile.name}",
    )

    def fail_filter(snapshot, patterns):
        raise AssertionError("filter_excluded_tables must not be called")

    monkeypatch.setattr(
        "schema_comparator.tui.actions.filter_excluded_tables", fail_filter
    )

    received = {}

    def fake_compare(snapshots):
        received["snapshots"] = snapshots
        return MagicMock(name="ComparisonResult")

    monkeypatch.setattr("schema_comparator.tui.actions.compare_snapshots", fake_compare)

    run_comparison(profiles, [])

    assert received["snapshots"] == ["snapshot-a", "snapshot-b"]


def test_run_comparison_propagates_extraction_error_unmodified(monkeypatch) -> None:
    profiles = _profiles()

    def raising_extract(profile):
        raise RuntimeError("connection boom")

    monkeypatch.setattr("schema_comparator.tui.actions.extract_schema", raising_extract)

    with pytest.raises(RuntimeError, match="connection boom"):
        run_comparison(profiles, [])
