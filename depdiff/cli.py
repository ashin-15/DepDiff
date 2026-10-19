"""Command-line interface for the depdiff Phase 1 foundation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .analysis import analyze_upgrade
from .errors import DepdiffError
from .fixtures import FixtureStore
from .models import PackageFixture, UpgradeAnalysis
from .reporters import render_json, render_markdown, render_terminal
from .rules import load_default_rules, load_rules


def build_parser() -> argparse.ArgumentParser:
    """Build the public command-line parser."""

    parser = argparse.ArgumentParser(
        prog="depdiff",
        description=(
            "Compare dependency versions using safe, offline npm fixtures. "
            "Report metadata and static capability changes for human review."
        ),
    )
    parser.add_argument("--version", action="version", version=f"depdiff {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    npm_parser = commands.add_parser(
        "npm", help="compare two versions of a package from local npm fixtures"
    )
    npm_parser.add_argument("package", help="npm package name, for example demo-package")
    npm_parser.add_argument("old_version", help="older fixture version")
    npm_parser.add_argument("new_version", help="newer fixture version")
    npm_parser.add_argument(
        "--fixtures-dir",
        default="fixtures",
        metavar="PATH",
        help="fixture root containing npm/<package>/<version> (default: ./fixtures)",
    )
    npm_parser.add_argument(
        "--format",
        choices=("terminal", "json", "markdown"),
        default="terminal",
        help="report format (default: terminal)",
    )
    npm_parser.add_argument(
        "--rules",
        metavar="PATH",
        help="YAML capability rules (default: shipped rules/default.yaml)",
    )
    npm_parser.add_argument(
        "--output",
        metavar="PATH",
        help="write the report to PATH instead of stdout; use '-' for stdout",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "npm":
        parser.error(f"unsupported command: {args.command}")

    try:
        old_fixture, new_fixture = _load_fixtures(args)
        rules = load_rules(args.rules) if args.rules else load_default_rules()
        analysis = analyze_upgrade(old_fixture, new_fixture, rules)
        report = render_report(args, analysis)
        _write_report(report, args.output)
    except DepdiffError as exc:
        print(f"depdiff: error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"depdiff: error: could not write report: {exc}", file=sys.stderr)
        return 1
    return 0


def _load_fixtures(args: argparse.Namespace) -> tuple[PackageFixture, PackageFixture]:
    store = FixtureStore(args.fixtures_dir)
    old_fixture = store.load(args.package, args.old_version)
    new_fixture = store.load(args.package, args.new_version)
    return old_fixture, new_fixture


def render_report(
    args: argparse.Namespace,
    analysis: UpgradeAnalysis,
) -> str:
    """Render a completed analysis in the requested format."""

    if args.format == "json":
        return render_json(analysis)
    if args.format == "markdown":
        return render_markdown(analysis)
    return render_terminal(analysis)


def _write_report(report: str, output: str | None) -> None:
    if output is None or output == "-":
        sys.stdout.write(report)
        return
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
