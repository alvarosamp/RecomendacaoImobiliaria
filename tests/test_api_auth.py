import dataclasses

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import auth


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def login_as(email: str, role: str) -> None:
    app.dependency_overrides[auth.get_current_user] = lambda: auth.User(id=1, name="Teste", email=email, role=role)


@pytest.mark.parametrize("method, path", [
    ("get", "/api/scores"),
    ("get", "/api/analytics/neighborhoods-geojson"),
    ("get", "/api/pipeline/status"),
    ("post", "/api/pipeline/run"),
    ("post", "/api/concept/generate-image"),
])
def test_data_routes_require_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401


def test_health_stays_public(client):
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("path", ["/api/pipeline/run", "/api/pipeline/refresh", "/api/pipeline/reset"])
def test_pipeline_actions_require_admin(client, path):
    login_as("corretor@example.com", "corretor")
    assert client.post(path).status_code == 403


def test_admin_by_email_survives_profile_change(client, monkeypatch):
    monkeypatch.setattr(auth, "settings", dataclasses.replace(auth.settings, admin_emails=("gestor@example.com",)))
    login_as("Gestor@Example.com", "incorporadora")
    # reset só limpa o estado em memória do pipeline: seguro para exercitar a permissão.
    assert client.post("/api/pipeline/reset").status_code == 200


def test_legacy_admin_role_is_admin(client):
    login_as("vish@urbia.local", "admin")
    assert client.post("/api/pipeline/reset").status_code == 200
