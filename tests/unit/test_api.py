# tests/unit/test_api.py
"""
Unit tests for the lightweight FastAPI health‑check endpoint defined in
`crypto_bot/api.py`.
These tests are intentionally tiny: they simply verify that the `/healthz`
route is wired up and returns the expected payload/HTTP status.
"""

from fastapi.testclient import TestClient

from crypto_bot.api import app

client = TestClient(app)


def test_healthz():
    """GET /healthz returns JSON {"status": "ok"} with HTTP 200."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
