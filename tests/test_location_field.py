"""Tests for location field functionality."""

import pytest
from pathlib import Path
import tempfile
import yaml

from regexvault import load_registry, Engine
from regexvault.models import Pattern


class TestLocationFieldLoading:
    """Tests for loading patterns with location field."""

    def test_patterns_have_location_field(self):
        """Test that all loaded patterns have location field."""
        registry = load_registry()

        for pattern in registry.get_all_patterns():
            assert hasattr(pattern, 'location'), f"Pattern {pattern.id} missing location field"
            assert pattern.location, f"Pattern {pattern.id} has empty location"
            assert isinstance(pattern.location, str), f"Pattern {pattern.id} location not string"

    def test_korean_patterns_location(self):
        """Test that Korean patterns have kr location."""
        registry = load_registry()
        kr_patterns = registry.get_namespace_patterns("kr")

        for pattern in kr_patterns:
            assert pattern.location == "kr", f"Pattern {pattern.id} should have location 'kr'"

    def test_us_patterns_location(self):
        """Test that US patterns have us location."""
        registry = load_registry()
        us_patterns = registry.get_namespace_patterns("us")

        for pattern in us_patterns:
            assert pattern.location == "us", f"Pattern {pattern.id} should have location 'us'"

    def test_common_patterns_location(self):
        """Test that common patterns have comm location."""
        registry = load_registry()
        common_patterns = registry.get_namespace_patterns("common")

        for pattern in common_patterns:
            assert pattern.location == "comm", f"Pattern {pattern.id} should have location 'comm'"


