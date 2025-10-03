"""Tests for the server API."""

import pytest
from fastapi.testclient import TestClient

from regexvault.server import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["patterns_loaded"] > 0
        assert len(data["namespaces"]) > 0


class TestFindEndpoint:
    """Tests for /find endpoint."""

    def test_find_with_matches(self, client):
        """Test find endpoint with matches."""
        response = client.post(
            "/find",
            json={
                "text": "Call me at 010-1234-5678",
                "namespaces": ["kr"],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 1
        assert len(data["hits"]) == 1
        assert data["hits"][0]["pattern_id"] == "mobile_01"

    def test_find_no_matches(self, client):
        """Test find endpoint with no matches."""
        response = client.post(
            "/find",
            json={
                "text": "This is plain text",
                "namespaces": ["kr"],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 0
        assert len(data["hits"]) == 0

    def test_find_multiple_namespaces(self, client):
        """Test find with multiple namespaces."""
        response = client.post(
            "/find",
            json={
                "text": "Email: test@example.com, Phone: 010-1234-5678",
                "namespaces": ["kr", "common"],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 2


class TestValidateEndpoint:
    """Tests for /validate endpoint."""

    def test_validate_valid_input(self, client):
        """Test validate endpoint with valid input."""
        response = client.post(
            "/validate",
            json={
                "text": "010-1234-5678",
                "ns_id": "kr/mobile_01",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["ns_id"] == "kr/mobile_01"

    def test_validate_invalid_input(self, client):
        """Test validate endpoint with invalid input."""
        response = client.post(
            "/validate",
            json={
                "text": "02-1234-5678",  # Landline, not mobile
                "ns_id": "kr/mobile_01",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is False

    def test_validate_pattern_not_found(self, client):
        """Test validate with non-existent pattern."""
        response = client.post(
            "/validate",
            json={
                "text": "test",
                "ns_id": "invalid/pattern",
            },
        )
        assert response.status_code == 404


class TestRedactEndpoint:
    """Tests for /redact endpoint."""

    def test_redact_with_matches(self, client):
        """Test redact endpoint with matches."""
        response = client.post(
            "/redact",
            json={
                "text": "My phone is 010-1234-5678",
                "namespaces": ["kr"],
                "strategy": "mask",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["redaction_count"] == 1
        assert "010-1234-5678" not in data["text"]
        assert data["strategy"] == "mask"

    def test_redact_hash_strategy(self, client):
        """Test redact with hash strategy."""
        response = client.post(
            "/redact",
            json={
                "text": "Email: test@example.com",
                "namespaces": ["common"],
                "strategy": "hash",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["redaction_count"] == 1
        assert "[HASH:" in data["text"]

    def test_redact_no_matches(self, client):
        """Test redact with no matches."""
        response = client.post(
            "/redact",
            json={
                "text": "This is clean text",
                "namespaces": ["kr"],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["redaction_count"] == 0
        assert data["text"] == "This is clean text"


class TestReloadEndpoint:
    """Tests for /reload endpoint."""

    def test_reload_patterns(self, client):
        """Test reload endpoint."""
        response = client.post("/reload")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["patterns_loaded"] > 0


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        # Make some requests first
        client.post(
            "/find",
            json={"text": "test 010-1234-5678", "namespaces": ["kr"]},
        )

        # Check metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "regexvault_requests_total" in response.text
