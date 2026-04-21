"""Test batch API endpoint."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_batch_analyze_endpoint_exists(client):
    """Test that the batch endpoint exists and returns expected error for empty items."""
    response = client.post("/api/analyze/batch", json={"items": []})
    # Should not be 404 - we expect it to exist
    assert response.status_code != 404, "Batch endpoint returned 404 - route not registered"


def test_batch_analyze_with_pipeline_param(client):
    """Test that the batch endpoint accepts pipeline query param."""
    response = client.post(
        "/api/analyze/batch?pipeline=voter",
        json={"items": []}
    )
    # Should not be 404
    assert response.status_code != 404, "Batch endpoint with pipeline param returned 404"
