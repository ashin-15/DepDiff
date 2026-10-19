import unittest

from depdiff.metadata import parse_package_metadata
from depdiff.models import CapabilityFinding, CapabilitySet
from depdiff.capabilities import compare_capabilities
from depdiff.scoring import assess_upgrade
from depdiff.metadata import compare_metadata


class ScoringTests(unittest.TestCase):
    def finding(self, capability: str, severity: str) -> CapabilityFinding:
        return CapabilityFinding(
            capability=capability,
            rule_id=f"{capability}-rule",
            severity=severity,
            source_file="index.js",
            line=1,
            evidence=f"{capability}()",
            reason=f"review {capability}",
        )

    def metadata(self, scripts=None):
        return parse_package_metadata(
            {"name": "sample", "version": "1.0.0", "scripts": scripts or {}}
        )

    def test_high_risk_new_process_is_block_recommended(self):
        old = CapabilitySet(())
        new = CapabilitySet((self.finding("process", "HIGH"),))
        assessment = assess_upgrade(
            compare_metadata(self.metadata(), self.metadata()),
            compare_capabilities(old, new),
        )

        self.assertEqual(assessment.verdict, "block-recommended")
        self.assertEqual(assessment.severity, "HIGH")
        self.assertEqual(assessment.score, 3)

    def test_existing_high_risk_capability_is_not_realerted(self):
        finding = self.finding("process", "HIGH")
        diff = compare_capabilities(CapabilitySet((finding,)), CapabilitySet((finding,)))
        assessment = assess_upgrade(
            compare_metadata(self.metadata(), self.metadata()), diff
        )

        self.assertEqual(assessment.verdict, "ok")
        self.assertEqual(assessment.score, 0)

    def test_filesystem_and_network_combination_requires_review(self):
        diff = compare_capabilities(
            CapabilitySet(()),
            CapabilitySet(
                (
                    self.finding("fs", "LOW"),
                    self.finding("network", "LOW"),
                )
            ),
        )
        assessment = assess_upgrade(
            compare_metadata(self.metadata(), self.metadata()), diff
        )

        self.assertEqual(assessment.verdict, "review")
        self.assertEqual(assessment.score, 4)
        self.assertTrue(any("together" in reason for reason in assessment.reasons))

    def test_modified_lifecycle_script_requires_review(self):
        old = self.metadata({"postinstall": "node old.js"})
        new = self.metadata({"postinstall": "node new.js"})
        assessment = assess_upgrade(
            compare_metadata(old, new), compare_capabilities((), ())
        )

        self.assertEqual(assessment.verdict, "review")
        self.assertEqual(assessment.score, 2)
        self.assertIn("postinstall", assessment.reasons[0])
