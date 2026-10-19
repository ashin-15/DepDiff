import tempfile
import unittest
from pathlib import Path

from depdiff.errors import RuleError
from depdiff.rules import load_default_rules, load_rules


class RuleLoaderTests(unittest.TestCase):
    def test_default_rules_cover_every_phase_two_category(self):
        rules = load_default_rules()

        self.assertEqual(
            {rule.capability for rule in rules},
            {
                "network",
                "fs",
                "process",
                "env",
                "dynamic-code",
                "crypto",
                "install-script",
            },
        )
        self.assertEqual(
            [rule.id for rule in rules], sorted(rule.id for rule in rules)
        )
        self.assertTrue(all(rule.reason for rule in rules))

    def test_loads_documented_yaml_subset_and_compiles_patterns(self):
        document = """\
version: 1
rules:
  - id: custom-network
    capability: network
    severity: medium
    pattern: '\\brequest\\s*\\('
    description: 'Finds a custom request call.'
    source: javascript
    flags: i
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.yaml"
            path.write_text(document, encoding="utf-8")

            rules = load_rules(path)

        self.assertEqual(len(rules), 1)
        rule = rules.rules[0]
        self.assertEqual(rule.severity, "MEDIUM")
        self.assertEqual(rule.reason, rule.description)
        self.assertEqual(rule.flags, "i")

    def test_rejects_invalid_rule_schema_and_regex(self):
        invalid_documents = (
            (
                "version: 1\nrules:\n  - id: duplicate\n    capability: fs\n"
                "    severity: LOW\n    pattern: '['\n    description: broken\n",
                "not valid regex",
            ),
            (
                "version: 1\nrules:\n  - id: one\n    capability: fs\n"
                "    severity: LOW\n    pattern: x\n    description: ok\n"
                "  - id: one\n    capability: fs\n    severity: LOW\n"
                "    pattern: y\n    description: duplicate\n",
                "duplicate rule id",
            ),
            (
                "version: 1\nrules:\n  - id: one\n    capability: fs\n"
                "    severity: LOW\n    pattern: x\n    description: ok\n"
                "    unexpected: value\n",
                "unsupported field",
            ),
        )
        for document, message in invalid_documents:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.yaml"
                path.write_text(document, encoding="utf-8")
                with self.assertRaisesRegex(RuleError, message):
                    load_rules(path)

    def test_rejects_missing_rule_file(self):
        with self.assertRaisesRegex(RuleError, "could not read rules file"):
            load_rules("does-not-exist.yaml")
