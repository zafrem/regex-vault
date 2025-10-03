"""Core detection and redaction engine."""

import hashlib
import logging
from typing import Optional

from regexvault.models import (
    Match,
    FindResult,
    ValidationResult,
    RedactionResult,
    RedactionStrategy,
)
from regexvault.registry import PatternRegistry

logger = logging.getLogger(__name__)


class Engine:
    """
    Core engine for PII detection, validation, and redaction.

    The engine uses a PatternRegistry to perform pattern matching operations.
    """

    def __init__(
        self,
        registry: PatternRegistry,
        default_mask_char: str = "*",
        hash_algorithm: str = "sha256",
    ) -> None:
        """
        Initialize engine with pattern registry.

        Args:
            registry: PatternRegistry with loaded patterns
            default_mask_char: Default character to use for masking
            hash_algorithm: Hash algorithm for hashing strategy
        """
        self.registry = registry
        self.default_mask_char = default_mask_char
        self.hash_algorithm = hash_algorithm

    def find(
        self,
        text: str,
        namespaces: Optional[list[str]] = None,
        allow_overlaps: bool = False,
        include_matched_text: bool = False,
    ) -> FindResult:
        """
        Find all PII matches in text.

        Args:
            text: Text to search
            namespaces: List of namespaces to search (e.g., ["kr", "common"]).
                       If None, searches all namespaces.
            allow_overlaps: Whether to allow overlapping matches
            include_matched_text: Whether to include matched text in results
                                 (respects pattern policy)

        Returns:
            FindResult with all matches
        """
        if namespaces is None:
            namespaces = list(self.registry.namespaces.keys())

        matches: list[Match] = []

        # Collect patterns from requested namespaces
        patterns = []
        for ns in namespaces:
            patterns.extend(self.registry.get_namespace_patterns(ns))

        # Search for each pattern
        for pattern in patterns:
            for regex_match in pattern.compiled.finditer(text):
                start, end = regex_match.span()

                # Check for overlaps if not allowed
                if not allow_overlaps:
                    if any(
                        self._spans_overlap((start, end), (m.start, m.end)) for m in matches
                    ):
                        continue

                # Get matched text if allowed by policy
                matched_text = None
                if include_matched_text and pattern.policy.store_raw:
                    matched_text = regex_match.group(0)

                match = Match(
                    ns_id=pattern.full_id,
                    pattern_id=pattern.id,
                    namespace=pattern.namespace,
                    category=pattern.category,
                    start=start,
                    end=end,
                    matched_text=matched_text,
                    mask=pattern.mask,
                    severity=pattern.policy.severity,
                )
                matches.append(match)

        # Sort matches by position
        matches.sort(key=lambda m: (m.start, m.end))

        return FindResult(
            text=text,
            matches=matches,
            namespaces_searched=namespaces,
        )

    def validate(self, text: str, ns_id: str) -> ValidationResult:
        """
        Validate text against a specific pattern.

        Args:
            text: Text to validate
            ns_id: Full namespace/id (e.g., "kr/mobile")

        Returns:
            ValidationResult indicating if text matches pattern

        Raises:
            ValueError: If pattern not found
        """
        pattern = self.registry.get_pattern(ns_id)
        if pattern is None:
            raise ValueError(f"Pattern not found: {ns_id}")

        regex_match = pattern.compiled.fullmatch(text)
        is_valid = regex_match is not None

        match = None
        if is_valid and regex_match:
            matched_text = None
            if pattern.policy.store_raw:
                matched_text = text

            match = Match(
                ns_id=pattern.full_id,
                pattern_id=pattern.id,
                namespace=pattern.namespace,
                category=pattern.category,
                start=0,
                end=len(text),
                matched_text=matched_text,
                mask=pattern.mask,
                severity=pattern.policy.severity,
            )

        return ValidationResult(
            text=text,
            ns_id=ns_id,
            is_valid=is_valid,
            match=match,
        )

    def redact(
        self,
        text: str,
        namespaces: Optional[list[str]] = None,
        strategy: Optional[RedactionStrategy] = None,
        allow_overlaps: bool = False,
    ) -> RedactionResult:
        """
        Redact PII from text.

        Args:
            text: Text to redact
            namespaces: List of namespaces to search. If None, searches all.
            strategy: Redaction strategy (mask/hash/tokenize). If None, uses mask.
            allow_overlaps: Whether to allow overlapping matches

        Returns:
            RedactionResult with redacted text and match information
        """
        if strategy is None:
            strategy = RedactionStrategy.MASK

        # Find all matches
        find_result = self.find(
            text,
            namespaces=namespaces,
            allow_overlaps=allow_overlaps,
            include_matched_text=True,
        )

        if not find_result.has_matches:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                strategy=strategy,
                matches=[],
                redaction_count=0,
            )

        # Build redacted text by replacing matches from end to start
        # (to preserve positions)
        redacted = text
        for match in reversed(find_result.matches):
            original = text[match.start : match.end]
            replacement = self._get_replacement(original, match, strategy)
            redacted = redacted[: match.start] + replacement + redacted[match.end :]

        return RedactionResult(
            original_text=text,
            redacted_text=redacted,
            strategy=strategy,
            matches=find_result.matches,
            redaction_count=len(find_result.matches),
        )

    def _get_replacement(
        self, original: str, match: Match, strategy: RedactionStrategy
    ) -> str:
        """Get replacement text for a match based on strategy."""
        if strategy == RedactionStrategy.MASK:
            # Use pattern mask if available, otherwise use default masking
            if match.mask:
                return match.mask
            return self.default_mask_char * len(original)

        elif strategy == RedactionStrategy.HASH:
            # Return hash of original text
            hasher = hashlib.new(self.hash_algorithm)
            hasher.update(original.encode("utf-8"))
            return f"[HASH:{hasher.hexdigest()[:16]}]"

        elif strategy == RedactionStrategy.TOKENIZE:
            # Return token reference
            return f"[TOKEN:{match.ns_id}:{match.start}]"

        return self.default_mask_char * len(original)

    @staticmethod
    def _spans_overlap(span1: tuple[int, int], span2: tuple[int, int]) -> bool:
        """Check if two spans overlap."""
        start1, end1 = span1
        start2, end2 = span2
        return not (end1 <= start2 or end2 <= start1)
