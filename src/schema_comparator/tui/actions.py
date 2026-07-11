"""Pure, Textual-independent business logic for TUI-triggered actions.

Kept separate from `app.py`/`widgets.py` so it can be unit-tested without
any Textual app/event-loop machinery, matching the existing
`formatting.py` convention of isolating pure logic from widget code.
"""

from schema_comparator.compare.engine import compare_snapshots
from schema_comparator.compare.models import ComparisonResult
from schema_comparator.config.models import ConnectionProfile
from schema_comparator.discovery.filters import filter_excluded_tables
from schema_comparator.discovery.service import extract_schema


def run_comparison(
    profiles: list[ConnectionProfile], exclude_patterns: list[str]
) -> ComparisonResult:
    """Re-extract schemas for `profiles` and re-compare, applying
    `exclude_patterns` exactly as `cli.py`'s startup path already does.

    Raises on extraction/connection failure — callers (the Textual worker
    in `app.py`) are responsible for catching and reporting it; this
    function intentionally has no `try`/`except` of its own.
    """
    snapshots = [extract_schema(profile) for profile in profiles]
    if exclude_patterns:
        snapshots = [
            filter_excluded_tables(snapshot, exclude_patterns) for snapshot in snapshots
        ]
    return compare_snapshots(snapshots)
