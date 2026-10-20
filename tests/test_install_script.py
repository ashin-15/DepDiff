"""Integration checks for the supported source-checkout installer."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = PROJECT_ROOT / "scripts" / "install.sh"


class InstallScriptTests(unittest.TestCase):
    def test_installs_and_reinstalls_user_command_from_relative_venv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            prefix = temporary_root / "prefix"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(temporary_root / "home"),
                    "PREFIX": str(prefix),
                    "PYTHON_BIN": sys.executable,
                    "VENV_DIR": "venv",
                }
            )

            for _ in range(2):
                result = subprocess.run(
                    [str(INSTALL_SCRIPT)],
                    cwd=temporary_root,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            command = prefix / "bin" / "depdiff"
            self.assertTrue(command.is_symlink())
            version = subprocess.run(
                [str(command), "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(version.stdout.strip(), "depdiff 0.1.0")


if __name__ == "__main__":
    unittest.main()
