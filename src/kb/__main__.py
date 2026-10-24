from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build_to_file
from .loader import prepare_kb
from .report import create_report


def _print_diagnostics(errors: list[str], warnings: list[str]) -> None:
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m src.kb")
    parser.add_argument("command", choices=("validate", "build", "report"))
    args = parser.parse_args()
    root = Path.cwd()

    if args.command == "validate":
        result = prepare_kb(root)
        _print_diagnostics(result.errors, result.warnings)
        if result.errors:
            return 1
        print(f"Validation passed: {len(result.entries)} entries")
        return 0

    if args.command == "build":
        result, payload = build_to_file(root)
        _print_diagnostics(result.errors, result.warnings)
        if result.errors or payload is None:
            return 1
        print(
            f"Build passed: {len(payload['entries'])} entries; "
            f"content hash {payload['content_hash']}"
        )
        return 0

    result, report = create_report(root)
    _print_diagnostics(result.errors, result.warnings)
    if result.errors or report is None:
        return 1
    print(report)
    print("Saved docs/kb_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
