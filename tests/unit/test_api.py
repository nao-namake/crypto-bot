import pytest
from fastapi.testclient import TestClient

from crypto_bot.api import app


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    return TestClient(app)


def test_health_endpoint(client):
    """Test the health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "ok"]
    assert "timestamp" in data


def test_healthz_endpoint(client):
    """Test the healthz endpoint"""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_health_detailed_endpoint(client):
    """Test the detailed health endpoint"""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "overall_status" in data
    assert "basic" in data
    assert "dependencies" in data


def test_health_ready_endpoint(client):
    """Test the readiness endpoint"""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_health_live_endpoint(client):
    """Test the liveness endpoint"""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_metrics_endpoint(client):
    """Test the metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Metrics should be in Prometheus format (text/plain)
    assert "text/plain" in response.headers.get("content-type", "")
