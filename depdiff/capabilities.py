"""Read-only JavaScript capability scanning and version-to-version diffing."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from .errors import CapabilityError, MetadataError
from .metadata import load_package_metadata
from .models import (
    LIFECYCLE_SCRIPTS,
    CapabilityChange,
    CapabilityDiff,
    CapabilityFinding,
    CapabilitySet,
    PackageFixture,
    PackageMetadata,
    Rule,
    RuleSet,
)
from .rules import compile_rule


JAVASCRIPT_EXTENSIONS = frozenset({".cjs", ".js", ".jsx", ".mjs"})
_MAX_EVIDENCE_CHARS = 240


def scan_javascript(
    root: str | Path, rules: RuleSet | Iterable[Rule]
) -> CapabilitySet:
    """Scan JavaScript source files below ``root`` without importing them.

    Files are opened as UTF-8 text, visited in POSIX path order, and matched
    one line at a time. Symlinked files are skipped. A rule creates at most one
    finding per source line, which keeps evidence stable even when a line
    repeats an API call.
    """

    package_root = _validated_root(root)
    javascript_rules = _normalise_rules(rules).for_source("javascript")
    compiled_rules = tuple((rule, compile_rule(rule)) for rule in javascript_rules)
    findings: list[CapabilityFinding] = []
    for source_path in _javascript_files(package_root):
        try:
            source = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise CapabilityError(f"could not read JavaScript source {source_path}: {exc}") from exc
        relative_path = source_path.relative_to(package_root).as_posix()
        for line_number, line in enumerate(source.splitlines(), start=1):
            for rule, pattern in compiled_rules:
                if pattern.search(line) is None:
                    continue
                findings.append(
                    CapabilityFinding(
                        capability=rule.capability,
                        rule_id=rule.id,
                        severity=rule.severity,
                        source_file=relative_path,
                        line=line_number,
                        evidence=_evidence(line),
                        reason=rule.reason or rule.description,
                    )
                )
    return CapabilitySet(tuple(findings))


def scan_package(
    package: PackageFixture | str | Path,
    rules: RuleSet | Iterable[Rule],
    *,
    metadata: PackageMetadata | None = None,
) -> CapabilitySet:
    """Scan package JavaScript and lifecycle metadata using the same rules.

    ``package`` may be a Phase 1 ``PackageFixture`` or a package root path. If
    a root path is supplied and it contains ``package.json``, metadata is read
    with the existing validated metadata loader. No JavaScript, npm command,
    lifecycle script, or other fixture code is executed.
    """

    fixture_metadata = package.metadata if isinstance(package, PackageFixture) else None
    package_root = _validated_root(package.root if isinstance(package, PackageFixture) else package)
    if metadata is None:
        metadata = fixture_metadata
    metadata_path = (
        Path(package.metadata_path)
        if isinstance(package, PackageFixture)
        else package_root / "package.json"
    )

    rule_set = _normalise_rules(rules)
    javascript = scan_javascript(package_root, rule_set)
    metadata_rules = rule_set.for_source("metadata")
    if not metadata_rules:
        return javascript

    if metadata is None and metadata_path.is_file():
        try:
            metadata = load_package_metadata(str(metadata_path))
        except MetadataError as exc:
            raise CapabilityError(
                f"could not load package metadata for capability scanning: {exc}"
            ) from exc
    if metadata is None:
        return javascript

    metadata_findings = _scan_lifecycle_metadata(
        package_root, metadata_path, metadata, metadata_rules
    )
    return CapabilitySet((*javascript.findings, *metadata_findings))


def compare_capabilities(
    old: CapabilitySet | Iterable[CapabilityFinding],
    new: CapabilitySet | Iterable[CapabilityFinding],
) -> CapabilityDiff:
    """Classify each capability category as ADDED, REMOVED, or UNCHANGED.

    Classification is category-based: changing the location or evidence for a
    category that existed in both versions remains ``UNCHANGED``. The complete
    old and new evidence is retained on each change for later reporting.
    """

    old_set = old if isinstance(old, CapabilitySet) else CapabilitySet(tuple(old))
    new_set = new if isinstance(new, CapabilitySet) else CapabilitySet(tuple(new))
    changes: list[CapabilityChange] = []
    for capability in sorted(set(old_set.capabilities) | set(new_set.capabilities)):
        old_findings = old_set.for_capability(capability)
        new_findings = new_set.for_capability(capability)
        if not old_findings:
            change = "ADDED"
        elif not new_findings:
            change = "REMOVED"
        else:
            change = "UNCHANGED"
        changes.append(
            CapabilityChange(
                capability=capability,
                change=change,
                old_findings=old_findings,
                new_findings=new_findings,
            )
        )
    return CapabilityDiff(tuple(changes))


def diff_capabilities(
    old: CapabilitySet | Iterable[CapabilityFinding],
    new: CapabilitySet | Iterable[CapabilityFinding],
) -> CapabilityDiff:
    """Backward-friendly alias for callers that prefer a diff verb."""

    return compare_capabilities(old, new)


def _normalise_rules(rules: RuleSet | Iterable[Rule]) -> RuleSet:
    if isinstance(rules, RuleSet):
        return rules
    return RuleSet(tuple(rules))


def _validated_root(root: str | Path) -> Path:
    path = Path(root).expanduser()
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as exc:
        raise CapabilityError(f"could not resolve package root {path}: {exc}") from exc
    if not resolved.exists():
        raise CapabilityError(f"package root does not exist: {path}")
    if not resolved.is_dir():
        raise CapabilityError(f"package root is not a directory: {path}")
    return resolved


def _javascript_files(root: Path) -> tuple[Path, ...]:
    files = [
        path
        for path in root.rglob("*")
        if path.suffix in JAVASCRIPT_EXTENSIONS
        and path.is_file()
        and not path.is_symlink()
    ]
    return tuple(sorted(files, key=lambda path: path.relative_to(root).as_posix()))


def _evidence(line: str) -> str:
    cleaned = line.strip()
    if len(cleaned) <= _MAX_EVIDENCE_CHARS:
        return cleaned
    return cleaned[: _MAX_EVIDENCE_CHARS - 3] + "..."


def _scan_lifecycle_metadata(
    package_root: Path,
    metadata_path: Path,
    metadata: PackageMetadata,
    rules: tuple[Rule, ...],
) -> tuple[CapabilityFinding, ...]:
    if not hasattr(metadata, "scripts") or not isinstance(metadata.scripts, dict):
        return ()

    metadata_lines = _read_metadata_lines(metadata_path)
    compiled_rules = tuple((rule, compile_rule(rule)) for rule in rules)
    findings: list[CapabilityFinding] = []
    for script_name in LIFECYCLE_SCRIPTS:
        command = metadata.scripts.get(script_name)
        if command is None:
            continue
        candidate = f"scripts.{script_name}"
        for rule, pattern in compiled_rules:
            if pattern.search(candidate) is None:
                continue
            findings.append(
                CapabilityFinding(
                    capability=rule.capability,
                    rule_id=rule.id,
                    severity=rule.severity,
                    source_file=_relative_metadata_path(package_root, metadata_path),
                    line=metadata_lines.get(script_name, 1),
                    evidence=_evidence(f"{candidate}: {command}"),
                    reason=rule.reason or rule.description,
                )
            )
    return tuple(findings)


def _read_metadata_lines(metadata_path: Path) -> dict[str, int]:
    try:
        lines = metadata_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}
    locations: dict[str, int] = {}
    for script_name in LIFECYCLE_SCRIPTS:
        key_pattern = re.compile(rf"^\s*\"{re.escape(script_name)}\"\s*:")
        for line_number, line in enumerate(lines, start=1):
            if key_pattern.search(line):
                locations[script_name] = line_number
                break
    return locations


def _relative_metadata_path(package_root: Path, metadata_path: Path) -> str:
    try:
        return metadata_path.resolve().relative_to(package_root).as_posix()
    except (ValueError, OSError):
        return metadata_path.name
