import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from depdiff import build_backend


class BuildBackendTests(unittest.TestCase):
    def test_repeated_wheel_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first_directory = root / "first"
            second_directory = root / "second"
            first_directory.mkdir()
            second_directory.mkdir()
            first_name = build_backend.build_wheel(str(first_directory))
            second_name = build_backend.build_wheel(str(second_directory))
            first_hash = hashlib.sha256(
                (first_directory / first_name).read_bytes()
            ).hexdigest()
            second_hash = hashlib.sha256(
                (second_directory / second_name).read_bytes()
            ).hexdigest()
            self.assertEqual(first_name, second_name)
            self.assertEqual(first_hash, second_hash)

    def test_wheel_contains_external_default_rules(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            wheel_name = build_backend.build_wheel(temporary_directory)
            with zipfile.ZipFile(Path(temporary_directory) / wheel_name) as wheel:
                self.assertIn("rules/default.yaml", wheel.namelist())
