"""Fictitious end-to-end demo: build four fake schema snapshots in memory
(no SQL Server connection needed), run them through the real comparison
engine, and generate real HTML/PDF/console reports.

Useful to see the tool's output shape before wiring up real database
connections. Run from the repo root with the project's venv:

    .\\.venv\\Scripts\\python.exe examples\\demo_fictitious_comparison.py
"""

from __future__ import annotations

from schema_comparator.compare.engine import compare_snapshots
from schema_comparator.discovery.models import (
    ColumnSnapshot,
    SchemaSnapshot,
    TableSnapshot,
)
from schema_comparator.report.write import write_reports


def _column(
    name: str,
    data_type: str,
    *,
    length: int | None = None,
    precision: int | None = None,
    scale: int | None = None,
    nullable: bool = True,
    ordinal: int,
) -> ColumnSnapshot:
    return ColumnSnapshot(
        name=name,
        data_type=data_type,
        character_maximum_length=length,
        numeric_precision=precision,
        numeric_scale=scale,
        is_nullable=nullable,
        ordinal_position=ordinal,
    )


def build_policies_db() -> SchemaSnapshot:
    """Fictitious 'policies-db' schema."""
    customers = TableSnapshot(
        schema_name="dbo",
        table_name="customers",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("full_name", "nvarchar", length=200, ordinal=2),
            _column("email", "nvarchar", length=320, ordinal=3),
            _column("loyalty_tier", "nvarchar", length=20, ordinal=4),  # length 20
        ),
    )
    policies = TableSnapshot(
        schema_name="dbo",
        table_name="policies",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("customer_id", "int", nullable=False, ordinal=2),
            _column("premium_amount", "decimal", precision=10, scale=2, ordinal=3),  # 10,2
        ),
    )
    return SchemaSnapshot(
        profile_name="policies-db",
        tables=(customers, policies),
    )


def build_claims_db() -> SchemaSnapshot:
    """Fictitious 'claims-db' schema."""
    customers = TableSnapshot(
        schema_name="dbo",
        table_name="customers",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("full_name", "nvarchar", length=200, ordinal=2),
            _column("email", "nvarchar", length=320, ordinal=3),
            # loyalty_tier is missing here
        ),
    )
    policies = TableSnapshot(
        schema_name="dbo",
        table_name="policies",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("customer_id", "int", nullable=False, ordinal=2),
            _column("premium_amount", "decimal", precision=12, scale=4, ordinal=3),  # 12,4 (Mismatch)
        ),
    )
    return SchemaSnapshot(
        profile_name="claims-db",
        tables=(customers, policies),
    )


def build_billing_db() -> SchemaSnapshot:
    """Fictitious 'billing-db' schema."""
    customers = TableSnapshot(
        schema_name="dbo",
        table_name="customers",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("full_name", "nvarchar", length=200, ordinal=2),
            _column("email", "nvarchar", length=320, ordinal=3),
            _column("loyalty_tier", "nvarchar", length=50, ordinal=4),  # length 50 (Mismatch)
        ),
    )
    policies = TableSnapshot(
        schema_name="dbo",
        table_name="policies",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("customer_id", "int", nullable=False, ordinal=2),
            _column("premium_amount", "decimal", precision=10, scale=2, ordinal=3),  # 10,2
        ),
    )
    invoices = TableSnapshot(
        schema_name="dbo",
        table_name="invoices",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("invoice_date", "datetime", ordinal=2),
            _column("tax_amount", "decimal", precision=18, scale=2, ordinal=3),
        ),
    )
    return SchemaSnapshot(
        profile_name="billing-db",
        tables=(customers, policies, invoices),
    )


def build_reporting_db() -> SchemaSnapshot:
    """Fictitious 'reporting-db' schema (warehouse-oriented)."""
    customers = TableSnapshot(
        schema_name="dbo",
        table_name="customers",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("full_name", "nvarchar", length=200, ordinal=2),
            _column("email", "nvarchar", length=100, ordinal=3),  # length 100 (Mismatch)
            # loyalty_tier is missing here
        ),
    )
    invoices = TableSnapshot(
        schema_name="dbo",
        table_name="invoices",
        columns=(
            _column("id", "int", nullable=False, ordinal=1),
            _column("invoice_date", "datetime", ordinal=2),
            # tax_amount is missing here
        ),
    )
    return SchemaSnapshot(
        profile_name="reporting-db",
        tables=(customers, invoices),
    )


def main() -> None:
    snapshots = [
        build_policies_db(),
        build_claims_db(),
        build_billing_db(),
        build_reporting_db(),
    ]
    result = compare_snapshots(snapshots)

    print(f"Compared profiles: {', '.join(result.compared_profiles)}")
    print(f"Diff entries found: {len(result.entries)}\n")

    write_reports(result)


if __name__ == "__main__":
    main()
