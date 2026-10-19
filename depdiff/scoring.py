"""Explainable, deterministic severity and verdict policy."""

from __future__ import annotations

from collections.abc import Iterable

from .models import CapabilityChange, CapabilityDiff, MetadataDiff, RiskAssessment


SEVERITY_WEIGHTS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
VERDICTS = ("ok", "review", "block-recommended")


def assess_upgrade(
    metadata_diff: MetadataDiff, capability_diff: CapabilityDiff
) -> RiskAssessment:
    """Score only newly introduced evidence and return a review recommendation.

    Existing capabilities are intentionally excluded from the score. Metadata
    lifecycle modifications remain visible and produce a review recommendation,
    while newly introduced high-risk capabilities are block-recommended.
    """

    added_changes = capability_diff.added
    added_findings = tuple(
        finding for change in added_changes for finding in change.new_findings
    )
    score = sum(SEVERITY_WEIGHTS.get(finding.severity, 0) for finding in added_findings)
    reasons: list[str] = []
    highest = _highest_severity(finding.severity for finding in added_findings)
    critical_capabilities = {
        change.capability
        for change in added_changes
        if change.capability in {"process", "dynamic-code", "install-script"}
    }

    for change in added_changes:
        reasons.append(
            f"Added {change.capability} capability with "
            f"{len(change.new_findings)} evidence finding(s)."
        )

    added_names = {change.capability for change in added_changes}
    if {"fs", "network"}.issubset(added_names):
        score += 2
        reasons.append(
            "Filesystem and network capabilities were introduced together, "
            "which increases review priority."
        )

    modified_lifecycle = tuple(
        change
        for change in metadata_diff.lifecycle_scripts
        if change.change == "modified"
    )
    if modified_lifecycle:
        score += 2
        names = ", ".join(change.name for change in modified_lifecycle)
        reasons.append(f"Existing lifecycle script behavior changed: {names}.")

    if critical_capabilities or highest == "HIGH":
        verdict = "block-recommended"
    elif added_findings or modified_lifecycle or {"fs", "network"}.issubset(added_names):
        verdict = "review"
    else:
        verdict = "ok"

    if not reasons and verdict == "ok":
        reasons.append("No new capability evidence or modified lifecycle scripts were found.")

    return RiskAssessment(
        score=score,
        severity=highest,
        verdict=verdict,
        reasons=tuple(reasons),
    )


def _highest_severity(severities: Iterable[str]) -> str | None:
    values = tuple(severities)
    if not values:
        return None
    return max(values, key=lambda severity: SEVERITY_ORDER.get(severity, 0))
