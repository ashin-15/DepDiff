import unittest

from depdiff.errors import MetadataError
from depdiff.metadata import compare_metadata, parse_package_metadata


class MetadataParsingTests(unittest.TestCase):
    def test_parses_relevant_package_json_fields(self):
        metadata = parse_package_metadata(
            {
                "name": "sample",
                "version": "1.0.0",
                "scripts": {"postinstall": "node setup.js", "test": "node test.js"},
                "dependencies": {"a": "^1.0.0"},
                "optionalDependencies": {"b": "^2.0.0"},
                "main": "index.js",
                "bin": {"sample": "cli.js"},
                "exports": {".": "./index.js"},
            }
        )

        self.assertEqual(metadata.name, "sample")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.scripts["postinstall"], "node setup.js")
        self.assertEqual(metadata.dependencies["optionalDependencies"]["b"], "^2.0.0")
        self.assertEqual(metadata.entry_points["bin"], {"sample": "cli.js"})

    def test_rejects_missing_required_fields(self):
        with self.assertRaisesRegex(MetadataError, "name"):
            parse_package_metadata({"version": "1.0.0"})

    def test_rejects_non_string_dependency_specifications(self):
        with self.assertRaisesRegex(MetadataError, "dependency 'a'"):
            parse_package_metadata(
                {
                    "name": "sample",
                    "version": "1.0.0",
                    "dependencies": {"a": {"version": "1.0.0"}},
                }
            )

    def test_validates_supported_entry_point_shapes(self):
        with self.assertRaisesRegex(MetadataError, "field 'main'"):
            parse_package_metadata(
                {"name": "sample", "version": "1.0.0", "main": ["index.js"]}
            )
        with self.assertRaisesRegex(MetadataError, "field 'bin'"):
            parse_package_metadata(
                {"name": "sample", "version": "1.0.0", "bin": {"sample": 7}}
            )
        with self.assertRaisesRegex(MetadataError, "field 'exports'"):
            parse_package_metadata(
                {"name": "sample", "version": "1.0.0", "exports": False}
            )


class MetadataComparisonTests(unittest.TestCase):
    def setUp(self):
        self.old = parse_package_metadata(
            {
                "name": "sample",
                "version": "1.0.0",
                "scripts": {
                    "preinstall": "node before.js",
                    "install": "node install.js",
                    "postinstall": "node old.js",
                },
                "dependencies": {"same": "^1.0.0", "removed": "^2.0.0"},
                "main": "index.js",
            }
        )
        self.new = parse_package_metadata(
            {
                "name": "sample",
                "version": "2.0.0",
                "scripts": {
                    "preinstall": "node before.js",
                    "install": "node install-v2.js",
                    "postinstall": "node new.js",
                },
                "dependencies": {
                    "same": "^1.0.0",
                    "added": "^3.0.0",
                },
                "main": "lib/index.js",
                "exports": {".": "./lib/index.js"},
            }
        )

    def test_detects_lifecycle_add_remove_and_modify(self):
        old_without_postinstall = parse_package_metadata(
            {"name": "sample", "version": "1.0.0", "scripts": {}}
        )
        new_with_postinstall = parse_package_metadata(
            {
                "name": "sample",
                "version": "2.0.0",
                "scripts": {"postinstall": "node setup.js"},
            }
        )
        added = compare_metadata(old_without_postinstall, new_with_postinstall)
        self.assertEqual(
            [(item.name, item.change) for item in added.lifecycle_scripts],
            [("postinstall", "added")],
        )

        removed = compare_metadata(new_with_postinstall, old_without_postinstall)
        self.assertEqual(
            [(item.name, item.change) for item in removed.lifecycle_scripts],
            [("postinstall", "removed")],
        )

        changed = compare_metadata(self.old, self.new)
        lifecycle = {item.name: item.change for item in changed.lifecycle_scripts}
        self.assertEqual(lifecycle, {"install": "modified", "postinstall": "modified"})

    def test_detects_dependency_and_entry_point_changes(self):
        diff = compare_metadata(self.old, self.new)
        dependency_changes = {
            (item.name, item.change) for item in diff.dependencies
        }
        self.assertEqual(
            dependency_changes,
            {
                ("dependencies:added", "added"),
                ("dependencies:removed", "removed"),
            },
        )
        entry_changes = {(item.name, item.change) for item in diff.entry_points}
        self.assertEqual(
            entry_changes,
            {
                ("main", "modified"),
                ("exports", "added"),
            },
        )

    def test_unchanged_metadata_has_no_changes(self):
        diff = compare_metadata(self.old, self.old)
        self.assertTrue(diff.is_empty)
        self.assertEqual(diff.to_dict()["changes"], [])

    def test_preserves_exports_condition_order_changes(self):
        old = parse_package_metadata(
            {
                "name": "sample",
                "version": "1.0.0",
                "exports": {"import": "./esm.js", "require": "./cjs.js"},
            }
        )
        new = parse_package_metadata(
            {
                "name": "sample",
                "version": "2.0.0",
                "exports": {"require": "./cjs.js", "import": "./esm.js"},
            }
        )
        diff = compare_metadata(old, new)
        self.assertEqual(
            [(item.name, item.change) for item in diff.entry_points],
            [("exports", "modified")],
        )
