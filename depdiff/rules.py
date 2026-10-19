"""External YAML capability rule loading.

The project intentionally does not depend on a YAML package.  The loader
implements the small, documented YAML subset used by the shipped rules rather
than silently treating a rule file as Python or JSON.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import RuleError
from .models import RULE_SOURCES, SEVERITIES, Rule, RuleSet


DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "default.yaml"
_RULE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_ALLOWED_FIELDS = {
    "id",
    "capability",
    "severity",
    "pattern",
    "description",
    "reason",
    "source",
    "flags",
}
_ALLOWED_DOCUMENT_FIELDS = {"version", "rules"}


@dataclass(frozen=True)
class _YamlLine:
    number: int
    indent: int
    text: str


def load_rules(path: str | Path) -> RuleSet:
    """Load and validate capability rules from a supported YAML file.

    The returned rules are sorted by rule ID.  Parsing and regular-expression
    validation happen before any scanner consumes the rules, so malformed
    configuration fails with a useful ``RuleError``.
    """

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuleError(f"could not read rules file {source}: {exc}") from exc

    document = _parse_yaml_subset(text, source)
    if not isinstance(document, dict):
        raise RuleError(f"{source} must contain a YAML mapping at the document root")
    unknown_document_fields = sorted(set(document) - _ALLOWED_DOCUMENT_FIELDS)
    if unknown_document_fields:
        raise RuleError(
            f"{source} contains unsupported document field(s): "
            f"{', '.join(unknown_document_fields)}"
        )
    _validate_document_version(document, source)
    raw_rules = document.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise RuleError(f"{source} field 'rules' must be a non-empty YAML list")

    rules: list[Rule] = []
    identifiers: set[str] = set()
    for index, raw_rule in enumerate(raw_rules, start=1):
        location = f"{source} rule {index}"
        if not isinstance(raw_rule, dict):
            raise RuleError(f"{location} must be a mapping")
        unknown = sorted(set(raw_rule) - _ALLOWED_FIELDS)
        if unknown:
            raise RuleError(f"{location} contains unsupported field(s): {', '.join(unknown)}")
        rule_id = _required_string(raw_rule, "id", location)
        if not _RULE_ID.fullmatch(rule_id):
            raise RuleError(
                f"{location} field 'id' must start with a letter and contain only "
                "letters, numbers, '.', '_' or '-'"
            )
        if rule_id in identifiers:
            raise RuleError(f"duplicate rule id {rule_id!r} in {source}")
        identifiers.add(rule_id)

        capability = _required_string(raw_rule, "capability", location)
        severity = _required_string(raw_rule, "severity", location).upper()
        if severity not in SEVERITIES:
            raise RuleError(
                f"{location} field 'severity' must be one of {', '.join(SEVERITIES)}"
            )
        pattern = _required_string(raw_rule, "pattern", location)
        description = _required_string(raw_rule, "description", location)
        reason = raw_rule.get("reason", description)
        if not isinstance(reason, str) or not reason.strip():
            raise RuleError(f"{location} field 'reason' must be a non-empty string")

        source_kind = raw_rule.get("source", "javascript")
        if not isinstance(source_kind, str) or source_kind.lower() not in RULE_SOURCES:
            raise RuleError(
                f"{location} field 'source' must be one of {', '.join(RULE_SOURCES)}"
            )
        source_kind = source_kind.lower()

        flags = raw_rule.get("flags", "")
        if not isinstance(flags, str):
            raise RuleError(f"{location} field 'flags' must be a string")
        _compile_pattern(pattern, flags, location)
        rules.append(
            Rule(
                id=rule_id,
                capability=capability,
                severity=severity,
                pattern=pattern,
                description=description,
                reason=reason.strip(),
                source=source_kind,
                flags=flags,
            )
        )

    return RuleSet(tuple(rules))


def load_default_rules() -> RuleSet:
    """Load the repository's shipped default rules."""

    return load_rules(DEFAULT_RULES_PATH)


def compile_rule(rule: Rule) -> re.Pattern[str]:
    """Compile one already validated rule for scanner use."""

    return _compile_pattern(rule.pattern, rule.flags, f"rule {rule.id}")


def _validate_document_version(document: dict[str, Any], source: Path) -> None:
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise RuleError(f"{source} field 'version' must be the integer 1")


