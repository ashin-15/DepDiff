"""Data models shared by fixture loading, metadata analysis, and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LIFECYCLE_SCRIPTS = ("preinstall", "install", "postinstall")
ENTRY_POINT_FIELDS = ("main", "bin", "exports")
DEPENDENCY_SECTIONS = (
    "dependencies",
    "optionalDependencies",
    "peerDependencies",
    "devDependencies",
)
CAPABILITY_CATEGORIES = (
    "network",
    "fs",
    "process",
    "env",
    "dynamic-code",
    "crypto",
    "install-script",
)
SEVERITIES = ("HIGH", "MEDIUM", "LOW")
RULE_SOURCES = ("javascript", "metadata")


@dataclass(frozen=True)
class PackageMetadata:
    """Validated metadata extracted from one package.json file."""

    name: str
    version: str
    scripts: dict[str, str]
    dependencies: dict[str, dict[str, str]]
    entry_points: dict[str, Any]


@dataclass(frozen=True)
class PackageFixture:
    """A package version selected from the local fixture store."""

    package: str
    version: str
    root: str
    metadata_path: str
    metadata: PackageMetadata


@dataclass(frozen=True)
class MetadataChange:
    """One deterministic metadata change between package versions."""

    area: str
    change: str
    name: str
    old_value: Any = None
    new_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return {
            "area": self.area,
            "change": self.change,
            "name": self.name,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


@dataclass(frozen=True)
class MetadataDiff:
    """The complete metadata comparison for two package versions."""

    lifecycle_scripts: tuple[MetadataChange, ...]
    dependencies: tuple[MetadataChange, ...]
    entry_points: tuple[MetadataChange, ...]

    @property
    def changes(self) -> tuple[MetadataChange, ...]:
        """Return all changes in stable area/name/change order."""

        return tuple(
            sorted(
                (*self.lifecycle_scripts, *self.dependencies, *self.entry_points),
                key=lambda item: (item.area, item.name, item.change),
            )
        )

    @property
    def is_empty(self) -> bool:
        """Whether the compared metadata has no relevant changes."""

        return not self.changes

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return {
            "lifecycle_scripts": [
                change.to_dict() for change in self.lifecycle_scripts
            ],
            "dependencies": [change.to_dict() for change in self.dependencies],
            "entry_points": [change.to_dict() for change in self.entry_points],
            "changes": [change.to_dict() for change in self.changes],
        }


@dataclass(frozen=True)
class Rule:
    """One externally configured static capability detection rule."""

    id: str
    capability: str
    severity: str
    pattern: str
    description: str
    reason: str = ""
    source: str = "javascript"
    flags: str = ""

    @property
    def rule_id(self) -> str:
        """Return the stable identifier using an explicit property name."""

        return self.id


@dataclass(frozen=True)
class RuleSet:
    """A deterministic collection of validated capability rules."""

    rules: tuple[Rule, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", tuple(sorted(self.rules, key=lambda item: item.id)))

    def __iter__(self):
        return iter(self.rules)

    def __len__(self) -> int:
        return len(self.rules)

    def for_source(self, source: str) -> tuple[Rule, ...]:
        """Return rules for one scanner source in stable identifier order."""

        return tuple(rule for rule in self.rules if rule.source == source)


@dataclass(frozen=True)
class CapabilityFinding:
    """One source-backed result from static capability analysis."""

    capability: str
    rule_id: str
    severity: str
    source_file: str
    line: int
    evidence: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return {
            "capability": self.capability,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "source_file": self.source_file,
            "line": self.line,
            "evidence": self.evidence,
            "reason": self.reason,
        }


def _finding_sort_key(finding: CapabilityFinding) -> tuple[Any, ...]:
    return (
        finding.capability,
        finding.source_file,
        finding.line,
        finding.rule_id,
        finding.severity,
        finding.evidence,
        finding.reason,
    )


@dataclass(frozen=True)
class CapabilitySet:
    """The findings extracted from one package version."""

    findings: tuple[CapabilityFinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(self.findings, key=_finding_sort_key)),
        )

    @property
    def capabilities(self) -> tuple[str, ...]:
        """Return detected capability categories in deterministic order."""

        return tuple(sorted({finding.capability for finding in self.findings}))

    def for_capability(self, capability: str) -> tuple[CapabilityFinding, ...]:
        """Return all evidence for one capability category."""

        return tuple(
            finding for finding in self.findings if finding.capability == capability
        )

    def to_dict(self) -> dict[str, Any]:
        """Return findings grouped by stable capability category."""

        return {
            "capabilities": list(self.capabilities),
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class CapabilityChange:
    """Presence classification for one capability category."""

    capability: str
    change: str
    old_findings: tuple[CapabilityFinding, ...] = ()
    new_findings: tuple[CapabilityFinding, ...] = ()

    @property
    def findings(self) -> tuple[CapabilityFinding, ...]:
        """Return the evidence relevant to the classified result."""

        if self.change == "REMOVED":
            return self.old_findings
        return self.new_findings

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return {
            "capability": self.capability,
            "change": self.change,
            "findings": [finding.to_dict() for finding in self.findings],
            "old_findings": [finding.to_dict() for finding in self.old_findings],
            "new_findings": [finding.to_dict() for finding in self.new_findings],
        }


@dataclass(frozen=True)
class CapabilityDiff:
    """The deterministic capability presence comparison for two versions."""

    changes: tuple[CapabilityChange, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "changes",
            tuple(sorted(self.changes, key=lambda item: item.capability)),
        )

    @property
    def added(self) -> tuple[CapabilityChange, ...]:
        return tuple(item for item in self.changes if item.change == "ADDED")

    @property
    def removed(self) -> tuple[CapabilityChange, ...]:
        return tuple(item for item in self.changes if item.change == "REMOVED")

    @property
    def unchanged(self) -> tuple[CapabilityChange, ...]:
        return tuple(item for item in self.changes if item.change == "UNCHANGED")

    @property
    def is_empty(self) -> bool:
        """Whether neither version has any detected capability category."""

        return not self.changes

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return {
            "added": [item.to_dict() for item in self.added],
            "removed": [item.to_dict() for item in self.removed],
            "unchanged": [item.to_dict() for item in self.unchanged],
            "changes": [item.to_dict() for item in self.changes],
        }


@dataclass(frozen=True)
class RiskAssessment:
    """Deterministic review recommendation for an upgrade."""

    score: int
    severity: str | None
    verdict: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "severity": self.severity,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class UpgradeAnalysis:
    """All evidence produced for one package upgrade comparison."""

    package: str
    old_version: str
    new_version: str
    metadata_diff: MetadataDiff
    old_capabilities: CapabilitySet
    new_capabilities: CapabilitySet
    capability_diff: CapabilityDiff
    assessment: RiskAssessment

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic machine-readable analysis result."""

        return {
            "package": {
                "name": self.package,
                "old_version": self.old_version,
                "new_version": self.new_version,
            },
            "metadata_diff": self.metadata_diff.to_dict(),
            "capabilities": {
                "old": self.old_capabilities.to_dict(),
                "new": self.new_capabilities.to_dict(),
                "diff": self.capability_diff.to_dict(),
            },
            "assessment": self.assessment.to_dict(),
        }
