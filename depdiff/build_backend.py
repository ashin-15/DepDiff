"""Minimal offline PEP 517 backend for the standard-library-only MVP.

The backend exists so a clean virtualenv can install depdiff without fetching
setuptools or wheel. It intentionally implements only the wheel operations
needed by this project.
"""

from __future__ import annotations

import base64
import hashlib
import tomllib
import zipfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
    PROJECT = tomllib.load(project_file)["project"]

NAME = PROJECT["name"]
VERSION = PROJECT["version"]
DIST_INFO = f"{NAME}-{VERSION}.dist-info"


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    del config_settings
    dist_info = Path(metadata_directory) / DIST_INFO
    dist_info.mkdir(parents=True, exist_ok=True)
    _write_metadata_files(dist_info)
    return DIST_INFO


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    del config_settings, metadata_directory
    wheel_name = f"{NAME}-{VERSION}-py3-none-any.whl"
    wheel_path = Path(wheel_directory) / wheel_name
    records: list[tuple[str, bytes]] = []

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for source_path in sorted((PROJECT_ROOT / NAME).rglob("*.py")):
            if "__pycache__" in source_path.parts:
                continue
            archive_path = source_path.relative_to(PROJECT_ROOT).as_posix()
            content = source_path.read_bytes()
            _write_zip_entry(wheel, archive_path, content)
            records.append((archive_path, content))

        for source_path in sorted((PROJECT_ROOT / "rules").glob("*.yaml")):
            archive_path = source_path.relative_to(PROJECT_ROOT).as_posix()
            content = source_path.read_bytes()
            _write_zip_entry(wheel, archive_path, content)
            records.append((archive_path, content))

        metadata_files = _metadata_files()
        for filename, content in metadata_files.items():
            archive_path = f"{DIST_INFO}/{filename}"
            _write_zip_entry(wheel, archive_path, content)
            records.append((archive_path, content))

        record_path = f"{DIST_INFO}/RECORD"
        record_lines = [
            f"{path},{_record_hash(content)},{len(content)}" for path, content in records
        ]
        record_lines.append(f"{record_path},,")
        record_content = ("\n".join(record_lines) + "\n").encode("utf-8")
        _write_zip_entry(wheel, record_path, record_content)

    return wheel_name


def _metadata_files() -> dict[str, bytes]:
    authors = PROJECT.get("authors", [])
    author = authors[0].get("name") if authors else None
    readme_name = PROJECT.get("readme", "README.md")
    readme = (PROJECT_ROOT / readme_name).read_text(encoding="utf-8")
    license_config = PROJECT.get("license", {})
    license_name = license_config.get("text", "") if isinstance(license_config, dict) else ""
    author_line = f"Author: {author}\n" if author else ""
    license_line = f"License: {license_name}\n" if license_name else ""
    return {
        "METADATA": (
            "Metadata-Version: 2.1\n"
            f"Name: {NAME}\n"
            f"Version: {VERSION}\n"
            f"Summary: {PROJECT['description']}\n"
            f"Requires-Python: {PROJECT['requires-python']}\n"
            f"{author_line}"
            f"{license_line}"
            "Description-Content-Type: text/markdown\n"
            "\n"
            f"{readme}\n"
        ).encode("utf-8"),
        "WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: depdiff.build_backend\n"
            "Root-Is-Purelib: true\n"
            "Tag: py3-none-any\n"
            "\n"
        ).encode("utf-8"),
        "entry_points.txt": b"[console_scripts]\ndepdiff = depdiff.cli:main\n",
    }


def _write_metadata_files(dist_info: Path) -> None:
    for filename, content in _metadata_files().items():
        (dist_info / filename).write_bytes(content)


def _record_hash(content: bytes) -> str:
    digest = hashlib.sha256(content).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _write_zip_entry(wheel: zipfile.ZipFile, path: str, content: bytes) -> None:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    wheel.writestr(info, content)
