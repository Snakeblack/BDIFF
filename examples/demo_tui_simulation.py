"""Simulation launcher for testing the interactive TUI and the Decision Phase.

Runs the TUI with fictitious in-memory schema snapshots without requiring any
database connection. Run from the repository root:

    .\\.venv\\Scripts\\python.exe examples\\demo_tui_simulation.py
"""

from schema_comparator.compare.engine import compare_snapshots
from schema_comparator.tui.app import SchemaComparatorApp
from demo_fictitious_comparison import (
    build_policies_db,
    build_claims_db,
    build_billing_db,
    build_reporting_db,
)
from schema_comparator.config.models import ConnectionProfile


def main() -> None:
    # 1. Build 4 fictitious snapshots
    snapshots = [
        build_policies_db(),
        build_claims_db(),
        build_billing_db(),
        build_reporting_db(),
    ]
    
    # 2. Compute differences
    result = compare_snapshots(snapshots)
    
    # 3. Build ConnectionProfile objects for simulation
    profiles = [
        ConnectionProfile(name=name, connection_string=f"Database={name};")
        for name in result.compared_profiles
    ]
    
    # 4. Launch TUI in simulation mode
    app = SchemaComparatorApp(
        result,
        profiles=profiles
    )
    app.run()


if __name__ == "__main__":
    main()
