import json
import tempfile
import unittest
from pathlib import Path

from depdiff.capabilities import compare_capabilities, scan_javascript, scan_package
from depdiff.models import CapabilityFinding, CapabilitySet
from depdiff.rules import load_default_rules, load_rules


FIXTURES = Path(__file__).parents[1] / "fixtures"
JAVASCRIPT_FIXTURES = FIXTURES / "javascript"


class JavaScriptScannerTests(unittest.TestCase):
    def setUp(self):
        self.rules = load_default_rules()

    def test_detects_all_javascript_capabilities_with_evidence(self):
        result = scan_javascript(JAVASCRIPT_FIXTURES, self.rules)

        self.assertEqual(
            set(result.capabilities),
            {"network", "fs", "process", "env", "dynamic-code", "crypto"},
        )
        self.assertEqual(
            {finding.rule_id for finding in result.findings},
            {
                "network-fetch",
                "network-node-client",
                "fs-file-operation",
                "process-child-process",
                "env-process",
                "dynamic-code-evaluation",
                "dynamic-code-vm",
                "crypto-node-api",
            },
        )
        for finding in result.findings:
            self.assertEqual(finding.source_file, "positive.js")
            self.assertGreaterEqual(finding.line, 1)
            self.assertTrue(finding.evidence)
            self.assertTrue(finding.reason)

    def test_negative_fixture_has_no_capability_findings(self):
        result = scan_javascript(JAVASCRIPT_FIXTURES / "negative", self.rules)

        self.assertEqual(result.findings, ())

    def test_custom_rule_is_detected_without_scanner_code_changes(self):
        document = """\
version: 1
rules:
  - id: custom-marker
    capability: custom
    severity: LOW
    pattern: 'MARKER'
    description: 'Finds a project-specific marker.'
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.js").write_text("const value = MARKER;\n", encoding="utf-8")
            rules_path = root / "rules.yaml"
            rules_path.write_text(document, encoding="utf-8")

            result = scan_javascript(root, load_rules(rules_path))

        self.assertEqual(result.capabilities, ("custom",))
        self.assertEqual(result.findings[0].rule_id, "custom-marker")

    def test_scans_metadata_lifecycle_scripts_without_executing_them(self):
        package_root = JAVASCRIPT_FIXTURES / "metadata-package"

        result = scan_package(package_root, self.rules)

        self.assertEqual(result.capabilities, ("install-script",))
        finding = result.findings[0]
        self.assertEqual(finding.source_file, "package.json")
        self.assertEqual(finding.line, 5)
        self.assertIn("node setup.js", finding.evidence)

    def test_benign_package_has_no_install_script_capability(self):
        package_root = FIXTURES / "npm" / "benign-package" / "1.0.0"

        result = scan_package(package_root, self.rules)

        self.assertEqual(result.findings, ())

    def test_finding_order_is_stable_across_repeated_scans(self):
        first = scan_javascript(JAVASCRIPT_FIXTURES, self.rules).to_dict()
        second = scan_javascript(JAVASCRIPT_FIXTURES, self.rules).to_dict()

        self.assertEqual(first, second)
        self.assertEqual(
            first["findings"],
            sorted(
                first["findings"],
                key=lambda item: (
                    item["capability"],
                    item["source_file"],
                    item["line"],
                    item["rule_id"],
                    item["severity"],
                    item["evidence"],
                    item["reason"],
                ),
            ),
        )


class CapabilityDiffTests(unittest.TestCase):
    def finding(self, capability: str, source_file: str) -> CapabilityFinding:
        return CapabilityFinding(
            capability=capability,
            rule_id=f"{capability}-rule",
            severity="MEDIUM",
            source_file=source_file,
            line=1,
            evidence=f"{capability}()",
            reason=f"review {capability}",
        )

    def test_classifies_added_removed_and_unchanged_categories(self):
        old = CapabilitySet(
            (
                self.finding("network", "old.js"),
                self.finding("fs", "old.js"),
            )
        )
        new = CapabilitySet(
            (
                self.finding("process", "new.js"),
                self.finding("network", "new.js"),
            )
        )

        diff = compare_capabilities(old, new)

        self.assertEqual(
            [(item.capability, item.change) for item in diff.changes],
            [("fs", "REMOVED"), ("network", "UNCHANGED"), ("process", "ADDED")],
        )
        self.assertEqual(diff.removed[0].findings[0].source_file, "old.js")
        self.assertEqual(diff.added[0].findings[0].source_file, "new.js")
        self.assertEqual(diff.unchanged[0].old_findings[0].source_file, "old.js")
        self.assertEqual(diff.unchanged[0].new_findings[0].source_file, "new.js")

    def test_diff_serialization_retains_source_evidence_and_is_json_safe(self):
        finding = self.finding("network", "index.js")

        payload = compare_capabilities((), (finding,)).to_dict()

        self.assertEqual(payload["added"][0]["findings"][0]["source_file"], "index.js")
        self.assertEqual(payload["added"][0]["findings"][0]["line"], 1)
        self.assertEqual(payload["added"][0]["findings"][0]["evidence"], "network()")
        self.assertEqual(payload["added"][0]["findings"][0]["reason"], "review network")
        json.dumps(payload, sort_keys=True)
