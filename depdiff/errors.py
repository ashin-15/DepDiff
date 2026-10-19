"""Domain errors raised by depdiff's offline foundation."""


class DepdiffError(Exception):
    """Base class for expected depdiff errors."""


class FixtureError(DepdiffError):
    """Raised when an offline fixture cannot be safely loaded."""


class MetadataError(DepdiffError):
    """Raised when package.json is missing or malformed."""


class RuleError(DepdiffError):
    """Raised when an external capability rule file is invalid."""


class CapabilityError(DepdiffError):
    """Raised when a package cannot be statically scanned."""
