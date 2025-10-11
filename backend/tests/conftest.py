"""
Pytest configuration and fixtures for Gov Contracts AI Backend tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """
    FastAPI test client fixture.

    Usage:
        def test_something(client):
            response = client.get("/endpoint")
            assert response.status_code == 200
    """
    return TestClient(app)


@pytest.fixture
def sample_licitacao_data():
    """Sample licitacao data for testing."""
    return {
        "id": "test-123",
        "cnpj": "12345678901234",
        "valor": 100000.00,
        "categoria": "construcao",
        "orgao": "Prefeitura Municipal",
    }


# Add more fixtures as needed for database, Redis, etc.
