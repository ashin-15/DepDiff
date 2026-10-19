import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from depdiff.analysis import analyze_upgrade
from depdiff.fixtures import FixtureStore
from depdiff.reporters import render_json, render_markdown, render_terminal
from depdiff.rules import load_default_rules
from scripts.build_showcase_data import build_data


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_showcase_data.py"
DATA = ROOT / "showcase" / "data" / "reports.json"
EXPECTED_SCENARIOS = (
    ("suspicious", "demo-package", "1.0.0", "2.0.0"),
    ("benign", "benign-package", "1.0.0", "1.1.0"),
    ("review", "demo-package", "2.0.0", "1.0.0"),
)


class ShowcaseDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checked_in_bytes = DATA.read_bytes()
        cls.payload = json.loads(cls.checked_in_bytes)

    def run_generator(self, *arguments, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_checked_in_data_matches_real_engine_and_reporters(self):
        self.assertEqual(set(self.payload), {"schema_version", "scenarios"})
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(
            [scenario["id"] for scenario in self.payload["scenarios"]],
            [scenario[0] for scenario in EXPECTED_SCENARIOS],
        )
        store = FixtureStore(ROOT / "fixtures")
        rules = load_default_rules()
        for scenario, expected in zip(self.payload["scenarios"], EXPECTED_SCENARIOS):
            scenario_id, package, old_version, new_version = expected
            with self.subTest(scenario=scenario_id):
                self.assertEqual(
                    set(scenario),
                    {"id", "label", "command", "report", "terminal", "markdown"},
                )
                self.assertIsInstance(scenario["label"], str)
                self.assertTrue(scenario["label"].strip())
                self.assertEqual(
                    scenario["command"],
                    f"python3 -m depdiff npm {package} {old_version} {new_version} "
                    "--fixtures-dir fixtures",
                )
                analysis = analyze_upgrade(
                    store.load(package, old_version),
                    store.load(package, new_version),
                    rules,
                )
                self.assertEqual(scenario["report"], json.loads(render_json(analysis)))
                self.assertEqual(scenario["terminal"], render_terminal(analysis))
                self.assertEqual(scenario["markdown"], render_markdown(analysis))
        self.assertEqual(build_data(), self.payload)
        self.assertNotIn(str(ROOT), self.checked_in_bytes.decode("utf-8"))

    def test_scenario_commands_reproduce_every_report_format(self):
        for scenario in self.payload["scenarios"]:
            for report_format, field in (
                ("terminal", "terminal"),
                ("json", "report"),
                ("markdown", "markdown"),
            ):
                with self.subTest(scenario=scenario["id"], format=report_format):
                    arguments = shlex.split(scenario["command"])
                    if report_format != "terminal":
                        arguments.extend(("--format", report_format))
                    result = subprocess.run(
                        arguments,
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    actual = (
                        json.loads(result.stdout)
                        if report_format == "json"
                        else result.stdout
                    )
                    self.assertEqual(actual, scenario[field])

    def test_real_verdicts_and_capability_removal_fallback(self):
        scenarios = {scenario["id"]: scenario for scenario in self.payload["scenarios"]}
        suspicious = scenarios["suspicious"]["report"]
        self.assertEqual(suspicious["assessment"]["verdict"], "block-recommended")
        self.assertEqual(suspicious["assessment"]["score"], 8)
        self.assertEqual(suspicious["assessment"]["severity"], "HIGH")
        self.assertEqual(
            [change["capability"] for change in suspicious["capabilities"]["diff"]["added"]],
            ["fs", "install-script", "process"],
        )
        benign = scenarios["benign"]["report"]
        self.assertEqual(benign["assessment"]["verdict"], "ok")
        self.assertEqual(benign["assessment"]["score"], 0)
        self.assertIsNone(benign["assessment"]["severity"])
        self.assertEqual(benign["metadata_diff"]["changes"], [])
        self.assertEqual(benign["capabilities"]["diff"]["changes"], [])

        # There is no versioned network/env review-only fixture in this checkout.
        # Do not invent a third verdict for the required "review" scenario ID.
        rollback = scenarios["review"]["report"]
        self.assertIn("Rollback", scenarios["review"]["label"])
        self.assertEqual(rollback["assessment"]["verdict"], "ok")
        self.assertEqual(rollback["assessment"]["score"], 0)
        self.assertEqual(rollback["capabilities"]["diff"]["added"], [])
        self.assertEqual(
            [change["capability"] for change in rollback["capabilities"]["diff"]["removed"]],
            ["fs", "install-script", "process"],
        )
        self.assertEqual(
            rollback["capabilities"]["old"], suspicious["capabilities"]["new"]
        )
        self.assertEqual(
            rollback["capabilities"]["new"], suspicious["capabilities"]["old"]
        )

    def test_generation_is_byte_deterministic_across_processes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            for seed in ("1", "8675309"):
                with self.subTest(hash_seed=seed):
                    output = Path(temporary_directory) / "generated data" / f"{seed}.json"
                    result = self.run_generator(
                        "--output",
                        output,
                        env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": ""},
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(output.read_bytes(), self.checked_in_bytes)

    def test_check_accepts_current_default_output_without_rewriting_it(self):
        before = DATA.stat().st_mtime_ns
        result = self.run_generator("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Showcase data is current: showcase/data/reports.json", result.stdout)
        self.assertEqual(DATA.read_bytes(), self.checked_in_bytes)
        self.assertEqual(DATA.stat().st_mtime_ns, before)

    def test_check_rejects_missing_output_without_creating_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "missing data" / "reports.json"
            result = self.run_generator("--check", "--output", output)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("Showcase data is missing", result.stderr)
            self.assertIn("python3 scripts/build_showcase_data.py", result.stderr)
            self.assertIn("--output", result.stderr)
            self.assertFalse(output.parent.exists())

    def test_check_rejects_stale_invalid_and_reformatted_output_without_writing(self):
        stale = json.loads(self.checked_in_bytes)
        stale["scenarios"][0]["report"]["assessment"]["score"] += 1
        cases = {
            "stale_report": json.dumps(stale).encode("utf-8"),
            "invalid_json": b"{invalid json\n",
            "extra_newline": self.checked_in_bytes + b"\n",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "reports.json"
            for name, content in cases.items():
                with self.subTest(case=name):
                    output.write_bytes(content)
                    before = output.stat().st_mtime_ns
                    result = self.run_generator("--check", "--output", output)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("Showcase data is stale", result.stderr)
                    self.assertIn("python3 scripts/build_showcase_data.py", result.stderr)
                    self.assertEqual(output.read_bytes(), content)
                    self.assertEqual(output.stat().st_mtime_ns, before)

    def test_generation_repairs_stale_output_then_check_passes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "reports.json"
            output.write_bytes(b"stale\n")
            result = self.run_generator("--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(output.read_bytes(), self.checked_in_bytes)
            checked = self.run_generator("--check", "--output", output)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(checked.stderr, "")
