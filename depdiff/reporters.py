"""Human and machine-readable renderers for completed analyses."""

from __future__ import annotations

import json

from .models import CapabilityChange, CapabilityFinding, MetadataChange, UpgradeAnalysis


def render_json(analysis: UpgradeAnalysis) -> str:
    """Render deterministic JSON suitable for automation."""

    return json.dumps(analysis.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n"


def render_terminal(analysis: UpgradeAnalysis) -> str:
    """Render a concise dependency upgrade review for a terminal."""

    lines = [
        "depdiff - behavioral dependency upgrade review",
        f"Package: {analysis.package}",
        f"Upgrade: {analysis.old_version} -> {analysis.new_version}",
        f"Verdict: {analysis.assessment.verdict}",
        f"Risk score: {analysis.assessment.score}",
        f"Highest new severity: {analysis.assessment.severity or 'none'}",
        "",
        "Capability changes:",
    ]
    lines.extend(_render_capability_change(change) for change in analysis.capability_diff.changes)
    if not analysis.capability_diff.changes:
        lines.append("- none detected")

    lines.extend(("", "Metadata changes:"))
    if analysis.metadata_diff.changes:
        for change in analysis.metadata_diff.changes:
            lines.append(_render_metadata_change(change))
    else:
        lines.append("- none")

    lines.extend(("", "New capability evidence:"))
    added_findings = tuple(
        finding
        for change in analysis.capability_diff.added
        for finding in change.new_findings
    )
    if added_findings:
        lines.extend(_render_finding(finding) for finding in added_findings)
    else:
        lines.append("- none")

    lines.extend(("", "Assessment:"))
    lines.extend(f"- {reason}" for reason in analysis.assessment.reasons)
    lines.append("")
    lines.append(
        "This is an explainable review recommendation, not proof of maliciousness or safety."
    )
    return "\n".join(lines) + "\n"


def render_markdown(analysis: UpgradeAnalysis) -> str:
    """Render a pull-request-friendly Markdown review."""

    assessment = analysis.assessment
    lines = [
        f"# depdiff review: `{analysis.package}` {analysis.old_version} -> {analysis.new_version}",
        "",
        f"**Verdict:** `{assessment.verdict}`<br>",
        f"**Risk score:** `{assessment.score}`<br>",
        f"**Highest new severity:** `{assessment.severity or 'none'}`",
        "",
        "> This is an explainable review recommendation, not proof of maliciousness or safety.",
        "",
        "## Capability changes",
        "",
        "| Capability | Status | Evidence count |",
        "| --- | --- | ---: |",
    ]
    if analysis.capability_diff.changes:
        for change in analysis.capability_diff.changes:
            lines.append(
                f"| `{change.capability}` | **{change.change}** | {len(change.findings)} |"
            )
    else:
        lines.append("| None detected | - | 0 |")

    lines.extend(("", "## Metadata changes", ""))
    if analysis.metadata_diff.changes:
        lines.extend(
            f"- **{change.change}** `{change.area}:{change.name}`"
            + _markdown_values(change)
            for change in analysis.metadata_diff.changes
        )
    else:
        lines.append("- None")

    lines.extend(("", "## New capability evidence", ""))
    findings = tuple(
        finding
        for change in analysis.capability_diff.added
        for finding in change.new_findings
    )
    if findings:
        lines.extend(
            "- **{severity}** `{capability}` via `{rule_id}` at `{source_file}:{line}` - "
            "{reason}\n\n  Evidence: `{evidence}`".format(**finding.to_dict())
            for finding in findings
        )
    else:
        lines.append("- None")

    lines.extend(("", "## Assessment", ""))
    lines.extend(f"- {reason}" for reason in assessment.reasons)
    lines.append("")
    return "\n".join(lines)


def _render_capability_change(change: CapabilityChange) -> str:
    return f"- {change.change}: {change.capability} ({len(change.findings)} finding(s))"


def _render_metadata_change(change: MetadataChange) -> str:
    values = []
    if change.old_value is not None:
        values.append(f"old={_display(change.old_value)}")
    if change.new_value is not None:
        values.append(f"new={_display(change.new_value)}")
    suffix = f" ({', '.join(values)})" if values else ""
    return f"- {change.change.upper()}: {change.area}:{change.name}{suffix}"


def _render_finding(finding: CapabilityFinding) -> str:
    return (
        f"- {finding.severity} {finding.capability} via {finding.rule_id} "
        f"at {finding.source_file}:{finding.line}: {finding.reason}\n"
        f"  evidence: {finding.evidence}"
    )


def _display(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _markdown_values(change: MetadataChange) -> str:
    values = []
    if change.old_value is not None:
        values.append(f"old `{_display(change.old_value)}`")
    if change.new_value is not None:
        values.append(f"new `{_display(change.new_value)}`")
    return f" ({'; '.join(values)})" if values else ""
