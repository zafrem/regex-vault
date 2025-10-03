"""
regex-vault: A general-purpose engine for detecting and masking personal information.

This package provides tools for PII detection, validation, and redaction using
pattern-based matching organized by country and information type.
"""

__version__ = "0.1.0"

from regexvault.engine import Engine
from regexvault.registry import load_registry, PatternRegistry
from regexvault.models import FindResult, ValidationResult, RedactionResult

__all__ = [
    "Engine",
    "load_registry",
    "PatternRegistry",
    "FindResult",
    "ValidationResult",
    "RedactionResult",
]
