import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes import auth, leads

HOT_LEAD = {
    "name": "Maria Silva",
    "email": "maria@example.com",
    "budget": 500000,
    "financing_status": "aprovado",
    "timeline": "imediato",
    "visits_done": 2,
    "motivation": "mudanca_urgente",
    "returning_client": True,
}

COLD_LEAD = {
    "name": "Joao Souza",
    "financing_status": "nao_iniciado",
    "timeline": "pesquisando",
    "visits_done": 0,
    "motivation": "apenas_pesquisando",
    "returning_client": False,
}


def make_test_app():
    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    app.include_router(leads.router, prefix="/api")
    return app


def make_sqlite_override():
    """Cria um banco SQLite isolado em memoria e devolve um override de get_db.

    auth.py roda `Base.metadata.create_all` contra o Postgres real no import do
    modulo (com fallback silencioso se o banco estiver fora) — para os testes,
    recriamos as tabelas explicitamente contra o engine SQLite de teste.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    auth.Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    return override_get_db


class LeadScoringTest(unittest.TestCase):
    def setUp(self):
        self.app = make_test_app()
        self.app.dependency_overrides[auth.get_db] = make_sqlite_override()
        self.client = TestClient(self.app)

    def _auth_headers(self, email="corretor@example.com", password="senha123"):
        self.client.post("/api/auth/register", json={"name": "Corretor", "email": email, "password": password})
        res = self.client.post("/api/auth/login", json={"email": email, "password": password})
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_hot_lead_scores_high(self):
        headers = self._auth_headers()
        res = self.client.post("/api/leads", json=HOT_LEAD, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["score"], 70)
        self.assertEqual(data["label"], "Alta chance")
        self.assertGreater(len(data["explain"]), 0)

    def test_cold_lead_scores_low(self):
        headers = self._auth_headers()
        res = self.client.post("/api/leads", json=COLD_LEAD, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertLess(data["score"], 40)
        self.assertEqual(data["label"], "Baixa chance")

    def test_create_requires_auth(self):
        res = self.client.post("/api/leads", json=HOT_LEAD)
        self.assertEqual(res.status_code, 401)

    def test_list_sorted_by_score_desc(self):
        headers = self._auth_headers()
        self.client.post("/api/leads", json=COLD_LEAD, headers=headers)
        self.client.post("/api/leads", json=HOT_LEAD, headers=headers)

        res = self.client.get("/api/leads", headers=headers)
        self.assertEqual(res.status_code, 200)
        rows = res.json()
        self.assertEqual(len(rows), 2)
        self.assertGreaterEqual(rows[0]["score"], rows[1]["score"])
        self.assertEqual(rows[0]["name"], HOT_LEAD["name"])

    def test_update_status_persists(self):
        headers = self._auth_headers()
        created = self.client.post("/api/leads", json=HOT_LEAD, headers=headers).json()

        patched = self.client.patch(
            f"/api/leads/{created['id']}/status", json={"status": "convertido"}, headers=headers
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["status"], "convertido")

        listed = self.client.get("/api/leads", headers=headers).json()
        self.assertEqual(listed[0]["status"], "convertido")

    def test_leads_isolated_per_user(self):
        headers_a = self._auth_headers(email="corretora@example.com")
        headers_b = self._auth_headers(email="corretorb@example.com")

        self.client.post("/api/leads", json=HOT_LEAD, headers=headers_a)
        self.client.post("/api/leads", json=COLD_LEAD, headers=headers_b)

        leads_a = self.client.get("/api/leads", headers=headers_a).json()
        leads_b = self.client.get("/api/leads", headers=headers_b).json()

        self.assertEqual(len(leads_a), 1)
        self.assertEqual(len(leads_b), 1)
        self.assertEqual(leads_a[0]["name"], HOT_LEAD["name"])
        self.assertEqual(leads_b[0]["name"], COLD_LEAD["name"])


if __name__ == "__main__":
    unittest.main()
