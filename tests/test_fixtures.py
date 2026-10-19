import json
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from depdiff.errors import FixtureError, MetadataError
from depdiff.fixtures import FixtureStore, extract_safe_tarball


FIXTURES = Path(__file__).parents[1] / "fixtures"


class FixtureStoreTests(unittest.TestCase):
    def test_loads_expected_offline_fixture(self):
        fixture = FixtureStore(FIXTURES).load("demo-package", "1.0.0")
        self.assertEqual(fixture.metadata.name, "demo-package")
        self.assertEqual(fixture.metadata.version, "1.0.0")
        self.assertTrue(fixture.metadata_path.endswith("package.json"))

    def test_rejects_path_traversal(self):
        with self.assertRaises(FixtureError):
            FixtureStore(FIXTURES).load("../demo-package", "1.0.0")
        with self.assertRaises(FixtureError):
            FixtureStore(FIXTURES).load("demo-package", "../1.0.0")

    def test_rejects_missing_fixture(self):
        with self.assertRaisesRegex(FixtureError, "fixture not found"):
            FixtureStore(FIXTURES).load("demo-package", "9.9.9")

    def test_rejects_metadata_name_or_version_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "npm" / "sample" / "1.0.0"
            root.mkdir(parents=True)
            (root / "package.json").write_text(
                json.dumps({"name": "different", "version": "1.0.0"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MetadataError, "expected 'sample'"):
                FixtureStore(temporary_directory).load("sample", "1.0.0")

    def test_rejects_non_standard_json_constants(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "npm" / "sample" / "1.0.0"
            root.mkdir(parents=True)
            (root / "package.json").write_text(
                '{"name": "sample", "version": "1.0.0", "exports": NaN}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MetadataError, "non-standard JSON"):
                FixtureStore(temporary_directory).load("sample", "1.0.0")

    def test_rejects_symlinked_fixture_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            outside = root / "outside"
            outside.mkdir()
            (outside / "package.json").write_text(
                json.dumps({"name": "sample", "version": "1.0.0"}),
                encoding="utf-8",
            )
            npm = root / "npm"
            npm.mkdir()
            (npm / "sample").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(FixtureError, "symlink"):
                FixtureStore(root).load("sample", "1.0.0")

    def test_rejects_symlink_loops_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            package_root = Path(temporary_directory) / "npm" / "sample"
            package_root.mkdir(parents=True)
            loop = package_root / "1.0.0"
            loop.symlink_to(loop, target_is_directory=True)
            with self.assertRaisesRegex(FixtureError, "could not resolve fixture path"):
                FixtureStore(temporary_directory).load("sample", "1.0.0")

    def test_safe_archive_extraction_rejects_traversal_and_links(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            traversal = root / "traversal.tgz"
            with tarfile.open(traversal, "w:gz") as archive:
                member = tarfile.TarInfo("../escape.txt")
                member.size = 4
                archive.addfile(member, io.BytesIO(b"nope"))
            with self.assertRaisesRegex(FixtureError, "escapes"):
                extract_safe_tarball(traversal, root / "out")

            link_archive = root / "link.tgz"
            with tarfile.open(link_archive, "w:gz") as archive:
                member = tarfile.TarInfo("package.json")
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
                archive.addfile(member)
            with self.assertRaisesRegex(FixtureError, "links"):
                extract_safe_tarball(link_archive, root / "link-out")

    def test_safe_archive_extraction_enforces_size_limit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archive_path = root / "large.tgz"
            with tarfile.open(archive_path, "w:gz") as archive:
                member = tarfile.TarInfo("package.json")
                member.size = 4
                archive.addfile(member, io.BytesIO(b"data"))
            with self.assertRaisesRegex(FixtureError, "total size limit"):
                extract_safe_tarball(
                    archive_path, root / "out", max_total_bytes=3
                )
