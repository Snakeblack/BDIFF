"""Optional table-name substring exclusion, applied to a `SchemaSnapshot`
after extraction and before comparison.

Filtering here (rather than inside the comparison engine) keeps
`compare_snapshots` unaware of any exclusion policy: an excluded table is
simply never part of any profile's snapshot, so it can never contribute a
`MissingTable`/`MissingColumn`/`ColumnMismatch` entry for any profile.
"""

from collections.abc import Sequence

from schema_comparator.discovery.models import SchemaSnapshot


def filter_excluded_tables(
    snapshot: SchemaSnapshot, exclude_patterns: Sequence[str]
) -> SchemaSnapshot:
    """Return a copy of `snapshot` with tables dropped whose `table_name`
    contains any of `exclude_patterns` (case-insensitive substring match).

    An empty/omitted `exclude_patterns` returns `snapshot` unchanged.
    """
    if not exclude_patterns:
        return snapshot
    needles = [p.lower() for p in exclude_patterns if p]
    if not needles:
        return snapshot
    tables = tuple(
        table
        for table in snapshot.tables
        if not any(needle in table.table_name.lower() for needle in needles)
    )
    return SchemaSnapshot(profile_name=snapshot.profile_name, tables=tables)
