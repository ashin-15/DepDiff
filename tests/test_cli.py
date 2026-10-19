import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from depdiff.cli import main


FIXTURES = Path(__file__).parents[1] / "fixtures"


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main([*arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_suspicious_metadata_fixture_is_explained(self):
        code, stdout, stderr = self.run_cli(
            "npm",
            "demo-package",
            "1.0.0",
            "2.0.0",
            "--fixtures-dir",
            str(FIXTURES),
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("postinstall", stdout)
        self.assertIn("dependencies:left-pad", stdout)
        self.assertIn("main", stdout)
        self.assertIn("Verdict: block-recommended", stdout)
        self.assertIn("process-child-process", stdout)
        self.assertIn("lib/index.js:6", stdout)

    def test_benign_metadata_fixture_reports_unchanged(self):
        code, stdout, stderr = self.run_cli(
            "npm",
            "benign-package",
            "1.0.0",
            "1.1.0",
            "--fixtures-dir",
            str(FIXTURES),
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Verdict: ok", stdout)
        self.assertIn("No new capability evidence", stdout)

    def test_json_output_is_machine_readable_and_stable(self):
        arguments = (
            "npm",
            "demo-package",
            "1.0.0",
            "2.0.0",
            "--fixtures-dir",
            str(FIXTURES),
            "--format",
            "json",
        )
        first = self.run_cli(*arguments)
        second = self.run_cli(*arguments)
        self.assertEqual(first[0], 0)
        self.assertEqual(first[1], second[1])
        payload = json.loads(first[1])
        self.assertEqual(len(payload["metadata_diff"]["changes"]), 6)
        self.assertEqual(payload["assessment"]["verdict"], "block-recommended")
        self.assertEqual(
            [item["capability"] for item in payload["capabilities"]["diff"]["added"]],
            ["fs", "install-script", "process"],
        )

    def test_invalid_fixture_returns_execution_error(self):
        code, stdout, stderr = self.run_cli(
            "npm",
            "../unsafe",
            "1.0.0",
            "2.0.0",
            "--fixtures-dir",
            str(FIXTURES),
        )
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("unsafe package name", stderr)

    def test_output_file_receives_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "nested" / "report.txt"
            code, stdout, stderr = self.run_cli(
                "npm",
                "benign-package",
                "1.0.0",
                "1.1.0",
                "--fixtures-dir",
                str(FIXTURES),
                "--output",
                str(output_path),
            )
            self.assertEqual(code, 0)
            self.assertEqual(stdout, "")
            self.assertEqual(stderr, "")
            self.assertIn("Verdict: ok", output_path.read_text())
