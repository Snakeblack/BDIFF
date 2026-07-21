"""Normalized, immutable table/column metadata models for one profile.

Re-exported from domain.schema.models for backward compatibility.
"""

from schema_comparator.domain.schema.models import (
    ColumnSnapshot,
    SchemaSnapshot,
    TableSnapshot,
)

__all__ = ["ColumnSnapshot", "TableSnapshot", "SchemaSnapshot"]
