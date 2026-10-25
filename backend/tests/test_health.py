
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_endpoint_returns_connected(monkeypatch):
    monkeypatch.setattr(
        "app.main.check_db_connection",
        lambda: True,
    )

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "connected",
    }


def test_database_health_endpoint_returns_503_on_failure(monkeypatch):
    def raise_database_error():
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(
        "app.main.check_db_connection",
        raise_database_error,
    )

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database connection failed",
    }
