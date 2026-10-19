"""Package metadata parsing and version-to-version comparison."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .errors import MetadataError
from .models import (
    DEPENDENCY_SECTIONS,
    ENTRY_POINT_FIELDS,
    LIFECYCLE_SCRIPTS,
    MetadataChange,
    MetadataDiff,
    PackageMetadata,
)


def parse_package_metadata(document: Any, source: str = "package.json") -> PackageMetadata:
    """Validate a decoded package.json document and extract relevant fields."""

    if not isinstance(document, dict):
        raise MetadataError(f"{source} must contain a JSON object")

    name = _required_string(document, "name", source)
    version = _required_string(document, "version", source)

    scripts = _string_mapping(document.get("scripts", {}), "scripts", source)
    dependencies: dict[str, dict[str, str]] = {}
    for section in DEPENDENCY_SECTIONS:
        value = document.get(section, {})
        dependencies[section] = _string_mapping(value, section, source)

    entry_points: dict[str, Any] = {}
    for field in ENTRY_POINT_FIELDS:
        if field in document:
            entry_points[field] = _validate_entry_point(field, document[field], source)

    return PackageMetadata(
        name=name,
        version=version,
        scripts=scripts,
        dependencies=dependencies,
        entry_points=entry_points,
    )


def load_package_metadata(path: str) -> PackageMetadata:
    """Read and validate package metadata from a package.json path."""

    try:
        with open(path, encoding="utf-8") as metadata_file:
            document = json.load(metadata_file, parse_constant=_reject_json_constant)
    except OSError as exc:
        raise MetadataError(f"could not read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MetadataError(
            f"{path} is not valid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc

    return parse_package_metadata(document, source=path)


def compare_metadata(old: PackageMetadata, new: PackageMetadata) -> MetadataDiff:
    """Compare relevant package metadata without executing package code."""

    lifecycle_changes = _compare_lifecycle_scripts(old.scripts, new.scripts)
    dependency_changes = _compare_dependencies(old.dependencies, new.dependencies)
    entry_point_changes = _compare_mapping(
        "entry-point", old.entry_points, new.entry_points
    )
    return MetadataDiff(
        lifecycle_scripts=tuple(lifecycle_changes),
        dependencies=tuple(dependency_changes),
        entry_points=tuple(entry_point_changes),
    )


def _required_string(document: Mapping[str, Any], field: str, source: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MetadataError(f"{source} field '{field}' must be a non-empty string")
    return value


def _string_mapping(value: Any, field: str, source: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise MetadataError(f"{source} field '{field}' must be an object")

    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise MetadataError(f"{source} field '{field}' contains an invalid name")
        if not isinstance(item, str) or not item.strip():
            raise MetadataError(
                f"{source} field '{field}' dependency '{key}' must be a non-empty string"
            )
        result[key] = item
    return result


def _validate_entry_point(field: str, value: Any, source: str) -> Any:
    if field == "main":
        if not isinstance(value, str) or not value.strip():
            raise MetadataError(f"{source} field 'main' must be a non-empty string")
        return value

    if field == "bin":
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            return _string_mapping(value, "bin", source)
        raise MetadataError(
            f"{source} field 'bin' must be a non-empty string or object of strings"
        )

    _validate_exports_value(value, f"{source} field 'exports'")
    return value


def _validate_exports_value(value: Any, source: str) -> None:
    """Validate the JSON shapes used by npm exports without changing key order."""

    if value is None or isinstance(value, str):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_exports_value(item, f"{source}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise MetadataError(f"{source} contains an invalid export key")
            _validate_exports_value(item, f"{source}.{key}")
        return
    raise MetadataError(
        f"{source} must contain only strings, arrays, objects, or null values"
    )


def _compare_lifecycle_scripts(
    old_scripts: Mapping[str, str], new_scripts: Mapping[str, str]
) -> list[MetadataChange]:
    changes: list[MetadataChange] = []
    for script in LIFECYCLE_SCRIPTS:
        old_value = old_scripts.get(script)
        new_value = new_scripts.get(script)
        if old_value is None and new_value is not None:
            change = "added"
        elif old_value is not None and new_value is None:
            change = "removed"
        elif old_value != new_value:
            change = "modified"
        else:
            continue
        changes.append(
            MetadataChange(
                area="lifecycle-script",
                change=change,
                name=script,
                old_value=old_value,
                new_value=new_value,
            )
        )
    return changes


def _compare_dependencies(
    old_dependencies: Mapping[str, Mapping[str, str]],
    new_dependencies: Mapping[str, Mapping[str, str]],
) -> list[MetadataChange]:
    changes: list[MetadataChange] = []
    for section in DEPENDENCY_SECTIONS:
        old_section = old_dependencies.get(section, {})
        new_section = new_dependencies.get(section, {})
        for change in _compare_mapping(
            "dependency", old_section, new_section, name_prefix=f"{section}:"
        ):
            changes.append(change)
    return changes


def _compare_mapping(
    area: str,
    old_values: Mapping[str, Any],
    new_values: Mapping[str, Any],
    name_prefix: str = "",
) -> list[MetadataChange]:
    changes: list[MetadataChange] = []
    names = sorted(set(old_values) | set(new_values))
    for name in names:
        old_value = old_values.get(name)
        new_value = new_values.get(name)
        if name not in old_values:
            change = "added"
        elif name not in new_values:
            change = "removed"
        elif _canonical_value(old_value) != _canonical_value(new_value):
            change = "modified"
        else:
            continue
        changes.append(
            MetadataChange(
                area=area,
                change=change,
                name=f"{name_prefix}{name}",
                old_value=old_value,
                new_value=new_value,
            )
        )
    return changes


def _canonical_value(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _reject_json_constant(value: str) -> None:
    raise MetadataError(
        f"package metadata contains non-standard JSON constant {value!r}"
    )
