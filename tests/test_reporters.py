import json
import unittest
from pathlib import Path

from depdiff.analysis import analyze_upgrade
from depdiff.fixtures import FixtureStore
from depdiff.reporters import render_json, render_markdown, render_terminal
from depdiff.rules import load_default_rules


FIXTURES = Path(__file__).parents[1] / "fixtures"


class ReporterTests(unittest.TestCase):
    def setUp(self):
        store = FixtureStore(FIXTURES)
        self.analysis = analyze_upgrade(
            store.load("demo-package", "1.0.0"),
            store.load("demo-package", "2.0.0"),
            load_default_rules(),
        )

    def test_json_report_is_deterministic_and_complete(self):
        first = render_json(self.analysis)
        second = render_json(self.analysis)
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertEqual(payload["package"]["name"], "demo-package")
        self.assertEqual(payload["assessment"]["verdict"], "block-recommended")
        self.assertEqual(
            payload["capabilities"]["diff"]["added"][0]["findings"][0]["source_file"],
            "lib/index.js",
        )

    def test_terminal_report_contains_review_evidence(self):
        report = render_terminal(self.analysis)
        self.assertIn("Verdict: block-recommended", report)
        self.assertIn("process-child-process", report)
        self.assertIn("lib/index.js:6", report)
        self.assertIn("postinstall", report)

    def test_markdown_report_is_pull_request_friendly(self):
        report = render_markdown(self.analysis)
        self.assertIn("# depdiff review", report)
        self.assertIn("| `process` | **ADDED** |", report)
        self.assertIn("`lib/index.js:6`", report)
        self.assertIn("block-recommended", report)
