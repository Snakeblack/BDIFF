"""Command-line entry point: load profiles, extract schemas, compare, report.

Wires `config.loader.load_profiles` -> `discovery.service.extract_schema`
-> `compare.engine.compare_snapshots` -> `report.write.write_reports`. No
`--format` flag: v1 always generates all three report outputs.
"""

from __future__ import annotations

import argparse

from schema_comparator.compare.engine import compare_snapshots
from schema_comparator.config.loader import load_profiles
from schema_comparator.discovery.service import extract_schema
from schema_comparator.report.write import write_reports


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="schema-comparator")
    parser.add_argument(
        "--config", required=True, help="Path to connection profiles YAML"
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        help="Subset of profile names to compare (default: all)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    profiles = load_profiles(args.config)
    if args.profiles:
        profiles = [p for p in profiles if p.name in args.profiles]

    snapshots = [extract_schema(p) for p in profiles]
    result = compare_snapshots(snapshots)

    write_reports(result)  # always all three; no --format flag


if __name__ == "__main__":
    main()

