"""Pattern registry for loading and managing regex patterns."""

import re
import logging
from pathlib import Path
from typing import Any, Optional

import yaml
import jsonschema

from regexvault.models import Pattern, Category, Policy, Examples, ActionOnMatch, Severity

logger = logging.getLogger(__name__)


class PatternRegistry:
    """Registry for compiled patterns."""

    def __init__(self) -> None:
        """Initialize empty pattern registry."""
        self.patterns: dict[str, Pattern] = {}  # full_id -> Pattern
        self.namespaces: dict[str, list[Pattern]] = {}  # namespace -> [Pattern]
        self._version: int = 0

    def add_pattern(self, pattern: Pattern) -> None:
        """Add a pattern to the registry."""
        full_id = pattern.full_id
        if full_id in self.patterns:
            logger.warning(f"Pattern {full_id} already exists, overwriting")

        self.patterns[full_id] = pattern

        # Add to namespace index
        if pattern.namespace not in self.namespaces:
            self.namespaces[pattern.namespace] = []
        if pattern not in self.namespaces[pattern.namespace]:
            self.namespaces[pattern.namespace].append(pattern)

        self._version += 1

    def get_pattern(self, ns_id: str) -> Optional[Pattern]:
        """Get pattern by full namespace/id."""
        return self.patterns.get(ns_id)

    def get_namespace_patterns(self, namespace: str) -> list[Pattern]:
        """Get all patterns for a namespace."""
        return self.namespaces.get(namespace, [])

    def get_all_patterns(self) -> list[Pattern]:
        """Get all patterns in registry."""
        return list(self.patterns.values())

    @property
    def version(self) -> int:
        """Get current registry version (increments on changes)."""
        return self._version

    def __len__(self) -> int:
        """Return number of patterns."""
        return len(self.patterns)

    def __repr__(self) -> str:
        """String representation."""
        return f"PatternRegistry(patterns={len(self.patterns)}, namespaces={list(self.namespaces.keys())})"


def load_registry(
    paths: Optional[list[str]] = None,
    validate_schema: bool = True,
    validate_examples: bool = True,
) -> PatternRegistry:
    """
    Load patterns from YAML files into registry.

    Args:
        paths: List of file paths to load. If None, loads default patterns.
        validate_schema: Whether to validate against JSON schema
        validate_examples: Whether to validate examples against patterns

    Returns:
        PatternRegistry with loaded patterns

    Raises:
        FileNotFoundError: If pattern file not found
        ValueError: If pattern validation fails
    """
    registry = PatternRegistry()

    if paths is None:
        # Load default patterns from package
        default_dir = Path(__file__).parent.parent.parent / "patterns"
        paths = [
            str(default_dir / "common.yml"),
            str(default_dir / "kr.yml"),
            str(default_dir / "us.yml"),
        ]

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            logger.warning(f"Pattern file not found: {path}")
            continue

        logger.info(f"Loading patterns from {path}")
        data = _load_yaml_file(path)

        if validate_schema:
            _validate_schema(data)

        patterns = _parse_pattern_file(data)

        for pattern in patterns:
            if validate_examples and pattern.examples:
                _validate_examples(pattern)
            registry.add_pattern(pattern)

    logger.info(f"Loaded {len(registry)} patterns from {len(registry.namespaces)} namespaces")
    return registry


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_schema(data: dict[str, Any]) -> None:
    """Validate pattern data against JSON schema."""
    schema_path = Path(__file__).parent.parent.parent / "schemas" / "pattern-schema.json"

    if not schema_path.exists():
        logger.warning("Pattern schema not found, skipping validation")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Pattern schema validation failed: {e.message}") from e


def _parse_pattern_file(data: dict[str, Any]) -> list[Pattern]:
    """Parse pattern file data into Pattern objects."""
    namespace = data["namespace"]
    patterns = []

    for pattern_data in data.get("patterns", []):
        pattern = _compile_pattern(namespace, pattern_data)
        patterns.append(pattern)

    return patterns


def _compile_pattern(namespace: str, data: dict[str, Any]) -> Pattern:
    """Compile a single pattern definition."""
    pattern_id = data["id"]
    location = data["location"]
    category = Category(data["category"])
    pattern_str = data["pattern"]

    # Parse regex flags
    flags = 0
    for flag_name in data.get("flags", []):
        if flag_name == "IGNORECASE":
            flags |= re.IGNORECASE
        elif flag_name == "MULTILINE":
            flags |= re.MULTILINE
        elif flag_name == "DOTALL":
            flags |= re.DOTALL
        elif flag_name == "UNICODE":
            flags |= re.UNICODE
        elif flag_name == "VERBOSE":
            flags |= re.VERBOSE

    # Compile pattern
    try:
        compiled = re.compile(pattern_str, flags)
    except re.error as e:
        raise ValueError(f"Failed to compile pattern {namespace}/{pattern_id}: {e}") from e

    # Parse policy
    policy_data = data.get("policy", {})
    policy = Policy(
        store_raw=policy_data.get("store_raw", False),
        action_on_match=ActionOnMatch(policy_data.get("action_on_match", "redact")),
        severity=Severity(policy_data.get("severity", "medium")),
    )

    # Parse examples
    examples = None
    if "examples" in data:
        examples = Examples(
            match=data["examples"].get("match", []),
            nomatch=data["examples"].get("nomatch", []),
        )

    return Pattern(
        id=pattern_id,
        namespace=namespace,
        location=location,
        category=category,
        pattern=pattern_str,
        compiled=compiled,
        description=data.get("description", ""),
        flags=data.get("flags", []),
        mask=data.get("mask"),
        examples=examples,
        policy=policy,
        metadata=data.get("metadata", {}),
    )


def _validate_examples(pattern: Pattern) -> None:
    """Validate pattern examples match/nomatch expectations."""
    if not pattern.examples:
        return

    errors = []

    # Check that match examples match
    for example in pattern.examples.match:
        if not pattern.compiled.fullmatch(example):
            errors.append(f"Example should match but doesn't: '{example}'")

    # Check that nomatch examples don't match
    for example in pattern.examples.nomatch:
        if pattern.compiled.fullmatch(example):
            errors.append(f"Example should NOT match but does: '{example}'")

    if errors:
        error_msg = f"Pattern {pattern.full_id} example validation failed:\n" + "\n".join(
            errors
        )
        raise ValueError(error_msg)

    logger.debug(f"Pattern {pattern.full_id} examples validated successfully")
