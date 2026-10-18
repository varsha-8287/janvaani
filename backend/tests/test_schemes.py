
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import get_db


client = TestClient(app)


def test_list_schemes_returns_empty_list():
    class FakeScalars:
        def all(self):
            return []

    class FakeSession:
        def scalars(self, statement):
            return FakeScalars()

    def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/schemes")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_schemes_rejects_invalid_limit():
    response = client.get("/schemes?limit=0")
    assert response.status_code == 422


def test_list_schemes_rejects_invalid_offset():
    response = client.get("/schemes?offset=-1")
    assert response.status_code == 422


def test_list_schemes_rejects_invalid_government_level():
    response = client.get("/schemes?government_level=invalid")
    assert response.status_code == 422


def test_get_missing_scheme_returns_404():
    class FakeScalars:
        def first(self):
            return None

    class FakeSession:
        def scalars(self, statement):
            return FakeScalars()

    def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/schemes/nonexistent-scheme")
        assert response.status_code == 404
        assert response.json()["detail"] == "Scheme not found"
    finally:
        app.dependency_overrides.clear()
