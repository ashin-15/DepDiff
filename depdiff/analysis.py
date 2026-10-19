"""Orchestration for a complete offline dependency upgrade analysis."""

from __future__ import annotations

from .capabilities import compare_capabilities, scan_package
from .metadata import compare_metadata
from .models import PackageFixture, RuleSet, UpgradeAnalysis
from .scoring import assess_upgrade


def analyze_upgrade(
    old_fixture: PackageFixture, new_fixture: PackageFixture, rules: RuleSet
) -> UpgradeAnalysis:
    """Analyze metadata and static capabilities without executing package code."""

    metadata_diff = compare_metadata(old_fixture.metadata, new_fixture.metadata)
    old_capabilities = scan_package(old_fixture, rules)
    new_capabilities = scan_package(new_fixture, rules)
    capability_diff = compare_capabilities(old_capabilities, new_capabilities)
    assessment = assess_upgrade(metadata_diff, capability_diff)
    return UpgradeAnalysis(
        package=old_fixture.package,
        old_version=old_fixture.version,
        new_version=new_fixture.version,
        metadata_diff=metadata_diff,
        old_capabilities=old_capabilities,
        new_capabilities=new_capabilities,
        capability_diff=capability_diff,
        assessment=assessment,
    )
