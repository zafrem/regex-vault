"""Tests for the core engine."""

import pytest

from regexvault import Engine, load_registry
from regexvault.models import RedactionStrategy


@pytest.fixture
def registry():
    """Load test registry."""
    return load_registry()


@pytest.fixture
def engine(registry):
    """Create engine instance."""
    return Engine(registry)


class TestFind:
    """Tests for find functionality."""

    def test_find_korean_mobile(self, engine):
        """Test finding Korean mobile numbers."""
        text = "Call me at 010-1234-5678 or 01098765432"
        result = engine.find(text, namespaces=["kr"])

        assert result.match_count == 2
        assert result.matches[0].pattern_id == "mobile_01"
        assert result.matches[0].namespace == "kr"

    def test_find_email(self, engine):
        """Test finding email addresses."""
        text = "Contact: john@example.com or support@company.org"
        result = engine.find(text, namespaces=["common"])

        assert result.match_count == 2
        assert all(m.pattern_id == "email_01" for m in result.matches)

    def test_find_multiple_namespaces(self, engine):
        """Test finding across multiple namespaces."""
        text = "Email: test@example.com, Phone: 010-1234-5678"
        result = engine.find(text, namespaces=["kr", "common"])

        assert result.match_count == 2
        categories = {m.category.value for m in result.matches}
        assert "email" in categories
        assert "phone" in categories

    def test_find_no_matches(self, engine):
        """Test finding with no matches."""
        text = "This is just plain text with no PII"
        result = engine.find(text, namespaces=["kr"])

        assert result.match_count == 0
        assert result.has_matches is False

    def test_find_overlaps_not_allowed(self, engine):
        """Test that overlapping matches are excluded by default."""
        # This would need a pattern that could create overlaps
        text = "test@example.com"
        result = engine.find(text, namespaces=["common"], allow_overlaps=False)

        # Should not have overlapping matches
        for i, match1 in enumerate(result.matches):
            for match2 in result.matches[i + 1 :]:
                assert not (
                    match1.start < match2.end and match2.start < match1.end
                ), "Overlapping matches found"


class TestValidate:
    """Tests for validate functionality."""

    def test_validate_valid_korean_mobile(self, engine):
        """Test validating a valid Korean mobile number."""
        result = engine.validate("010-1234-5678", "kr/mobile_01")

        assert result.is_valid is True
        assert result.ns_id == "kr/mobile_01"
        assert result.match is not None

    def test_validate_invalid_korean_mobile(self, engine):
        """Test validating an invalid Korean mobile number."""
        result = engine.validate("02-1234-5678", "kr/mobile_01")  # Landline, not mobile

        assert result.is_valid is False
        assert result.match is None

    def test_validate_valid_email(self, engine):
        """Test validating a valid email."""
        result = engine.validate("user@example.com", "common/email_01")

        assert result.is_valid is True

    def test_validate_pattern_not_found(self, engine):
        """Test validating with non-existent pattern."""
        with pytest.raises(ValueError, match="Pattern not found"):
            engine.validate("test", "invalid/pattern")


class TestRedact:
    """Tests for redact functionality."""

    def test_redact_mask_strategy(self, engine):
        """Test redaction with mask strategy."""
        text = "My phone is 010-1234-5678"
        result = engine.redact(text, namespaces=["kr"], strategy=RedactionStrategy.MASK)

        assert result.redaction_count == 1
        assert "010-1234-5678" not in result.redacted_text
        assert result.strategy == RedactionStrategy.MASK

    def test_redact_hash_strategy(self, engine):
        """Test redaction with hash strategy."""
        text = "Email: test@example.com"
        result = engine.redact(text, namespaces=["common"], strategy=RedactionStrategy.HASH)

        assert result.redaction_count == 1
        assert "test@example.com" not in result.redacted_text
        assert "[HASH:" in result.redacted_text

    def test_redact_tokenize_strategy(self, engine):
        """Test redaction with tokenize strategy."""
        text = "SSN: 123-45-6789"
        result = engine.redact(text, namespaces=["us"], strategy=RedactionStrategy.TOKENIZE)

        assert result.redaction_count == 1
        assert "[TOKEN:" in result.redacted_text

    def test_redact_multiple_items(self, engine):
        """Test redacting multiple PII items."""
        text = "Call 010-1234-5678 or email test@example.com"
        result = engine.redact(text, namespaces=["kr", "common"])

        assert result.redaction_count == 2
        assert "010-1234-5678" not in result.redacted_text
        assert "test@example.com" not in result.redacted_text

    def test_redact_no_matches(self, engine):
        """Test redaction with no matches."""
        text = "This is clean text"
        result = engine.redact(text, namespaces=["kr"])

        assert result.redaction_count == 0
        assert result.redacted_text == text

    def test_redact_preserves_structure(self, engine):
        """Test that redaction preserves text structure."""
        text = "Start 010-1234-5678 End"
        result = engine.redact(text, namespaces=["kr"])

        assert result.redacted_text.startswith("Start ")
        assert result.redacted_text.endswith(" End")


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_text(self, engine):
        """Test with empty text."""
        result = engine.find("", namespaces=["kr"])
        assert result.match_count == 0

    def test_very_long_text(self, engine):
        """Test with very long text."""
        text = "Plain text. " * 10000 + " 010-1234-5678"
        result = engine.find(text, namespaces=["kr"])
        assert result.match_count == 1

    def test_unicode_text(self, engine):
        """Test with unicode characters."""
        text = "연락처: 010-1234-5678 입니다"
        result = engine.find(text, namespaces=["kr"])
        assert result.match_count == 1