def _required_string(document: dict[str, Any], field: str, location: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RuleError(f"{location} field '{field}' must be a non-empty string")
    return value.strip()


def _compile_pattern(pattern: str, flags: str, location: str) -> re.Pattern[str]:
    flag_value = 0
    supported_flags = {
        "i": re.IGNORECASE,
        "m": re.MULTILINE,
        "s": re.DOTALL,
    }
    for flag in flags:
        if flag not in supported_flags:
            raise RuleError(
                f"{location} field 'flags' contains unsupported flag {flag!r}; "
                "supported flags are i, m, and s"
            )
        flag_value |= supported_flags[flag]
    try:
        return re.compile(pattern, flag_value)
    except re.error as exc:
        raise RuleError(f"{location} field 'pattern' is not valid regex: {exc}") from exc


def _parse_yaml_subset(text: str, source: Path) -> Any:
    lines: list[_YamlLine] = []
    for number, raw_line in enumerate(text.splitlines(), start=1):
        if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
            raise RuleError(f"{source}:{number}: tabs are not supported for indentation")
        without_comment = _strip_comment(raw_line).rstrip()
        if not without_comment.strip():
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        lines.append(_YamlLine(number, indent, without_comment[indent:]))

    if not lines:
        raise RuleError(f"{source} is empty")
    if lines[0].indent != 0:
        raise RuleError(f"{source}:{lines[0].number}: document must start at column 1")
    value, index = _parse_block(lines, 0, 0, source)
    if index != len(lines):
        line = lines[index]
        raise RuleError(f"{source}:{line.number}: unexpected YAML content")
    return value


def _parse_block(
    lines: list[_YamlLine], index: int, indent: int, source: Path
) -> tuple[Any, int]:
    if index >= len(lines):
        raise RuleError(f"{source}: expected a YAML value")
    line = lines[index]
    if line.indent != indent:
        raise RuleError(f"{source}:{line.number}: invalid indentation")
    if line.text.startswith("-") and (len(line.text) == 1 or line.text[1].isspace()):
        return _parse_sequence(lines, index, indent, source)
    return _parse_mapping(lines, index, indent, source)


def _parse_mapping(
    lines: list[_YamlLine], index: int, indent: int, source: Path
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise RuleError(f"{source}:{line.number}: unexpected indentation")
        if line.text.startswith("-") and (len(line.text) == 1 or line.text[1].isspace()):
            break
        key, raw_value = _split_mapping(line.text, source, line.number)
        if key in result:
            raise RuleError(f"{source}:{line.number}: duplicate YAML key {key!r}")
        if raw_value:
            value = _parse_scalar(raw_value, source, line.number)
            index += 1
        else:
            index += 1
            if index >= len(lines) or lines[index].indent <= indent:
                raise RuleError(
                    f"{source}:{line.number}: mapping key {key!r} needs a value"
                )
            value, index = _parse_block(lines, index, lines[index].indent, source)
        result[key] = value
    return result, index


def _parse_sequence(
    lines: list[_YamlLine], index: int, indent: int, source: Path
) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent != indent:
            raise RuleError(f"{source}:{line.number}: invalid sequence indentation")
        if not line.text.startswith("-") or (
            len(line.text) > 1 and not line.text[1].isspace()
        ):
            break

        item_text = line.text[1:].strip()
        index += 1
        if not item_text:
            if index >= len(lines) or lines[index].indent <= indent:
                raise RuleError(f"{source}:{line.number}: sequence item needs a value")
            item, index = _parse_block(lines, index, lines[index].indent, source)
            result.append(item)
            continue

        mapping_entry = _split_mapping(item_text, source, line.number, required=False)
        if mapping_entry is None:
            result.append(_parse_scalar(item_text, source, line.number))
            if index < len(lines) and lines[index].indent > indent:
                raise RuleError(
                    f"{source}:{lines[index].number}: scalar sequence item cannot have children"
                )
            continue

        key, raw_value = mapping_entry
        item: dict[str, Any] = {}
        if raw_value:
            item[key] = _parse_scalar(raw_value, source, line.number)
        else:
            if index >= len(lines) or lines[index].indent <= indent:
                raise RuleError(
                    f"{source}:{line.number}: mapping key {key!r} needs a value"
                )
            item[key], index = _parse_block(lines, index, lines[index].indent, source)

        if index < len(lines) and lines[index].indent > indent:
            continuation_indent = lines[index].indent
            continuation, index = _parse_mapping(
                lines, index, continuation_indent, source
            )
            for continuation_key, continuation_value in continuation.items():
                if continuation_key in item:
                    raise RuleError(
                        f"{source}:{lines[index - 1].number}: duplicate YAML key "
                        f"{continuation_key!r}"
                    )
                item[continuation_key] = continuation_value
        result.append(item)
    return result, index


def _split_mapping(
    text: str, source: Path, line_number: int, required: bool = True
) -> tuple[str, str] | None:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(text):
        if quote:
            if quote == '"' and character == "\\" and not escaped:
                escaped = True
                continue
            if character == quote:
                if quote == "'" and index + 1 < len(text) and text[index + 1] == "'":
                    continue
                if not escaped:
                    quote = None
            escaped = False
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == ":" and (index + 1 == len(text) or text[index + 1].isspace()):
            key = text[:index].strip()
            if not key:
                break
            if key[0] in {"'", '"'}:
                key = _parse_scalar(key, source, line_number)
            if not isinstance(key, str) or not key:
                break
            return key, text[index + 1 :].strip()
    if required:
        raise RuleError(f"{source}:{line_number}: expected a YAML mapping entry")
    return None


def _parse_scalar(value: str, source: Path, line_number: int) -> Any:
    if not value:
        raise RuleError(f"{source}:{line_number}: empty YAML scalar")
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise RuleError(f"{source}:{line_number}: unterminated single-quoted scalar")
        return value[1:-1].replace("''", "'")
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuleError(f"{source}:{line_number}: invalid double-quoted scalar") from exc
        if not isinstance(parsed, str):
            raise RuleError(f"{source}:{line_number}: quoted scalar must be a string")
        return parsed
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    return value


def _strip_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(line):
        if quote:
            if quote == '"' and character == "\\" and not escaped:
                escaped = True
                continue
            if character == quote:
                if not escaped:
                    quote = None
            escaped = False
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line