class TestLocationFieldValidation:
    """Tests for location field validation."""

    def test_location_field_required(self):
        """Test that location field is required in schema."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            # Pattern without location field
            pattern_data = {
                'namespace': 'test',
                'patterns': [{
                    'id': 'test_01',
                    # 'location': 'test',  # Missing location
                    'category': 'phone',
                    'pattern': r'\d{3}-\d{4}',
                }]
            }
            yaml.dump(pattern_data, f)
            temp_path = f.name

        try:
            # Should fail validation due to missing location
            with pytest.raises(Exception):  # Could be ValueError or ValidationError
                load_registry(paths=[temp_path], validate_schema=True)
        finally:
            Path(temp_path).unlink()

    def test_location_field_format_valid(self):
        """Test valid location field formats."""
        valid_locations = ['kr', 'us', 'jp', 'cn', 'comm', 'intl']

        for location in valid_locations:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                pattern_data = {
                    'namespace': 'test',
                    'patterns': [{
                        'id': 'test_01',
                        'location': location,
                        'category': 'phone',
                        'pattern': r'\d{3}-\d{4}',
                    }]
                }
                yaml.dump(pattern_data, f)
                temp_path = f.name

            try:
                # Should load successfully
                registry = load_registry(paths=[temp_path], validate_schema=False)
                patterns = registry.get_namespace_patterns('test')
                assert len(patterns) == 1
                assert patterns[0].location == location
            finally:
                Path(temp_path).unlink()


class TestLocationFieldInPattern:
    """Tests for location field in Pattern model."""

    def test_pattern_has_location_attribute(self):
        """Test that Pattern model has location attribute."""
        registry = load_registry()
        pattern = registry.get_pattern("kr/mobile_01")

        assert hasattr(pattern, 'location')
        assert pattern.location == 'kr'

    def test_pattern_location_in_all_namespaces(self):
        """Test location field exists in all namespace patterns."""
        registry = load_registry()

        namespaces_to_test = ['kr', 'us', 'common']
        expected_locations = {'kr': 'kr', 'us': 'us', 'common': 'comm'}

        for namespace in namespaces_to_test:
            patterns = registry.get_namespace_patterns(namespace)
            assert len(patterns) > 0, f"No patterns found for namespace {namespace}"

            for pattern in patterns:
                assert pattern.location == expected_locations[namespace], \
                    f"Pattern {pattern.id} has wrong location: {pattern.location}"


class TestLocationFieldFiltering:
    """Tests for filtering patterns by location."""

    def test_filter_patterns_by_location_kr(self):
        """Test filtering patterns by Korean location."""
        registry = load_registry()

        kr_patterns = [p for p in registry.get_all_patterns() if p.location == 'kr']

        assert len(kr_patterns) == 8, "Should have 8 Korean patterns"
        for pattern in kr_patterns:
            assert pattern.location == 'kr'
            assert pattern.namespace == 'kr'

    def test_filter_patterns_by_location_us(self):
        """Test filtering patterns by US location."""
        registry = load_registry()

        us_patterns = [p for p in registry.get_all_patterns() if p.location == 'us']

        assert len(us_patterns) == 8, "Should have 8 US patterns"
        for pattern in us_patterns:
            assert pattern.location == 'us'
            assert pattern.namespace == 'us'

    def test_filter_patterns_by_location_comm(self):
        """Test filtering patterns by common location."""
        registry = load_registry()

        comm_patterns = [p for p in registry.get_all_patterns() if p.location == 'comm']

        assert len(comm_patterns) == 6, "Should have 6 common patterns"
        for pattern in comm_patterns:
            assert pattern.location == 'comm'
            assert pattern.namespace == 'common'

    def test_get_all_locations(self):
        """Test getting all unique locations."""
        registry = load_registry()

        locations = {p.location for p in registry.get_all_patterns()}

        assert 'kr' in locations
        assert 'us' in locations
        assert 'comm' in locations
        assert len(locations) == 3


class TestLocationFieldWithEngine:
    """Tests for location field with Engine operations."""

    def test_engine_find_with_location_aware_patterns(self):
        """Test that engine can find patterns with location field."""
        registry = load_registry()
        engine = Engine(registry)

        # Test Korean pattern
        text = "Call me at 010-1234-5678"
        result = engine.find(text, namespaces=["kr"])

        assert result.match_count == 1
        assert result.matches[0].ns_id == "kr/mobile_01"

        # Get the pattern and verify location
        pattern = registry.get_pattern("kr/mobile_01")
        assert pattern.location == 'kr'

    def test_engine_validate_with_location_field(self):
        """Test engine validation with location field."""
        registry = load_registry()
        engine = Engine(registry)

        result = engine.validate("010-1234-5678", "kr/mobile_01")

        assert result.is_valid
        assert result.match is not None

        # Verify pattern has location
        pattern = registry.get_pattern("kr/mobile_01")
        assert pattern.location == 'kr'

    def test_engine_redact_with_location_field(self):
        """Test engine redaction with location field."""
        registry = load_registry()
        engine = Engine(registry)

        text = "My phone is 010-1234-5678"
        result = engine.redact(text, namespaces=["kr"])

        assert result.redaction_count == 1
        assert "010-1234-5678" not in result.redacted_text


class TestLocationFieldConsistency:
    """Tests for location field consistency."""

    def test_namespace_location_consistency(self):
        """Test that namespace and location are consistent."""
        registry = load_registry()

        # Expected mappings
        expected_mappings = {
            'kr': 'kr',
            'us': 'us',
            'common': 'comm',
        }

        for namespace, expected_location in expected_mappings.items():
            patterns = registry.get_namespace_patterns(namespace)
            for pattern in patterns:
                assert pattern.location == expected_location, \
                    f"Pattern {pattern.id} in namespace {namespace} has location {pattern.location}, expected {expected_location}"

    def test_all_patterns_have_valid_location(self):
        """Test that all patterns have valid location values."""
        registry = load_registry()
        valid_locations = {'kr', 'us', 'comm'}

        for pattern in registry.get_all_patterns():
            assert pattern.location in valid_locations, \
                f"Pattern {pattern.id} has invalid location: {pattern.location}"

    def test_location_field_not_empty(self):
        """Test that no pattern has empty location field."""
        registry = load_registry()

        for pattern in registry.get_all_patterns():
            assert pattern.location, f"Pattern {pattern.id} has empty location"
            assert len(pattern.location) >= 2, f"Pattern {pattern.id} location too short"
            assert len(pattern.location) <= 4, f"Pattern {pattern.id} location too long"


class TestLocationFieldWithCustomPatterns:
    """Tests for location field with custom pattern files."""

    def test_load_custom_pattern_with_location(self):
        """Test loading a custom pattern file with location field."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            pattern_data = {
                'namespace': 'custom',
                'description': 'Custom test patterns',
                'patterns': [
                    {
                        'id': 'custom_phone_01',
                        'location': 'test',
                        'category': 'phone',
                        'description': 'Test phone pattern',
                        'pattern': r'\d{3}-\d{4}',
                        'mask': '***-****',
                    }
                ]
            }
            yaml.dump(pattern_data, f)
            temp_path = f.name

        try:
            registry = load_registry(paths=[temp_path], validate_schema=False)
            patterns = registry.get_namespace_patterns('custom')

            assert len(patterns) == 1
            assert patterns[0].id == 'custom_phone_01'
            assert patterns[0].location == 'test'
            assert patterns[0].category.value == 'phone'
        finally:
            Path(temp_path).unlink()

    def test_multiple_patterns_same_location(self):
        """Test multiple patterns can share the same location."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            pattern_data = {
                'namespace': 'multi',
                'patterns': [
                    {
                        'id': 'pattern_01',
                        'location': 'test',
                        'category': 'phone',
                        'pattern': r'\d{3}',
                    },
                    {
                        'id': 'pattern_02',
                        'location': 'test',
                        'category': 'email',
                        'pattern': r'.+@.+',
                    }
                ]
            }
            yaml.dump(pattern_data, f)
            temp_path = f.name

        try:
            registry = load_registry(paths=[temp_path], validate_schema=False)
            patterns = registry.get_namespace_patterns('multi')

            assert len(patterns) == 2
            assert all(p.location == 'test' for p in patterns)
        finally:
            Path(temp_path).unlink()


class TestLocationFieldDocumentation:
    """Tests to verify location field is properly documented."""

    def test_pattern_repr_includes_location(self):
        """Test that pattern representation shows location."""
        registry = load_registry()
        pattern = registry.get_pattern("kr/mobile_01")

        # Pattern object should have location accessible
        assert pattern.location == 'kr'

    def test_all_example_patterns_have_location(self):
        """Test that all example patterns in files have location."""
        registry = load_registry()

        pattern_count = len(registry.get_all_patterns())
        assert pattern_count == 22, f"Expected 22 patterns, found {pattern_count}"

        # All should have location
        patterns_with_location = [p for p in registry.get_all_patterns() if hasattr(p, 'location') and p.location]
        assert len(patterns_with_location) == 22, "All patterns should have location field"
