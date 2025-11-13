#!/usr/bin/env python3
"""
Utility runner to orchestrate all extract jobs.

Usage examples:
  python scripts/run_extracts.py            # run every extract
  python scripts/run_extracts.py --only neo4j --only glossary
  python scripts/run_extracts.py --all      # explicit full run
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXTRACT_SCRIPTS = {
    "core": SCRIPT_DIR / "extract.py",
    "neo4j": SCRIPT_DIR / "extract_neo4j.py",
    "glossary": SCRIPT_DIR / "extract_glossary.py",
}


def run_script(name, path):
    """Execute a child Python process and stream logs to stdout."""
    print(f"\n=== Running '{name}' ({path}) ===")
    result = subprocess.run([sys.executable, str(path)])
    if result.returncode == 0:
        print(f"--- '{name}' completed successfully ---")
    else:
        print(f"--- '{name}' failed with exit code {result.returncode} ---")
    return result.returncode


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run one or more extract jobs sequentially."
    )
    parser.add_argument(
        "--only",
        choices=EXTRACT_SCRIPTS.keys(),
        action="append",
        help="Specify one or more extract jobs to run (default: all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all extract jobs (default if no --only flags provided)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.only and args.all:
        print("Cannot combine --all with --only", file=sys.stderr)
        return 2

    if args.only:
        targets = args.only
    else:
        targets = list(EXTRACT_SCRIPTS.keys())

    missing = [name for name in targets if name not in EXTRACT_SCRIPTS]
    if missing:
        print(f"Unknown extract name(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    failures = {}
    for name in targets:
        exit_code = run_script(name, EXTRACT_SCRIPTS[name])
        if exit_code != 0:
            failures[name] = exit_code

    if failures:
        print("\nOne or more extracts failed:")
        for name, code in failures.items():
            print(f"  - {name}: exit code {code}")
        return 1

    print("\nAll requested extracts completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
