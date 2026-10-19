"""Build authentic, offline showcase reports with the depdiff engine.

Run from the repository root with ``python3 scripts/build_showcase_data.py``.
Use ``--check`` to verify the checked-in data without writing any files.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("showcase/data/reports.json")

# Direct script execution puts scripts/, rather than the checkout, on sys.path.
sys.path.insert(0, str(REPO_ROOT))

from depdiff.analysis import analyze_upgrade
from depdiff.errors import DepdiffError
from depdiff.fixtures import FixtureStore
from depdiff.reporters import render_json, render_markdown, render_terminal
from depdiff.rules import load_default_rules


SCENARIOS = (
    (
        "suspicious",
        "Installation, filesystem, and process capabilities added",
        "demo-package",
        "1.0.0",
        "2.0.0",
    ),
    (
        "benign",
        "Formatting update with no new capability evidence",
        "benign-package",
        "1.0.0",
        "1.1.0",
    ),
    # No versioned review-only npm fixture is available. A rollback demonstrates
    # removed capabilities instead; its verdict remains the engine's real "ok".
    (
        "review",
        "Rollback: installation, filesystem, and process capabilities removed",
        "demo-package",
        "2.0.0",
        "1.0.0",
    ),
)


def build_data() -> dict[str, object]:
    """Analyze existing fixtures and preserve all three real report formats."""

    store = FixtureStore(REPO_ROOT / "fixtures")
    rules = load_default_rules()
    scenarios = []
    for scenario_id, label, package, old_version, new_version in SCENARIOS:
        analysis = analyze_upgrade(
            store.load(package, old_version),
            store.load(package, new_version),
            rules,
        )
        scenarios.append(
            {
                "id": scenario_id,
                "label": label,
                "command": (
                    f"python3 -m depdiff npm {package} {old_version} {new_version} "
                    "--fixtures-dir fixtures"
                ),
                "report": json.loads(render_json(analysis)),
                "terminal": render_terminal(analysis),
                "markdown": render_markdown(analysis),
            }
        )
    return {"schema_version": 1, "scenarios": scenarios}


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the data, or return nonzero when checked-in bytes are stale."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail if output is missing or stale"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="output path, relative to the repository root unless absolute",
    )
    args = parser.parse_args(argv)
    destination = REPO_ROOT / args.output
    regenerate = "python3 scripts/build_showcase_data.py"
    if args.output != DEFAULT_OUTPUT:
        regenerate += f" --output {shlex.quote(str(args.output))}"
    try:
        expected = (json.dumps(build_data(), indent=2, allow_nan=False) + "\n").encode(
            "utf-8"
        )
        if args.check:
            try:
                actual = destination.read_bytes()
            except FileNotFoundError:
                print(
                    f"Showcase data is missing: {args.output}. Run {regenerate}.",
                    file=sys.stderr,
                )
                return 1
            if actual != expected:
                print(
                    f"Showcase data is stale: {args.output}. Run {regenerate}.",
                    file=sys.stderr,
                )
                return 1
            print(f"Showcase data is current: {args.output}")
            return 0

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(expected)
    except (DepdiffError, OSError) as exc:
        print(f"Showcase data error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote showcase data: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
