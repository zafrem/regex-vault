"""Tests for pattern validation."""

import pytest

from regexvault import load_registry


@pytest.fixture
def registry():
    """Load test registry."""
    return load_registry()


class TestPatternLoading:
    """Tests for pattern loading."""

    def test_registry_loads_patterns(self, registry):
        """Test that registry loads patterns successfully."""
        assert len(registry) > 0
        assert len(registry.namespaces) > 0

    def test_korean_patterns_loaded(self, registry):
        """Test that Korean patterns are loaded."""
        kr_patterns = registry.get_namespace_patterns("kr")
        assert len(kr_patterns) > 0

        pattern_ids = {p.id for p in kr_patterns}
        assert "mobile_01" in pattern_ids
        assert "rrn_01" in pattern_ids

    def test_common_patterns_loaded(self, registry):
        """Test that common patterns are loaded."""
        common_patterns = registry.get_namespace_patterns("common")
        assert len(common_patterns) > 0

        pattern_ids = {p.id for p in common_patterns}
        assert "email_01" in pattern_ids

    def test_us_patterns_loaded(self, registry):
        """Test that US patterns are loaded."""
        us_patterns = registry.get_namespace_patterns("us")
        assert len(us_patterns) > 0

        pattern_ids = {p.id for p in us_patterns}
        assert "ssn_01" in pattern_ids
        assert "phone_01" in pattern_ids


class TestKoreanPatterns:
    """Tests for Korean patterns."""

    def test_korean_mobile_pattern(self, registry):
        """Test Korean mobile phone pattern."""
        pattern = registry.get_pattern("kr/mobile_01")
        assert pattern is not None

        # Test matches
        assert pattern.compiled.fullmatch("010-1234-5678")
        assert pattern.compiled.fullmatch("01012345678")
        assert pattern.compiled.fullmatch("011-123-4567")

        # Test non-matches
        assert not pattern.compiled.fullmatch("02-1234-5678")  # Landline
        assert not pattern.compiled.fullmatch("012-1234-5678")  # Invalid prefix

    def test_korean_rrn_pattern(self, registry):
        """Test Korean RRN (Resident Registration Number) pattern."""
        pattern = registry.get_pattern("kr/rrn_01")
        assert pattern is not None

        # Test matches
        assert pattern.compiled.fullmatch("900101-1234567")
        assert pattern.compiled.fullmatch("900101-2234567")
        assert pattern.compiled.fullmatch("8001011234567")  # Without hyphen

        # Test non-matches
        assert not pattern.compiled.fullmatch("900101-5234567")  # Invalid gender digit
        assert not pattern.compiled.fullmatch("900101-123456")  # Too short


class TestCommonPatterns:
    """Tests for common patterns."""

    def test_email_pattern(self, registry):
        """Test email pattern."""
        pattern = registry.get_pattern("common/email_01")
        assert pattern is not None

        # Test matches (using search since pattern doesn't require ^ and $)
        assert pattern.compiled.search("user@example.com")
        assert pattern.compiled.search("john.doe+tag@company.co.uk")
        assert pattern.compiled.search("test_user123@mail-server.org")

        # Test non-matches
        assert not pattern.compiled.fullmatch("invalid.email@")
        assert not pattern.compiled.fullmatch("@example.com")

    def test_ipv4_pattern(self, registry):
        """Test IPv4 pattern."""
        pattern = registry.get_pattern("common/ipv4_01")
        assert pattern is not None

        # Test matches
        assert pattern.compiled.search("192.168.1.1")
        assert pattern.compiled.search("10.0.0.1")
        assert pattern.compiled.search("255.255.255.255")

        # Test non-matches
        assert not pattern.compiled.search("256.1.1.1")
        assert not pattern.compiled.search("192.168.1.1.1")


class TestUSPatterns:
    """Tests for US patterns."""

    def test_us_ssn_pattern(self, registry):
        """Test US SSN pattern."""
        pattern = registry.get_pattern("us/ssn_01")
        assert pattern is not None

        # Test matches
        assert pattern.compiled.fullmatch("123-45-6789")
        assert pattern.compiled.fullmatch("123456789")

        # Test non-matches
        assert not pattern.compiled.fullmatch("12-345-6789")
        assert not pattern.compiled.fullmatch("1234-56-789")

    def test_us_phone_pattern(self, registry):
        """Test US phone pattern."""
        pattern = registry.get_pattern("us/phone_01")
        assert pattern is not None

        # Test matches
        assert pattern.compiled.search("(555) 123-4567")
        assert pattern.compiled.search("555-123-4567")
        assert pattern.compiled.search("5551234567")
        assert pattern.compiled.search("+1-555-123-4567")

        # Test non-matches
        assert not pattern.compiled.fullmatch("123-4567")  # Too short


class TestPatternExamples:
    """Tests that validate pattern examples."""

    def test_all_patterns_have_valid_examples(self, registry):
        """Test that all pattern examples are valid."""
        errors = []

        for pattern in registry.get_all_patterns():
            if not pattern.examples:
                continue

            # Test match examples
            for example in pattern.examples.match:
                if not pattern.compiled.fullmatch(example):
                    errors.append(
                        f"{pattern.full_id}: Example should match but doesn't: '{example}'"
                    )

            # Test nomatch examples
            for example in pattern.examples.nomatch:
                if pattern.compiled.fullmatch(example):
                    errors.append(
                        f"{pattern.full_id}: Example should NOT match but does: '{example}'"
                    )

        if errors:
            pytest.fail("\n".join(errors))


class TestPatternMetadata:
    """Tests for pattern metadata."""

    def test_patterns_have_required_fields(self, registry):
        """Test that all patterns have required fields."""
        for pattern in registry.get_all_patterns():
            assert pattern.id
            assert pattern.namespace
            assert pattern.category
            assert pattern.pattern
            assert pattern.compiled

    def test_patterns_have_policies(self, registry):
        """Test that all patterns have policies."""
        for pattern in registry.get_all_patterns():
            assert pattern.policy is not None
            assert pattern.policy.action_on_match is not None
            assert pattern.policy.severity is not None

    def test_critical_patterns_dont_store_raw(self, registry):
        """Test that critical patterns don't store raw data."""
        for pattern in registry.get_all_patterns():
            if pattern.policy.severity.value == "critical":
                assert (
                    not pattern.policy.store_raw
                ), f"Critical pattern {pattern.full_id} allows storing raw data"
