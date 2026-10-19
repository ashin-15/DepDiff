"""Safe loading of directory-based offline npm fixtures."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path, PurePosixPath

from .errors import FixtureError, MetadataError
from .metadata import load_package_metadata
from .models import PackageFixture


DEFAULT_MAX_METADATA_BYTES = 1_048_576
DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_TOTAL_BYTES = 50 * 1_024 * 1_024


class FixtureStore:
    """Resolve package versions from ``<root>/npm/<package>/<version>``.

    The loader only reads package.json and never imports or executes fixture code.
    Fixture paths are checked for traversal and symlink escapes before reading.
    """

    def __init__(
        self,
        fixtures_dir: str | Path,
        max_metadata_bytes: int = DEFAULT_MAX_METADATA_BYTES,
        max_files: int = DEFAULT_MAX_FILES,
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    ) -> None:
        base = Path(fixtures_dir).expanduser()
        if not base.exists():
            raise FixtureError(f"fixtures directory does not exist: {base}")
        if not base.is_dir():
            raise FixtureError(f"fixtures path is not a directory: {base}")
        if max_metadata_bytes <= 0 or max_files <= 0 or max_total_bytes <= 0:
            raise ValueError("fixture limits must be positive")
        self._base = base.resolve()
        self._max_metadata_bytes = max_metadata_bytes
        self._max_files = max_files
        self._max_total_bytes = max_total_bytes

    def load(self, package: str, version: str) -> PackageFixture:
        """Load and validate one package version from the fixture directory."""

        package_parts = _safe_package_parts(package)
        _safe_version(version)
        package_root = self._base / "npm" / Path(*package_parts) / version
        try:
            resolved_root = package_root.resolve()
        except (OSError, RuntimeError) as exc:
            raise FixtureError(f"could not resolve fixture path {package_root}: {exc}") from exc
        if not _is_within(resolved_root, self._base):
            raise FixtureError("fixture path escapes the fixtures directory")
        _reject_symlinks(package_root, self._base)
        if not resolved_root.is_dir():
            raise FixtureError(
                f"fixture not found for {package}@{version}: {package_root}"
            )
        validate_fixture_tree(
            resolved_root,
            max_files=self._max_files,
            max_total_bytes=self._max_total_bytes,
        )

        metadata_path = resolved_root / "package.json"
        if not metadata_path.is_file():
            raise FixtureError(f"fixture is missing package.json: {metadata_path}")
        if metadata_path.is_symlink():
            raise FixtureError(f"fixture package.json must not be a symlink: {metadata_path}")
        if metadata_path.stat().st_size > self._max_metadata_bytes:
            raise FixtureError(
                f"fixture package.json exceeds {self._max_metadata_bytes} bytes: {metadata_path}"
            )

        try:
            metadata = load_package_metadata(str(metadata_path))
        except MetadataError:
            raise
        if metadata.name != package:
            raise MetadataError(
                f"{metadata_path} field 'name' is '{metadata.name}', expected '{package}'"
            )
        if metadata.version != version:
            raise MetadataError(
                f"{metadata_path} field 'version' is '{metadata.version}', expected '{version}'"
            )

        return PackageFixture(
            package=package,
            version=version,
            root=str(resolved_root),
            metadata_path=str(metadata_path),
            metadata=metadata,
        )


def _safe_package_parts(package: str) -> tuple[str, ...]:
    if not isinstance(package, str) or not package.strip():
        raise FixtureError("package name must be a non-empty string")
    if "\\" in package:
        raise FixtureError("package name must use POSIX-style path-safe characters")
    path = PurePosixPath(package)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise FixtureError(f"unsafe package name: {package!r}")
    if len(path.parts) not in {1, 2}:
        raise FixtureError(f"unsupported package name: {package!r}")
    return path.parts


def _safe_version(version: str) -> None:
    if not isinstance(version, str) or not version.strip():
        raise FixtureError("package version must be a non-empty string")
    path = PurePosixPath(version)
    if (
        path.is_absolute()
        or len(path.parts) != 1
        or path.parts[0] in {"", ".", ".."}
        or "\\" in version
    ):
        raise FixtureError(f"unsafe package version: {version!r}")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _reject_symlinks(path: Path, base: Path) -> None:
    """Reject symlinks in the selected fixture path, even if they stay in-root."""

    try:
        relative_parts = path.relative_to(base).parts
    except ValueError as exc:
        raise FixtureError("fixture path is outside the fixtures directory") from exc

    current = base
    for part in relative_parts:
        current /= part
        if current.is_symlink():
            raise FixtureError(f"fixture path must not contain symlinks: {current}")


def validate_fixture_tree(
    root: str | Path,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> None:
    """Validate a directory fixture's file count, size, and link safety."""

    root_path = Path(root)
    if max_files <= 0 or max_total_bytes <= 0:
        raise ValueError("fixture limits must be positive")
    if not root_path.is_dir():
        raise FixtureError(f"fixture root is not a directory: {root_path}")

    file_count = 0
    total_bytes = 0
    for path in sorted(root_path.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise FixtureError(f"fixture tree must not contain symlinks: {path}")
        if not path.is_file():
            continue
        file_count += 1
        if file_count > max_files:
            raise FixtureError(f"fixture contains more than {max_files} files")
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise FixtureError(f"could not inspect fixture file {path}: {exc}") from exc
        total_bytes += size
        if total_bytes > max_total_bytes:
            raise FixtureError(
                f"fixture exceeds the {max_total_bytes} byte total size limit"
            )


def extract_safe_tarball(
    archive_path: str | Path,
    destination: str | Path,
    *,
    max_members: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> Path:
    """Extract a tar archive without allowing traversal, links, or special files.

    This helper is intentionally not an installation mechanism. It only
    materializes files for static inspection and rejects symlinks and hardlinks
    instead of attempting to reason about where they resolve.
    """

    archive = Path(archive_path)
    target = Path(destination)
    if max_members <= 0 or max_total_bytes <= 0:
        raise ValueError("archive limits must be positive")
    target.mkdir(parents=True, exist_ok=True)
    target_resolved = target.resolve()
    member_count = 0
    total_bytes = 0
    try:
        with tarfile.open(archive, mode="r:*") as tar:
            for member in tar:
                member_count += 1
                if member_count > max_members:
                    raise FixtureError(f"archive contains more than {max_members} members")
                member_path = _safe_archive_member(member.name, target_resolved)
                if member.issym() or member.islnk():
                    raise FixtureError(f"archive links are not allowed: {member.name}")
                if not (member.isdir() or member.isfile()):
                    raise FixtureError(f"archive special file is not allowed: {member.name}")
                if member.isfile():
                    total_bytes += member.size
                    if total_bytes > max_total_bytes:
                        raise FixtureError(
                            f"archive exceeds the {max_total_bytes} byte total size limit"
                        )
                member_path.parent.mkdir(parents=True, exist_ok=True)
                if member.isdir():
                    member_path.mkdir(parents=True, exist_ok=True)
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    raise FixtureError(f"could not read archive member: {member.name}")
                with member_path.open("wb") as output:
                    while True:
                        chunk = extracted.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
    except (OSError, tarfile.TarError) as exc:
        raise FixtureError(f"could not safely extract archive {archive}: {exc}") from exc
    return target


def _safe_archive_member(name: str, destination: Path) -> Path:
    if not name or "\\" in name:
        raise FixtureError(f"unsafe archive entry: {name!r}")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise FixtureError(f"archive entry escapes extraction directory: {name!r}")
    candidate = (destination / Path(*relative.parts)).resolve()
    if not _is_within(candidate, destination):
        raise FixtureError(f"archive entry escapes extraction directory: {name!r}")
    return candidate
