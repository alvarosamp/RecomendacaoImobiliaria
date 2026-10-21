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
    ("get", "/api/cases"),
    ("get", "/api/municipalities"),
    ("get", "/api/cases/1/report"),
    ("post", "/api/case-demos/invest"),
    ("get", "/api/projects"),
    ("get", "/api/organizations"),
    ("get", "/api/government/diagnosis"),
    ("get", "/api/projects/1/report"),
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


def test_private_routes_reject_missing_token_before_checking_database(client, monkeypatch):
    def unavailable():
        raise AssertionError('Database should not be touched before authentication')
    monkeypatch.setattr(auth, 'ensure_auth_schema', unavailable)
    for path in ['/api/projects', '/api/organizations', '/api/projects/1/report']:
        assert client.get(path).status_code == 401

def test_operational_logs_omit_query_values(client,monkeypatch):
    from api import main
    from api.routes import market
    import pandas as pd
    logged=[]
    monkeypatch.setattr(main.request_log,'info',lambda message:logged.append(message))
    monkeypatch.setattr(market,'_real_listings',lambda:pd.DataFrame())
    login_as('test@example.com','client')
    response=client.get('/api/market/compare?neighborhood=Centro&asking_price=987654321&area_m2=100')
    assert response.status_code==200 and response.headers.get('X-Request-ID')
    assert '/market/compare' in ''.join(logged)
    assert '987654321' not in ''.join(logged) and 'neighborhood' not in ''.join(logged)

def test_operational_errors_do_not_log_documents(client,monkeypatch):
    from api import main
    logged=[]
    monkeypatch.setattr(main.request_log,'error',lambda message:logged.append(message))
    def broken():raise RuntimeError('private document and declared amount 987654321')
    app.dependency_overrides[auth.get_db]=broken
    login_as('test@example.com','client')
    response=client.get('/api/cases')
    assert response.status_code==500
    assert '987654321' not in response.text+''.join(logged)
    assert 'private document' not in response.text+''.join(logged)
